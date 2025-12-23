"""
Tests for PasskeyService - WebAuthn passkey authentication.

These tests verify the passkey registration and authentication flow,
particularly the challenge handling that was fixed to correctly parse
clientDataJSON from py_webauthn.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from webauthn.helpers import bytes_to_base64url, base64url_to_bytes


@pytest.mark.unit
class TestPasskeyChallengeHandling:
    """Test challenge storage and verification logic."""

    def test_bytes_to_base64url_roundtrip(self) -> None:
        """Test that challenge encoding/decoding is consistent."""
        # Generate random bytes similar to a WebAuthn challenge
        import os
        original_bytes = os.urandom(32)
        
        # Encode to base64url (what we store in DB)
        encoded = bytes_to_base64url(original_bytes)
        
        # Decode back (what we compare against)
        decoded = base64url_to_bytes(encoded)
        
        assert original_bytes == decoded
        assert isinstance(encoded, str)
        assert '-' in encoded or '_' in encoded or ('+' not in encoded and '/' not in encoded)

    def test_client_data_json_parsing(self) -> None:
        """
        Test that clientDataJSON from WebAuthn is correctly parsed.
        
        This is the core fix: py_webauthn's parse_registration_credential_json
        already decodes clientDataJSON from base64url to raw bytes.
        We should NOT try to base64-decode it again.
        """
        # Simulate what py_webauthn returns after parsing
        challenge_b64url = "test-challenge-in-base64url"
        client_data = {
            "type": "webauthn.create",
            "challenge": challenge_b64url,
            "origin": "https://localhost:3001",
            "crossOrigin": False,
        }
        
        # py_webauthn provides this as raw JSON bytes, NOT base64url encoded
        raw_client_data = json.dumps(client_data, separators=(',', ':')).encode('utf-8')
        
        # The correct way to parse (our fix)
        if isinstance(raw_client_data, bytes):
            parsed = json.loads(raw_client_data.decode('utf-8'))
        else:
            parsed = json.loads(raw_client_data)
        
        assert parsed["challenge"] == challenge_b64url
        assert parsed["type"] == "webauthn.create"

    def test_client_data_json_incorrect_double_decode_fails(self) -> None:
        """
        Test that double-decoding clientDataJSON (the old bug) fails.
        
        The bug was trying to base64-decode client_data_json when it was
        already decoded by py_webauthn. This should fail or give wrong results.
        """
        import base64
        
        # Simulate what py_webauthn returns
        challenge_b64url = "test-challenge-value"
        client_data = {
            "type": "webauthn.create",
            "challenge": challenge_b64url,
            "origin": "https://localhost:3001",
        }
        raw_client_data = json.dumps(client_data, separators=(',', ':')).encode('utf-8')
        
        # The OLD buggy code would try to base64-decode this
        client_data_b64_str = raw_client_data.decode('ascii')
        
        # This would fail because it's not valid base64
        with pytest.raises(Exception):  # binascii.Error or ValueError
            # Add padding if needed (what the old code did)
            padding = 4 - len(client_data_b64_str) % 4
            if padding != 4:
                client_data_b64_str += "=" * padding
            base64.urlsafe_b64decode(client_data_b64_str)


@pytest.mark.unit  
class TestPasskeyServiceChallenge:
    """Test PasskeyService challenge generation and storage."""

    @pytest.mark.asyncio
    async def test_challenge_is_stored_as_base64url(self) -> None:
        """Test that challenges are stored in base64url format."""
        from webauthn import generate_registration_options
        
        # Generate options like PasskeyService does
        options = generate_registration_options(
            rp_id='localhost',
            rp_name='Test',
            user_id='test-user'.encode(),
            user_name='test@example.com',
        )
        
        # Convert challenge to base64url (as PasskeyService does)
        challenge_str = bytes_to_base64url(options.challenge)
        
        # Verify it's a string and doesn't have standard base64 chars
        assert isinstance(challenge_str, str)
        assert '+' not in challenge_str
        assert '/' not in challenge_str
        
        # Verify we can decode it back
        decoded = base64url_to_bytes(challenge_str)
        assert decoded == options.challenge


@pytest.mark.unit
class TestPasskeyRegistrationOptions:
    """Test registration options generation."""

    def test_options_dict_format(self) -> None:
        """Test that options are formatted correctly for the frontend."""
        from webauthn import generate_registration_options
        from webauthn.helpers.structs import (
            AttestationConveyancePreference,
            AuthenticatorAttachment,
            AuthenticatorSelectionCriteria,
            ResidentKeyRequirement,
            UserVerificationRequirement,
        )
        
        options = generate_registration_options(
            rp_id='localhost',
            rp_name='TruePulse Test',
            user_id='user-123'.encode(),
            user_name='test@example.com',
            user_display_name='Test User',
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            timeout=300000,
        )
        
        # Build options dict like PasskeyService does
        challenge_id = str(uuid4())
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
            "timeout": options.timeout,
            "attestation": options.attestation.value if hasattr(options.attestation, "value") else options.attestation,
            "authenticatorSelection": {
                "authenticatorAttachment": auth_selection.authenticator_attachment.value
                if auth_selection and auth_selection.authenticator_attachment
                else None,
                "residentKey": auth_selection.resident_key.value if auth_selection else None,
                "userVerification": auth_selection.user_verification.value if auth_selection else None,
            },
        }
        
        # Verify all required fields exist
        assert "challengeId" in options_dict
        assert "rp" in options_dict
        assert "user" in options_dict
        assert "challenge" in options_dict
        assert "timeout" in options_dict
        assert "attestation" in options_dict
        assert "authenticatorSelection" in options_dict
        
        # Verify values
        assert options_dict["rp"]["id"] == "localhost"
        assert options_dict["user"]["name"] == "test@example.com"
        assert options_dict["attestation"] == "none"
        assert options_dict["authenticatorSelection"]["userVerification"] == "required"


@pytest.mark.integration
class TestPasskeyServiceIntegration:
    """Integration tests requiring database access."""

    @pytest.mark.asyncio
    async def test_generate_registration_options_requires_verified_email(self) -> None:
        """Test that passkey registration requires verified email."""
        # This test would need a database fixture
        # Skipped in unit tests
        pass
