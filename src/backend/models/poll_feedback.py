"""
Poll Feedback model for crowdsourced quality improvement.

Allows users to provide feedback on AI-generated poll quality,
which is used to improve future poll generation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class FeedbackIssueType(str, Enum):
    """Specific quality issues users can flag."""

    # Content alignment issues
    ANSWERS_DONT_MATCH_ARTICLE = "answers_dont_match_article"
    TEMPORAL_CONFUSION = "temporal_confusion"  # Past vs present confusion
    MISSING_CONTEXT = "missing_context"

    # Bias and framing issues
    BIASED_QUESTION = "biased_question"
    LEADING_LANGUAGE = "leading_language"
    POLITICAL_SLANT = "political_slant"

    # Choice quality issues
    CHOICES_TOO_SIMILAR = "choices_too_similar"
    MISSING_VIEWPOINT = "missing_viewpoint"
    TOO_FEW_CHOICES = "too_few_choices"
    UNCLEAR_CHOICES = "unclear_choices"

    # Topic relevance
    TOO_LOCAL = "too_local"
    NOT_NEWSWORTHY = "not_newsworthy"
    OUTDATED_TOPIC = "outdated_topic"

    # Other
    OTHER = "other"


class PollFeedback(Base):
    """
    User feedback on poll quality.

    Privacy-preserving: Uses vote_hash instead of user_id
    to link feedback to the anonymous voting record.
    """

    __tablename__ = "poll_feedback"

    __table_args__ = (
        # One feedback per user per poll (using vote_hash for privacy)
        Index("ix_poll_feedback_vote_hash_poll", "vote_hash", "poll_id", unique=True),
        # For aggregating feedback by poll
        Index("ix_poll_feedback_poll_rating", "poll_id", "quality_rating"),
        # For finding poorly-rated polls
        Index("ix_poll_feedback_rating_created", "quality_rating", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Link to poll
    poll_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("polls.id", ondelete="CASCADE"),
        index=True,
    )

    # Privacy-preserving user identifier (same hash used for voting)
    # This allows one feedback per user per poll without storing user_id
    vote_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hex
        index=True,
    )

    # Overall quality rating (1-5 stars)
    quality_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Specific issues flagged (stored as JSON array of FeedbackIssueType values)
    issues: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Free-form feedback text (optional, limited to prevent abuse)
    feedback_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Was this poll's content from an AI-generated source?
    was_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Category of the poll (denormalized for analysis)
    poll_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # Metadata for analysis
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Relationship
    poll = relationship("Poll", backref="feedback")


class FeedbackAggregate(Base):
    """
    Aggregated feedback statistics per poll.

    Updated periodically to provide quick access to poll quality metrics
    without querying individual feedback records.
    """

    __tablename__ = "poll_feedback_aggregates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    poll_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("polls.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Aggregate metrics
    total_feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[float] = mapped_column(Integer, default=0)  # Stored as int * 100 for precision

    # Issue frequency counts (JSON: {"temporal_confusion": 5, "biased_question": 2})
    issue_counts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Most common issue for quick reference
    most_common_issue: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

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

    # Relationship
    poll = relationship("Poll", backref="feedback_aggregate", uselist=False)


class CategoryFeedbackPattern(Base):
    """
    Tracks feedback patterns by category to improve future generation.

    For example, if "technology" polls frequently get "temporal_confusion"
    feedback, we can add extra temporal awareness to tech poll prompts.
    """

    __tablename__ = "category_feedback_patterns"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Category being tracked
    category: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    # Total polls analyzed in this category
    total_polls_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    # Average rating across all polls in category
    average_rating: Mapped[float] = mapped_column(Integer, default=0)

    # Issue frequencies (JSON: {"issue_type": percentage})
    issue_frequencies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Top 3 issues for this category
    top_issues: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Custom prompt adjustments learned from feedback
    # JSON: {"temporal_awareness": "high", "bias_check": "strict"}
    learned_adjustments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

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
