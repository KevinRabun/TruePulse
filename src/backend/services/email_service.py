"""
Email Service using Azure Communication Services.

Handles:
- Password reset emails
- Email verification
- Notification emails
"""

from typing import Optional

import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """
    Email service using Azure Communication Services.

    Features:
    - Password reset emails with secure tokens
    - Email verification for new accounts
    - Notification emails (poll reminders, etc.)
    """

    def __init__(self):
        self._client = None
        self._initialized = False
        self._sender_address: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the Azure Email client."""
        if self._initialized:
            return

        connection_string = getattr(
            settings, "AZURE_COMMUNICATION_CONNECTION_STRING", None
        )
        self._sender_address = getattr(settings, "AZURE_EMAIL_SENDER_ADDRESS", None)

        if not connection_string or not self._sender_address:
            logger.warning(
                "email_service_not_configured",
                has_connection_string=bool(connection_string),
                has_sender_address=bool(self._sender_address),
            )
            self._initialized = True
            return

        try:
            from azure.communication.email import EmailClient

            self._client = EmailClient.from_connection_string(connection_string)
            self._initialized = True
            logger.info("email_service_initialized")

        except ImportError:
            logger.warning(
                "email_sdk_not_installed",
                message="Install with: pip install azure-communication-email",
            )
            self._initialized = True
        except Exception as e:
            logger.error("email_service_init_failed", error=str(e))
            self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if email service is available."""
        return self._client is not None and self._sender_address is not None

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        frontend_url: Optional[str] = None,
    ) -> bool:
        """
        Send a password reset email.

        Args:
            to_email: Recipient email address
            reset_token: The password reset token
            frontend_url: Base URL for the frontend (defaults to settings)

        Returns:
            True if sent successfully
        """
        await self.initialize()

        if not self.is_available:
            logger.warning(
                "email_service_unavailable",
                action="password_reset",
                to_email=to_email[:3] + "***",
            )
            return False

        base_url = frontend_url or getattr(
            settings, "FRONTEND_URL", "http://localhost:3000"
        )
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        subject = "Reset Your TruePulse Password"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h1 style="color: #1a1a1a; margin-bottom: 24px;">Password Reset Request</h1>

                <p style="color: #4a4a4a; line-height: 1.6;">
                    We received a request to reset the password for your TruePulse account.
                    Click the button below to set a new password:
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{reset_url}"
                       style="display: inline-block; background-color: #3b82f6; color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                    This link will expire in 1 hour. If you didn't request a password reset,
                    you can safely ignore this email.
                </p>

                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">

                <p style="color: #9ca3af; font-size: 12px;">
                    If the button doesn't work, copy and paste this URL into your browser:<br>
                    <span style="color: #3b82f6; word-break: break-all;">{reset_url}</span>
                </p>

                <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
                    — The TruePulse Team
                </p>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
Password Reset Request

We received a request to reset the password for your TruePulse account.

Reset your password here: {reset_url}

This link will expire in 1 hour. If you didn't request a password reset,
you can safely ignore this email.

— The TruePulse Team
        """.strip()

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
        frontend_url: Optional[str] = None,
    ) -> bool:
        """
        Send an email verification email.

        Args:
            to_email: Recipient email address
            verification_token: The verification token
            username: User's display name
            frontend_url: Base URL for the frontend

        Returns:
            True if sent successfully
        """
        await self.initialize()

        if not self.is_available:
            logger.warning(
                "email_service_unavailable",
                action="verification",
                to_email=to_email[:3] + "***",
            )
            return False

        base_url = frontend_url or getattr(
            settings, "FRONTEND_URL", "http://localhost:3000"
        )
        verify_url = f"{base_url}/verify-email?token={verification_token}"

        subject = "Verify Your TruePulse Account"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h1 style="color: #1a1a1a; margin-bottom: 24px;">Welcome to TruePulse, {username}!</h1>

                <p style="color: #4a4a4a; line-height: 1.6;">
                    Thanks for signing up! Please verify your email address to complete your registration
                    and start participating in real-time polls.
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{verify_url}"
                       style="display: inline-block; background-color: #10b981; color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600;">
                        Verify Email Address
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                    This link will expire in 24 hours.
                </p>

                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">

                <p style="color: #9ca3af; font-size: 12px;">
                    If you didn't create a TruePulse account, you can safely ignore this email.
                </p>

                <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
                    — The TruePulse Team
                </p>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
Welcome to TruePulse, {username}!

Thanks for signing up! Please verify your email address to complete your registration.

Verify here: {verify_url}

This link will expire in 24 hours.

If you didn't create a TruePulse account, you can safely ignore this email.

— The TruePulse Team
        """.strip()

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
        )

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: str,
    ) -> bool:
        """
        Internal method to send an email.

        Args:
            to_email: Recipient address
            subject: Email subject
            html_content: HTML body
            plain_text: Plain text fallback

        Returns:
            True if sent successfully
        """
        if not self._client or not self._sender_address:
            return False

        try:
            message = {
                "senderAddress": self._sender_address,
                "recipients": {
                    "to": [{"address": to_email}],
                },
                "content": {
                    "subject": subject,
                    "plainText": plain_text,
                    "html": html_content,
                },
            }

            poller = self._client.begin_send(message)
            result = poller.result()

            if result["status"] == "Succeeded":
                logger.info(
                    "email_sent",
                    to=to_email[:3] + "***",
                    subject=subject,
                    message_id=result.get("id"),
                )
                return True
            else:
                logger.error(
                    "email_send_failed",
                    status=result["status"],
                    error=result.get("error"),
                )
                return False

        except Exception as e:
            logger.error("email_send_error", error=str(e), to=to_email[:3] + "***")
            return False


# Global instance
email_service = EmailService()


async def get_email_service() -> EmailService:
    """Dependency for getting email service."""
    await email_service.initialize()
    return email_service
