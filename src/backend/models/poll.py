"""
Poll model for PostgreSQL storage.

Contains poll metadata and aggregated results.
Individual votes are stored in Azure Table Storage.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class PollStatus(str, Enum):
    """Poll lifecycle status."""

    SCHEDULED = "scheduled"  # Poll is scheduled but not yet active
    ACTIVE = "active"  # Poll is currently accepting votes
    CLOSED = "closed"  # Poll has ended, results are visible
    ARCHIVED = "archived"  # Poll is archived (old polls)


class PollType(str, Enum):
    """Type of poll determining its duration and scheduling."""

    PULSE = "pulse"  # Daily featured poll, 8am-8pm ET (12 hours)
    FLASH = "flash"  # Breaking news poll, runs for 1 hour
    STANDARD = "standard"  # Regular poll with custom duration


class Poll(Base):
    """
    Poll model storing question and aggregated results.

    Individual votes are NOT stored here - they're in Azure Table Storage
    with privacy-preserving hashes.

    Hourly Poll Rotation:
    - Polls start at the top of each hour
    - Duration is configurable (default 1 hour)
    - Only one poll can be "current" at a time
    - Previous poll results shown on main page
    """

    __tablename__ = "polls"

    # Table args including composite indexes for common queries
    __table_args__ = (
        # Composite index for scheduler queries: "get scheduled polls to activate"
        # Used by poll_scheduler.py to efficiently find polls ready to activate
        Index("ix_polls_status_scheduled_start", "status", "scheduled_start"),
        # Composite index for "get active polls by type"
        Index("ix_polls_status_poll_type", "status", "poll_type"),
        # Unique constraint: Only ONE poll per type per time window
        # Prevents race conditions in concurrent scheduler runs from creating duplicates
        UniqueConstraint("poll_type", "scheduled_start", name="uq_polls_type_scheduled_start"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Question
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)

    # Source event (for AI-generated polls)
    source_event: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_event_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=PollStatus.SCHEDULED.value,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Poll type (pulse, flash, or standard)
    poll_type: Mapped[str] = mapped_column(
        String(20),
        default=PollType.STANDARD.value,
        index=True,
    )

    # Special poll flag (for polls that run longer than the standard duration)
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_hours: Mapped[int] = mapped_column(Integer, default=1)  # Override default duration

    # Scheduling
    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )

    # Aggregated results (updated when votes come in)
    total_votes: Mapped[int] = mapped_column(Integer, default=0)

    # Demographic breakdown (JSONB for flexible structure)
    # Format: {"age_25-34": {"choice_1": 45, "choice_2": 55}, ...}
    demographic_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Statistical data
    confidence_interval: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    margin_of_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # AI bias analysis
    bias_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    choices = relationship("PollChoice", back_populates="poll", cascade="all, delete-orphan")

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
        return self.status == PollStatus.ACTIVE.value and not self.is_expired

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


class PollChoice(Base):
    """
    Individual choice option for a poll.

    Stores aggregated vote count - individual votes are in Cosmos DB.
    """

    __tablename__ = "poll_choices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    poll_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("polls.id", ondelete="CASCADE"),
        index=True,
    )

    text: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Aggregated vote count
    vote_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    poll = relationship("Poll", back_populates="choices")

    @property
    def vote_percentage(self) -> float:
        """Calculate vote percentage."""
        if self.poll and self.poll.total_votes > 0:
            return (self.vote_count / self.poll.total_votes) * 100
        return 0.0


class DailyPollSet(Base):
    """
    A set of featured polls for a specific day.
    """

    __tablename__ = "daily_poll_sets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        unique=True,
        index=True,
    )

    theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Poll IDs (stored as JSONB array)
    poll_ids: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
