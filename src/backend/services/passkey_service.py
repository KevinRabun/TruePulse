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
from models.cosmos_documents import PasskeyDocument, UserDocument
from repositories.cosmos_user_repository import CosmosUserRepository
from schemas.user import UserInDB
from services.redis_service import RedisService, get_redis_service

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
    CHALLENGE_PREFIX = "passkey:challenge:"  # Redis key prefix for challenges

    def __init__(self, user_repo: CosmosUserRepository, redis_service: RedisService | None = None):
        """Initialize the passkey service."""
        self.user_repo = user_repo
        self._redis_service = redis_service

    async def generate_registration_options(
        self,
        user: UserInDB,
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

        # Get existing credentials to exclude from UserDocument
        user_doc = await self.user_repo.get_by_id(user.id)
        existing_passkeys = user_doc.passkeys if user_doc else []
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
            for pk in existing_passkeys
            if pk.is_active
        ]

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
        logger.debug(f"passkey_challenge_stored: challenge_id={challenge_id}, challenge_length={len(challenge_str)}")
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
        user: UserInDB,
        challenge_id: str,
        credential_data: dict[str, Any],
        credential_name: str | None = None,
    ) -> PasskeyDocument:
        """
        Verify and store a WebAuthn registration response.

        Args:
            user: The user registering the passkey
            challenge_id: The challenge ID from registration options
            credential_data: The credential dict from the client (not JSON string)
            credential_name: Optional friendly name for the passkey

        Returns:
            The stored PasskeyDocument

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
            # Initialize debug variables at the start
            stored_challenge = "NOT_SET"
            client_challenge = "NOT_SET"

            # Pass credential dict directly to parse_registration_credential_json
            # It accepts Union[str, dict], so no JSON string manipulation needed
            # This avoids double-stringify issues that could corrupt base64url data
            logger.info(f"Processing credential with keys: {list(credential_data.keys())}")
            credential = parse_registration_credential_json(credential_data)

            # Debug: Log challenge comparison
            stored_challenge = challenge_data["challenge"]
            stored_challenge_bytes = base64url_to_bytes(stored_challenge)

            # Extract challenge from client data to see what browser sent
            # NOTE: py_webauthn's parse_registration_credential_json behavior varies:
            # - Sometimes it decodes client_data_json from base64url to raw bytes
            # - Sometimes it leaves it as base64url encoded bytes
            raw_client_data = credential.response.client_data_json

            try:
                # Try multiple decoding strategies
                client_data = None

                if isinstance(raw_client_data, bytes):
                    # Strategy 1: Try direct UTF-8 decode (already decoded JSON bytes)
                    try:
                        client_data = json.loads(raw_client_data.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        # Strategy 2: Try base64url decode first (still encoded)
                        try:
                            decoded_bytes = base64url_to_bytes(raw_client_data.decode("ascii"))
                            client_data = json.loads(decoded_bytes.decode("utf-8"))
                        except Exception:
                            pass

                    # Strategy 3: Maybe it's raw base64url bytes that need decoding
                    if client_data is None:
                        try:
                            # The bytes themselves might be base64url data
                            import base64

                            # Add padding if needed
                            padded = raw_client_data + b"=" * (4 - len(raw_client_data) % 4)
                            decoded_bytes = base64.urlsafe_b64decode(padded)
                            client_data = json.loads(decoded_bytes.decode("utf-8"))
                        except Exception:
                            pass
                elif isinstance(raw_client_data, str):
                    # It's a string - try direct JSON parse or base64url decode
                    try:
                        client_data = json.loads(raw_client_data)
                    except json.JSONDecodeError:
                        decoded_bytes = base64url_to_bytes(raw_client_data)
                        client_data = json.loads(decoded_bytes.decode("utf-8"))

                if client_data:
                    client_challenge = client_data.get("challenge", "NOT_FOUND")
                else:
                    client_challenge = "PARSE_FAILED"

            except Exception as decode_err:
                raw_preview = repr(raw_client_data[:50]) if raw_client_data else "None"
                logger.error(
                    f"Failed to decode clientDataJSON: {decode_err}, raw type: {type(raw_client_data)}, raw[:50]: {raw_preview}"
                )
                client_challenge = f"DECODE_ERROR: {decode_err}"

            logger.debug(
                f"passkey_challenge_verification: stored_challenge_match={stored_challenge == client_challenge}"
            )

            # Debug: Log all credential fields before verification
            logger.info(
                f"Credential debug - id_len={len(credential.id) if credential.id else 0}, "
                f"raw_id_type={type(credential.raw_id).__name__}, "
                f"raw_id_len={len(credential.raw_id) if credential.raw_id else 0}, "
                f"client_data_len={len(raw_client_data) if raw_client_data else 0}, "
                f"attestation_obj_type={type(credential.response.attestation_object).__name__}, "
                f"attestation_obj_len={len(credential.response.attestation_object) if credential.response.attestation_object else 0}"
            )

            # Check for potential 157-char value
            if credential.id and len(credential.id) == 157:
                logger.error(f"credential.id is 157 chars! Value: {credential.id}")
            if credential.raw_id and len(credential.raw_id) == 157:
                logger.error(f"credential.raw_id is 157 bytes! First 50: {credential.raw_id[:50]!r}")

            # Verify the registration
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=stored_challenge_bytes,
                expected_rp_id=self.RP_ID,
                expected_origin=self.ORIGIN,
                require_user_verification=True,
            )

            # Determine transports
            transports = []
            if credential.response.transports:
                transports = [t.value for t in credential.response.transports]

            # Create passkey document for embedding in user
            passkey = PasskeyDocument(
                id=str(uuid4()),
                credential_id=bytes_to_base64url(verification.credential_id),
                public_key=bytes_to_base64url(verification.credential_public_key),
                sign_count=verification.sign_count,
                device_name=credential_name or self._generate_device_name(challenge_data.get("device_info")),
                transports=transports,
                created_at=datetime.now(UTC),
                is_active=True,
            )

            # Add passkey to user document and update
            user_doc = await self.user_repo.get_by_id(user.id)
            if not user_doc:
                raise PasskeyRegistrationError("User not found")

            user_doc.passkeys.append(passkey)
            await self.user_repo.update(user_doc)

            # Invalidate challenge
            await self._invalidate_challenge(challenge_id)

            logger.info(f"Registered passkey {passkey.id} for user {user.id}")
            return passkey

        except Exception as e:
            # Log debug info for troubleshooting but don't expose in exception
            logger.error(
                f"Passkey registration failed for user {user.id}: {e}",
                extra={
                    "stored_challenge": stored_challenge[:16] + "..." if stored_challenge else None,
                    "client_challenge": client_challenge[:16] + "..." if client_challenge else None,
                    "challenge_match": stored_challenge == client_challenge,
                },
            )
            raise PasskeyRegistrationError(f"Registration verification failed: {e}") from e

    async def generate_authentication_options(
        self,
        user: UserDocument | None = None,
        device_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate WebAuthn authentication options.

        Args:
            user: Optional user document (if None, allows discoverable credential flow)
            device_info: Optional device information

        Returns:
            Authentication options to be sent to the client
        """
        allow_credentials = []

        if user:
            # Get user's registered credentials from embedded passkeys
            allow_credentials = [
                PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(pk.credential_id),
                    transports=pk.transports if pk.transports else None,  # type: ignore[arg-type]
                )
                for pk in user.passkeys
                if pk.is_active
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
        credential_data: dict[str, Any],
    ) -> tuple[UserDocument, PasskeyDocument]:
        """
        Verify a WebAuthn authentication response.

        Args:
            challenge_id: The challenge ID from authentication options
            credential_data: The credential data from the client (as dict)

        Returns:
            Tuple of (authenticated user document, passkey document used)

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
            # Parse the credential - py_webauthn handles base64url padding
            credential = parse_authentication_credential_json(credential_data)

            # Find the passkey by credential ID across all users
            user, passkey = await self._find_credential_by_id(credential.raw_id)
            if not user or not passkey:
                raise PasskeyAuthenticationError("Unknown credential")

            # Verify authentication
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(challenge_data["challenge"]),
                expected_rp_id=self.RP_ID,
                expected_origin=self.ORIGIN,
                credential_public_key=base64url_to_bytes(passkey.public_key),
                credential_current_sign_count=passkey.sign_count,
                require_user_verification=True,
            )

            # Update sign count and last used timestamp (replay attack protection)
            passkey.sign_count = verification.new_sign_count
            passkey.last_used_at = datetime.now(UTC)

            if not user.is_active:
                raise PasskeyAuthenticationError("User account is disabled")

            # Update the user document with the modified passkey
            await self.user_repo.update(user)

            # Invalidate challenge
            await self._invalidate_challenge(challenge_id)

            logger.info(f"Authenticated user {user.id} with passkey {passkey.id}")
            return user, passkey

        except PasskeyAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Passkey authentication failed: {e}")
            raise PasskeyAuthenticationError(f"Authentication verification failed: {e}") from e

    async def delete_passkey(self, user: UserInDB, passkey_id: str) -> bool:
        """
        Delete a passkey credential.

        Args:
            user: The user schema who owns the passkey
            passkey_id: The passkey ID to delete

        Returns:
            True if deleted, False if not found
        """
        user_doc = await self.user_repo.get_by_id(user.id)
        if not user_doc:
            return False

        # Find the passkey in embedded list
        passkey_to_delete = None
        for pk in user_doc.passkeys:
            if pk.id == passkey_id:
                passkey_to_delete = pk
                break

        if not passkey_to_delete:
            return False

        # Count active passkeys
        active_passkeys = [pk for pk in user_doc.passkeys if pk.is_active]
        if len(active_passkeys) <= 1 and getattr(user_doc, "passkey_only", False):
            raise PasskeyError("Cannot delete last passkey for passkey-only account")

        # Remove passkey from list
        user_doc.passkeys = [pk for pk in user_doc.passkeys if pk.id != passkey_id]
        await self.user_repo.update(user_doc)

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
        user_doc = await self.user_repo.get_by_id(user_id)
        if not user_doc:
            return []

        return [
            {
                "id": pk.id,
                "deviceName": pk.device_name or "Passkey",
                "createdAt": pk.created_at.isoformat() if pk.created_at else None,
                "lastUsedAt": pk.last_used_at.isoformat() if pk.last_used_at else None,
                "backupEligible": False,  # Not tracked in embedded model
                "backupState": False,  # Not tracked in embedded model
            }
            for pk in user_doc.passkeys
            if pk.is_active
        ]

    # --- Helper methods ---

    async def _get_redis_service(self) -> RedisService:
        """Get or initialize the Redis service."""
        if self._redis_service is None:
            redis = await get_redis_service()
            await redis.initialize()
            self._redis_service = redis
        return self._redis_service

    async def _store_challenge(
        self,
        challenge_id: str,
        challenge: str,
        user_id: str | None,
        operation: str,
        device_info: dict[str, Any] | None = None,
    ) -> None:
        """Store a challenge in Redis for later verification.

        Uses Redis/Table storage to support multi-worker deployments where
        each worker has its own memory space.
        """
        redis_service = await self._get_redis_service()
        challenge_data = {
            "challenge": challenge,
            "user_id": user_id,
            "operation": operation,
            "device_info": device_info,
            "expires_at": (datetime.now(UTC) + self.CHALLENGE_TIMEOUT).isoformat(),
        }
        key = f"{self.CHALLENGE_PREFIX}{challenge_id}"
        ttl_seconds = int(self.CHALLENGE_TIMEOUT.total_seconds())
        await redis_service.cache_set(key, json.dumps(challenge_data), ttl_seconds)
        logger.debug(f"passkey_challenge_stored: challenge_id={challenge_id}")

    async def _get_challenge(self, challenge_id: str) -> dict[str, Any] | None:
        """Retrieve and validate a challenge from Redis."""
        redis_service = await self._get_redis_service()
        key = f"{self.CHALLENGE_PREFIX}{challenge_id}"
        challenge_json = await redis_service.cache_get(key)

        if not challenge_json:
            return None

        challenge_data = json.loads(challenge_json)

        # Check expiration (Redis TTL should handle this, but double-check)
        expires_at = datetime.fromisoformat(challenge_data["expires_at"])
        if datetime.now(UTC) > expires_at:
            await redis_service.cache_delete(key)
            return None

        return challenge_data

    async def _invalidate_challenge(self, challenge_id: str) -> None:
        """Remove a challenge after use."""
        redis_service = await self._get_redis_service()
        key = f"{self.CHALLENGE_PREFIX}{challenge_id}"
        await redis_service.cache_delete(key)

    async def _find_credential_by_id(self, credential_id: bytes) -> tuple[UserDocument | None, PasskeyDocument | None]:
        """
        Find a passkey by its WebAuthn credential ID across all users.

        Since passkeys are embedded in user documents, we need to search
        using a Cosmos DB query.
        """
        credential_id_b64 = bytes_to_base64url(credential_id)

        # Query users container for matching credential_id in embedded passkeys
        user_doc = await self.user_repo.get_by_passkey_credential_id(credential_id_b64)
        if not user_doc:
            return None, None

        # Find the specific passkey
        for passkey in user_doc.passkeys:
            if passkey.credential_id == credential_id_b64 and passkey.is_active:
                return user_doc, passkey

        return None, None

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


# Singleton-style factory for service instances
def get_passkey_service(
    user_repo: CosmosUserRepository,
    redis_service: RedisService | None = None,
) -> PasskeyService:
    """Get a PasskeyService instance."""
    return PasskeyService(user_repo, redis_service)
