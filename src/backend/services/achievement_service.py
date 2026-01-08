"""
Achievement awarding service.

Handles checking and awarding achievements when users perform actions.
Now uses Cosmos DB repositories instead of SQLAlchemy.
"""

from typing import Optional

from models.cosmos_documents import AchievementDocument, UserDocument
from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_user_repository import CosmosUserRepository


class AchievementService:
    """Service for checking and awarding achievements using Cosmos DB."""

    def __init__(self):
        self.achievement_repo = CosmosAchievementRepository()
        self.user_repo = CosmosUserRepository()

    async def check_and_award_voting_achievements(self, user: UserDocument) -> list[AchievementDocument]:
        """
        Check and award voting-related achievements.
        Called after a user casts a vote.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Get voting achievements
        voting_achievements = await self.achievement_repo.get_achievements_by_action_type("vote")

        for achievement in voting_achievements:
            if user.votes_cast >= achievement.target_count:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def check_and_award_streak_achievements(self, user: UserDocument) -> list[AchievementDocument]:
        """
        Check and award streak-related achievements.
        Called after streak is updated.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Get streak achievements
        streak_achievements = await self.achievement_repo.get_achievements_by_action_type("streak")

        for achievement in streak_achievements:
            # Use longest_streak so achievement stays even if current streak breaks
            if user.longest_streak >= achievement.target_count:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def check_and_award_sharing_achievements(
        self, user: UserDocument, platform: str
    ) -> tuple[list[AchievementDocument], int]:
        """
        Check and award sharing-related achievements.
        Called after a user shares content.

        Args:
            user: The user who shared
            platform: The platform shared to

        Returns tuple of (newly awarded achievements, points earned from share).
        """
        awarded = []
        points_earned = 0

        # Award base points for sharing (5 points per share)
        share_points = 5
        await self.user_repo.award_points(str(user.id), share_points)
        points_earned += share_points

        # Record the points transaction
        await self.achievement_repo.record_points_transaction(
            user_id=str(user.id),
            action="share",
            points=share_points,
            description=f"Shared content to {platform}",
        )

        # Update total shares on user (we need to refresh user after this)
        user.total_shares = (user.total_shares or 0) + 1
        await self.user_repo.update(user)

        # Check total share achievements
        share_achievements = await self.achievement_repo.get_achievements_by_action_type("share")

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
            platform_achievement = await self.achievement_repo.get_achievement(achievement_id)

            if platform_achievement:
                newly_awarded = await self._try_award_achievement(user, platform_achievement)
                if newly_awarded:
                    awarded.append(platform_achievement)
                    points_earned += platform_achievement.points_reward

        # Check cross-platform champion achievement
        # Need to check if user has earned all platform achievements
        all_platform_ids = list(platform_map.values())
        user_achievements = await self.achievement_repo.get_user_achievements(str(user.id), unlocked_only=True)
        earned_platform_count = sum(1 for ua in user_achievements if ua.achievement_id in all_platform_ids)

        if earned_platform_count >= 6:
            cross_platform_achievement = await self.achievement_repo.get_achievement("share_all_platforms")

            if cross_platform_achievement:
                newly_awarded = await self._try_award_achievement(user, cross_platform_achievement)
                if newly_awarded:
                    awarded.append(cross_platform_achievement)
                    points_earned += cross_platform_achievement.points_reward

        return awarded, points_earned

    async def check_and_award_demographic_achievements(
        self, user: UserDocument, field_updated: str
    ) -> list[AchievementDocument]:
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
            "demo_marital": ["marital_status"],
            "demo_religion": ["religious_affiliation"],
            "demo_ethnicity": ["ethnicity"],
            "demo_income": ["household_income"],
            "demo_parental": ["parental_status"],
            "demo_housing": ["housing_status"],
        }

        for achievement_id, required_fields in demo_map.items():
            # Check if all required fields are filled
            all_filled = all(getattr(user, field, None) for field in required_fields)

            if all_filled:
                achievement = await self.achievement_repo.get_achievement(achievement_id)
                if achievement:
                    newly_awarded = await self._try_award_achievement(user, achievement)
                    if newly_awarded:
                        awarded.append(achievement)

        # Check profile_complete achievement (8+ basic fields)
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
            achievement = await self.achievement_repo.get_achievement("profile_complete")
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        # Check demo_complete_extended achievement (14+ fields)
        extended_count = 0
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
            "marital_status",
            "religious_affiliation",
            "ethnicity",
            "household_income",
            "parental_status",
            "housing_status",
        ]:
            if getattr(user, field, None):
                extended_count += 1

        if extended_count >= 14:
            achievement = await self.achievement_repo.get_achievement("demo_complete_extended")
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded

    async def award_leaderboard_achievement(
        self,
        user: UserDocument,
        rank: int,
        period_type: str,  # "daily", "monthly", "yearly"
        period_key: str,  # e.g., "2025-01-15" or "2025-01" or "2025"
    ) -> Optional[AchievementDocument]:
        """
        Award a leaderboard achievement for a specific period.
        Called by a scheduled job at the end of each period.

        Returns the awarded achievement if successful.
        """
        if rank > 3:
            return None

        achievement_id = f"{period_type}_rank_{rank}"
        achievement = await self.achievement_repo.get_achievement(achievement_id)

        if not achievement:
            return None

        # For repeatable achievements, check if already earned for this period
        existing = await self.achievement_repo.get_user_achievement(str(user.id), achievement_id, period_key)

        if existing and existing.is_unlocked:
            return None  # Already earned for this period

        # Award the achievement with period_key
        await self.achievement_repo.unlock_achievement(str(user.id), achievement_id, period_key=period_key)

        # Award points
        await self._award_points(
            user,
            achievement.points_reward,
            f"Leaderboard achievement: {achievement.name} ({period_key})",
            "leaderboard_achievement",
        )

        return achievement

    async def _try_award_achievement(
        self,
        user: UserDocument,
        achievement: AchievementDocument,
        period_key: Optional[str] = None,
    ) -> bool:
        """
        Try to award an achievement to a user.
        Returns True if newly awarded, False if already had it.
        """
        # Check if user already has this achievement
        existing = await self.achievement_repo.get_user_achievement(str(user.id), achievement.id, period_key)

        if existing and existing.is_unlocked:
            # Already have it
            if not achievement.is_repeatable:
                return False
            # For repeatable, need to check period_key
            if period_key and existing.period_key == period_key:
                return False

        # Award the achievement
        await self.achievement_repo.unlock_achievement(str(user.id), achievement.id, period_key=period_key)

        # Award points
        await self._award_points(
            user,
            achievement.points_reward,
            f"Achievement unlocked: {achievement.name}",
            "achievement",
        )

        return True

    async def _award_points(self, user: UserDocument, points: int, description: str, action: str) -> None:
        """Award points to a user and create a transaction record."""
        # Update user's total points
        await self.user_repo.award_points(str(user.id), points)

        # Create transaction record
        await self.achievement_repo.record_points_transaction(
            user_id=str(user.id),
            action=action,
            points=points,
            description=description,
        )

    async def check_and_award_pulse_achievements(self, user: UserDocument) -> list[AchievementDocument]:
        """
        Check and award pulse poll-related achievements.
        Called after a user votes on a pulse poll.

        Returns list of newly awarded achievements.
        """
        awarded = []
        pulse_votes = user.pulse_polls_voted or 0
        pulse_streak = user.pulse_poll_streak or 0

        # Pulse vote count achievements
        pulse_vote_achievements = [
            ("pulse_first", 1),
            ("pulse_10", 10),
            ("pulse_30", 30),
            ("pulse_100", 100),
            ("pulse_365", 365),
        ]

        for achievement_id, target in pulse_vote_achievements:
            if pulse_votes >= target:
                achievement = await self.achievement_repo.get_achievement(achievement_id)
                if achievement:
                    newly_awarded = await self._try_award_achievement(user, achievement)
                    if newly_awarded:
                        awarded.append(achievement)

        # Pulse streak achievements
        pulse_streak_achievements = [
            ("pulse_streak_7", 7),
            ("pulse_streak_30", 30),
            ("pulse_streak_90", 90),
            ("pulse_streak_365", 365),
        ]

        for achievement_id, target in pulse_streak_achievements:
            if pulse_streak >= target:
                achievement = await self.achievement_repo.get_achievement(achievement_id)
                if achievement:
                    newly_awarded = await self._try_award_achievement(user, achievement)
                    if newly_awarded:
                        awarded.append(achievement)

        return awarded

    async def check_and_award_flash_achievements(self, user: UserDocument) -> list[AchievementDocument]:
        """
        Check and award flash poll-related achievements.
        Called after a user votes on a flash poll.

        Returns list of newly awarded achievements.
        """
        awarded = []
        flash_votes = user.flash_polls_voted or 0

        # Flash vote count achievements
        flash_vote_achievements = [
            ("flash_first", 1),
            ("flash_10", 10),
            ("flash_50", 50),
            ("flash_100", 100),
            ("flash_500", 500),
        ]

        for achievement_id, target in flash_vote_achievements:
            if flash_votes >= target:
                achievement = await self.achievement_repo.get_achievement(achievement_id)
                if achievement:
                    newly_awarded = await self._try_award_achievement(user, achievement)
                    if newly_awarded:
                        awarded.append(achievement)

        # Note: Flash early bird, daily, and weekly achievements require
        # additional tracking (time since poll opened, daily vote count)
        # These would need additional user fields to track properly

        return awarded

    async def check_and_award_verification_achievements(
        self,
        user: UserDocument,
        verification_type: str,  # "email" or "passkey"
    ) -> list[AchievementDocument]:
        """
        Check and award verification-related achievements.
        Called after a user verifies their email or registers a passkey.

        Returns list of newly awarded achievements.
        """
        awarded = []

        # Award specific verification achievement for email
        if verification_type == "email":
            achievement = await self.achievement_repo.get_achievement("email_verified")
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        # Check if fully verified (requires BOTH email verified AND at least one passkey)
        # The user must have verified email AND registered at least one passkey
        has_passkey = len(user.passkeys) > 0 if user.passkeys else False
        if user.email_verified and has_passkey:
            achievement = await self.achievement_repo.get_achievement("fully_verified")
            if achievement:
                newly_awarded = await self._try_award_achievement(user, achievement)
                if newly_awarded:
                    awarded.append(achievement)

        return awarded


async def check_all_achievements_for_user(user: UserDocument) -> list[AchievementDocument]:
    """
    Check and award all applicable achievements for a user.
    Useful for retroactively awarding achievements after system updates.

    Returns list of all newly awarded achievements.
    """
    service = AchievementService()
    awarded = []

    awarded.extend(await service.check_and_award_voting_achievements(user))
    awarded.extend(await service.check_and_award_streak_achievements(user))
    awarded.extend(await service.check_and_award_demographic_achievements(user, ""))

    return awarded
