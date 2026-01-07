"""
Poll Notification Service

Sends email notifications to users when new polls are created.
Respects user notification preferences and daily limits.
Now uses Cosmos DB repositories.
"""

from datetime import datetime, timezone

import structlog

from core.config import settings
from models.cosmos_documents import PollDocument, UserDocument
from repositories.cosmos_user_repository import CosmosUserRepository
from services.email_service import EmailService

logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Service for sending poll notification emails.

    Features:
    - Sends notifications for Pulse and Flash polls
    - Respects user notification preferences
    - Enforces daily limits for Flash poll notifications
    - Resets daily counters at midnight UTC
    """

    def __init__(self):
        self.user_repo = CosmosUserRepository()
        self.email_service = EmailService()

    async def send_poll_notifications(
        self,
        poll: PollDocument,
        poll_type: str,
    ) -> dict:
        """
        Send notifications to eligible users for a new poll.

        Args:
            poll: The poll to notify users about
            poll_type: 'pulse' or 'flash'

        Returns:
            Dict with notification stats
        """
        await self.email_service.initialize()

        if not self.email_service.is_available:
            logger.warning("email_service_not_available", action="poll_notification")
            return {"sent": 0, "skipped": 0, "errors": 0, "reason": "email_service_unavailable"}

        # Get users who have notifications enabled for this poll type
        users = await self._get_eligible_users(poll_type)

        if not users:
            logger.info("no_eligible_users", poll_type=poll_type, poll_id=str(poll.id))
            return {"sent": 0, "skipped": 0, "errors": 0}

        sent = 0
        skipped = 0
        errors = 0

        for user in users:
            try:
                # Check daily limit for flash polls
                if poll_type == "flash":
                    if not self._can_send_flash_notification(user):
                        skipped += 1
                        continue

                # Send the notification email
                success = await self._send_poll_notification_email(user, poll, poll_type)

                if success:
                    sent += 1
                    # Increment flash notification counter
                    if poll_type == "flash":
                        await self._increment_flash_notification_count(user)
                else:
                    errors += 1

            except Exception as e:
                logger.error(
                    "notification_send_error",
                    user_id=str(user.id),
                    poll_id=str(poll.id),
                    error=str(e),
                )
                errors += 1

        logger.info(
            "poll_notifications_sent",
            poll_type=poll_type,
            poll_id=str(poll.id),
            sent=sent,
            skipped=skipped,
            errors=errors,
        )

        return {"sent": sent, "skipped": skipped, "errors": errors}

    async def _get_eligible_users(self, poll_type: str) -> list[UserDocument]:
        """Get users who have notifications enabled for the given poll type."""
        # Reset daily flash notification counters if needed (done in repository)
        # Get users by notification preference
        if poll_type == "pulse":
            users = await self.user_repo.get_users_by_notification_preference(pulse_notifications=True)
        elif poll_type == "flash":
            users = await self.user_repo.get_users_by_notification_preference(flash_notifications=True)
        else:
            return []

        # Filter to only active and verified users
        return [u for u in users if u.is_active and u.email_verified]

    def _can_send_flash_notification(self, user: UserDocument) -> bool:
        """Check if user can receive another flash notification today."""
        # 0 means unlimited
        flash_per_day = getattr(user, "flash_polls_per_day", 0)
        if flash_per_day == 0:
            return True

        notified_today = getattr(user, "flash_polls_notified_today", 0)
        return notified_today < flash_per_day

    async def _increment_flash_notification_count(self, user: UserDocument) -> None:
        """Increment the flash notification counter for a user."""
        user.flash_polls_notified_today = getattr(user, "flash_polls_notified_today", 0) + 1
        await self.user_repo.update(user)

    async def _send_poll_notification_email(
        self,
        user: UserDocument,
        poll: PollDocument,
        poll_type: str,
    ) -> bool:
        """Send a poll notification email to a user."""
        frontend_url = getattr(settings, "FRONTEND_URL", "https://truepulse.app")
        poll_url = f"{frontend_url}/poll?id={poll.id}"

        display_name = user.display_name or user.username

        # Customize based on poll type
        if poll_type == "pulse":
            subject = "🫀 New Daily Pulse Poll on TruePulse"
            poll_type_label = "Daily Pulse Poll"
            poll_type_description = "the daily pulse of public opinion"
            poll_color = "#f43f5e"  # Rose
            poll_emoji = "🫀"
        else:
            subject = "⚡ Flash Poll Alert on TruePulse"
            poll_type_label = "Flash Poll"
            poll_type_description = "a quick vote on breaking news"
            poll_color = "#f59e0b"  # Amber
            poll_emoji = "⚡"

        # Calculate time remaining
        end_time = poll.scheduled_end or poll.expires_at

        now = datetime.now(timezone.utc)
        if end_time is None:
            time_remaining = "soon"
        else:
            time_diff = end_time - now
            hours_left = int(time_diff.total_seconds() // 3600)
            minutes_left = int((time_diff.total_seconds() % 3600) // 60)

            if hours_left > 0:
                time_remaining = f"{hours_left}h {minutes_left}m"
            else:
                time_remaining = f"{minutes_left} minutes"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <!-- Header with poll type color -->
                <div style="background: linear-gradient(135deg, {poll_color}, {poll_color}dd); padding: 24px; text-align: center;">
                    <span style="font-size: 48px;">{poll_emoji}</span>
                    <h1 style="color: white; margin: 12px 0 0 0; font-size: 24px;">{poll_type_label}</h1>
                </div>

                <div style="padding: 32px;">
                    <p style="color: #4a4a4a; line-height: 1.6; margin-top: 0;">
                        Hi {display_name},
                    </p>

                    <p style="color: #4a4a4a; line-height: 1.6;">
                        A new {poll_type_label.lower()} is live! Join {poll_type_description} and share your voice.
                    </p>

                    <!-- Poll Question -->
                    <div style="background: #f8fafc; border-radius: 8px; padding: 20px; margin: 24px 0; border-left: 4px solid {poll_color};">
                        <p style="color: #1a1a1a; font-size: 18px; font-weight: 600; margin: 0; line-height: 1.4;">
                            {poll.question}
                        </p>
                        <p style="color: #6b7280; font-size: 14px; margin: 12px 0 0 0;">
                            ⏱️ {time_remaining} remaining to vote
                        </p>
                    </div>

                    <div style="text-align: center; margin: 32px 0;">
                        <a href="{poll_url}"
                           style="display: inline-block; background: linear-gradient(135deg, {poll_color}, {poll_color}dd); color: white; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                            Vote Now
                        </a>
                        <p style="color: #6b7280; font-size: 12px; margin-top: 12px;">
                            Or copy this link: <a href="{poll_url}" style="color: {poll_color};">{poll_url}</a>
                        </p>
                    </div>

                    <p style="color: #9ca3af; font-size: 13px; text-align: center;">
                        Earn points for every vote and climb the leaderboard!
                    </p>
                </div>

                <!-- Footer -->
                <div style="background: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                        You're receiving this because you enabled {poll_type_label.lower()} notifications.<br>
                        <a href="{frontend_url}/profile?tab=settings" style="color: #6b7280;">Manage notification preferences</a>
                    </p>
                    <p style="color: #9ca3af; font-size: 12px; margin-top: 12px;">
                        — The TruePulse Team
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
{poll_type_label} on TruePulse

Hi {display_name},

A new {poll_type_label.lower()} is live! Join {poll_type_description} and share your voice.

{poll.question}

⏱️ {time_remaining} remaining to vote

Vote now: {poll_url}

Earn points for every vote and climb the leaderboard!

---
You're receiving this because you enabled {poll_type_label.lower()} notifications.
Manage preferences: {frontend_url}/profile?tab=settings

— The TruePulse Team
        """.strip()

        return await self.email_service._send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )


async def send_poll_notifications(
    poll: PollDocument,
    poll_type: str,
) -> dict:
    """
    Convenience function to send poll notifications.

    Args:
        poll: The poll to notify users about
        poll_type: 'pulse' or 'flash'

    Returns:
        Dict with notification stats
    """
    service = NotificationService()
    return await service.send_poll_notifications(poll, poll_type)
