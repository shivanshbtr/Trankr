"""
email_utils.py — sends the OTP verification email.

Works with any SMTP provider (Gmail app password, Resend, Brevo, etc.) —
just set these env vars:

    SMTP_HOST      e.g. smtp.resend.com  /  smtp.gmail.com
    SMTP_PORT      e.g. 587
    SMTP_USER      your SMTP username (for Resend: "resend"; for Gmail: your address)
    SMTP_PASSWORD  your SMTP password / app password / API key
    SMTP_FROM      the "from" address shown to recipients

If SMTP_HOST isn't set (e.g. local dev), the OTP is printed to the server
console instead of emailed, so local testing never requires real email setup.
"""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST     = os.getenv("SMTP_HOST")
SMTP_PORT     = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER     = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER or "noreply@trankr.app")


def send_otp_email(to_email: str, otp: str, name: str = ""):
    subject = "Your Trankr verification code"
    body = (
        f"Hi {name or 'there'},\n\n"
        f"Your Trankr verification code is: {otp}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, "
        f"you can ignore this email.\n"
    )

    if not SMTP_HOST:
        # Dev fallback — no email service configured, just log it.
        print(f"[DEV MODE] No SMTP configured. OTP for {to_email}: {otp}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
