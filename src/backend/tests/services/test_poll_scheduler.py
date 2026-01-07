"""
Tests for Poll Scheduler Service.

Tests the hourly poll rotation system including:
- Poll window calculations
- Current/previous/next poll retrieval
- Poll activation and closing
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment before imports
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POLL_DURATION_HOURS", "1")


class TestPollSchedulerWindowCalculations:
    """Tests for poll window time calculations."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with 1-hour poll duration."""
        with patch("services.poll_scheduler.settings") as mock:
            mock.POLL_DURATION_HOURS = 1
            yield mock

    def test_get_current_poll_window_on_hour(self, mock_settings):
        """Test window calculation when time is exactly on the hour."""
        from services.poll_scheduler import PollScheduler

        # Mock current time to be exactly 10:00 UTC
        fixed_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_current_poll_window()

            assert start.hour == 10
            assert start.minute == 0
            assert end.hour == 11
            assert end.minute == 0

    def test_get_current_poll_window_mid_hour(self, mock_settings):
        """Test window calculation when time is mid-hour."""
        from services.poll_scheduler import PollScheduler

        # Mock current time to be 10:30 UTC
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_current_poll_window()

            # Should still be in the 10:00-11:00 window
            assert start.hour == 10
            assert end.hour == 11

    def test_get_previous_poll_window(self, mock_settings):
        """Test previous window calculation."""
        from services.poll_scheduler import PollScheduler

        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_previous_poll_window()

            # Previous window should be 9:00-10:00
            assert start.hour == 9
            assert end.hour == 10

    def test_get_next_poll_window(self, mock_settings):
        """Test next window calculation."""
        from services.poll_scheduler import PollScheduler

        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_next_poll_window()

            # Next window should be 11:00-12:00
            assert start.hour == 11
            assert end.hour == 12


class TestPollSchedulerTwoHourDuration:
    """Tests for poll window calculations with 2-hour duration."""

    @pytest.fixture
    def mock_settings_2h(self):
        """Mock settings with 2-hour poll duration."""
        with patch("services.poll_scheduler.settings") as mock:
            mock.POLL_DURATION_HOURS = 2
            yield mock

    def test_get_current_poll_window_two_hour(self, mock_settings_2h):
        """Test 2-hour window calculation."""
        from services.poll_scheduler import PollScheduler

        # Mock current time to be 10:30 UTC
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_current_poll_window()

            # With 2-hour windows, 10:30 is in 10:00-12:00 window
            assert start.hour == 10
            assert end.hour == 12

    def test_get_current_poll_window_odd_hour(self, mock_settings_2h):
        """Test 2-hour window at odd hour."""
        from services.poll_scheduler import PollScheduler

        # Mock current time to be 11:30 UTC (odd hour)
        fixed_time = datetime(2024, 1, 15, 11, 30, 0, tzinfo=timezone.utc)

        with patch("services.poll_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            start, end = PollScheduler.get_current_poll_window()

            # With 2-hour windows, 11:30 is still in 10:00-12:00 window
            assert start.hour == 10
            assert end.hour == 12


class TestPollSchedulerDatabase:
    """Tests for PollScheduler database operations."""

    @pytest.fixture
    def scheduler(self):
        """Create PollScheduler instance."""
        from services.poll_scheduler import PollScheduler

        return PollScheduler()

    @pytest.mark.asyncio
    async def test_get_current_poll_returns_active(self, scheduler):
        """Test that get_current_poll returns active poll."""
        from models.cosmos_documents import PollDocument, PollStatus

        mock_poll = MagicMock(spec=PollDocument)
        mock_poll.id = "poll-123"
        mock_poll.status = PollStatus.ACTIVE

        with patch.object(scheduler.repo, "get_current_poll", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_poll

            result = await scheduler.get_current_poll()

            assert result is not None
            assert result.id == "poll-123"

    @pytest.mark.asyncio
    async def test_get_current_poll_returns_none_when_no_active(self, scheduler):
        """Test that get_current_poll returns None when no active poll."""
        with patch.object(scheduler.repo, "get_current_poll", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await scheduler.get_current_poll()

            assert result is None


class TestPollSchedulerPollManagement:
    """Tests for poll activation and closing."""

    @pytest.fixture
    def scheduler(self):
        """Create PollScheduler instance."""
        from services.poll_scheduler import PollScheduler

        return PollScheduler()

    @pytest.mark.asyncio
    async def test_close_expired_polls(self, scheduler):
        """Test that expired polls are closed."""
        # Mock the repository close_expired_polls method which returns count of closed polls
        with patch.object(scheduler.repo, "close_expired_polls", new_callable=AsyncMock) as mock_close:
            mock_close.return_value = 1  # 1 poll was closed

            result = await scheduler.close_expired_polls()

            # Verify repository method was called
            mock_close.assert_called_once()
            # Service returns empty list (repo handles updates internally)
            assert result == []


class TestPollSchedulerIntegration:
    """Integration-style tests for PollScheduler."""

    def test_window_boundaries_are_contiguous(self):
        """Test that poll windows don't have gaps."""
        from services.poll_scheduler import PollScheduler

        with patch("services.poll_scheduler.settings") as mock_settings:
            mock_settings.POLL_DURATION_HOURS = 1

            fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

            with patch("services.poll_scheduler.datetime") as mock_dt:
                mock_dt.now.return_value = fixed_time
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

                prev_start, prev_end = PollScheduler.get_previous_poll_window()
                curr_start, curr_end = PollScheduler.get_current_poll_window()
                next_start, next_end = PollScheduler.get_next_poll_window()

                # Previous end should equal current start
                assert prev_end == curr_start

                # Current end should equal next start
                assert curr_end == next_start

    def test_windows_have_correct_duration(self):
        """Test that all windows have the correct duration."""
        from services.poll_scheduler import PollScheduler

        with patch("services.poll_scheduler.settings") as mock_settings:
            mock_settings.POLL_DURATION_HOURS = 2

            fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

            with patch("services.poll_scheduler.datetime") as mock_dt:
                mock_dt.now.return_value = fixed_time
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

                for window_fn in [
                    PollScheduler.get_previous_poll_window,
                    PollScheduler.get_current_poll_window,
                    PollScheduler.get_next_poll_window,
                ]:
                    start, end = window_fn()
                    duration = end - start
                    assert duration == timedelta(hours=2)
