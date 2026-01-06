"""
Poll Scheduler Service

Manages the hourly poll rotation system:
- Creates new polls at the top of each hour
- Closes expired polls and updates their status
- Retrieves current and previous polls

The scheduler uses APScheduler to run background tasks.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import structlog
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.poll import Poll, PollChoice, PollStatus
from repositories.feedback_repository import FeedbackRepository

logger = structlog.get_logger(__name__)


class PollScheduler:
    """
    Manages hourly poll rotation.

    Features:
    - Automatically activates scheduled polls at the top of each hour
    - Closes polls when their duration expires
    - Provides access to current and previous polls
    - Supports special polls with custom durations
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.poll_duration_hours = settings.POLL_DURATION_HOURS

    @staticmethod
    def get_current_poll_window() -> tuple[datetime, datetime]:
        """
        Get the current poll window (start and end times).

        Polls start at the top of each hour based on POLL_DURATION_HOURS.
        For 1-hour polls: 10:00-11:00, 11:00-12:00, etc.
        For 2-hour polls: 10:00-12:00, 12:00-14:00, etc.
        """
        now = datetime.now(timezone.utc)
        duration = settings.POLL_DURATION_HOURS

        # Calculate the start of the current window
        hours_since_midnight = now.hour
        window_start_hour = (hours_since_midnight // duration) * duration

        window_start = now.replace(
            hour=window_start_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        window_end = window_start + timedelta(hours=duration)

        return window_start, window_end

    @staticmethod
    def get_previous_poll_window() -> tuple[datetime, datetime]:
        """Get the previous poll window."""
        current_start, _ = PollScheduler.get_current_poll_window()
        duration = settings.POLL_DURATION_HOURS

        previous_end = current_start
        previous_start = previous_end - timedelta(hours=duration)

        return previous_start, previous_end

    @staticmethod
    def get_next_poll_window() -> tuple[datetime, datetime]:
        """Get the next poll window."""
        _, current_end = PollScheduler.get_current_poll_window()
        duration = settings.POLL_DURATION_HOURS

        next_start = current_end
        next_end = next_start + timedelta(hours=duration)

        return next_start, next_end

    async def get_current_poll(self) -> Optional[Poll]:
        """
        Get the currently active poll.

        Returns the poll scheduled for the current time window,
        or any special poll that is currently active.
        """
        now = datetime.now(timezone.utc)
        window_start, window_end = self.get_current_poll_window()

        # First, check for any active special polls
        special_poll_query = (
            select(Poll)
            .where(
                and_(
                    Poll.is_special == True,
                    Poll.status == PollStatus.ACTIVE.value,
                    Poll.scheduled_start <= now,
                    Poll.scheduled_end > now,
                )
            )
            .order_by(Poll.created_at.desc())
        )

        result = await self.db.execute(special_poll_query)
        special_poll = result.scalar_one_or_none()
        if special_poll:
            return special_poll

        # Get the regular poll for this time window
        query = select(Poll).where(
            and_(
                Poll.is_special == False,
                Poll.status == PollStatus.ACTIVE.value,
                Poll.scheduled_start == window_start,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_previous_poll(self) -> Optional[Poll]:
        """
        Get the most recently closed poll.

        Returns the poll from the previous time window.
        """
        previous_start, previous_end = self.get_previous_poll_window()

        query = select(Poll).where(
            and_(
                Poll.is_special == False,
                Poll.status == PollStatus.CLOSED.value,
                Poll.scheduled_start == previous_start,
            )
        )

        result = await self.db.execute(query)
        poll = result.scalar_one_or_none()

        # If no poll from previous window, get the most recently closed poll
        if not poll:
            fallback_query = (
                select(Poll)
                .where(
                    Poll.status == PollStatus.CLOSED.value,
                )
                .order_by(Poll.closed_at.desc())
                .limit(1)
            )

            result = await self.db.execute(fallback_query)
            poll = result.scalar_one_or_none()

        return poll

    async def get_upcoming_polls(self, limit: int = 5) -> list[Poll]:
        """Get polls scheduled for future time windows."""
        now = datetime.now(timezone.utc)

        query = (
            select(Poll)
            .where(
                and_(
                    Poll.status == PollStatus.SCHEDULED.value,
                    Poll.scheduled_start > now,
                )
            )
            .order_by(Poll.scheduled_start.asc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def schedule_poll(
        self,
        question: str,
        choices: list[str],
        category: str,
        source_event: Optional[str] = None,
        source_event_url: Optional[str] = None,
        scheduled_start: Optional[datetime] = None,
        duration_hours: Optional[int] = None,
        is_special: bool = False,
        ai_generated: bool = False,
    ) -> Poll:
        """
        Schedule a new poll.

        Args:
            question: The poll question
            choices: List of choice texts (2-10 options)
            category: Poll category
            source_event: Optional source event description
            source_event_url: Optional URL to source
            scheduled_start: When to start (defaults to next available slot)
            duration_hours: Custom duration (defaults to settings)
            is_special: Whether this is a special extended poll
            ai_generated: Whether AI generated this poll

        Returns:
            The created Poll instance
        """
        if scheduled_start is None:
            # Schedule for the next available window
            next_start, _ = self.get_next_poll_window()
            scheduled_start = next_start

        if duration_hours is None:
            duration_hours = self.poll_duration_hours

        scheduled_end = scheduled_start + timedelta(hours=duration_hours)

        # Create the poll
        poll = Poll(
            id=str(uuid4()),
            question=question,
            category=category,
            source_event=source_event,
            source_event_url=source_event_url,
            status=PollStatus.SCHEDULED.value,
            is_active=False,
            is_featured=True,
            is_special=is_special,
            duration_hours=duration_hours,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            expires_at=scheduled_end,
            ai_generated=ai_generated,
            total_votes=0,
        )

        self.db.add(poll)

        # Create choices
        for order, choice_text in enumerate(choices):
            choice = PollChoice(
                id=str(uuid4()),
                poll_id=poll.id,
                text=choice_text,
                order=order,
                vote_count=0,
            )
            self.db.add(choice)

        await self.db.commit()
        await self.db.refresh(poll)

        logger.info(
            f"Scheduled poll '{question[:50]}...' for {scheduled_start} "
            f"(duration: {duration_hours}h, special: {is_special})"
        )

        return poll

    async def activate_scheduled_polls(self) -> list[Poll]:
        """
        Activate polls whose scheduled start time has arrived.

        Called by the background scheduler at the top of each hour.
        """
        now = datetime.now(timezone.utc)

        # Find polls that should be activated
        query = select(Poll).where(
            and_(
                Poll.status == PollStatus.SCHEDULED.value,
                Poll.scheduled_start <= now,
                Poll.scheduled_end > now,
            )
        )

        result = await self.db.execute(query)
        polls_to_activate = list(result.scalars().all())

        for poll in polls_to_activate:
            poll.status = PollStatus.ACTIVE.value
            poll.is_active = True
            logger.info(f"Activated poll: {poll.id} - '{poll.question[:50]}...'")

        if polls_to_activate:
            await self.db.commit()

        return polls_to_activate

    async def close_expired_polls(self) -> list[Poll]:
        """
        Close polls whose scheduled end time has passed.

        Called by the background scheduler.
        """
        now = datetime.now(timezone.utc)

        # Find polls that should be closed
        query = select(Poll).where(
            and_(
                Poll.status == PollStatus.ACTIVE.value,
                Poll.scheduled_end <= now,
            )
        )

        result = await self.db.execute(query)
        polls_to_close = list(result.scalars().all())

        for poll in polls_to_close:
            poll.status = PollStatus.CLOSED.value
            poll.is_active = False
            poll.closed_at = now
            logger.info(f"Closed poll: {poll.id} - '{poll.question[:50]}...' (total votes: {poll.total_votes})")

        if polls_to_close:
            await self.db.commit()

        return polls_to_close

    async def run_rotation_cycle(self) -> dict:
        """
        Run a complete poll rotation cycle.

        This should be called at the top of each hour (or poll interval).
        Handles both pulse (daily 12-hour) and flash (hourly) polls independently.

        Returns:
            Summary of actions taken
        """
        logger.info("Running poll rotation cycle...")

        # 1. Close expired polls
        closed_polls = await self.close_expired_polls()

        # 2. Activate scheduled polls
        activated_polls = await self.activate_scheduled_polls()

        # 3. Generate polls if auto-generate is enabled
        generated_poll = None
        if settings.POLL_AUTO_GENERATE:
            # Check if we need to generate a poll
            # The _generate_poll_from_events method determines the correct poll type
            # (pulse vs flash) based on the current time window
            generated_poll = await self._generate_poll_from_events()

        # Get current poll status for return value
        current_poll = await self.get_current_poll()

        return {
            "closed_count": len(closed_polls),
            "activated_count": len(activated_polls),
            "activated_polls": activated_polls,
            "current_poll_id": current_poll.id if current_poll else None,
            "generated_poll": generated_poll,
        }

    async def _get_recently_used_categories(self, hours: int = 48) -> set[str]:
        """
        Get categories used in recent polls to ensure topic diversity.

        Args:
            hours: Number of hours to look back

        Returns:
            Set of category names recently used
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            select(Poll.category)
            .where(
                and_(
                    Poll.created_at >= cutoff,
                    Poll.ai_generated == True,
                )
            )
            .distinct()
        )
        result = await self.db.execute(query)
        return {row[0] for row in result.fetchall() if row[0]}

    async def _get_recently_used_event_titles(self, hours: int = 72) -> set[str]:
        """
        Get source event titles used recently to avoid duplicate topics.

        Args:
            hours: Number of hours to look back

        Returns:
            Set of normalized event titles (lowercase, stripped)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = select(Poll.source_event).where(
            and_(
                Poll.created_at >= cutoff,
                Poll.source_event.isnot(None),
            )
        )
        result = await self.db.execute(query)
        return {row[0].lower().strip() for row in result.fetchall() if row[0]}

    async def _determine_next_poll_type(self) -> tuple[str, datetime, datetime]:
        """
        Determine whether to generate a pulse or flash poll based on schedule.

        Flash polls: Run every 3 hours (0:00, 3:00, 6:00, 9:00, 12:00, 15:00, 18:00, 21:00 UTC)
                     Each flash poll is open for 1 hour only.
        Pulse polls: Run 8am-8pm ET (12 hours), one per day during prime hours.

        Returns:
            Tuple of (poll_type, window_start, window_end)
        """
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)

        # Check if we already have an active pulse poll today (8am-8pm ET)
        if 8 <= now_et.hour < 20:
            # Check for existing pulse poll today
            today_start_et = now_et.replace(hour=8, minute=0, second=0, microsecond=0)
            today_start_utc = today_start_et.astimezone(timezone.utc)

            query = select(Poll).where(
                and_(
                    Poll.poll_type == "pulse",
                    Poll.scheduled_start >= today_start_utc,
                )
            )
            result = await self.db.execute(query)
            existing_pulse = result.scalar_one_or_none()

            if not existing_pulse:
                # No pulse poll today, create one
                pulse_start, pulse_end = get_pulse_poll_window()
                logger.info(f"Creating daily pulse poll for {pulse_start.isoformat()} to {pulse_end.isoformat()}")
                return "pulse", pulse_start, pulse_end

        # Otherwise, schedule a flash poll
        # Flash polls run at: 0:00, 3:00, 6:00, 9:00, 12:00, 15:00, 18:00, 21:00 UTC
        flash_start, flash_end = get_next_flash_poll_window()
        logger.info(f"Scheduling flash poll for {flash_start.isoformat()} (1 hour duration)")
        return "flash", flash_start, flash_end

    async def _generate_poll_from_events(self) -> Optional[Poll]:
        """
        Generate a new poll from current events using the AI system.

        Uses the EventAggregator to fetch trending events and
        the PollGenerator to create unbiased poll questions.

        Ensures:
        - Alternating between pulse and flash poll types
        - Different categories/topics from recent polls
        - Diverse event selection
        - No duplicate polls for the same time window
        """
        from ai.event_aggregator import EventAggregator
        from ai.poll_generator import PollGenerator

        try:
            # Determine which poll type to generate and get the time window
            poll_type, window_start, window_end = await self._determine_next_poll_type()

            # *** CRITICAL: Check if a poll already exists for this time window ***
            # This prevents duplicate polls from concurrent scheduler invocations
            existing_poll_query = select(Poll).where(
                and_(
                    Poll.poll_type == poll_type,
                    Poll.scheduled_start == window_start,
                )
            )
            result = await self.db.execute(existing_poll_query)
            existing_poll = result.scalar_one_or_none()

            if existing_poll:
                logger.info(
                    f"Poll already exists for {poll_type} window {window_start.isoformat()}: "
                    f"{existing_poll.id} - skipping generation"
                )
                return existing_poll

            # Get recently used categories and events to avoid repetition
            recent_categories = await self._get_recently_used_categories(hours=24)
            recent_events = await self._get_recently_used_event_titles(hours=72)

            logger.info(f"Generating {poll_type} poll, avoiding categories: {recent_categories}")

            # Initialize the event aggregator
            async with EventAggregator() as aggregator:
                # Define all available categories
                all_categories = [
                    "politics",
                    "business",
                    "technology",
                    "health",
                    "environment",
                    "science",
                    "world",
                    "entertainment",
                    "sports",
                ]

                # Prioritize categories NOT recently used
                prioritized_categories = [c for c in all_categories if c not in recent_categories]
                if not prioritized_categories:
                    # All categories used recently, reset
                    prioritized_categories = all_categories

                # Fetch trending events from prioritized categories
                logger.info(f"Fetching events from prioritized categories: {prioritized_categories[:5]}")
                events = await aggregator.fetch_trending_events(
                    categories=prioritized_categories[:5],  # API limit on categories
                    limit=30,
                )

            if not events:
                logger.warning("No trending events available for poll generation")
                return None

            # Filter out events similar to recently used ones
            filtered_events = []
            for event in events:
                event_title_normalized = event.title.lower().strip()
                # Check if this event is too similar to recent ones
                is_duplicate = False
                for recent in recent_events:
                    # Simple word overlap check
                    event_words = set(event_title_normalized.split())
                    recent_words = set(recent.split())
                    if event_words and recent_words:
                        overlap = len(event_words & recent_words) / len(event_words | recent_words)
                        if overlap > 0.5:  # More than 50% word overlap
                            is_duplicate = True
                            break
                if not is_duplicate:
                    filtered_events.append(event)

            if not filtered_events:
                logger.warning("All events filtered as duplicates, using original list")
                filtered_events = events[:10]

            logger.info(f"Filtered to {len(filtered_events)} unique events from {len(events)} total")

            # Fetch feedback guidance for categories being used
            feedback_repo = FeedbackRepository(self.db)
            feedback_guidance_by_category: dict[str, list[str]] = {}

            categories_in_events = set(e.category for e in filtered_events)
            for category in categories_in_events:
                feedback_context = await feedback_repo.get_feedback_context_for_generation(category)
                if feedback_context.get("has_patterns") and feedback_context.get("specific_guidance"):
                    feedback_guidance_by_category[category] = feedback_context["specific_guidance"]
                    logger.info(
                        f"Loaded feedback guidance for {category}: {len(feedback_context['specific_guidance'])} items"
                    )

            # Initialize the poll generator
            generator = PollGenerator()

            # Generate a poll from the events with feedback guidance
            generated_polls = await generator.generate_daily_polls(
                events=filtered_events,
                count=1,
                feedback_guidance_by_category=feedback_guidance_by_category if feedback_guidance_by_category else None,
            )

            if not generated_polls:
                logger.warning("Failed to generate poll from events")
                return None

            poll_data = generated_polls[0]

            # Set duration and special flag based on poll type
            if poll_type == "pulse":
                duration_hours = 12
                is_special = True
            else:  # flash
                duration_hours = 1
                is_special = False

            # Check current window status
            now = datetime.now(timezone.utc)
            if window_start <= now < window_end:
                initial_status = PollStatus.ACTIVE
            else:
                initial_status = PollStatus.SCHEDULED

            # Create the poll in database
            new_poll = Poll(
                id=str(uuid4()),
                question=poll_data.question,
                category=poll_data.category,
                status=initial_status,
                poll_type=poll_type,
                is_special=is_special,
                duration_hours=duration_hours,
                scheduled_start=window_start,
                scheduled_end=window_end,
                expires_at=window_end,
                ai_generated=True,
                source_event=poll_data.source_event if hasattr(poll_data, "source_event") else None,
            )

            # Add choices
            for i, choice in enumerate(poll_data.choices):
                poll_choice = PollChoice(
                    id=str(uuid4()),
                    poll_id=new_poll.id,
                    text=choice.text if hasattr(choice, "text") else str(choice),
                    order=i,
                )
                new_poll.choices.append(poll_choice)

            self.db.add(new_poll)
            try:
                await self.db.commit()
                await self.db.refresh(new_poll)

                logger.info(
                    f"{poll_type.upper()} poll generated: {new_poll.id} - '{new_poll.question[:50]}' "
                    f"[{new_poll.category}] scheduled for {window_start.isoformat()}"
                )

                return new_poll
            except IntegrityError:
                # Unique constraint violation - another process already created a poll for this window
                # This is expected behavior in concurrent environments, not an error
                await self.db.rollback()
                logger.info(
                    f"Poll already exists for {poll_type} window {window_start.isoformat()} "
                    f"(concurrent creation detected via unique constraint) - fetching existing poll"
                )
                # Fetch the existing poll that was created by another process
                result = await self.db.execute(
                    select(Poll).where(
                        and_(
                            Poll.poll_type == poll_type,
                            Poll.scheduled_start == window_start,
                        )
                    )
                )
                existing_poll = result.scalar_one_or_none()
                return existing_poll

        except Exception as e:
            logger.error(f"Poll generation error: {e}", exc_info=True)
            return None


# Background task functions for APScheduler or similar
async def poll_rotation_task(db_session: AsyncSession) -> None:
    """
    Background task to run poll rotation.

    Should be scheduled to run at the start of each poll window.
    """
    scheduler = PollScheduler(db_session)
    result = await scheduler.run_rotation_cycle()
    logger.info(f"Poll rotation completed: {result}")


def get_next_rotation_time() -> datetime:
    """
    Calculate when the next poll rotation should occur.

    Returns the start time of the next poll window.
    """
    next_start, _ = PollScheduler.get_next_poll_window()
    return next_start


# ============================================================================
# Pulse Poll Scheduling (Daily 8am-8pm ET)
# ============================================================================


def get_pulse_poll_window() -> tuple[datetime, datetime]:
    """
    Get the current or next Pulse Poll window (8am-8pm ET daily).

    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    from zoneinfo import ZoneInfo

    et_tz = ZoneInfo("America/New_York")
    now_et = datetime.now(et_tz)

    # Pulse Poll runs 8am-8pm ET
    pulse_start_hour = 8
    pulse_end_hour = 20  # 8pm

    # Check if we're currently in the pulse window
    if pulse_start_hour <= now_et.hour < pulse_end_hour:
        # We're in the window, get today's start time
        start_et = now_et.replace(hour=pulse_start_hour, minute=0, second=0, microsecond=0)
        end_et = now_et.replace(hour=pulse_end_hour, minute=0, second=0, microsecond=0)
    elif now_et.hour >= pulse_end_hour:
        # After today's window, get tomorrow's
        tomorrow = now_et + timedelta(days=1)
        start_et = tomorrow.replace(hour=pulse_start_hour, minute=0, second=0, microsecond=0)
        end_et = tomorrow.replace(hour=pulse_end_hour, minute=0, second=0, microsecond=0)
    else:
        # Before today's window
        start_et = now_et.replace(hour=pulse_start_hour, minute=0, second=0, microsecond=0)
        end_et = now_et.replace(hour=pulse_end_hour, minute=0, second=0, microsecond=0)

    # Convert to UTC
    start_utc = start_et.astimezone(timezone.utc)
    end_utc = end_et.astimezone(timezone.utc)

    return start_utc, end_utc


async def schedule_daily_pulse_poll(
    db_session: AsyncSession,
    question: str,
    choices: list[str],
    category: str,
    source_event: Optional[str] = None,
) -> Poll:
    """
    Schedule the daily Pulse Poll (8am-8pm ET).

    Pulse Polls are featured daily polls on important topics.
    They run for 12 hours in the prime engagement window.
    """
    start_utc, end_utc = get_pulse_poll_window()

    poll = Poll(
        id=str(uuid4()),
        question=question,
        category=category,
        source_event=source_event,
        status=PollStatus.SCHEDULED.value,
        is_active=False,
        is_featured=True,
        is_special=True,  # Pulse polls are special (non-standard duration)
        poll_type="pulse",
        duration_hours=12,
        scheduled_start=start_utc,
        scheduled_end=end_utc,
        expires_at=end_utc,
        ai_generated=False,
        total_votes=0,
    )

    db_session.add(poll)

    for order, choice_text in enumerate(choices):
        choice = PollChoice(
            id=str(uuid4()),
            poll_id=poll.id,
            text=choice_text,
            order=order,
            vote_count=0,
        )
        db_session.add(choice)

    await db_session.commit()
    await db_session.refresh(poll)

    logger.info(f"Scheduled Pulse Poll: '{question[:50]}...' for {start_utc} - {end_utc}")

    return poll


# ============================================================================
# Flash Poll Scheduling (Every 2-3 hours, 1 hour duration)
# ============================================================================


def get_flash_poll_schedule() -> list[tuple[datetime, datetime]]:
    """
    Get the flash poll schedule for the next 24 hours.

    Flash Polls run every 2-3 hours, 24/7, with 1-hour duration.
    Schedule: 0:00, 3:00, 6:00, 9:00, 12:00, 15:00, 18:00, 21:00 UTC
    """
    now = datetime.now(timezone.utc)

    # Flash poll start hours (UTC)
    flash_hours = [0, 3, 6, 9, 12, 15, 18, 21]
    flash_duration_hours = 1

    schedule = []

    for day_offset in range(2):  # Today and tomorrow
        for hour in flash_hours:
            start = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)

            # Skip past times
            if start <= now:
                continue

            end = start + timedelta(hours=flash_duration_hours)
            schedule.append((start, end))

            if len(schedule) >= 12:  # Return next 12 flash poll windows
                return schedule

    return schedule


def get_next_flash_poll_window() -> tuple[datetime, datetime]:
    """
    Get the next flash poll window.

    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    schedule = get_flash_poll_schedule()
    if schedule:
        return schedule[0]

    # Fallback: next 3-hour mark
    now = datetime.now(timezone.utc)
    hours_since = now.hour % 3
    next_hour = now.hour + (3 - hours_since) if hours_since > 0 else now.hour + 3
    start = now.replace(hour=next_hour % 24, minute=0, second=0, microsecond=0)
    if next_hour >= 24:
        start = start + timedelta(days=1)
    end = start + timedelta(hours=1)

    return start, end


async def schedule_flash_poll(
    db_session: AsyncSession,
    question: str,
    choices: list[str],
    category: str,
    source_event: Optional[str] = None,
    scheduled_start: Optional[datetime] = None,
) -> Poll:
    """
    Schedule a Flash Poll (1-hour quick poll).

    Flash Polls cover breaking news and rapid-response topics.
    They run every 2-3 hours around the clock.
    """
    if scheduled_start is None:
        start_utc, end_utc = get_next_flash_poll_window()
    else:
        start_utc = scheduled_start
        end_utc = start_utc + timedelta(hours=1)

    poll = Poll(
        id=str(uuid4()),
        question=question,
        category=category,
        source_event=source_event,
        status=PollStatus.SCHEDULED.value,
        is_active=False,
        is_featured=False,
        is_special=False,
        poll_type="flash",
        duration_hours=1,
        scheduled_start=start_utc,
        scheduled_end=end_utc,
        expires_at=end_utc,
        ai_generated=False,
        total_votes=0,
    )

    db_session.add(poll)

    for order, choice_text in enumerate(choices):
        choice = PollChoice(
            id=str(uuid4()),
            poll_id=poll.id,
            text=choice_text,
            order=order,
            vote_count=0,
        )
        db_session.add(choice)

    await db_session.commit()
    await db_session.refresh(poll)

    logger.info(f"Scheduled Flash Poll: '{question[:50]}...' for {start_utc} (1 hour)")

    return poll
