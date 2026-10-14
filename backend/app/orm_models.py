"""
SQLAlchemy ORM table definitions for DeepGuard (MySQL).

Tables:
  users, otp_verifications, api_keys, analyses,
  usage, privacy_consents, audit_logs
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    monthly_limit: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# otp_verifications
# ---------------------------------------------------------------------------

class OTPVerificationORM(Base):
    __tablename__ = "otp_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), default="email_verification")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# api_keys
# ---------------------------------------------------------------------------

class APIKeyORM(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), default="development")
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Privacy / consent fields (denormalised from privacy_consents)
    retention: Mapped[str] = mapped_column(String(50), default="delete_immediately")
    allow_model_improvement: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_version: Mapped[str] = mapped_column(String(10), default="1.0")
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Usage counters
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    monthly_limit: Mapped[int] = mapped_column(Integer, default=100)
    requests_this_month: Mapped[int] = mapped_column(Integer, default=0)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# analyses
# ---------------------------------------------------------------------------

class AnalysisORM(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    # File info
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Three-stage results stored as JSON
    provenance_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ensemble_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Final verdict
    assessment: Mapped[str] = mapped_column(String(50), default="inconclusive")
    assessment_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    assessment_explanation: Mapped[str] = mapped_column(Text, default="")
    assessment_reasons_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ML versioning
    model_version: Mapped[str] = mapped_column(String(20), default="v1")
    # Processing
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Storage / privacy
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retention_policy: Mapped[str] = mapped_column(String(50), default="delete_immediately")
    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# usage
# ---------------------------------------------------------------------------

class UsageORM(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assessment: Mapped[str] = mapped_column(String(50), default="inconclusive")
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)   # ISO date YYYY-MM-DD
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# ---------------------------------------------------------------------------
# privacy_consents
# ---------------------------------------------------------------------------

class PrivacyConsentORM(Base):
    __tablename__ = "privacy_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    api_key_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    retention: Mapped[str] = mapped_column(String(50), default="delete_immediately")
    allow_model_improvement: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_version: Mapped[str] = mapped_column(String(10), default="1.0")
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# audit_logs
# ---------------------------------------------------------------------------

class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
