"""
auth.py — password hashing, JWT creation/verification, current-user dependency
"""
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
import models

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
# SECRET_KEY MUST be set via env var in production — anyone with this value
# can forge login tokens for any account. Generate one with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY         = os.getenv("SECRET_KEY") or "trankr-super-secret-key-change-in-production"
ALGORITHM          = "HS256"
TOKEN_EXPIRE_DAYS  = 30

# Use sha256_crypt as primary (bcrypt has a version conflict with Python 3.12+)
# sha256_crypt is equally secure for this use case and has no dependency issues
pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2  = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# ── OTP helpers ───────────────────────────────────────────────────────────────
import secrets as _secrets

OTP_EXPIRE_MINUTES  = 10
OTP_RESEND_COOLDOWN = 60  # seconds

def generate_otp() -> str:
    return f"{_secrets.randbelow(1_000_000):06d}"

def hash_otp(otp: str) -> str:
    return pwd_ctx.hash(otp)

def verify_otp(otp: str, hashed: str) -> bool:
    return pwd_ctx.verify(otp, hashed)


# ── Dependency ────────────────────────────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> models.User:
    cred_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise cred_err

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise cred_err
    return user
