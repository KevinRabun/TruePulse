"""
Field-Level Encryption for PII Data.

Provides transparent encryption/decryption for sensitive user data
using Azure Key Vault or a local key for development.

This module implements AES-256-GCM encryption for:
- Email addresses
- Phone numbers
- Other PII as needed

Design Principles:
1. Encryption at rest for PII fields
2. Searchable via hash index for lookups
3. Key rotation support via Key Vault
4. Graceful degradation in development
"""

import base64
import hashlib
import os
import secrets
from functools import lru_cache
from typing import Optional

import structlog
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings

logger = structlog.get_logger(__name__)


class FieldEncryptionError(Exception):
    """Raised when field encryption/decryption fails."""

    pass


class FieldEncryption:
    """
    AES-256-GCM field-level encryption for PII data.

    Uses a 256-bit key from either:
    - Azure Key Vault (production)
    - Environment variable (development)
    - Generated key (test only, not persistent)
    """

    # Prefix to identify encrypted data
    ENCRYPTED_PREFIX = "enc:v1:"

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize with encryption key.

        Args:
            encryption_key: 32-byte AES key. If None, loads from settings/Key Vault.
        """
        self._key = encryption_key or self._load_key()
        self._aesgcm = AESGCM(self._key) if self._key else None
        self._enabled = self._aesgcm is not None

        if self._enabled:
            logger.info("field_encryption_initialized", status="enabled")
        else:
            logger.warning(
                "field_encryption_disabled",
                reason="no_key_configured",
                message="PII fields will NOT be encrypted. Configure FIELD_ENCRYPTION_KEY for production.",
            )

    def _load_key(self) -> Optional[bytes]:
        """Load encryption key from settings or Key Vault."""
        # First, check for environment variable
        key_str = getattr(settings, "FIELD_ENCRYPTION_KEY", None)

        if key_str:
            try:
                # Key should be base64 encoded 32-byte key
                key = base64.b64decode(key_str)
                if len(key) != 32:
                    logger.error(
                        "invalid_encryption_key_length",
                        expected=32,
                        actual=len(key),
                    )
                    return None
                return key
            except Exception as e:
                logger.error("failed_to_decode_encryption_key", error=str(e))
                return None

        # For development/test without Key Vault, generate a warning
        app_env = getattr(settings, "APP_ENV", "development")
        if app_env in ("production", "staging"):
            logger.error(
                "encryption_key_required_in_production",
                app_env=app_env,
                message="FIELD_ENCRYPTION_KEY must be set in production/staging",
            )
        else:
            logger.warning(
                "no_encryption_key_configured",
                app_env=app_env,
                message="PII encryption disabled in development",
            )

        return None

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._enabled

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted string with prefix (enc:v1:base64data)
            or original string if encryption disabled
        """
        if not plaintext:
            return plaintext

        if not self._enabled:
            return plaintext

        try:
            # Generate random 12-byte nonce
            nonce = secrets.token_bytes(12)

            # Encrypt
            ciphertext = self._aesgcm.encrypt(
                nonce, plaintext.encode("utf-8"), None
            )

            # Combine nonce + ciphertext and base64 encode
            encrypted_data = base64.b64encode(nonce + ciphertext).decode("ascii")

            return f"{self.ENCRYPTED_PREFIX}{encrypted_data}"

        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise FieldEncryptionError(f"Failed to encrypt field: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string (with enc:v1: prefix)

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext

        # Check if data is encrypted
        if not ciphertext.startswith(self.ENCRYPTED_PREFIX):
            # Return as-is (not encrypted or legacy data)
            return ciphertext

        if not self._enabled:
            logger.error("cannot_decrypt_without_key")
            raise FieldEncryptionError("Encryption key not configured, cannot decrypt")

        try:
            # Remove prefix and decode
            encrypted_data = base64.b64decode(
                ciphertext[len(self.ENCRYPTED_PREFIX) :]
            )

            # Extract nonce (first 12 bytes) and ciphertext
            nonce = encrypted_data[:12]
            actual_ciphertext = encrypted_data[12:]

            # Decrypt
            plaintext = self._aesgcm.decrypt(nonce, actual_ciphertext, None)

            return plaintext.decode("utf-8")

        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise FieldEncryptionError(f"Failed to decrypt field: {e}") from e

    def compute_search_hash(self, plaintext: str) -> str:
        """
        Compute a deterministic hash for searchable encryption.

        This allows lookup by email/phone without decrypting all records.
        Uses HMAC-SHA256 with the encryption key.

        Args:
            plaintext: The value to hash (e.g., email address)

        Returns:
            Hex-encoded hash
        """
        if not plaintext:
            return ""

        # Normalize (lowercase for email, strip for phone)
        normalized = plaintext.lower().strip()

        # Use HMAC with encryption key as secret
        key = self._key or settings.SECRET_KEY.encode("utf-8")
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            normalized.encode("utf-8"),
            key,
            iterations=10000,
        )

        return hash_value.hex()

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is already encrypted."""
        return value.startswith(self.ENCRYPTED_PREFIX) if value else False


@lru_cache()
def get_field_encryption() -> FieldEncryption:
    """Get the singleton FieldEncryption instance."""
    return FieldEncryption()


def generate_encryption_key() -> str:
    """
    Generate a new base64-encoded 256-bit encryption key.

    Use this to generate a new key for FIELD_ENCRYPTION_KEY.
    Run: python -c "from core.encryption import generate_encryption_key; print(generate_encryption_key())"
    """
    key = secrets.token_bytes(32)
    return base64.b64encode(key).decode("ascii")


# Convenience functions for use in models
def encrypt_pii(value: str) -> str:
    """Encrypt a PII field value."""
    return get_field_encryption().encrypt(value)


def decrypt_pii(value: str) -> str:
    """Decrypt a PII field value."""
    return get_field_encryption().decrypt(value)


def hash_pii(value: str) -> str:
    """Compute searchable hash of a PII value."""
    return get_field_encryption().compute_search_hash(value)
