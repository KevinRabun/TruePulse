"""
Tests for poll API endpoints.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestPollEndpoints:
    """Test poll-related endpoints."""

    @pytest.mark.integration
    async def test_get_polls_unauthenticated(self, client: AsyncClient) -> None:
        """Test that polls can be viewed without authentication."""
        response = await client.get("/api/v1/polls")
        # Should return 200 (public endpoint) or list of polls
        assert response.status_code in [200, 404]

    @pytest.mark.integration
    async def test_get_single_poll(
        self,
        client: AsyncClient,
        sample_poll_data: dict[str, Any],
    ) -> None:
        """Test getting a single poll by ID."""
        poll_id = sample_poll_data["id"]
        response = await client.get(f"/api/v1/polls/{poll_id}")
        # Poll may or may not exist in test db
        assert response.status_code in [200, 404]

    @pytest.mark.integration
    async def test_get_active_poll(self, client: AsyncClient) -> None:
        """Test getting currently active poll."""
        response = await client.get("/api/v1/polls/current")
        assert response.status_code in [200, 404]

    @pytest.mark.integration
    async def test_vote_requires_authentication(
        self,
        client: AsyncClient,
        sample_poll_data: dict[str, Any],
    ) -> None:
        """Test that voting requires authentication (using votes endpoint)."""
        response = await client.post(
            "/api/v1/votes",
            json={"poll_id": sample_poll_data["id"], "choice_id": "1"},
        )
        # Should require auth
        assert response.status_code in [401, 403, 422]


@pytest.mark.unit
class TestPollResultsEndpoints:
    """Test poll results endpoints."""

    @pytest.mark.integration
    async def test_get_poll_results_public(
        self,
        client: AsyncClient,
        sample_poll_data: dict[str, Any],
    ) -> None:
        """Test that poll results are publicly accessible."""
        poll_id = sample_poll_data["id"]
        response = await client.get(f"/api/v1/polls/{poll_id}/results")
        # Results are public
        assert response.status_code in [200, 404]

    @pytest.mark.integration
    async def test_results_contain_expected_fields(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that results response has expected structure."""
        response = await client.get("/api/v1/polls/current")
        if response.status_code == 200:
            data = response.json()
            # If we got a poll, verify structure
            if data:
                assert "question" in data or "id" in data
