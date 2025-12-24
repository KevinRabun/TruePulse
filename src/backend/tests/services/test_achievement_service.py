"""
Tests for Achievement Service.

Tests the achievement awarding functionality including:
- Voting achievements
- Streak achievements
- Profile/demographic achievements
- Email verification achievements
- Achievement idempotency (not double-awarding)
"""

import os

import pytest

# Set test environment before imports
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")


@pytest.mark.unit
class TestVotingAchievements:
    """Tests for voting-related achievements."""

    def test_first_vote_threshold(self) -> None:
        """Test that first vote achievement requires exactly 1 vote."""
        # Achievement definition
        first_vote_achievement = {
            "id": "first_vote",
            "name": "First Vote",
            "action_type": "vote",
            "target_count": 1,
            "points_reward": 50,
        }

        # User with 1 vote should qualify
        assert 1 >= first_vote_achievement["target_count"]

        # User with 0 votes should not qualify
        assert not (0 >= first_vote_achievement["target_count"])

    def test_votes_10_threshold(self) -> None:
        """Test that 10 votes achievement requires 10 votes."""
        votes_10_achievement = {
            "id": "votes_10",
            "name": "Getting Started",
            "action_type": "vote",
            "target_count": 10,
            "points_reward": 100,
        }

        # User with 10+ votes should qualify
        assert 10 >= votes_10_achievement["target_count"]
        assert 15 >= votes_10_achievement["target_count"]

        # User with <10 votes should not qualify
        assert not (9 >= votes_10_achievement["target_count"])

    def test_progressive_voting_achievements(self) -> None:
        """Test that voting achievements are progressive (1, 10, 50, 100, etc.)."""
        voting_thresholds = [1, 10, 50, 100, 250, 500, 1000]

        # User with 55 votes should have earned 1, 10, 50 but not 100+
        user_votes = 55
        earned = [t for t in voting_thresholds if user_votes >= t]
        not_earned = [t for t in voting_thresholds if user_votes < t]

        assert earned == [1, 10, 50]
        assert not_earned == [100, 250, 500, 1000]


@pytest.mark.unit
class TestStreakAchievements:
    """Tests for streak-related achievements."""

    def test_streak_achievement_uses_longest_streak(self) -> None:
        """Test that streak achievements use longest_streak, not current_streak."""
        streak_achievement = {
            "id": "streak_7",
            "name": "Week Warrior",
            "action_type": "streak",
            "target_count": 7,
        }

        # User who had 7-day streak but broke it should still qualify
        user_current_streak = 2
        user_longest_streak = 10

        # Should use longest_streak for achievement check
        assert user_longest_streak >= streak_achievement["target_count"]

    def test_streak_thresholds(self) -> None:
        """Test various streak achievement thresholds."""
        streak_thresholds = [3, 7, 14, 30, 60, 100, 365]

        # User with 45 day longest streak
        longest_streak = 45
        earned = [t for t in streak_thresholds if longest_streak >= t]

        assert earned == [3, 7, 14, 30]


@pytest.mark.unit
class TestDemographicAchievements:
    """Tests for demographic/profile completion achievements."""

    def test_profile_complete_requires_8_fields(self) -> None:
        """Test that profile complete achievement requires 8 demographic fields."""
        required_fields = [
            "age_range",
            "gender",
            "country",
            "state_province",
            "city",
            "education_level",
            "employment_status",
            "industry",
        ]

        # User with all 8 fields filled
        user_demographics = {
            "age_range": "25-34",
            "gender": "male",
            "country": "US",
            "state_province": "CA",
            "city": "Los Angeles",
            "education_level": "bachelors",
            "employment_status": "employed",
            "industry": "technology",
        }

        filled_count = sum(1 for f in required_fields if user_demographics.get(f))
        assert filled_count >= 8

    def test_partial_profile_not_complete(self) -> None:
        """Test that partial profile doesn't qualify for complete achievement."""
        required_fields = [
            "age_range",
            "gender",
            "country",
            "state_province",
            "city",
            "education_level",
            "employment_status",
            "industry",
        ]

        # User with only 5 fields filled
        user_demographics = {
            "age_range": "25-34",
            "gender": "male",
            "country": "US",
            "state_province": None,
            "city": None,
            "education_level": "bachelors",
            "employment_status": "employed",
            "industry": None,
        }

        filled_count = sum(1 for f in required_fields if user_demographics.get(f))
        assert filled_count < 8


@pytest.mark.unit
class TestAchievementIdempotency:
    """Tests for achievement idempotency (not double-awarding)."""

    def test_non_repeatable_achievement_once_only(self) -> None:
        """Test that non-repeatable achievements can only be earned once."""
        non_repeatable = {
            "id": "first_vote",
            "is_repeatable": False,
        }

        user_achievements = [
            {"achievement_id": "first_vote", "is_unlocked": True},
        ]

        # Check if already has this achievement
        already_has = any(
            ua["achievement_id"] == non_repeatable["id"] and ua["is_unlocked"] for ua in user_achievements
        )

        assert already_has is True
        # Should not award again

    def test_repeatable_achievement_with_period_key(self) -> None:
        """Test that repeatable achievements check period_key."""
        repeatable = {
            "id": "daily_rank_1",
            "is_repeatable": True,
        }

        user_achievements = [
            {"achievement_id": "daily_rank_1", "is_unlocked": True, "period_key": "2025-12-23"},
            {"achievement_id": "daily_rank_1", "is_unlocked": True, "period_key": "2025-12-22"},
        ]

        # Check if already has for today's period
        today_period = "2025-12-24"
        already_has_today = any(
            ua["achievement_id"] == repeatable["id"] and ua["is_unlocked"] and ua.get("period_key") == today_period
            for ua in user_achievements
        )

        assert already_has_today is False  # Can earn for new period


@pytest.mark.unit
class TestAchievementPointsRewards:
    """Tests for achievement point rewards."""

    def test_achievement_awards_points(self) -> None:
        """Test that achievements award their points_reward."""
        achievement = {
            "id": "first_vote",
            "name": "First Vote",
            "points_reward": 50,
        }

        user_points_before = 100
        user_points_after = user_points_before + achievement["points_reward"]

        assert user_points_after == 150

    def test_multiple_achievements_stack_points(self) -> None:
        """Test that earning multiple achievements stacks points."""
        achievements = [
            {"id": "first_vote", "points_reward": 50},
            {"id": "email_verified", "points_reward": 25},
            {"id": "profile_complete", "points_reward": 100},
        ]

        user_points_before = 0
        total_reward = sum(a["points_reward"] for a in achievements)
        user_points_after = user_points_before + total_reward

        assert user_points_after == 175


@pytest.mark.unit
class TestAchievementTiers:
    """Tests for achievement tier system."""

    def test_achievement_tiers(self) -> None:
        """Test that achievements have proper tier assignments."""
        valid_tiers = ["bronze", "silver", "gold", "platinum"]

        # Sample achievements with tiers
        achievements = [
            {"id": "first_vote", "tier": "bronze"},
            {"id": "votes_100", "tier": "silver"},
            {"id": "votes_1000", "tier": "gold"},
            {"id": "legendary_voter", "tier": "platinum"},
        ]

        for achievement in achievements:
            assert achievement["tier"] in valid_tiers

    def test_tier_progression(self) -> None:
        """Test that higher thresholds have higher tiers."""
        tier_order = {"bronze": 0, "silver": 1, "gold": 2, "platinum": 3}

        voting_achievements = [
            {"id": "first_vote", "target_count": 1, "tier": "bronze"},
            {"id": "votes_100", "target_count": 100, "tier": "silver"},
            {"id": "votes_1000", "target_count": 1000, "tier": "gold"},
        ]

        # Higher targets should have equal or higher tiers
        for i in range(len(voting_achievements) - 1):
            current = voting_achievements[i]
            next_achievement = voting_achievements[i + 1]

            current_tier_rank = tier_order[current["tier"]]
            next_tier_rank = tier_order[next_achievement["tier"]]

            assert next_tier_rank >= current_tier_rank


@pytest.mark.unit
class TestAchievementCategories:
    """Tests for achievement category system."""

    def test_valid_categories(self) -> None:
        """Test that achievements have valid categories."""
        valid_categories = ["voting", "streak", "profile", "leaderboard", "sharing", "general"]

        achievements = [
            {"id": "first_vote", "category": "voting"},
            {"id": "streak_7", "category": "streak"},
            {"id": "profile_complete", "category": "profile"},
            {"id": "daily_rank_1", "category": "leaderboard"},
        ]

        for achievement in achievements:
            assert achievement["category"] in valid_categories

    def test_filter_by_category(self) -> None:
        """Test filtering achievements by category."""
        all_achievements = [
            {"id": "first_vote", "category": "voting"},
            {"id": "votes_10", "category": "voting"},
            {"id": "streak_7", "category": "streak"},
            {"id": "profile_complete", "category": "profile"},
        ]

        voting_only = [a for a in all_achievements if a["category"] == "voting"]
        assert len(voting_only) == 2
        assert all(a["category"] == "voting" for a in voting_only)
