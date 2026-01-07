"""Tests for the notification service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.notification_service import NotificationService


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def mock_poll(self):
        """Create a mock poll."""
        poll = MagicMock()
        poll.id = "test-poll-id"
        poll.question = "What is your favorite color?"
        poll.poll_type = "pulse"
        poll.scheduled_end = datetime.now(timezone.utc)
        poll.expires_at = datetime.now(timezone.utc)
        return poll

    @pytest.fixture
    def mock_user(self):
        """Create a mock user document."""
        user = MagicMock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.username = "testuser"
        user.display_name = "Test User"
        user.flash_polls_per_day = 5
        user.flash_polls_notified_today = 0
        return user

    def test_service_instantiation(self):
        """Test that NotificationService can be instantiated."""
        service = NotificationService()
        assert service.user_repo is not None
        assert service.email_service is not None

    def test_can_send_flash_notification_under_limit(self, mock_user):
        """Test that flash notifications can be sent when under daily limit."""
        service = NotificationService()
        mock_user.flash_polls_per_day = 5
        mock_user.flash_polls_notified_today = 3

        result = service._can_send_flash_notification(mock_user)
        assert result is True

    def test_can_send_flash_notification_at_limit(self, mock_user):
        """Test that flash notifications are blocked when at daily limit."""
        service = NotificationService()
        mock_user.flash_polls_per_day = 5
        mock_user.flash_polls_notified_today = 5

        result = service._can_send_flash_notification(mock_user)
        assert result is False

    def test_can_send_flash_notification_unlimited(self, mock_user):
        """Test that 0 means unlimited flash notifications."""
        service = NotificationService()
        mock_user.flash_polls_per_day = 0  # Unlimited
        mock_user.flash_polls_notified_today = 100

        result = service._can_send_flash_notification(mock_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_poll_notifications_returns_stats(self, mock_poll):
        """Test that notification sending returns proper stats."""
        service = NotificationService()

        # Mock email service as unavailable by patching the _client attribute
        service.email_service._client = None
        service.email_service._initialized = True

        result = await service.send_poll_notifications(mock_poll, "pulse")

        assert "sent" in result
        assert "skipped" in result
        assert "errors" in result
        assert result["reason"] == "email_service_unavailable"

    @pytest.mark.asyncio
    async def test_get_eligible_users_pulse(self):
        """Test getting eligible users for pulse poll notifications."""
        service = NotificationService()

        # Mock the user repository query
        with patch.object(service.user_repo, "get_users_by_notification_preference") as mock_get:
            mock_get.return_value = []

            users = await service._get_eligible_users("pulse")

            assert users == []
            mock_get.assert_called_once_with(pulse_notifications=True)

    @pytest.mark.asyncio
    async def test_get_eligible_users_flash(self):
        """Test getting eligible users for flash poll notifications."""
        service = NotificationService()

        # Mock the user repository query
        with patch.object(service.user_repo, "get_users_by_notification_preference") as mock_get:
            mock_get.return_value = []

            users = await service._get_eligible_users("flash")

            assert users == []
            mock_get.assert_called_once_with(flash_notifications=True)

    @pytest.mark.asyncio
    async def test_get_eligible_users_unknown_type(self):
        """Test getting users for unknown poll type returns empty list."""
        service = NotificationService()

        users = await service._get_eligible_users("unknown")

        assert users == []


class TestNotificationEmailContent:
    """Tests for notification email content generation."""

    @pytest.fixture
    def mock_poll(self):
        """Create a mock poll with full data."""
        poll = MagicMock()
        poll.id = "test-poll-123"
        poll.question = "Should AI be regulated more strictly?"
        poll.poll_type = "pulse"
        poll.scheduled_end = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        poll.expires_at = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        return poll

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = "user-123"
        user.email = "voter@example.com"
        user.username = "aivoter"
        user.display_name = "AI Voter"
        return user

    @pytest.mark.asyncio
    async def test_pulse_poll_email_subject(self, mock_poll, mock_user):
        """Test that pulse poll emails have correct subject."""
        service = NotificationService()

        # Mock email service with patching
        with patch.object(service, "email_service") as mock_email_service:
            mock_email_service.is_available = True
            mock_email_service._send_email = AsyncMock(return_value=True)

            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.FRONTEND_URL = "https://truepulse.app"

                await service._send_poll_notification_email(mock_user, mock_poll, "pulse")

                # Verify email was sent with pulse subject
                call_args = mock_email_service._send_email.call_args
                assert "Pulse Poll" in call_args.kwargs["subject"]

    @pytest.mark.asyncio
    async def test_flash_poll_email_subject(self, mock_poll, mock_user):
        """Test that flash poll emails have correct subject."""
        service = NotificationService()
        mock_poll.poll_type = "flash"

        # Mock email service with patching
        with patch.object(service, "email_service") as mock_email_service:
            mock_email_service.is_available = True
            mock_email_service._send_email = AsyncMock(return_value=True)

            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.FRONTEND_URL = "https://truepulse.app"

                await service._send_poll_notification_email(mock_user, mock_poll, "flash")

                # Verify email was sent with flash subject
                call_args = mock_email_service._send_email.call_args
                assert "Flash Poll" in call_args.kwargs["subject"]

    @pytest.mark.asyncio
    async def test_poll_email_contains_vote_link(self, mock_poll, mock_user):
        """Test that poll emails contain a clickable link to the poll."""
        service = NotificationService()

        with patch.object(service, "email_service") as mock_email_service:
            mock_email_service.is_available = True
            mock_email_service._send_email = AsyncMock(return_value=True)

            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.FRONTEND_URL = "https://truepulse.app"

                await service._send_poll_notification_email(mock_user, mock_poll, "pulse")

                call_args = mock_email_service._send_email.call_args
                html_content = call_args.kwargs["html_content"]
                plain_text = call_args.kwargs["plain_text"]
                poll_url = f"https://truepulse.app/poll?id={mock_poll.id}"

                # Verify link is in HTML (button and fallback text link)
                assert poll_url in html_content
                assert "Vote Now" in html_content
                assert f'href="{poll_url}"' in html_content

                # Verify link is in plain text
                assert poll_url in plain_text
                assert "Vote now:" in plain_text
