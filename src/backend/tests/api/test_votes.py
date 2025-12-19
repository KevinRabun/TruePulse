"""
Tests for vote API endpoints.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create mock auth headers for testing."""
    return {"Authorization": "Bearer mock-test-token"}


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_verified = True
    user.total_points = 100
    user.level = 1
    user.votes_cast = 5
    user.current_streak = 3
    user.longest_streak = 7
    user.hashed_password = "hashed"
    return user


@pytest.fixture
def mock_poll():
    """Create a mock poll for testing."""
    poll = MagicMock()
    poll.id = str(uuid.uuid4())
    poll.question = "Test question?"
    poll.status = MagicMock(value="active")
    poll.choices = [
        MagicMock(id=str(uuid.uuid4()), text="Option A", vote_count=10),
        MagicMock(id=str(uuid.uuid4()), text="Option B", vote_count=5),
    ]
    poll.total_votes = 15
    return poll


@pytest.mark.unit
class TestVoteEndpoints:
    """Test vote-related endpoints."""

    async def test_vote_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that voting requires authentication."""
        response = await client.post(
            "/api/v1/votes",
            json={
                "poll_id": str(uuid.uuid4()),
                "choice_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in [401, 403]

    async def test_vote_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that vote endpoint is registered."""
        response = await client.post(
            "/api/v1/votes",
            json={
                "poll_id": "test-poll-id",
                "choice_id": "test-choice-id",
            },
        )
        # Should not be 404 - endpoint exists
        assert response.status_code != 404

    async def test_check_vote_status_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that checking vote status requires auth."""
        poll_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/votes/status/{poll_id}")
        assert response.status_code in [401, 403]

    async def test_retract_vote_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that retracting vote requires auth."""
        poll_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/votes/{poll_id}")
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestSecureVoteEndpoints:
    """Test secure vote endpoints with fraud detection."""

    async def test_secure_vote_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that secure vote endpoint is registered."""
        response = await client.post(
            "/api/v1/secure-votes",
            json={
                "poll_id": "test-poll-id",
                "choice_id": "test-choice-id",
            },
        )
        # Should not be 404 - endpoint exists
        assert response.status_code != 404

    async def test_secure_vote_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that secure voting requires authentication."""
        response = await client.post(
            "/api/v1/secure-votes",
            json={
                "poll_id": str(uuid.uuid4()),
                "choice_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in [401, 403]

    async def test_pre_check_vote_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that pre-check endpoint requires auth."""
        response = await client.post(
            "/api/v1/secure-votes/pre-check",
            json={
                "poll_id": str(uuid.uuid4()),
                "choice_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestVoteHashPrivacy:
    """Test vote hash generation for privacy."""

    def test_vote_hash_deterministic(self) -> None:
        """Test that vote hash is deterministic."""
        from core.security import generate_vote_hash

        user_id = "user-123"
        poll_id = "poll-456"

        hash1 = generate_vote_hash(user_id, poll_id)
        hash2 = generate_vote_hash(user_id, poll_id)

        assert hash1 == hash2

    def test_vote_hash_unique_per_combination(self) -> None:
        """Test that different user/poll combos have different hashes."""
        from core.security import generate_vote_hash

        hash1 = generate_vote_hash("user-1", "poll-1")
        hash2 = generate_vote_hash("user-2", "poll-1")
        hash3 = generate_vote_hash("user-1", "poll-2")

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    def test_vote_hash_format(self) -> None:
        """Test that vote hash is proper SHA-256 format."""
        from core.security import generate_vote_hash

        vote_hash = generate_vote_hash("user-123", "poll-456")

        # SHA-256 produces 64 character hex string
        assert len(vote_hash) == 64
        assert all(c in "0123456789abcdef" for c in vote_hash)
