"""
Gamification endpoints for points, achievements, and leaderboards.
"""

from datetime import datetime, timezone
from typing import Annotated, List, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_active_user, get_user_repository
from models.cosmos_documents import AchievementDocument, UserDocument
from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.provider import get_achievement_repository
from schemas.gamification import (
    AchievementEarnedDate,
    AchievementWithHistory,
    LeaderboardEntry,
    LeaderboardResponse,
    LevelDefinitionResponse,
    PointsTransaction,
    ShareTrackRequest,
    ShareTrackResponse,
    UserProgress,
)
from schemas.user import UserInDB

router = APIRouter()


class LevelDefinition(TypedDict):
    """Type for level definition entries."""

    level: int
    name: str
    points_required: int
    perks: list[str]


# Level definitions for progression
LEVEL_DEFINITIONS: list[LevelDefinition] = [
    {"level": 1, "name": "Newcomer", "points_required": 0, "perks": []},
    {
        "level": 2,
        "name": "Engaged Citizen",
        "points_required": 100,
        "perks": ["Custom avatar frame"],
    },
    {
        "level": 3,
        "name": "Poll Enthusiast",
        "points_required": 300,
        "perks": ["Priority poll access"],
    },
    {
        "level": 4,
        "name": "Civic Champion",
        "points_required": 600,
        "perks": ["Exclusive polls"],
    },
    {
        "level": 5,
        "name": "Democracy Defender",
        "points_required": 1000,
        "perks": ["Beta features"],
    },
    {
        "level": 6,
        "name": "Truth Seeker",
        "points_required": 1500,
        "perks": ["Verified badge"],
    },
    {
        "level": 7,
        "name": "Voice of the People",
        "points_required": 2500,
        "perks": ["Suggest polls"],
    },
    {
        "level": 8,
        "name": "Public Pulse",
        "points_required": 4000,
        "perks": ["Early results"],
    },
    {
        "level": 9,
        "name": "Opinion Leader",
        "points_required": 6000,
        "perks": ["Analytics access"],
    },
    {
        "level": 10,
        "name": "TruePulse Legend",
        "points_required": 10000,
        "perks": ["All perks"],
    },
]


def get_level_name(level: int) -> str:
    """Get the name for a given level."""
    for definition in LEVEL_DEFINITIONS:
        if definition["level"] == level:
            return definition["name"]
    return "Newcomer"


def get_points_to_next_level(points: int, current_level: int) -> int:
    """Calculate points needed to reach the next level."""
    for definition in LEVEL_DEFINITIONS:
        if definition["level"] == current_level + 1:
            return max(0, definition["points_required"] - points)
    return 0  # Max level reached


@router.get("/progress", response_model=UserProgress)
async def get_user_progress(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> UserProgress:
    """
    Get the current user's gamification progress.

    Includes points, level, streaks, and progress to next level.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        return UserProgress(
            user_id=current_user.id,
            total_points=0,
            level=1,
            level_name="Newcomer",
            points_to_next_level=100,
            current_streak=0,
            longest_streak=0,
            votes_cast=0,
            polls_participated=0,
        )

    return UserProgress(
        user_id=str(user.id),
        total_points=user.total_points,
        level=user.level,
        level_name=get_level_name(user.level),
        points_to_next_level=get_points_to_next_level(user.total_points, user.level),
        current_streak=user.current_streak,
        longest_streak=user.longest_streak,
        votes_cast=user.votes_cast,
        polls_participated=user.votes_cast,  # For now, votes = polls participated
    )


def calculate_achievement_progress(user: UserDocument, achievement: AchievementDocument) -> tuple[int, bool]:
    """Calculate progress and unlock status for an achievement based on user data."""
    action_type = achievement.action_type
    target = achievement.target_count

    if action_type == "vote":
        progress = min(user.votes_cast, target)
        is_unlocked = user.votes_cast >= target
    elif action_type == "streak":
        # Use longest_streak for streak achievements (so they stay unlocked)
        progress = min(user.longest_streak, target)
        is_unlocked = user.longest_streak >= target
    elif action_type == "profile":
        demo_count = 0
        for field in [
            "age_range",
            "gender",
            "country",
            "region",
            "state_province",
            "city",
            "education_level",
            "employment_status",
            "industry",
            "political_leaning",
        ]:
            if getattr(user, field, None):
                demo_count += 1
        progress = min(demo_count, target)
        is_unlocked = demo_count >= target
    elif action_type == "demographic":
        # These are awarded when specific demographics are filled
        # Check based on achievement id
        demo_map = {
            "demo_age": "age_range",
            "demo_gender": "gender",
            "demo_location": "country",
            "demo_education": "education_level",
            "demo_employment": "employment_status",
            "demo_political": "political_leaning",
        }
        if achievement.id in demo_map:
            is_unlocked = bool(getattr(user, demo_map[achievement.id], None))
            progress = 1 if is_unlocked else 0
        elif achievement.id == "demo_geo_detailed":
            has_both = bool(getattr(user, "state_province", None)) and bool(getattr(user, "city", None))
            is_unlocked = has_both
            progress = 1 if is_unlocked else 0
        else:
            progress = 0
            is_unlocked = False
    elif action_type.startswith("leaderboard"):
        # Leaderboard achievements are awarded by a scheduled job
        progress = 0
        is_unlocked = False
    elif action_type == "share":
        # Total share count achievements
        total_shares = getattr(user, "total_shares", 0) or 0
        progress = min(total_shares, target)
        is_unlocked = total_shares >= target
    elif action_type.startswith("share_"):
        # Platform-specific share achievements are tracked in user achievement records
        # These are marked unlocked when awarded, so progress is binary
        progress = 0
        is_unlocked = False
    else:
        progress = 0
        is_unlocked = False

    return progress, is_unlocked


@router.get("/achievements", response_model=List[AchievementWithHistory])
async def get_achievements(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
    include_locked: bool = Query(True),
    category: Optional[str] = Query(None, description="Filter by category: voting, streak, profile, leaderboard"),
) -> List[AchievementWithHistory]:
    """
    Get the user's achievements and badges with earn history.

    For repeatable achievements, shows all dates earned.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        return []

    # Get all achievements from Cosmos DB
    if category:
        all_achievements = await achievement_repo.get_achievements_by_category(category)
    else:
        all_achievements = await achievement_repo.get_all_achievements()

    # Get user's earned achievements
    user_achievements = await achievement_repo.get_user_achievements(
        user_id=str(user.id),
        unlocked_only=True,
    )

    # Build a map of achievement_id -> list of earned dates
    earned_dates_map: dict[str, list[datetime]] = {}
    for ua in user_achievements:
        if ua.achievement_id not in earned_dates_map:
            earned_dates_map[ua.achievement_id] = []
        if ua.unlocked_at:
            earned_dates_map[ua.achievement_id].append(ua.unlocked_at)

    achievements_response = []
    for achievement in all_achievements:
        progress, is_unlocked = calculate_achievement_progress(user, achievement)

        # Check if user has earned this achievement (from database records)
        earned_dates = earned_dates_map.get(achievement.id, [])
        if earned_dates:
            is_unlocked = True

        # Sort dates descending (most recent first)
        earned_dates.sort(reverse=True)

        # Get first unlocked date
        unlocked_at = earned_dates[0] if earned_dates else None

        # Build earned history for repeatable achievements
        earned_history = [AchievementEarnedDate(earned_at=d, period_key=None) for d in earned_dates]

        achievement_response = AchievementWithHistory(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            points_reward=achievement.points_reward,
            is_unlocked=is_unlocked,
            unlocked_at=unlocked_at,
            progress=progress,
            target=achievement.target_count,
            tier=achievement.tier,
            category=achievement.category,
            is_repeatable=achievement.is_repeatable,
            times_earned=len(earned_dates),
            earned_history=earned_history if achievement.is_repeatable else [],
        )

        if include_locked or is_unlocked:
            achievements_response.append(achievement_response)

    return achievements_response


@router.get("/achievements/all", response_model=List[AchievementWithHistory])
async def get_all_achievements(
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
    category: Optional[str] = Query(None, description="Filter by category: voting, streak, profile, leaderboard"),
    tier: Optional[str] = Query(None, description="Filter by tier: bronze, silver, gold, platinum"),
    search: Optional[str] = Query(None, description="Search by name or description"),
) -> List[AchievementWithHistory]:
    """
    Get all available achievements (public endpoint).

    Does not require authentication. Shows all achievements without user progress.
    """
    # Get all achievements from Cosmos DB
    if category:
        all_achievements = await achievement_repo.get_achievements_by_category(category)
    elif tier:
        from models.cosmos_documents import AchievementTier

        all_achievements = await achievement_repo.get_achievements_by_tier(AchievementTier(tier))
    else:
        all_achievements = await achievement_repo.get_all_achievements()

    # Apply tier filter if category was used
    if category and tier:
        all_achievements = [a for a in all_achievements if a.tier == tier]

    achievements_response = []
    for achievement in all_achievements:
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            if search_lower not in achievement.name.lower() and search_lower not in achievement.description.lower():
                continue

        achievement_response = AchievementWithHistory(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            points_reward=achievement.points_reward,
            is_unlocked=False,
            unlocked_at=None,
            progress=0,
            target=achievement.target_count,
            tier=achievement.tier,
            category=achievement.category,
            is_repeatable=achievement.is_repeatable,
            times_earned=0,
            earned_history=[],
        )
        achievements_response.append(achievement_response)

    return achievements_response


@router.get("/achievements/user", response_model=List[AchievementWithHistory])
async def get_user_achievements_status(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
    category: Optional[str] = Query(None, description="Filter by category: voting, streak, profile, leaderboard"),
    tier: Optional[str] = Query(None, description="Filter by tier: bronze, silver, gold, platinum"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    unlocked_only: bool = Query(False, description="Only show unlocked achievements"),
) -> List[AchievementWithHistory]:
    """
    Get achievements with user's progress and unlock status.

    Requires authentication. Shows which achievements the user has earned.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        return []

    # Get all achievements from Cosmos DB
    if category:
        all_achievements = await achievement_repo.get_achievements_by_category(category)
    elif tier:
        from models.cosmos_documents import AchievementTier

        all_achievements = await achievement_repo.get_achievements_by_tier(AchievementTier(tier))
    else:
        all_achievements = await achievement_repo.get_all_achievements()

    # Apply tier filter if category was used
    if category and tier:
        all_achievements = [a for a in all_achievements if a.tier == tier]

    # Get user's earned achievements
    user_achievements = await achievement_repo.get_user_achievements(
        user_id=str(user.id),
        unlocked_only=True,
    )

    # Build a map of achievement_id -> list of earned dates
    earned_dates_map: dict[str, list[datetime]] = {}
    for ua in user_achievements:
        if ua.achievement_id not in earned_dates_map:
            earned_dates_map[ua.achievement_id] = []
        if ua.unlocked_at:
            earned_dates_map[ua.achievement_id].append(ua.unlocked_at)

    achievements_response = []
    for achievement in all_achievements:
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            if search_lower not in achievement.name.lower() and search_lower not in achievement.description.lower():
                continue

        progress, is_unlocked = calculate_achievement_progress(user, achievement)

        # Check if user has earned this achievement (from database records)
        earned_dates = earned_dates_map.get(achievement.id, [])
        if earned_dates:
            is_unlocked = True

        # Apply unlocked_only filter
        if unlocked_only and not is_unlocked:
            continue

        # Sort dates descending (most recent first)
        earned_dates.sort(reverse=True)

        # Get first unlocked date
        unlocked_at = earned_dates[0] if earned_dates else None

        # Build earned history for repeatable achievements
        earned_history = [AchievementEarnedDate(earned_at=d, period_key=None) for d in earned_dates]

        achievement_response = AchievementWithHistory(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            points_reward=achievement.points_reward,
            is_unlocked=is_unlocked,
            unlocked_at=unlocked_at,
            progress=progress,
            target=achievement.target_count,
            tier=achievement.tier,
            category=achievement.category,
            is_repeatable=achievement.is_repeatable,
            times_earned=len(earned_dates),
            earned_history=earned_history if achievement.is_repeatable else [],
        )
        achievements_response.append(achievement_response)

    return achievements_response


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    period: str = Query("weekly", regex="^(daily|weekly|monthly|alltime)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> LeaderboardResponse:
    """
    Get the public leaderboard.

    Only shows users who have opted in to leaderboard visibility.
    """
    offset = (page - 1) * per_page

    # Get leaderboard users (filtered by show_on_leaderboard in repo)
    users = await user_repo.get_leaderboard(limit=per_page, offset=offset)

    entries = []
    for rank, user in enumerate(users, start=offset + 1):
        if user.show_on_leaderboard:
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    username=user.username,
                    display_name=user.display_name or user.username,
                    avatar_url=user.avatar_url,
                    points=user.total_points,
                    level=user.level,
                    level_name=get_level_name(user.level),
                )
            )

    # Get total count for pagination
    total_users = await user_repo.get_leaderboard(limit=10000, offset=0)
    total_count = len([u for u in total_users if u.show_on_leaderboard])
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

    return LeaderboardResponse(
        entries=entries,
        period=period,
        total_participants=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/leaderboard/me", response_model=LeaderboardEntry | None)
async def get_my_leaderboard_position(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    period: str = Query("weekly", regex="^(daily|weekly|monthly|alltime)$"),
) -> LeaderboardEntry | None:
    """
    Get the current user's position on the leaderboard.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        return None

    # Calculate rank by counting users with more points
    all_users = await user_repo.get_leaderboard(limit=10000, offset=0)
    rank = 1
    for other_user in all_users:
        if other_user.total_points > user.total_points:
            rank += 1

    return LeaderboardEntry(
        rank=rank,
        username=user.username,
        display_name=user.display_name or user.username,
        avatar_url=user.avatar_url,
        points=user.total_points,
        level=user.level,
        level_name=get_level_name(user.level),
    )


@router.get("/history", response_model=list[PointsTransaction])
async def get_points_history(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> list[PointsTransaction]:
    """
    Get the user's points transaction history.
    """
    offset = (page - 1) * per_page
    transactions = await achievement_repo.get_points_history(
        user_id=current_user.id,
        limit=per_page,
        offset=offset,
    )

    return [
        PointsTransaction(
            id=t.id,
            action=t.action,
            points=t.points,
            description=t.description,
            created_at=t.created_at,
        )
        for t in transactions
    ]


@router.get("/levels", response_model=list[LevelDefinitionResponse])
async def get_level_definitions() -> list[LevelDefinitionResponse]:
    """
    Get the level progression definitions.
    """
    return [LevelDefinitionResponse(**level) for level in LEVEL_DEFINITIONS]


@router.post("/share", response_model=ShareTrackResponse)
async def track_share(
    request: ShareTrackRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> ShareTrackResponse:
    """
    Track a poll share action and award points/achievements.

    Awards 5 points per share and checks for sharing achievements:
    - First Share: Share your first poll
    - Social Butterfly: Share 10 polls
    - Influencer: Share 50 polls
    - Ambassador: Share 100 polls
    - Platform-specific achievements for each social platform
    - Cross-Platform Champion: Share on all available platforms
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Normalize platform name
    platform = request.platform.lower()
    valid_platforms = [
        "twitter",
        "facebook",
        "linkedin",
        "reddit",
        "whatsapp",
        "telegram",
        "copy",
        "native",
    ]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )

    # Award 5 points for sharing
    share_points = 5
    await user_repo.award_points(user.id, share_points)
    await user_repo.increment_shares(user.id)

    # Record the points transaction
    await achievement_repo.record_points_transaction(
        user_id=user.id,
        action="share",
        points=share_points,
        description=f"Shared poll on {platform}",
        reference_type="share",
        reference_id=platform,
    )

    # Get updated user
    updated_user = await user_repo.get_by_id(user.id)
    total_shares = updated_user.total_shares if updated_user else user.total_shares + 1

    # Check for sharing achievements
    awarded_achievements: list[AchievementDocument] = []
    share_achievements = [
        ("first_share", 1),
        ("social_butterfly", 10),
        ("influencer", 50),
        ("ambassador", 100),
    ]

    for achievement_id, target in share_achievements:
        if total_shares >= target:
            # Check if already unlocked
            existing = await achievement_repo.get_user_achievement(user.id, achievement_id)
            if not existing or not existing.is_unlocked:
                achievement = await achievement_repo.get_achievement(achievement_id)
                if achievement:
                    await achievement_repo.unlock_achievement(user.id, achievement_id)
                    awarded_achievements.append(achievement)
                    # Award achievement points
                    if achievement.points_reward > 0:
                        await user_repo.award_points(user.id, achievement.points_reward)
                        await achievement_repo.record_points_transaction(
                            user_id=user.id,
                            action="achievement",
                            points=achievement.points_reward,
                            description=f"Unlocked: {achievement.name}",
                            reference_type="achievement",
                            reference_id=achievement_id,
                        )

    # Calculate total points earned
    points_earned = share_points + sum(a.points_reward for a in awarded_achievements)

    # Build response with new achievement details
    new_achievements = []
    for achievement in awarded_achievements:
        new_achievements.append(
            AchievementWithHistory(
                id=achievement.id,
                name=achievement.name,
                description=achievement.description,
                icon=achievement.icon,
                points_reward=achievement.points_reward,
                is_unlocked=True,
                unlocked_at=datetime.now(timezone.utc),
                progress=achievement.target_count,
                target=achievement.target_count,
                tier=achievement.tier,
                category=achievement.category,
                is_repeatable=achievement.is_repeatable,
                times_earned=1,
                earned_history=[],
            )
        )

    # Build message
    if awarded_achievements:
        achievement_names = [a.name for a in awarded_achievements]
        message = f"Share recorded! You earned {points_earned} points and unlocked: {', '.join(achievement_names)}"
    else:
        message = f"Share recorded! You earned {points_earned} points."

    return ShareTrackResponse(
        points_earned=points_earned,
        total_shares=total_shares,
        new_achievements=new_achievements,
        message=message,
    )
