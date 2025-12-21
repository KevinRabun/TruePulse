"""
Distributed Lock Service

Provides distributed locking for coordinating background jobs
across multiple application instances (Container App replicas).

Uses PostgreSQL advisory locks and the distributed_locks table
to ensure only one instance runs a particular job at a time.
"""

import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncGenerator, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from models.distributed_lock import DistributedLock

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

logger = structlog.get_logger(__name__)

# Default lock timeout (how long a lock is valid before considered stale)
DEFAULT_LOCK_TIMEOUT_SECONDS = 300  # 5 minutes

# Generate a unique instance identifier
_instance_id: Optional[str] = None


def get_instance_id() -> str:
    """Get a unique identifier for this application instance."""
    global _instance_id
    if _instance_id is None:
        hostname = socket.gethostname()
        pid = os.getpid()
        _instance_id = f"{hostname}:{pid}"
    return _instance_id


class DistributedLockService:
    """
    Service for managing distributed locks.

    Usage:
        async with DistributedLockService.acquire_lock(db, "my_job") as acquired:
            if acquired:
                # Do the work
                pass
            else:
                # Another instance is running this job
                pass
    """

    @staticmethod
    async def ensure_lock_exists(db: AsyncSession, lock_name: str) -> DistributedLock:
        """
        Ensure a lock record exists for the given name.

        Creates the lock if it doesn't exist.
        """
        result = await db.execute(
            select(DistributedLock).where(DistributedLock.lock_name == lock_name)
        )
        lock = result.scalar_one_or_none()

        if lock is None:
            lock = DistributedLock(
                lock_name=lock_name,
                is_locked=False,
            )
            db.add(lock)
            await db.commit()
            await db.refresh(lock)
            logger.info(f"Created new lock record: {lock_name}")

        return lock

    @staticmethod
    async def try_acquire(
        db: AsyncSession,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> bool:
        """
        Attempt to acquire a lock.

        Uses optimistic locking with version numbers to prevent race conditions.
        Also releases expired locks automatically.

        Args:
            db: Database session
            lock_name: Name of the lock to acquire
            timeout_seconds: How long the lock is valid

        Returns:
            True if lock acquired, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=timeout_seconds)

        try:
            # First, ensure the lock exists
            lock = await DistributedLockService.ensure_lock_exists(db, lock_name)

            # Check if lock is available or expired
            if lock.is_locked and lock.expires_at and lock.expires_at > now:
                logger.debug(
                    f"Lock '{lock_name}' is held by {lock.locked_by} "
                    f"until {lock.expires_at}"
                )
                return False

            # Try to acquire using optimistic locking
            old_version = lock.version
            result: CursorResult = await db.execute(  # type: ignore[assignment]
                update(DistributedLock)
                .where(
                    DistributedLock.lock_name == lock_name,
                    DistributedLock.version == old_version,
                )
                .values(
                    is_locked=True,
                    locked_by=instance_id,
                    locked_at=now,
                    expires_at=expires_at,
                    version=old_version + 1,
                )
            )

            if result.rowcount == 1:
                await db.commit()
                logger.info(f"Lock '{lock_name}' acquired by {instance_id}")
                return True
            else:
                # Another instance beat us to it
                await db.rollback()
                logger.debug(f"Lock '{lock_name}' acquisition failed (race condition)")
                return False

        except SQLAlchemyError as e:
            logger.error(f"Error acquiring lock '{lock_name}': {e}")
            await db.rollback()
            return False

    @staticmethod
    async def release(
        db: AsyncSession,
        lock_name: str,
        success: bool = True,
        result_notes: Optional[str] = None,
    ) -> bool:
        """
        Release a lock.

        Args:
            db: Database session
            lock_name: Name of the lock to release
            success: Whether the job completed successfully
            result_notes: Optional notes about the job result

        Returns:
            True if lock released, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)

        try:
            result: CursorResult = await db.execute(  # type: ignore[assignment]
                update(DistributedLock)
                .where(
                    DistributedLock.lock_name == lock_name,
                    DistributedLock.locked_by == instance_id,
                )
                .values(
                    is_locked=False,
                    locked_by=None,
                    locked_at=None,
                    expires_at=None,
                    last_run_at=now,
                    last_run_result=result_notes or ("success" if success else "failed"),
                )
            )

            if result.rowcount == 1:
                await db.commit()
                logger.info(f"Lock '{lock_name}' released by {instance_id}")
                return True
            else:
                await db.rollback()
                logger.warning(
                    f"Lock '{lock_name}' release failed - not held by {instance_id}"
                )
                return False

        except SQLAlchemyError as e:
            logger.error(f"Error releasing lock '{lock_name}': {e}")
            await db.rollback()
            return False

    @staticmethod
    async def extend(
        db: AsyncSession,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> bool:
        """
        Extend the timeout of a held lock (heartbeat).

        Call this periodically during long-running jobs to prevent
        the lock from expiring.

        Args:
            db: Database session
            lock_name: Name of the lock to extend
            timeout_seconds: New timeout duration

        Returns:
            True if lock extended, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=timeout_seconds)

        try:
            result: CursorResult = await db.execute(  # type: ignore[assignment]
                update(DistributedLock)
                .where(
                    DistributedLock.lock_name == lock_name,
                    DistributedLock.locked_by == instance_id,
                    DistributedLock.is_locked == True,  # noqa: E712
                )
                .values(expires_at=expires_at)
            )

            if result.rowcount == 1:
                await db.commit()
                logger.debug(f"Lock '{lock_name}' extended until {expires_at}")
                return True
            else:
                await db.rollback()
                return False

        except SQLAlchemyError as e:
            logger.error(f"Error extending lock '{lock_name}': {e}")
            await db.rollback()
            return False

    @staticmethod
    @asynccontextmanager
    async def acquire_lock(
        db: AsyncSession,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> AsyncGenerator[bool, None]:
        """
        Context manager for acquiring and releasing a lock.

        Usage:
            async with DistributedLockService.acquire_lock(db, "my_job") as acquired:
                if acquired:
                    # Do the work
                    pass

        Args:
            db: Database session
            lock_name: Name of the lock to acquire
            timeout_seconds: How long the lock is valid

        Yields:
            True if lock acquired, False otherwise
        """
        acquired = await DistributedLockService.try_acquire(
            db, lock_name, timeout_seconds
        )
        success = True
        result_notes = None

        try:
            yield acquired
        except Exception as e:
            success = False
            result_notes = str(e)[:500]  # Truncate error message
            raise
        finally:
            if acquired:
                await DistributedLockService.release(
                    db, lock_name, success, result_notes
                )

    @staticmethod
    async def get_lock_status(
        db: AsyncSession, lock_name: str
    ) -> Optional[DistributedLock]:
        """Get the current status of a lock."""
        result = await db.execute(
            select(DistributedLock).where(DistributedLock.lock_name == lock_name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_locks(db: AsyncSession) -> list[DistributedLock]:
        """Get all registered locks and their status."""
        result = await db.execute(select(DistributedLock))
        return list(result.scalars().all())

    @staticmethod
    async def cleanup_expired_locks(db: AsyncSession) -> int:
        """
        Release all expired locks.

        Call this periodically to clean up locks from crashed instances.

        Returns:
            Number of locks cleaned up
        """
        now = datetime.now(timezone.utc)

        try:
            result: CursorResult = await db.execute(  # type: ignore[assignment]
                update(DistributedLock)
                .where(
                    DistributedLock.is_locked == True,  # noqa: E712
                    DistributedLock.expires_at < now,
                )
                .values(
                    is_locked=False,
                    locked_by=None,
                    locked_at=None,
                    expires_at=None,
                    last_run_result="expired (auto-cleanup)",
                )
            )

            count = result.rowcount
            if count > 0:
                await db.commit()
                logger.warning(f"Cleaned up {count} expired locks")
            return count

        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up expired locks: {e}")
            await db.rollback()
            return 0


# Lock names for standard jobs
LOCK_POLL_ROTATION = "poll_rotation"
LOCK_POLL_GENERATION = "poll_generation"
