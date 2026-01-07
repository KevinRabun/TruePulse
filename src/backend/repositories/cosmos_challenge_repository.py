"""
Cosmos DB repository for authentication challenges.

Stores passkey registration/authentication challenges directly in Cosmos DB
to ensure reliability across container replicas during authentication flows.
Uses Cosmos DB TTL for automatic expiration.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from db.cosmos_session import (
    AUTH_CHALLENGES_CONTAINER,
    create_item,
    delete_item,
    read_item,
)

logger = logging.getLogger(__name__)

# Special partition key for anonymous/discoverable credential authentication challenges
ANONYMOUS_USER_PARTITION = "__anonymous__"


class AuthChallengeDocument(BaseModel):
    """
    Document model for authentication challenges.

    Stored in the auth-challenges container with TTL-based auto-expiration.
    """

    id: str = Field(description="Unique challenge ID")
    user_id: str = Field(description="User ID this challenge belongs to, or '__anonymous__' for discoverable flows")
    challenge: str = Field(description="Base64URL-encoded challenge bytes")
    operation: str = Field(description="Operation type: 'registration' or 'authentication'")
    device_info: dict[str, Any] | None = Field(default=None, description="Optional device information")
    expires_at: str = Field(description="ISO timestamp when challenge expires")
    created_at: str = Field(description="ISO timestamp when challenge was created")
    ttl: int = Field(description="TTL in seconds for Cosmos DB auto-deletion")


class CosmosChallengeRepository:
    """
    Repository for managing authentication challenges in Cosmos DB.

    Features:
    - Direct Cosmos DB storage (no caching)
    - Automatic TTL-based expiration
    - Partition by user_id for efficient lookups
    """

    CHALLENGE_TTL_SECONDS = 300  # 5 minutes

    async def create_challenge(
        self,
        user_id: str | None,
        challenge: str,
        operation: str,
        device_info: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new authentication challenge.

        Args:
            user_id: User ID this challenge belongs to (None for discoverable credential flow)
            challenge: Base64URL-encoded challenge bytes
            operation: Operation type ('registration' or 'authentication')
            device_info: Optional device information for trust scoring

        Returns:
            The challenge ID
        """
        challenge_id = str(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.CHALLENGE_TTL_SECONDS)

        # Use special partition for anonymous challenges
        partition_key = user_id if user_id else ANONYMOUS_USER_PARTITION

        doc = AuthChallengeDocument(
            id=challenge_id,
            user_id=partition_key,
            challenge=challenge,
            operation=operation,
            device_info=device_info,
            expires_at=expires_at.isoformat(),
            created_at=now.isoformat(),
            ttl=self.CHALLENGE_TTL_SECONDS,
        )

        await create_item(AUTH_CHALLENGES_CONTAINER, doc.model_dump())
        logger.debug(f"Created auth challenge: id={challenge_id}, user={partition_key}, operation={operation}")
        return challenge_id

    async def get_challenge(self, challenge_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        """
        Retrieve a challenge by ID.

        Args:
            challenge_id: The challenge ID
            user_id: User ID (partition key), or None for anonymous challenges

        Returns:
            Challenge data dict or None if not found/expired
        """
        partition_key = user_id if user_id else ANONYMOUS_USER_PARTITION

        try:
            doc = await read_item(AUTH_CHALLENGES_CONTAINER, challenge_id, partition_key)
            if not doc:
                logger.debug(f"Challenge not found: id={challenge_id}")
                return None

            # Double-check expiration (Cosmos TTL may have slight delay)
            expires_at = datetime.fromisoformat(doc["expires_at"])
            if datetime.now(UTC) > expires_at:
                logger.debug(f"Challenge expired: id={challenge_id}")
                # Try to delete expired challenge
                await self.delete_challenge(challenge_id, user_id)
                return None

            # Convert user_id back to None for anonymous partition
            if doc.get("user_id") == ANONYMOUS_USER_PARTITION:
                doc["user_id"] = None

            return doc
        except Exception as e:
            logger.error(f"Error retrieving challenge: id={challenge_id}, error={e}")
            return None

    async def delete_challenge(self, challenge_id: str, user_id: str | None = None) -> bool:
        """
        Delete a challenge after use.

        Args:
            challenge_id: The challenge ID to delete
            user_id: User ID (partition key), or None for anonymous challenges

        Returns:
            True if deleted, False otherwise
        """
        partition_key = user_id if user_id else ANONYMOUS_USER_PARTITION

        try:
            await delete_item(AUTH_CHALLENGES_CONTAINER, challenge_id, partition_key)
            logger.debug(f"Deleted auth challenge: id={challenge_id}")
            return True
        except Exception as e:
            logger.warning(f"Error deleting challenge: id={challenge_id}, error={e}")
            return False
