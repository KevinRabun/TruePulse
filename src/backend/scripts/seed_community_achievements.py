"""
Seed script for community achievements.

Run with: python -m scripts.seed_community_achievements
"""

import asyncio

from sqlalchemy import select

from db.session import async_session_maker
from models.achievement import CommunityAchievement

COMMUNITY_ACHIEVEMENTS = [
    # === DAILY VOTE MILESTONES ===
    {
        "id": "community_daily_1k",
        "name": "1K Voices Day",
        "description": "Be part of a day where 1,000 votes are cast",
        "icon": "🎯",
        "badge_icon": "🥉",
        "goal_type": "daily_votes",
        "target_count": 1000,
        "time_window_hours": 24,
        "points_reward": 25,
        "bonus_multiplier": 1.0,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "bronze",
        "category": "community",
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "community_daily_5k",
        "name": "5K Voices Day",
        "description": "Be part of a day where 5,000 votes are cast",
        "icon": "🎪",
        "badge_icon": "🥈",
        "goal_type": "daily_votes",
        "target_count": 5000,
        "time_window_hours": 24,
        "points_reward": 50,
        "bonus_multiplier": 1.1,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "silver",
        "category": "community",
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "community_daily_10k",
        "name": "10K Voices Day",
        "description": "Be part of a day where 10,000 votes are cast - democracy in action!",
        "icon": "🏟️",
        "badge_icon": "🥇",
        "goal_type": "daily_votes",
        "target_count": 10000,
        "time_window_hours": 24,
        "points_reward": 100,
        "bonus_multiplier": 1.25,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "gold",
        "category": "community",
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": "community_daily_50k",
        "name": "50K Voices Day",
        "description": "Be part of an extraordinary day with 50,000 votes!",
        "icon": "🌟",
        "badge_icon": "💫",
        "goal_type": "daily_votes",
        "target_count": 50000,
        "time_window_hours": 24,
        "points_reward": 250,
        "bonus_multiplier": 1.5,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "platinum",
        "category": "community",
        "sort_order": 4,
        "is_active": True,
    },
    # === SINGLE POLL MILESTONES ===
    {
        "id": "community_poll_500",
        "name": "Poll Surge",
        "description": "Participate in a single poll that reaches 500 votes",
        "icon": "📊",
        "badge_icon": "📈",
        "goal_type": "poll_votes",
        "target_count": 500,
        "time_window_hours": None,
        "points_reward": 30,
        "bonus_multiplier": 1.0,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "bronze",
        "category": "community",
        "sort_order": 10,
        "is_active": True,
    },
    {
        "id": "community_poll_1k",
        "name": "Poll Phenomenon",
        "description": "Participate in a single poll that reaches 1,000 votes",
        "icon": "🔥",
        "badge_icon": "🎖️",
        "goal_type": "poll_votes",
        "target_count": 1000,
        "time_window_hours": None,
        "points_reward": 75,
        "bonus_multiplier": 1.15,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "silver",
        "category": "community",
        "sort_order": 11,
        "is_active": True,
    },
    {
        "id": "community_poll_5k",
        "name": "Viral Poll",
        "description": "Participate in a poll that goes viral with 5,000 votes!",
        "icon": "🚀",
        "badge_icon": "🏅",
        "goal_type": "poll_votes",
        "target_count": 5000,
        "time_window_hours": None,
        "points_reward": 200,
        "bonus_multiplier": 1.3,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "gold",
        "category": "community",
        "sort_order": 12,
        "is_active": True,
    },
    # === FLASH POLL COMMUNITY ACHIEVEMENTS ===
    {
        "id": "community_flash_100",
        "name": "Flash Mob",
        "description": "Be part of a Flash Poll that reaches 100 votes in under an hour",
        "icon": "⚡",
        "badge_icon": "⚡",
        "goal_type": "flash_poll_votes",
        "target_count": 100,
        "time_window_hours": 1,
        "points_reward": 40,
        "bonus_multiplier": 1.0,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "bronze",
        "category": "community",
        "sort_order": 20,
        "is_active": True,
    },
    {
        "id": "community_flash_500",
        "name": "Lightning Strike",
        "description": "Be part of a Flash Poll that reaches 500 votes in under an hour",
        "icon": "🌩️",
        "badge_icon": "🌩️",
        "goal_type": "flash_poll_votes",
        "target_count": 500,
        "time_window_hours": 1,
        "points_reward": 100,
        "bonus_multiplier": 1.2,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "silver",
        "category": "community",
        "sort_order": 21,
        "is_active": True,
    },
    {
        "id": "community_flash_1k",
        "name": "Thunder Clap",
        "description": "Be part of a Flash Poll that reaches 1,000 votes in under an hour - incredible engagement!",
        "icon": "⛈️",
        "badge_icon": "⛈️",
        "goal_type": "flash_poll_votes",
        "target_count": 1000,
        "time_window_hours": 1,
        "points_reward": 250,
        "bonus_multiplier": 1.5,
        "is_recurring": True,
        "cooldown_hours": 1,
        "tier": "gold",
        "category": "community",
        "sort_order": 22,
        "is_active": True,
    },
    # === PULSE POLL COMMUNITY ACHIEVEMENTS ===
    {
        "id": "community_pulse_1k",
        "name": "Pulse Power",
        "description": "Be part of a Pulse Poll that reaches 1,000 votes",
        "icon": "💓",
        "badge_icon": "💓",
        "goal_type": "pulse_poll_votes",
        "target_count": 1000,
        "time_window_hours": 12,
        "points_reward": 50,
        "bonus_multiplier": 1.0,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "bronze",
        "category": "community",
        "sort_order": 30,
        "is_active": True,
    },
    {
        "id": "community_pulse_5k",
        "name": "Pulse Wave",
        "description": "Be part of a Pulse Poll that reaches 5,000 votes",
        "icon": "💗",
        "badge_icon": "💗",
        "goal_type": "pulse_poll_votes",
        "target_count": 5000,
        "time_window_hours": 12,
        "points_reward": 150,
        "bonus_multiplier": 1.2,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "silver",
        "category": "community",
        "sort_order": 31,
        "is_active": True,
    },
    {
        "id": "community_pulse_10k",
        "name": "Pulse Tsunami",
        "description": "Be part of a Pulse Poll that reaches 10,000 votes - the nation speaks!",
        "icon": "💖",
        "badge_icon": "💖",
        "goal_type": "pulse_poll_votes",
        "target_count": 10000,
        "time_window_hours": 12,
        "points_reward": 300,
        "bonus_multiplier": 1.5,
        "is_recurring": True,
        "cooldown_hours": 24,
        "tier": "gold",
        "category": "community",
        "sort_order": 32,
        "is_active": True,
    },
    # === PLATFORM MILESTONES (One-time) ===
    {
        "id": "community_platform_100k",
        "name": "100K Club",
        "description": "Be an active voter when the platform reaches 100,000 total votes",
        "icon": "🎊",
        "badge_icon": "🎊",
        "goal_type": "platform_total_votes",
        "target_count": 100000,
        "time_window_hours": None,
        "points_reward": 500,
        "bonus_multiplier": 1.0,
        "is_recurring": False,
        "cooldown_hours": None,
        "tier": "gold",
        "category": "milestone",
        "sort_order": 40,
        "is_active": True,
    },
    {
        "id": "community_platform_1m",
        "name": "Million Voices",
        "description": "Be an active voter when the platform reaches 1,000,000 total votes",
        "icon": "🎆",
        "badge_icon": "🎆",
        "goal_type": "platform_total_votes",
        "target_count": 1000000,
        "time_window_hours": None,
        "points_reward": 1000,
        "bonus_multiplier": 1.0,
        "is_recurring": False,
        "cooldown_hours": None,
        "tier": "platinum",
        "category": "milestone",
        "sort_order": 41,
        "is_active": True,
    },
    # === SPECIAL EVENTS ===
    {
        "id": "community_election_day",
        "name": "Election Day Participant",
        "description": "Vote on Election Day when participation peaks",
        "icon": "🗳️",
        "badge_icon": "🇺🇸",
        "goal_type": "special_event",
        "target_count": 1,
        "time_window_hours": 24,
        "points_reward": 200,
        "bonus_multiplier": 2.0,
        "is_recurring": True,
        "cooldown_hours": 8760,  # Once per year
        "tier": "platinum",
        "category": "special",
        "sort_order": 50,
        "is_active": True,
    },
    {
        "id": "community_new_year",
        "name": "New Year Voter",
        "description": "Cast a vote on New Year's Day",
        "icon": "🎉",
        "badge_icon": "🎉",
        "goal_type": "special_event",
        "target_count": 1,
        "time_window_hours": 24,
        "points_reward": 100,
        "bonus_multiplier": 1.5,
        "is_recurring": True,
        "cooldown_hours": 8760,  # Once per year
        "tier": "gold",
        "category": "special",
        "sort_order": 51,
        "is_active": True,
    },
]


async def seed_community_achievements():
    """Seed community achievements into the database."""
    async with async_session_maker() as session:
        for achievement_data in COMMUNITY_ACHIEVEMENTS:
            # Check if achievement already exists
            result = await session.execute(
                select(CommunityAchievement).where(
                    CommunityAchievement.id == achievement_data["id"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing achievement
                for key, value in achievement_data.items():
                    setattr(existing, key, value)
                print(f"Updated community achievement: {achievement_data['id']}")
            else:
                # Create new achievement
                achievement = CommunityAchievement(**achievement_data)
                session.add(achievement)
                print(f"Created community achievement: {achievement_data['id']}")

        await session.commit()
        print(
            f"\nSeeded {len(COMMUNITY_ACHIEVEMENTS)} community achievements successfully!"
        )


if __name__ == "__main__":
    asyncio.run(seed_community_achievements())
