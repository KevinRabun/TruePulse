"""
Silent Mobile Verification Service.

Provides carrier-level identity verification without user interaction.
Uses network-based authentication to verify the user controls the phone number.

Supported Providers:
- IPification: Mobile network-based verification
- Twilio SNA: Silent Network Auth

This provides a much stronger signal than SMS OTP because:
1. Cannot be intercepted by SIM swap attacks
2. Verifies the actual network subscriber
3. No codes to enter (phishing resistant)
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.passkey import DeviceTrustScore, SilentMobileVerification
from models.user import User

logger = logging.getLogger(__name__)


class VerificationProvider(str, Enum):
    """Supported silent verification providers."""

    IPIFICATION = "ipification"
    TWILIO_SNA = "twilio-sna"


class VerificationResult:
    """Result of a silent mobile verification attempt."""

    def __init__(
        self,
        success: bool,
        phone_verified: bool = False,
        carrier_name: str | None = None,
        mcc_mnc: str | None = None,
        error: str | None = None,
        confidence_score: int = 0,
    ):
        self.success = success
        self.phone_verified = phone_verified
        self.carrier_name = carrier_name
        self.mcc_mnc = mcc_mnc  # Mobile Country Code + Mobile Network Code
        self.error = error
        self.confidence_score = confidence_score  # 0-100


class SilentMobileVerifier(ABC):
    """Abstract base class for silent mobile verification providers."""

    @abstractmethod
    async def verify(self, phone_number: str, client_ip: str, request_data: dict[str, Any]) -> VerificationResult:
        """Perform silent verification of a phone number."""
        pass


class IPificationVerifier(SilentMobileVerifier):
    """
    IPification-based silent mobile verification.

    Uses the IPification API to verify that the request originates from
    the mobile network of the claimed phone number owner.
    """

    API_BASE = "https://api.ipification.com"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def verify(self, phone_number: str, client_ip: str, request_data: dict[str, Any]) -> VerificationResult:
        """
        Verify phone number using IPification.

        This works by checking if the request comes from the mobile network
        associated with the phone number.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get access token
                auth_response = await client.post(
                    f"{self.API_BASE}/auth/realms/main/protocol/openid-connect/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )

                if auth_response.status_code != 200:
                    logger.error(f"IPification auth failed: {auth_response.text}")
                    return VerificationResult(success=False, error="Authentication failed")

                token = auth_response.json().get("access_token")

                # Step 2: Verify phone number
                verify_response = await client.post(
                    f"{self.API_BASE}/api/v1/verify",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "phone_number": phone_number,
                        "ip_address": client_ip,
                    },
                )

                if verify_response.status_code != 200:
                    logger.warning(f"IPification verify failed: {verify_response.text}")
                    return VerificationResult(success=False, error="Verification request failed")

                result = verify_response.json()

                return VerificationResult(
                    success=True,
                    phone_verified=result.get("match", False),
                    carrier_name=result.get("carrier"),
                    mcc_mnc=result.get("mcc_mnc"),
                    confidence_score=result.get("confidence", 0),
                )

        except httpx.TimeoutException:
            logger.error("IPification request timed out")
            return VerificationResult(success=False, error="Request timed out")
        except Exception as e:
            logger.error(f"IPification verification error: {e}")
            return VerificationResult(success=False, error=str(e))


class TwilioSNAVerifier(SilentMobileVerifier):
    """
    Twilio Silent Network Authentication (SNA) verifier.

    Uses Twilio's SNA API to silently verify phone number ownership
    through the mobile carrier network.
    """

    API_BASE = "https://verify.twilio.com/v2"

    def __init__(self, account_sid: str, auth_token: str):
        self.account_sid = account_sid
        self.auth_token = auth_token

    async def verify(self, phone_number: str, client_ip: str, request_data: dict[str, Any]) -> VerificationResult:
        """
        Verify phone number using Twilio Silent Network Auth.

        Twilio SNA works differently - it generates a URL that the client
        must load over mobile data to complete verification.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Create verification request
                verify_response = await client.post(
                    f"{self.API_BASE}/Services/{self.account_sid}/Verifications",
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": phone_number,
                        "Channel": "sna",
                    },
                )

                if verify_response.status_code not in (200, 201):
                    logger.warning(f"Twilio SNA request failed: {verify_response.text}")
                    return VerificationResult(success=False, error="Verification request failed")

                result = verify_response.json()

                # SNA returns a URL that needs to be loaded by the client
                # The actual verification happens when the client loads this URL
                # For now, we just return the setup success
                return VerificationResult(
                    success=True,
                    phone_verified=result.get("status") == "approved",
                    confidence_score=80 if result.get("status") == "approved" else 0,
                )

        except httpx.TimeoutException:
            logger.error("Twilio SNA request timed out")
            return VerificationResult(success=False, error="Request timed out")
        except Exception as e:
            logger.error(f"Twilio SNA verification error: {e}")
            return VerificationResult(success=False, error=str(e))


class SilentMobileService:
    """
    Service for managing silent mobile verification.

    Handles provider selection, verification attempts, and
    updating user/device trust scores based on results.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._verifier = self._create_verifier()

    def _create_verifier(self) -> SilentMobileVerifier | None:
        """Create the appropriate verifier based on configuration."""
        provider = settings.SILENT_MOBILE_PROVIDER

        if provider == "ipification":
            if settings.IPIFICATION_CLIENT_ID and settings.IPIFICATION_CLIENT_SECRET:
                return IPificationVerifier(
                    client_id=settings.IPIFICATION_CLIENT_ID,
                    client_secret=settings.IPIFICATION_CLIENT_SECRET,
                )
            logger.warning("IPification configured but credentials not set")
            return None

        elif provider == "twilio-sna":
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                return TwilioSNAVerifier(
                    account_sid=settings.TWILIO_ACCOUNT_SID,
                    auth_token=settings.TWILIO_AUTH_TOKEN,
                )
            logger.warning("Twilio SNA configured but credentials not set")
            return None

        return None

    @property
    def is_available(self) -> bool:
        """Check if silent mobile verification is available."""
        return self._verifier is not None

    async def verify_phone(
        self,
        user: User,
        phone_number: str,
        client_ip: str,
        device_fingerprint: str | None = None,
        request_data: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """
        Attempt silent mobile verification for a user.

        Args:
            user: The user to verify
            phone_number: The phone number to verify
            client_ip: The client's IP address
            device_fingerprint: Optional device fingerprint
            request_data: Additional request data for verification

        Returns:
            VerificationResult with verification outcome
        """
        if not self._verifier:
            logger.info("Silent mobile verification not configured, skipping")
            return VerificationResult(
                success=False,
                error="Silent mobile verification not configured",
            )

        # Hash phone number for storage
        phone_hash = self._hash_phone(phone_number)

        # Check for recent verification attempts (rate limiting)
        recent = await self._get_recent_attempts(phone_hash)
        if len(recent) >= 5:
            logger.warning(f"Rate limit hit for phone verification: {phone_hash[:16]}...")
            return VerificationResult(
                success=False,
                error="Too many verification attempts. Please try again later.",
            )

        # Perform verification
        result = await self._verifier.verify(
            phone_number=phone_number,
            client_ip=client_ip,
            request_data=request_data or {},
        )

        # Record the attempt - parse mcc_mnc if available
        mcc = None
        mnc = None
        if result.mcc_mnc and len(result.mcc_mnc) >= 5:
            mcc = result.mcc_mnc[:3]
            mnc = result.mcc_mnc[3:]

        # Hash device fingerprint if provided
        fingerprint_hash = None
        if device_fingerprint:
            import hashlib
            fingerprint_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

        verification_record = SilentMobileVerification(
            id=str(uuid4()),
            user_id=user.id,
            phone_hash=phone_hash,
            verified=result.phone_verified,
            verification_method=self._verifier.__class__.__name__.lower().replace("verifier", ""),
            carrier_name=result.carrier_name,
            carrier_mcc=mcc,
            carrier_mnc=mnc,
            ip_address=client_ip,
            device_fingerprint_hash=fingerprint_hash,
        )
        self.db.add(verification_record)

        # Update device trust score if verification succeeded
        if result.phone_verified and device_fingerprint:
            await self._update_device_trust(
                user_id=user.id,
                device_fingerprint=device_fingerprint,
                carrier_verified=True,
                confidence_boost=result.confidence_score,
            )

        # Update user's phone verified status if successful
        if result.phone_verified:
            user.phone_verified = True
            logger.info(f"Silent mobile verification successful for user {user.id}")

        await self.db.commit()

        return result

    async def check_carrier_match(
        self,
        user: User,
        client_ip: str,
    ) -> bool:
        """
        Quick check if the current request appears to be from the user's carrier.

        This is a lighter-weight check that can be used during authentication
        to verify the user is on their expected carrier.

        Returns True if the carrier appears to match, False otherwise.
        """
        if not self._verifier:
            return False

        if not user.phone_number:
            return False

        # Get user's last successful verification
        phone_hash = self._hash_phone(user.phone_number)
        result = await self.db.execute(
            select(SilentMobileVerification)
            .where(
                SilentMobileVerification.phone_hash == phone_hash,
                SilentMobileVerification.verified.is_(True),
            )
            .order_by(SilentMobileVerification.created_at.desc())
            .limit(1)
        )
        last_verification = result.scalar_one_or_none()

        # Get stored MCC/MNC
        last_mcc_mnc = None
        if last_verification and last_verification.carrier_mcc and last_verification.carrier_mnc:
            last_mcc_mnc = f"{last_verification.carrier_mcc}{last_verification.carrier_mnc}"

        if not last_mcc_mnc:
            return False

        # Perform a quick verification to check carrier
        current_result = await self._verifier.verify(
            phone_number=user.phone_number,
            client_ip=client_ip,
            request_data={},
        )

        # Check if MCC/MNC matches
        return (
            current_result.success
            and current_result.mcc_mnc == last_mcc_mnc
        )

    async def _get_recent_attempts(self, phone_hash: str) -> list[SilentMobileVerification]:
        """Get recent verification attempts for rate limiting."""
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(hours=1)
        result = await self.db.execute(
            select(SilentMobileVerification)
            .where(
                SilentMobileVerification.phone_hash == phone_hash,
                SilentMobileVerification.created_at > cutoff,
            )
        )
        return list(result.scalars().all())

    async def _update_device_trust(
        self,
        user_id: str,
        device_fingerprint: str,
        carrier_verified: bool,
        confidence_boost: int,
    ) -> None:
        """Update device trust score based on carrier verification."""
        # Hash device fingerprint for storage
        fingerprint_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

        result = await self.db.execute(
            select(DeviceTrustScore).where(
                DeviceTrustScore.user_id == user_id,
                DeviceTrustScore.device_fingerprint_hash == fingerprint_hash,
            )
        )
        trust_score = result.scalar_one_or_none()

        if trust_score:
            trust_score.carrier_verified = carrier_verified
            if carrier_verified:
                # Boost verification score based on carrier confidence
                boost = min(30, confidence_boost // 3)
                trust_score.verification_score = min(100, trust_score.verification_score + boost)

                # Recalculate overall trust score
                trust_score.trust_score = int(
                    trust_score.verification_score * 0.4
                    + trust_score.behavioral_score * 0.3
                    + trust_score.history_score * 0.3
                )
        else:
            # Create new trust score with carrier verification
            trust_score = DeviceTrustScore(
                id=str(uuid4()),
                user_id=user_id,
                device_fingerprint_hash=fingerprint_hash,
                trust_score=70 if carrier_verified else 50,
                verification_score=80 if carrier_verified else 50,
                behavioral_score=50,
                history_score=50,
                carrier_verified=carrier_verified,
                successful_auths=1 if carrier_verified else 0,
            )
            self.db.add(trust_score)

    @staticmethod
    def _hash_phone(phone: str) -> str:
        """Create a hash of a phone number."""
        normalized = "".join(c for c in phone if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _hash_ip(ip: str) -> str:
        """Create a hash of an IP address."""
        return hashlib.sha256(ip.encode()).hexdigest()


def get_silent_mobile_service(db: AsyncSession) -> SilentMobileService:
    """Get a SilentMobileService instance."""
    return SilentMobileService(db)
