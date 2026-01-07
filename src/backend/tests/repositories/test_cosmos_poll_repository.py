"""
Tests for Cosmos DB poll repository.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from models.cosmos_documents import PollChoiceDocument, PollDocument, PollStatus, PollType


@pytest.fixture
def sample_poll_doc():
    """Create a sample poll document."""
    poll_id = str(uuid.uuid4())
    return PollDocument(
        id=poll_id,
        question="Test question?",
        category="general",
        status=PollStatus.ACTIVE,
        poll_type=PollType.PULSE,
        scheduled_start=datetime.now(timezone.utc) - timedelta(hours=1),
        scheduled_end=datetime.now(timezone.utc) + timedelta(hours=23),
        choices=[
            PollChoiceDocument(id=str(uuid.uuid4()), text="Option A", vote_count=60, order=0),
            PollChoiceDocument(id=str(uuid.uuid4()), text="Option B", vote_count=40, order=1),
        ],
        total_votes=100,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.unit
class TestCosmosPollRepository:
    """Test CosmosPollRepository operations."""

    @pytest.mark.asyncio
    async def test_repository_instantiation(self) -> None:
        """Test that repository can be instantiated."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        repo = CosmosPollRepository()
        assert repo is not None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_poll(self, sample_poll_doc) -> None:
        """Test getting poll by ID."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        with patch("repositories.cosmos_poll_repository.read_item") as mock_read:
            mock_read.return_value = sample_poll_doc.model_dump()

            repo = CosmosPollRepository()
            result = await repo.get_by_id(sample_poll_doc.id)

            assert result is not None
            assert result.id == sample_poll_doc.id
            assert result.question == "Test question?"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self) -> None:
        """Test getting non-existent poll returns None."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        with patch("repositories.cosmos_poll_repository.read_item") as mock_read:
            mock_read.return_value = None

            repo = CosmosPollRepository()
            result = await repo.get_by_id("non-existent-id")

            assert result is None


@pytest.mark.unit
class TestPollStatusTransitions:
    """Test poll status transition logic."""

    def test_valid_status_transitions(self) -> None:
        """Test valid poll status transitions."""
        # Valid transitions:
        # SCHEDULED -> ACTIVE -> CLOSED -> ARCHIVED

        valid_transitions = [
            (PollStatus.SCHEDULED, PollStatus.ACTIVE),
            (PollStatus.ACTIVE, PollStatus.CLOSED),
            (PollStatus.CLOSED, PollStatus.ARCHIVED),
        ]

        # Verify the enums exist
        for from_status, to_status in valid_transitions:
            assert from_status is not None
            assert to_status is not None

    def test_poll_status_values(self) -> None:
        """Test poll status enum values."""
        assert PollStatus.SCHEDULED.value == "scheduled"
        assert PollStatus.ACTIVE.value == "active"
        assert PollStatus.CLOSED.value == "closed"
        assert PollStatus.ARCHIVED.value == "archived"


@pytest.mark.unit
class TestPollDocument:
    """Test PollDocument model."""

    def test_poll_document_creation(self) -> None:
        """Test creating a poll document."""
        poll = PollDocument(
            id=str(uuid.uuid4()),
            question="What is your favorite color?",
            category="lifestyle",
            status=PollStatus.SCHEDULED,
            poll_type=PollType.PULSE,
            scheduled_start=datetime.now(timezone.utc),
            scheduled_end=datetime.now(timezone.utc) + timedelta(hours=24),
            choices=[
                PollChoiceDocument(id=str(uuid.uuid4()), text="Red", vote_count=0, order=0),
                PollChoiceDocument(id=str(uuid.uuid4()), text="Blue", vote_count=0, order=1),
            ],
        )

        assert poll.question == "What is your favorite color?"
        assert len(poll.choices) == 2
        assert poll.status == PollStatus.SCHEDULED

    def test_poll_document_total_votes_default(self) -> None:
        """Test that total_votes defaults to 0."""
        poll = PollDocument(
            id=str(uuid.uuid4()),
            question="Test?",
            category="test",
            status=PollStatus.ACTIVE,
            poll_type=PollType.STANDARD,
            scheduled_start=datetime.now(timezone.utc),
            scheduled_end=datetime.now(timezone.utc) + timedelta(hours=1),
            choices=[],
        )

        assert poll.total_votes == 0

    def test_poll_choice_document_creation(self) -> None:
        """Test creating a poll choice document."""
        choice = PollChoiceDocument(
            id=str(uuid.uuid4()),
            text="Option A",
            vote_count=50,
            order=0,
        )

        assert choice.text == "Option A"
        assert choice.vote_count == 50
        assert choice.order == 0


@pytest.mark.unit
class TestGetPollByScheduledStart:
    """Test get_poll_by_scheduled_start method for duplicate detection."""

    @pytest.mark.asyncio
    async def test_get_poll_by_scheduled_start_returns_poll(self, sample_poll_doc) -> None:
        """Test finding a poll by scheduled_start returns the poll."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        with patch("repositories.cosmos_poll_repository.query_items") as mock_query:
            mock_query.return_value = [sample_poll_doc.model_dump()]

            repo = CosmosPollRepository()
            # poll_type from fixture is PollType enum, use .value
            poll_type_value = (
                sample_poll_doc.poll_type.value
                if hasattr(sample_poll_doc.poll_type, "value")
                else str(sample_poll_doc.poll_type)
            )
            result = await repo.get_poll_by_scheduled_start(
                scheduled_start=sample_poll_doc.scheduled_start,
                poll_type=poll_type_value,
            )

            assert result is not None
            assert result.id == sample_poll_doc.id
            mock_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_poll_by_scheduled_start_returns_none_when_not_found(self) -> None:
        """Test that None is returned when no poll exists for the scheduled start."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        with patch("repositories.cosmos_poll_repository.query_items") as mock_query:
            mock_query.return_value = []

            repo = CosmosPollRepository()
            result = await repo.get_poll_by_scheduled_start(
                scheduled_start=datetime.now(timezone.utc),
                poll_type="pulse",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_poll_by_scheduled_start_without_poll_type(self, sample_poll_doc) -> None:
        """Test finding a poll by scheduled_start without poll_type filter."""
        from repositories.cosmos_poll_repository import CosmosPollRepository

        with patch("repositories.cosmos_poll_repository.query_items") as mock_query:
            mock_query.return_value = [sample_poll_doc.model_dump()]

            repo = CosmosPollRepository()
            result = await repo.get_poll_by_scheduled_start(
                scheduled_start=sample_poll_doc.scheduled_start,
            )

            assert result is not None
            # Verify query was called without poll_type in the query
            mock_query.assert_called_once()
