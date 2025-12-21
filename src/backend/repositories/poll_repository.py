"""
Poll repository for database operations.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.poll import Poll, PollChoice, PollStatus


class PollRepository:
    """Repository for poll database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_rowcount(self, result: Any) -> int:
        """Safely get rowcount from result."""
        return getattr(result, "rowcount", 0) or 0

    async def get_by_id(self, poll_id: str) -> Optional[Poll]:
        """Get a poll by ID with its choices."""
        result = await self.db.execute(select(Poll).options(selectinload(Poll.choices)).where(Poll.id == poll_id))
        return result.scalar_one_or_none()

    async def get_current_poll(self) -> Optional[Poll]:
        """Get the currently active poll."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.ACTIVE.value,
                    Poll.scheduled_start <= now,
                    Poll.scheduled_end > now,
                )
            )
            .order_by(Poll.scheduled_start.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_previous_poll(self) -> Optional[Poll]:
        """Get the most recently closed poll."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.CLOSED.value,
                    Poll.scheduled_end <= now,
                )
            )
            .order_by(Poll.scheduled_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_polls(self, limit: int = 5) -> list[Poll]:
        """Get polls scheduled for the future."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.SCHEDULED.value,
                    Poll.scheduled_start > now,
                )
            )
            .order_by(Poll.scheduled_start.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_polls(
        self,
        page: int = 1,
        per_page: int = 10,
        active_only: bool = True,
        category: Optional[str] = None,
    ) -> tuple[list[Poll], int]:
        """List polls with pagination."""
        query = select(Poll).options(selectinload(Poll.choices))
        count_query = select(func.count(Poll.id))

        if active_only:
            query = query.where(Poll.is_active == True)
            count_query = count_query.where(Poll.is_active == True)

        if category:
            query = query.where(Poll.category == category)
            count_query = count_query.where(Poll.category == category)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Poll.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        polls = list(result.scalars().all())

        return polls, total

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
    ) -> Poll:
        """Create a new poll with choices."""
        initial_status = status or PollStatus.SCHEDULED.value
        
        poll = Poll(
            id=str(uuid4()),
            question=question,
            category=category,
            source_event=source_event,
            source_event_url=source_event_url,
            status=initial_status,
            is_active=initial_status == PollStatus.ACTIVE.value,
            is_featured=is_featured,
            is_special=is_special,
            ai_generated=ai_generated,
            poll_type=poll_type,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            expires_at=scheduled_end,
            duration_hours=int((scheduled_end - scheduled_start).total_seconds() / 3600),
        )

        self.db.add(poll)
        await self.db.flush()

        # Create choices
        for idx, choice_text in enumerate(choices):
            choice = PollChoice(
                id=str(uuid4()),
                poll_id=poll.id,
                text=choice_text,
                order=idx,
                vote_count=0,
            )
            self.db.add(choice)

        await self.db.flush()
        await self.db.refresh(poll)

        return poll

    async def update_status(self, poll_id: str, status: PollStatus) -> bool:
        """Update poll status."""
        result = await self.db.execute(update(Poll).where(Poll.id == poll_id).values(status=status.value))
        return self._get_rowcount(result) > 0

    async def increment_vote_count(self, poll_id: str, choice_id: str) -> bool:
        """Increment vote count for a poll choice."""
        # Increment choice vote count
        await self.db.execute(
            update(PollChoice).where(PollChoice.id == choice_id).values(vote_count=PollChoice.vote_count + 1)
        )

        # Increment poll total votes
        await self.db.execute(update(Poll).where(Poll.id == poll_id).values(total_votes=Poll.total_votes + 1))

        return True

    async def decrement_vote_count(self, poll_id: str, choice_id: str) -> bool:
        """Decrement vote count for a poll choice (for vote retraction)."""
        # Decrement choice vote count
        await self.db.execute(
            update(PollChoice)
            .where(PollChoice.id == choice_id)
            .values(vote_count=func.greatest(0, PollChoice.vote_count - 1))
        )

        # Decrement poll total votes
        await self.db.execute(
            update(Poll).where(Poll.id == poll_id).values(total_votes=func.greatest(0, Poll.total_votes - 1))
        )

        return True

    async def close_expired_polls(self) -> int:
        """Close all polls that have passed their end time."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(Poll)
            .where(
                and_(
                    Poll.status == PollStatus.ACTIVE.value,
                    Poll.scheduled_end <= now,
                )
            )
            .values(
                status=PollStatus.CLOSED.value,
                is_active=False,
                closed_at=now,
            )
        )
        return self._get_rowcount(result)

    async def activate_scheduled_polls(self) -> int:
        """Activate polls that have reached their start time."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(Poll)
            .where(
                and_(
                    Poll.status == PollStatus.SCHEDULED.value,
                    Poll.scheduled_start <= now,
                    Poll.scheduled_end > now,
                )
            )
            .values(status=PollStatus.ACTIVE.value)
        )
        return self._get_rowcount(result)

    # ========================================================================
    # Poll Type Methods (Pulse and Flash)
    # ========================================================================

    async def get_current_poll_by_type(self, poll_type: str) -> Optional[Poll]:
        """Get the currently active poll of a specific type."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.ACTIVE.value,
                    Poll.poll_type == poll_type,
                    Poll.scheduled_start <= now,
                    Poll.scheduled_end > now,
                )
            )
            .order_by(Poll.scheduled_start.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_previous_poll_by_type(self, poll_type: str) -> Optional[Poll]:
        """Get the most recently closed poll of a specific type."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.CLOSED.value,
                    Poll.poll_type == poll_type,
                    Poll.scheduled_end <= now,
                )
            )
            .order_by(Poll.scheduled_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_polls_by_type(self, poll_type: str, limit: int = 5) -> list[Poll]:
        """Get upcoming scheduled polls of a specific type."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Poll)
            .options(selectinload(Poll.choices))
            .where(
                and_(
                    Poll.status == PollStatus.SCHEDULED.value,
                    Poll.poll_type == poll_type,
                    Poll.scheduled_start > now,
                )
            )
            .order_by(Poll.scheduled_start.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_polls_by_type(
        self,
        poll_type: str,
        page: int = 1,
        per_page: int = 10,
        active_only: bool = True,
    ) -> tuple[list[Poll], int]:
        """List polls of a specific type with pagination."""
        query = select(Poll).options(selectinload(Poll.choices))
        count_query = select(func.count(Poll.id))

        # Filter by type
        query = query.where(Poll.poll_type == poll_type)
        count_query = count_query.where(Poll.poll_type == poll_type)

        if active_only:
            query = query.where(Poll.is_active == True)
            count_query = count_query.where(Poll.is_active == True)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Poll.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        polls = list(result.scalars().all())

        return polls, total

    async def delete_poll(self, poll_id: str) -> bool:
        """Delete a poll and its choices by ID."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False
        
        # Delete choices first (foreign key constraint)
        for choice in poll.choices:
            await self.db.delete(choice)
        
        # Delete the poll
        await self.db.delete(poll)
        await self.db.commit()
        return True

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
    ) -> tuple[list[Poll], int]:
        """Get all polls with advanced filtering for admin views."""
        query = select(Poll).options(selectinload(Poll.choices))
        count_query = select(func.count(Poll.id))

        # Apply filters
        if status_filter:
            query = query.where(Poll.status == status_filter)
            count_query = count_query.where(Poll.status == status_filter)

        if poll_type:
            query = query.where(Poll.poll_type == poll_type)
            count_query = count_query.where(Poll.poll_type == poll_type)

        if not include_inactive:
            query = query.where(Poll.is_active == True)
            count_query = count_query.where(Poll.is_active == True)

        if ai_generated_filter is not None:
            query = query.where(Poll.ai_generated == ai_generated_filter)
            count_query = count_query.where(Poll.ai_generated == ai_generated_filter)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(Poll.question.ilike(search_pattern))
            count_query = count_query.where(Poll.question.ilike(search_pattern))

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results (most recent first)
        query = query.order_by(Poll.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        polls = list(result.scalars().all())

        return polls, total

    async def get_poll_statistics(self) -> dict:
        """Get aggregate statistics about polls for admin dashboard."""
        # Total polls
        total_result = await self.db.execute(select(func.count(Poll.id)))
        total_polls = total_result.scalar() or 0

        # Active polls
        active_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.status == PollStatus.ACTIVE.value)
        )
        active_polls = active_result.scalar() or 0

        # Scheduled polls
        scheduled_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.status == PollStatus.SCHEDULED.value)
        )
        scheduled_polls = scheduled_result.scalar() or 0

        # Closed polls
        closed_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.status == PollStatus.CLOSED.value)
        )
        closed_polls = closed_result.scalar() or 0

        # Polls with votes
        polls_with_votes_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.total_votes > 0)
        )
        polls_with_votes = polls_with_votes_result.scalar() or 0

        # Total votes across all polls
        total_votes_result = await self.db.execute(
            select(func.sum(Poll.total_votes))
        )
        total_votes = total_votes_result.scalar() or 0

        # AI generated vs manual
        ai_generated_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.ai_generated == True)
        )
        ai_generated_count = ai_generated_result.scalar() or 0

        manual_count = total_polls - ai_generated_count

        return {
            "total_polls": total_polls,
            "active_polls": active_polls,
            "scheduled_polls": scheduled_polls,
            "closed_polls": closed_polls,
            "polls_with_votes": polls_with_votes,
            "total_votes": total_votes,
            "ai_generated_count": ai_generated_count,
            "manual_count": manual_count,
        }

    async def update_poll(
        self,
        poll_id: str,
        update_fields: dict,
        new_choices: Optional[list] = None,
    ) -> Optional[Poll]:
        """Update a poll with the given fields."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return None

        # Update scalar fields
        for field, value in update_fields.items():
            if hasattr(poll, field):
                setattr(poll, field, value)

        # Update choices if provided
        if new_choices is not None:
            # Delete existing choices
            for choice in poll.choices:
                await self.db.delete(choice)
            
            # Create new choices
            for idx, choice_data in enumerate(new_choices):
                choice = PollChoice(
                    id=str(uuid4()),
                    poll_id=poll.id,
                    text=choice_data.text if hasattr(choice_data, 'text') else choice_data,
                    order=choice_data.order if hasattr(choice_data, 'order') else idx,
                    vote_count=0,
                )
                self.db.add(choice)

        await self.db.commit()
        await self.db.refresh(poll)
        
        return poll

