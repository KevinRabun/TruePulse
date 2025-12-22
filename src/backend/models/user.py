"""
User model for PostgreSQL storage.

Contains user profile and authentication data.
Vote records are stored separately in Cosmos DB for privacy.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.passkey import DeviceTrustScore, PasskeyCredential, SilentMobileVerification


class User(Base):
    """
    User account model.

    Privacy Design:
    - User IDs are never stored with vote records
    - Demographics are stored here but linked to votes only via aggregation

    Authentication Strategy:
    - Primary & Only: Passkeys (WebAuthn/FIDO2) - phishing resistant, biometric
    - No passwords - passwordless by design for maximum security
    - Verification: Phone carrier verification + email verification
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Authentication - Passkey-only approach (no passwords)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Gamification
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    votes_cast: Mapped[int] = mapped_column(Integer, default=0)
    total_shares: Mapped[int] = mapped_column(Integer, default=0)  # Track sharing for achievements

    # Ad engagement tracking (supports TruePulse)
    ad_views: Mapped[int] = mapped_column(Integer, default=0)
    ad_clicks: Mapped[int] = mapped_column(Integer, default=0)
    ad_view_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_ad_view_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Demographics (optional, for aggregation only)
    age_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # ISO code
    state_province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # State/Province name
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # City name
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Legacy field
    education_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    political_leaning: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # New demographic fields
    marital_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    religious_affiliation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ethnicity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    household_income: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parental_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    housing_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Settings
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_poll_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    show_on_leaderboard: Mapped[bool] = mapped_column(Boolean, default=True)
    share_anonymous_demographics: Mapped[bool] = mapped_column(Boolean, default=True)
    theme_preference: Mapped[str] = mapped_column(String(20), default="system")  # light, dark, system

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Passkey-only mode: user cannot use password authentication
    passkey_only: Mapped[bool] = mapped_column(Boolean, default=True)  # New accounts are passkey-only by default

    # Poll Notification Preferences
    pulse_poll_notifications: Mapped[bool] = mapped_column(Boolean, default=True)  # Daily pulse poll notifications
    flash_poll_notifications: Mapped[bool] = mapped_column(Boolean, default=True)  # Flash poll notifications
    flash_polls_per_day: Mapped[int] = mapped_column(
        Integer, default=5
    )  # Max flash poll notifications per day (0 = unlimited)
    flash_polls_notified_today: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Counter for today's flash notifications
    flash_notification_reset_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Poll engagement stats
    pulse_polls_voted: Mapped[int] = mapped_column(Integer, default=0)
    flash_polls_voted: Mapped[int] = mapped_column(Integer, default=0)
    pulse_poll_streak: Mapped[int] = mapped_column(Integer, default=0)  # Consecutive days voting on pulse polls
    longest_pulse_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_pulse_vote_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_vote_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    achievements = relationship("UserAchievement", back_populates="user")
    # Passkey authentication relationships
    passkey_credentials: Mapped[list["PasskeyCredential"]] = relationship(
        "PasskeyCredential", back_populates="user", cascade="all, delete-orphan"
    )
    device_trust_scores: Mapped[list["DeviceTrustScore"]] = relationship(
        "DeviceTrustScore", back_populates="user", cascade="all, delete-orphan"
    )
    silent_mobile_verifications: Mapped[list["SilentMobileVerification"]] = relationship(
        "SilentMobileVerification", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_passkey(self) -> bool:
        """Check if user has at least one registered passkey."""
        return len(self.passkey_credentials) > 0 if self.passkey_credentials else False

    @property
    def can_use_passwordless(self) -> bool:
        """Check if user can authenticate without password (passkey-only auth)."""
        return self.has_passkey and self.is_verified

    def get_demographics_bucket(self) -> str | None:
        """
        Generate an anonymized demographics bucket for vote aggregation.

        Returns a string like "25-34_US_employed" that can be used
        for demographic analysis without identifying the user.
        """
        if not self.share_anonymous_demographics:
            return None

        parts = []
        if self.age_range:
            parts.append(self.age_range)
        if self.country:
            parts.append(self.country)
        if self.employment_status:
            parts.append(self.employment_status[:3])

        return "_".join(parts) if parts else None
