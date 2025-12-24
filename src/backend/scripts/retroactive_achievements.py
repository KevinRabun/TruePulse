"""
Retroactive achievement awarding script.

Awards achievements to existing users based on their current stats.
Run with: python -m scripts.retroactive_achievements

This script should be run AFTER seed_achievements.py to award
achievements to users who already qualify.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from db.session import async_session_maker
from models.achievement import Achievement, UserAchievement
from models.user import User
from services.achievement_service import AchievementService


async def award_retroactive_achievements():
    """Award achievements to all existing users based on their current stats."""
    async with async_session_maker() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()

        print(f"Found {len(users)} user(s) to process")
        print("=" * 50)

        total_awarded = 0

        for user in users:
            print(f"\nProcessing user: {user.username} (ID: {user.id})")
            print(f"  - Votes cast: {user.votes_cast}")
            print(f"  - Current streak: {user.current_streak}")
            print(f"  - Longest streak: {user.longest_streak}")
            print(f"  - Email verified: {user.email_verified}")
            print(f"  - Total points: {user.total_points}")

            service = AchievementService(db)
            user_awarded = []

            # Check voting achievements
            voting_awarded = await service.check_and_award_voting_achievements(user)
            if voting_awarded:
                user_awarded.extend(voting_awarded)
                print(f"  ✅ Voting achievements: {[a.name for a in voting_awarded]}")

            # Check streak achievements
            streak_awarded = await service.check_and_award_streak_achievements(user)
            if streak_awarded:
                user_awarded.extend(streak_awarded)
                print(f"  ✅ Streak achievements: {[a.name for a in streak_awarded]}")

            # Check demographic/profile achievements
            demo_awarded = await service.check_and_award_demographic_achievements(user, "")
            if demo_awarded:
                user_awarded.extend(demo_awarded)
                print(f"  ✅ Profile achievements: {[a.name for a in demo_awarded]}")

            # Check verification achievements (email verified)
            if user.email_verified:
                verif_awarded = await service.check_and_award_verification_achievements(
                    user, "email"
                )
                if verif_awarded:
                    user_awarded.extend(verif_awarded)
                    print(f"  ✅ Verification achievements: {[a.name for a in verif_awarded]}")

            if user_awarded:
                total_awarded += len(user_awarded)
                print(f"  📊 Total new achievements for {user.username}: {len(user_awarded)}")
            else:
                print(f"  ℹ️  No new achievements to award (may already have them)")

        # Commit all changes
        await db.commit()

        print("\n" + "=" * 50)
        print(f"✅ Done! Awarded {total_awarded} achievement(s) across {len(users)} user(s)")


if __name__ == "__main__":
    asyncio.run(award_retroactive_achievements())
