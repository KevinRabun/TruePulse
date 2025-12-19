"""
Vote repository for database operations.

Implements privacy-preserving vote storage.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.vote import Vote


class VoteRepository:
    """Repository for vote database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_hash(self, vote_hash: str) -> Optional[Vote]:
        """Get a vote by its privacy-preserving hash."""
        result = await self.db.execute(select(Vote).where(Vote.vote_hash == vote_hash))
        return result.scalar_one_or_none()

    async def exists_by_hash(self, vote_hash: str) -> bool:
        """Check if a vote exists by hash (for duplicate detection)."""
        result = await self.db.execute(
            select(func.count(Vote.id)).where(Vote.vote_hash == vote_hash)
        )
        count = result.scalar() or 0
        return count > 0

    async def create(
        self,
        vote_hash: str,
        poll_id: str,
        choice_id: str,
        demographics_bucket: Optional[str] = None,
    ) -> Vote:
        """
        Create a vote record.

        NOTE: user_id is NEVER stored - only the hash.
        """
        vote = Vote(
            id=str(uuid4()),
            vote_hash=vote_hash,
            poll_id=poll_id,
            choice_id=choice_id,
            demographics_bucket=demographics_bucket,
        )

        self.db.add(vote)
        await self.db.flush()
        await self.db.refresh(vote)

        return vote

    async def delete_by_hash(self, vote_hash: str) -> Optional[Vote]:
        """Delete a vote by hash and return the deleted vote (for retraction)."""
        # First get the vote to return choice_id for decrementing
        vote = await self.get_by_hash(vote_hash)
        if vote:
            await self.db.execute(delete(Vote).where(Vote.vote_hash == vote_hash))
        return vote

    async def count_by_poll(self, poll_id: str) -> int:
        """Get total vote count for a poll."""
        result = await self.db.execute(
            select(func.count(Vote.id)).where(Vote.poll_id == poll_id)
        )
        return result.scalar() or 0

    async def count_by_choice(self, choice_id: str) -> int:
        """Get vote count for a specific choice."""
        result = await self.db.execute(
            select(func.count(Vote.id)).where(Vote.choice_id == choice_id)
        )
        return result.scalar() or 0

    async def get_demographic_breakdown(
        self, poll_id: str
    ) -> dict[str, dict[str, int]]:
        """
        Get vote breakdown by demographics bucket.

        Returns: {"age_25-34_country_US": {"choice_1": 45, "choice_2": 55}, ...}
        """
        result = await self.db.execute(
            select(
                Vote.demographics_bucket,
                Vote.choice_id,
                func.count(Vote.id).label("count"),
            )
            .where(
                and_(
                    Vote.poll_id == poll_id,
                    Vote.demographics_bucket.isnot(None),
                )
            )
            .group_by(Vote.demographics_bucket, Vote.choice_id)
        )

        breakdown: dict[str, dict[str, int]] = {}
        for row in result.all():
            bucket = (
                str(row.demographics_bucket) if row.demographics_bucket else "unknown"
            )
            if bucket not in breakdown:
                breakdown[bucket] = {}
            count_val: int = row[2]  # Access count by index
            breakdown[bucket][str(row.choice_id)] = count_val

        return breakdown

    async def get_votes_in_period(
        self,
        poll_id: str,
        start: datetime,
        end: datetime,
    ) -> int:
        """Get vote count in a specific time period."""
        result = await self.db.execute(
            select(func.count(Vote.id)).where(
                and_(
                    Vote.poll_id == poll_id,
                    Vote.created_at >= start,
                    Vote.created_at < end,
                )
            )
        )
        return result.scalar() or 0
