"""
Auth Service -- user registration, login, JWT management (in-memory store).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.db.memory_store import (
    create_user as store_create_user,
    get_user_by_email,
    update_user,
)
from app.models.user import UserCreate, UserResponse
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


async def create_user(data: UserCreate) -> str:
    """
    Register a new user. Returns the new user's string ID.
    Raises 409 if email already exists.
    """
    if get_user_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_TAKEN", "message": "An account with this email already exists."},
        )

    user_id = store_create_user(
        email=data.email.lower(),
        name=data.name.strip(),
        password_hash=hash_password(data.password),
    )

    logger.info("User created: id=%s email=%s", user_id, data.email)
    return user_id


async def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate with email/password. Returns a JWT access token.
    Raises 401 on failure.
    """
    user = get_user_by_email(email)
    
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."},
        )

    if not user["email_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Please verify your email address before logging in.",
            },
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DISABLED", "message": "Your account has been disabled."},
        )

    user_id = user["id"]
    token = create_access_token(subject=user_id)

    update_user(user_id, last_login_at=datetime.now(timezone.utc))

    logger.info("User authenticated: id=%s", user_id)
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


async def get_current_user(token: str) -> UserResponse:
    """Decode JWT and return the authenticated user."""
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_id(user_id_str)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        name=user["name"],
        email_verified=user["email_verified"],
        plan=user["plan"],
        created_at=user["created_at"],
        last_login_at=user["last_login_at"],
    )


async def mark_email_verified(email: str) -> None:
    user = get_user_by_email(email)
    if user:
        update_user(user["id"], email_verified=True, updated_at=datetime.now(timezone.utc))
    logger.info("Email verified: %s", email)


# Need to import get_user_by_id
from app.db.memory_store import get_user_by_id