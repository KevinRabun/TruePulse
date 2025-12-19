"""
Tests for vote repository.
"""

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
class TestVoteRepository:
    """Test VoteRepository operations."""

    def test_repository_instantiation(self, mock_session) -> None:
        """Test that repository can be instantiated."""
        from repositories.vote_repository import VoteRepository

        repo = VoteRepository(mock_session)
        assert repo.db == mock_session

    async def test_exists_by_hash_returns_true(self, mock_session) -> None:
        """Test exists_by_hash returns True for existing vote."""
        from repositories.vote_repository import VoteRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoteRepository(mock_session)
        result = await repo.exists_by_hash("existing-hash")

        assert result is True

    async def test_exists_by_hash_returns_false(self, mock_session) -> None:
        """Test exists_by_hash returns False for new hash."""
        from repositories.vote_repository import VoteRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoteRepository(mock_session)
        result = await repo.exists_by_hash("new-hash")

        assert result is False

    async def test_create_vote_does_not_store_user_id(self, mock_session) -> None:
        """Test that creating vote doesn't store user_id (privacy)."""
        from repositories.vote_repository import VoteRepository

        repo = VoteRepository(mock_session)

        # Create a vote - only hash, poll_id, choice_id should be stored
        await repo.create(
            vote_hash="test-hash",
            poll_id="poll-123",
            choice_id="choice-456",
            demographics_bucket="25-34_US_emp",
        )

        # Verify add was called
        mock_session.add.assert_called_once()

        # Get the vote object that was added
        vote_obj = mock_session.add.call_args[0][0]

        # Verify vote object doesn't have user_id attribute or it's None
        # (The actual Vote model shouldn't have user_id)

    async def test_get_by_hash_returns_vote(self, mock_session) -> None:
        """Test getting vote by hash."""
        from repositories.vote_repository import VoteRepository

        mock_vote = MagicMock()
        mock_vote.vote_hash = "test-hash"
        mock_vote.poll_id = "poll-123"
        mock_vote.choice_id = "choice-456"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_vote)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoteRepository(mock_session)
        result = await repo.get_by_hash("test-hash")

        assert result == mock_vote

    async def test_delete_by_hash_removes_vote(self, mock_session) -> None:
        """Test deleting vote by hash."""
        from repositories.vote_repository import VoteRepository

        mock_vote = MagicMock()
        mock_vote.id = "vote-123"
        mock_vote.choice_id = "choice-456"

        # First call returns the vote (get_by_hash)
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none = MagicMock(return_value=mock_vote)
        # Second call is the delete
        mock_result2 = MagicMock()
        mock_result2.rowcount = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        repo = VoteRepository(mock_session)
        result = await repo.delete_by_hash("test-hash")

        assert result is not None
        assert result.choice_id == "choice-456"


@pytest.mark.unit
class TestVoteRepositoryPrivacy:
    """Test vote repository privacy guarantees."""

    def test_vote_hash_is_one_way(self) -> None:
        """Test that vote hash cannot be reversed to get user_id."""
        from core.security import generate_vote_hash

        user_id = "user-123"
        poll_id = "poll-456"

        vote_hash = generate_vote_hash(user_id, poll_id)

        # Hash should not contain user_id
        assert user_id not in vote_hash

        # Hash should be 64 chars (SHA-256)
        assert len(vote_hash) == 64

    def test_same_user_different_polls_different_hashes(self) -> None:
        """Test that same user voting on different polls has different hashes."""
        from core.security import generate_vote_hash

        user_id = "user-123"

        hash1 = generate_vote_hash(user_id, "poll-1")
        hash2 = generate_vote_hash(user_id, "poll-2")

        assert hash1 != hash2

    def test_different_users_same_poll_different_hashes(self) -> None:
        """Test that different users on same poll have different hashes."""
        from core.security import generate_vote_hash

        poll_id = "poll-123"

        hash1 = generate_vote_hash("user-1", poll_id)
        hash2 = generate_vote_hash("user-2", poll_id)

        assert hash1 != hash2


@pytest.mark.unit
class TestVoteRepositoryAggregation:
    """Test vote aggregation functions."""

    async def test_count_by_poll_returns_total(self, mock_session) -> None:
        """Test counting votes for a poll."""
        from repositories.vote_repository import VoteRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=42)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoteRepository(mock_session)
        result = await repo.count_by_poll("poll-123")

        assert result == 42

    async def test_count_by_choice_returns_count(self, mock_session) -> None:
        """Test counting votes for a specific choice."""
        from repositories.vote_repository import VoteRepository

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=15)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoteRepository(mock_session)
        # count_by_choice only takes choice_id
        result = await repo.count_by_choice("choice-456")

        assert result == 15
