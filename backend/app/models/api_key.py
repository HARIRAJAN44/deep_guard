"""
API Key Pydantic models (MySQL-backed).
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PrivacyPolicy(BaseModel):
    """Privacy policy selected when creating an API key."""
    retention: str = "delete_immediately"   # delete_immediately | retain_7d | retain_30d | retain_90d
    allow_model_improvement: bool = False   # MUST be explicit opt-in
    policy_version: str = "1.0"
    consented_at: datetime = Field(default_factory=utcnow)


class APIKeyDocument(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: str
    environment: str = "development"        # development | production
    prefix: str                             # e.g. "dg_live_"
    key_hash: str                           # SHA-256 of the full key
    status: str = "active"                  # active | revoked
    privacy_policy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)
    # Usage counters (denormalised for fast reads)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    # Business-model scaffolding
    plan: str = "free"
    monthly_limit: int = 100
    requests_this_month: int = 0
    # Timestamps
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    environment: str = "development"
    retention: str = "delete_immediately"
    allow_model_improvement: bool = False


class APIKeyResponse(BaseModel):
    id: str
    name: str
    environment: str
    prefix: str
    status: str
    privacy_policy: PrivacyPolicy
    total_requests: int
    successful_requests: int
    failed_requests: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    # full_key is only present immediately after creation
    full_key: Optional[str] = None
