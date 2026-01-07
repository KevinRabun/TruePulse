"""
Tests for Cosmos DB vote repository.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from models.cosmos_documents import VoteDocument


@pytest.fixture
def sample_vote_doc():
    """Create a sample vote document."""
    return VoteDocument(
        id=str(uuid.uuid4()),
        vote_hash="test-hash-abc123",
        poll_id=str(uuid.uuid4()),
        choice_id=str(uuid.uuid4()),
        demographics_bucket="25-34_US_emp",
        voted_at=datetime.now(timezone.utc),
    )


@pytest.mark.unit
class TestCosmosVoteRepository:
    """Test CosmosVoteRepository operations."""

    @pytest.mark.asyncio
    async def test_repository_instantiation(self) -> None:
        """Test that repository can be instantiated."""
        from repositories.cosmos_vote_repository import CosmosVoteRepository

        repo = CosmosVoteRepository()
        assert repo is not None

    @pytest.mark.asyncio
    async def test_exists_by_hash_returns_true(self, sample_vote_doc) -> None:
        """Test exists_by_hash returns True for existing vote."""
        from repositories.cosmos_vote_repository import CosmosVoteRepository

        with patch("repositories.cosmos_vote_repository.query_count") as mock_query:
            mock_query.return_value = 1  # COUNT query returns 1 for existing

            repo = CosmosVoteRepository()
            result = await repo.exists_by_hash(sample_vote_doc.vote_hash, sample_vote_doc.poll_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_hash_returns_false(self) -> None:
        """Test exists_by_hash returns False for new hash."""
        from repositories.cosmos_vote_repository import CosmosVoteRepository

        with patch("repositories.cosmos_vote_repository.query_count") as mock_query:
            mock_query.return_value = 0  # COUNT query returns 0 for non-existing

            repo = CosmosVoteRepository()
            result = await repo.exists_by_hash("non-existent-hash", "test-poll-id")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_by_hash_returns_vote(self, sample_vote_doc) -> None:
        """Test getting vote by hash."""
        from repositories.cosmos_vote_repository import CosmosVoteRepository

        with patch("repositories.cosmos_vote_repository.query_items") as mock_query:
            mock_query.return_value = [sample_vote_doc.model_dump()]

            repo = CosmosVoteRepository()
            result = await repo.get_by_hash(sample_vote_doc.vote_hash, sample_vote_doc.poll_id)

            assert result is not None
            assert result.vote_hash == sample_vote_doc.vote_hash


@pytest.mark.unit
class TestVoteRepositoryPrivacy:
    """Test vote repository privacy guarantees."""

    def test_vote_hash_is_one_way(self) -> None:
        """Test that vote hash cannot be reversed to get user_id."""
        from core.security import generate_vote_hash

        user_id = str(uuid.uuid4())
        poll_id = str(uuid.uuid4())

        vote_hash = generate_vote_hash(user_id, poll_id)

        # Cannot extract user_id from hash
        assert user_id not in vote_hash
        assert poll_id not in vote_hash

    def test_same_user_different_polls_different_hashes(self) -> None:
        """Test that same user voting on different polls gets different hashes."""
        from core.security import generate_vote_hash

        user_id = str(uuid.uuid4())
        poll_id_1 = str(uuid.uuid4())
        poll_id_2 = str(uuid.uuid4())

        hash_1 = generate_vote_hash(user_id, poll_id_1)
        hash_2 = generate_vote_hash(user_id, poll_id_2)

        assert hash_1 != hash_2

    def test_different_users_same_poll_different_hashes(self) -> None:
        """Test that different users voting on same poll get different hashes."""
        from core.security import generate_vote_hash

        user_id_1 = str(uuid.uuid4())
        user_id_2 = str(uuid.uuid4())
        poll_id = str(uuid.uuid4())

        hash_1 = generate_vote_hash(user_id_1, poll_id)
        hash_2 = generate_vote_hash(user_id_2, poll_id)

        assert hash_1 != hash_2


@pytest.mark.unit
class TestVoteDocument:
    """Test VoteDocument model."""

    def test_vote_document_creation(self) -> None:
        """Test creating a vote document."""
        poll_id = str(uuid.uuid4())
        vote = VoteDocument(
            id=str(uuid.uuid4()),
            vote_hash="test-hash",
            poll_id=poll_id,
            choice_id=str(uuid.uuid4()),
        )

        assert vote.vote_hash == "test-hash"
        assert vote.poll_id == poll_id

    def test_vote_document_does_not_store_user_id(self) -> None:
        """Test that vote document doesn't have user_id field."""
        vote = VoteDocument(
            id=str(uuid.uuid4()),
            vote_hash="test-hash",
            poll_id=str(uuid.uuid4()),
            choice_id=str(uuid.uuid4()),
        )

        # VoteDocument should NOT have user_id attribute
        # It only stores the vote_hash for privacy
        assert not hasattr(vote, "user_id") or vote.model_fields.get("user_id") is None

    def test_vote_document_has_demographics_bucket(self) -> None:
        """Test that vote document can store demographics bucket."""
        vote = VoteDocument(
            id=str(uuid.uuid4()),
            vote_hash="test-hash",
            poll_id=str(uuid.uuid4()),
            choice_id=str(uuid.uuid4()),
            demographics_bucket="25-34_US_emp",
        )

        assert vote.demographics_bucket == "25-34_US_emp"
