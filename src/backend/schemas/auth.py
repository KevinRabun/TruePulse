"""
Authentication-related Pydantic schemas.

TruePulse uses passkey-only authentication - no passwords.
"""

from typing import Optional

from pydantic import BaseModel

from schemas.user import UserResponse


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str


# Note: Password reset schemas removed - TruePulse uses passkey-only authentication.
# Account recovery is handled via phone verification + passkey re-registration.
