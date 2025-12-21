"""
Distributed Lock Model

Provides advisory locking mechanism for coordinating background jobs
across multiple application instances (Container App replicas).

Uses database-level locking to ensure only one instance runs
a particular job at any given time.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class DistributedLock(Base):
    """
    Distributed lock table for coordinating background jobs.

    Each lock has:
    - lock_name: Unique identifier for the job (e.g., 'poll_rotation')
    - locked_by: Identifier of the instance holding the lock
    - locked_at: When the lock was acquired
    - expires_at: When the lock automatically expires (heartbeat protection)
    - is_locked: Current lock state

    Usage:
    1. Try to acquire lock by updating is_locked=True WHERE is_locked=False
    2. If successful, the job runs
    3. After job completes (or fails), release the lock
    4. Automatic expiry prevents dead locks if instance crashes
    """

    __tablename__ = "distributed_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Lock identifier (e.g., 'poll_rotation', 'poll_generation')
    lock_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Which instance holds the lock (hostname + timestamp or UUID)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # When the lock was acquired
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # When the lock expires (for dead lock prevention)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Current lock state
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional: Last successful run timestamp (for monitoring)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional: Last run result/notes
    last_run_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Version for optimistic locking (prevents race conditions)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Indexes for efficient querying
    __table_args__ = (Index("ix_distributed_locks_name_locked", "lock_name", "is_locked"),)

    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self) -> str:
        return f"<DistributedLock(name={self.lock_name}, locked={self.is_locked}, by={self.locked_by})>"
