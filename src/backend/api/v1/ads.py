"""
Ad engagement endpoints for tracking ad views/clicks and awarding achievements.

Migrated to Cosmos DB.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_current_active_user, get_user_repository
from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.provider import get_achievement_repository
from schemas.user import UserInDB

router = APIRouter()


class AdEngagementRequest(BaseModel):
    """Request to track an ad engagement event."""

    event_type: str  # "view" or "click"
    ad_type: str  # "banner", "native", "interstitial", etc.
    placement: str  # "footer", "polls-grid", "fullscreen", etc.


class AchievementUnlocked(BaseModel):
    """Achievement that was unlocked."""

    id: str
    name: str
    description: str
    points_reward: int


class AdEngagementResponse(BaseModel):
    """Response from tracking ad engagement."""

    success: bool
    achievement_unlocked: Optional[AchievementUnlocked] = None


class AdEngagementStats(BaseModel):
    """User's ad engagement statistics."""

    total_views: int
    total_clicks: int
    achievements_from_ads: int


async def check_and_award_ad_achievement(
    achievement_repo: CosmosAchievementRepository,
    user_id: str,
    action_type: str,
    target_count: int,
) -> Optional[AchievementUnlocked]:
    """Check if user qualifies for an ad-related achievement and award it."""
    # Query achievements matching the action type and target
    achievements = await achievement_repo.get_achievements_by_action_type(action_type)

    for achievement in achievements:
        # Check if this is the exact target for this achievement
        if achievement.target_count != target_count:
            continue

        # Check if already unlocked
        existing = await achievement_repo.get_user_achievement(user_id, achievement.id)
        if existing and existing.is_unlocked and not achievement.is_repeatable:
            continue

        # Unlock the achievement
        await achievement_repo.unlock_achievement(user_id, achievement.id)

        # Record points if any
        if achievement.points_reward > 0:
            await achievement_repo.record_points_transaction(
                user_id=user_id,
                action="achievement",
                points=achievement.points_reward,
                description=f"Unlocked: {achievement.name}",
                reference_type="achievement",
                reference_id=achievement.id,
            )

        return AchievementUnlocked(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            points_reward=achievement.points_reward,
        )

    return None


@router.post("/engagement", response_model=AdEngagementResponse)
async def track_ad_engagement(
    request: AdEngagementRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: Annotated[CosmosUserRepository, Depends(get_user_repository)],
    achievement_repo: Annotated[CosmosAchievementRepository, Depends(get_achievement_repository)],
) -> AdEngagementResponse:
    """
    Track an ad engagement event (view or click).

    This helps support TruePulse and can unlock achievements for users
    who help keep the platform free.
    """
    # Get the user from Cosmos DB
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    achievement_unlocked = None

    if request.event_type == "view":
        # Record ad view (handles streak logic internally)
        await user_repo.record_ad_view(current_user.id)

        # Refresh user to get updated counts
        user = await user_repo.get_by_id(current_user.id)
        if user:
            # Check for view achievements
            achievement_unlocked = await check_and_award_ad_achievement(
                achievement_repo, current_user.id, "ad_view", user.ad_views
            )

            # Check for streak achievement if not already unlocked
            if not achievement_unlocked:
                achievement_unlocked = await check_and_award_ad_achievement(
                    achievement_repo, current_user.id, "ad_streak", user.ad_view_streak
                )

    elif request.event_type == "click":
        # Record ad click
        await user_repo.record_ad_click(current_user.id)

        # Refresh user to get updated counts
        user = await user_repo.get_by_id(current_user.id)
        if user:
            # Check for click achievements
            achievement_unlocked = await check_and_award_ad_achievement(
                achievement_repo, current_user.id, "ad_click", user.ad_clicks
            )

    return AdEngagementResponse(success=True, achievement_unlocked=achievement_unlocked)


@router.get("/stats", response_model=AdEngagementStats)
async def get_ad_engagement_stats(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: Annotated[CosmosUserRepository, Depends(get_user_repository)],
    achievement_repo: Annotated[CosmosAchievementRepository, Depends(get_achievement_repository)],
) -> AdEngagementStats:
    """
    Get the current user's ad engagement statistics.
    """
    # Get the user from Cosmos DB
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count ad-related achievements earned (support category)
    user_achievements = await achievement_repo.get_user_achievements(current_user.id)
    ad_achievement_count = 0

    for ua in user_achievements:
        if ua.is_unlocked:
            achievement = await achievement_repo.get_achievement(ua.achievement_id)
            if achievement and achievement.category == "support":
                ad_achievement_count += 1

    return AdEngagementStats(
        total_views=user.ad_views or 0,
        total_clicks=user.ad_clicks or 0,
        achievements_from_ads=ad_achievement_count,
    )
