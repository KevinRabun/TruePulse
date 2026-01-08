"""
Tests for Cosmos DB user repository.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from models.cosmos_documents import UserDocument


@pytest.fixture
def sample_user_doc():
    """Create a sample user document."""
    user_id = str(uuid.uuid4())
    return UserDocument(
        id=user_id,
        email="test@example.com",
        username="testuser",
        total_points=100,
        level=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.unit
class TestCosmosUserRepository:
    """Test CosmosUserRepository operations."""

    @pytest.mark.asyncio
    async def test_repository_instantiation(self) -> None:
        """Test that repository can be instantiated."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        repo = CosmosUserRepository()
        assert repo is not None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_user(self, sample_user_doc) -> None:
        """Test getting user by ID."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            mock_read.return_value = sample_user_doc.model_dump()

            repo = CosmosUserRepository()
            result = await repo.get_by_id(sample_user_doc.id)

            assert result is not None
            assert result.id == sample_user_doc.id
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self) -> None:
        """Test getting non-existent user returns None."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            mock_read.return_value = None

            repo = CosmosUserRepository()
            result = await repo.get_by_id("non-existent-id")

            assert result is None

    @pytest.mark.asyncio
    async def test_email_exists_returns_true(self) -> None:
        """Test email exists check returns true for existing email."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            # Simulating email lookup document exists
            mock_read.return_value = {"user_id": "user123"}

            repo = CosmosUserRepository()
            result = await repo.email_exists("existing@example.com")

            assert result is True

    @pytest.mark.asyncio
    async def test_email_exists_returns_false(self) -> None:
        """Test email exists check returns false for new email."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            # Simulating email lookup document doesn't exist
            mock_read.return_value = None

            repo = CosmosUserRepository()
            result = await repo.email_exists("new@example.com")

            assert result is False

    @pytest.mark.asyncio
    async def test_username_exists_returns_true(self) -> None:
        """Test username exists check returns true for existing username."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            # Simulating username lookup document exists
            mock_read.return_value = {"user_id": "user123"}

            repo = CosmosUserRepository()
            result = await repo.username_exists("existinguser")

            assert result is True

    @pytest.mark.asyncio
    async def test_username_exists_returns_false(self) -> None:
        """Test username exists check returns false for new username."""
        from repositories.cosmos_user_repository import CosmosUserRepository

        with patch("repositories.cosmos_user_repository.read_item") as mock_read:
            # Simulating username lookup document doesn't exist
            mock_read.return_value = None

            repo = CosmosUserRepository()
            result = await repo.username_exists("newuser")

            assert result is False


@pytest.mark.unit
class TestUserDocument:
    """Test UserDocument model."""

    def test_user_document_creation(self) -> None:
        """Test creating a user document."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_user_document_defaults(self) -> None:
        """Test user document default values."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
        )

        assert user.total_points == 0
        assert user.level == 1
        assert user.is_active is True
        # Settings are embedded directly in UserDocument
        assert user.email_notifications is True
        assert user.push_notifications is False
        assert user.theme_preference == "system"


@pytest.mark.unit
class TestUserAwardPoints:
    """Test user points awarding logic."""

    def test_points_can_be_updated(self) -> None:
        """Test that user points can be updated."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            total_points=100,
        )

        # Simulate points update
        user.total_points += 50

        assert user.total_points == 150

    def test_level_can_be_updated(self) -> None:
        """Test that user level can be updated."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            level=1,
        )

        # Simulate level up
        user.level = 2

        assert user.level == 2

    def test_show_on_leaderboard_defaults_to_true(self) -> None:
        """Test that show_on_leaderboard defaults to True for new users."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
        )

        # show_on_leaderboard should default to True
        assert user.show_on_leaderboard is True

    def test_show_on_leaderboard_is_serialized(self) -> None:
        """Test that show_on_leaderboard is included in JSON serialization."""
        user = UserDocument(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
        )

        # When serialized to JSON for Cosmos DB, the field should be present
        user_dict = user.model_dump(mode="json")
        assert "show_on_leaderboard" in user_dict
        assert user_dict["show_on_leaderboard"] is True
