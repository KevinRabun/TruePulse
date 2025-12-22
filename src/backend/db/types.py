"""
SQLAlchemy Type Decorators for Encrypted Fields.

Provides transparent encryption/decryption for PII columns.
"""

from typing import Optional

from sqlalchemy import String, TypeDecorator

from core.encryption import decrypt_pii, encrypt_pii, hash_pii


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that transparently encrypts/decrypts string values.

    Usage in models:
        email: Mapped[str] = mapped_column(EncryptedString(255), unique=False)
        email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    Note: For unique constraints and indexes on encrypted fields,
    use a separate hash column (email_hash) computed from the plaintext.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 255, **kwargs):
        """Initialize with column length (should accommodate encrypted data)."""
        # Encrypted data is larger than plaintext (base64 + prefix + nonce + tag)
        # For a 255-char string, encrypted version is roughly 350-400 chars
        super().__init__(length=length * 2 + 100, **kwargs)

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        return encrypt_pii(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt value when reading from database."""
        if value is None:
            return None
        return decrypt_pii(value)


class SearchableEncryptedString(TypeDecorator):
    """
    SQLAlchemy type for encrypted strings that also computes a search hash.

    This type is for documentation purposes. In practice, use two columns:
    1. EncryptedString for the encrypted value
    2. Regular String for the hash (for lookups)

    The hash must be computed manually when setting the value.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 255, **kwargs):
        super().__init__(length=length * 2 + 100, **kwargs)

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_pii(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return decrypt_pii(value)


def compute_email_hash(email: str) -> str:
    """
    Compute searchable hash for an email address.

    Use this when creating/updating a user to set email_hash.
    """
    return hash_pii(email.lower().strip()) if email else ""


def compute_phone_hash(phone: Optional[str]) -> str:
    """
    Compute searchable hash for a phone number.

    Use this when creating/updating a user to set phone_hash.
    """
    # Normalize phone: remove all non-digits
    if not phone:
        return ""
    normalized = "".join(c for c in phone if c.isdigit())
    return hash_pii(normalized)
