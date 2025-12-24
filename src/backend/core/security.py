"""Security utilities for authentication and authorization.

TruePulse uses passkey-only authentication - no passwords.
Implements privacy-preserving vote hashing and secure token management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from core.config import settings

# Token issuer and audience for validation
TOKEN_ISSUER = "truepulse-api"
TOKEN_AUDIENCE = "truepulse-client"


def _create_token_base(
    data: dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Create a JWT token with standard claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "type": token_type,
            "iss": TOKEN_ISSUER,
            "aud": TOKEN_AUDIENCE,
            "jti": secrets.token_urlsafe(16),  # Unique token ID for revocation
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token_base(data, "access", delta)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token_base(data, "refresh", delta)


def create_verification_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT email verification token."""
    delta = expires_delta or timedelta(hours=24)
    return _create_token_base({"sub": user_id}, "verify", delta)


def create_magic_link_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT magic link login token (15 minute expiry)."""
    delta = expires_delta or timedelta(minutes=15)
    return _create_token_base({"sub": user_id}, "magic_link", delta)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode
        expected_type: If provided, validates the token type matches

    Returns:
        The decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
        )
        # Validate token type if specified
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def generate_vote_hash(user_id: str, poll_id: str) -> str:
    """
    Generate a privacy-preserving hash for vote deduplication.

    This hash allows us to:
    1. Prevent duplicate votes (same user + poll = same hash)
    2. Cannot reverse to determine which user voted
    3. Cannot link votes across different polls

    The hash uses a server-side salt (SECRET_KEY) to prevent rainbow table attacks.

    Args:
        user_id: The user's unique identifier
        poll_id: The poll's unique identifier

    Returns:
        A SHA-256 hash that uniquely identifies this user+poll combination
    """
    # Combine user_id, poll_id, and secret salt
    data = f"{user_id}:{poll_id}:{settings.SECRET_KEY}"

    # Generate SHA-256 hash
    return hashlib.sha256(data.encode()).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)
