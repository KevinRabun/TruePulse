"""
Azure Tables Service for TruePulse.

Provides Azure Table Storage operations for:
- Votes (high-volume, serverless scaling)
- Token blacklist (session invalidation)
- Password reset tokens (secure one-time tokens)
- Rate limiting (distributed request throttling)

Uses managed identity authentication in production,
falls back to connection string for local development.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables.aio import (
    TableClient as AsyncTableClient,
)
from azure.data.tables.aio import (
    TableServiceClient as AsyncTableServiceClient,
)
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

from core.config import get_settings

logger = structlog.get_logger(__name__)


# Table names
VOTES_TABLE = "votes"
TOKEN_BLACKLIST_TABLE = "tokenblacklist"
RESET_TOKENS_TABLE = "resettokens"
RATE_LIMITS_TABLE = "ratelimits"


class AzureTableService:
    """
    Azure Table Storage service for TruePulse.

    Provides cost-effective storage for:
    - Vote records (partition by poll_id)
    - Token blacklist for logout
    - Password reset tokens
    - Rate limiting data
    """

    def __init__(
        self,
        account_name: Optional[str] = None,
        table_endpoint: Optional[str] = None,
        connection_string: Optional[str] = None,
    ):
        """
        Initialize the Azure Table Service.

        Args:
            account_name: Azure Storage account name
            table_endpoint: Azure Storage table endpoint URL
            connection_string: Optional connection string (for local dev)
        """
        settings = get_settings()

        self.account_name = account_name or settings.AZURE_STORAGE_ACCOUNT_NAME
        self.table_endpoint = table_endpoint or settings.AZURE_STORAGE_TABLE_ENDPOINT
        self._connection_string = connection_string or getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

        self._service_client: Optional[AsyncTableServiceClient] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize the table service client and ensure tables exist."""
        if self._is_initialized:
            return

        try:
            if self._connection_string:
                # Use connection string (local development)
                self._service_client = AsyncTableServiceClient.from_connection_string(self._connection_string)
                logger.info("azure_tables_init", method="connection_string")
            else:
                # Use managed identity (production)
                credential = AsyncDefaultAzureCredential()
                if not self.table_endpoint:
                    raise ValueError("AZURE_STORAGE_TABLE_ENDPOINT must be set for managed identity auth")
                self._service_client = AsyncTableServiceClient(
                    endpoint=self.table_endpoint,
                    credential=credential,
                )
                logger.info(
                    "azure_tables_init",
                    method="managed_identity",
                    endpoint=self.table_endpoint,
                )

            # Ensure tables exist
            await self._ensure_tables_exist()
            self._is_initialized = True

        except Exception as e:
            logger.error("azure_tables_init_failed", error=str(e))
            raise

    async def _ensure_tables_exist(self) -> None:
        """Create tables if they don't exist."""
        if not self._service_client:
            raise RuntimeError("Azure Table Service client not initialized")

        tables = [
            VOTES_TABLE,
            TOKEN_BLACKLIST_TABLE,
            RESET_TOKENS_TABLE,
            RATE_LIMITS_TABLE,
        ]

        for table_name in tables:
            try:
                await self._service_client.create_table(table_name)
                logger.info("table_created", table=table_name)
            except ResourceExistsError:
                # Table already exists
                pass
            except Exception as e:
                logger.warning("table_create_failed", table=table_name, error=str(e))

    def _get_table_client(self, table_name: str) -> AsyncTableClient:
        """Get a table client for the specified table."""
        if not self._service_client:
            raise RuntimeError("Azure Table Service not initialized. Call initialize() first.")
        return self._service_client.get_table_client(table_name)

    async def close(self) -> None:
        """Close the service client."""
        if self._service_client:
            await self._service_client.close()
            self._service_client = None
            self._is_initialized = False

    # =========================================================================
    # Vote Operations
    # =========================================================================

    async def store_vote(
        self,
        poll_id: str,
        vote_hash: str,
        choice_id: str,
        demographics_bucket: Optional[str] = None,
    ) -> bool:
        """
        Store a vote in Azure Tables.

        Partition key: poll_id (efficient queries by poll)
        Row key: vote_hash (ensures uniqueness per user+poll)

        Args:
            poll_id: The poll identifier (partition key)
            vote_hash: SHA-256 hash of user_id + poll_id (row key)
            choice_id: The choice the user selected
            demographics_bucket: Optional anonymized demographics

        Returns:
            True if vote was stored, False if duplicate
        """
        table_client = self._get_table_client(VOTES_TABLE)

        entity = {
            "PartitionKey": poll_id,
            "RowKey": vote_hash,
            "choice_id": choice_id,
            "demographics_bucket": demographics_bucket or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await table_client.create_entity(entity)
            logger.info("vote_stored", poll_id=poll_id, vote_hash=vote_hash[:8])
            return True
        except ResourceExistsError:
            logger.warning("duplicate_vote", poll_id=poll_id, vote_hash=vote_hash[:8])
            return False

    async def get_vote(self, poll_id: str, vote_hash: str) -> Optional[dict]:
        """
        Check if a vote exists.

        Args:
            poll_id: The poll identifier
            vote_hash: The vote hash to check

        Returns:
            Vote entity if found, None otherwise
        """
        table_client = self._get_table_client(VOTES_TABLE)

        try:
            entity = await table_client.get_entity(poll_id, vote_hash)
            return dict(entity)
        except ResourceNotFoundError:
            return None

    async def get_poll_votes(self, poll_id: str) -> list[dict]:
        """
        Get all votes for a poll.

        Args:
            poll_id: The poll identifier

        Returns:
            List of vote entities
        """
        table_client = self._get_table_client(VOTES_TABLE)

        votes = []
        async for entity in table_client.query_entities(query_filter=f"PartitionKey eq '{poll_id}'"):
            votes.append(dict(entity))

        return votes

    async def count_poll_votes(self, poll_id: str) -> dict[str, int]:
        """
        Count votes by choice for a poll.

        Args:
            poll_id: The poll identifier

        Returns:
            Dict mapping choice_id to vote count
        """
        votes = await self.get_poll_votes(poll_id)

        counts: dict[str, int] = {}
        for vote in votes:
            choice_id = vote.get("choice_id", "")
            counts[choice_id] = counts.get(choice_id, 0) + 1

        return counts

    # =========================================================================
    # Token Blacklist Operations
    # =========================================================================

    async def blacklist_token(self, token_hash: str, ttl_seconds: int) -> bool:
        """
        Add a token to the blacklist (for logout).

        Partition key: "blacklist" (single partition for simplicity)
        Row key: token_hash

        Args:
            token_hash: Hash of the JWT token
            ttl_seconds: How long until the token expires naturally

        Returns:
            True if blacklisted successfully
        """
        table_client = self._get_table_client(TOKEN_BLACKLIST_TABLE)

        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        entity = {
            "PartitionKey": "blacklist",
            "RowKey": token_hash,
            "expires_at": expiry.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await table_client.upsert_entity(entity)
            logger.info("token_blacklisted", token_hash=token_hash[:8])
            return True
        except Exception as e:
            logger.error("token_blacklist_failed", error=str(e))
            return False

    async def is_token_blacklisted(self, token_hash: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token_hash: Hash of the JWT token

        Returns:
            True if token is blacklisted and not expired
        """
        table_client = self._get_table_client(TOKEN_BLACKLIST_TABLE)

        try:
            entity = await table_client.get_entity("blacklist", token_hash)
            expires_at = datetime.fromisoformat(entity["expires_at"])

            # Check if still valid (not expired)
            if datetime.now(timezone.utc) < expires_at:
                return True

            # Token expired, can be cleaned up
            return False
        except ResourceNotFoundError:
            return False

    # =========================================================================
    # Password Reset Token Operations
    # =========================================================================

    async def store_password_reset_token(
        self,
        user_id: str,
        token: str,
        ttl_seconds: int = 3600,  # 1 hour default
    ) -> bool:
        """
        Store a password reset token.

        Partition key: "reset"
        Row key: token (hashed for security)

        Args:
            user_id: The user's ID
            token: The reset token
            ttl_seconds: Token validity period

        Returns:
            True if stored successfully
        """
        table_client = self._get_table_client(RESET_TOKENS_TABLE)

        # Hash the token for storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        entity = {
            "PartitionKey": "reset",
            "RowKey": token_hash,
            "user_id": user_id,
            "expires_at": expiry.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await table_client.upsert_entity(entity)
            logger.info("reset_token_stored", user_id=user_id)
            return True
        except Exception as e:
            logger.error("reset_token_store_failed", error=str(e))
            return False

    async def validate_password_reset_token(self, token: str) -> Optional[str]:
        """
        Validate a password reset token and return the user_id.

        Args:
            token: The reset token to validate

        Returns:
            user_id if valid, None otherwise
        """
        table_client = self._get_table_client(RESET_TOKENS_TABLE)

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            entity = await table_client.get_entity("reset", token_hash)
            expires_at = datetime.fromisoformat(entity["expires_at"])

            if datetime.now(timezone.utc) < expires_at:
                return entity["user_id"]

            # Token expired
            return None
        except ResourceNotFoundError:
            return None

    async def delete_password_reset_token(self, token: str) -> bool:
        """
        Delete a password reset token (after use).

        Args:
            token: The reset token to delete

        Returns:
            True if deleted successfully
        """
        table_client = self._get_table_client(RESET_TOKENS_TABLE)

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            await table_client.delete_entity("reset", token_hash)
            return True
        except ResourceNotFoundError:
            return False

    # =========================================================================
    # Rate Limiting Operations
    # =========================================================================

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check and update rate limit for a key.

        Args:
            key: Rate limit key (e.g., "login:user@example.com")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        table_client = self._get_table_client(RATE_LIMITS_TABLE)

        # Partition by key prefix, row by full key
        partition = key.split(":")[0] if ":" in key else "default"
        row_key = hashlib.sha256(key.encode()).hexdigest()

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        try:
            entity = await table_client.get_entity(partition, row_key)

            # Check if window has reset
            last_reset = datetime.fromisoformat(entity.get("window_start", now.isoformat()))

            if last_reset < window_start:
                # Window expired, reset counter
                count = 1
                entity["count"] = count
                entity["window_start"] = now.isoformat()
            else:
                count = int(entity.get("count", 0)) + 1
                entity["count"] = count

            await table_client.upsert_entity(entity)

        except ResourceNotFoundError:
            # First request
            count = 1
            new_entity: dict[str, object] = {
                "PartitionKey": partition,
                "RowKey": row_key,
                "count": count,
                "window_start": now.isoformat(),
            }
            await table_client.upsert_entity(new_entity)

        allowed = count <= max_requests
        remaining = max(0, max_requests - count)

        return allowed, remaining


# Singleton instance
_table_service: Optional[AzureTableService] = None


async def get_table_service() -> AzureTableService:
    """Get the singleton Azure Table Service instance."""
    global _table_service

    if _table_service is None:
        _table_service = AzureTableService()
        await _table_service.initialize()

    return _table_service


async def close_table_service() -> None:
    """Close the Azure Table Service."""
    global _table_service

    if _table_service:
        await _table_service.close()
        _table_service = None
