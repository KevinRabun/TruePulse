"""
Community achievements API endpoints.

Community achievements are collective goals where all participants
earn rewards when the community reaches a target together.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_user_optional, get_current_verified_user
from db.session import get_db
from models.achievement import (
    CommunityAchievement,
    CommunityAchievementEvent,
    CommunityAchievementParticipant,
)
from models.user import User
from schemas.user import UserInDB

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class CommunityAchievementSchema(BaseModel):
    """Schema for community achievement response."""

    id: str
    name: str
    description: str
    icon: str
    badge_icon: str
    goal_type: str
    target_count: int
    time_window_hours: Optional[int] = None
    points_reward: int
    bonus_multiplier: float
    is_recurring: bool
    cooldown_hours: Optional[int] = None
    tier: str
    category: str
    is_active: bool

    model_config = {"from_attributes": True}


class CommunityAchievementProgress(BaseModel):
    """Schema for community achievement with progress."""

    achievement: CommunityAchievementSchema
    current_count: int = 0
    progress_percentage: float = 0.0
    participant_count: int = 0
    time_remaining_hours: Optional[float] = None
    started_at: Optional[datetime] = None
    user_participated: bool = False
    user_contribution: int = 0


class CommunityAchievementEventSchema(BaseModel):
    """Schema for a completed community achievement event."""

    id: str
    achievement_id: str
    achievement_name: str
    achievement_icon: str
    badge_icon: str
    triggered_at: datetime
    completed_at: Optional[datetime] = None
    final_count: int
    participant_count: int
    points_reward: int
    user_earned_badge: bool = False
    user_earned_points: int = 0


class CommunityLeaderboard(BaseModel):
    """Schema for community contribution leaderboard."""

    user_id: str
    display_name: str
    avatar_url: Optional[str]
    total_contributions: int
    achievements_participated: int
    badges_earned: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/active", response_model=list[CommunityAchievementProgress])
async def get_active_community_achievements(
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[CommunityAchievementProgress]:
    """
    Get all active community achievements with current progress.

    Shows the collective goals that the community is working towards,
    along with current progress and participant counts.
    """
    # Get active community achievements
    result = await db.execute(
        select(CommunityAchievement)
        .where(CommunityAchievement.is_active == True)
        .order_by(CommunityAchievement.sort_order.asc())
    )
    achievements = result.scalars().all()

    progress_list = []
    now = datetime.now(timezone.utc)

    for ach in achievements:
        # Get the latest event for this achievement (if any)
        event_result = await db.execute(
            select(CommunityAchievementEvent)
            .where(
                and_(
                    CommunityAchievementEvent.achievement_id == ach.id,
                    CommunityAchievementEvent.is_completed == False,
                )
            )
            .order_by(CommunityAchievementEvent.triggered_at.desc())
            .limit(1)
        )
        event = event_result.scalar_one_or_none()

        # Calculate progress
        current_count = 0
        participant_count = 0
        started_at = None
        time_remaining = None
        user_participated = False
        user_contribution = 0

        if event:
            current_count = event.final_count
            participant_count = event.participant_count
            started_at = event.triggered_at

            # Calculate time remaining if there's a window
            if ach.time_window_hours:
                end_time = event.triggered_at.replace(tzinfo=timezone.utc) + timedelta(hours=ach.time_window_hours)
                remaining = (end_time - now).total_seconds() / 3600
                time_remaining = max(0, remaining)

            # Check if current user participated
            if current_user:
                part_result = await db.execute(
                    select(CommunityAchievementParticipant).where(
                        and_(
                            CommunityAchievementParticipant.event_id == event.id,
                            CommunityAchievementParticipant.user_id == current_user.id,
                        )
                    )
                )
                participant = part_result.scalar_one_or_none()
                if participant:
                    user_participated = True
                    user_contribution = participant.contribution_count

        progress_list.append(
            CommunityAchievementProgress(
                achievement=CommunityAchievementSchema.model_validate(ach),
                current_count=current_count,
                progress_percentage=min(100, (current_count / ach.target_count * 100)) if ach.target_count > 0 else 0,
                participant_count=participant_count,
                time_remaining_hours=time_remaining,
                started_at=started_at,
                user_participated=user_participated,
                user_contribution=user_contribution,
            )
        )

    return progress_list


@router.get("/completed", response_model=list[CommunityAchievementEventSchema])
async def get_completed_community_achievements(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[CommunityAchievementEventSchema]:
    """
    Get recently completed community achievements.

    Shows historical community achievements that were successfully completed.
    """
    result = await db.execute(
        select(CommunityAchievementEvent)
        .options(selectinload(CommunityAchievementEvent.achievement))
        .where(CommunityAchievementEvent.is_completed == True)
        .order_by(CommunityAchievementEvent.completed_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    events = result.scalars().all()

    event_list = []
    for event in events:
        user_earned_badge = False
        user_earned_points = 0

        if current_user:
            part_result = await db.execute(
                select(CommunityAchievementParticipant).where(
                    and_(
                        CommunityAchievementParticipant.event_id == event.id,
                        CommunityAchievementParticipant.user_id == current_user.id,
                    )
                )
            )
            participant = part_result.scalar_one_or_none()
            if participant:
                user_earned_badge = participant.badge_awarded
                user_earned_points = participant.points_awarded

        event_list.append(
            CommunityAchievementEventSchema(
                id=str(event.id),
                achievement_id=event.achievement_id,
                achievement_name=event.achievement.name,
                achievement_icon=event.achievement.icon,
                badge_icon=event.achievement.badge_icon,
                triggered_at=event.triggered_at,
                completed_at=event.completed_at,
                final_count=event.final_count,
                participant_count=event.participant_count,
                points_reward=event.achievement.points_reward,
                user_earned_badge=user_earned_badge,
                user_earned_points=user_earned_points,
            )
        )

    return event_list


@router.get("/user/badges", response_model=list[CommunityAchievementEventSchema])
async def get_user_community_badges(
    current_user: UserInDB = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommunityAchievementEventSchema]:
    """
    Get all community badges earned by the current user.
    """
    result = await db.execute(
        select(CommunityAchievementParticipant)
        .options(
            selectinload(CommunityAchievementParticipant.event).selectinload(CommunityAchievementEvent.achievement)
        )
        .where(
            and_(
                CommunityAchievementParticipant.user_id == current_user.id,
                CommunityAchievementParticipant.badge_awarded == True,
            )
        )
        .order_by(CommunityAchievementParticipant.contributed_at.desc())
    )
    participants = result.scalars().all()

    return [
        CommunityAchievementEventSchema(
            id=str(p.event.id),
            achievement_id=p.event.achievement_id,
            achievement_name=p.event.achievement.name,
            achievement_icon=p.event.achievement.icon,
            badge_icon=p.event.achievement.badge_icon,
            triggered_at=p.event.triggered_at,
            completed_at=p.event.completed_at,
            final_count=p.event.final_count,
            participant_count=p.event.participant_count,
            points_reward=p.event.achievement.points_reward,
            user_earned_badge=True,
            user_earned_points=p.points_awarded,
        )
        for p in participants
    ]


@router.get("/leaderboard", response_model=list[CommunityLeaderboard])
async def get_community_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[CommunityLeaderboard]:
    """
    Get the community achievement leaderboard.

    Shows top contributors to community achievements.
    """
    # Aggregate user contributions
    result = await db.execute(
        select(
            CommunityAchievementParticipant.user_id,
            func.sum(CommunityAchievementParticipant.contribution_count).label("total_contributions"),
            func.count(CommunityAchievementParticipant.id).label("achievements_participated"),
            func.sum(func.cast(CommunityAchievementParticipant.badge_awarded, Integer)).label("badges_earned"),
        )
        .group_by(CommunityAchievementParticipant.user_id)
        .order_by(func.sum(CommunityAchievementParticipant.contribution_count).desc())
        .limit(limit)
    )
    rows = result.all()

    # Get user details
    leaderboard = []
    for row in rows:
        user_result = await db.execute(select(User).where(User.id == row.user_id))
        user = user_result.scalar_one_or_none()

        if user:
            leaderboard.append(
                CommunityLeaderboard(
                    user_id=str(user.id),
                    display_name=user.username,
                    avatar_url=user.avatar_url,
                    total_contributions=row.total_contributions or 0,
                    achievements_participated=row.achievements_participated or 0,
                    badges_earned=row.badges_earned or 0,
                )
            )

    return leaderboard


@router.get("/{achievement_id}", response_model=CommunityAchievementProgress)
async def get_community_achievement(
    achievement_id: str,
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> CommunityAchievementProgress:
    """
    Get details of a specific community achievement.
    """
    from datetime import timedelta

    result = await db.execute(select(CommunityAchievement).where(CommunityAchievement.id == achievement_id))
    achievement = result.scalar_one_or_none()

    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community achievement not found",
        )

    # Get current event progress
    now = datetime.now(timezone.utc)
    event_result = await db.execute(
        select(CommunityAchievementEvent)
        .where(
            and_(
                CommunityAchievementEvent.achievement_id == achievement_id,
                CommunityAchievementEvent.is_completed == False,
            )
        )
        .order_by(CommunityAchievementEvent.triggered_at.desc())
        .limit(1)
    )
    event = event_result.scalar_one_or_none()

    current_count = 0
    participant_count = 0
    started_at = None
    time_remaining = None
    user_participated = False
    user_contribution = 0

    if event:
        current_count = event.final_count
        participant_count = event.participant_count
        started_at = event.triggered_at

        if achievement.time_window_hours:
            end_time = event.triggered_at.replace(tzinfo=timezone.utc) + timedelta(hours=achievement.time_window_hours)
            remaining = (end_time - now).total_seconds() / 3600
            time_remaining = max(0, remaining)

        if current_user:
            part_result = await db.execute(
                select(CommunityAchievementParticipant).where(
                    and_(
                        CommunityAchievementParticipant.event_id == event.id,
                        CommunityAchievementParticipant.user_id == current_user.id,
                    )
                )
            )
            participant = part_result.scalar_one_or_none()
            if participant:
                user_participated = True
                user_contribution = participant.contribution_count

    return CommunityAchievementProgress(
        achievement=CommunityAchievementSchema.model_validate(achievement),
        current_count=current_count,
        progress_percentage=min(100, (current_count / achievement.target_count * 100))
        if achievement.target_count > 0
        else 0,
        participant_count=participant_count,
        time_remaining_hours=time_remaining,
        started_at=started_at,
        user_participated=user_participated,
        user_contribution=user_contribution,
    )


# Import needed for leaderboard query
from datetime import timedelta

from sqlalchemy import Integer
