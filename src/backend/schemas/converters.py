"""
Schema converter functions.

Centralized helper functions for converting Cosmos DB documents to Pydantic schemas.
These are the single source of truth for document-to-schema conversions, ensuring DRY code.
"""

from models.cosmos_documents import PollDocument, PollStatus
from schemas.poll import (
    Poll,
    PollChoice,
    PollChoiceWithResults,
    PollStatusEnum,
    PollTypeEnum,
    PollWithResults,
)


def _get_status_value(status: PollStatus | str) -> str:
    """Extract the string value from a PollStatus enum or string."""
    if isinstance(status, PollStatus):
        return status.value
    return status


def _get_poll_type_value(poll_type) -> str:
    """Extract the string value from a PollType enum or string."""
    if poll_type is None:
        return "standard"
    if hasattr(poll_type, "value"):
        return poll_type.value
    return str(poll_type)


def poll_model_to_schema(poll: PollDocument, include_vote_counts: bool = False) -> Poll:
    """
    Convert a PollDocument (Cosmos DB) to a Poll Pydantic schema.

    This is the single source of truth for PollDocument -> schema conversion.
    Used by both public and admin endpoints.

    Args:
        poll: The poll document to convert
        include_vote_counts: If True, include vote counts in choices (for closed polls)
    """
    # Include vote counts if requested or if poll is closed
    status_value = _get_status_value(poll.status)
    should_include_votes = include_vote_counts or status_value in ("closed", "archived")

    return Poll(
        id=str(poll.id),
        question=poll.question,
        choices=[
            PollChoice(
                id=str(c.id),
                text=c.text,
                order=c.order,
                vote_count=c.vote_count if should_include_votes else None,
            )
            for c in sorted(poll.choices, key=lambda x: x.order)
        ],
        category=poll.category,
        source_event=poll.source_event,
        source_event_url=poll.source_event_url,
        status=PollStatusEnum(status_value),
        created_at=poll.created_at,
        expires_at=poll.expires_at,
        scheduled_start=poll.scheduled_start,
        scheduled_end=poll.scheduled_end,
        is_active=poll.is_active,
        is_special=poll.is_special,
        duration_hours=poll.duration_hours,
        total_votes=poll.total_votes,
        is_featured=poll.is_featured,
        ai_generated=poll.ai_generated,
        poll_type=PollTypeEnum(_get_poll_type_value(poll.poll_type)),
        time_remaining_seconds=poll.time_remaining_seconds,
    )


def poll_model_to_results_schema(poll: PollDocument) -> PollWithResults:
    """
    Convert a PollDocument (Cosmos DB) to a PollWithResults Pydantic schema.

    This includes vote counts and percentages for each choice.
    This is the single source of truth for PollDocument -> results schema conversion.
    Used by both public and admin endpoints.
    """
    total = poll.total_votes or 0
    status_value = _get_status_value(poll.status)

    return PollWithResults(
        id=str(poll.id),
        question=poll.question,
        choices=[
            PollChoiceWithResults(
                id=str(c.id),
                text=c.text,
                order=c.order,
                vote_count=c.vote_count,
                vote_percentage=(c.vote_count / total * 100) if total > 0 else 0.0,
            )
            for c in sorted(poll.choices, key=lambda x: x.order)
        ],
        category=poll.category,
        source_event=poll.source_event,
        source_event_url=poll.source_event_url,
        status=PollStatusEnum(status_value),
        created_at=poll.created_at,
        expires_at=poll.expires_at,
        scheduled_start=poll.scheduled_start,
        scheduled_end=poll.scheduled_end,
        is_active=poll.is_active,
        is_special=poll.is_special,
        duration_hours=poll.duration_hours,
        total_votes=total,
        is_featured=poll.is_featured,
        ai_generated=poll.ai_generated,
        poll_type=PollTypeEnum(_get_poll_type_value(poll.poll_type)),
        time_remaining_seconds=poll.time_remaining_seconds,
        demographic_breakdown=poll.demographic_results,
        confidence_interval=poll.confidence_interval,
    )
