"""
Background Scheduler Service

Manages scheduled background tasks using APScheduler:
- Poll rotation (hourly)
- Poll generation from news events
- Cleanup tasks

This runs in-process with the FastAPI application.
Uses distributed locks to coordinate across multiple replicas.
"""

from datetime import timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from db.session import async_session_maker
from services.distributed_lock_service import (
    LOCK_POLL_GENERATION,
    LOCK_POLL_ROTATION,
    DistributedLockService,
)

logger = structlog.get_logger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def poll_rotation_job() -> None:
    """
    Background job to run poll rotation cycle.

    This job:
    1. Closes any expired polls
    2. Activates any scheduled polls whose time has come
    3. Generates new polls from current events if needed
    4. Sends notifications for newly activated polls

    Uses distributed locking to ensure only one replica runs at a time.
    """
    from services.poll_scheduler import PollScheduler

    logger.info("Poll rotation job triggered, attempting to acquire lock...")

    try:
        async with async_session_maker() as db:
            # Use distributed lock to coordinate across replicas
            async with DistributedLockService.acquire_lock(db, LOCK_POLL_ROTATION, timeout_seconds=300) as acquired:
                if not acquired:
                    logger.info("Poll rotation skipped - another instance is running")
                    return

                logger.info("Lock acquired, starting poll rotation...")
                scheduler = PollScheduler(db)
                result = await scheduler.run_rotation_cycle()

                logger.info(
                    f"Poll rotation completed: "
                    f"closed={result.get('closed_count', 0)}, "
                    f"activated={result.get('activated_count', 0)}, "
                    f"generated={'yes' if result.get('generated_poll') else 'no'}"
                )

                # Send notifications for newly activated polls
                activated_polls = result.get("activated_polls", [])
                if activated_polls:
                    await _send_notifications_for_polls(db, activated_polls)

    except Exception as e:
        logger.error(f"Poll rotation job failed: {e}", exc_info=True)


async def _send_notifications_for_polls(db, polls: list) -> None:
    """Send notifications for a list of newly activated polls."""
    from services.notification_service import send_poll_notifications

    for poll in polls:
        try:
            poll_type = getattr(poll, "poll_type", "standard")
            if poll_type in ("pulse", "flash"):
                result = await send_poll_notifications(db, poll, poll_type)
                logger.info(
                    "poll_notifications_complete",
                    poll_id=str(poll.id),
                    poll_type=poll_type,
                    sent=result.get("sent", 0),
                    skipped=result.get("skipped", 0),
                )
        except Exception as e:
            logger.error(f"Failed to send notifications for poll {poll.id}: {e}")


async def generate_polls_job() -> None:
    """
    Background job to generate polls from current events.

    Runs periodically to ensure there are always upcoming polls scheduled.
    Uses distributed locking to ensure only one replica runs at a time.
    """
    from services.poll_scheduler import PollScheduler

    logger.info("Poll generation job triggered, attempting to acquire lock...")

    try:
        async with async_session_maker() as db:
            # Use distributed lock to coordinate across replicas
            async with DistributedLockService.acquire_lock(db, LOCK_POLL_GENERATION, timeout_seconds=600) as acquired:
                if not acquired:
                    logger.info("Poll generation skipped - another instance is running")
                    return

                logger.info("Lock acquired, checking poll generation needs...")
                scheduler = PollScheduler(db)

                # Check if we need more scheduled polls
                upcoming = await scheduler.get_upcoming_polls(limit=5)

                if len(upcoming) < 3:  # Generate more if we have less than 3 upcoming
                    logger.info(f"Only {len(upcoming)} upcoming polls, generating more...")
                    poll = await scheduler._generate_poll_from_events()

                    if poll:
                        logger.info(f"Generated new poll: {poll.question[:50]}...")
                    else:
                        logger.warning("Failed to generate poll from events")
                else:
                    logger.info(f"Have {len(upcoming)} upcoming polls, skipping generation")

    except Exception as e:
        logger.error(f"Poll generation job failed: {e}", exc_info=True)


async def cleanup_locks_job() -> None:
    """
    Background job to clean up expired locks.

    Runs periodically to release locks from crashed instances.
    This job does NOT use distributed locking itself to avoid deadlock.
    """
    logger.debug("Running lock cleanup job...")

    try:
        async with async_session_maker() as db:
            count = await DistributedLockService.cleanup_expired_locks(db)
            if count > 0:
                logger.info(f"Cleaned up {count} expired locks")
    except Exception as e:
        logger.error(f"Lock cleanup job failed: {e}", exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=timezone.utc)
    return _scheduler


async def start_scheduler() -> None:
    """Start the background scheduler with all jobs."""
    scheduler = get_scheduler()

    if scheduler.running:
        logger.info("Scheduler already running")
        return

    logger.info("Configuring background scheduler...")

    # Job 1: Poll rotation - runs at the top of every hour
    # This activates/closes polls based on their scheduled times
    scheduler.add_job(
        poll_rotation_job,
        trigger=CronTrigger(minute=0),  # Every hour at :00
        id="poll_rotation",
        name="Poll Rotation",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Added poll rotation job (hourly at :00)")

    # Job 2: Poll generation - runs every 30 minutes
    # This ensures we always have upcoming polls ready
    scheduler.add_job(
        generate_polls_job,
        trigger=IntervalTrigger(minutes=30),
        id="poll_generation",
        name="Poll Generation",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Added poll generation job (every 30 minutes)")

    # Job 3: Lock cleanup - runs every 5 minutes
    # This releases expired locks from crashed instances
    scheduler.add_job(
        cleanup_locks_job,
        trigger=IntervalTrigger(minutes=5),
        id="lock_cleanup",
        name="Lock Cleanup",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Added lock cleanup job (every 5 minutes)")

    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started")

    # Run initial poll rotation immediately on startup
    logger.info("Running initial poll rotation...")
    await poll_rotation_job()


async def stop_scheduler() -> None:
    """Stop the background scheduler gracefully."""
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.info("Stopping background scheduler...")
        _scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")

    _scheduler = None


async def trigger_poll_rotation() -> dict:
    """
    Manually trigger a poll rotation cycle.

    Useful for testing or manual intervention.
    Returns the result of the rotation cycle.
    """
    from services.poll_scheduler import PollScheduler

    async with async_session_maker() as db:
        scheduler = PollScheduler(db)
        return await scheduler.run_rotation_cycle()


async def trigger_poll_generation() -> dict:
    """
    Manually trigger poll generation.

    Returns info about the generated poll or None.
    """
    from services.poll_scheduler import PollScheduler

    async with async_session_maker() as db:
        scheduler = PollScheduler(db)
        poll = await scheduler._generate_poll_from_events()

        if poll:
            return {
                "success": True,
                "poll_id": poll.id,
                "question": poll.question,
                "scheduled_start": poll.scheduled_start.isoformat() if poll.scheduled_start else None,
            }
        return {"success": False, "error": "Failed to generate poll"}
