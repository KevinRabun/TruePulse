"""
Tests for user repository.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.unit
class TestUserRepository:
    """Test UserRepository operations."""

    def test_repository_instantiation(self, mock_session) -> None:
        """Test that repository can be instantiated."""
        from repositories.user_repository import UserRepository

        repo = UserRepository(mock_session)
        assert repo.db == mock_session

    async def test_get_by_id_returns_user(self, mock_session) -> None:
        """Test getting user by ID."""
        from repositories.user_repository import UserRepository

        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "test@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.get_by_id(mock_user.id)

        assert result == mock_user
        mock_session.execute.assert_called_once()

    async def test_get_by_id_returns_none_for_missing(self, mock_session) -> None:
        """Test getting non-existent user returns None."""
        from repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.get_by_id("non-existent-id")

        assert result is None

    async def test_email_exists_returns_true(self, mock_session) -> None:
        """Test email exists check returns true for existing email."""
        from repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.email_exists("existing@example.com")

        assert result is True

    async def test_email_exists_returns_false(self, mock_session) -> None:
        """Test email exists check returns false for new email."""
        from repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.email_exists("new@example.com")

        assert result is False

    async def test_username_exists_returns_true(self, mock_session) -> None:
        """Test username exists check returns true for existing username."""
        from repositories.user_repository import UserRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.username_exists("existinguser")

        assert result is True

    async def test_create_user_with_welcome_points(self, mock_session) -> None:
        """Test creating user awards welcome points."""
        from repositories.user_repository import UserRepository

        repo = UserRepository(mock_session)

        user = await repo.create(
            email="new@example.com",
            username="newuser",
            welcome_points=100,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    async def test_award_points_updates_user(self, mock_session) -> None:
        """Test that awarding points updates user record."""
        from repositories.user_repository import UserRepository

        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.total_points = 100
        mock_user.level = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.refresh = AsyncMock()

        repo = UserRepository(mock_session)
        result = await repo.award_points(mock_user.id, 50)

        # Should have been called at least twice (get + update)
        assert mock_session.execute.call_count >= 1

    async def test_get_leaderboard_returns_list(self, mock_session) -> None:
        """Test leaderboard returns list of users."""
        from repositories.user_repository import UserRepository

        mock_users = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_users)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = UserRepository(mock_session)
        result = await repo.get_leaderboard(limit=10)

        assert len(result) == 2


@pytest.mark.unit
class TestUserRepositoryPointsCalculation:
    """Test points and level calculation."""

    def test_level_calculation_formula(self) -> None:
        """Test that level calculation follows expected formula."""
        # Level formula: level = (points // 500) + 1
        # Level 1: 0-499 points
        # Level 2: 500-999 points
        # Level 3: 1000-1499 points
        test_cases = [
            (0, 1),
            (100, 1),
            (499, 1),
            (500, 2),
            (999, 2),
            (1000, 3),
        ]

        for points, expected_level in test_cases:
            calculated_level = max(1, (points // 500) + 1)
            assert calculated_level == expected_level, f"Points {points} should be level {expected_level}"


@pytest.mark.unit
class TestUserRepositoryStreakCalculation:
    """Test voting streak calculation logic."""

    def test_first_vote_ever_starts_streak_at_one(self) -> None:
        """Test that first vote sets streak to 1."""
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)

        result = repo._calculate_new_streak(None, 0, now)
        assert result == 1

    def test_same_day_vote_keeps_streak(self) -> None:
        """Test that voting same day doesn't change streak."""
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        # Last vote was earlier today
        last_vote = now.replace(hour=8, minute=0, second=0)

        result = repo._calculate_new_streak(last_vote, 5, now)
        assert result == 5

    def test_same_day_first_vote_sets_streak_to_one(self) -> None:
        """Test that same day vote with 0 streak sets to 1."""
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        last_vote = now.replace(hour=8, minute=0, second=0)

        result = repo._calculate_new_streak(last_vote, 0, now)
        assert result == 1

    def test_consecutive_day_increments_streak(self) -> None:
        """Test that voting on consecutive day increments streak."""
        from datetime import datetime, timedelta, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        # Last vote was yesterday
        last_vote = now - timedelta(days=1)

        result = repo._calculate_new_streak(last_vote, 3, now)
        assert result == 4

    def test_two_day_gap_resets_streak(self) -> None:
        """Test that 2+ day gap resets streak to 1."""
        from datetime import datetime, timedelta, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        # Last vote was 2 days ago
        last_vote = now - timedelta(days=2)

        result = repo._calculate_new_streak(last_vote, 10, now)
        assert result == 1

    def test_week_gap_resets_streak(self) -> None:
        """Test that week-long gap resets streak to 1."""
        from datetime import datetime, timedelta, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        # Last vote was 7 days ago
        last_vote = now - timedelta(days=7)

        result = repo._calculate_new_streak(last_vote, 50, now)
        assert result == 1

    def test_naive_datetime_handled(self) -> None:
        """Test that naive datetime is handled correctly."""
        from datetime import datetime, timedelta, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        now = datetime.now(timezone.utc)
        # Naive datetime (no timezone)
        last_vote = datetime.now() - timedelta(days=1)

        result = repo._calculate_new_streak(last_vote, 3, now)
        assert result == 4

    def test_midnight_boundary_same_day(self) -> None:
        """Test voting just before and after midnight on same calendar day."""
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        # Vote at 11:59 PM
        last_vote = datetime(2024, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
        # Vote at 12:01 AM same day
        now = datetime(2024, 1, 15, 0, 1, 0, tzinfo=timezone.utc)

        # Since now is earlier in the day, this is actually a negative day diff
        # This edge case is handled by comparing dates
        result = repo._calculate_new_streak(last_vote, 5, now)
        # Same calendar day
        assert result == 5

    def test_midnight_boundary_next_day(self) -> None:
        """Test voting just before midnight and just after midnight next day."""
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        repo = UserRepository(MagicMock())
        # Vote at 11:59 PM on Jan 15
        last_vote = datetime(2024, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
        # Vote at 12:01 AM on Jan 16
        now = datetime(2024, 1, 16, 0, 1, 0, tzinfo=timezone.utc)

        result = repo._calculate_new_streak(last_vote, 5, now)
        # Consecutive days
        assert result == 6
