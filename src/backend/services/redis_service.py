"""
Token and cache service for centralized state management.

Previously used Redis, now uses Azure Table Storage for cost optimization.
Provides:
- Token blacklisting for JWT logout
- Rate limiting with sliding window
- Password reset token management
- Distributed caching for stats and other data

Maintains the same interface for backward compatibility.
"""

from datetime import datetime, timezone
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class RedisService:
    """
    Token and cache service (now backed by Azure Tables).

    Maintains the same interface as the original Redis-based service
    for backward compatibility, but uses Azure Table Storage.

    Features:
    - Token blacklist management
    - Rate limiting
    - Generic caching (in-memory with optional persistence)
    """

    _instance: Optional["RedisService"] = None
    _table_service: Optional[Any] = None
    _in_memory_cache: dict[str, tuple[Any, datetime]] = {}  # key -> (value, expires_at)

    # Key prefixes for namespacing
    PREFIX_TOKEN_BLACKLIST = "token:blacklist:"
    PREFIX_RATE_LIMIT = "rate:"
    PREFIX_CACHE = "cache:"
    PREFIX_PASSWORD_RESET = "password_reset:"

    def __new__(cls) -> "RedisService":
        """Singleton pattern for service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._in_memory_cache = {}
        return cls._instance

    async def initialize(self) -> None:
        """Initialize Azure Table Storage connection."""
        if self._table_service is not None:
            return

        try:
            from services.table_service import get_table_service

            self._table_service = await get_table_service()
            logger.info("token_service_initialized", backend="azure_tables")
        except Exception as e:
            logger.warning("table_service_unavailable", error=str(e))
            logger.info("token_service_initialized", backend="in_memory")

    async def close(self) -> None:
        """Close service connections."""
        if self._table_service:
            from services.table_service import close_table_service

            await close_table_service()
            self._table_service = None

    @property
    def is_available(self) -> bool:
        """Check if Azure Tables is available."""
        return self._table_service is not None

    # =========================================================================
    # Token Blacklist (for JWT logout)
    # =========================================================================

    async def blacklist_token(
        self,
        token_jti: str,
        expires_in_seconds: int,
    ) -> bool:
        """
        Add a token to the blacklist.

        Args:
            token_jti: The JWT ID (jti claim) or token hash
            expires_in_seconds: TTL matching token expiration

        Returns:
            True if blacklisted successfully
        """
        if self._table_service:
            try:
                return await self._table_service.blacklist_token(
                    token_jti, expires_in_seconds
                )
            except Exception as e:
                logger.error("token_blacklist_failed", error=str(e))

        # Fallback to in-memory
        key = f"{self.PREFIX_TOKEN_BLACKLIST}{token_jti}"
        from datetime import timedelta

        self._in_memory_cache[key] = (
            "1",
            datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
        )
        logger.info("token_blacklisted", jti=token_jti[:8], backend="in_memory")
        return True

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token_jti: The JWT ID to check

        Returns:
            True if blacklisted (logout was called)
        """
        if self._table_service:
            try:
                return await self._table_service.is_token_blacklisted(token_jti)
            except Exception as e:
                logger.error("token_blacklist_check_failed", error=str(e))

        # Fallback to in-memory
        key = f"{self.PREFIX_TOKEN_BLACKLIST}{token_jti}"
        if key in self._in_memory_cache:
            value, expires_at = self._in_memory_cache[key]
            if datetime.now(timezone.utc) < expires_at:
                return True
            del self._in_memory_cache[key]
        return False

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.

        Args:
            identifier: User ID, IP address, or other identifier
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        if self._table_service:
            try:
                return await self._table_service.check_rate_limit(
                    identifier, limit, window_seconds
                )
            except Exception as e:
                logger.error("rate_limit_check_failed", error=str(e))

        # Fail open if service unavailable
        return True, limit

    # =========================================================================
    # Password Reset Tokens
    # =========================================================================

    async def store_password_reset_token(
        self,
        token: str,
        user_id: str,
        email: str,
        expires_in_seconds: int = 3600,
    ) -> bool:
        """
        Store a password reset token.

        Args:
            token: The reset token
            user_id: User's ID
            email: User's email
            expires_in_seconds: Token TTL (default: 1 hour)

        Returns:
            True if stored successfully
        """
        if self._table_service:
            try:
                return await self._table_service.store_password_reset_token(
                    user_id, token, expires_in_seconds
                )
            except Exception as e:
                logger.error("password_reset_store_failed", error=str(e))

        # Fallback to in-memory
        key = f"{self.PREFIX_PASSWORD_RESET}{token}"
        from datetime import timedelta

        self._in_memory_cache[key] = (
            {"user_id": user_id, "email": email},
            datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
        )
        return True

    async def get_password_reset_token(
        self,
        token: str,
    ) -> Optional[dict[str, str]]:
        """
        Get password reset token data.

        Returns:
            Token data dict or None if not found/expired
        """
        if self._table_service:
            try:
                user_id = await self._table_service.validate_password_reset_token(token)
                if user_id:
                    return {"user_id": user_id}
                return None
            except Exception as e:
                logger.error("password_reset_get_failed", error=str(e))

        # Fallback to in-memory
        key = f"{self.PREFIX_PASSWORD_RESET}{token}"
        if key in self._in_memory_cache:
            value, expires_at = self._in_memory_cache[key]
            if datetime.now(timezone.utc) < expires_at:
                return value
            del self._in_memory_cache[key]
        return None

    async def delete_password_reset_token(self, token: str) -> bool:
        """Delete a password reset token (single use)."""
        if self._table_service:
            try:
                return await self._table_service.delete_password_reset_token(token)
            except Exception as e:
                logger.error("password_reset_delete_failed", error=str(e))

        # Fallback to in-memory
        key = f"{self.PREFIX_PASSWORD_RESET}{token}"
        if key in self._in_memory_cache:
            del self._in_memory_cache[key]
        return True

    # =========================================================================
    # Generic Caching (in-memory only for simplicity)
    # =========================================================================

    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> bool:
        """Set a value in cache with TTL."""
        from datetime import timedelta

        cache_key = f"{self.PREFIX_CACHE}{key}"
        self._in_memory_cache[cache_key] = (
            value,
            datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
        return True

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        cache_key = f"{self.PREFIX_CACHE}{key}"
        if cache_key in self._in_memory_cache:
            value, expires_at = self._in_memory_cache[cache_key]
            if datetime.now(timezone.utc) < expires_at:
                return value
            del self._in_memory_cache[cache_key]
        return None

    async def cache_delete(self, key: str) -> bool:
        """Delete a value from cache."""
        cache_key = f"{self.PREFIX_CACHE}{key}"
        if cache_key in self._in_memory_cache:
            del self._in_memory_cache[cache_key]
        return True


# Global instance
redis_service = RedisService()


async def get_redis_service() -> RedisService:
    """Dependency for getting token/cache service."""
    await redis_service.initialize()
    return redis_service
