"""
Achievement and gamification models.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Achievement(Base):
    """
    Achievement/badge definition.
    """

    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(10))  # Emoji or icon code

    # Requirements
    action_type: Mapped[str] = mapped_column(String(50))  # e.g., "vote", "streak", "leaderboard"
    target_count: Mapped[int] = mapped_column(Integer, default=1)

    # Rewards
    points_reward: Mapped[int] = mapped_column(Integer, default=0)

    # Repeatability - can this achievement be earned multiple times?
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Display
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(20), default="bronze")  # bronze, silver, gold, platinum
    category: Mapped[str] = mapped_column(String(50), default="general")  # voting, streak, leaderboard, profile

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """
    User's progress toward and completion of achievements.
    For repeatable achievements, multiple records can exist per user/achievement pair.
    """

    __tablename__ = "user_achievements"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    achievement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        index=True,
    )

    # Progress (for non-repeatable achievements)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Context for repeatable achievements (e.g., "2025-12-18" for daily, "2025-12" for monthly)
    period_key: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    # Timestamps
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    # Unique constraint: for non-repeatable, one record per user/achievement
    # For repeatable, one record per user/achievement/period
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", "period_key", name="uq_user_achievement_period"),)


class PointsTransaction(Base):
    """
    Record of points earned or spent by a user.
    """

    __tablename__ = "points_transactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Transaction details
    action: Mapped[str] = mapped_column(String(50))  # e.g., "vote", "achievement", "streak"
    points: Mapped[int] = mapped_column(Integer)  # Positive for earned, negative for spent
    description: Mapped[str] = mapped_column(Text)

    # Reference (e.g., poll_id, achievement_id)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class LeaderboardSnapshot(Base):
    """
    Periodic snapshots of leaderboard for performance.
    """

    __tablename__ = "leaderboard_snapshots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    period: Mapped[str] = mapped_column(String(20), index=True)  # daily, weekly, monthly, alltime

    # Snapshot data (JSONB array of {rank, user_id, username, points, level})
    from sqlalchemy.dialects.postgresql import JSONB

    rankings: Mapped[list] = mapped_column(JSONB, default=list)

    total_participants: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class CommunityAchievement(Base):
    """
    Community-wide achievements that all participants earn together.

    Examples:
    - "10K Votes Day" - All who voted on a day that hits 10k total votes
    - "Million Voices" - All who contributed to the millionth vote
    - "Flash Mob" - 1000+ participants in a single flash poll
    """

    __tablename__ = "community_achievements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(10))  # Emoji
    badge_icon: Mapped[str] = mapped_column(String(10))  # Special badge emoji

    # Goal type and target
    goal_type: Mapped[str] = mapped_column(String(50))  # daily_votes, poll_votes, total_platform_votes, etc.
    target_count: Mapped[int] = mapped_column(Integer)

    # Time constraints
    time_window_hours: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Time window for goal (e.g., 24 for daily)

    # Rewards
    points_reward: Mapped[int] = mapped_column(Integer, default=0)
    bonus_multiplier: Mapped[float] = mapped_column(Float, default=1.0)  # Multiplier for points during event

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)  # Can be earned multiple times
    cooldown_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Hours before can trigger again

    # Display
    tier: Mapped[str] = mapped_column(String(20), default="gold")
    category: Mapped[str] = mapped_column(String(50), default="community")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    events = relationship("CommunityAchievementEvent", back_populates="achievement")


class CommunityAchievementEvent(Base):
    """
    Instance of a community achievement being triggered.

    Tracks when the goal was reached and who participated.
    """

    __tablename__ = "community_achievement_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    achievement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("community_achievements.id", ondelete="CASCADE"),
        index=True,
    )

    # Event details
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Progress tracking
    final_count: Mapped[int] = mapped_column(Integer)  # Final count when goal was reached
    participant_count: Mapped[int] = mapped_column(Integer, default=0)

    # Context (e.g., which poll, which day)
    context_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # poll, daily, weekly
    context_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # poll_id or date string

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    achievement = relationship("CommunityAchievement", back_populates="events")
    participants = relationship("CommunityAchievementParticipant", back_populates="event")


class CommunityAchievementParticipant(Base):
    """
    Record of a user participating in a community achievement event.
    """

    __tablename__ = "community_achievement_participants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("community_achievement_events.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Participation details
    contributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    contribution_count: Mapped[int] = mapped_column(Integer, default=1)  # How many actions contributed

    # Reward status
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    badge_awarded: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    event = relationship("CommunityAchievementEvent", back_populates="participants")

    # Unique constraint: one participation per user per event
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_community_participant"),)
