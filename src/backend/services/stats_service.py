"""
Platform statistics service with configurable caching.

Computes and caches platform-wide statistics (polls, votes, active users)
to avoid expensive database queries on every request.
Now uses Cosmos DB repositories.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from repositories.cosmos_poll_repository import CosmosPollRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.cosmos_vote_repository import CosmosVoteRepository


@dataclass
class PlatformStats:
    """Platform statistics data."""

    polls_created: int
    completed_polls: int  # Closed/archived pulse and flash polls
    votes_cast: int
    active_users: int  # Users active in last 30 days
    total_users: int
    countries_represented: int  # Unique countries from user demographics
    computed_at: datetime
    cache_ttl_hours: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "polls_created": self.polls_created,
            "completed_polls": self.completed_polls,
            "votes_cast": self.votes_cast,
            "active_users": self.active_users,
            "total_users": self.total_users,
            "countries_represented": self.countries_represented,
            "computed_at": self.computed_at.isoformat(),
            "cache_ttl_hours": self.cache_ttl_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlatformStats":
        """Create from dictionary."""
        return cls(
            polls_created=data["polls_created"],
            completed_polls=data.get("completed_polls", 0),
            votes_cast=data["votes_cast"],
            active_users=data["active_users"],
            total_users=data["total_users"],
            countries_represented=data.get("countries_represented", 0),
            computed_at=datetime.fromisoformat(data["computed_at"]),
            cache_ttl_hours=data["cache_ttl_hours"],
        )

    def is_stale(self) -> bool:
        """Check if cached stats are stale and need recomputing."""
        expiry = self.computed_at + timedelta(hours=self.cache_ttl_hours)
        return datetime.now(timezone.utc) > expiry


class StatsService:
    """Service for computing and caching platform statistics."""

    # In-memory cache (sufficient for Container Apps with single replica in dev)
    # For multi-replica production, stats are recomputed per-replica which is acceptable
    # since they're read-only aggregations and the cache TTL ensures consistency
    _cache: Optional[PlatformStats] = None

    def __init__(
        self,
        cache_ttl_hours: int = 1,
    ):
        """
        Initialize stats service.

        Args:
            cache_ttl_hours: How long to cache stats (default: 1 hour)
        """
        self.poll_repo = CosmosPollRepository()
        self.user_repo = CosmosUserRepository()
        self.vote_repo = CosmosVoteRepository()
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_key = "platform:stats:v1"

    async def get_stats(self, force_refresh: bool = False) -> PlatformStats:
        """
        Get platform statistics, using cache if available and fresh.

        Args:
            force_refresh: If True, bypass cache and recompute stats

        Returns:
            PlatformStats with current platform metrics
        """
        if not force_refresh:
            cached = await self._get_cached_stats()
            if cached and not cached.is_stale():
                return cached

        # Compute fresh stats
        stats = await self._compute_stats()

        # Cache the results
        await self._cache_stats(stats)

        return stats

    async def _compute_stats(self) -> PlatformStats:
        """Compute fresh statistics from Cosmos DB."""
        now = datetime.now(timezone.utc)

        # Count published polls using repository method
        polls_created = await self.poll_repo.count_published_polls()

        # Count completed pulse and flash polls
        completed_polls = await self.poll_repo.count_completed_polls()

        # Count total votes
        votes_cast = await self.vote_repo.count_total_votes()

        # Count active users (logged in within last 30 days)
        active_users = await self.user_repo.count_active_users_since(days=30)

        # Count total registered users
        total_users = await self.user_repo.count_active_users()

        # Count unique countries from users who shared demographics
        countries_represented = await self.user_repo.count_unique_countries()

        return PlatformStats(
            polls_created=polls_created,
            completed_polls=completed_polls,
            votes_cast=votes_cast,
            active_users=active_users,
            total_users=total_users,
            countries_represented=countries_represented,
            computed_at=now,
            cache_ttl_hours=self.cache_ttl_hours,
        )

    async def _get_cached_stats(self) -> Optional[PlatformStats]:
        """Get stats from in-memory cache."""
        # Use in-memory cache (sufficient for Container Apps)
        if StatsService._cache and not StatsService._cache.is_stale():
            return StatsService._cache

        return None

    async def _cache_stats(self, stats: PlatformStats) -> None:
        """Cache stats in memory."""
        # Update in-memory cache
        StatsService._cache = stats

    async def invalidate_cache(self) -> None:
        """Invalidate cached stats (call when data changes significantly)."""
        StatsService._cache = None


def format_stat_value(value: int) -> str:
    """
    Format a statistic value for display (e.g., 1234567 -> "1.2M").

    Args:
        value: Raw numeric value

    Returns:
        Formatted string for display
    """
    if value >= 1_000_000:
        formatted = value / 1_000_000
        if formatted >= 10:
            return f"{formatted:.0f}M"
        return f"{formatted:.1f}M"
    elif value >= 1_000:
        formatted = value / 1_000
        if formatted >= 10:
            return f"{formatted:.0f}K"
        return f"{formatted:.1f}K"
    else:
        return f"{value:,}"
