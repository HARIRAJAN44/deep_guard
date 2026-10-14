"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.models.user import UserCreate, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_current_user,
    mark_email_verified,
)
from app.services.otp_service import send_otp, verify_otp_code

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    purpose: str = "email_verification"


class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "email_verification"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ── Signup ────────────────────────────────────────────────────────────────────

@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description="Registers a new user and sends an email OTP for verification.",
)
async def signup(data: UserCreate):
    user_id = await create_user(data)
    # Send OTP immediately after registration
    await send_otp(data.email, purpose="email_verification")
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "message": "Account created. Please check your email for a 6-digit verification code.",
        },
    }


# ── Verify OTP ────────────────────────────────────────────────────────────────

@router.post(
    "/verify-otp",
    summary="Verify email OTP",
    description="Verifies the 6-digit OTP and activates the user's account.",
)
async def verify_otp_endpoint(data: OTPVerifyRequest):
    await verify_otp_code(data.email, data.otp, purpose=data.purpose)
    if data.purpose == "email_verification":
        await mark_email_verified(data.email)
    return {
        "success": True,
        "data": {"message": "Email verified successfully. You can now log in."},
    }


# ── Resend OTP ────────────────────────────────────────────────────────────────

@router.post(
    "/resend-otp",
    summary="Resend OTP",
    description="Sends a fresh OTP. Subject to cooldown restrictions.",
)
async def resend_otp(data: ResendOTPRequest):
    await send_otp(data.email, purpose=data.purpose)
    return {
        "success": True,
        "data": {"message": "A new OTP has been sent."},
    }


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=None,
    summary="Login",
    description="Authenticate with email and password. Returns a JWT access token.",
)
async def login(data: LoginRequest):
    result = await authenticate_user(data.email, data.password)
    return {"success": True, "data": result}


# ── Get Current User ──────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=None,
    summary="Get current user",
    description="Returns the authenticated user's profile.",
)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await get_current_user(credentials.credentials)
    return {"success": True, "data": user.model_dump()}
