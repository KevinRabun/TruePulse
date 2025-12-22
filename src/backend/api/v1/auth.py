"""
Authentication endpoints for user registration.

TruePulse uses passkey-only authentication (WebAuthn/FIDO2) for maximum security.
No passwords are stored or used - all authentication is via passkeys.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, TypedDict

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
)
from db.session import get_db
from models.user import User
from schemas.auth import RefreshTokenRequest, TokenResponse
from schemas.user import UserCreate, UserResponse
from services.email_service import EmailService, get_email_service
from services.redis_service import RedisService, get_redis_service

logger = structlog.get_logger(__name__)

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password - deprecated, passkey recovery instead."""

    email: EmailStr


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Register a new user account.

    Registration flow:
    1. User provides email, phone, and display name
    2. Account is created (unverified)
    3. User must verify phone via SMS
    4. User creates a passkey for authentication
    5. Once phone verified + passkey created, user can vote

    No passwords are used - authentication is passkey-only for maximum security.
    """
    # Check if user already exists by email
    result = await db.execute(select(User).where(User.email == user_data.email.lower()))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if phone number already exists
    result = await db.execute(select(User).where(User.phone_number == user_data.phone_number))
    existing_phone = result.scalar_one_or_none()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_username = result.scalar_one_or_none()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user in database (no password - passkey-only authentication)
    # User starts unverified - must verify phone AND create passkey to vote
    new_user = User(
        email=user_data.email.lower(),
        username=user_data.username,
        phone_number=user_data.phone_number,
        is_active=True,
        is_verified=False,  # Will be True when phone verified
        email_verified=False,
        phone_verified=False,
        total_points=100,  # Welcome bonus
        level=1,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create tokens for immediate session (but user can't vote until phone verified + passkey created)
    token_data = {"sub": str(new_user.id), "email": new_user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            username=new_user.username,
            display_name=user_data.display_name or new_user.username,
            is_active=new_user.is_active,
            is_verified=new_user.is_verified,
            phone_number=new_user.phone_number,
            phone_verified=new_user.phone_verified,
            points=new_user.total_points,
            level=new_user.level,
            has_passkey=False,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    """
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Create new tokens
    token_data = {"sub": payload.get("sub"), "email": payload.get("email")}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    refresh_token: Optional[str] = Body(None, embed=True),
    redis: RedisService = Depends(get_redis_service),
) -> dict[str, str]:
    """
    Logout user and invalidate tokens.

    Adds the refresh token to a blacklist to prevent reuse.
    Access tokens will naturally expire (short-lived).
    """
    if refresh_token:
        # Create a hash of the token for the blacklist key
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()[:16]

        # Blacklist for the duration of refresh token validity
        ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        success = await redis.blacklist_token(token_hash, ttl_seconds)
        if success:
            logger.info("user_logout", token_blacklisted=True)
        else:
            logger.warning("user_logout", token_blacklisted=False, reason="redis_unavailable")
    else:
        logger.info("user_logout", token_blacklisted=False, reason="no_token_provided")

    return {"message": "Successfully logged out"}


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Verify user email address."""
    # Decode the verification token
    payload = decode_token(token)

    if payload is None or payload.get("type") != "verify":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Check user exists first
    from sqlalchemy import select

    user_check = await db.execute(select(User).where(User.id == user_id))
    if not user_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update user to verified
    from sqlalchemy import update as sql_update

    # First, set email_verified=True
    await db.execute(sql_update(User).where(User.id == user_id).values(email_verified=True))

    # Check if phone is also verified, if so set is_verified=True
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.phone_verified:
        await db.execute(sql_update(User).where(User.id == user_id).values(is_verified=True))

    # Award verification achievement
    if user:
        from services.achievement_service import AchievementService

        achievement_service = AchievementService(db)
        await achievement_service.check_and_award_verification_achievements(user, "email")

    await db.commit()

    return {"message": "Email verified successfully"}


# Note: Password reset endpoints removed - TruePulse uses passkey-only authentication.
# Account recovery is handled via phone verification + passkey re-registration.
