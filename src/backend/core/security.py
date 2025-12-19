"""
Security utilities for authentication and authorization.

Implements privacy-preserving vote hashing and secure token management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
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
