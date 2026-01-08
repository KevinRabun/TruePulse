"""
Cosmos DB User repository.

Handles user CRUD operations using Azure Cosmos DB with secondary indexes
for email and username lookups.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from db.cosmos_session import (
    EMAIL_LOOKUP_CONTAINER,
    USERNAME_LOOKUP_CONTAINER,
    USERS_CONTAINER,
    create_item,
    delete_item,
    query_count,
    query_items,
    read_item,
    upsert_item,
)
from models.cosmos_documents import (
    EmailLookupDocument,
    UserDocument,
    UsernameLookupDocument,
)

logger = logging.getLogger(__name__)


class CosmosUserRepository:
    """Repository for user operations using Cosmos DB."""

    # ========================================================================
    # Read Operations
    # ========================================================================

    async def get_by_id(self, user_id: str) -> Optional[UserDocument]:
        """Get a user by ID (direct point read - very efficient)."""
        data = await read_item(USERS_CONTAINER, user_id, partition_key=user_id)
        if data is None:
            return None
        return UserDocument(**data)

    async def get_by_email(self, email: str) -> Optional[UserDocument]:
        """
        Get a user by email using secondary index lookup.

        Two-step process:
        1. Look up user_id from email-lookup container
        2. Point read user from users container
        """
        email_lower = email.lower()

        # Step 1: Find user_id from email lookup
        lookup_data = await read_item(
            EMAIL_LOOKUP_CONTAINER,
            email_lower,  # email is the ID in lookup container
            partition_key=email_lower,
        )
        if lookup_data is None:
            return None

        # Step 2: Get user document
        user_id = lookup_data.get("user_id")
        if not user_id:
            return None

        return await self.get_by_id(user_id)

    async def get_by_username(self, username: str) -> Optional[UserDocument]:
        """
        Get a user by username using secondary index lookup.

        Two-step process:
        1. Look up user_id from username-lookup container
        2. Point read user from users container
        """
        # Step 1: Find user_id from username lookup
        lookup_data = await read_item(
            USERNAME_LOOKUP_CONTAINER,
            username,  # username is the ID in lookup container
            partition_key=username,
        )
        if lookup_data is None:
            return None

        # Step 2: Get user document
        user_id = lookup_data.get("user_id")
        if not user_id:
            return None

        return await self.get_by_id(user_id)

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered (efficient lookup)."""
        email_lower = email.lower()
        lookup_data = await read_item(
            EMAIL_LOOKUP_CONTAINER,
            email_lower,
            partition_key=email_lower,
        )
        return lookup_data is not None

    async def username_exists(self, username: str) -> bool:
        """Check if username is already taken (efficient lookup)."""
        lookup_data = await read_item(
            USERNAME_LOOKUP_CONTAINER,
            username,
            partition_key=username,
        )
        return lookup_data is not None

    # ========================================================================
    # Write Operations
    # ========================================================================

    async def create(
        self,
        email: str,
        username: str,
        welcome_points: int = 100,
        display_name: str | None = None,
    ) -> UserDocument:
        """
        Create a new user with secondary indexes.

        Creates three documents:
        1. User document in users container
        2. Email lookup in email-lookup container
        3. Username lookup in username-lookup container
        """
        user_id = str(uuid4())
        email_lower = email.lower()
        now = datetime.now(timezone.utc)

        # Create user document
        user = UserDocument(
            id=user_id,
            email=email_lower,
            username=username,
            display_name=display_name,
            is_active=True,
            is_verified=False,
            total_points=welcome_points,
            level=1,
            created_at=now,
            updated_at=now,
        )

        # Create email lookup document
        email_lookup = EmailLookupDocument(
            id=email_lower,
            email=email_lower,
            user_id=user_id,
        )

        # Create username lookup document
        username_lookup = UsernameLookupDocument(
            id=username,
            username=username,
            user_id=user_id,
        )

        # Write all three documents
        # Note: In production, consider using transactional batch for atomicity
        await create_item(USERS_CONTAINER, user.model_dump(mode="json"))
        await create_item(EMAIL_LOOKUP_CONTAINER, email_lookup.model_dump(mode="json"))
        await create_item(USERNAME_LOOKUP_CONTAINER, username_lookup.model_dump(mode="json"))

        logger.info(f"Created user {user_id} with email {email_lower}")
        return user

    async def update(self, user: UserDocument) -> UserDocument:
        """Update a user document."""
        user.updated_at = datetime.now(timezone.utc)
        await upsert_item(USERS_CONTAINER, user.model_dump(mode="json"))
        return user

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user and their lookup indexes.

        Note: Consider soft delete instead by setting deleted_at.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        # Delete in reverse order: lookups first, then user
        try:
            await delete_item(EMAIL_LOOKUP_CONTAINER, user.email, partition_key=user.email)
        except Exception as e:
            logger.warning(f"Failed to delete email lookup for {user.email}: {e}")

        try:
            await delete_item(USERNAME_LOOKUP_CONTAINER, user.username, partition_key=user.username)
        except Exception as e:
            logger.warning(f"Failed to delete username lookup for {user.username}: {e}")

        await delete_item(USERS_CONTAINER, user_id, partition_key=user_id)

        logger.info(f"Deleted user {user_id}")
        return True

    async def soft_delete(self, user_id: str) -> Optional[UserDocument]:
        """Soft delete a user by setting deleted_at timestamp."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        return await self.update(user)

    # ========================================================================
    # Profile & Settings Updates
    # ========================================================================

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.last_login_at = datetime.now(timezone.utc)
        await self.update(user)
        return True

    async def award_points(
        self,
        user_id: str,
        points: int,
        update_level: bool = True,
    ) -> Optional[UserDocument]:
        """Award points to a user and optionally update level."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.total_points += points

        if update_level:
            # Level calculation: level up every 500 points
            user.level = max(1, (user.total_points // 500) + 1)

        return await self.update(user)

    async def increment_votes_cast(self, user_id: str) -> bool:
        """Increment the user's vote count and update streak."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        now = datetime.now(timezone.utc)
        new_streak = self._calculate_new_streak(user.last_vote_at, user.current_streak, now)

        user.votes_cast += 1
        user.last_vote_at = now
        user.current_streak = new_streak
        user.longest_streak = max(user.longest_streak, new_streak)

        await self.update(user)
        return True

    def _calculate_new_streak(
        self,
        last_vote_at: Optional[datetime],
        current_streak: int,
        now: datetime,
    ) -> int:
        """
        Calculate the new voting streak based on the last vote time.

        Streak rules:
        - First vote ever: streak = 1
        - Voted same day: streak unchanged
        - Voted yesterday (within 24-48 hours): streak + 1
        - Voted more than 48 hours ago: streak resets to 1
        """
        if last_vote_at is None:
            return 1

        # Ensure timezone-aware comparison
        if last_vote_at.tzinfo is None:
            last_vote_at = last_vote_at.replace(tzinfo=timezone.utc)

        # Calculate days since last vote using calendar dates
        last_vote_date = last_vote_at.date()
        today_date = now.date()
        days_since_last_vote = (today_date - last_vote_date).days

        if days_since_last_vote == 0:
            return max(current_streak, 1)
        elif days_since_last_vote == 1:
            return current_streak + 1
        else:
            return 1

    async def update_streak(self, user_id: str, new_streak: int) -> bool:
        """Update user's voting streak."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.current_streak = new_streak
        user.longest_streak = max(user.longest_streak, new_streak)
        await self.update(user)
        return True

    async def update_profile(
        self,
        user_id: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> Optional[UserDocument]:
        """Update user profile fields."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Handle username change (need to update lookup)
        if username is not None and username != user.username:
            # Check if new username is available
            if await self.username_exists(username):
                raise ValueError(f"Username '{username}' is already taken")

            # Delete old lookup, create new one
            try:
                await delete_item(USERNAME_LOOKUP_CONTAINER, user.username, partition_key=user.username)
            except Exception:
                pass

            new_lookup = UsernameLookupDocument(
                id=username,
                username=username,
                user_id=user_id,
            )
            await create_item(USERNAME_LOOKUP_CONTAINER, new_lookup.model_dump(mode="json"))
            user.username = username

        if display_name is not None:
            user.display_name = display_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if bio is not None:
            user.bio = bio

        return await self.update(user)

    async def update_demographics(
        self,
        user_id: str,
        age_range: Optional[str] = None,
        gender: Optional[str] = None,
        country: Optional[str] = None,
        state_province: Optional[str] = None,
        city: Optional[str] = None,
        education_level: Optional[str] = None,
        employment_status: Optional[str] = None,
        industry: Optional[str] = None,
        political_leaning: Optional[str] = None,
        marital_status: Optional[str] = None,
        religious_affiliation: Optional[str] = None,
        ethnicity: Optional[str] = None,
        household_income: Optional[str] = None,
        parental_status: Optional[str] = None,
        housing_status: Optional[str] = None,
    ) -> Optional[UserDocument]:
        """Update user demographics."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if age_range is not None:
            user.age_range = age_range
        if gender is not None:
            user.gender = gender
        if country is not None:
            user.country = country
        if state_province is not None:
            user.state_province = state_province
        if city is not None:
            user.city = city
        if education_level is not None:
            user.education_level = education_level
        if employment_status is not None:
            user.employment_status = employment_status
        if industry is not None:
            user.industry = industry
        if political_leaning is not None:
            user.political_leaning = political_leaning
        if marital_status is not None:
            user.marital_status = marital_status
        if religious_affiliation is not None:
            user.religious_affiliation = religious_affiliation
        if ethnicity is not None:
            user.ethnicity = ethnicity
        if household_income is not None:
            user.household_income = household_income
        if parental_status is not None:
            user.parental_status = parental_status
        if housing_status is not None:
            user.housing_status = housing_status

        return await self.update(user)

    async def update_settings(
        self,
        user_id: str,
        email_notifications: Optional[bool] = None,
        push_notifications: Optional[bool] = None,
        daily_poll_reminder: Optional[bool] = None,
        show_on_leaderboard: Optional[bool] = None,
        share_anonymous_demographics: Optional[bool] = None,
        theme_preference: Optional[str] = None,
        pulse_poll_notifications: Optional[bool] = None,
        flash_poll_notifications: Optional[bool] = None,
        flash_polls_per_day: Optional[int] = None,
    ) -> Optional[UserDocument]:
        """Update user settings."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if email_notifications is not None:
            user.email_notifications = email_notifications
        if push_notifications is not None:
            user.push_notifications = push_notifications
        if daily_poll_reminder is not None:
            user.daily_poll_reminder = daily_poll_reminder
        if show_on_leaderboard is not None:
            user.show_on_leaderboard = show_on_leaderboard
        if share_anonymous_demographics is not None:
            user.share_anonymous_demographics = share_anonymous_demographics
        if theme_preference is not None:
            user.theme_preference = theme_preference
        if pulse_poll_notifications is not None:
            user.pulse_poll_notifications = pulse_poll_notifications
        if flash_poll_notifications is not None:
            user.flash_poll_notifications = flash_poll_notifications
        if flash_polls_per_day is not None:
            user.flash_polls_per_day = flash_polls_per_day

        return await self.update(user)

    async def verify_email(self, user_id: str) -> bool:
        """Mark user's email as verified."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.email_verified = True
        user.is_verified = True
        await self.update(user)
        return True

    # ========================================================================
    # Query Operations
    # ========================================================================

    async def get_leaderboard(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserDocument]:
        """
        Get users sorted by points for leaderboard.

        Note: Cross-partition query - use cached leaderboard snapshots for production.
        """
        # Use IS_DEFINED check to handle legacy documents where show_on_leaderboard
        # field doesn't exist (defaults to True per the UserDocument model)
        query = """
            SELECT * FROM c
            WHERE c.is_active = true
              AND (c.show_on_leaderboard = true OR NOT IS_DEFINED(c.show_on_leaderboard))
              AND NOT IS_DEFINED(c.deleted_at)
            ORDER BY c.total_points DESC
            OFFSET @offset LIMIT @limit
        """
        results = await query_items(
            USERS_CONTAINER,
            query,
            parameters=[
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ],
        )
        return [UserDocument(**r) for r in results]

    async def count_active_users(self) -> int:
        """Count total active users."""
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.is_active = true
              AND NOT IS_DEFINED(c.deleted_at)
        """
        return await query_count(USERS_CONTAINER, query)

    async def get_users_by_ids(self, user_ids: list[str]) -> list[UserDocument]:
        """Get multiple users by their IDs."""
        if not user_ids:
            return []

        # For small lists, parallel point reads are more efficient
        # For large lists, use a query
        if len(user_ids) <= 10:
            users = []
            for user_id in user_ids:
                user = await self.get_by_id(user_id)
                if user:
                    users.append(user)
            return users

        # Use IN query for larger lists
        placeholders = ", ".join([f"@id{i}" for i in range(len(user_ids))])
        query = f"SELECT * FROM c WHERE c.id IN ({placeholders})"
        parameters = [{"name": f"@id{i}", "value": uid} for i, uid in enumerate(user_ids)]

        results = await query_items(USERS_CONTAINER, query, parameters=parameters)
        return [UserDocument(**r) for r in results]

    async def get_users_by_notification_preference(
        self,
        pulse_notifications: bool = False,
        flash_notifications: bool = False,
    ) -> list[UserDocument]:
        """
        Get users by notification preferences.

        Args:
            pulse_notifications: If True, get users with pulse_poll_notifications enabled
            flash_notifications: If True, get users with flash_poll_notifications enabled

        Returns:
            List of users matching the notification preference criteria
        """
        conditions = [
            "c.is_active = true",
            "NOT IS_DEFINED(c.deleted_at)",
        ]

        if pulse_notifications:
            conditions.append("c.pulse_poll_notifications = true")
        if flash_notifications:
            conditions.append("c.flash_poll_notifications = true")

        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM c WHERE {where_clause}"

        results = await query_items(USERS_CONTAINER, query)
        return [UserDocument(**r) for r in results]

    async def count_active_users_since(self, days: int = 30) -> int:
        """
        Count active users who have logged in within the specified number of days.

        Used for platform statistics.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.is_active = true
              AND NOT IS_DEFINED(c.deleted_at)
              AND c.last_login_at >= @cutoff
        """
        return await query_count(
            USERS_CONTAINER,
            query,
            parameters=[{"name": "@cutoff", "value": cutoff_iso}],
        )

    async def count_unique_countries(self) -> int:
        """
        Count unique countries from users who shared demographics.

        Used for platform statistics.
        """
        query = """
            SELECT VALUE COUNT(1) FROM (
                SELECT DISTINCT c.country FROM c
                WHERE c.is_active = true
                  AND NOT IS_DEFINED(c.deleted_at)
                  AND IS_DEFINED(c.country)
                  AND c.country != null
                  AND c.share_anonymous_demographics = true
            )
        """
        return await query_count(USERS_CONTAINER, query)

    # ========================================================================
    # Ad Engagement
    # ========================================================================

    async def record_ad_view(self, user_id: str) -> bool:
        """Record an ad view for a user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        now = datetime.now(timezone.utc)

        # Check if this continues the ad view streak
        if user.last_ad_view_at:
            last_date = user.last_ad_view_at.date()
            today = now.date()
            days_diff = (today - last_date).days

            if days_diff == 1:
                user.ad_view_streak += 1
            elif days_diff > 1:
                user.ad_view_streak = 1
            # Same day - streak unchanged
        else:
            user.ad_view_streak = 1

        user.ad_views += 1
        user.last_ad_view_at = now

        await self.update(user)
        return True

    async def record_ad_click(self, user_id: str) -> bool:
        """Record an ad click for a user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.ad_clicks += 1
        await self.update(user)
        return True

    async def increment_shares(self, user_id: str) -> bool:
        """Increment the user's share count."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.total_shares += 1
        await self.update(user)
        return True

    # ========================================================================
    # Passkey Operations
    # ========================================================================

    async def get_by_passkey_credential_id(self, credential_id: str) -> Optional[UserDocument]:
        """
        Find a user by their passkey credential ID.

        Since passkeys are embedded in user documents, we need to use a
        Cosmos DB query with ARRAY_CONTAINS to find the matching user.

        Args:
            credential_id: The base64url-encoded credential ID to search for

        Returns:
            UserDocument if found, None otherwise
        """
        # Query for users with matching passkey credential_id
        query = """
            SELECT * FROM c
            WHERE ARRAY_CONTAINS(c.passkeys, {"credential_id": @credential_id}, true)
        """
        parameters = [{"name": "@credential_id", "value": credential_id}]

        results = await query_items(USERS_CONTAINER, query, parameters=parameters)
        if results:
            return UserDocument(**results[0])
        return None
