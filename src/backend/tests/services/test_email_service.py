"""
Tests for Email Service.

Tests the Azure Communication Services email integration including:
- Service initialization
- Password reset emails
- Email verification
- Error handling
"""

# Set test environment before imports
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")


class TestEmailService:
    """Tests for EmailService class."""

    @pytest.fixture
    def email_service(self):
        """Create a fresh EmailService instance."""
        from services.email_service import EmailService

        return EmailService()

    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self, email_service):
        """Test initialization without Azure credentials."""
        with patch.object(email_service, "_client", None):
            with patch("services.email_service.settings") as mock_settings:
                mock_settings.AZURE_COMMUNICATION_CONNECTION_STRING = None
                mock_settings.AZURE_EMAIL_SENDER_ADDRESS = None

                email_service._initialized = False
                await email_service.initialize()

                assert email_service._client is None
                assert email_service._initialized is True

    @pytest.mark.asyncio
    async def test_is_available_without_client(self, email_service):
        """Test is_available returns False when client is not initialized."""
        email_service._client = None
        email_service._sender_address = None

        assert email_service.is_available is False

    @pytest.mark.asyncio
    async def test_is_available_with_client(self, email_service):
        """Test is_available returns True when properly configured."""
        email_service._client = MagicMock()
        email_service._sender_address = "test@domain.com"

        assert email_service.is_available is True

    @pytest.mark.asyncio
    async def test_send_password_reset_unavailable(self, email_service):
        """Test password reset returns False when service unavailable."""
        email_service._initialized = True
        email_service._client = None

        result = await email_service.send_password_reset_email(
            to_email="user@example.com",
            reset_token="test-token-123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_password_reset_success(self, email_service):
        """Test successful password reset email sending."""
        mock_client = MagicMock()
        mock_poller = MagicMock()
        # The email service accesses result with dict-like syntax: result["status"]
        mock_result = {"status": "Succeeded", "id": "msg-123"}
        mock_poller.result.return_value = mock_result
        mock_client.begin_send.return_value = mock_poller

        email_service._client = mock_client
        email_service._sender_address = "noreply@truepulse.com"
        email_service._initialized = True

        with patch("services.email_service.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "https://truepulse.com"

            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                reset_token="test-token-123",
            )

            assert result is True
            mock_client.begin_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_password_reset_failure(self, email_service):
        """Test handling of email send failure."""
        mock_client = MagicMock()
        mock_client.begin_send.side_effect = Exception("Send failed")

        email_service._client = mock_client
        email_service._sender_address = "noreply@truepulse.com"
        email_service._initialized = True

        result = await email_service.send_password_reset_email(
            to_email="user@example.com",
            reset_token="test-token-123",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_with_import_error(self, email_service):
        """Test graceful handling when Azure SDK not installed."""
        import builtins

        # Reset state
        email_service._initialized = False
        email_service._client = None

        with patch("services.email_service.settings") as mock_settings:
            mock_settings.AZURE_COMMUNICATION_CONNECTION_STRING = "valid-connection-string"
            mock_settings.AZURE_EMAIL_SENDER_ADDRESS = "test@domain.com"

            # Mock the import to raise ImportError
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "azure.communication.email" in name:
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                # The service should handle this gracefully and still mark as initialized
                await email_service.initialize()
                # Service is marked initialized but client is None
                assert email_service._initialized is True
                assert email_service._client is None

    @pytest.mark.asyncio
    async def test_skip_reinitialization(self, email_service):
        """Test that initialize() skips if already initialized."""
        email_service._initialized = True
        original_client = MagicMock()
        email_service._client = original_client

        await email_service.initialize()

        # Client should not have changed
        assert email_service._client is original_client


class TestEmailServiceIntegration:
    """Integration-style tests for email service (mocked Azure)."""

    @pytest.mark.asyncio
    async def test_email_content_password_reset(self):
        """Test that password reset email contains correct content."""
        from services.email_service import EmailService

        service = EmailService()
        mock_client = MagicMock()
        captured_message = None

        def capture_message(message):
            nonlocal captured_message
            captured_message = message
            mock_poller = MagicMock()
            mock_result = MagicMock(status="Succeeded")
            mock_poller.result.return_value = mock_result
            return mock_poller

        mock_client.begin_send.side_effect = capture_message
        service._client = mock_client
        service._sender_address = "noreply@truepulse.com"
        service._initialized = True

        with patch("services.email_service.settings") as mock_settings:
            mock_settings.FRONTEND_URL = "https://truepulse.com"

            await service.send_password_reset_email(
                to_email="user@example.com",
                reset_token="abc123",
            )

        # Verify message structure
        assert captured_message is not None
        assert "user@example.com" in str(captured_message)
