"""
Platform statistics API endpoint.

Provides public platform statistics (polls created, votes cast, active users)
with configurable caching to minimize database load.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.config import settings
from models.cosmos_documents import PollStatus
from repositories.cosmos_poll_repository import CosmosPollRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.cosmos_vote_repository import CosmosVoteRepository
from services.stats_service import format_stat_value

router = APIRouter()


# =============================================================================
# Repository Dependencies
# =============================================================================


def get_user_repository() -> CosmosUserRepository:
    """Get the Cosmos DB user repository instance."""
    return CosmosUserRepository()


def get_poll_repository() -> CosmosPollRepository:
    """Get the Cosmos DB poll repository instance."""
    return CosmosPollRepository()


def get_vote_repository() -> CosmosVoteRepository:
    """Get the Cosmos DB vote repository instance."""
    return CosmosVoteRepository()


# =============================================================================
# Response Models
# =============================================================================


class FormattedStats(BaseModel):
    """Formatted statistics for display."""

    polls_created: str
    polls_created_raw: int
    completed_polls: str
    completed_polls_raw: int
    votes_cast: str
    votes_cast_raw: int
    active_users: str
    active_users_raw: int
    total_users: str
    total_users_raw: int
    countries_represented: str
    countries_represented_raw: int

    class Config:
        json_schema_extra = {
            "example": {
                "polls_created": "12.5K",
                "polls_created_raw": 12453,
                "completed_polls": "10.2K",
                "completed_polls_raw": 10200,
                "votes_cast": "2.4M",
                "votes_cast_raw": 2400000,
                "active_users": "89K",
                "active_users_raw": 89000,
                "total_users": "150K",
                "total_users_raw": 150000,
                "countries_represented": "142",
                "countries_represented_raw": 142,
            }
        }


class PlatformStatsResponse(BaseModel):
    """Full platform statistics response."""

    stats: FormattedStats
    computed_at: datetime
    cache_ttl_hours: int
    next_refresh_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "stats": {
                    "polls_created": "12.5K",
                    "polls_created_raw": 12453,
                    "completed_polls": "10.2K",
                    "completed_polls_raw": 10200,
                    "votes_cast": "2.4M",
                    "votes_cast_raw": 2400000,
                    "active_users": "89K",
                    "active_users_raw": 89000,
                    "total_users": "150K",
                    "total_users_raw": 150000,
                    "countries_represented": "142",
                    "countries_represented_raw": 142,
                },
                "computed_at": "2025-12-18T10:00:00Z",
                "cache_ttl_hours": 24,
                "next_refresh_at": "2025-12-19T10:00:00Z",
            }
        }


# Default cache TTL in hours (configurable via environment)
DEFAULT_CACHE_TTL_HOURS = getattr(settings, "STATS_CACHE_TTL_HOURS", 24)


# =============================================================================
# Simple In-Memory Cache
# =============================================================================


class _StatsCache:
    """Simple in-memory cache for platform statistics."""

    def __init__(self) -> None:
        self._cached_stats: Optional[dict] = None
        self._computed_at: Optional[datetime] = None
        self._ttl_hours: int = DEFAULT_CACHE_TTL_HOURS

    def is_valid(self) -> bool:
        """Check if cache is valid and not stale."""
        if self._cached_stats is None or self._computed_at is None:
            return False
        expiry = self._computed_at + timedelta(hours=self._ttl_hours)
        return datetime.now(timezone.utc) <= expiry

    def get(self) -> tuple[dict, datetime] | None:
        """Get cached stats if valid."""
        if self.is_valid() and self._cached_stats is not None and self._computed_at is not None:
            return self._cached_stats, self._computed_at
        return None

    def set(self, stats: dict, computed_at: datetime) -> None:
        """Cache the stats."""
        self._cached_stats = stats
        self._computed_at = computed_at

    def invalidate(self) -> None:
        """Invalidate the cache."""
        self._cached_stats = None
        self._computed_at = None


_stats_cache = _StatsCache()


@router.get(
    "/",
    response_model=PlatformStatsResponse,
    summary="Get platform statistics",
    description="""
    Returns platform-wide statistics including polls created, votes cast,
    and active users. Statistics are cached and refreshed periodically
    (default: every 24 hours) to minimize database load.

    **No authentication required** - these are public statistics.

    ### Response includes:
    - **stats**: Formatted values for display (e.g., "2.4M") and raw numbers
    - **computed_at**: When the statistics were last computed
    - **cache_ttl_hours**: How long stats are cached before refresh
    - **next_refresh_at**: When stats will be recomputed
    """,
)
async def get_platform_stats(
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    poll_repo: CosmosPollRepository = Depends(get_poll_repository),
    vote_repo: CosmosVoteRepository = Depends(get_vote_repository),
    refresh: bool = Query(
        False,
        description="Force refresh stats (admin use only, respects rate limits)",
    ),
) -> PlatformStatsResponse:
    """
    Get platform statistics.

    Returns cached statistics to minimize database load.
    Stats are automatically refreshed based on cache_ttl_hours setting.
    """
    # Check cache first
    if not refresh:
        cached = _stats_cache.get()
        if cached:
            stats_dict, computed_at = cached
            next_refresh = computed_at + timedelta(hours=DEFAULT_CACHE_TTL_HOURS)
            return PlatformStatsResponse(
                stats=FormattedStats(**stats_dict),
                computed_at=computed_at,
                cache_ttl_hours=DEFAULT_CACHE_TTL_HOURS,
                next_refresh_at=next_refresh,
            )

    # Compute fresh stats using Cosmos repositories
    now = datetime.now(timezone.utc)

    # Count polls by status using repository
    active_polls = await poll_repo.count_polls_by_status(PollStatus.ACTIVE)
    closed_polls = await poll_repo.count_polls_by_status(PollStatus.CLOSED)
    archived_polls = await poll_repo.count_polls_by_status(PollStatus.ARCHIVED)
    polls_created = active_polls + closed_polls + archived_polls
    completed_polls = closed_polls + archived_polls

    # Count total votes using repository
    votes_cast = await vote_repo.get_total_votes_across_all_polls()

    # Count active users using repository
    active_users = await user_repo.count_active_users()

    # Count total users and unique countries
    total_users = active_users  # TODO: Add count_total_users() to CosmosUserRepository
    countries_represented = await user_repo.count_unique_countries()

    # Build formatted stats
    formatted = FormattedStats(
        polls_created=format_stat_value(polls_created),
        polls_created_raw=polls_created,
        completed_polls=format_stat_value(completed_polls),
        completed_polls_raw=completed_polls,
        votes_cast=format_stat_value(votes_cast),
        votes_cast_raw=votes_cast,
        active_users=format_stat_value(active_users),
        active_users_raw=active_users,
        total_users=format_stat_value(total_users),
        total_users_raw=total_users,
        countries_represented=str(countries_represented),
        countries_represented_raw=countries_represented,
    )

    # Cache the stats
    stats_dict = {
        "polls_created": formatted.polls_created,
        "polls_created_raw": formatted.polls_created_raw,
        "completed_polls": formatted.completed_polls,
        "completed_polls_raw": formatted.completed_polls_raw,
        "votes_cast": formatted.votes_cast,
        "votes_cast_raw": formatted.votes_cast_raw,
        "active_users": formatted.active_users,
        "active_users_raw": formatted.active_users_raw,
        "total_users": formatted.total_users,
        "total_users_raw": formatted.total_users_raw,
        "countries_represented": formatted.countries_represented,
        "countries_represented_raw": formatted.countries_represented_raw,
    }
    _stats_cache.set(stats_dict, now)

    next_refresh = now + timedelta(hours=DEFAULT_CACHE_TTL_HOURS)

    return PlatformStatsResponse(
        stats=formatted,
        computed_at=now,
        cache_ttl_hours=DEFAULT_CACHE_TTL_HOURS,
        next_refresh_at=next_refresh,
    )
