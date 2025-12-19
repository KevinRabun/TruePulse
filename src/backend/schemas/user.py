"""
User-related Pydantic schemas.
"""

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for user registration.

    Both email and phone are required for registration to ensure
    one person = one vote and prevent bot registrations.
    """

    password: str = Field(..., min_length=8, max_length=100)
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Phone number for SMS verification",
    )
    display_name: Optional[str] = Field(None, max_length=100)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format."""
        # Remove common formatting characters
        cleaned = re.sub(r"[\s\-\(\)\.]", "", v)
        # Must start with + or be digits only
        if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
            raise ValueError(
                "Invalid phone number format. Use format: +1234567890 or 1234567890"
            )
        return cleaned


class RecentVote(BaseModel):
    """Schema for recent vote activity (no vote content, just participation)."""

    poll_id: str
    poll_question: str
    voted_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    """Schema for user responses (public-safe)."""

    id: str
    display_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    points: int = 0
    level: int = 1
    total_votes: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    achievements_count: int = 0
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    phone_verified: bool = False
    created_at: Optional[datetime] = None
    recent_votes: List[RecentVote] = []

    model_config = {"from_attributes": True}


class UserInDB(UserBase):
    """Schema for user stored in database (internal use)."""

    id: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False  # True only when BOTH email AND phone are verified
    is_admin: bool = False
    phone_number: Optional[str] = None
    phone_verified: bool = False
    email_verified: bool = False
    points: int = 0
    level: int = 1
    votes_cast: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    # Demographics for vote aggregation
    age_range: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None  # Legacy field
    education_level: Optional[str] = None
    employment_status: Optional[str] = None
    industry: Optional[str] = None
    political_leaning: Optional[str] = None
    # Settings
    share_anonymous_demographics: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)


class UserDemographics(BaseModel):
    """
    User demographic information for aggregated polling insights.

    All fields are optional - users choose what to share.
    This data is NEVER linked to individual votes.
    """

    age_range: Optional[str] = Field(
        None,
        description="Age range (e.g., '18-24', '25-34', '35-44', '45-54', '55-64', '65+')",
    )
    gender: Optional[str] = Field(None, description="Gender identity")
    country: Optional[str] = Field(
        None, description="Country of residence (ISO 3166-1 alpha-2)"
    )
    state_province: Optional[str] = Field(
        None, description="State or Province of residence"
    )
    city: Optional[str] = Field(None, description="City of residence")
    region: Optional[str] = Field(None, description="Region/State (legacy field)")
    education_level: Optional[str] = Field(None, description="Highest education level")
    employment_status: Optional[str] = Field(None, description="Employment status")
    industry: Optional[str] = Field(None, description="Industry sector")
    political_leaning: Optional[str] = Field(
        None, description="General political leaning (optional, self-reported)"
    )
    # New demographic fields
    marital_status: Optional[str] = Field(
        None,
        description="Marital status (e.g., 'single', 'married', 'divorced', 'widowed')",
    )
    religious_affiliation: Optional[str] = Field(
        None, description="Religious affiliation (optional, self-reported)"
    )
    ethnicity: Optional[str] = Field(
        None, description="Ethnic background (optional, self-reported)"
    )
    household_income: Optional[str] = Field(None, description="Household income range")
    parental_status: Optional[str] = Field(
        None, description="Parental status (e.g., 'no children', 'parent')"
    )
    housing_status: Optional[str] = Field(
        None, description="Housing status (e.g., 'own', 'rent')"
    )


# Points awarded for each demographic field
DEMOGRAPHIC_POINTS = {
    "age_range": 150,
    "gender": 100,
    "country": 150,
    "state_province": 125,  # Points for state/province
    "city": 100,  # Points for city
    "region": 100,  # Legacy
    "education_level": 150,
    "employment_status": 125,
    "industry": 125,
    "political_leaning": 200,  # Extra points for sensitive info
    # New fields
    "marital_status": 125,
    "religious_affiliation": 175,  # Higher points for sensitive info
    "ethnicity": 175,  # Higher points for sensitive info
    "household_income": 200,  # Higher points for financial info
    "parental_status": 100,
    "housing_status": 100,
}


class DemographicsUpdateResponse(BaseModel):
    """Response for demographics update with points earned."""

    demographics: UserDemographics
    points_earned: int
    points_breakdown: dict[str, int]
    new_total_points: int
    message: str


class UserSettings(BaseModel):
    """User notification and privacy settings."""

    email_notifications: bool = True
    push_notifications: bool = False
    daily_poll_reminder: bool = True
    show_on_leaderboard: bool = True
    share_anonymous_demographics: bool = True
    sms_notifications: bool = False
    daily_poll_sms: bool = False
    theme_preference: str = "system"  # light, dark, system
    # Pulse Poll notifications (daily 12-hour polls)
    pulse_poll_notifications: bool = True
    # Flash Poll notifications (every 2-3 hours)
    flash_poll_notifications: bool = True
    flash_polls_per_day: int = Field(
        default=5,
        ge=0,
        le=12,
        description="Maximum number of flash poll notifications per day (0 to disable)",
    )


class PhoneNumberUpdate(BaseModel):
    """Schema for adding/updating phone number."""

    phone_number: str = Field(..., min_length=10, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number to E.164 format."""
        # Remove all non-numeric characters except leading +
        cleaned = re.sub(r"[^\d+]", "", v)

        # Ensure it starts with + for international format
        if not cleaned.startswith("+"):
            # Assume US number if no country code
            if len(cleaned) == 10:
                cleaned = "+1" + cleaned
            elif len(cleaned) == 11 and cleaned.startswith("1"):
                cleaned = "+" + cleaned
            else:
                raise ValueError(
                    "Phone number must include country code or be a valid US number"
                )

        # Validate length (E.164 is max 15 digits)
        if len(cleaned) < 10 or len(cleaned) > 16:
            raise ValueError("Invalid phone number length")

        return cleaned


class PhoneVerificationRequest(BaseModel):
    """Schema for verifying phone number with code."""

    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PhoneVerificationResponse(BaseModel):
    """Response for phone verification operations."""

    success: bool
    message: str
    phone_verified: bool = False


class SMSPreferencesUpdate(BaseModel):
    """Schema for updating SMS notification preferences."""

    sms_notifications: bool = False
    daily_poll_sms: bool = False
