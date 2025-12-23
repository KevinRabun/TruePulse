"""
Passkey (WebAuthn/FIDO2) authentication service.

Provides phishing-resistant passwordless authentication using the WebAuthn standard.
Credentials are bound to verified phone numbers to prevent duplicate accounts.
"""

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from core.config import settings
from models.passkey import DeviceTrustScore, PasskeyChallenge, PasskeyCredential
from models.user import User

logger = logging.getLogger(__name__)


class PasskeyError(Exception):
    """Base exception for passkey operations."""

    pass


class PasskeyRegistrationError(PasskeyError):
    """Error during passkey registration."""

    pass


class PasskeyAuthenticationError(PasskeyError):
    """Error during passkey authentication."""

    pass


class ChallengeExpiredError(PasskeyError):
    """Challenge has expired."""

    pass


class PasskeyService:
    """
    WebAuthn passkey service for registration and authentication.

    Security Features:
    - Phishing resistant (origin-bound credentials)
    - Replay attack protection (challenge-response)
    - Credential binding to verified phone numbers
    - Device trust scoring integration
    """

    # Configuration
    RP_ID = settings.WEBAUTHN_RP_ID  # Relying Party ID (domain)
    RP_NAME = settings.WEBAUTHN_RP_NAME  # Relying Party name
    ORIGIN = settings.WEBAUTHN_ORIGIN  # Expected origin
    CHALLENGE_TIMEOUT = timedelta(minutes=5)  # Challenge validity period

    def __init__(self, db: AsyncSession):
        """Initialize the passkey service."""
        self.db = db

    async def generate_registration_options(
        self,
        user: User,
        device_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate WebAuthn registration options for a user.

        Args:
            user: The user registering a passkey
            device_info: Optional device information for trust scoring

        Returns:
            Registration options to be sent to the client

        Raises:
            PasskeyRegistrationError: If user is not eligible for passkey registration
        """
        # Verify user has verified email (required for credential binding)
        if not user.email_verified:
            raise PasskeyRegistrationError(
                "Email verification required before registering a passkey. This helps ensure one person = one vote."
            )

        # Get existing credentials to exclude
        existing_credentials = await self._get_user_credentials(user.id)
        exclude_credentials = [PublicKeyCredentialDescriptor(id=cred.credential_id) for cred in existing_credentials]

        # Generate registration options
        options = generate_registration_options(
            rp_id=self.RP_ID,
            rp_name=self.RP_NAME,
            user_id=user.id.encode(),
            user_name=user.email,
            user_display_name=user.display_name or user.username,
            attestation=AttestationConveyancePreference.NONE,  # Privacy-friendly
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,  # Prefer platform authenticators
                resident_key=ResidentKeyRequirement.PREFERRED,  # Discoverable credentials
                user_verification=UserVerificationRequirement.REQUIRED,  # Require biometric/PIN
            ),
            exclude_credentials=exclude_credentials,
            timeout=int(self.CHALLENGE_TIMEOUT.total_seconds() * 1000),  # Milliseconds
        )

        # Store challenge for verification
        challenge_id = str(uuid4())
        challenge_str = bytes_to_base64url(options.challenge)
        logger.warning(
            f"DEBUG Storing challenge - id: {challenge_id}, challenge: {challenge_str} "
            f"(len={len(challenge_str)}, original_bytes_len={len(options.challenge)})"
        )
        await self._store_challenge(
            challenge_id=challenge_id,
            challenge=challenge_str,
            user_id=user.id,
            operation="registration",
            device_info=device_info,
        )

        # Convert to JSON-serializable dict
        # Type ignore comments for webauthn library type issues
        auth_selection = options.authenticator_selection
        options_dict = {
            "challengeId": challenge_id,
            "rp": {"id": options.rp.id, "name": options.rp.name},
            "user": {
                "id": bytes_to_base64url(options.user.id),
                "name": options.user.name,
                "displayName": options.user.display_name,
            },
            "challenge": bytes_to_base64url(options.challenge),
            "pubKeyCredParams": [
                {"type": param.type, "alg": param.alg}  # type: ignore[attr-defined]
                for param in options.pub_key_cred_params
            ],
            "timeout": options.timeout,
            "attestation": options.attestation.value if hasattr(options.attestation, "value") else options.attestation,
            "excludeCredentials": [
                {"type": "public-key", "id": bytes_to_base64url(cred.id)} for cred in exclude_credentials
            ],
            "authenticatorSelection": {
                "authenticatorAttachment": auth_selection.authenticator_attachment.value
                if auth_selection and auth_selection.authenticator_attachment
                else None,  # type: ignore[union-attr]
                "residentKey": auth_selection.resident_key.value if auth_selection else None,  # type: ignore[union-attr]
                "userVerification": auth_selection.user_verification.value if auth_selection else None,  # type: ignore[union-attr]
            },
        }

        logger.info(f"Generated registration options for user {user.id}")
        return options_dict

    async def verify_registration(
        self,
        user: User,
        challenge_id: str,
        credential_json: str,
        credential_name: str | None = None,
    ) -> PasskeyCredential:
        """
        Verify and store a WebAuthn registration response.

        Args:
            user: The user registering the passkey
            challenge_id: The challenge ID from registration options
            credential_json: The credential JSON from the client
            credential_name: Optional friendly name for the passkey

        Returns:
            The stored PasskeyCredential

        Raises:
            PasskeyRegistrationError: If verification fails
            ChallengeExpiredError: If the challenge has expired
        """
        # Retrieve and validate challenge
        challenge_data = await self._get_challenge(challenge_id)
        if not challenge_data:
            raise ChallengeExpiredError("Registration challenge not found or expired")

        if challenge_data["user_id"] != user.id:
            raise PasskeyRegistrationError("Challenge does not belong to this user")

        if challenge_data["operation"] != "registration":
            raise PasskeyRegistrationError("Invalid challenge type")

        try:
            # Parse the credential
            credential = parse_registration_credential_json(credential_json)

            # Debug: Log challenge comparison
            stored_challenge = challenge_data["challenge"]
            stored_challenge_bytes = base64url_to_bytes(stored_challenge)

            # Extract challenge from client data to see what browser sent
            import base64
            client_data_json = base64.urlsafe_b64decode(
                credential.response.client_data_json + "=="
            )
            client_data = json.loads(client_data_json)
            client_challenge = client_data.get("challenge", "NOT_FOUND")

            logger.warning(
                f"DEBUG Challenge comparison - "
                f"stored_b64: {stored_challenge} (len={len(stored_challenge)}), "
                f"client_b64: {client_challenge} (len={len(client_challenge)}), "
                f"match: {stored_challenge == client_challenge}"
            )

            # Verify the registration
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=stored_challenge_bytes,
                expected_rp_id=self.RP_ID,
                expected_origin=self.ORIGIN,
                require_user_verification=True,
            )

            # No phone binding - passkeys are bound to email-verified user identity
            phone_hash = None

            # Determine transports
            transports = []
            if credential.response.transports:
                transports = [t.value for t in credential.response.transports]

            # Create passkey credential record
            passkey = PasskeyCredential(
                id=str(uuid4()),
                user_id=user.id,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                credential_name=credential_name or self._generate_device_name(challenge_data.get("device_info")),
                transports=json.dumps(transports) if transports else None,
                is_backup_eligible=getattr(verification, "credential_backed_up", False),
                is_backed_up=getattr(verification, "credential_backed_up", False),
                bound_phone_hash=phone_hash,
                aaguid=str(verification.aaguid) if verification.aaguid else None,
            )

            self.db.add(passkey)

            # Update device trust score if device info provided
            if challenge_data.get("device_info"):
                await self._update_device_trust(
                    user_id=user.id,
                    device_info=challenge_data["device_info"],
                    verification_type="passkey_registration",
                )

            await self.db.commit()
            await self.db.refresh(passkey)

            # Invalidate challenge
            await self._invalidate_challenge(challenge_id)

            logger.info(f"Registered passkey {passkey.id} for user {user.id}")
            return passkey

        except Exception as e:
            logger.error(f"Passkey registration failed for user {user.id}: {e}")
            raise PasskeyRegistrationError(f"Registration verification failed: {e}") from e

    async def generate_authentication_options(
        self,
        user: User | None = None,
        device_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate WebAuthn authentication options.

        Args:
            user: Optional user (if None, allows discoverable credential flow)
            device_info: Optional device information

        Returns:
            Authentication options to be sent to the client
        """
        allow_credentials = []

        if user:
            # Get user's registered credentials
            credentials = await self._get_user_credentials(user.id)
            allow_credentials = [
                PublicKeyCredentialDescriptor(
                    id=cred.credential_id,
                    transports=json.loads(cred.transports) if cred.transports else None,
                )
                for cred in credentials
            ]

        # Generate authentication options
        options = generate_authentication_options(
            rp_id=self.RP_ID,
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.REQUIRED,
            timeout=int(self.CHALLENGE_TIMEOUT.total_seconds() * 1000),
        )

        # Store challenge
        challenge_id = str(uuid4())
        await self._store_challenge(
            challenge_id=challenge_id,
            challenge=bytes_to_base64url(options.challenge),
            user_id=user.id if user else None,
            operation="authentication",
            device_info=device_info,
        )

        # Convert to JSON-serializable dict
        user_verification = options.user_verification
        options_dict = {
            "challengeId": challenge_id,
            "rpId": self.RP_ID,
            "challenge": bytes_to_base64url(options.challenge),
            "timeout": options.timeout,
            "userVerification": user_verification.value if hasattr(user_verification, "value") else user_verification,  # type: ignore[union-attr]
            "allowCredentials": [
                {
                    "type": "public-key",
                    "id": bytes_to_base64url(cred.id),
                    "transports": cred.transports if cred.transports else [],
                }
                for cred in (allow_credentials or [])
            ],
        }

        logger.info(f"Generated authentication options (user: {user.id if user else 'discoverable'})")
        return options_dict

    async def verify_authentication(
        self,
        challenge_id: str,
        credential_json: str,
    ) -> tuple[User, PasskeyCredential]:
        """
        Verify a WebAuthn authentication response.

        Args:
            challenge_id: The challenge ID from authentication options
            credential_json: The credential JSON from the client

        Returns:
            Tuple of (authenticated user, passkey credential used)

        Raises:
            PasskeyAuthenticationError: If verification fails
            ChallengeExpiredError: If the challenge has expired
        """
        # Retrieve challenge
        challenge_data = await self._get_challenge(challenge_id)
        if not challenge_data:
            raise ChallengeExpiredError("Authentication challenge not found or expired")

        if challenge_data["operation"] != "authentication":
            raise PasskeyAuthenticationError("Invalid challenge type")

        try:
            # Parse the credential
            credential = parse_authentication_credential_json(credential_json)

            # Find the passkey by credential ID
            passkey = await self._get_credential_by_id(credential.raw_id)
            if not passkey:
                raise PasskeyAuthenticationError("Unknown credential")

            # Verify authentication
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(challenge_data["challenge"]),
                expected_rp_id=self.RP_ID,
                expected_origin=self.ORIGIN,
                credential_public_key=passkey.public_key,
                credential_current_sign_count=passkey.sign_count,
                require_user_verification=True,
            )

            # Update sign count (replay attack protection)
            passkey.sign_count = verification.new_sign_count
            passkey.last_used_at = datetime.now(UTC)

            # Get user
            user = await self._get_user(passkey.user_id)
            if not user:
                raise PasskeyAuthenticationError("User not found")

            if not user.is_active:
                raise PasskeyAuthenticationError("User account is disabled")

            # Update device trust
            if challenge_data.get("device_info"):
                await self._update_device_trust(
                    user_id=user.id,
                    device_info=challenge_data["device_info"],
                    verification_type="passkey_authentication",
                )

            await self.db.commit()

            # Invalidate challenge
            await self._invalidate_challenge(challenge_id)

            logger.info(f"Authenticated user {user.id} with passkey {passkey.id}")
            return user, passkey

        except PasskeyAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Passkey authentication failed: {e}")
            raise PasskeyAuthenticationError(f"Authentication verification failed: {e}") from e

    async def delete_passkey(self, user: User, passkey_id: str) -> bool:
        """
        Delete a passkey credential.

        Args:
            user: The user who owns the passkey
            passkey_id: The passkey ID to delete

        Returns:
            True if deleted, False if not found
        """
        passkey = await self._get_passkey_by_id(passkey_id)
        if not passkey or passkey.user_id != user.id:
            return False

        # Ensure user has at least one other passkey or password
        credentials = await self._get_user_credentials(user.id)
        if len(credentials) <= 1 and user.passkey_only:
            raise PasskeyError("Cannot delete last passkey for passkey-only account")

        await self.db.delete(passkey)
        await self.db.commit()

        logger.info(f"Deleted passkey {passkey_id} for user {user.id}")
        return True

    async def get_user_passkeys(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get all passkeys for a user (for management UI).

        Args:
            user_id: The user ID

        Returns:
            List of passkey info dicts
        """
        credentials = await self._get_user_credentials(user_id)
        return [
            {
                "id": cred.id,
                "deviceName": cred.credential_name,
                "createdAt": cred.created_at.isoformat(),
                "lastUsedAt": cred.last_used_at.isoformat() if cred.last_used_at else None,
                "backupEligible": cred.is_backup_eligible,
                "backupState": cred.is_backed_up,
            }
            for cred in credentials
        ]

    # --- Helper methods ---

    async def _store_challenge(
        self,
        challenge_id: str,
        challenge: str,
        user_id: str | None,
        operation: str,
        device_info: dict[str, Any] | None = None,
    ) -> None:
        """Store a challenge in the database for later verification.

        Uses database storage to support multi-worker deployments where
        each worker has its own memory space.
        """
        challenge_record = PasskeyChallenge(
            id=challenge_id,
            challenge=challenge,
            user_id=user_id,
            operation=operation,
            device_info=json.dumps(device_info) if device_info else None,
            expires_at=datetime.now(UTC) + self.CHALLENGE_TIMEOUT,
        )
        self.db.add(challenge_record)
        await self.db.flush()

    async def _get_challenge(self, challenge_id: str) -> dict[str, Any] | None:
        """Retrieve and validate a challenge from the database."""
        result = await self.db.execute(select(PasskeyChallenge).where(PasskeyChallenge.id == challenge_id))
        challenge_record = result.scalar_one_or_none()

        if not challenge_record:
            return None

        if datetime.now(UTC) > challenge_record.expires_at:
            await self.db.delete(challenge_record)
            await self.db.flush()
            return None

        return {
            "challenge": challenge_record.challenge,
            "user_id": challenge_record.user_id,
            "operation": challenge_record.operation,
            "device_info": json.loads(challenge_record.device_info) if challenge_record.device_info else None,
            "expires_at": challenge_record.expires_at,
        }

    async def _invalidate_challenge(self, challenge_id: str) -> None:
        """Remove a challenge after use."""
        result = await self.db.execute(select(PasskeyChallenge).where(PasskeyChallenge.id == challenge_id))
        challenge_record = result.scalar_one_or_none()
        if challenge_record:
            await self.db.delete(challenge_record)
            await self.db.flush()

    async def _get_user_credentials(self, user_id: str) -> list[PasskeyCredential]:
        """Get all passkey credentials for a user."""
        result = await self.db.execute(select(PasskeyCredential).where(PasskeyCredential.user_id == user_id))
        return list(result.scalars().all())

    async def _get_credential_by_id(self, credential_id: bytes) -> PasskeyCredential | None:
        """Get a passkey by its WebAuthn credential ID."""
        result = await self.db.execute(
            select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        )
        return result.scalar_one_or_none()

    async def _get_passkey_by_id(self, passkey_id: str) -> PasskeyCredential | None:
        """Get a passkey by its internal ID."""
        result = await self.db.execute(select(PasskeyCredential).where(PasskeyCredential.id == passkey_id))
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    def _hash_phone(phone: str) -> str:
        """Create a hash of a phone number for binding verification."""
        # Normalize phone number
        normalized = "".join(c for c in phone if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _generate_device_name(device_info: dict[str, Any] | None) -> str:
        """Generate a friendly device name from device info."""
        if not device_info:
            return f"Passkey {secrets.token_hex(4)}"

        # Try to create a meaningful name
        parts = []
        if device_info.get("platform"):
            parts.append(device_info["platform"])
        if device_info.get("browser"):
            parts.append(device_info["browser"])

        if parts:
            return " ".join(parts)
        return f"Passkey {secrets.token_hex(4)}"

    async def _update_device_trust(
        self,
        user_id: str,
        device_info: dict[str, Any],
        verification_type: str,
    ) -> None:
        """Update device trust score after successful verification."""
        device_fingerprint = device_info.get("fingerprint", "")
        if not device_fingerprint:
            return

        # Hash the fingerprint for storage
        import hashlib

        fingerprint_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()

        # Check for existing trust score
        result = await self.db.execute(
            select(DeviceTrustScore).where(
                DeviceTrustScore.user_id == user_id,
                DeviceTrustScore.device_fingerprint_hash == fingerprint_hash,
            )
        )
        trust_score = result.scalar_one_or_none()

        if trust_score:
            # Update existing trust score
            trust_score.successful_auths += 1
            trust_score.last_seen_at = datetime.now(UTC)

            # Increase verification score based on type
            if verification_type == "passkey_registration":
                trust_score.verification_score = min(100, trust_score.verification_score + 20)
            elif verification_type == "passkey_authentication":
                trust_score.verification_score = min(100, trust_score.verification_score + 5)

            # Recalculate overall trust score
            trust_score.trust_score = int(
                trust_score.verification_score * 0.4
                + trust_score.behavioral_score * 0.3
                + trust_score.history_score * 0.3
            )
        else:
            # Create new trust score
            trust_score = DeviceTrustScore(
                id=str(uuid4()),
                user_id=user_id,
                device_fingerprint_hash=fingerprint_hash,
                trust_score=50,  # Initial score
                verification_score=60 if verification_type == "passkey_registration" else 40,
                behavioral_score=50,
                history_score=50,
                successful_auths=1,
            )
            self.db.add(trust_score)

        # No commit here - let the caller commit


# Singleton-style factory for service instances
def get_passkey_service(db: AsyncSession) -> PasskeyService:
    """Get a PasskeyService instance."""
    return PasskeyService(db)
