"""
Tests for API dependencies (deps.py).

Tests the UserInDB construction and dependency functions.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from api.deps import _user_model_to_schema
from schemas.user import UserInDB


@pytest.mark.unit
class TestUserModelToSchemaHelper:
    """Test the _user_model_to_schema helper function for DRY conversion."""

    def test_helper_converts_user_model_with_display_name(self) -> None:
        """Test that the helper correctly converts a User model to UserInDB."""
        # Create a mock User model
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "helper@example.com"
        mock_user.username = "helperuser"
        mock_user.display_name = "Helper Display"
        mock_user.is_active = True
        mock_user.is_verified = True
        mock_user.is_admin = False
        mock_user.email_verified = True
        mock_user.total_points = 250
        mock_user.level = 3
        mock_user.votes_cast = 15
        mock_user.current_streak = 3
        mock_user.longest_streak = 8
        mock_user.created_at = datetime.now(timezone.utc)

        result = _user_model_to_schema(mock_user)

        assert isinstance(result, UserInDB)
        assert result.id == str(mock_user.id)
        assert result.email == "helper@example.com"
        assert result.username == "helperuser"
        assert result.display_name == "Helper Display"
        assert result.is_active is True
        assert result.is_verified is True
        assert result.is_admin is False
        assert result.email_verified is True
        assert result.points == 250
        assert result.level == 3
        assert result.votes_cast == 15
        assert result.current_streak == 3
        assert result.longest_streak == 8

    def test_helper_preserves_none_display_name(self) -> None:
        """Test that helper preserves None display_name (doesn't fall back to username)."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "noname@example.com"
        mock_user.username = "username_here"
        mock_user.display_name = None  # No display name set
        mock_user.is_active = True
        mock_user.is_verified = True
        mock_user.is_admin = False
        mock_user.email_verified = True
        mock_user.total_points = 0
        mock_user.level = 1
        mock_user.votes_cast = 0
        mock_user.current_streak = 0
        mock_user.longest_streak = 0
        mock_user.created_at = datetime.now(timezone.utc)

        result = _user_model_to_schema(mock_user)

        # display_name should be None, not username
        assert result.display_name is None
        assert result.username == "username_here"

    def test_helper_maps_total_points_to_points(self) -> None:
        """Test that helper correctly maps model.total_points to schema.points."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.display_name = "Test"
        mock_user.is_active = True
        mock_user.is_verified = True
        mock_user.is_admin = False
        mock_user.email_verified = True
        mock_user.total_points = 1500  # Model uses total_points
        mock_user.level = 5
        mock_user.votes_cast = 100
        mock_user.current_streak = 10
        mock_user.longest_streak = 20
        mock_user.created_at = datetime.now(timezone.utc)

        result = _user_model_to_schema(mock_user)

        # Schema uses 'points', model uses 'total_points'
        assert result.points == 1500


@pytest.mark.unit
class TestUserInDBConstruction:
    """Test UserInDB schema construction with all fields."""

    def test_user_in_db_includes_display_name(self) -> None:
        """Test that UserInDB correctly includes display_name field."""
        user = UserInDB(
            id="test-id",
            email="test@example.com",
            username="testuser",
            display_name="Test Display Name",
            is_active=True,
            is_verified=True,
            is_admin=False,
            email_verified=True,
            points=100,
            level=2,
            votes_cast=10,
            current_streak=5,
            longest_streak=10,
            created_at=datetime.now(timezone.utc),
        )

        assert user.display_name == "Test Display Name"
        assert user.username == "testuser"

    def test_user_in_db_display_name_defaults_to_none(self) -> None:
        """Test that UserInDB display_name defaults to None when not provided."""
        user = UserInDB(
            id="test-id",
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=True,
        )

        assert user.display_name is None

    def test_user_in_db_display_name_can_be_null(self) -> None:
        """Test that UserInDB display_name can explicitly be set to None."""
        user = UserInDB(
            id="test-id",
            email="test@example.com",
            username="testuser",
            display_name=None,
            is_active=True,
            is_verified=True,
        )

        assert user.display_name is None

    def test_user_in_db_display_name_differs_from_username(self) -> None:
        """Test that display_name and username can differ."""
        user = UserInDB(
            id="test-id",
            email="test@example.com",
            username="john.doe",
            display_name="John",
            is_active=True,
            is_verified=True,
        )

        assert user.display_name == "John"
        assert user.username == "john.doe"
        assert user.display_name != user.username


@pytest.mark.unit
class TestUserInDBFromModel:
    """Test constructing UserInDB from database model attributes."""

    def test_construct_from_model_attributes(self) -> None:
        """Test creating UserInDB from model-like attributes dict."""
        # Simulate what deps.py does when constructing from a User model
        model_data = {
            "id": str(uuid4()),
            "email": "user@example.com",
            "username": "model_user",
            "display_name": "Model User Display",
            "is_active": True,
            "is_verified": True,
            "is_admin": False,
            "email_verified": True,
            "total_points": 500,
            "level": 3,
            "votes_cast": 25,
            "current_streak": 7,
            "longest_streak": 14,
            "created_at": datetime.now(timezone.utc),
        }

        # Construct UserInDB as deps.py does
        user = UserInDB(
            id=str(model_data["id"]),
            email=model_data["email"],
            username=model_data["username"],
            display_name=model_data["display_name"],
            is_active=model_data["is_active"],
            is_verified=model_data["is_verified"],
            is_admin=model_data["is_admin"],
            email_verified=model_data["email_verified"],
            points=model_data["total_points"],
            level=model_data["level"],
            votes_cast=model_data["votes_cast"],
            current_streak=model_data["current_streak"],
            longest_streak=model_data["longest_streak"],
            created_at=model_data["created_at"],
        )

        assert user.display_name == "Model User Display"
        assert user.points == 500

    def test_construct_with_none_display_name_from_model(self) -> None:
        """Test that None display_name from model is preserved."""
        user = UserInDB(
            id="test-id",
            email="user@example.com",
            username="username",
            display_name=None,  # Model has None
            is_active=True,
            is_verified=True,
            is_admin=False,
            email_verified=True,
            points=0,
            level=1,
            votes_cast=0,
            current_streak=0,
            longest_streak=0,
        )

        # display_name should be None, not fall back to username
        assert user.display_name is None


@pytest.mark.unit
class TestUserInDBAllFields:
    """Test that all UserInDB fields are properly typed and accessible."""

    def test_all_required_fields_present(self) -> None:
        """Test that UserInDB has all expected fields."""
        user = UserInDB(
            id="test-id",
            email="test@example.com",
            username="testuser",
            display_name="Test User",
            is_active=True,
            is_verified=True,
            is_admin=False,
            email_verified=True,
            points=100,
            level=2,
            votes_cast=10,
            current_streak=5,
            longest_streak=10,
            age_range="25-34",
            gender="male",
            country="US",
            state_province="CA",
            city="Los Angeles",
            education_level="bachelors",
            employment_status="employed",
            industry="technology",
        )

        # Core fields
        assert user.id == "test-id"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.display_name == "Test User"

        # Status fields
        assert user.is_active is True
        assert user.is_verified is True
        assert user.is_admin is False
        assert user.email_verified is True

        # Gamification fields
        assert user.points == 100
        assert user.level == 2
        assert user.votes_cast == 10
        assert user.current_streak == 5
        assert user.longest_streak == 10

        # Demographics fields
        assert user.age_range == "25-34"
        assert user.gender == "male"
        assert user.country == "US"
        assert user.state_province == "CA"
        assert user.city == "Los Angeles"
        assert user.education_level == "bachelors"
        assert user.employment_status == "employed"
        assert user.industry == "technology"
