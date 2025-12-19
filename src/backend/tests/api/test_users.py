"""
Tests for user API endpoints.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestUserProfileEndpoints:
    """Test user profile endpoints."""

    async def test_get_profile_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that getting profile requires authentication."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code in [401, 403]

    async def test_update_profile_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that updating profile requires authentication."""
        response = await client.put(
            "/api/v1/users/me",
            json={"username": "newusername"},
        )
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestUserDemographicsEndpoints:
    """Test user demographics endpoints."""

    async def test_get_demographics_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that getting demographics requires auth."""
        response = await client.get("/api/v1/users/me/demographics")
        assert response.status_code in [401, 403]

    async def test_update_demographics_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that updating demographics requires auth."""
        response = await client.put(
            "/api/v1/users/me/demographics",
            json={
                "age_range": "25-34",
                "gender": "prefer_not_to_say",
                "country": "US",
            },
        )
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestUserSettingsEndpoints:
    """Test user settings endpoints."""

    async def test_get_settings_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that getting settings requires auth."""
        response = await client.get("/api/v1/users/me/settings")
        assert response.status_code in [401, 403]

    async def test_update_settings_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that updating settings requires auth."""
        response = await client.put(
            "/api/v1/users/me/settings",
            json={
                "email_notifications": True,
                "push_notifications": False,
            },
        )
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestPhoneVerificationEndpoints:
    """Test phone verification endpoints."""

    async def test_add_phone_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that adding phone requires auth."""
        response = await client.post(
            "/api/v1/users/me/phone",
            json={"phone_number": "+15551234567"},
        )
        assert response.status_code in [401, 403]

    async def test_verify_phone_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that phone verification requires auth."""
        response = await client.post(
            "/api/v1/users/me/phone/verify",
            json={"code": "123456"},
        )
        assert response.status_code in [401, 403]

    async def test_resend_verification_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that resending verification requires auth."""
        response = await client.post("/api/v1/users/me/phone/resend")
        assert response.status_code in [401, 403]

    async def test_remove_phone_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that removing phone requires auth."""
        response = await client.delete("/api/v1/users/me/phone")
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestAccountDeletionEndpoint:
    """Test account deletion endpoint."""

    async def test_delete_account_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that deleting account requires auth."""
        response = await client.delete("/api/v1/users/me")
        assert response.status_code in [401, 403]
