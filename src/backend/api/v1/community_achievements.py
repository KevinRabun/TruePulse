"""
Community achievements API endpoints.

Community achievements are collective goals where all participants
earn rewards when the community reaches a target together.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.deps import get_current_user_optional, get_current_verified_user, get_user_repository
from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.provider import get_achievement_repository
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
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> list[CommunityAchievementProgress]:
    """
    Get all active community achievements with current progress.

    Shows the collective goals that the community is working towards,
    along with current progress and participant counts.
    """
    # Get active community achievements
    achievements = await achievement_repo.get_active_community_achievements()

    progress_list = []
    now = datetime.now(timezone.utc)

    for ach in achievements:
        # Get the latest event for this achievement (if any)
        event = await achievement_repo.get_community_achievement_event(ach.id, active_only=True)

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
                triggered = event.triggered_at
                if triggered.tzinfo is None:
                    triggered = triggered.replace(tzinfo=timezone.utc)
                end_time = triggered + timedelta(hours=ach.time_window_hours)
                remaining = (end_time - now).total_seconds() / 3600
                time_remaining = max(0, remaining)

            # Check if current user participated
            if current_user:
                participant = await achievement_repo.get_user_community_participation(current_user.id, event.id)
                if participant:
                    user_participated = True
                    user_contribution = participant.contribution_count

        progress_list.append(
            CommunityAchievementProgress(
                achievement=CommunityAchievementSchema(
                    id=ach.id,
                    name=ach.name,
                    description=ach.description,
                    icon=ach.icon,
                    badge_icon=ach.badge_icon,
                    goal_type=ach.goal_type,
                    target_count=ach.target_count,
                    time_window_hours=ach.time_window_hours,
                    points_reward=ach.points_reward,
                    bonus_multiplier=ach.bonus_multiplier,
                    is_recurring=ach.is_recurring,
                    cooldown_hours=ach.cooldown_hours,
                    tier=ach.tier if isinstance(ach.tier, str) else ach.tier.value,
                    category=ach.category,
                    is_active=ach.is_active,
                ),
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
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> list[CommunityAchievementEventSchema]:
    """
    Get recently completed community achievements.

    Shows historical community achievements that were successfully completed.
    """
    offset = (page - 1) * per_page
    events = await achievement_repo.get_completed_community_events(limit=per_page, offset=offset)

    event_list = []
    for event in events:
        # Get the achievement details
        achievement = await achievement_repo.get_community_achievement(event.achievement_id)
        if not achievement:
            continue

        user_earned_badge = False
        user_earned_points = 0

        if current_user:
            participant = await achievement_repo.get_user_community_participation(current_user.id, event.id)
            if participant:
                user_earned_badge = participant.badge_awarded
                user_earned_points = participant.points_awarded

        event_list.append(
            CommunityAchievementEventSchema(
                id=event.id,
                achievement_id=event.achievement_id,
                achievement_name=achievement.name,
                achievement_icon=achievement.icon,
                badge_icon=achievement.badge_icon,
                triggered_at=event.triggered_at,
                completed_at=event.completed_at,
                final_count=event.final_count,
                participant_count=event.participant_count,
                points_reward=achievement.points_reward,
                user_earned_badge=user_earned_badge,
                user_earned_points=user_earned_points,
            )
        )

    return event_list


@router.get("/user/badges", response_model=list[CommunityAchievementEventSchema])
async def get_user_community_badges(
    current_user: UserInDB = Depends(get_current_verified_user),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> list[CommunityAchievementEventSchema]:
    """
    Get all community badges earned by the current user.
    """
    participants = await achievement_repo.get_user_community_badges(current_user.id)

    result = []
    for p in participants:
        # Get the event and achievement details
        event = await achievement_repo.get_community_achievement_event(p.achievement_id, active_only=False)
        if not event:
            continue

        achievement = await achievement_repo.get_community_achievement(p.achievement_id)
        if not achievement:
            continue

        result.append(
            CommunityAchievementEventSchema(
                id=event.id,
                achievement_id=event.achievement_id,
                achievement_name=achievement.name,
                achievement_icon=achievement.icon,
                badge_icon=achievement.badge_icon,
                triggered_at=event.triggered_at,
                completed_at=event.completed_at,
                final_count=event.final_count,
                participant_count=event.participant_count,
                points_reward=achievement.points_reward,
                user_earned_badge=True,
                user_earned_points=p.points_awarded,
            )
        )

    return result


@router.get("/leaderboard", response_model=list[CommunityLeaderboard])
async def get_community_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> list[CommunityLeaderboard]:
    """
    Get the community achievement leaderboard.

    Shows top contributors to community achievements.
    """
    # Get aggregated user contributions
    rows = await achievement_repo.get_community_leaderboard(limit=limit)

    # Get user details
    leaderboard = []
    for row in rows:
        user = await user_repo.get_user(row["user_id"])

        if user:
            leaderboard.append(
                CommunityLeaderboard(
                    user_id=user.id,
                    display_name=user.display_name or user.username,
                    avatar_url=user.avatar_url,
                    total_contributions=row.get("total_contributions", 0) or 0,
                    achievements_participated=row.get("achievements_participated", 0) or 0,
                    badges_earned=row.get("badges_earned", 0) or 0,
                )
            )

    return leaderboard


@router.get("/{achievement_id}", response_model=CommunityAchievementProgress)
async def get_community_achievement(
    achievement_id: str,
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> CommunityAchievementProgress:
    """
    Get details of a specific community achievement.
    """
    achievement = await achievement_repo.get_community_achievement(achievement_id)

    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community achievement not found",
        )

    # Get current event progress
    now = datetime.now(timezone.utc)
    event = await achievement_repo.get_community_achievement_event(achievement_id, active_only=True)

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
            triggered = event.triggered_at
            if triggered.tzinfo is None:
                triggered = triggered.replace(tzinfo=timezone.utc)
            end_time = triggered + timedelta(hours=achievement.time_window_hours)
            remaining = (end_time - now).total_seconds() / 3600
            time_remaining = max(0, remaining)

        if current_user:
            participant = await achievement_repo.get_user_community_participation(current_user.id, event.id)
            if participant:
                user_participated = True
                user_contribution = participant.contribution_count

    return CommunityAchievementProgress(
        achievement=CommunityAchievementSchema(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            badge_icon=achievement.badge_icon,
            goal_type=achievement.goal_type,
            target_count=achievement.target_count,
            time_window_hours=achievement.time_window_hours,
            points_reward=achievement.points_reward,
            bonus_multiplier=achievement.bonus_multiplier,
            is_recurring=achievement.is_recurring,
            cooldown_hours=achievement.cooldown_hours,
            tier=achievement.tier if isinstance(achievement.tier, str) else achievement.tier.value,
            category=achievement.category,
            is_active=achievement.is_active,
        ),
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
