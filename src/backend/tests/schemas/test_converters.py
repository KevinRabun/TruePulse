"""Tests for the schema converters."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from schemas.converters import poll_model_to_schema


class TestPollModelToSchema:
    """Tests for poll_model_to_schema converter."""

    @pytest.fixture
    def mock_poll_choice(self):
        """Create a mock poll choice."""

        def _create_choice(text: str, vote_count: int, order: int = 0):
            choice = MagicMock()
            choice.id = f"choice-{text.lower()}"
            choice.text = text
            choice.vote_count = vote_count
            choice.order = order
            return choice

        return _create_choice

    @pytest.fixture
    def mock_poll(self, mock_poll_choice):
        """Create a mock poll with all required fields."""
        poll = MagicMock()
        poll.id = "test-poll-id"
        poll.question = "What is your favorite color?"
        poll.poll_type = "pulse"
        poll.status = "active"
        poll.category = "preferences"
        poll.source_event = "Test Event"
        poll.scheduled_start = datetime.now(timezone.utc)
        poll.scheduled_end = datetime.now(timezone.utc)
        poll.created_at = datetime.now(timezone.utc)
        poll.updated_at = datetime.now(timezone.utc)
        poll.expires_at = datetime.now(timezone.utc)
        poll.is_active = True
        poll.is_special = False
        poll.duration_hours = 12
        poll.choices = [
            mock_poll_choice("Red", 10, 0),
            mock_poll_choice("Blue", 15, 1),
            mock_poll_choice("Green", 5, 2),
        ]
        return poll

    def test_active_poll_excludes_vote_counts(self, mock_poll):
        """Test that active polls do NOT include vote counts."""
        mock_poll.status = "active"

        result = poll_model_to_schema(mock_poll)

        assert result.id == "test-poll-id"
        assert result.question == "What is your favorite color?"
        assert len(result.choices) == 3

        # Vote counts should NOT be included for active polls
        for choice in result.choices:
            assert choice.vote_count is None

    def test_closed_poll_includes_vote_counts(self, mock_poll):
        """Test that closed polls include vote counts."""
        mock_poll.status = "closed"

        result = poll_model_to_schema(mock_poll)

        assert result.id == "test-poll-id"
        assert len(result.choices) == 3

        # Vote counts SHOULD be included for closed polls
        vote_counts = [c.vote_count for c in result.choices]
        assert 10 in vote_counts
        assert 15 in vote_counts
        assert 5 in vote_counts

    def test_archived_poll_includes_vote_counts(self, mock_poll):
        """Test that archived polls include vote counts."""
        mock_poll.status = "archived"

        result = poll_model_to_schema(mock_poll)

        assert len(result.choices) == 3

        # Vote counts SHOULD be included for archived polls
        vote_counts = [c.vote_count for c in result.choices]
        assert 10 in vote_counts
        assert 15 in vote_counts
        assert 5 in vote_counts

    def test_scheduled_poll_excludes_vote_counts(self, mock_poll):
        """Test that scheduled polls do NOT include vote counts."""
        mock_poll.status = "scheduled"

        result = poll_model_to_schema(mock_poll)

        # Vote counts should NOT be included for scheduled polls
        for choice in result.choices:
            assert choice.vote_count is None

    def test_include_vote_counts_override_true(self, mock_poll):
        """Test that include_vote_counts=True includes counts for any status."""
        mock_poll.status = "active"

        result = poll_model_to_schema(mock_poll, include_vote_counts=True)

        # Vote counts SHOULD be included when explicitly requested
        vote_counts = [c.vote_count for c in result.choices]
        assert 10 in vote_counts
        assert 15 in vote_counts
        assert 5 in vote_counts

    def test_include_vote_counts_override_false_on_active(self, mock_poll):
        """Test that include_vote_counts=False keeps votes hidden for active polls."""
        mock_poll.status = "active"

        result = poll_model_to_schema(mock_poll, include_vote_counts=False)

        # Vote counts should NOT be included when explicitly disabled on active poll
        for choice in result.choices:
            assert choice.vote_count is None

    def test_closed_polls_always_include_vote_counts(self, mock_poll):
        """Test that closed polls always include vote counts regardless of parameter."""
        mock_poll.status = "closed"

        # Even with include_vote_counts=False, closed polls should show votes
        # This is the intended behavior - closed polls always reveal results
        result = poll_model_to_schema(mock_poll, include_vote_counts=False)

        # Vote counts SHOULD still be included for closed polls (business logic)
        vote_counts = [c.vote_count for c in result.choices]
        assert 10 in vote_counts
        assert 15 in vote_counts
        assert 5 in vote_counts

    def test_poll_choice_fields_preserved(self, mock_poll):
        """Test that all poll choice fields are properly preserved."""
        mock_poll.status = "closed"

        result = poll_model_to_schema(mock_poll)

        for choice in result.choices:
            assert choice.id is not None
            assert choice.text in ["Red", "Blue", "Green"]
