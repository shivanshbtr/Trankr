"""
main.py — FastAPI application entry point
Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from database import engine, get_db, Base
import models, schemas
from auth import (
    hash_password, verify_password, create_token, get_current_user,
    generate_otp, hash_otp, verify_otp, OTP_EXPIRE_MINUTES, OTP_RESEND_COOLDOWN,
)
from email_utils import send_otp_email
from datetime import datetime, timedelta
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from routes.goals  import router as goals_router
from routes.tasks  import router as tasks_router
from routes.habits import router as habits_router

# ── Create all tables ─────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Trankr API",
    description = "Backend for Trankr Goal & Progress Tracker",
    version     = "1.0.0",
)

# Allow the frontend (any origin during dev; lock down in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Housekeeping ──────────────────────────────────────────────────────────────
# Unverified accounts whose OTP expired long ago are just dead weight — nobody
# can log in with them anyway. Rather than a separate cron job (overkill at
# personal scale), we sweep them opportunistically whenever someone registers.
STALE_UNVERIFIED_AFTER_HOURS = 24

def cleanup_stale_unverified(db: Session):
    cutoff = datetime.utcnow() - timedelta(hours=STALE_UNVERIFIED_AFTER_HOURS)
    db.query(models.User).filter(
        models.User.is_verified == False,          # noqa: E712
        models.User.otp_expires_at.isnot(None),
        models.User.otp_expires_at < cutoff,
    ).delete(synchronize_session=False)
    db.commit()


# ── Access control ────────────────────────────────────────────────────────────
# Optional single-tenant lock: if ALLOWED_EMAILS is set (comma-separated),
# only those addresses can register. Leave unset for an open instance —
# this is how self-hosters running their own copy would typically run it.
_allowed_emails_raw = os.getenv("ALLOWED_EMAILS", "").strip()
ALLOWED_EMAILS = {e.strip().lower() for e in _allowed_emails_raw.split(",") if e.strip()}

def is_email_allowed(email: str) -> bool:
    return not ALLOWED_EMAILS or email.lower() in ALLOWED_EMAILS

# Google Sign-In: OAuth Client ID from https://console.cloud.google.com/apis/credentials
# (Credentials -> Create Credentials -> OAuth client ID -> Web application).
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()


@app.get("/auth/config", tags=["Auth"])
def auth_config():
    """Public, non-secret config the frontend needs at load time."""
    return {"google_client_id": GOOGLE_CLIENT_ID}


# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=schemas.RegisterResponse, tags=["Auth"])
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    cleanup_stale_unverified(db)

    email = body.email.lower()
    if not is_email_allowed(email):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This instance is private. To use Trankr yourself, clone the repo "
            "and self-host — see instruction_manual.txt in the project root."
        )

    existing = db.query(models.User).filter(models.User.email == email).first()

    if existing and existing.is_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    otp = generate_otp()
    now = datetime.utcnow()

    if existing and not existing.is_verified:
        # Re-registering before verifying — just refresh their OTP, don't
        # create a duplicate row (also lets them fix a typo'd password).
        existing.name           = body.name
        existing.hashed_pw      = hash_password(body.password)
        existing.otp_hash       = hash_otp(otp)
        existing.otp_expires_at = now + timedelta(minutes=OTP_EXPIRE_MINUTES)
        existing.otp_sent_at    = now
        db.commit()
    else:
        user = models.User(
            name           = body.name,
            email          = email,
            hashed_pw      = hash_password(body.password),
            is_verified    = False,
            otp_hash       = hash_otp(otp),
            otp_expires_at = now + timedelta(minutes=OTP_EXPIRE_MINUTES),
            otp_sent_at    = now,
        )
        db.add(user); db.commit()

    send_otp_email(email, otp, body.name)
    return schemas.RegisterResponse(message="Verification code sent to your email", email=email)


@app.post("/auth/verify", response_model=schemas.TokenResponse, tags=["Auth"])
def verify(body: schemas.VerifyOTPRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not user.otp_hash:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending verification for this email")
    if user.is_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already verified — please log in")
    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code expired — request a new one")
    if not verify_otp(body.otp, user.otp_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect code")

    user.is_verified    = True
    user.otp_hash        = None
    user.otp_expires_at  = None
    db.commit()

    return schemas.TokenResponse(
        access_token = create_token(user.id),
        user_id      = user.id,
        name         = user.name,
    )


@app.post("/auth/resend-otp", tags=["Auth"])
def resend_otp(body: schemas.ResendOTPRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or user.is_verified:
        # Don't reveal whether the account exists/is verified.
        return {"message": "If that email is pending verification, a new code has been sent"}

    now = datetime.utcnow()
    if user.otp_sent_at and (now - user.otp_sent_at).total_seconds() < OTP_RESEND_COOLDOWN:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Please wait before requesting another code")

    otp = generate_otp()
    user.otp_hash       = hash_otp(otp)
    user.otp_expires_at = now + timedelta(minutes=OTP_EXPIRE_MINUTES)
    user.otp_sent_at    = now
    db.commit()

    send_otp_email(email, otp, user.name)
    return {"message": "If that email is pending verification, a new code has been sent"}


@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email.lower()).first()
    if not user or not user.hashed_pw or not verify_password(body.password, user.hashed_pw):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email before logging in")
    return schemas.TokenResponse(
        access_token = create_token(user.id),
        user_id      = user.id,
        name         = user.name,
    )


@app.post("/auth/google", response_model=schemas.TokenResponse, tags=["Auth"])
def google_auth(body: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Google Sign-In isn't configured on this server (GOOGLE_CLIENT_ID unset)."
        )

    # Verifies the token's signature, expiry, and that it was issued for our
    # own Client ID (prevents someone else's Google login token from being
    # replayed here). Google itself has already confirmed the email is real
    # and reachable, so there's no OTP/SMTP step needed at all.
    try:
        payload = google_id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google credential")

    if not payload.get("email_verified", False):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google account email is not verified")

    email = payload["email"].lower()
    name  = payload.get("name") or email.split("@")[0]

    if not is_email_allowed(email):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This instance is private. To use Trankr yourself, clone the repo "
            "and self-host — see instruction_manual.txt in the project root."
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            name        = name,
            email       = email,
            hashed_pw   = None,          # Google-only account, no password
            is_verified = True,          # Google already verified the email
        )
        db.add(user); db.commit()
    elif not user.is_verified:
        # Existing unverified password-registration row for this email —
        # Google's own verification is sufficient, so just flip it on.
        user.is_verified = True
        db.commit()

    return schemas.TokenResponse(
        access_token = create_token(user.id),
        user_id      = user.id,
        name         = user.name,
    )


@app.get("/auth/me", tags=["Auth"])
def me(user=Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email}


# ── Feature Routers ───────────────────────────────────────────────────────────
app.include_router(goals_router)
app.include_router(tasks_router)
app.include_router(habits_router)


# ── Serve frontend ────────────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    app.mount("/icons", StaticFiles(directory=os.path.join(frontend_dir, "icons")), name="icons")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/manifest.json", include_in_schema=False)
    def serve_manifest():
        return FileResponse(os.path.join(frontend_dir, "manifest.json"))

    @app.get("/sw.js", include_in_schema=False)
    def serve_sw():
        # must be served from root (not /static) so its scope covers the whole app
        return FileResponse(os.path.join(frontend_dir, "sw.js"), media_type="application/javascript")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "app": "Trankr"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
