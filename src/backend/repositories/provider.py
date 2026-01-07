"""
Repository provider for dependency injection.

This module provides a unified interface for accessing repositories
using Cosmos DB as the primary data store.

Usage:
    from repositories.provider import get_user_repository, get_poll_repository, ...

    # In FastAPI dependencies:
    async def some_endpoint(
        user_repo: UserRepositoryProtocol = Depends(get_user_repository),
    ):
        user = await user_repo.get_by_id(user_id)
"""

import logging
from typing import Protocol, runtime_checkable

from core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


def is_cosmos_enabled() -> bool:
    """Check if Cosmos DB is configured and enabled."""
    # Cosmos DB can be configured via either:
    # 1. AZURE_COSMOS_ENDPOINT (for Azure deployment with RBAC)
    # 2. AZURE_COSMOS_CONNECTION_STRING (for local emulator)
    return bool(settings.AZURE_COSMOS_ENDPOINT or settings.AZURE_COSMOS_CONNECTION_STRING)


# =============================================================================
# Repository Protocols (Interfaces)
# =============================================================================


@runtime_checkable
class UserRepositoryProtocol(Protocol):
    """Protocol defining user repository operations."""

    async def get_by_id(self, user_id: str): ...
    async def get_by_email(self, email: str): ...
    async def get_by_username(self, username: str): ...
    async def create(self, email: str, username: str, display_name: str | None = None, **kwargs): ...
    async def update_profile(self, user_id: str, **kwargs): ...


@runtime_checkable
class PollRepositoryProtocol(Protocol):
    """Protocol defining poll repository operations."""

    async def get_by_id(self, poll_id: str): ...
    async def get_current_poll(self): ...
    async def create(self, **kwargs): ...


@runtime_checkable
class VoteRepositoryProtocol(Protocol):
    """Protocol defining vote repository operations."""

    async def get_by_hash(self, vote_hash: str, poll_id: str): ...
    async def exists_by_hash(self, vote_hash: str, poll_id: str) -> bool: ...
    async def create(self, vote_hash: str, poll_id: str, choice_id: str, **kwargs): ...


@runtime_checkable
class AchievementRepositoryProtocol(Protocol):
    """Protocol defining achievement repository operations."""

    async def get_achievement(self, achievement_id: str): ...
    async def get_all_achievements(self, include_secret: bool = False): ...
    async def get_user_achievements(self, user_id: str, unlocked_only: bool = False): ...


# =============================================================================
# Repository Factory Functions
# =============================================================================


async def get_user_repository():
    """
    Get the appropriate user repository based on configuration.

    Returns Cosmos repository if Cosmos DB is configured,
    otherwise returns SQL repository wrapper.
    """
    if is_cosmos_enabled():
        from repositories.cosmos_user_repository import CosmosUserRepository

        return CosmosUserRepository()
    else:
        # TODO: Implement SQL repository wrapper if needed for gradual migration
        raise NotImplementedError(
            "SQL repository wrapper not implemented. Please configure AZURE_COSMOS_ENDPOINT to use Cosmos DB."
        )


async def get_poll_repository():
    """Get the appropriate poll repository based on configuration."""
    if is_cosmos_enabled():
        from repositories.cosmos_poll_repository import CosmosPollRepository

        return CosmosPollRepository()
    else:
        raise NotImplementedError(
            "SQL repository wrapper not implemented. Please configure AZURE_COSMOS_ENDPOINT to use Cosmos DB."
        )


async def get_vote_repository():
    """Get the appropriate vote repository based on configuration."""
    if is_cosmos_enabled():
        from repositories.cosmos_vote_repository import CosmosVoteRepository

        return CosmosVoteRepository()
    else:
        raise NotImplementedError(
            "SQL repository wrapper not implemented. Please configure AZURE_COSMOS_ENDPOINT to use Cosmos DB."
        )


async def get_achievement_repository():
    """Get the appropriate achievement repository based on configuration."""
    if is_cosmos_enabled():
        from repositories.cosmos_achievement_repository import CosmosAchievementRepository

        return CosmosAchievementRepository()
    else:
        raise NotImplementedError(
            "SQL repository wrapper not implemented. Please configure AZURE_COSMOS_ENDPOINT to use Cosmos DB."
        )


# =============================================================================
# FastAPI Dependencies
# =============================================================================

# Lazy imports to avoid circular dependencies
if is_cosmos_enabled():
    try:
        from repositories.cosmos_achievement_repository import (
            CosmosAchievementRepository as AchievementRepository,
        )
        from repositories.cosmos_poll_repository import (
            CosmosPollRepository as PollRepository,
        )
        from repositories.cosmos_user_repository import (
            CosmosUserRepository as UserRepository,
        )
        from repositories.cosmos_vote_repository import (
            CosmosVoteRepository as VoteRepository,
        )
    except ImportError as e:
        logger.warning(f"Cosmos repositories not available: {e}")
        UserRepository = None  # type: ignore[misc,assignment]
        PollRepository = None  # type: ignore[misc,assignment]
        VoteRepository = None  # type: ignore[misc,assignment]
        AchievementRepository = None  # type: ignore[misc,assignment]
else:
    UserRepository = None  # type: ignore[misc,assignment]
    PollRepository = None  # type: ignore[misc,assignment]
    VoteRepository = None  # type: ignore[misc,assignment]
    AchievementRepository = None  # type: ignore[misc,assignment]
