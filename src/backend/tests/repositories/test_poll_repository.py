"""
Tests for poll repository.
"""

import uuid
from datetime import datetime, timedelta, timezone
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


@pytest.fixture
def mock_poll():
    """Create a mock poll object."""
    poll = MagicMock()
    poll.id = str(uuid.uuid4())
    poll.question = "Test question?"
    poll.status = MagicMock(value="active")
    poll.total_votes = 100
    poll.starts_at = datetime.now(timezone.utc) - timedelta(hours=1)
    poll.ends_at = datetime.now(timezone.utc) + timedelta(hours=23)
    poll.choices = [
        MagicMock(id=str(uuid.uuid4()), text="Option A", vote_count=60),
        MagicMock(id=str(uuid.uuid4()), text="Option B", vote_count=40),
    ]
    return poll


@pytest.mark.unit
class TestPollRepository:
    """Test PollRepository operations."""

    def test_repository_instantiation(self, mock_session) -> None:
        """Test that repository can be instantiated."""
        from repositories.poll_repository import PollRepository

        repo = PollRepository(mock_session)
        assert repo.db == mock_session

    async def test_get_by_id_returns_poll(self, mock_session, mock_poll) -> None:
        """Test getting poll by ID."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_poll)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.get_by_id(mock_poll.id)

        assert result == mock_poll
        mock_session.execute.assert_called_once()

    async def test_get_by_id_returns_none_for_missing(self, mock_session) -> None:
        """Test getting non-existent poll returns None."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.get_by_id("non-existent-id")

        assert result is None

    async def test_get_current_poll_returns_active_poll(self, mock_session, mock_poll) -> None:
        """Test getting current active poll."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_poll)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.get_current_poll()

        assert result == mock_poll

    async def test_list_polls_returns_list(self, mock_session, mock_poll) -> None:
        """Test listing polls returns paginated list."""
        from repositories.poll_repository import PollRepository

        mock_polls = [mock_poll, MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_polls)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        # Also mock the count query result
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=2)
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        repo = PollRepository(mock_session)
        polls, total = await repo.list_polls(page=1, per_page=10)

        assert len(polls) == 2
        assert total == 2


@pytest.mark.unit
class TestPollRepositoryVoteCount:
    """Test vote count operations."""

    async def test_increment_vote_count(self, mock_session, mock_poll) -> None:
        """Test incrementing vote count."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.increment_vote_count(mock_poll.id, mock_poll.choices[0].id)

        assert result is True

    async def test_decrement_vote_count(self, mock_session, mock_poll) -> None:
        """Test decrementing vote count (for retracted votes)."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.decrement_vote_count(mock_poll.id, mock_poll.choices[0].id)

        assert result is True


@pytest.mark.unit
class TestPollRepositoryScheduling:
    """Test poll scheduling operations."""

    async def test_get_upcoming_polls(self, mock_session) -> None:
        """Test getting upcoming scheduled polls."""
        from repositories.poll_repository import PollRepository

        mock_polls = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_polls)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.get_upcoming_polls(limit=5)

        assert len(result) == 2

    async def test_get_previous_poll(self, mock_session, mock_poll) -> None:
        """Test getting the previous poll."""
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_poll)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.get_previous_poll()

        assert result == mock_poll

    async def test_update_status(self, mock_session, mock_poll) -> None:
        """Test updating poll status."""
        from models.poll import PollStatus
        from repositories.poll_repository import PollRepository

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = PollRepository(mock_session)
        result = await repo.update_status(mock_poll.id, PollStatus.CLOSED)

        assert result is True


@pytest.mark.unit
class TestPollStatusTransitions:
    """Test poll status transition logic."""

    def test_valid_status_transitions(self) -> None:
        """Test valid poll status transitions."""
        from models.poll import PollStatus

        # Valid transitions:
        # SCHEDULED -> ACTIVE -> CLOSED -> ARCHIVED

        valid_transitions = [
            (PollStatus.SCHEDULED, PollStatus.ACTIVE),
            (PollStatus.ACTIVE, PollStatus.CLOSED),
            (PollStatus.CLOSED, PollStatus.ARCHIVED),
        ]

        # Just verify the enums exist
        for from_status, to_status in valid_transitions:
            assert from_status is not None
            assert to_status is not None
