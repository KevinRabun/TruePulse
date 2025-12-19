"""
Pytest fixtures for TruePulse backend tests.
"""

import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("POSTGRES_PASSWORD", "test-password")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "truepulse_test")
os.environ.setdefault("FRONTEND_API_SECRET", "test-frontend-secret-for-testing")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio backend for async tests."""
    return "asyncio"


@pytest.fixture
async def app() -> Any:
    """Create FastAPI application for testing."""
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture
async def client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with required frontend headers."""
    # Include X-Frontend-Secret and Origin headers to pass FrontendOnlyMiddleware
    headers = {
        "X-Frontend-Secret": os.environ.get("FRONTEND_API_SECRET", "test-frontend-secret-for-testing"),
        "Origin": "http://localhost:3000",  # From ALLOWED_ORIGINS
    }
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_verified": True,
    }


@pytest.fixture
def sample_poll_data() -> dict[str, Any]:
    """Sample poll data for testing."""
    return {
        "id": "test-poll-123",
        "question": "What is your opinion on this test question?",
        "choices": [
            {"id": "1", "text": "Strongly agree", "order": 0},
            {"id": "2", "text": "Agree", "order": 1},
            {"id": "3", "text": "Neutral", "order": 2},
            {"id": "4", "text": "Disagree", "order": 3},
            {"id": "5", "text": "Strongly disagree", "order": 4},
        ],
        "category": "Test",
        "is_active": True,
        "time_remaining_seconds": 3600,
    }


@pytest.fixture
def auth_headers(sample_user_data: dict[str, Any]) -> dict[str, str]:
    """Generate authentication headers for testing."""
    # In a real test, you'd generate a valid JWT here
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json",
    }
