"""
Vote model for PostgreSQL storage.

Privacy-preserving vote storage using cryptographic hashing.
The user_id is NEVER stored with the vote - only a one-way hash.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Vote(Base):
    """
    Privacy-preserving vote record.

    PRIVACY DESIGN:
    - user_id is NEVER stored
    - vote_hash = SHA-256(user_id + poll_id) - cannot be reversed
    - Only the hash and choice are stored
    - Demographics are optional and anonymized (bucket-level only)
    """

    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Privacy-preserving hash (cannot identify user)
    vote_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hex
        unique=True,
        index=True,
    )

    # Poll and choice (no user reference)
    poll_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("polls.id", ondelete="CASCADE"),
        index=True,
    )
    choice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("poll_choices.id", ondelete="CASCADE"),
        index=True,
    )

    # Anonymized demographics bucket (optional)
    # Format: "age_25-34_country_US" - coarse-grained only
    demographics_bucket: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Composite index for efficient queries
    __table_args__ = (
        Index("ix_votes_poll_choice", "poll_id", "choice_id"),
        Index("ix_votes_poll_created", "poll_id", "created_at"),
    )
