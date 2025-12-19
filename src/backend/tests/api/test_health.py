"""
Tests for health and utility endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health check endpoints."""

    async def test_health_check(self, client: AsyncClient) -> None:
        """Test basic health check endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_root_endpoint(self, client: AsyncClient) -> None:
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "TruePulse" in data.get("name", "") or "truepulse" in data.get("message", "").lower()


@pytest.mark.unit
class TestAPIDocumentation:
    """Test API documentation endpoints."""

    async def test_openapi_schema_available(self, client: AsyncClient) -> None:
        """Test OpenAPI schema is accessible (only in debug mode)."""
        from core.config import settings
        response = await client.get("/openapi.json")
        if settings.DEBUG:
            assert response.status_code == 200
            data = response.json()
            assert "openapi" in data
            assert "paths" in data
        else:
            # Docs disabled in production
            assert response.status_code in [200, 404]

    async def test_docs_available(self, client: AsyncClient) -> None:
        """Test Swagger UI docs are accessible (only in debug mode)."""
        from core.config import settings
        response = await client.get("/docs")
        if settings.DEBUG:
            assert response.status_code == 200
        else:
            # Docs disabled in production
            assert response.status_code in [200, 404]
