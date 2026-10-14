"""
API Key Service -- creation, lookup, revocation, usage tracking (MySQL).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_factory
from app.models.api_key import APIKeyCreate, APIKeyResponse, PrivacyPolicy
from app.orm_models import APIKeyORM, PrivacyConsentORM
from app.utils.security import generate_api_key, verify_api_key

logger = logging.getLogger(__name__)


async def create_api_key(user_id: str, data: APIKeyCreate) -> APIKeyResponse:
    """Create a new API key. Returns the response including the full key (shown ONCE)."""
    factory = get_session_factory()
    async with factory() as session:
        full_key, prefix, key_hash = generate_api_key(data.environment)
        now = datetime.now(timezone.utc)

        api_key = APIKeyORM(
            user_id=int(user_id),
            name=data.name.strip(),
            environment=data.environment,
            prefix=prefix,
            key_hash=key_hash,
            status="active",
            retention=data.retention,
            allow_model_improvement=data.allow_model_improvement,
            policy_version="1.0",
            consented_at=now,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            plan="free",
            monthly_limit=100,
            requests_this_month=0,
            created_at=now,
            last_used_at=None,
            revoked_at=None,
        )
        session.add(api_key)
        await session.flush()   # populate api_key.id
        key_id = str(api_key.id)

        # Store privacy consent record
        session.add(PrivacyConsentORM(
            user_id=user_id,
            api_key_id=key_id,
            retention=data.retention,
            allow_model_improvement=data.allow_model_improvement,
            policy_version="1.0",
            consented_at=now,
        ))
        await session.commit()

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
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(APIKeyORM)
            .where(APIKeyORM.user_id == int(user_id))
            .order_by(APIKeyORM.created_at.desc())
        )
        rows = result.scalars().all()
    return [_orm_to_response(row) for row in rows]


async def get_api_key_by_id(key_id: str, user_id: str) -> APIKeyResponse:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(APIKeyORM).where(
                APIKeyORM.id == int(key_id),
                APIKeyORM.user_id == int(user_id),
            )
        )
        row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return _orm_to_response(row)


async def revoke_api_key(key_id: str, user_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            update(APIKeyORM)
            .where(
                APIKeyORM.id == int(key_id),
                APIKeyORM.user_id == int(user_id),
                APIKeyORM.status == "active",
            )
            .values(status="revoked", revoked_at=datetime.now(timezone.utc))
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or already revoked",
            )
    logger.info("API key revoked: id=%s user=%s", key_id, user_id)


async def delete_api_key(key_id: str, user_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            delete(APIKeyORM).where(
                APIKeyORM.id == int(key_id),
                APIKeyORM.user_id == int(user_id),
            )
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
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

    from app.utils.security import hash_api_key
    key_hash = hash_api_key(submitted_key)

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(APIKeyORM).where(APIKeyORM.key_hash == key_hash)
        )
        row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "API key not found."},
        )

    if row.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_KEY_REVOKED", "message": "This API key has been revoked."},
        )

    # Update last_used_at and total_requests counter
    factory2 = get_session_factory()
    async with factory2() as session2:
        await session2.execute(
            update(APIKeyORM)
            .where(APIKeyORM.id == row.id)
            .values(
                last_used_at=datetime.now(timezone.utc),
                total_requests=APIKeyORM.total_requests + 1,
            )
        )
        await session2.commit()

    # Return a plain dict compatible with the existing API layer
    return {
        "_id": str(row.id),
        "user_id": str(row.user_id),
        "privacy_policy": {
            "retention": row.retention,
            "allow_model_improvement": row.allow_model_improvement,
        },
        "monthly_limit": row.monthly_limit,
        "requests_this_month": row.requests_this_month,
        "status": row.status,
    }


async def record_api_key_result(key_id: str, success: bool) -> None:
    """Increment success or failure counter for an API key."""
    factory = get_session_factory()
    async with factory() as session:
        if success:
            await session.execute(
                update(APIKeyORM)
                .where(APIKeyORM.id == int(key_id))
                .values(
                    successful_requests=APIKeyORM.successful_requests + 1,
                    requests_this_month=APIKeyORM.requests_this_month + 1,
                )
            )
        else:
            await session.execute(
                update(APIKeyORM)
                .where(APIKeyORM.id == int(key_id))
                .values(
                    failed_requests=APIKeyORM.failed_requests + 1,
                    requests_this_month=APIKeyORM.requests_this_month + 1,
                )
            )
        await session.commit()


def _orm_to_response(row: APIKeyORM) -> APIKeyResponse:
    privacy = PrivacyPolicy(
        retention=row.retention,
        allow_model_improvement=row.allow_model_improvement,
        policy_version=row.policy_version,
        consented_at=row.consented_at,
    )
    return APIKeyResponse(
        id=str(row.id),
        name=row.name,
        environment=row.environment,
        prefix=row.prefix,
        status=row.status,
        privacy_policy=privacy,
        total_requests=row.total_requests,
        successful_requests=row.successful_requests,
        failed_requests=row.failed_requests,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        full_key=None,   # NEVER revealed again
    )
