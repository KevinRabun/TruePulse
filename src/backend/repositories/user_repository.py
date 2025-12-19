"""
User repository for database operations.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_rowcount(self, result: Any) -> int:
        """Safely get rowcount from result."""
        return getattr(result, "rowcount", 0) or 0

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        result = await self.db.execute(select(func.count(User.id)).where(User.email == email.lower()))
        count = result.scalar() or 0
        return count > 0

    async def username_exists(self, username: str) -> bool:
        """Check if username is already taken."""
        result = await self.db.execute(select(func.count(User.id)).where(User.username == username))
        count = result.scalar() or 0
        return count > 0

    async def create(
        self,
        email: str,
        username: str,
        hashed_password: str,
        welcome_points: int = 100,
    ) -> User:
        """Create a new user."""
        user = User(
            id=str(uuid4()),
            email=email.lower(),
            username=username,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            total_points=welcome_points,
            level=1,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        result = await self.db.execute(
            update(User).where(User.id == user_id).values(last_login_at=datetime.now(timezone.utc))
        )
        return self._get_rowcount(result) > 0

    async def award_points(
        self,
        user_id: str,
        points: int,
        update_level: bool = True,
    ) -> Optional[User]:
        """Award points to a user and optionally update level."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        new_points = user.total_points + points
        new_level = user.level

        if update_level:
            # Level calculation: level up every 500 points
            new_level = max(1, (new_points // 500) + 1)

        await self.db.execute(update(User).where(User.id == user_id).values(total_points=new_points, level=new_level))

        await self.db.refresh(user)
        return user

    async def increment_votes_cast(self, user_id: str) -> bool:
        """Increment the user's vote count."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                votes_cast=User.votes_cast + 1,
                last_vote_at=datetime.now(timezone.utc),
            )
        )
        return self._get_rowcount(result) > 0

    async def update_streak(self, user_id: str, new_streak: int) -> bool:
        """Update user's voting streak."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        longest_streak = max(user.longest_streak, new_streak)

        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                current_streak=new_streak,
                longest_streak=longest_streak,
            )
        )
        return self._get_rowcount(result) > 0

    async def update_profile(
        self,
        user_id: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> Optional[User]:
        """Update user profile fields."""
        updates = {}
        if username is not None:
            updates["username"] = username
        if avatar_url is not None:
            updates["avatar_url"] = avatar_url
        if bio is not None:
            updates["bio"] = bio

        if not updates:
            return await self.get_by_id(user_id)

        await self.db.execute(update(User).where(User.id == user_id).values(**updates))

        return await self.get_by_id(user_id)

    async def update_demographics(
        self,
        user_id: str,
        age_range: Optional[str] = None,
        gender: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        state_province: Optional[str] = None,
        city: Optional[str] = None,
        education_level: Optional[str] = None,
        employment_status: Optional[str] = None,
        industry: Optional[str] = None,
        political_leaning: Optional[str] = None,
    ) -> Optional[User]:
        """Update user demographics."""
        updates = {}
        if age_range is not None:
            updates["age_range"] = age_range
        if gender is not None:
            updates["gender"] = gender
        if country is not None:
            updates["country"] = country
        if region is not None:
            updates["region"] = region
        if state_province is not None:
            updates["state_province"] = state_province
        if city is not None:
            updates["city"] = city
        if education_level is not None:
            updates["education_level"] = education_level
        if employment_status is not None:
            updates["employment_status"] = employment_status
        if industry is not None:
            updates["industry"] = industry
        if political_leaning is not None:
            updates["political_leaning"] = political_leaning

        if not updates:
            return await self.get_by_id(user_id)

        await self.db.execute(update(User).where(User.id == user_id).values(**updates))

        return await self.get_by_id(user_id)

    async def verify_user(self, user_id: str) -> bool:
        """Mark user as verified."""
        result = await self.db.execute(update(User).where(User.id == user_id).values(is_verified=True))
        return self._get_rowcount(result) > 0

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user's password."""
        result = await self.db.execute(update(User).where(User.id == user_id).values(hashed_password=hashed_password))
        return self._get_rowcount(result) > 0

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        result = await self.db.execute(update(User).where(User.id == user_id).values(is_active=False))
        return self._get_rowcount(result) > 0

    async def get_leaderboard(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users sorted by points for leaderboard."""
        result = await self.db.execute(
            select(User).where(User.is_active == True).order_by(User.total_points.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_rank(self, user_id: str) -> Optional[int]:
        """Get a user's rank on the leaderboard."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        result = await self.db.execute(
            select(func.count(User.id)).where(
                User.total_points > user.total_points,
                User.is_active == True,
            )
        )
        higher_count = result.scalar() or 0
        return higher_count + 1

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
    ) -> Optional[User]:
        """Update user settings."""
        updates = {}
        if email_notifications is not None:
            updates["email_notifications"] = email_notifications
        if push_notifications is not None:
            updates["push_notifications"] = push_notifications
        if daily_poll_reminder is not None:
            updates["daily_poll_reminder"] = daily_poll_reminder
        if show_on_leaderboard is not None:
            updates["show_on_leaderboard"] = show_on_leaderboard
        if share_anonymous_demographics is not None:
            updates["share_anonymous_demographics"] = share_anonymous_demographics
        if theme_preference is not None:
            updates["theme_preference"] = theme_preference
        if pulse_poll_notifications is not None:
            updates["pulse_poll_notifications"] = pulse_poll_notifications
        if flash_poll_notifications is not None:
            updates["flash_poll_notifications"] = flash_poll_notifications
        if flash_polls_per_day is not None:
            updates["flash_polls_per_day"] = flash_polls_per_day

        if not updates:
            return await self.get_by_id(user_id)

        await self.db.execute(update(User).where(User.id == user_id).values(**updates))

        return await self.get_by_id(user_id)

    async def set_phone_verification(
        self,
        user_id: str,
        phone_number: str,
        verification_code: str,
    ) -> bool:
        """Set phone number and verification code."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                phone_number=phone_number,
                phone_verified=False,
                phone_verification_code=verification_code,
                phone_verification_sent_at=datetime.now(timezone.utc),
            )
        )
        return self._get_rowcount(result) > 0

    async def verify_phone(self, user_id: str) -> bool:
        """Mark phone as verified and set is_verified if email also verified."""
        # First check if email is already verified
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        # Set phone_verified and potentially is_verified
        update_values = {
            "phone_verified": True,
            "phone_verification_code": None,
        }

        # If email is already verified, set is_verified=True
        if user and user.email_verified:
            update_values["is_verified"] = True

        result = await self.db.execute(update(User).where(User.id == user_id).values(**update_values))
        return self._get_rowcount(result) > 0

    async def remove_phone(self, user_id: str) -> bool:
        """Remove phone number and disable SMS notifications."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                phone_number=None,
                phone_verified=False,
                phone_verification_code=None,
                sms_notifications=False,
                daily_poll_sms=False,
            )
        )
        return self._get_rowcount(result) > 0

    async def update_sms_preferences(
        self,
        user_id: str,
        sms_notifications: Optional[bool] = None,
        daily_poll_sms: Optional[bool] = None,
    ) -> bool:
        """Update SMS notification preferences."""
        updates = {}
        if sms_notifications is not None:
            updates["sms_notifications"] = sms_notifications
        if daily_poll_sms is not None:
            updates["daily_poll_sms"] = daily_poll_sms

        if not updates:
            return True

        result = await self.db.execute(update(User).where(User.id == user_id).values(**updates))
        return self._get_rowcount(result) > 0

    async def delete_user(self, user_id: str) -> bool:
        """Soft delete a user by deactivating and clearing personal data."""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_active=False,
                email=f"deleted_{user_id}@deleted.truepulse.com",
                username=f"deleted_{user_id}",
                hashed_password="",
                phone_number=None,
                phone_verified=False,
                phone_verification_code=None,
                avatar_url=None,
                bio=None,
                # Keep demographics for aggregate stats but clear identifiable info
                deleted_at=datetime.now(timezone.utc),
            )
        )
        return self._get_rowcount(result) > 0
