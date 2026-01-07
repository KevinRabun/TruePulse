"""
Tests for Field-Level Encryption.

Tests the PII encryption functionality including:
- Encryption/decryption
- Search hashing
- Error handling
"""

import base64
import os

import pytest

# Set test environment before imports
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")


class TestFieldEncryption:
    """Tests for FieldEncryption class."""

    @pytest.fixture
    def encryption_key(self):
        """Generate a test encryption key."""
        import secrets

        return secrets.token_bytes(32)

    @pytest.fixture
    def encryption(self, encryption_key):
        """Create FieldEncryption instance with test key."""
        from core.encryption import FieldEncryption

        return FieldEncryption(encryption_key=encryption_key)

    def test_encrypt_returns_prefixed_string(self, encryption):
        """Test that encrypted data has the expected prefix."""
        plaintext = "test@example.com"
        encrypted = encryption.encrypt(plaintext)

        assert encrypted.startswith("enc:v1:")
        assert encrypted != plaintext

    def test_decrypt_returns_original(self, encryption):
        """Test that decryption returns the original plaintext."""
        plaintext = "test@example.com"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_empty_string_returns_empty(self, encryption):
        """Test that empty string is returned as-is."""
        assert encryption.encrypt("") == ""
        assert encryption.encrypt(None) is None

    def test_decrypt_empty_string_returns_empty(self, encryption):
        """Test that empty string decryption returns empty."""
        assert encryption.decrypt("") == ""
        assert encryption.decrypt(None) is None

    def test_decrypt_non_encrypted_returns_as_is(self, encryption):
        """Test that non-encrypted data is returned unchanged."""
        plaintext = "not-encrypted@example.com"
        result = encryption.decrypt(plaintext)

        assert result == plaintext

    def test_different_encryptions_produce_different_ciphertext(self, encryption):
        """Test that same plaintext produces different ciphertext (due to random nonce)."""
        plaintext = "test@example.com"

        encrypted1 = encryption.encrypt(plaintext)
        encrypted2 = encryption.encrypt(plaintext)

        # Should be different due to random nonce
        assert encrypted1 != encrypted2

        # Both should decrypt to same value
        assert encryption.decrypt(encrypted1) == plaintext
        assert encryption.decrypt(encrypted2) == plaintext

    def test_unicode_support(self, encryption):
        """Test encryption/decryption of unicode strings."""
        plaintext = "tëst@éxample.cöm"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext

    def test_long_string_support(self, encryption):
        """Test encryption/decryption of long strings."""
        plaintext = "a" * 1000  # 1000 character string
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext

    def test_is_encrypted_detection(self, encryption):
        """Test detection of encrypted vs unencrypted values."""
        plaintext = "test@example.com"
        encrypted = encryption.encrypt(plaintext)

        assert encryption.is_encrypted(encrypted) is True
        assert encryption.is_encrypted(plaintext) is False
        assert encryption.is_encrypted("") is False
        assert encryption.is_encrypted(None) is False


class TestSearchHash:
    """Tests for searchable hash functionality."""

    @pytest.fixture
    def encryption(self):
        """Create FieldEncryption instance with test key."""
        import secrets

        from core.encryption import FieldEncryption

        return FieldEncryption(encryption_key=secrets.token_bytes(32))

    def test_hash_is_deterministic(self, encryption):
        """Test that hash is deterministic for same input."""
        email = "test@example.com"

        hash1 = encryption.compute_search_hash(email)
        hash2 = encryption.compute_search_hash(email)

        assert hash1 == hash2

    def test_hash_is_case_insensitive(self, encryption):
        """Test that hash normalizes case."""
        hash1 = encryption.compute_search_hash("TEST@EXAMPLE.COM")
        hash2 = encryption.compute_search_hash("test@example.com")

        assert hash1 == hash2

    def test_hash_strips_whitespace(self, encryption):
        """Test that hash strips whitespace."""
        hash1 = encryption.compute_search_hash("  test@example.com  ")
        hash2 = encryption.compute_search_hash("test@example.com")

        assert hash1 == hash2

    def test_different_values_produce_different_hashes(self, encryption):
        """Test that different values produce different hashes."""
        hash1 = encryption.compute_search_hash("test1@example.com")
        hash2 = encryption.compute_search_hash("test2@example.com")

        assert hash1 != hash2

    def test_hash_is_hex_string(self, encryption):
        """Test that hash is a valid hex string."""
        hash_value = encryption.compute_search_hash("test@example.com")

        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_empty_value_returns_empty_hash(self, encryption):
        """Test that empty value returns empty hash."""
        assert encryption.compute_search_hash("") == ""


class TestDisabledEncryption:
    """Tests for encryption when disabled (no key)."""

    @pytest.fixture
    def disabled_encryption(self):
        """Create FieldEncryption instance without key."""
        from core.encryption import FieldEncryption

        return FieldEncryption(encryption_key=None)

    def test_encrypt_returns_plaintext_when_disabled(self, disabled_encryption):
        """Test that encryption returns plaintext when disabled."""
        plaintext = "test@example.com"
        result = disabled_encryption.encrypt(plaintext)

        assert result == plaintext

    def test_is_enabled_returns_false(self, disabled_encryption):
        """Test that is_enabled returns False when no key."""
        assert disabled_encryption.is_enabled is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_encryption_key_format(self):
        """Test that generated key is valid base64."""
        from core.encryption import generate_encryption_key

        key_str = generate_encryption_key()

        # Should be valid base64
        key_bytes = base64.b64decode(key_str)

        # Should be 32 bytes (256 bits)
        assert len(key_bytes) == 32


# Note: TestDbTypes class was removed as it tested SQLAlchemy-specific
# type decorators (compute_email_hash, compute_phone_hash) that are
# no longer needed after the migration to Cosmos DB.
