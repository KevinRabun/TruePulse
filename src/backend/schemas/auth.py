"""
Authentication-related Pydantic schemas.
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


class PasswordResetRequest(BaseModel):
    """Request password reset."""
    email: str


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""
    token: str
    new_password: str
