"""
OTP Service -- generate, store (hashed), verify, and resend OTPs (in-memory store).

Development mode: OTP is printed to the console.
Production mode: OTP is sent via SMTP.
"""
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import HTTPException, status

from app.config import get_settings
from app.db.memory_store import (
    get_otp,
    upsert_otp,
    increment_otp_attempts,
    delete_otp,
)
from app.utils.security import generate_otp, hash_otp, verify_otp

logger = logging.getLogger(__name__)


async def send_otp(email: str, purpose: str = "email_verification") -> None:
    """
    Generate a fresh OTP, store its hash, and deliver it.
    Replaces any existing OTP for this email+purpose.
    """
    settings = get_settings()

    # Check resend cooldown
    existing = get_otp(email, purpose)

    if existing:
        created = existing["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        cooldown = timedelta(seconds=settings.otp_resend_cooldown_seconds)
        elapsed = datetime.now(timezone.utc) - created
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "OTP_COOLDOWN",
                    "message": f"Please wait {remaining} seconds before requesting a new OTP.",
                },
            )

    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiration_minutes)
    now = datetime.now(timezone.utc)

    upsert_otp(email, purpose, hash_otp(otp), expires_at)

    # Deliver the OTP
    if settings.otp_dev_mode:
        logger.warning(
            "DEV MODE -- OTP for %s [%s]: %s  (expires in %d min)",
            email, purpose, otp, settings.otp_expiration_minutes,
        )
        print(f"\n{'='*60}")
        print(f"  DEV MODE OTP")
        print(f"  Email   : {email}")
        print(f"  Purpose : {purpose}")
        print(f"  OTP     : {otp}")
        print(f"  Expires : {settings.otp_expiration_minutes} minutes")
        print(f"{'='*60}\n")
    else:
        await _send_email_otp(email, otp, purpose, settings)


async def verify_otp_code(email: str, otp_code: str, purpose: str = "email_verification") -> None:
    """
    Verify a submitted OTP. Raises HTTPException on failure.
    Deletes the OTP record on success.
    """
    settings = get_settings()
    otp_row = get_otp(email, purpose)

    if not otp_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_NOT_FOUND", "message": "No pending OTP found. Please request a new one."},
        )

    # Check expiry
    expires_at = otp_row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        delete_otp(email, purpose)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_EXPIRED", "message": "The OTP has expired. Please request a new one."},
        )

    # Check attempt limit
    attempts = otp_row["attempts"]
    if attempts >= settings.otp_max_attempts:
        delete_otp(email, purpose)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "OTP_MAX_ATTEMPTS",
                "message": "Too many incorrect attempts. Please request a new OTP.",
            },
        )

    # Verify
    if not verify_otp(otp_code, otp_row["otp_hash"]):
        increment_otp_attempts(email, purpose)
        remaining = settings.otp_max_attempts - attempts - 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_OTP",
                "message": f"Incorrect OTP. {remaining} attempt(s) remaining.",
            },
        )

    # Success -- delete OTP record
    delete_otp(email, purpose)

    logger.info("OTP verified successfully for %s [%s]", email, purpose)


async def _send_email_otp(email: str, otp: str, purpose: str, settings) -> None:
    """Send OTP via SMTP (production mode)."""
    subject = "Your DeepGuard Verification Code"
    body = f"""
    <html><body style="font-family: sans-serif; background: #0a0e1a; color: #e2e8f0; padding: 40px;">
    <div style="max-width: 500px; margin: auto; background: #1a2035; border-radius: 12px; padding: 32px;">
      <h1 style="color: #6366f1;">DeepGuard</h1>
      <p>Your verification code is:</p>
      <div style="font-size: 36px; font-weight: bold; color: #6366f1; letter-spacing: 8px; padding: 16px 0;">
        {otp}
      </div>
      <p style="color: #94a3b8;">This code expires in {settings.otp_expiration_minutes} minutes.</p>
      <p style="color: #94a3b8; font-size: 12px;">
        If you did not request this, please ignore this email.
      </p>
    </div>
    </body></html>
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = email
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from, email, msg.as_string())

        logger.info("OTP email sent to %s", email)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", email, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EMAIL_SEND_FAILED", "message": "Failed to send verification email. Please try again."},
        )