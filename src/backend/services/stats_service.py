"""
Platform statistics service with configurable caching.

Computes and caches platform-wide statistics (polls, votes, active users)
to avoid expensive database queries on every request.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from dataclasses import dataclass

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.poll import Poll, PollStatus
from models.vote import Vote
from models.user import User


@dataclass
class PlatformStats:
    """Platform statistics data."""
    polls_created: int
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
    
    # In-memory cache (for single instance deployments)
    # For production with multiple instances, use Redis
    _cache: Optional[PlatformStats] = None
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[Any] = None,
        cache_ttl_hours: int = 24,
    ):
        """
        Initialize stats service.
        
        Args:
            db: Database session
            redis_client: Optional Redis client for distributed caching
            cache_ttl_hours: How long to cache stats (default: 24 hours)
        """
        self.db = db
        self.redis_client = redis_client
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
        """Compute fresh statistics from database."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Count published polls (active, closed, or archived - excludes scheduled)
        polls_result = await self.db.execute(
            select(func.count(Poll.id)).where(
                Poll.status.in_([
                    PollStatus.ACTIVE.value,
                    PollStatus.CLOSED.value,
                    PollStatus.ARCHIVED.value,
                ])
            )
        )
        polls_created = polls_result.scalar() or 0
        
        # Count total votes
        votes_result = await self.db.execute(
            select(func.count(Vote.id))
        )
        votes_cast = votes_result.scalar() or 0
        
        # Count active users (logged in within last 30 days)
        active_users_result = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.last_login_at >= thirty_days_ago,
                    User.is_active == True,  # noqa: E712
                )
            )
        )
        active_users = active_users_result.scalar() or 0
        
        # Count total registered users
        total_users_result = await self.db.execute(
            select(func.count(User.id)).where(
                User.is_active == True  # noqa: E712
            )
        )
        total_users = total_users_result.scalar() or 0
        
        # Count unique countries from users who shared demographics
        countries_result = await self.db.execute(
            select(func.count(func.distinct(User.country))).where(
                and_(
                    User.is_active == True,  # noqa: E712
                    User.country.isnot(None),
                    User.share_anonymous_demographics == True,  # noqa: E712
                )
            )
        )
        countries_represented = countries_result.scalar() or 0
        
        return PlatformStats(
            polls_created=polls_created,
            votes_cast=votes_cast,
            active_users=active_users,
            total_users=total_users,
            countries_represented=countries_represented,
            computed_at=now,
            cache_ttl_hours=self.cache_ttl_hours,
        )
    
    async def _get_cached_stats(self) -> Optional[PlatformStats]:
        """Get stats from cache (Redis or in-memory)."""
        # Try Redis first if available
        if self.redis_client:
            try:
                cached_json = await self.redis_client.get(self.cache_key)
                if cached_json:
                    data = json.loads(cached_json)
                    return PlatformStats.from_dict(data)
            except Exception:
                # Redis error, fall back to in-memory
                pass
        
        # Fall back to in-memory cache
        if StatsService._cache and not StatsService._cache.is_stale():
            return StatsService._cache
        
        return None
    
    async def _cache_stats(self, stats: PlatformStats) -> None:
        """Cache stats in Redis and/or in-memory."""
        # Update in-memory cache
        StatsService._cache = stats
        
        # Also store in Redis if available
        if self.redis_client:
            try:
                stats_json = json.dumps(stats.to_dict())
                # Set with TTL slightly longer than our cache_ttl
                ttl_seconds = (self.cache_ttl_hours + 1) * 3600
                await self.redis_client.setex(
                    self.cache_key,
                    ttl_seconds,
                    stats_json,
                )
            except Exception:
                # Redis error, in-memory cache is still valid
                pass
    
    async def invalidate_cache(self) -> None:
        """Invalidate cached stats (call when data changes significantly)."""
        StatsService._cache = None
        
        if self.redis_client:
            try:
                await self.redis_client.delete(self.cache_key)
            except Exception:
                pass


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
