"""
SMS Service using Azure Communication Services.

Handles:
- Phone number verification
- Daily poll notifications via SMS
- SMS delivery tracking
"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict

import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class BulkSMSResult(TypedDict):
    """Result of bulk SMS sending operation."""

    sent: int
    failed: int
    failed_user_ids: list[str]


class SMSService:
    """
    SMS notification service using Azure Communication Services.

    Features:
    - Phone verification with 6-digit codes
    - Daily poll reminders with direct links
    - Delivery status tracking
    """

    def __init__(self):
        self._client = None
        self._initialized = False

    async def initialize(self):
        """Initialize the Azure Communication Services client."""
        if self._initialized:
            return

        if not settings.AZURE_COMMUNICATION_CONNECTION_STRING:
            logger.warning("Azure Communication Services not configured, SMS disabled")
            self._initialized = True
            return

        try:
            from azure.communication.sms import SmsClient

            self._client = SmsClient.from_connection_string(settings.AZURE_COMMUNICATION_CONNECTION_STRING)
            self._initialized = True
            logger.info("SMS service initialized successfully")

        except ImportError:
            logger.warning("azure-communication-sms not installed. Install with: pip install azure-communication-sms")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize SMS service: {e}")
            self._initialized = True

    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code."""
        return "".join(random.choices(string.digits, k=6))

    def is_code_expired(self, sent_at: Optional[datetime]) -> bool:
        """Check if a verification code has expired."""
        if not sent_at:
            return True

        expiry = sent_at + timedelta(minutes=settings.SMS_VERIFICATION_CODE_EXPIRY_MINUTES)
        return datetime.now(timezone.utc) > expiry

    async def send_verification_code(
        self,
        phone_number: str,
        code: str,
    ) -> bool:
        """
        Send a verification code via SMS.

        Args:
            phone_number: Phone number in E.164 format
            code: 6-digit verification code

        Returns:
            True if sent successfully, False otherwise
        """
        await self.initialize()

        if not self._client:
            logger.warning("SMS service not available, cannot send verification")
            return False

        message = (
            f"Your TruePulse verification code is: {code}\n\n"
            f"This code expires in {settings.SMS_VERIFICATION_CODE_EXPIRY_MINUTES} minutes."
        )

        sender = settings.AZURE_COMMUNICATION_SENDER_NUMBER
        if not sender:
            logger.error("SMS sender number not configured")
            return False

        try:
            response = self._client.send(
                from_=sender,
                to=phone_number,
                message=message,
            )

            # Check if successful
            if response.successful:
                logger.info(f"Verification SMS sent to {phone_number[:6]}***")
                return True
            else:
                logger.error(f"SMS send failed: {response.error_message}")
                return False

        except Exception as e:
            logger.error(f"Error sending verification SMS: {e}")
            return False

    async def send_daily_poll_notification(
        self,
        phone_number: str,
        poll_question: str,
        poll_id: str,
        base_url: str = "https://truepulse.app",
    ) -> bool:
        """
        Send a daily poll notification via SMS.

        Args:
            phone_number: Phone number in E.164 format
            poll_question: The poll question (truncated if needed)
            poll_id: Poll ID for the link
            base_url: Base URL of the application

        Returns:
            True if sent successfully, False otherwise
        """
        await self.initialize()

        if not self._client:
            logger.warning("SMS service not available, cannot send notification")
            return False

        # Truncate question if too long (SMS is limited)
        max_question_len = 100
        if len(poll_question) > max_question_len:
            poll_question = poll_question[: max_question_len - 3] + "..."

        poll_url = f"{base_url}/polls/{poll_id}"

        message = (
            f'📊 Today\'s TruePulse Poll:\n\n"{poll_question}"\n\nVote now: {poll_url}\n\nReply STOP to unsubscribe'
        )

        sender = settings.AZURE_COMMUNICATION_SENDER_NUMBER
        if not sender:
            logger.error("SMS sender number not configured")
            return False

        try:
            response = self._client.send(
                from_=sender,
                to=phone_number,
                message=message,
            )

            if response.successful:
                logger.info(f"Daily poll SMS sent to {phone_number[:6]}***")
                return True
            else:
                logger.error(f"Daily poll SMS failed: {response.error_message}")
                return False

        except Exception as e:
            logger.error(f"Error sending daily poll SMS: {e}")
            return False

    async def send_bulk_daily_notifications(
        self,
        recipients: list[dict],
        poll_question: str,
        poll_id: str,
        base_url: str = "https://truepulse.app",
    ) -> BulkSMSResult:
        """
        Send daily poll notifications to multiple recipients.

        Args:
            recipients: List of dicts with 'phone_number' and 'user_id'
            poll_question: The poll question
            poll_id: Poll ID for the link
            base_url: Base URL of the application

        Returns:
            Dict with 'sent' count, 'failed' count, and 'failed_numbers' list
        """
        results: BulkSMSResult = {
            "sent": 0,
            "failed": 0,
            "failed_user_ids": [],
        }

        for recipient in recipients:
            success = await self.send_daily_poll_notification(
                phone_number=recipient["phone_number"],
                poll_question=poll_question,
                poll_id=poll_id,
                base_url=base_url,
            )

            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["failed_user_ids"].append(recipient["user_id"])

        logger.info(f"Bulk SMS complete: {results['sent']} sent, {results['failed']} failed")

        return results


# Singleton instance
sms_service = SMSService()
