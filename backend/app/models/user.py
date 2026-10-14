"""
Pydantic models for user data (MySQL-backed).
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserDocument(BaseModel):
    """Represents a user row in MySQL."""
    id: Optional[int] = None
    email: str
    name: str
    password_hash: str
    email_verified: bool = False
    is_active: bool = True
    is_admin: bool = False
    plan: str = "free"                      # free | pro | business | enterprise
    monthly_limit: int = 100
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str
    accept_terms: bool

    def model_post_init(self, __context):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("You must accept the terms of service")


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    email_verified: bool
    plan: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
