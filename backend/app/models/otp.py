"""
OTP document model.
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OTPDocument(BaseModel):
    email: str
    otp_hash: str                           # SHA-256 of the 6-digit OTP
    purpose: str = "email_verification"    # email_verification | password_reset
    attempts: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime                   # set by otp_service

    class Config:
        populate_by_name = True
