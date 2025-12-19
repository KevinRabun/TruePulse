"""
Platform statistics API endpoint.

Provides public platform statistics (polls created, votes cast, active users)
with configurable caching to minimize database load.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.stats_service import StatsService, format_stat_value
from services.redis_service import get_redis_service, RedisService
from core.config import settings


router = APIRouter()


class FormattedStats(BaseModel):
    """Formatted statistics for display."""
    polls_created: str
    polls_created_raw: int
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
DEFAULT_CACHE_TTL_HOURS = getattr(settings, 'STATS_CACHE_TTL_HOURS', 24)


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
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_service),
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
    # Create stats service with configurable TTL and Redis client
    # Note: RedisService now uses Azure Tables but maintains same interface
    stats_service = StatsService(
        db=db,
        redis_client=redis if redis.is_available else None,
        cache_ttl_hours=DEFAULT_CACHE_TTL_HOURS,
    )
    
    # Get stats (cached or fresh)
    stats = await stats_service.get_stats(force_refresh=refresh)
    
    # Calculate next refresh time
    from datetime import timedelta
    next_refresh = stats.computed_at + timedelta(hours=stats.cache_ttl_hours)
    
    # Format for display
    formatted = FormattedStats(
        polls_created=format_stat_value(stats.polls_created),
        polls_created_raw=stats.polls_created,
        votes_cast=format_stat_value(stats.votes_cast),
        votes_cast_raw=stats.votes_cast,
        active_users=format_stat_value(stats.active_users),
        active_users_raw=stats.active_users,
        total_users=format_stat_value(stats.total_users),
        total_users_raw=stats.total_users,
        countries_represented=str(stats.countries_represented),
        countries_represented_raw=stats.countries_represented,
    )
    
    return PlatformStatsResponse(
        stats=formatted,
        computed_at=stats.computed_at,
        cache_ttl_hours=stats.cache_ttl_hours,
        next_refresh_at=next_refresh,
    )
