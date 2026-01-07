"""
Cosmos DB Achievement repository.

Handles achievement definitions and user achievement progress.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from db.cosmos_session import (
    ACHIEVEMENTS_CONTAINER,
    POLLS_CONTAINER,
    USER_ACHIEVEMENTS_CONTAINER,
    create_item,
    delete_item,
    query_count,
    query_items,
    read_item,
    upsert_item,
)
from models.cosmos_documents import (
    AchievementDocument,
    AchievementTier,
    CommunityAchievementDocument,
    CommunityAchievementEventDocument,
    CommunityAchievementParticipantDocument,
    LeaderboardEntryDocument,
    LeaderboardSnapshotDocument,
    PointsTransactionDocument,
    UserAchievementDocument,
)

logger = logging.getLogger(__name__)


class CosmosAchievementRepository:
    """
    Repository for achievement operations using Cosmos DB.

    Manages:
    - Achievement definitions (achievements container)
    - User achievement progress (user-achievements container)
    - Points transactions (user-achievements container)
    - Leaderboard snapshots (polls container)
    """

    # ========================================================================
    # Achievement Definition Operations
    # ========================================================================

    async def get_achievement(self, achievement_id: str) -> Optional[AchievementDocument]:
        """Get an achievement definition by ID."""
        try:
            result = await read_item(ACHIEVEMENTS_CONTAINER, achievement_id, partition_key=achievement_id)
            if result is None:
                return None
            return AchievementDocument(**result)
        except Exception as e:
            logger.warning(f"Achievement {achievement_id} not found: {e}")
            return None

    async def get_all_achievements(self, include_secret: bool = False) -> list[AchievementDocument]:
        """Get all achievement definitions, optionally including secret ones."""
        if include_secret:
            query = "SELECT * FROM c ORDER BY c.sort_order"
        else:
            query = "SELECT * FROM c WHERE c.is_secret = false ORDER BY c.sort_order"

        results = await query_items(ACHIEVEMENTS_CONTAINER, query)
        return [AchievementDocument(**r) for r in results]

    async def get_achievements_by_category(self, category: str) -> list[AchievementDocument]:
        """Get achievements in a specific category."""
        query = """
            SELECT * FROM c
            WHERE c.category = @category
            ORDER BY c.sort_order
        """
        results = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@category", "value": category}],
        )
        return [AchievementDocument(**r) for r in results]

    async def get_achievements_by_tier(self, tier: AchievementTier) -> list[AchievementDocument]:
        """Get achievements of a specific tier."""
        query = """
            SELECT * FROM c
            WHERE c.tier = @tier
            ORDER BY c.sort_order
        """
        results = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@tier", "value": tier.value}],
        )
        return [AchievementDocument(**r) for r in results]

    async def get_achievements_by_action_type(self, action_type: str) -> list[AchievementDocument]:
        """Get achievements by action type (e.g., 'ad_view', 'ad_click', 'ad_streak')."""
        query = """
            SELECT * FROM c
            WHERE c.action_type = @action_type
            ORDER BY c.target_count
        """
        results = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@action_type", "value": action_type}],
        )
        return [AchievementDocument(**r) for r in results]

    async def create_achievement(self, achievement: AchievementDocument) -> AchievementDocument:
        """Create a new achievement definition."""
        await create_item(ACHIEVEMENTS_CONTAINER, achievement.model_dump(mode="json"))
        logger.info(f"Created achievement: {achievement.id}")
        return achievement

    async def update_achievement(self, achievement: AchievementDocument) -> AchievementDocument:
        """Update an achievement definition."""
        await upsert_item(ACHIEVEMENTS_CONTAINER, achievement.model_dump(mode="json"))
        logger.info(f"Updated achievement: {achievement.id}")
        return achievement

    async def delete_achievement(self, achievement_id: str) -> bool:
        """Delete an achievement definition."""
        try:
            await delete_item(ACHIEVEMENTS_CONTAINER, achievement_id, partition_key=achievement_id)
            logger.info(f"Deleted achievement: {achievement_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete achievement {achievement_id}: {e}")
            return False

    # ========================================================================
    # User Achievement Operations
    # ========================================================================

    async def get_user_achievement(
        self,
        user_id: str,
        achievement_id: str,
        period_key: Optional[str] = None,
    ) -> Optional[UserAchievementDocument]:
        """Get a specific user achievement record."""
        # Build query based on whether period_key is provided
        if period_key is not None:
            query = """
                SELECT * FROM c
                WHERE c.user_id = @user_id
                  AND c.achievement_id = @achievement_id
                  AND c.period_key = @period_key
                  AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@achievement_id", "value": achievement_id},
                {"name": "@period_key", "value": period_key},
            ]
        else:
            query = """
                SELECT * FROM c
                WHERE c.user_id = @user_id
                  AND c.achievement_id = @achievement_id
                  AND (c.period_key = null OR NOT IS_DEFINED(c.period_key))
                  AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@achievement_id", "value": achievement_id},
            ]

        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=parameters,
            partition_key=user_id,
            max_items=1,
        )
        if not results:
            return None
        return UserAchievementDocument(**results[0])

    async def get_user_achievements(
        self,
        user_id: str,
        unlocked_only: bool = False,
    ) -> list[UserAchievementDocument]:
        """Get all achievements for a user."""
        if unlocked_only:
            query = """
                SELECT * FROM c
                WHERE c.user_id = @user_id
                  AND c.is_unlocked = true
                  AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
                ORDER BY c.unlocked_at DESC
            """
        else:
            query = """
                SELECT * FROM c
                WHERE c.user_id = @user_id
                  AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
            """

        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@user_id", "value": user_id}],
            partition_key=user_id,
        )
        return [UserAchievementDocument(**r) for r in results]

    async def get_recent_unlocks(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[UserAchievementDocument]:
        """Get recently unlocked achievements for a user."""
        query = """
            SELECT TOP @limit * FROM c
            WHERE c.user_id = @user_id
              AND c.is_unlocked = true
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
            ORDER BY c.unlocked_at DESC
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ],
            partition_key=user_id,
        )
        return [UserAchievementDocument(**r) for r in results]

    async def create_or_update_user_achievement(
        self,
        user_id: str,
        achievement_id: str,
        progress: int = 0,
        is_unlocked: bool = False,
        period_key: Optional[str] = None,
        unlocked_at: Optional[datetime] = None,
    ) -> UserAchievementDocument:
        """Create or update a user achievement record."""
        # Check if record exists
        existing = await self.get_user_achievement(user_id, achievement_id, period_key)

        if existing:
            # Update existing
            existing.progress = progress
            existing.is_unlocked = is_unlocked
            if is_unlocked and not existing.unlocked_at:
                existing.unlocked_at = unlocked_at or datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)
            await upsert_item(USER_ACHIEVEMENTS_CONTAINER, existing.model_dump(mode="json"))
            return existing
        else:
            # Create new
            user_achievement = UserAchievementDocument(
                id=str(uuid4()),
                user_id=user_id,
                achievement_id=achievement_id,
                progress=progress,
                is_unlocked=is_unlocked,
                period_key=period_key,
                unlocked_at=unlocked_at or (datetime.now(timezone.utc) if is_unlocked else None),
            )
            await create_item(USER_ACHIEVEMENTS_CONTAINER, user_achievement.model_dump(mode="json"))
            return user_achievement

    async def increment_progress(
        self,
        user_id: str,
        achievement_id: str,
        increment: int = 1,
        period_key: Optional[str] = None,
    ) -> UserAchievementDocument:
        """Increment progress on an achievement."""
        existing = await self.get_user_achievement(user_id, achievement_id, period_key)

        if existing:
            existing.progress += increment
            existing.updated_at = datetime.now(timezone.utc)
            await upsert_item(USER_ACHIEVEMENTS_CONTAINER, existing.model_dump(mode="json"))
            return existing
        else:
            # Create with initial progress
            return await self.create_or_update_user_achievement(
                user_id=user_id,
                achievement_id=achievement_id,
                progress=increment,
                period_key=period_key,
            )

    async def unlock_achievement(
        self,
        user_id: str,
        achievement_id: str,
        period_key: Optional[str] = None,
    ) -> UserAchievementDocument:
        """Mark an achievement as unlocked."""
        existing = await self.get_user_achievement(user_id, achievement_id, period_key)
        now = datetime.now(timezone.utc)

        if existing:
            if not existing.is_unlocked:
                existing.is_unlocked = True
                existing.unlocked_at = now
                existing.updated_at = now
                await upsert_item(USER_ACHIEVEMENTS_CONTAINER, existing.model_dump(mode="json"))
                logger.info(f"Unlocked achievement {achievement_id} for user {user_id}")
            return existing
        else:
            return await self.create_or_update_user_achievement(
                user_id=user_id,
                achievement_id=achievement_id,
                is_unlocked=True,
                period_key=period_key,
                unlocked_at=now,
            )

    async def get_achievement_unlock_count(self, achievement_id: str) -> int:
        """Get count of users who have unlocked an achievement."""
        # Note: This is a cross-partition query - use sparingly
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.achievement_id = @achievement_id
              AND c.is_unlocked = true
              AND (NOT IS_DEFINED(c.document_type) OR c.document_type = 'user_achievement')
        """
        return await query_count(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@achievement_id", "value": achievement_id}],
        )

    # ========================================================================
    # Points Transaction Operations
    # ========================================================================

    async def record_points_transaction(
        self,
        user_id: str,
        action: str,
        points: int,
        description: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> PointsTransactionDocument:
        """Record a points transaction for a user."""
        transaction = PointsTransactionDocument(
            id=str(uuid4()),
            user_id=user_id,
            action=action,
            points=points,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc),
        )
        await create_item(USER_ACHIEVEMENTS_CONTAINER, transaction.model_dump(mode="json"))
        logger.debug(f"Recorded points transaction: {points} for user {user_id}")
        return transaction

    async def get_points_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PointsTransactionDocument]:
        """Get points transaction history for a user."""
        query = """
            SELECT * FROM c
            WHERE c.user_id = @user_id
              AND c.document_type = 'points_transaction'
            ORDER BY c.created_at DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ],
            partition_key=user_id,
        )
        return [PointsTransactionDocument(**r) for r in results]

    async def get_points_earned_since(
        self,
        user_id: str,
        since: datetime,
    ) -> int:
        """Get total points earned since a specific time."""
        query = """
            SELECT VALUE SUM(c.points) FROM c
            WHERE c.user_id = @user_id
              AND c.document_type = 'points_transaction'
              AND c.points > 0
              AND c.created_at >= @since
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@since", "value": since.isoformat()},
            ],
            partition_key=user_id,
        )
        if results and results[0]:
            result = results[0]
            if isinstance(result, (int, float)):
                return int(result)
        return 0

    # ========================================================================
    # Leaderboard Operations
    # ========================================================================

    async def get_leaderboard_snapshot(
        self,
        period_type: str,
        period_key: str,
    ) -> Optional[LeaderboardSnapshotDocument]:
        """Get a leaderboard snapshot."""
        # ID is combination of period_type and period_key
        snapshot_id = f"leaderboard_{period_type}_{period_key}"
        try:
            result = await read_item(POLLS_CONTAINER, snapshot_id, partition_key=snapshot_id)
            if result is None:
                return None
            return LeaderboardSnapshotDocument(**result)
        except Exception:
            return None

    async def save_leaderboard_snapshot(
        self,
        period_type: str,
        period_key: str,
        entries: list[LeaderboardEntryDocument],
        total_users: int,
    ) -> LeaderboardSnapshotDocument:
        """Save a leaderboard snapshot."""
        snapshot_id = f"leaderboard_{period_type}_{period_key}"
        snapshot = LeaderboardSnapshotDocument(
            id=snapshot_id,
            period_type=period_type,
            period_key=period_key,
            entries=entries,
            total_users=total_users,
            created_at=datetime.now(timezone.utc),
        )
        await upsert_item(POLLS_CONTAINER, snapshot.model_dump(mode="json"))
        logger.info(f"Saved leaderboard snapshot: {snapshot_id}")
        return snapshot

    async def get_latest_leaderboard(
        self,
        period_type: str,
    ) -> Optional[LeaderboardSnapshotDocument]:
        """Get the most recent leaderboard snapshot for a period type."""
        query = """
            SELECT TOP 1 * FROM c
            WHERE c.document_type = 'leaderboard_snapshot'
              AND c.period_type = @period_type
            ORDER BY c.created_at DESC
        """
        results = await query_items(
            POLLS_CONTAINER,
            query,
            parameters=[{"name": "@period_type", "value": period_type}],
        )
        if not results:
            return None
        return LeaderboardSnapshotDocument(**results[0])

    # ========================================================================
    # Achievement Checking Helper Methods
    # ========================================================================

    async def check_and_unlock_voting_achievements(
        self,
        user_id: str,
        votes_cast: int,
    ) -> list[AchievementDocument]:
        """Check and unlock any voting-based achievements."""
        unlocked: list[AchievementDocument] = []

        # Get all voting achievements
        query = """
            SELECT * FROM c
            WHERE c.action_type = 'vote'
              AND c.target_count <= @votes_cast
        """
        achievements = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@votes_cast", "value": votes_cast}],
        )

        for ach_data in achievements:
            achievement = AchievementDocument(**ach_data)

            # Check if already unlocked
            existing = await self.get_user_achievement(user_id, achievement.id)
            if existing and existing.is_unlocked:
                continue

            # Unlock it
            await self.unlock_achievement(user_id, achievement.id)
            unlocked.append(achievement)

            # Record points if any
            if achievement.points_reward > 0:
                await self.record_points_transaction(
                    user_id=user_id,
                    action="achievement",
                    points=achievement.points_reward,
                    description=f"Unlocked: {achievement.name}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                )

        return unlocked

    async def check_and_unlock_streak_achievements(
        self,
        user_id: str,
        current_streak: int,
    ) -> list[AchievementDocument]:
        """Check and unlock any streak-based achievements."""
        unlocked: list[AchievementDocument] = []

        # Get all streak achievements
        query = """
            SELECT * FROM c
            WHERE c.action_type = 'streak'
              AND c.target_count <= @streak
        """
        achievements = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@streak", "value": current_streak}],
        )

        for ach_data in achievements:
            achievement = AchievementDocument(**ach_data)

            # Check if already unlocked
            existing = await self.get_user_achievement(user_id, achievement.id)
            if existing and existing.is_unlocked:
                continue

            # Unlock it
            await self.unlock_achievement(user_id, achievement.id)
            unlocked.append(achievement)

            # Record points if any
            if achievement.points_reward > 0:
                await self.record_points_transaction(
                    user_id=user_id,
                    action="achievement",
                    points=achievement.points_reward,
                    description=f"Unlocked: {achievement.name}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                )

        return unlocked

    async def get_user_achievement_summary(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Get summary of user's achievement progress."""
        # Get all achievements
        all_achievements = await self.get_all_achievements(include_secret=True)

        # Get user's achievements
        user_achievements = await self.get_user_achievements(user_id)
        user_ach_map = {ua.achievement_id: ua for ua in user_achievements}

        # Calculate stats
        total = len(all_achievements)
        unlocked = sum(1 for ua in user_achievements if ua.is_unlocked)
        total_points = sum(
            a.points_reward for a in all_achievements if a.id in user_ach_map and user_ach_map[a.id].is_unlocked
        )

        # Group by category
        by_category: dict[str, dict[str, int]] = {}
        for ach in all_achievements:
            if ach.category not in by_category:
                by_category[ach.category] = {"total": 0, "unlocked": 0}
            by_category[ach.category]["total"] += 1
            if ach.id in user_ach_map and user_ach_map[ach.id].is_unlocked:
                by_category[ach.category]["unlocked"] += 1

        return {
            "total_achievements": total,
            "unlocked_achievements": unlocked,
            "completion_percentage": round((unlocked / total * 100) if total > 0 else 0, 1),
            "total_points_from_achievements": total_points,
            "by_category": by_category,
        }

    # ========================================================================
    # Community Achievement Operations
    # ========================================================================

    async def get_community_achievement(self, achievement_id: str) -> Optional[CommunityAchievementDocument]:
        """Get a community achievement definition by ID."""
        try:
            result = await read_item(ACHIEVEMENTS_CONTAINER, achievement_id, partition_key=achievement_id)
            if result is None:
                return None
            if result.get("document_type") == "community_achievement":
                return CommunityAchievementDocument(**result)
            return None
        except Exception as e:
            logger.warning(f"Community achievement {achievement_id} not found: {e}")
            return None

    async def get_active_community_achievements(
        self,
    ) -> list[CommunityAchievementDocument]:
        """Get all active community achievements."""
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'community_achievement'
              AND c.is_active = true
            ORDER BY c.sort_order
        """
        results = await query_items(ACHIEVEMENTS_CONTAINER, query)
        return [CommunityAchievementDocument(**r) for r in results]

    async def get_community_achievement_event(
        self,
        achievement_id: str,
        active_only: bool = True,
    ) -> Optional[CommunityAchievementEventDocument]:
        """Get the latest event for a community achievement."""
        if active_only:
            query = """
                SELECT TOP 1 * FROM c
                WHERE c.document_type = 'community_event'
                  AND c.achievement_id = @achievement_id
                  AND c.is_completed = false
                ORDER BY c.triggered_at DESC
            """
        else:
            query = """
                SELECT TOP 1 * FROM c
                WHERE c.document_type = 'community_event'
                  AND c.achievement_id = @achievement_id
                ORDER BY c.triggered_at DESC
            """
        results = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@achievement_id", "value": achievement_id}],
        )
        if not results:
            return None
        return CommunityAchievementEventDocument(**results[0])

    async def get_completed_community_events(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> list[CommunityAchievementEventDocument]:
        """Get completed community achievement events."""
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'community_event'
              AND c.is_completed = true
            ORDER BY c.completed_at DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(
            ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ],
        )
        return [CommunityAchievementEventDocument(**r) for r in results]

    async def get_user_community_participation(
        self,
        user_id: str,
        event_id: str,
    ) -> Optional[CommunityAchievementParticipantDocument]:
        """Get a user's participation in a community achievement event."""
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'community_participant'
              AND c.user_id = @user_id
              AND c.event_id = @event_id
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@event_id", "value": event_id},
            ],
            partition_key=user_id,
            max_items=1,
        )
        if not results:
            return None
        return CommunityAchievementParticipantDocument(**results[0])

    async def get_user_community_badges(
        self,
        user_id: str,
    ) -> list[CommunityAchievementParticipantDocument]:
        """Get all community badges earned by a user."""
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'community_participant'
              AND c.user_id = @user_id
              AND c.badge_awarded = true
            ORDER BY c.contributed_at DESC
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            parameters=[{"name": "@user_id", "value": user_id}],
            partition_key=user_id,
        )
        return [CommunityAchievementParticipantDocument(**r) for r in results]

    async def get_community_leaderboard(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get aggregated community contribution leaderboard."""
        # Cross-partition query to aggregate contributions
        query = """
            SELECT
                c.user_id,
                SUM(c.contribution_count) as total_contributions,
                COUNT(1) as achievements_participated,
                SUM(c.badge_awarded ? 1 : 0) as badges_earned
            FROM c
            WHERE c.document_type = 'community_participant'
            GROUP BY c.user_id
            ORDER BY SUM(c.contribution_count) DESC
        """
        results = await query_items(
            USER_ACHIEVEMENTS_CONTAINER,
            query,
            max_items=limit,
        )
        return results

    async def create_community_achievement(
        self,
        achievement: CommunityAchievementDocument,
    ) -> CommunityAchievementDocument:
        """Create a new community achievement definition."""
        await create_item(ACHIEVEMENTS_CONTAINER, achievement.model_dump(mode="json"))
        logger.info(f"Created community achievement: {achievement.id}")
        return achievement

    async def update_community_event(
        self,
        event: CommunityAchievementEventDocument,
    ) -> CommunityAchievementEventDocument:
        """Update a community achievement event."""
        await upsert_item(ACHIEVEMENTS_CONTAINER, event.model_dump(mode="json"))
        return event

    async def create_or_update_participation(
        self,
        participation: CommunityAchievementParticipantDocument,
    ) -> CommunityAchievementParticipantDocument:
        """Create or update user participation in a community achievement."""
        await upsert_item(USER_ACHIEVEMENTS_CONTAINER, participation.model_dump(mode="json"))
        return participation
