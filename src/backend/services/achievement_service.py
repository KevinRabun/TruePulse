"""
Achievement awarding service.

Handles checking and awarding achievements when users perform actions.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.achievement import Achievement, PointsTransaction, UserAchievement
from models.user import User


class AchievementService:
    """Service for checking and awarding achievements."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_award_voting_achievements(
        self, user: User
    ) -> list[Achievement]:
        """
        Check and award voting-related achievements.
        Called after a user casts a vote.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Get voting achievements
        result = await self.db.execute(
            select(Achievement).where(Achievement.action_type == "vote")
        )
        voting_achievements = result.scalars().all()

        for achievement in voting_achievements:
            if user.votes_cast >= achievement.target_count:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def check_and_award_streak_achievements(
        self, user: User
    ) -> list[Achievement]:
        """
        Check and award streak-related achievements.
        Called after streak is updated.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Get streak achievements
        result = await self.db.execute(
            select(Achievement).where(Achievement.action_type == "streak")
        )
        streak_achievements = result.scalars().all()

        for achievement in streak_achievements:
            # Use longest_streak so achievement stays even if current streak breaks
            if user.longest_streak >= achievement.target_count:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def check_and_award_sharing_achievements(
        self, user: User, platform: str
    ) -> tuple[list[Achievement], int]:
        """
        Check and award sharing-related achievements.
        Called after a user shares content.

        Args:
            user: The user who shared
            platform: The platform shared to (twitter, facebook, linkedin, reddit, whatsapp, telegram, copy, native)

        Returns tuple of (newly awarded achievements, points earned from share).
        """
        awarded = []
        points_earned = 0

        # Award base points for sharing (5 points per share)
        share_points = 5
        user.total_points += share_points
        points_earned += share_points

        # Create transaction for share points
        transaction = PointsTransaction(
            id=str(uuid4()),
            user_id=str(user.id),
            action="share",
            points=share_points,
            description=f"Shared content to {platform}",
        )
        self.db.add(transaction)

        # Increment total shares
        user.total_shares += 1

        # Check total share achievements (first, 10th, 50th, 100th)
        result = await self.db.execute(
            select(Achievement).where(Achievement.action_type == "share")
        )
        share_achievements = result.scalars().all()

        for achievement in share_achievements:
            if user.total_shares >= achievement.target_count:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)
                    points_earned += achievement.points_reward

        # Check platform-specific achievements
        platform_map = {
            "twitter": "share_twitter",
            "facebook": "share_facebook",
            "linkedin": "share_linkedin",
            "reddit": "share_reddit",
            "whatsapp": "share_whatsapp",
            "telegram": "share_telegram",
        }

        if platform in platform_map:
            achievement_id = platform_map[platform]
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == achievement_id)
            )
            achievement = result.scalar_one_or_none()

            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)
                    points_earned += achievement.points_reward

        # Check cross-platform champion achievement
        # Need to check if user has earned all platform achievements
        all_platform_ids = list(platform_map.values())
        result = await self.db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == str(user.id),
                UserAchievement.achievement_id.in_(all_platform_ids),
                UserAchievement.is_unlocked == True,
            )
        )
        earned_platform_achievements = result.scalars().all()

        if len(earned_platform_achievements) >= 6:
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == "share_all_platforms")
            )
            cross_platform_achievement = result.scalar_one_or_none()

            if cross_platform_achievement:
                newly_awarded = await self._try_award_achievement(
                    user, cross_platform_achievement
                )
                if newly_awarded:
                    awarded.append(cross_platform_achievement)
                    points_earned += cross_platform_achievement.points_reward

        return awarded, points_earned

    async def check_and_award_demographic_achievements(
        self, user: User, field_updated: str
    ) -> list[Achievement]:
        """
        Check and award demographic-related achievements.
        Called after a user updates their profile demographics.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Map of achievement_id to required field(s)
        demo_map = {
            "demo_age": ["age_range"],
            "demo_gender": ["gender"],
            "demo_location": ["country"],
            "demo_geo_detailed": ["state_province", "city"],
            "demo_education": ["education_level"],
            "demo_employment": ["employment_status"],
            "demo_political": ["political_leaning"],
        }

        for achievement_id, required_fields in demo_map.items():
            # Check if all required fields are filled
            all_filled = all(getattr(user, field, None) for field in required_fields)

            if all_filled:
                # Get the achievement
                result = await self.db.execute(
                    select(Achievement).where(Achievement.id == achievement_id)
                )
                achievement = result.scalar_one_or_none()

                if achievement:
                    newly_awarded = await self._try_award_achievement(user, achievement)
                    if newly_awarded:
                        awarded.append(achievement)

        # Check profile_complete achievement
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

        if demo_count >= 8:
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == "profile_complete")
            )
            achievement = result.scalar_one_or_none()
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def award_leaderboard_achievement(
        self,
        user: User,
        rank: int,
        period_type: str,  # "daily", "monthly", "yearly"
        period_key: str,  # e.g., "2025-01-15" or "2025-01" or "2025"
    ) -> Optional[Achievement]:
        """
        Award a leaderboard achievement for a specific period.
        Called by a scheduled job at the end of each period.

        Returns the awarded achievement if successful.
        """
        if rank > 3:
            return None

        achievement_id = f"{period_type}_rank_{rank}"

        result = await self.db.execute(
            select(Achievement).where(Achievement.id == achievement_id)
        )
        achievement = result.scalar_one_or_none()

        if not achievement:
            return None

        # For repeatable achievements, check if already earned for this period
        existing = await self.db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == str(user.id),
                UserAchievement.achievement_id == achievement_id,
                UserAchievement.period_key == period_key,
            )
        )

        if existing.scalar_one_or_none():
            return None  # Already earned for this period

        # Award the achievement
        user_achievement = UserAchievement(
            id=str(uuid4()),
            user_id=str(user.id),
            achievement_id=achievement_id,
            progress=1,
            is_unlocked=True,
            period_key=period_key,
            unlocked_at=datetime.now(timezone.utc),
        )
        self.db.add(user_achievement)

        # Award points
        await self._award_points(
            user,
            achievement.points_reward,
            f"Leaderboard achievement: {achievement.name} ({period_key})",
            "leaderboard_achievement",
        )

        return achievement

    async def _try_award_achievement(
        self, user: User, achievement: Achievement, period_key: Optional[str] = None
    ) -> bool:
        """
        Try to award an achievement to a user.
        Returns True if newly awarded, False if already had it.
        """
        # Check if user already has this achievement
        query = select(UserAchievement).where(
            UserAchievement.user_id == str(user.id),
            UserAchievement.achievement_id == achievement.id,
            UserAchievement.is_unlocked == True,
        )

        if not achievement.is_repeatable:
            # For non-repeatable, just check if exists
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                return False
        else:
            # For repeatable, check if exists for this period
            if period_key:
                query = query.where(UserAchievement.period_key == period_key)
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                return False

        # Award the achievement
        user_achievement = UserAchievement(
            id=str(uuid4()),
            user_id=str(user.id),
            achievement_id=achievement.id,
            progress=achievement.target_count,
            is_unlocked=True,
            period_key=period_key,
            unlocked_at=datetime.now(timezone.utc),
        )
        self.db.add(user_achievement)

        # Award points
        await self._award_points(
            user,
            achievement.points_reward,
            f"Achievement unlocked: {achievement.name}",
            "achievement",
        )

        return True

    async def _award_points(
        self, user: User, points: int, description: str, action: str
    ) -> None:
        """Award points to a user and create a transaction record."""
        # Update user's total points
        user.total_points += points

        # Create transaction record
        transaction = PointsTransaction(
            id=str(uuid4()),
            user_id=str(user.id),
            action=action,
            points=points,
            description=description,
        )
        self.db.add(transaction)

    async def check_and_award_verification_achievements(
        self,
        user: User,
        verification_type: str,  # "email" or "phone"
    ) -> list[Achievement]:
        """
        Check and award verification-related achievements.
        Called after a user verifies their email or phone.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Award specific verification achievement
        if verification_type == "email":
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == "email_verified")
            )
            achievement = result.scalar_one_or_none()
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        elif verification_type == "phone":
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == "phone_verified")
            )
            achievement = result.scalar_one_or_none()
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        # Check if fully verified (both email and phone)
        if user.email_verified and user.phone_verified:
            result = await self.db.execute(
                select(Achievement).where(Achievement.id == "fully_verified")
            )
            achievement = result.scalar_one_or_none()
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded


async def check_all_achievements_for_user(
    db: AsyncSession, user: User
) -> list[Achievement]:
    """
    Check and award all applicable achievements for a user.
    Useful for retroactively awarding achievements after system updates.

    Returns list of all newly awarded achievements.
    """
    service = AchievementService(db)
    awarded = []

    awarded.extend(await service.check_and_award_voting_achievements(user))
    awarded.extend(await service.check_and_award_streak_achievements(user))
    awarded.extend(await service.check_and_award_demographic_achievements(user, ""))

    return awarded
