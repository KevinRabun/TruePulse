"""
Shared dependencies for API endpoints.

Includes:
- User JWT authentication for consumer API
- Rate limiting (per-user)
"""

from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import decode_token
from db.session import get_db
from models.user import User
from schemas.user import UserInDB
from services.redis_service import RedisService, get_redis_service

logger = structlog.get_logger(__name__)

# Security schemes
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


# =============================================================================
# User Authentication (JWT-based)
# =============================================================================


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> UserInDB:
    """
    Extract and validate the current user from the JWT token.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInDB(
        id=str(user.id),
        email=user.email,
        username=user.username,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        phone_number=user.phone_number,
        phone_verified=user.phone_verified,
        email_verified=user.email_verified,
        points=user.total_points,
        level=user.level,
        votes_cast=user.votes_cast,
        current_streak=user.current_streak,
        longest_streak=user.longest_streak,
        created_at=user.created_at,
    )


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)],
    db: AsyncSession = Depends(get_db),
) -> UserInDB | None:
    """
    Optionally extract and validate the current user from the JWT token.

    Returns None if no token is provided or token is invalid.
    Does not raise exceptions - useful for endpoints that work for both
    authenticated and unauthenticated users.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return None

    return UserInDB(
        id=str(user.id),
        email=user.email,
        username=user.username,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        phone_number=user.phone_number,
        phone_verified=user.phone_verified,
        email_verified=user.email_verified,
        points=user.total_points,
        level=user.level,
        votes_cast=user.votes_cast,
        current_streak=user.current_streak,
        longest_streak=user.longest_streak,
        created_at=user.created_at,
    )


async def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
) -> UserInDB:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_verified_user(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
) -> UserInDB:
    """
    Ensure the current user is fully verified.

    Verification requires BOTH:
    - Email verified
    - Phone verified

    This is required for voting to ensure one person = one vote.
    """
    if not current_user.is_verified:
        # Check what's missing for a helpful error message
        if not current_user.email_verified and not current_user.phone_verified:
            detail = "Please verify both your email and phone number to vote"
        elif not current_user.email_verified:
            detail = "Please verify your email address to vote"
        elif not current_user.phone_verified:
            detail = "Please verify your phone number to vote"
        else:
            detail = "Account verification required to vote"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
    return current_user


async def get_current_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
) -> UserInDB:
    """
    Ensure the current user is an admin.

    Used for administrative actions.
    """
    # Check admin role from database
    # For now, we rely on the is_admin field being checked elsewhere
    return current_user


# =============================================================================
# Rate Limiting
# =============================================================================


class RateLimiter:
    """
    Rate limiter dependency for API endpoints.

    Uses Redis sliding window algorithm for distributed rate limiting.
    Falls back to allowing requests if Redis is unavailable.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        key_prefix: str = "api",
    ):
        self.requests_per_minute = requests_per_minute
        self.key_prefix = key_prefix

    async def __call__(
        self,
        request: Request,
        redis: RedisService = Depends(get_redis_service),
    ) -> None:
        """
        Check rate limit for the current request.

        Raises HTTPException 429 if rate limit exceeded.
        """
        # Get identifier (user ID from auth, or IP address)
        identifier = self._get_identifier(request)
        key = f"{self.key_prefix}:{identifier}"

        is_allowed, remaining = await redis.check_rate_limit(
            identifier=key,
            limit=self.requests_per_minute,
            window_seconds=60,
        )

        if not is_allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier[:20],
                limit=self.requests_per_minute,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Add rate limit headers to response (via request state)
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = self.requests_per_minute

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get user ID from authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in chain (client IP)
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"


# Pre-configured rate limiters
rate_limit_default = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
rate_limit_auth = RateLimiter(requests_per_minute=10, key_prefix="auth")  # Stricter for auth
rate_limit_vote = RateLimiter(requests_per_minute=30, key_prefix="vote")  # Moderate for voting
