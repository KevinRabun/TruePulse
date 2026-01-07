"""
Cosmos DB Vote repository.

Handles vote storage with privacy-preserving design.
Partition key is poll_id for efficient per-poll queries.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from db.cosmos_session import (
    VOTES_CONTAINER,
    create_item,
    delete_item,
    query_count,
    query_items,
)
from models.cosmos_documents import VoteDocument

logger = logging.getLogger(__name__)


class CosmosVoteRepository:
    """
    Repository for vote operations using Cosmos DB.

    Privacy Design:
    - User ID is NEVER stored with votes
    - vote_hash = hash(user_id + poll_id + secret) ensures one vote per user per poll
    - Demographics are optional and anonymized
    """

    # ========================================================================
    # Read Operations
    # ========================================================================

    async def get_by_hash(self, vote_hash: str, poll_id: str) -> Optional[VoteDocument]:
        """
        Get a vote by its privacy-preserving hash.

        Note: Requires poll_id as partition key for efficient lookup.
        """
        # Query within the poll partition
        query = """
            SELECT * FROM c
            WHERE c.vote_hash = @vote_hash
              AND c.poll_id = @poll_id
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[
                {"name": "@vote_hash", "value": vote_hash},
                {"name": "@poll_id", "value": poll_id},
            ],
            partition_key=poll_id,
            max_items=1,
        )
        if not results:
            return None
        return VoteDocument(**results[0])

    async def exists_by_hash(self, vote_hash: str, poll_id: str) -> bool:
        """Check if a vote exists by hash (for duplicate detection)."""
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.vote_hash = @vote_hash
              AND c.poll_id = @poll_id
        """
        count = await query_count(
            VOTES_CONTAINER,
            query,
            parameters=[
                {"name": "@vote_hash", "value": vote_hash},
                {"name": "@poll_id", "value": poll_id},
            ],
            partition_key=poll_id,
        )
        return count > 0

    async def find_vote_for_poll(self, vote_hash: str, poll_id: str) -> Optional[VoteDocument]:
        """
        Find a user's vote for a specific poll.

        This is the main method for checking if a user has already voted.
        """
        return await self.get_by_hash(vote_hash, poll_id)

    # ========================================================================
    # Write Operations
    # ========================================================================

    async def create(
        self,
        vote_hash: str,
        poll_id: str,
        choice_id: str,
        demographics_bucket: Optional[str] = None,
    ) -> VoteDocument:
        """
        Create a vote record.

        NOTE: user_id is NEVER stored - only the privacy-preserving hash.
        """
        vote_id = str(uuid4())
        now = datetime.now(timezone.utc)

        vote = VoteDocument(
            id=vote_id,
            vote_hash=vote_hash,
            poll_id=poll_id,
            choice_id=choice_id,
            demographics_bucket=demographics_bucket,
            voted_at=now,
        )

        await create_item(VOTES_CONTAINER, vote.model_dump(mode="json"))
        logger.debug(f"Created vote for poll {poll_id}")
        return vote

    async def delete_by_hash(self, vote_hash: str, poll_id: str) -> Optional[VoteDocument]:
        """Delete a vote by hash and return the deleted vote (for retraction)."""
        vote = await self.get_by_hash(vote_hash, poll_id)
        if vote:
            await delete_item(VOTES_CONTAINER, vote.id, partition_key=poll_id)
            logger.debug(f"Deleted vote for poll {poll_id}")
        return vote

    # ========================================================================
    # Query Operations
    # ========================================================================

    async def count_by_poll(self, poll_id: str) -> int:
        """Get total vote count for a poll (efficient partition query)."""
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.poll_id = @poll_id
        """
        return await query_count(
            VOTES_CONTAINER,
            query,
            parameters=[{"name": "@poll_id", "value": poll_id}],
            partition_key=poll_id,
        )

    async def count_by_choice(self, poll_id: str, choice_id: str) -> int:
        """Get vote count for a specific choice within a poll."""
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.poll_id = @poll_id
              AND c.choice_id = @choice_id
        """
        return await query_count(
            VOTES_CONTAINER,
            query,
            parameters=[
                {"name": "@poll_id", "value": poll_id},
                {"name": "@choice_id", "value": choice_id},
            ],
            partition_key=poll_id,
        )

    async def get_choice_counts(self, poll_id: str) -> dict[str, int]:
        """Get vote counts for all choices in a poll."""
        query = """
            SELECT c.choice_id, COUNT(1) as count FROM c
            WHERE c.poll_id = @poll_id
            GROUP BY c.choice_id
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[{"name": "@poll_id", "value": poll_id}],
            partition_key=poll_id,
        )

        counts: dict[str, int] = {}
        for row in results:
            counts[row["choice_id"]] = int(row["count"])  # type: ignore[arg-type]
        return counts

    async def get_demographic_breakdown(self, poll_id: str) -> dict[str, dict[str, int]]:
        """
        Get vote breakdown by demographics bucket.

        Returns: {"age_25-34_country_US": {"choice_1": 45, "choice_2": 55}, ...}
        """
        query = """
            SELECT c.demographics_bucket, c.choice_id, COUNT(1) as count FROM c
            WHERE c.poll_id = @poll_id
              AND IS_DEFINED(c.demographics_bucket)
              AND c.demographics_bucket != null
            GROUP BY c.demographics_bucket, c.choice_id
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[{"name": "@poll_id", "value": poll_id}],
            partition_key=poll_id,
        )

        breakdown: dict[str, dict[str, int]] = {}
        for row in results:
            bucket = row["demographics_bucket"]
            choice = row["choice_id"]
            count = row["count"]

            if bucket not in breakdown:
                breakdown[bucket] = {}
            breakdown[bucket][choice] = count

        return breakdown

    async def get_votes_for_poll(
        self,
        poll_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[VoteDocument]:
        """
        Get all votes for a poll (for analysis/export).

        Note: Returns anonymized data only.
        """
        query = """
            SELECT * FROM c
            WHERE c.poll_id = @poll_id
            ORDER BY c.voted_at DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[
                {"name": "@poll_id", "value": poll_id},
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ],
            partition_key=poll_id,
        )
        return [VoteDocument(**r) for r in results]

    async def get_recent_votes(
        self,
        poll_id: str,
        since: datetime,
    ) -> list[VoteDocument]:
        """Get votes cast since a specific time (for real-time updates)."""
        query = """
            SELECT * FROM c
            WHERE c.poll_id = @poll_id
              AND c.voted_at >= @since
            ORDER BY c.voted_at DESC
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[
                {"name": "@poll_id", "value": poll_id},
                {"name": "@since", "value": since.isoformat()},
            ],
            partition_key=poll_id,
        )
        return [VoteDocument(**r) for r in results]

    # ========================================================================
    # Analytics Operations
    # ========================================================================

    async def get_vote_timeline(
        self,
        poll_id: str,
        interval_minutes: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get vote timeline showing votes over time.

        Note: Cosmos DB doesn't have built-in time bucketing,
        so we fetch votes and bucket them in Python.
        """
        query = """
            SELECT c.voted_at, c.choice_id FROM c
            WHERE c.poll_id = @poll_id
            ORDER BY c.voted_at ASC
        """
        results = await query_items(
            VOTES_CONTAINER,
            query,
            parameters=[{"name": "@poll_id", "value": poll_id}],
            partition_key=poll_id,
        )

        if not results:
            return []

        # Bucket votes by time interval

        timeline: list[dict[str, Any]] = []
        current_bucket_start: Optional[datetime] = None
        current_bucket: dict[str, int] = {}

        for row in results:
            # Parse voted_at (could be string or datetime)
            voted_at = row["voted_at"]
            if isinstance(voted_at, str):
                voted_at = datetime.fromisoformat(voted_at.replace("Z", "+00:00"))

            # Determine bucket
            bucket_start = voted_at.replace(
                minute=(voted_at.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0,
            )

            if current_bucket_start != bucket_start:
                # Save previous bucket
                if current_bucket_start is not None:
                    timeline.append(
                        {
                            "timestamp": current_bucket_start.isoformat(),
                            "votes": current_bucket,
                        }
                    )

                # Start new bucket
                current_bucket_start = bucket_start
                current_bucket = {}

            # Add to current bucket
            choice_id = row["choice_id"]
            current_bucket[choice_id] = current_bucket.get(choice_id, 0) + 1

        # Don't forget the last bucket
        if current_bucket_start is not None:
            timeline.append(
                {
                    "timestamp": current_bucket_start.isoformat(),
                    "votes": current_bucket,
                }
            )

        return timeline

    async def get_total_votes_across_all_polls(self) -> int:
        """
        Get total vote count across all polls.

        Note: This is a cross-partition query - use sparingly.
        Consider caching this value.
        """
        query = "SELECT VALUE COUNT(1) FROM c"
        return await query_count(VOTES_CONTAINER, query)

    async def count_total_votes(self) -> int:
        """
        Count total votes across all polls.

        Alias for get_total_votes_across_all_polls for stats service compatibility.
        """
        return await self.get_total_votes_across_all_polls()
