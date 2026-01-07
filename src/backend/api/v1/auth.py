"""
Authentication endpoints for user registration.

TruePulse uses passkey-only authentication (WebAuthn/FIDO2) for maximum security.
No passwords are stored or used - all authentication is via passkeys.
"""

import hashlib
from typing import Optional

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.deps import get_user_repository, rate_limit_auth
from core.config import settings
from core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
)
from repositories.cosmos_user_repository import CosmosUserRepository
from schemas.auth import RefreshTokenRequest, TokenResponse
from schemas.user import UserCreate, UserResponse
from services.email_service import get_email_service
from services.redis_service import RedisService, get_redis_service

logger = structlog.get_logger(__name__)

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password - deprecated, passkey recovery instead."""

    email: EmailStr


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    _rate_limit: None = Depends(rate_limit_auth),
) -> TokenResponse:
    """
    Register a new user account.

    Registration flow:
    1. User provides email and display name
    2. Account is created (unverified)
    3. User verifies email
    4. User creates a passkey for authentication
    5. Once email verified + passkey created, user can vote

    No passwords are used - authentication is passkey-only for maximum security.
    """
    # Check if user already exists by email
    existing_user = await user_repo.get_by_email(user_data.email.lower())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    existing_username = await user_repo.get_by_username(user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user in database (no password - passkey-only authentication)
    # User starts unverified - must verify email AND create passkey to vote
    new_user = await user_repo.create(
        email=user_data.email.lower(),
        username=user_data.username,
        display_name=user_data.display_name,
        welcome_points=100,  # Welcome bonus
    )

    # Create tokens for immediate session (but user can't vote until email verified + passkey created)
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
            display_name=new_user.display_name or new_user.username,
            is_active=new_user.is_active,
            is_verified=new_user.is_verified,
            points=new_user.total_points,
            level=new_user.level,
            has_passkey=False,
        ),
    )


@router.post("/send-verification-email")
async def send_verification_email(
    email: EmailStr = Body(..., embed=True),
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> dict[str, str]:
    """
    Send a verification email to the user.

    This endpoint can be used to:
    - Send initial verification email after registration
    - Resend verification email if the first one was lost/expired
    """
    # Find user by email
    user = await user_repo.get_by_email(email.lower())

    if not user:
        # Don't reveal whether email exists for security
        logger.info("verification_email_requested", email=email[:3] + "***", user_found=False)
        return {"message": "If an account exists with this email, a verification link has been sent."}

    if user.email_verified:
        logger.info("verification_email_already_verified", user_id=user.id)
        return {"message": "Email is already verified."}

    # Create verification token
    verification_token = create_verification_token(user.id)

    # Send verification email
    email_service = await get_email_service()

    if email_service.is_available:
        sent = await email_service.send_verification_email(
            to_email=user.email,
            verification_token=verification_token,
            username=user.display_name or user.username,
            frontend_url=settings.FRONTEND_URL if hasattr(settings, "FRONTEND_URL") else None,
        )
        logger.info(
            "verification_email_sent",
            user_id=user.id,
            success=sent,
        )
    else:
        logger.warning(
            "verification_email_service_unavailable",
            user_id=user.id,
        )

    return {"message": "If an account exists with this email, a verification link has been sent."}


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
    user_repo: CosmosUserRepository = Depends(get_user_repository),
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
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update user to verified
    # Set email_verified=True and is_verified=True (email is our only verification now)
    user.email_verified = True
    user.is_verified = True
    await user_repo.update(user)

    # Award verification achievement
    # TODO: Update achievement service to use Cosmos DB
    # from services.achievement_service import AchievementService
    # achievement_service = AchievementService()
    # await achievement_service.check_and_award_verification_achievements(user, "email")

    return {"message": "Email verified successfully"}


@router.post("/send-magic-link")
async def send_magic_link(
    email: EmailStr = Body(..., embed=True),
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    _rate_limit: None = Depends(rate_limit_auth),
) -> dict[str, str]:
    """
    Send a magic link login email.

    This allows users to log in without a passkey by clicking a link in their email.
    Useful for:
    - First-time setup after registration
    - Account recovery when switching devices
    - Devices that don't support passkeys
    """
    # Find user by email
    user = await user_repo.get_by_email(email.lower())

    if not user:
        # Return a hint that user may need to register (not a security risk since email enumeration
        # is already possible via registration). This improves UX significantly.
        logger.info("magic_link_requested", email=email[:3] + "***", user_found=False)
        return {
            "message": "No account found with this email. Please register first.",
            "status": "not_found",
        }

    # Create magic link token (15 minute expiry)
    magic_token = create_magic_link_token(str(user.id))

    # Build the magic link URL
    frontend_url = settings.FRONTEND_URL if hasattr(settings, "FRONTEND_URL") else "http://localhost:3001"

    logger.info("magic_link_generated", user_id=str(user.id))

    # Send magic link email
    email_service = await get_email_service()

    if email_service.is_available:
        sent = await email_service.send_magic_link_email(
            to_email=user.email,
            magic_token=magic_token,
            username=user.display_name or user.username,
            frontend_url=frontend_url,
        )
        logger.info(
            "magic_link_sent",
            user_id=str(user.id),
            success=sent,
        )
    else:
        logger.warning(
            "magic_link_email_service_unavailable",
            user_id=str(user.id),
        )

    return {"message": "Login link sent! Check your email.", "status": "sent"}


@router.post("/verify-magic-link/{token}")
async def verify_magic_link(
    token: str,
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """Verify a magic link token and return auth tokens."""
    # Decode the magic link token
    payload = decode_token(token)

    if payload is None or payload.get("type") != "magic_link":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired login link",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login link",
        )

    # Get user
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated",
        )

    # Mark email as verified since clicking magic link proves email ownership
    if not user.email_verified:
        user.email_verified = True
        await user_repo.update(user)
        logger.info("email_verified_via_magic_link", user_id=str(user.id))

    # Check if user has any passkeys
    # TODO: Update passkey check to use Cosmos DB passkey repository
    has_passkey = False  # Placeholder until passkey repository is migrated

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(
        "magic_link_login_success",
        user_id=str(user.id),
        has_passkey=has_passkey,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            display_name=user.display_name or user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            points=user.total_points,
            level=user.level,
            has_passkey=has_passkey,
        ),
    )


# Note: Password reset endpoints removed - TruePulse uses passkey-only authentication.
# Account recovery is handled via email verification + magic link login + passkey re-registration.
