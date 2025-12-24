"""
Schema converter functions.

Centralized helper functions for converting SQLAlchemy models to Pydantic schemas.
These are the single source of truth for model-to-schema conversions, ensuring DRY code.
"""

from typing import TYPE_CHECKING

from schemas.poll import (
    Poll,
    PollChoice,
    PollChoiceWithResults,
    PollStatusEnum,
    PollTypeEnum,
    PollWithResults,
)

if TYPE_CHECKING:
    from models.poll import Poll as PollModel


def poll_model_to_schema(poll: "PollModel") -> Poll:
    """
    Convert a Poll SQLAlchemy model to a Poll Pydantic schema.

    This is the single source of truth for Poll model -> schema conversion.
    Used by both public and admin endpoints.
    """
    return Poll(
        id=str(poll.id),
        question=poll.question,
        choices=[
            PollChoice(id=str(c.id), text=c.text, order=c.order)
            for c in sorted(poll.choices, key=lambda x: x.order)
        ],
        category=poll.category,
        source_event=poll.source_event,
        status=PollStatusEnum(poll.status),
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
        poll_type=PollTypeEnum(poll.poll_type) if poll.poll_type else PollTypeEnum.STANDARD,
        time_remaining_seconds=poll.time_remaining_seconds,
    )


def poll_model_to_results_schema(poll: "PollModel") -> PollWithResults:
    """
    Convert a Poll SQLAlchemy model to a PollWithResults Pydantic schema.

    This includes vote counts and percentages for each choice.
    This is the single source of truth for Poll model -> results schema conversion.
    Used by both public and admin endpoints.
    """
    total = poll.total_votes or 0

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
        status=PollStatusEnum(poll.status),
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
        poll_type=PollTypeEnum(poll.poll_type) if poll.poll_type else PollTypeEnum.STANDARD,
        time_remaining_seconds=poll.time_remaining_seconds,
        demographic_breakdown=poll.demographic_results,
        confidence_interval=poll.confidence_interval,
    )
