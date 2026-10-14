"""
Auth Service -- user registration, login, JWT management (MySQL).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_factory
from app.models.user import UserCreate, UserResponse
from app.orm_models import AuditLogORM, UserORM
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


async def _get_session() -> AsyncSession:
    factory = get_session_factory()
    return factory()


async def create_user(data: UserCreate) -> str:
    """
    Register a new user. Returns the new user's string ID.
    Raises 409 if email already exists.
    """
    factory = get_session_factory()
    async with factory() as session:
        # Check for duplicate
        result = await session.execute(
            select(UserORM).where(UserORM.email == data.email.lower())
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_TAKEN", "message": "An account with this email already exists."},
            )

        user = UserORM(
            email=data.email.lower(),
            name=data.name.strip(),
            password_hash=hash_password(data.password),
            email_verified=False,
            is_active=True,
            is_admin=False,
            plan="free",
            monthly_limit=100,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_login_at=None,
        )
        session.add(user)
        await session.flush()   # populate user.id
        user_id = str(user.id)

        # Audit log
        session.add(AuditLogORM(
            action="user_registered",
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
        ))
        await session.commit()

    logger.info("User created: id=%s email=%s", user_id, data.email)
    return user_id


async def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate with email/password. Returns a JWT access token.
    Raises 401 on failure.
    """
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(UserORM).where(UserORM.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."},
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EMAIL_NOT_VERIFIED",
                    "message": "Please verify your email address before logging in.",
                },
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCOUNT_DISABLED", "message": "Your account has been disabled."},
            )

        user_id = str(user.id)
        token = create_access_token(subject=user_id)

        # Update last login
        await session.execute(
            update(UserORM)
            .where(UserORM.id == user.id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await session.commit()

    logger.info("User authenticated: id=%s", user_id)
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


async def get_current_user(token: str) -> UserResponse:
    """Decode JWT and return the authenticated user."""
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        email_verified=user.email_verified,
        plan=user.plan,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


async def mark_email_verified(email: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            update(UserORM)
            .where(UserORM.email == email.lower())
            .values(email_verified=True, updated_at=datetime.now(timezone.utc))
        )
        await session.commit()
    logger.info("Email verified: %s", email)
