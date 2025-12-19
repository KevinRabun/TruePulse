"""
User Vote History model for tracking user voting activity.

This table stores WHICH polls a user voted on and WHEN,
but NOT what they voted for (preserving vote privacy).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class UserVoteHistory(Base):
    """
    User voting history record.

    PURPOSE:
    - Track which polls a user has participated in
    - Enable "recent activity" features
    - Support voting streaks

    PRIVACY NOTE:
    - Stores only poll_id and timestamp
    - Does NOT store what the user voted for
    - Actual vote choice remains anonymous in the votes table
    """

    __tablename__ = "user_vote_history"

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

    poll_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("polls.id", ondelete="CASCADE"),
        index=True,
    )

    voted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (Index("ix_user_vote_history_user_voted", "user_id", "voted_at"),)
