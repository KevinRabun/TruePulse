"""
Cosmos DB document models for TruePulse.

These Pydantic models define the document structure stored in Cosmos DB.
Unlike SQLAlchemy models, these are flat documents with embedded relationships
where appropriate.

Container Strategy:
- users: User profiles and settings (partition: /id)
- polls: Poll definitions with embedded choices (partition: /id)
- votes: Individual votes (partition: /poll_id)
- achievements: Achievement definitions (partition: /id)
- user-achievements: User progress on achievements (partition: /user_id)
- email-lookup: Secondary index for email -> user_id (partition: /email)
- username-lookup: Secondary index for username -> user_id (partition: /username)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class PollStatus(str, Enum):
    """Poll lifecycle status."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class PollType(str, Enum):
    """Type of poll determining its duration and scheduling."""

    PULSE = "pulse"  # Daily featured poll
    FLASH = "flash"  # Breaking news poll
    STANDARD = "standard"  # Regular poll


class AchievementTier(str, Enum):
    """Achievement tier levels."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# ============================================================================
# Base Document Model
# ============================================================================


class CosmosDocument(BaseModel):
    """
    Base class for Cosmos DB documents.

    All documents have:
    - id: Unique identifier (also used as partition key for most containers)
    - _ts: Timestamp (managed by Cosmos DB)
    - _etag: ETag for optimistic concurrency (managed by Cosmos DB)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        # Allow extra fields for Cosmos DB system properties (_ts, _etag, etc.)
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True


# ============================================================================
# User Documents
# ============================================================================


class UserDocument(CosmosDocument):
    """
    User document stored in the 'users' container.

    Partition key: /id
    Contains all user profile data, settings, and gamification stats.
    """

    # Authentication (passkey-only)
    email: str  # Unique, indexed via email-lookup container
    username: str  # Unique, indexed via username-lookup container

    # Account status
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    email_verified: bool = False
    passkey_only: bool = True

    # Profile
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

    # Gamification stats
    total_points: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    votes_cast: int = 0
    total_shares: int = 0

    # Ad engagement tracking
    ad_views: int = 0
    ad_clicks: int = 0
    ad_view_streak: int = 0
    last_ad_view_at: Optional[datetime] = None

    # Demographics (optional, for aggregation)
    age_range: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None  # Legacy field for backwards compatibility
    state_province: Optional[str] = None
    city: Optional[str] = None
    education_level: Optional[str] = None
    employment_status: Optional[str] = None
    industry: Optional[str] = None
    political_leaning: Optional[str] = None
    marital_status: Optional[str] = None
    religious_affiliation: Optional[str] = None
    ethnicity: Optional[str] = None
    household_income: Optional[str] = None
    parental_status: Optional[str] = None
    housing_status: Optional[str] = None

    # Demographics consent tracking (GDPR compliance)
    demographics_consent_at: Optional[datetime] = None  # When user consented to share demographics
    demographics_consent_version: Optional[str] = None  # Version of consent form accepted (e.g., "1.0")

    # Settings
    email_notifications: bool = True
    push_notifications: bool = False
    daily_poll_reminder: bool = True
    show_on_leaderboard: bool = True
    share_anonymous_demographics: bool = True
    theme_preference: str = "system"

    # Poll notification preferences
    pulse_poll_notifications: bool = True
    flash_poll_notifications: bool = True
    flash_polls_per_day: int = 5
    flash_polls_notified_today: int = 0
    flash_notification_reset_date: Optional[datetime] = None

    # Poll engagement stats
    pulse_polls_voted: int = 0
    flash_polls_voted: int = 0
    pulse_poll_streak: int = 0
    longest_pulse_streak: int = 0
    last_pulse_vote_date: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    last_login_at: Optional[datetime] = None
    last_vote_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # Passkeys - embedded for efficiency (typically 1-5 per user)
    passkeys: list["PasskeyDocument"] = Field(default_factory=list)

    def get_demographics_bucket(self) -> str | None:
        """Generate an anonymized demographics bucket for vote aggregation."""
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


class PasskeyDocument(BaseModel):
    """Embedded passkey credential within UserDocument."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    credential_id: str  # Base64-encoded credential ID
    public_key: str  # Base64-encoded public key
    sign_count: int = 0
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    transports: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    last_used_at: Optional[datetime] = None
    is_active: bool = True


class EmailLookupDocument(CosmosDocument):
    """
    Secondary index: email -> user_id lookup.

    Partition key: /email
    Used for efficient email-based user lookup.
    """

    email: str
    user_id: str


class UsernameLookupDocument(CosmosDocument):
    """
    Secondary index: username -> user_id lookup.

    Partition key: /username
    Used for efficient username-based user lookup.
    """

    username: str
    user_id: str


# ============================================================================
# Poll Documents
# ============================================================================


class PollChoiceDocument(BaseModel):
    """Embedded poll choice within PollDocument."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    order: int = 0
    vote_count: int = 0

    @property
    def vote_percentage(self) -> float:
        """Vote percentage is calculated at the poll level."""
        return 0.0  # Calculated dynamically


class PollDocument(CosmosDocument):
    """
    Poll document stored in the 'polls' container.

    Partition key: /id
    Contains poll metadata and embedded choices.
    """

    # Question
    question: str
    category: str

    # Source event (for AI-generated polls)
    source_event: Optional[str] = None
    source_event_url: Optional[str] = None

    # Status and type
    status: PollStatus = PollStatus.SCHEDULED
    poll_type: PollType = PollType.STANDARD
    is_active: bool = True
    is_featured: bool = False
    ai_generated: bool = False
    is_special: bool = False
    duration_hours: int = 1

    # Scheduling
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

    # Aggregated results
    total_votes: int = 0

    # Embedded choices (typically 2-6 per poll)
    choices: list[PollChoiceDocument] = Field(default_factory=list)

    # Demographic breakdown (flexible JSON structure)
    demographic_results: Optional[dict[str, Any]] = None

    # Statistical data
    confidence_interval: Optional[float] = None
    margin_of_error: Optional[float] = None

    # AI bias analysis
    bias_analysis: Optional[dict[str, Any]] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    expires_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    notifications_sent_at: Optional[datetime] = None  # Track when notifications were sent

    @property
    def is_expired(self) -> bool:
        """Check if the poll has expired."""
        from datetime import timezone as tz

        now = datetime.now(tz.utc)
        return now > self.expires_at if self.expires_at else False

    @property
    def is_current(self) -> bool:
        """Check if this is the currently active poll."""
        from datetime import timezone as tz

        now = datetime.now(tz.utc)
        if self.scheduled_start and self.scheduled_end:
            return self.scheduled_start <= now < self.scheduled_end
        return self.status == PollStatus.ACTIVE and not self.is_expired

    @property
    def time_remaining_seconds(self) -> int:
        """Get seconds remaining until poll closes."""
        from datetime import timezone as tz

        now = datetime.now(tz.utc)
        end_time = self.scheduled_end or self.expires_at
        if end_time:
            remaining = (end_time - now).total_seconds()
            return max(0, int(remaining))
        return 0

    def get_choice_percentage(self, choice_id: str) -> float:
        """Calculate percentage for a specific choice."""
        if self.total_votes == 0:
            return 0.0
        for choice in self.choices:
            if choice.id == choice_id:
                return (choice.vote_count / self.total_votes) * 100
        return 0.0


# ============================================================================
# Vote Documents
# ============================================================================


class VoteDocument(CosmosDocument):
    """
    Vote document stored in the 'votes' container.

    Partition key: /poll_id
    Privacy-preserving vote record.
    """

    # Vote identification
    poll_id: str  # Partition key
    choice_id: str

    # Privacy-preserving hash (hash of user_id + poll_id + secret)
    vote_hash: str  # Unique per user+poll combination

    # Anonymous demographics (optional)
    demographics_bucket: Optional[str] = None

    # Metadata
    voted_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Note: user_id is NOT stored to preserve privacy
    # The vote_hash prevents duplicate votes while maintaining anonymity


# ============================================================================
# Achievement Documents
# ============================================================================


class AchievementDocument(CosmosDocument):
    """
    Achievement definition stored in the 'achievements' container.

    Partition key: /id
    Defines badges/achievements users can earn.
    """

    # Custom ID (e.g., "first_vote", "streak_7")
    name: str
    description: str
    icon: str  # Emoji or icon code

    # Requirements
    action_type: str  # e.g., "vote", "streak", "leaderboard"
    target_count: int = 1

    # Rewards
    points_reward: int = 0

    # Configuration
    is_repeatable: bool = False
    is_secret: bool = False
    sort_order: int = 0
    tier: AchievementTier = AchievementTier.BRONZE
    category: str = "general"


class UserAchievementDocument(CosmosDocument):
    """
    User's progress on achievements, stored in 'user-achievements' container.

    Partition key: /user_id
    Tracks progress and unlock status for each user.
    """

    user_id: str  # Partition key
    achievement_id: str

    # Progress tracking
    progress: int = 0
    is_unlocked: bool = False

    # For repeatable achievements
    period_key: Optional[str] = None

    # Timestamps
    unlocked_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# Points Transaction Document
# ============================================================================


class PointsTransactionDocument(CosmosDocument):
    """
    Points transaction stored in the 'user-achievements' container.

    Uses same container as UserAchievementDocument but with different document type.
    Partition key: /user_id
    """

    user_id: str  # Partition key
    document_type: str = "points_transaction"

    # Transaction details
    action: str  # e.g., "vote", "achievement", "streak"
    points: int  # Positive for earned, negative for spent
    description: str

    # Reference
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None

    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


# ============================================================================
# Leaderboard Documents
# ============================================================================


class LeaderboardEntryDocument(BaseModel):
    """Embedded leaderboard entry."""

    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    points: int
    rank: int


# ============================================================================
# Community Achievement Documents
# ============================================================================


class CommunityAchievementDocument(CosmosDocument):
    """
    Community achievement definition stored in the 'achievements' container.

    Partition key: /id
    Community achievements are collective goals where all participants
    earn rewards when the community reaches a target together.
    """

    document_type: str = "community_achievement"

    # Basic info
    name: str
    description: str
    icon: str  # Emoji or icon code
    badge_icon: str  # Icon for the badge earned

    # Goal configuration
    goal_type: str  # e.g., "votes", "shares", "streak_users"
    target_count: int
    time_window_hours: Optional[int] = None  # Time limit to achieve goal

    # Rewards
    points_reward: int = 0
    bonus_multiplier: float = 1.0  # Bonus for top contributors

    # Configuration
    is_recurring: bool = False  # Can be triggered multiple times
    cooldown_hours: Optional[int] = None  # Cooldown between recurrences
    tier: AchievementTier = AchievementTier.BRONZE
    category: str = "community"
    sort_order: int = 0
    is_active: bool = True


class CommunityAchievementEventDocument(CosmosDocument):
    """
    Community achievement event tracking stored in 'achievements' container.

    Partition key: /id
    Tracks an active or completed community achievement attempt.
    """

    document_type: str = "community_event"

    achievement_id: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    completed_at: Optional[datetime] = None
    is_completed: bool = False
    final_count: int = 0
    participant_count: int = 0


class CommunityAchievementParticipantDocument(CosmosDocument):
    """
    Community achievement participant stored in 'user-achievements' container.

    Partition key: /user_id
    Tracks user participation in community achievements.
    """

    document_type: str = "community_participant"

    user_id: str  # Partition key
    event_id: str
    achievement_id: str
    contribution_count: int = 0
    contributed_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    badge_awarded: bool = False
    points_awarded: int = 0


class LeaderboardSnapshotDocument(CosmosDocument):
    """
    Leaderboard snapshot stored in the 'polls' container.

    Uses same container as polls with different document type for efficiency.
    Partition key: /id
    """

    document_type: str = "leaderboard_snapshot"
    period_type: str  # "daily", "weekly", "monthly", "all_time"
    period_key: str  # e.g., "2025-01-15", "2025-W03", "2025-01"

    # Embedded top entries (typically top 100)
    entries: list[LeaderboardEntryDocument] = Field(default_factory=list)

    # Metadata
    total_users: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


# ============================================================================
# Location Documents
# ============================================================================


class CountryDocument(CosmosDocument):
    """
    Country document stored in the 'locations' container.

    Partition key: /document_type
    Uses a single partition for countries since they're a small set (250).
    """

    document_type: str = "country"
    code: str  # ISO 3166-1 alpha-2 country code (e.g., "US", "GB")
    name: str  # Full country name


class StateDocument(CosmosDocument):
    """
    State/Province document stored in the 'locations' container.

    Partition key: /document_type
    Grouped by document_type for efficient querying by country.
    """

    document_type: str = "state"
    state_id: int  # Unique numeric ID for the state
    code: Optional[str] = None  # State code (e.g., "CA", "TX")
    name: str  # Full state/province name
    country_code: str  # ISO country code this state belongs to


class CityDocument(CosmosDocument):
    """
    City document stored in the 'locations' container.

    Partition key: /document_type
    Grouped by document_type for efficient querying by state.
    """

    document_type: str = "city"
    city_id: int  # Unique numeric ID for the city
    name: str  # City name
    state_id: int  # State ID this city belongs to
