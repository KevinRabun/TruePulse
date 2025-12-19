"""
Ad engagement endpoints for tracking ad views/clicks and awarding achievements.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from db.session import get_db
from models.achievement import Achievement, UserAchievement
from models.user import User
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
    db: AsyncSession, user: User, action_type: str, target_count: int
) -> Optional[AchievementUnlocked]:
    """Check if user qualifies for an ad-related achievement and award it."""

    # Find matching achievements
    result = await db.execute(
        select(Achievement).where(
            Achievement.action_type == action_type,
            Achievement.target_count <= target_count,
        )
    )
    achievements = result.scalars().all()

    for achievement in achievements:
        # Check if already earned (for non-repeatable)
        existing_result = await db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == achievement.id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing and existing.is_unlocked and not achievement.is_repeatable:
            continue

        # Check if this is the exact target for this achievement
        if action_type == "ad_view" and user.ad_views == achievement.target_count:
            pass  # Award it
        elif action_type == "ad_click" and user.ad_clicks == achievement.target_count:
            pass  # Award it
        elif (
            action_type == "ad_streak"
            and user.ad_view_streak == achievement.target_count
        ):
            pass  # Award it
        else:
            continue

        # Award the achievement
        now = datetime.now(timezone.utc)
        if not existing:
            user_achievement = UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id,
                is_unlocked=True,
                unlocked_at=now,
                progress=achievement.target_count,
            )
            db.add(user_achievement)
        else:
            existing.is_unlocked = True
            existing.unlocked_at = now
            existing.progress = achievement.target_count

        # Award points
        user.total_points += achievement.points_reward

        await db.commit()

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
    db: AsyncSession = Depends(get_db),
) -> AdEngagementResponse:
    """
    Track an ad engagement event (view or click).

    This helps support TruePulse and can unlock achievements for users
    who help keep the platform free.
    """
    # Get the actual user from database
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    achievement_unlocked = None
    now = datetime.now(timezone.utc)

    if request.event_type == "view":
        user.ad_views += 1

        # Update ad view streak
        if user.last_ad_view_at:
            # Check if this is a new day (within 24-48 hours to maintain streak)
            time_since_last = now - user.last_ad_view_at
            if time_since_last < timedelta(hours=48) and time_since_last >= timedelta(
                hours=12
            ):
                # New day, extend streak
                user.ad_view_streak += 1
            elif time_since_last >= timedelta(hours=48):
                # Streak broken, reset
                user.ad_view_streak = 1
            # If less than 12 hours, same day - don't increment streak
        else:
            user.ad_view_streak = 1

        user.last_ad_view_at = now

        # Check for view achievements
        achievement_unlocked = await check_and_award_ad_achievement(
            db, user, "ad_view", user.ad_views
        )

        # Check for streak achievement if not already unlocked
        if not achievement_unlocked:
            achievement_unlocked = await check_and_award_ad_achievement(
                db, user, "ad_streak", user.ad_view_streak
            )

    elif request.event_type == "click":
        user.ad_clicks += 1

        # Check for click achievements
        achievement_unlocked = await check_and_award_ad_achievement(
            db, user, "ad_click", user.ad_clicks
        )

    await db.commit()

    return AdEngagementResponse(success=True, achievement_unlocked=achievement_unlocked)


@router.get("/stats", response_model=AdEngagementStats)
async def get_ad_engagement_stats(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> AdEngagementStats:
    """
    Get the current user's ad engagement statistics.
    """
    # Get the actual user from database
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count ad-related achievements earned
    ad_achievements_result = await db.execute(
        select(UserAchievement)
        .join(Achievement)
        .where(UserAchievement.user_id == user.id, Achievement.category == "support")
    )
    ad_achievements = ad_achievements_result.scalars().all()

    return AdEngagementStats(
        total_views=user.ad_views or 0,
        total_clicks=user.ad_clicks or 0,
        achievements_from_ads=len(ad_achievements),
    )
