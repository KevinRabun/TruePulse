"""Database models module - Cosmos DB document models."""

from models.cosmos_documents import (
    AchievementDocument,
    AchievementTier,
    CommunityAchievementDocument,
    CommunityAchievementEventDocument,
    CommunityAchievementParticipantDocument,
    CosmosDocument,
    EmailLookupDocument,
    LeaderboardEntryDocument,
    LeaderboardSnapshotDocument,
    PasskeyDocument,
    PointsTransactionDocument,
    PollChoiceDocument,
    PollDocument,
    PollStatus,
    PollType,
    UserAchievementDocument,
    UserDocument,
    UsernameLookupDocument,
    VoteDocument,
)

__all__ = [
    # Base
    "CosmosDocument",
    # Enums
    "PollStatus",
    "PollType",
    "AchievementTier",
    # User documents
    "UserDocument",
    "PasskeyDocument",
    "EmailLookupDocument",
    "UsernameLookupDocument",
    # Poll documents
    "PollDocument",
    "PollChoiceDocument",
    # Vote documents
    "VoteDocument",
    # Achievement documents
    "AchievementDocument",
    "UserAchievementDocument",
    "PointsTransactionDocument",
    "LeaderboardEntryDocument",
    "LeaderboardSnapshotDocument",
    # Community achievement documents
    "CommunityAchievementDocument",
    "CommunityAchievementEventDocument",
    "CommunityAchievementParticipantDocument",
]
