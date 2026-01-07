"""
Cosmos DB Poll repository.

Handles poll CRUD operations using Azure Cosmos DB with embedded choices.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from db.cosmos_session import (
    POLLS_CONTAINER,
    create_item,
    delete_item,
    query_count,
    query_items,
    read_item,
    upsert_item,
)
from models.cosmos_documents import (
    PollChoiceDocument,
    PollDocument,
    PollStatus,
    PollType,
)

logger = logging.getLogger(__name__)


class CosmosPollRepository:
    """Repository for poll operations using Cosmos DB."""

    # ========================================================================
    # Read Operations
    # ========================================================================

    async def get_by_id(self, poll_id: str) -> Optional[PollDocument]:
        """Get a poll by ID (direct point read - very efficient)."""
        data = await read_item(POLLS_CONTAINER, poll_id, partition_key=poll_id)
        if data is None:
            return None
        return PollDocument(**data)

    async def get_current_poll(self) -> Optional[PollDocument]:
        """Get the currently active poll."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.scheduled_start <= @now
              AND c.scheduled_end > @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_start DESC
            OFFSET 0 LIMIT 1
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.ACTIVE.value},
                {"name": "@now", "value": now},
            ],
        )
        if not results:
            return None
        return PollDocument(**results[0])

    async def get_previous_poll(self) -> Optional[PollDocument]:
        """Get the most recently closed poll."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.scheduled_end <= @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_end DESC
            OFFSET 0 LIMIT 1
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.CLOSED.value},
                {"name": "@now", "value": now},
            ],
        )
        if not results:
            return None
        return PollDocument(**results[0])

    async def get_upcoming_polls(self, limit: int = 5) -> list[PollDocument]:
        """Get polls scheduled for the future."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.scheduled_start > @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_start ASC
            OFFSET 0 LIMIT @limit
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.SCHEDULED.value},
                {"name": "@now", "value": now},
                {"name": "@limit", "value": limit},
            ],
        )
        return [PollDocument(**r) for r in results]

    async def list_polls(
        self,
        page: int = 1,
        per_page: int = 10,
        active_only: bool = True,
        category: Optional[str] = None,
    ) -> tuple[list[PollDocument], int]:
        """List polls with pagination."""
        offset = (page - 1) * per_page

        # Build query conditions
        conditions = ["(NOT IS_DEFINED(c.document_type) OR c.document_type = null)"]
        parameters: list[dict[str, Any]] = []

        if active_only:
            conditions.append("c.is_active = true")

        if category:
            conditions.append("c.category = @category")
            parameters.append({"name": "@category", "value": category})

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        total = await query_count(POLLS_CONTAINER, count_query, parameters=parameters)

        # Get paginated results
        parameters.extend(
            [
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": per_page},
            ]
        )

        query = f"""
            SELECT * FROM c
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(POLLS_CONTAINER, query, parameters=parameters)
        polls = [PollDocument(**r) for r in results]

        return polls, total

    # ========================================================================
    # Write Operations
    # ========================================================================

    async def create(
        self,
        question: str,
        choices: list[str],
        category: str,
        scheduled_start: datetime,
        scheduled_end: datetime,
        source_event: Optional[str] = None,
        source_event_url: Optional[str] = None,
        is_featured: bool = False,
        ai_generated: bool = False,
        poll_type: str = "standard",
        is_special: bool = False,
        status: Optional[str] = None,
    ) -> PollDocument:
        """Create a new poll with embedded choices."""
        poll_id = str(uuid4())
        initial_status = status or PollStatus.SCHEDULED.value
        now = datetime.now(timezone.utc)

        # Create choice documents
        choice_docs = [
            PollChoiceDocument(
                id=str(uuid4()),
                text=choice_text,
                order=idx,
                vote_count=0,
            )
            for idx, choice_text in enumerate(choices)
        ]

        poll = PollDocument(
            id=poll_id,
            question=question,
            category=category,
            source_event=source_event,
            source_event_url=source_event_url,
            status=PollStatus(initial_status),
            poll_type=PollType(poll_type),
            is_active=initial_status == PollStatus.ACTIVE.value,
            is_featured=is_featured,
            is_special=is_special,
            ai_generated=ai_generated,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            expires_at=scheduled_end,
            duration_hours=int((scheduled_end - scheduled_start).total_seconds() / 3600),
            choices=choice_docs,
            total_votes=0,
            created_at=now,
        )

        await create_item(POLLS_CONTAINER, poll.model_dump(mode="json"))
        logger.info(f"Created poll {poll_id}: {question[:50]}...")
        return poll

    async def update(self, poll: PollDocument) -> PollDocument:
        """Update a poll document."""
        await upsert_item(POLLS_CONTAINER, poll.model_dump(mode="json"))
        return poll

    async def delete(self, poll_id: str) -> bool:
        """Delete a poll."""
        try:
            await delete_item(POLLS_CONTAINER, poll_id, partition_key=poll_id)
            logger.info(f"Deleted poll {poll_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete poll {poll_id}: {e}")
            return False

    async def update_status(self, poll_id: str, status: PollStatus) -> bool:
        """Update poll status."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False

        poll.status = status
        poll.is_active = status == PollStatus.ACTIVE

        if status == PollStatus.CLOSED:
            poll.closed_at = datetime.now(timezone.utc)

        await self.update(poll)
        return True

    async def increment_vote_count(self, poll_id: str, choice_id: str) -> bool:
        """Increment vote count for a poll choice."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False

        # Find and increment the choice
        for choice in poll.choices:
            if choice.id == choice_id:
                choice.vote_count += 1
                break
        else:
            logger.warning(f"Choice {choice_id} not found in poll {poll_id}")
            return False

        # Increment total votes
        poll.total_votes += 1

        await self.update(poll)
        return True

    async def decrement_vote_count(self, poll_id: str, choice_id: str) -> bool:
        """Decrement vote count for a poll choice (for vote retraction)."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False

        # Find and decrement the choice
        for choice in poll.choices:
            if choice.id == choice_id:
                choice.vote_count = max(0, choice.vote_count - 1)
                break
        else:
            return False

        # Decrement total votes
        poll.total_votes = max(0, poll.total_votes - 1)

        await self.update(poll)
        return True

    async def close_expired_polls(self) -> int:
        """Close all polls that have passed their end time."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.scheduled_end <= @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.ACTIVE.value},
                {"name": "@now", "value": now_iso},
            ],
        )

        closed_count = 0
        for result in results:
            poll = PollDocument(**result)
            poll.status = PollStatus.CLOSED
            poll.is_active = False
            poll.closed_at = now
            await self.update(poll)
            closed_count += 1

        if closed_count > 0:
            logger.info(f"Closed {closed_count} expired polls")

        return closed_count

    async def activate_scheduled_polls(self) -> int:
        """Activate polls that have reached their start time."""
        now = datetime.now(timezone.utc).isoformat()

        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.scheduled_start <= @now
              AND c.scheduled_end > @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.SCHEDULED.value},
                {"name": "@now", "value": now},
            ],
        )

        activated_count = 0
        for result in results:
            poll = PollDocument(**result)
            poll.status = PollStatus.ACTIVE
            poll.is_active = True
            await self.update(poll)
            activated_count += 1

        if activated_count > 0:
            logger.info(f"Activated {activated_count} scheduled polls")

        return activated_count

    # ========================================================================
    # Poll Type Methods (Pulse and Flash)
    # ========================================================================

    async def get_current_poll_by_type(self, poll_type: str) -> Optional[PollDocument]:
        """Get the currently active poll of a specific type."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.poll_type = @poll_type
              AND c.scheduled_start <= @now
              AND c.scheduled_end > @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_start DESC
            OFFSET 0 LIMIT 1
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.ACTIVE.value},
                {"name": "@poll_type", "value": poll_type},
                {"name": "@now", "value": now},
            ],
        )
        if not results:
            return None
        return PollDocument(**results[0])

    async def get_previous_poll_by_type(self, poll_type: str) -> Optional[PollDocument]:
        """Get the most recently closed poll of a specific type."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.poll_type = @poll_type
              AND c.scheduled_end <= @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_end DESC
            OFFSET 0 LIMIT 1
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.CLOSED.value},
                {"name": "@poll_type", "value": poll_type},
                {"name": "@now", "value": now},
            ],
        )
        if not results:
            return None
        return PollDocument(**results[0])

    async def get_upcoming_polls_by_type(self, poll_type: str, limit: int = 5) -> list[PollDocument]:
        """Get upcoming scheduled polls of a specific type."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.status = @status
              AND c.poll_type = @poll_type
              AND c.scheduled_start > @now
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
            ORDER BY c.scheduled_start ASC
            OFFSET 0 LIMIT @limit
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@status", "value": PollStatus.SCHEDULED.value},
                {"name": "@poll_type", "value": poll_type},
                {"name": "@now", "value": now},
                {"name": "@limit", "value": limit},
            ],
        )
        return [PollDocument(**r) for r in results]

    async def list_polls_by_type(
        self,
        poll_type: str,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None,
    ) -> tuple[list[PollDocument], int]:
        """List polls of a specific type with pagination."""
        offset = (page - 1) * per_page

        # Build query conditions
        conditions = [
            "c.poll_type = @poll_type",
            "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)",
        ]
        parameters: list[dict[str, Any]] = [
            {"name": "@poll_type", "value": poll_type},
        ]

        if status:
            conditions.append("c.status = @status")
            parameters.append({"name": "@status", "value": status})

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        total = await query_count(POLLS_CONTAINER, count_query, parameters=parameters)

        # Get paginated results
        parameters.extend(
            [
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": per_page},
            ]
        )

        query = f"""
            SELECT * FROM c
            WHERE {where_clause}
            ORDER BY c.scheduled_start DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(POLLS_CONTAINER, query, parameters=parameters)
        polls = [PollDocument(**r) for r in results]

        return polls, total

    async def get_polls_by_category(
        self,
        category: str,
        limit: int = 10,
        include_closed: bool = True,
    ) -> list[PollDocument]:
        """Get polls by category."""
        conditions = [
            "c.category = @category",
            "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)",
        ]

        if not include_closed:
            conditions.append("c.status != @closed_status")

        where_clause = " AND ".join(conditions)

        parameters: list[dict[str, Any]] = [
            {"name": "@category", "value": category},
            {"name": "@limit", "value": limit},
        ]

        if not include_closed:
            parameters.append({"name": "@closed_status", "value": PollStatus.CLOSED.value})

        query = f"""
            SELECT * FROM c
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            OFFSET 0 LIMIT @limit
        """
        results = await query_items(POLLS_CONTAINER, query, parameters=parameters)
        return [PollDocument(**r) for r in results]

    async def update_demographic_results(
        self,
        poll_id: str,
        demographic_results: dict[str, Any],
    ) -> bool:
        """Update poll's demographic results aggregation."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False

        poll.demographic_results = demographic_results
        await self.update(poll)
        return True

    async def count_polls_by_status(self, status: PollStatus) -> int:
        """Count polls by status."""
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.status = @status
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = null)
        """
        return await query_count(
            POLLS_CONTAINER,
            query,
            parameters=[{"name": "@status", "value": status.value}],
        )

    async def get_polls_created_since(
        self,
        since: datetime,
        poll_type: Optional[str] = None,
    ) -> list[PollDocument]:
        """Get polls created since a specific time."""
        conditions = [
            "c.created_at >= @since",
            "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)",
        ]
        parameters: list[dict[str, Any]] = [
            {"name": "@since", "value": since.isoformat()},
        ]

        if poll_type:
            conditions.append("c.poll_type = @poll_type")
            parameters.append({"name": "@poll_type", "value": poll_type})

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT * FROM c
            WHERE {where_clause}
            ORDER BY c.created_at DESC
        """
        results = await query_items(POLLS_CONTAINER, query, parameters=parameters)
        return [PollDocument(**r) for r in results]

    # ========================================================================
    # Admin Methods
    # ========================================================================

    async def get_all_polls(
        self,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        poll_type: Optional[str] = None,
        include_inactive: bool = True,
        ai_generated_filter: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> tuple[list[PollDocument], int]:
        """Get all polls with advanced filtering for admin views."""
        offset = (page - 1) * per_page

        # Build query conditions
        conditions = ["(NOT IS_DEFINED(c.document_type) OR c.document_type = null)"]
        parameters: list[dict[str, Any]] = []

        if status_filter:
            conditions.append("c.status = @status")
            parameters.append({"name": "@status", "value": status_filter})

        if poll_type:
            conditions.append("c.poll_type = @poll_type")
            parameters.append({"name": "@poll_type", "value": poll_type})

        if not include_inactive:
            conditions.append("c.is_active = true")

        if ai_generated_filter is not None:
            conditions.append("c.ai_generated = @ai_generated")
            parameters.append({"name": "@ai_generated", "value": ai_generated_filter})

        if search_query:
            conditions.append("CONTAINS(LOWER(c.question), @search)")
            parameters.append({"name": "@search", "value": search_query.lower()})

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        total = await query_count(POLLS_CONTAINER, count_query, parameters=parameters)

        # Get paginated results
        parameters.extend(
            [
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": per_page},
            ]
        )

        query = f"""
            SELECT * FROM c
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(POLLS_CONTAINER, query, parameters=parameters)
        polls = [PollDocument(**r) for r in results]

        return polls, total

    async def get_poll_statistics(self) -> dict[str, Any]:
        """Get aggregate statistics about polls for admin dashboard."""
        base_condition = "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)"

        # Total polls
        total_query = f"SELECT VALUE COUNT(1) FROM c WHERE {base_condition}"
        total_polls = await query_count(POLLS_CONTAINER, total_query)

        # Active polls
        active_query = f"""
            SELECT VALUE COUNT(1) FROM c
            WHERE {base_condition} AND c.status = @status
        """
        active_polls = await query_count(
            POLLS_CONTAINER,
            active_query,
            parameters=[{"name": "@status", "value": PollStatus.ACTIVE.value}],
        )

        # Scheduled polls
        scheduled_polls = await query_count(
            POLLS_CONTAINER,
            active_query,
            parameters=[{"name": "@status", "value": PollStatus.SCHEDULED.value}],
        )

        # Closed polls
        closed_polls = await query_count(
            POLLS_CONTAINER,
            active_query,
            parameters=[{"name": "@status", "value": PollStatus.CLOSED.value}],
        )

        # Polls with votes
        polls_with_votes_query = f"""
            SELECT VALUE COUNT(1) FROM c
            WHERE {base_condition} AND c.total_votes > 0
        """
        polls_with_votes = await query_count(POLLS_CONTAINER, polls_with_votes_query)

        # Total votes across all polls
        total_votes_query = f"""
            SELECT VALUE SUM(c.total_votes) FROM c
            WHERE {base_condition}
        """
        total_votes_result = await query_items(POLLS_CONTAINER, total_votes_query)
        total_votes: int = (
            int(total_votes_result[0])  # type: ignore[arg-type]
            if total_votes_result and total_votes_result[0] is not None
            else 0
        )

        # AI generated vs manual
        ai_generated_query = f"""
            SELECT VALUE COUNT(1) FROM c
            WHERE {base_condition} AND c.ai_generated = true
        """
        ai_generated_count = await query_count(POLLS_CONTAINER, ai_generated_query)

        manual_count = total_polls - ai_generated_count

        return {
            "total_polls": total_polls,
            "active_polls": active_polls,
            "scheduled_polls": scheduled_polls,
            "closed_polls": closed_polls,
            "polls_with_votes": polls_with_votes,
            "total_votes": total_votes or 0,
            "ai_generated_count": ai_generated_count,
            "manual_count": manual_count,
        }

    async def update_poll(
        self,
        poll_id: str,
        update_fields: dict[str, Any],
        new_choices: Optional[list[Any]] = None,
    ) -> Optional[PollDocument]:
        """Update a poll with the given fields and optionally replace choices."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return None

        # Update scalar fields
        for field, value in update_fields.items():
            if hasattr(poll, field):
                setattr(poll, field, value)

        # Update choices if provided
        if new_choices is not None:
            poll.choices = [
                PollChoiceDocument(
                    id=str(uuid4()),
                    text=choice.text if hasattr(choice, "text") else str(choice),
                    order=choice.order if hasattr(choice, "order") else idx,
                    vote_count=0,
                )
                for idx, choice in enumerate(new_choices)
            ]

        await self.update(poll)
        return poll

    async def count_published_polls(self) -> int:
        """
        Count published polls (active, closed, or archived - excludes scheduled).

        Used for platform statistics.
        """
        base_condition = "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)"
        query = f"""
            SELECT VALUE COUNT(1) FROM c
            WHERE {base_condition}
              AND c.status IN (@active, @closed, @archived)
        """
        return await query_count(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@active", "value": PollStatus.ACTIVE.value},
                {"name": "@closed", "value": PollStatus.CLOSED.value},
                {"name": "@archived", "value": PollStatus.ARCHIVED.value},
            ],
        )

    async def count_completed_polls(self) -> int:
        """
        Count completed pulse and flash polls (closed or archived).

        Used for platform statistics.
        """
        base_condition = "(NOT IS_DEFINED(c.document_type) OR c.document_type = null)"
        query = f"""
            SELECT VALUE COUNT(1) FROM c
            WHERE {base_condition}
              AND c.status IN (@closed, @archived)
              AND c.poll_type IN (@pulse, @flash)
        """
        return await query_count(
            POLLS_CONTAINER,
            query,
            parameters=[
                {"name": "@closed", "value": PollStatus.CLOSED.value},
                {"name": "@archived", "value": PollStatus.ARCHIVED.value},
                {"name": "@pulse", "value": PollType.PULSE.value},
                {"name": "@flash", "value": PollType.FLASH.value},
            ],
        )
