"""
Distributed Lock Service

Provides distributed locking for coordinating background jobs
across multiple application instances (Container App replicas).

Uses Azure Table Storage (via TokenCacheService) for lock state,
ensuring only one instance runs a particular job at a time.
"""

import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Optional

import structlog

from services.token_cache_service import TokenCacheService

logger = structlog.get_logger(__name__)

# Default lock timeout (how long a lock is valid before considered stale)
DEFAULT_LOCK_TIMEOUT_SECONDS = 300  # 5 minutes

# Key prefix for distributed locks
LOCK_PREFIX = "lock:"

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


class LockInfo:
    """Information about a distributed lock."""

    def __init__(
        self,
        lock_name: str,
        is_locked: bool = False,
        locked_by: Optional[str] = None,
        locked_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        last_run_at: Optional[datetime] = None,
        last_run_result: Optional[str] = None,
    ):
        self.lock_name = lock_name
        self.is_locked = is_locked
        self.locked_by = locked_by
        self.locked_at = locked_at
        self.expires_at = expires_at
        self.last_run_at = last_run_at
        self.last_run_result = last_run_result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "lock_name": self.lock_name,
            "is_locked": self.is_locked,
            "locked_by": self.locked_by,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_result": self.last_run_result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LockInfo":
        """Create from dictionary."""
        return cls(
            lock_name=data.get("lock_name", ""),
            is_locked=data.get("is_locked", False),
            locked_by=data.get("locked_by"),
            locked_at=datetime.fromisoformat(data["locked_at"]) if data.get("locked_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_run_at=datetime.fromisoformat(data["last_run_at"]) if data.get("last_run_at") else None,
            last_run_result=data.get("last_run_result"),
        )


class DistributedLockService:
    """
    Service for managing distributed locks.

    Usage:
        token_cache_svc = await get_token_cache_service()
        async with DistributedLockService.acquire_lock(token_cache_svc, "my_job") as acquired:
            if acquired:
                # Do the work
                pass
            else:
                # Another instance is running this job
                pass
    """

    @staticmethod
    async def _get_lock_info(token_cache_svc: TokenCacheService, lock_name: str) -> Optional[LockInfo]:
        """Get lock info from cache."""
        data = await token_cache_svc.cache_get(f"{LOCK_PREFIX}{lock_name}")
        if data is None:
            return None
        return LockInfo.from_dict(data)

    @staticmethod
    async def _set_lock_info(
        token_cache_svc: TokenCacheService,
        lock_info: LockInfo,
        ttl_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> bool:
        """Save lock info to cache."""
        return await token_cache_svc.cache_set(
            f"{LOCK_PREFIX}{lock_info.lock_name}",
            lock_info.to_dict(),
            ttl_seconds + 60,  # Keep a bit longer than lock timeout for history
        )

    @staticmethod
    async def try_acquire(
        token_cache_svc: TokenCacheService,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> bool:
        """
        Attempt to acquire a lock.

        Uses optimistic locking - checks if lock is free or expired,
        then tries to acquire it.

        Args:
            token_cache_svc: Token cache service instance
            lock_name: Name of the lock to acquire
            timeout_seconds: How long the lock is valid

        Returns:
            True if lock acquired, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=timeout_seconds)

        try:
            # Get current lock state
            lock_info = await DistributedLockService._get_lock_info(token_cache_svc, lock_name)

            # Check if lock is available or expired
            if lock_info is not None:
                if lock_info.is_locked:
                    if lock_info.expires_at and lock_info.expires_at > now:
                        logger.debug(
                            f"Lock '{lock_name}' is held by {lock_info.locked_by} until {lock_info.expires_at}"
                        )
                        return False
                    # Lock is expired, we can take it
                    logger.info(f"Lock '{lock_name}' expired, taking over from {lock_info.locked_by}")

            # Create/update lock with our acquisition
            new_lock = LockInfo(
                lock_name=lock_name,
                is_locked=True,
                locked_by=instance_id,
                locked_at=now,
                expires_at=expires_at,
                last_run_at=lock_info.last_run_at if lock_info else None,
                last_run_result=lock_info.last_run_result if lock_info else None,
            )

            await DistributedLockService._set_lock_info(token_cache_svc, new_lock, timeout_seconds)
            logger.info(f"Lock '{lock_name}' acquired by {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Error acquiring lock '{lock_name}': {e}")
            return False

    @staticmethod
    async def release(
        token_cache_svc: TokenCacheService,
        lock_name: str,
        success: bool = True,
        result_notes: Optional[str] = None,
    ) -> bool:
        """
        Release a lock.

        Args:
            token_cache_svc: Token cache service instance
            lock_name: Name of the lock to release
            success: Whether the job completed successfully
            result_notes: Optional notes about the job result

        Returns:
            True if lock released, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)

        try:
            lock_info = await DistributedLockService._get_lock_info(token_cache_svc, lock_name)

            if lock_info is None or lock_info.locked_by != instance_id:
                logger.warning(f"Lock '{lock_name}' release failed - not held by {instance_id}")
                return False

            # Release the lock but keep history
            lock_info.is_locked = False
            lock_info.locked_by = None
            lock_info.locked_at = None
            lock_info.expires_at = None
            lock_info.last_run_at = now
            lock_info.last_run_result = result_notes or ("success" if success else "failed")

            await DistributedLockService._set_lock_info(token_cache_svc, lock_info, 86400)  # Keep for 24h
            logger.info(f"Lock '{lock_name}' released by {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Error releasing lock '{lock_name}': {e}")
            return False

    @staticmethod
    async def extend(
        token_cache_svc: TokenCacheService,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> bool:
        """
        Extend the timeout of a held lock (heartbeat).

        Call this periodically during long-running jobs to prevent
        the lock from expiring.

        Args:
            token_cache_svc: Token cache service instance
            lock_name: Name of the lock to extend
            timeout_seconds: New timeout duration

        Returns:
            True if lock extended, False otherwise
        """
        instance_id = get_instance_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=timeout_seconds)

        try:
            lock_info = await DistributedLockService._get_lock_info(token_cache_svc, lock_name)

            if lock_info is None or not lock_info.is_locked or lock_info.locked_by != instance_id:
                return False

            lock_info.expires_at = expires_at
            await DistributedLockService._set_lock_info(token_cache_svc, lock_info, timeout_seconds)
            logger.debug(f"Lock '{lock_name}' extended until {expires_at}")
            return True

        except Exception as e:
            logger.error(f"Error extending lock '{lock_name}': {e}")
            return False

    @staticmethod
    @asynccontextmanager
    async def acquire_lock(
        token_cache_svc: TokenCacheService,
        lock_name: str,
        timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> AsyncGenerator[bool, None]:
        """
        Context manager for acquiring and releasing a lock.

        Usage:
            token_cache_svc = await get_token_cache_service()
            async with DistributedLockService.acquire_lock(token_cache_svc, "my_job") as acquired:
                if acquired:
                    # Do the work
                    pass

        Args:
            token_cache_svc: Token cache service instance
            lock_name: Name of the lock to acquire
            timeout_seconds: How long the lock is valid

        Yields:
            True if lock acquired, False otherwise
        """
        acquired = await DistributedLockService.try_acquire(token_cache_svc, lock_name, timeout_seconds)
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
                await DistributedLockService.release(token_cache_svc, lock_name, success, result_notes)

    @staticmethod
    async def get_lock_status(token_cache_svc: TokenCacheService, lock_name: str) -> Optional[LockInfo]:
        """Get the current status of a lock."""
        return await DistributedLockService._get_lock_info(token_cache_svc, lock_name)


# Lock names for standard jobs
LOCK_POLL_ROTATION = "poll_rotation"
LOCK_POLL_GENERATION = "poll_generation"
LOCK_POLL_NOTIFICATION = "poll_notification"
