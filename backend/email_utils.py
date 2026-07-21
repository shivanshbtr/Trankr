"""
email_utils.py — sends the OTP verification email via Brevo's HTTP API.

Render's free tier blocks outbound SMTP ports (25/465/587), so smtplib
can't be used there. Brevo's transactional email API is a plain HTTPS
POST on port 443, which works fine on Render's free tier.

Set these env vars (see backend/.env.example):

    BREVO_API_KEY   your Brevo API key (Settings -> SMTP & API -> API Keys)
    EMAIL_FROM      the "from" address shown to recipients
                    (must be a verified sender in your Brevo account)
    EMAIL_FROM_NAME optional display name for the "from" address

If BREVO_API_KEY isn't set (e.g. local dev), the OTP is printed to the
server console instead of emailed, so local testing never requires a
real email account.

No third-party HTTP library is required — this uses Python's stdlib
urllib, so no new entries were needed in requirements.txt.
"""
import json
import os
import urllib.error
import urllib.request

BREVO_API_KEY   = os.getenv("BREVO_API_KEY")
EMAIL_FROM      = os.getenv("EMAIL_FROM", "noreply@trankr.app")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Trankr")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_otp_email(to_email: str, otp: str, name: str = ""):
    subject = "Your Trankr verification code"
    text_body = (
        f"Hi {name or 'there'},\n\n"
        f"Your Trankr verification code is: {otp}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, "
        f"you can ignore this email.\n"
    )
    html_body = (
        f"<p>Hi {name or 'there'},</p>"
        f"<p>Your Trankr verification code is: <strong>{otp}</strong></p>"
        f"<p>This code expires in 10 minutes. If you didn't request this, "
        f"you can ignore this email.</p>"
    )

    if not BREVO_API_KEY:
        # Dev fallback — no email service configured, just log it.
        print(f"[DEV MODE] No BREVO_API_KEY configured. OTP for {to_email}: {otp}")
        return

    payload = {
        "sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM},
        "to": [{"email": to_email, "name": name or to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
    }

    req = urllib.request.Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        # Surface Brevo's error body to make debugging (bad key, unverified
        # sender, etc.) obvious in the Render logs instead of a bare 401/400.
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Brevo API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to reach Brevo API: {e.reason}") from e
