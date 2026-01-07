"""
Background Scheduler Service

Manages scheduled background tasks using APScheduler:
- Poll rotation (hourly)
- Poll generation from news events
- Cleanup tasks

This runs in-process with the FastAPI application.
Uses Redis-based distributed locks to coordinate across multiple replicas.
Now uses Cosmos DB via repositories.
"""

import socket
from contextlib import asynccontextmanager
from datetime import timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from services.redis_service import RedisService

logger = structlog.get_logger(__name__)

# Lock names
LOCK_POLL_ROTATION = "lock:poll_rotation"
LOCK_POLL_GENERATION = "lock:poll_generation"

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


class RedisDistributedLock:
    """Redis-based distributed lock for coordinating across replicas."""

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.instance_id = f"{socket.gethostname()}:{id(self)}"

    @asynccontextmanager
    async def acquire_lock(self, lock_name: str, timeout_seconds: int = 300):
        """
        Acquire a distributed lock using Redis.

        Args:
            lock_name: Unique name for the lock
            timeout_seconds: Lock expiry (prevents deadlock from crashes)

        Yields:
            True if lock acquired, False if another instance holds it
        """
        # Try to acquire lock by setting if not exists
        existing = await self.redis.cache_get(lock_name)
        if existing is not None:
            # Lock exists, another instance has it
            logger.debug(f"Lock {lock_name} held by another instance")
            yield False
            return

        # Set the lock with TTL
        await self.redis.cache_set(lock_name, self.instance_id, timeout_seconds)

        try:
            yield True
        finally:
            # Release the lock - only if we still own it
            current_holder = await self.redis.cache_get(lock_name)
            if current_holder == self.instance_id:
                await self.redis.cache_delete(lock_name)
                logger.debug(f"Released lock {lock_name}")


async def poll_rotation_job() -> None:
    """
    Background job to run poll rotation cycle.

    This job:
    1. Closes any expired polls
    2. Activates any scheduled polls whose time has come
    3. Generates new polls from current events if needed
    4. Sends notifications for newly activated polls

    Uses Redis-based distributed locking to ensure only one replica runs at a time.
    """
    from services.poll_scheduler import PollScheduler

    logger.info("Poll rotation job triggered, attempting to acquire lock...")

    try:
        redis_service = RedisService()
        await redis_service.initialize()
        lock_manager = RedisDistributedLock(redis_service)

        async with lock_manager.acquire_lock(LOCK_POLL_ROTATION, timeout_seconds=300) as acquired:
            if not acquired:
                logger.info("Poll rotation skipped - another instance is running")
                return

            logger.info("Lock acquired, starting poll rotation...")
            scheduler = PollScheduler()
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
                await _send_notifications_for_polls(activated_polls)

    except Exception as e:
        logger.error(f"Poll rotation job failed: {e}", exc_info=True)


async def _send_notifications_for_polls(polls: list) -> None:
    """Send notifications for a list of newly activated polls."""
    from services.notification_service import send_poll_notifications

    for poll in polls:
        try:
            poll_type = getattr(poll, "poll_type", None)
            if poll_type:
                poll_type_value = poll_type.value if hasattr(poll_type, "value") else str(poll_type)
                if poll_type_value in ("pulse", "flash"):
                    result = await send_poll_notifications(poll, poll_type_value)
                    logger.info(
                        "poll_notifications_complete",
                        poll_id=str(poll.id),
                        poll_type=poll_type_value,
                        sent=result.get("sent", 0),
                        skipped=result.get("skipped", 0),
                    )
        except Exception as e:
            logger.error(f"Failed to send notifications for poll {poll.id}: {e}")


async def generate_polls_job() -> None:
    """
    Background job to generate polls from current events.

    Runs periodically to ensure there are always upcoming polls scheduled.
    Uses Redis-based distributed locking to ensure only one replica runs at a time.
    """
    from services.poll_scheduler import PollScheduler

    logger.info("Poll generation job triggered, attempting to acquire lock...")

    try:
        redis_service = RedisService()
        await redis_service.initialize()
        lock_manager = RedisDistributedLock(redis_service)

        async with lock_manager.acquire_lock(LOCK_POLL_GENERATION, timeout_seconds=600) as acquired:
            if not acquired:
                logger.info("Poll generation skipped - another instance is running")
                return

            logger.info("Lock acquired, checking poll generation needs...")
            scheduler = PollScheduler()

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
    Background job to clean up expired cache entries.

    Runs periodically to release memory from expired in-memory cache entries.
    Note: Redis/Azure Tables entries automatically expire via TTL.
    """
    logger.debug("Running cache cleanup job...")

    try:
        redis_service = RedisService()
        # Clean up expired entries from in-memory cache
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        expired_keys = [k for k, (_, exp) in list(redis_service._in_memory_cache.items()) if exp < now]
        for key in expired_keys:
            if key in redis_service._in_memory_cache:
                del redis_service._in_memory_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        else:
            logger.debug("Cache cleanup completed - no expired entries")
    except Exception as e:
        logger.error(f"Cache cleanup job failed: {e}", exc_info=True)


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

    scheduler = PollScheduler()
    return await scheduler.run_rotation_cycle()


async def trigger_poll_generation() -> dict:
    """
    Manually trigger poll generation.

    Returns info about the generated poll or None.
    """
    from services.poll_scheduler import PollScheduler

    scheduler = PollScheduler()
    poll = await scheduler._generate_poll_from_events()

    if poll:
        return {
            "success": True,
            "poll_id": poll.id,
            "question": poll.question,
            "scheduled_start": poll.scheduled_start.isoformat() if poll.scheduled_start else None,
        }
    return {"success": False, "error": "Failed to generate poll"}
