"""
User profile and settings endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_active_user, get_current_verified_user, get_user_repository
from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.provider import get_achievement_repository
from schemas.user import (
    DEMOGRAPHIC_POINTS,
    DemographicsUpdateResponse,
    RecentVote,
    UserDemographics,
    UserInDB,
    UserProfileUpdate,
    UserResponse,
    UserSettings,
)
from services.achievement_service import AchievementService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> UserResponse:
    """
    Get the current user's profile.
    """
    # Get recent votes - Note: Vote history is not stored in Cosmos due to privacy design
    # Votes don't contain user_id. This would require a separate user-votes container.
    # For now, return empty list pending full vote history migration.
    recent_votes: list[RecentVote] = []

    # Count unlocked achievements using Cosmos repository
    user_achievements = await achievement_repo.get_user_achievements(
        user_id=current_user.id,
        unlocked_only=True,
    )
    achievements_count = len(user_achievements)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name or current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        email_verified=current_user.email_verified,
        points=current_user.points,
        level=current_user.level,
        total_votes=current_user.votes_cast,
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        achievements_count=achievements_count,
        created_at=current_user.created_at,
        recent_votes=recent_votes,
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> UserResponse:
    """
    Update the current user's profile.
    """
    # Check if new username is already taken (if changing)
    if profile_data.username and profile_data.username != current_user.username:
        if await user_repo.username_exists(profile_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    try:
        updated_user = await user_repo.update_profile(
            user_id=current_user.id,
            username=profile_data.username,
            display_name=profile_data.display_name,
            avatar_url=profile_data.avatar_url,
            bio=profile_data.bio,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        username=updated_user.username,
        display_name=updated_user.display_name or updated_user.username,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        email_verified=updated_user.email_verified,
        points=updated_user.total_points,
        level=updated_user.level,
        avatar_url=updated_user.avatar_url,
    )


@router.get("/me/demographics", response_model=UserDemographics | None)
async def get_demographics(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> UserDemographics | None:
    """
    Get the current user's demographic information.

    This data is used ONLY for aggregated polling insights.
    It is NEVER linked to individual vote records.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        return None

    # Return demographics if any are set
    if any(
        [
            user.age_range,
            user.gender,
            user.country,
            user.region,
            user.state_province,
            user.city,
            user.education_level,
            user.employment_status,
            user.industry,
            user.political_leaning,
        ]
    ):
        return UserDemographics(
            age_range=user.age_range,
            gender=user.gender,
            country=user.country,
            region=user.region,
            state_province=user.state_province,
            city=user.city,
            education_level=user.education_level,
            employment_status=user.employment_status,
            industry=user.industry,
            political_leaning=user.political_leaning,
            marital_status=user.marital_status,
            religious_affiliation=user.religious_affiliation,
            ethnicity=user.ethnicity,
            household_income=user.household_income,
            parental_status=user.parental_status,
            housing_status=user.housing_status,
        )

    return None


@router.put("/me/demographics", response_model=DemographicsUpdateResponse)
async def update_demographics(
    demographics: UserDemographics,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
    achievement_repo: CosmosAchievementRepository = Depends(get_achievement_repository),
) -> DemographicsUpdateResponse:
    """
    Update demographic information.

    Providing demographic data is optional but helps improve
    polling insights. Users earn gamification points for
    providing this information:
    - Age range: 150 points
    - Gender: 100 points
    - Country: 150 points
    - Region: 100 points
    - State/Province: 125 points
    - City: 100 points
    - Education level: 150 points
    - Employment status: 125 points
    - Industry: 125 points
    - Political leaning: 200 points

    Privacy Note: Demographics are stored separately from votes
    and only used in aggregated form.
    """
    # Get existing user demographics to avoid double-awarding points
    existing_user = await user_repo.get_by_id(current_user.id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Calculate points only for newly provided demographic fields
    points_breakdown: dict[str, int] = {}
    total_points_earned = 0

    demographics_dict = demographics.model_dump(exclude_none=True)
    for field, value in demographics_dict.items():
        if value and field in DEMOGRAPHIC_POINTS:
            # Check if this field was previously empty
            existing_value = getattr(existing_user, field, None)
            if not existing_value:  # Only award points if field was not previously set
                points = DEMOGRAPHIC_POINTS[field]
                points_breakdown[field] = points
                total_points_earned += points

    # Update demographics in database
    updated_user = await user_repo.update_demographics(
        user_id=current_user.id,
        age_range=demographics.age_range,
        gender=demographics.gender,
        country=demographics.country,
        state_province=demographics.state_province,
        city=demographics.city,
        education_level=demographics.education_level,
        employment_status=demographics.employment_status,
        industry=demographics.industry,
        political_leaning=demographics.political_leaning,
        marital_status=demographics.marital_status,
        religious_affiliation=demographics.religious_affiliation,
        ethnicity=demographics.ethnicity,
        household_income=demographics.household_income,
        parental_status=demographics.parental_status,
        housing_status=demographics.housing_status,
    )

    # Award gamification points if any earned
    if total_points_earned > 0:
        await user_repo.award_points(current_user.id, total_points_earned, update_level=True)

    # Refresh to get updated points
    updated_user = await user_repo.get_by_id(current_user.id)
    new_total_points = updated_user.total_points if updated_user else 0

    # Check and award demographic achievements
    if updated_user:
        achievement_service = AchievementService(achievement_repo, user_repo)
        await achievement_service.check_and_award_demographic_achievements(updated_user, "")

    return DemographicsUpdateResponse(
        demographics=demographics,
        points_earned=total_points_earned,
        points_breakdown=points_breakdown,
        new_total_points=new_total_points,
        message=f"Demographics updated! You earned {total_points_earned} points."
        if total_points_earned > 0
        else "Demographics updated.",
    )


@router.get("/me/settings", response_model=UserSettings)
async def get_settings(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> UserSettings:
    """
    Get user notification and privacy settings.
    """
    user = await user_repo.get_by_id(current_user.id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserSettings(
        email_notifications=user.email_notifications if hasattr(user, "email_notifications") else True,
        push_notifications=user.push_notifications if hasattr(user, "push_notifications") else False,
        daily_poll_reminder=user.daily_poll_reminder if hasattr(user, "daily_poll_reminder") else True,
        show_on_leaderboard=user.show_on_leaderboard if hasattr(user, "show_on_leaderboard") else True,
        share_anonymous_demographics=user.share_anonymous_demographics
        if hasattr(user, "share_anonymous_demographics")
        else True,
        theme_preference=user.theme_preference if hasattr(user, "theme_preference") else "system",
        pulse_poll_notifications=user.pulse_poll_notifications if hasattr(user, "pulse_poll_notifications") else True,
        flash_poll_notifications=user.flash_poll_notifications if hasattr(user, "flash_poll_notifications") else True,
        flash_polls_per_day=user.flash_polls_per_day if hasattr(user, "flash_polls_per_day") else 5,
    )


@router.put("/me/settings", response_model=UserSettings)
async def update_settings(
    settings: UserSettings,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> UserSettings:
    """
    Update user settings.
    """
    updated_user = await user_repo.update_settings(
        user_id=current_user.id,
        email_notifications=settings.email_notifications,
        push_notifications=settings.push_notifications,
        daily_poll_reminder=settings.daily_poll_reminder,
        show_on_leaderboard=settings.show_on_leaderboard,
        share_anonymous_demographics=settings.share_anonymous_demographics,
        theme_preference=settings.theme_preference,
        pulse_poll_notifications=settings.pulse_poll_notifications,
        flash_poll_notifications=settings.flash_poll_notifications,
        flash_polls_per_day=settings.flash_polls_per_day,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return settings


@router.delete("/me")
async def delete_account(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(get_user_repository),
) -> dict[str, str]:
    """
    Delete user account and all associated data.

    Note: Vote records (which contain only hashes, not user IDs)
    will remain in the system to maintain polling accuracy,
    but they cannot be linked back to the deleted user.
    """
    # Soft delete the user (Cosmos uses soft_delete method)
    # Vote hashes remain (already anonymized - no user_id stored)
    await user_repo.soft_delete(current_user.id)

    return {"message": "Account deleted successfully"}
