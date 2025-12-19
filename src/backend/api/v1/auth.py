"""
Authentication endpoints for user registration and login.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, TypedDict

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    get_password_hash,
    verify_password,
)
from db.session import get_db
from models.user import User
from schemas.auth import RefreshTokenRequest, TokenResponse
from schemas.user import UserCreate, UserResponse
from services.email_service import EmailService, get_email_service
from services.redis_service import RedisService, get_redis_service

logger = structlog.get_logger(__name__)

router = APIRouter()


class PasswordResetToken(TypedDict):
    """Type for password reset token data."""

    email: str
    user_id: str
    expires_at: datetime


# Fallback in-memory store for password reset tokens (used only when Redis unavailable)
# In production, Redis is preferred for distributed systems
_password_reset_tokens: dict[str, PasswordResetToken] = {}


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for password reset."""

    new_password: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Register a new user account.

    Requirements for voting eligibility:
    - Email must be unique and will require verification
    - Phone must be unique and will require verification
    - Both email AND phone must be verified before user can vote

    This ensures one person = one vote and prevents bot registrations.
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

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user in database
    # User starts unverified - must verify both email AND phone to vote
    new_user = User(
        email=user_data.email.lower(),
        username=user_data.username,
        phone_number=user_data.phone_number,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=False,  # Will be True only when both email AND phone verified
        email_verified=False,
        phone_verified=False,
        total_points=100,  # Welcome bonus
        level=1,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create tokens for immediate login (but user can't vote until verified)
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
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens.

    Uses OAuth2 password flow for compatibility with OpenAPI.
    """
    # Fetch user from database
    result = await db.execute(select(User).where(User.email == form_data.username.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            display_name=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            points=user.total_points,
            level=user.level,
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


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
    email_svc: EmailService = Depends(get_email_service),
) -> dict[str, str]:
    """
    Request password reset email.

    Always returns success to prevent email enumeration attacks.
    If the email exists, a reset link will be sent.
    """
    email = request.email.lower()

    # Check if user exists in database
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = generate_secure_token(32)

        # Store token in Redis (preferred) or fallback to in-memory
        if redis.is_available:
            await redis.store_password_reset_token(
                token=reset_token,
                user_id=str(user.id),
                email=email,
                expires_in_seconds=3600,  # 1 hour
            )
        else:
            # Fallback to in-memory (single instance only)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            _password_reset_tokens[reset_token] = {
                "email": email,
                "user_id": str(user.id),
                "expires_at": expires_at,
            }

        # Send password reset email
        email_sent = await email_svc.send_password_reset_email(
            to_email=email,
            reset_token=reset_token,
        )

        if email_sent:
            logger.info("password_reset_email_sent", email=email[:3] + "***")
        else:
            # Log the token for development when email service unavailable
            logger.warning(
                "password_reset_email_not_sent",
                email=email[:3] + "***",
                reason="email_service_unavailable",
                token_generated=True,
            )
    else:
        logger.info("password_reset_requested_nonexistent", email=email[:3] + "***")

    # Always return success to prevent enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.get("/validate-reset-token/{token}")
async def validate_reset_token(
    token: str,
    redis: RedisService = Depends(get_redis_service),
) -> dict[str, bool]:
    """
    Validate a password reset token.

    Used by frontend to check if token is valid before showing reset form.
    """
    # Try Redis first
    if redis.is_available:
        redis_token_data = await redis.get_password_reset_token(token)
        if redis_token_data:
            return {"valid": True}

    # Fallback to in-memory
    inmem_token_data = _password_reset_tokens.get(token)

    if not inmem_token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if datetime.now(timezone.utc) > inmem_token_data["expires_at"]:
        # Clean up expired token
        del _password_reset_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    return {"valid": True}


@router.post("/reset-password/{token}")
async def reset_password(
    token: str,
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
) -> dict[str, str]:
    """
    Reset password using reset token.

    Token is single-use and expires after 1 hour.
    """
    email: str | None = None
    user_id: str | None = None
    from_redis = False
    expires_at: datetime | None = None

    # Try Redis first
    if redis.is_available:
        redis_token_data = await redis.get_password_reset_token(token)
        if redis_token_data:
            from_redis = True
            email = redis_token_data.get("email")
            user_id = redis_token_data.get("user_id")

    # Fallback to in-memory
    if not email:
        inmem_token_data = _password_reset_tokens.get(token)
        if inmem_token_data:
            email = inmem_token_data["email"]
            user_id = inmem_token_data["user_id"]
            expires_at = inmem_token_data["expires_at"]

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check expiry for in-memory tokens (Redis handles TTL automatically)
    if not from_redis and expires_at and datetime.now(timezone.utc) > expires_at:
        del _password_reset_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Hash the new password
    hashed_password = get_password_hash(request.new_password)

    # Update user password in database
    if user_id:
        from sqlalchemy import update as sql_update

        await db.execute(sql_update(User).where(User.id == user_id).values(hashed_password=hashed_password))
        await db.commit()

    # Invalidate the token (single-use)
    if from_redis:
        await redis.delete_password_reset_token(token)
    elif token in _password_reset_tokens:
        del _password_reset_tokens[token]

    logger.info("password_reset_completed", email=email[:3] + "***")

    return {"message": "Password reset successfully"}
