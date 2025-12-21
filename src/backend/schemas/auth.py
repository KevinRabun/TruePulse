"""
Authentication-related Pydantic schemas.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

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
    """Confirm password reset with token.

    Password requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v
