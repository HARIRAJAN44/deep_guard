"""
API Key Service -- creation, lookup, revocation, usage tracking (in-memory store).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.db.memory_store import (
    create_api_key_record,
    get_api_key_by_hash,
    get_api_key_by_id,
    list_api_keys_for_user,
    update_api_key,
)
from app.models.api_key import APIKeyCreate, APIKeyResponse, PrivacyPolicy
from app.utils.security import generate_api_key, hash_api_key

logger = logging.getLogger(__name__)


async def create_api_key(user_id: str, data: APIKeyCreate) -> APIKeyResponse:
    """Create a new API key. Returns the response including the full key (shown ONCE)."""
    full_key, prefix, key_hash = generate_api_key(data.environment)
    now = datetime.now(timezone.utc)

    key_id = create_api_key_record(
        user_id=user_id,
        name=data.name.strip(),
        environment=data.environment,
        prefix=prefix,
        key_hash=key_hash,
        retention=data.retention,
        allow_model_improvement=data.allow_model_improvement,
    )

    logger.info("API key created: id=%s user=%s env=%s", key_id, user_id, data.environment)

    privacy = PrivacyPolicy(
        retention=data.retention,
        allow_model_improvement=data.allow_model_improvement,
    )
    return APIKeyResponse(
        id=key_id,
        name=data.name.strip(),
        environment=data.environment,
        prefix=prefix,
        status="active",
        privacy_policy=privacy,
        total_requests=0,
        successful_requests=0,
        failed_requests=0,
        created_at=now,
        full_key=full_key,    # shown ONCE
    )


async def list_api_keys(user_id: str) -> list[APIKeyResponse]:
    """List all API keys for a user (no full_key revealed)."""
    rows = list_api_keys_for_user(user_id)
    return [_row_to_response(row) for row in rows]


async def get_api_key_by_id(key_id: str, user_id: str) -> APIKeyResponse:
    row = get_api_key_by_id(key_id)
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return _row_to_response(row)


async def revoke_api_key(key_id: str, user_id: str) -> None:
    row = get_api_key_by_id(key_id)
    if not row or row["user_id"] != user_id or row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or already revoked",
        )
    update_api_key(key_id, status="revoked", revoked_at=datetime.now(timezone.utc))
    logger.info("API key revoked: id=%s user=%s", key_id, user_id)


async def delete_api_key(key_id: str, user_id: str) -> None:
    row = get_api_key_by_id(key_id)
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    # In-memory store doesn't have delete, just mark as revoked
    update_api_key(key_id, status="revoked", revoked_at=datetime.now(timezone.utc))
    logger.info("API key deleted: id=%s user=%s", key_id, user_id)


async def authenticate_api_key(submitted_key: str) -> dict:
    """
    Validate a submitted API key and return a plain dict of key attributes.
    Raises 401 if invalid or revoked.
    """
    if not submitted_key or not submitted_key.startswith("dg_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "Invalid API key format."},
        )

    key_hash = hash_api_key(submitted_key)
    row = get_api_key_by_hash(key_hash)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "API key not found."},
        )

    if row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_KEY_REVOKED", "message": "This API key has been revoked."},
        )

    # Update last_used_at and total_requests counter
    update_api_key(
        row["id"],
        last_used_at=datetime.now(timezone.utc),
        total_requests=row["total_requests"] + 1,
    )

    # Return a plain dict compatible with the existing API layer
    return {
        "_id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "privacy_policy": {
            "retention": row["retention"],
            "allow_model_improvement": row["allow_model_improvement"],
        },
        "monthly_limit": row["monthly_limit"],
        "requests_this_month": row["requests_this_month"],
        "status": row["status"],
    }


async def record_api_key_result(key_id: str, success: bool) -> None:
    """Increment success or failure counter for an API key."""
    row = get_api_key_by_id(key_id)
    if not row:
        return
    
    now = datetime.now(timezone.utc)
    if success:
        update_api_key(
            key_id,
            successful_requests=row["successful_requests"] + 1,
            requests_this_month=row["requests_this_month"] + 1,
            last_used_at=now,
        )
    else:
        update_api_key(
            key_id,
            failed_requests=row["failed_requests"] + 1,
            requests_this_month=row["requests_this_month"] + 1,
            last_used_at=now,
        )


def _row_to_response(row: dict) -> APIKeyResponse:
    privacy = PrivacyPolicy(
        retention=row["retention"],
        allow_model_improvement=row["allow_model_improvement"],
        policy_version=row["policy_version"],
        consented_at=row["consented_at"],
    )
    return APIKeyResponse(
        id=str(row["id"]),
        name=row["name"],
        environment=row["environment"],
        prefix=row["prefix"],
        status=row["status"],
        privacy_policy=privacy,
        total_requests=row["total_requests"],
        successful_requests=row["successful_requests"],
        failed_requests=row["failed_requests"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
        full_key=None,   # NEVER revealed again
    )