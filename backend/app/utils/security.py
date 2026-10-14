"""
Security utilities — password hashing, JWT, API key generation.
"""
import hashlib
import hmac
import secrets
import string
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    *,
    extra: dict | None = None,
    expires_minutes: int | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.jwt_expiration_minutes)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": exp,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── API Key generation ────────────────────────────────────────────────────────

_SAFE_CHARS = string.ascii_letters + string.digits


def generate_api_key(environment: str = "live") -> tuple[str, str, str]:
    """
    Returns (full_key, prefix, key_hash).
    Full key is shown ONCE at creation; only the hash is stored in DB.
    """
    env_slug = "test" if environment == "development" else "live"
    random_part = "".join(secrets.choice(_SAFE_CHARS) for _ in range(40))
    prefix = f"dg_{env_slug}_"
    full_key = f"{prefix}{random_part}"
    key_hash = hash_api_key(full_key)
    return full_key, prefix, key_hash


def hash_api_key(key: str) -> str:
    """SHA-256 hash of the full API key — stored in DB."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(submitted_key: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    submitted_hash = hash_api_key(submitted_key)
    return hmac.compare_digest(submitted_hash, stored_hash)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def hash_otp(otp: str) -> str:
    """SHA-256 hash so we never store the plain OTP."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(plain), stored_hash)
