"""
User profile and settings endpoints.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_verified_user, get_current_active_user
from db.session import get_db
from models.user_vote_history import UserVoteHistory
from models.poll import Poll
from models.achievement import UserAchievement
from repositories.user_repository import UserRepository
from services.achievement_service import AchievementService
from schemas.user import (
    UserInDB,
    UserResponse,
    UserProfileUpdate,
    UserDemographics,
    DemographicsUpdateResponse,
    DEMOGRAPHIC_POINTS,
    UserSettings,
    PhoneNumberUpdate,
    PhoneVerificationRequest,
    PhoneVerificationResponse,
    SMSPreferencesUpdate,
    RecentVote,
)
from services.sms_service import sms_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get the current user's profile.
    """
    # Get recent votes from vote history
    result = await db.execute(
        select(UserVoteHistory, Poll.question)
        .join(Poll, UserVoteHistory.poll_id == Poll.id)
        .where(UserVoteHistory.user_id == current_user.id)
        .order_by(UserVoteHistory.voted_at.desc())
        .limit(10)
    )
    vote_history = result.all()
    
    recent_votes = [
        RecentVote(
            poll_id=str(vh.poll_id),
            poll_question=question,
            voted_at=vh.voted_at,
        )
        for vh, question in vote_history
    ]
    
    # Count unlocked achievements
    achievements_result = await db.execute(
        select(func.count(func.distinct(UserAchievement.achievement_id)))
        .where(UserAchievement.user_id == current_user.id)
        .where(UserAchievement.is_unlocked == True)
    )
    achievements_count = achievements_result.scalar() or 0
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
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
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's profile.
    """
    repo = UserRepository(db)
    
    # Check if new username is already taken (if changing)
    if profile_data.username and profile_data.username != current_user.username:
        if await repo.username_exists(profile_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
    
    updated_user = await repo.update_profile(
        user_id=current_user.id,
        username=profile_data.username,
        avatar_url=profile_data.avatar_url,
        bio=profile_data.bio,
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
        display_name=updated_user.username,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        points=updated_user.total_points,
        level=updated_user.level,
        avatar_url=updated_user.avatar_url,
    )


@router.get("/me/demographics", response_model=UserDemographics | None)
async def get_demographics(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> UserDemographics | None:
    """
    Get the current user's demographic information.
    
    This data is used ONLY for aggregated polling insights.
    It is NEVER linked to individual vote records.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    
    if not user:
        return None
    
    # Return demographics if any are set
    if any([
        user.age_range, user.gender, user.country, user.region,
        user.state_province, user.city,
        user.education_level, user.employment_status, user.industry,
        user.political_leaning
    ]):
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
    db: AsyncSession = Depends(get_db),
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
    repo = UserRepository(db)
    
    # Get existing user demographics to avoid double-awarding points
    existing_user = await repo.get_by_id(current_user.id)
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
    updated_user = await repo.update_demographics(
        user_id=current_user.id,
        age_range=demographics.age_range,
        gender=demographics.gender,
        country=demographics.country,
        region=demographics.region,
        state_province=demographics.state_province,
        city=demographics.city,
        education_level=demographics.education_level,
        employment_status=demographics.employment_status,
        industry=demographics.industry,
        political_leaning=demographics.political_leaning,
    )
    
    # Award gamification points if any earned
    if total_points_earned > 0:
        await repo.award_points(current_user.id, total_points_earned, update_level=True)
    
    # Refresh to get updated points
    updated_user = await repo.get_by_id(current_user.id)
    new_total_points = updated_user.total_points if updated_user else 0
    
    # Check and award demographic achievements
    if updated_user:
        achievement_service = AchievementService(db)
        # Pass any field that was updated to check relevant achievements
        for field in demographics_dict.keys():
            await achievement_service.check_and_award_demographic_achievements(updated_user, field)
    
    return DemographicsUpdateResponse(
        demographics=demographics,
        points_earned=total_points_earned,
        points_breakdown=points_breakdown,
        new_total_points=new_total_points,
        message=f"Demographics updated! You earned {total_points_earned} points." if total_points_earned > 0 else "Demographics updated."
    )


@router.get("/me/settings", response_model=UserSettings)
async def get_settings(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> UserSettings:
    """
    Get user notification and privacy settings.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserSettings(
        email_notifications=user.email_notifications if hasattr(user, 'email_notifications') else True,
        push_notifications=user.push_notifications if hasattr(user, 'push_notifications') else False,
        daily_poll_reminder=user.daily_poll_reminder if hasattr(user, 'daily_poll_reminder') else True,
        show_on_leaderboard=user.show_on_leaderboard if hasattr(user, 'show_on_leaderboard') else True,
        share_anonymous_demographics=user.share_anonymous_demographics if hasattr(user, 'share_anonymous_demographics') else True,
        theme_preference=user.theme_preference if hasattr(user, 'theme_preference') else "system",
        pulse_poll_notifications=user.pulse_poll_notifications if hasattr(user, 'pulse_poll_notifications') else True,
        flash_poll_notifications=user.flash_poll_notifications if hasattr(user, 'flash_poll_notifications') else True,
        flash_polls_per_day=user.flash_polls_per_day if hasattr(user, 'flash_polls_per_day') else 5,
    )


@router.put("/me/settings", response_model=UserSettings)
async def update_settings(
    settings: UserSettings,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> UserSettings:
    """
    Update user settings.
    """
    repo = UserRepository(db)
    
    updated_user = await repo.update_settings(
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


# ============== Phone/SMS Endpoints ==============

@router.post("/me/phone", response_model=PhoneVerificationResponse)
async def add_phone_number(
    phone_data: PhoneNumberUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationResponse:
    """
    Add or update phone number and send verification code.
    
    The phone number must be verified before SMS notifications can be enabled.
    A 6-digit verification code will be sent via SMS.
    """
    repo = UserRepository(db)
    
    # Generate verification code
    code = sms_service.generate_verification_code()
    
    # Send verification SMS
    sent = await sms_service.send_verification_code(
        phone_number=phone_data.phone_number,
        code=code,
    )
    
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send verification SMS. Please try again later.",
        )
    
    # Store phone number and verification code in database
    await repo.set_phone_verification(
        user_id=current_user.id,
        phone_number=phone_data.phone_number,
        verification_code=code,
    )
    
    return PhoneVerificationResponse(
        success=True,
        message=f"Verification code sent to {phone_data.phone_number[:6]}***",
        phone_verified=False,
    )


@router.post("/me/phone/verify", response_model=PhoneVerificationResponse)
async def verify_phone_number(
    verification: PhoneVerificationRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationResponse:
    """
    Verify phone number with the 6-digit code sent via SMS.
    
    Once both email AND phone are verified, user can vote.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    stored_code = getattr(user, 'phone_verification_code', None)
    sent_at = getattr(user, 'phone_verification_sent_at', None)
    
    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one.",
        )
    
    # Check if code is expired
    if sms_service.is_code_expired(sent_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )
    
    # Verify code
    if stored_code != verification.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )
    
    # Mark phone as verified
    await repo.verify_phone(current_user.id)
    
    # Refresh user to get updated verification status
    user = await repo.get_by_id(current_user.id)
    
    # Award verification achievement
    if user:
        from services.achievement_service import AchievementService
        achievement_service = AchievementService(db)
        await achievement_service.check_and_award_verification_achievements(user, "phone")
        await db.commit()
    
    return PhoneVerificationResponse(
        success=True,
        message="Phone number verified successfully!",
        phone_verified=True,
    )


@router.post("/me/phone/resend", response_model=PhoneVerificationResponse)
async def resend_verification_code(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationResponse:
    """
    Resend the phone verification code.
    
    Can only be called if user has a phone number on file.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    phone_number = getattr(user, 'phone_number', None)
    
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phone number on file. Please add a phone number first.",
        )
    
    if getattr(user, 'phone_verified', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already verified.",
        )
    
    # Generate new code
    code = sms_service.generate_verification_code()
    
    # Send verification SMS
    sent = await sms_service.send_verification_code(
        phone_number=phone_number,
        code=code,
    )
    
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send verification SMS. Please try again later.",
        )
    
    # Update database with new code
    await repo.set_phone_verification(
        user_id=current_user.id,
        phone_number=phone_number,
        verification_code=code,
    )
    
    return PhoneVerificationResponse(
        success=True,
        message=f"Verification code resent to {phone_number[:6]}***",
        phone_verified=False,
    )


@router.delete("/me/phone", response_model=PhoneVerificationResponse)
async def remove_phone_number(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationResponse:
    """
    Remove phone number and disable all SMS notifications.
    """
    repo = UserRepository(db)
    
    await repo.remove_phone(current_user.id)
    
    return PhoneVerificationResponse(
        success=True,
        message="Phone number removed and SMS notifications disabled.",
        phone_verified=False,
    )


@router.put("/me/sms-preferences", response_model=SMSPreferencesUpdate)
async def update_sms_preferences(
    preferences: SMSPreferencesUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> SMSPreferencesUpdate:
    """
    Update SMS notification preferences.
    
    Phone number must be verified before enabling SMS notifications.
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if phone is verified
    if not getattr(user, 'phone_verified', False):
        if preferences.sms_notifications or preferences.daily_poll_sms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number must be verified before enabling SMS notifications.",
            )
    
    await repo.update_sms_preferences(
        user_id=current_user.id,
        sms_notifications=preferences.sms_notifications,
        daily_poll_sms=preferences.daily_poll_sms,
    )
    
    return preferences


@router.delete("/me")
async def delete_account(
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete user account and all associated data.
    
    Note: Vote records (which contain only hashes, not user IDs)
    will remain in the system to maintain polling accuracy,
    but they cannot be linked back to the deleted user.
    """
    repo = UserRepository(db)
    
    # Soft delete or hard delete the user
    # Vote hashes remain (already anonymized - no user_id stored)
    await repo.delete_user(current_user.id)
    
    return {"message": "Account deleted successfully"}
