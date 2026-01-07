"""Repository modules for Cosmos DB database access."""

from repositories.cosmos_achievement_repository import CosmosAchievementRepository
from repositories.cosmos_poll_repository import CosmosPollRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.cosmos_vote_repository import CosmosVoteRepository
from repositories.provider import (
    get_achievement_repository,
    get_poll_repository,
    get_user_repository,
    get_vote_repository,
)

__all__ = [
    "CosmosAchievementRepository",
    "CosmosPollRepository",
    "CosmosUserRepository",
    "CosmosVoteRepository",
    "get_achievement_repository",
    "get_poll_repository",
    "get_user_repository",
    "get_vote_repository",
]
