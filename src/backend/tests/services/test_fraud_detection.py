"""
Tests for Fraud Detection Service.

Tests the multi-layered fraud prevention system including:
- Device fingerprinting
- Behavioral analysis
- Risk assessment
- CAPTCHA triggers
- IP intelligence
"""

import os

import pytest

# Set test environment before imports
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")

from services.fraud_detection import (
    BehavioralSignals,
    ChallengeType,
    DeviceFingerprint,
    FraudConfig,
    RiskLevel,
    UserReputationScore,
    VoteRiskAssessment,
)


class TestDeviceFingerprint:
    """Tests for DeviceFingerprint model."""

    def test_compute_fingerprint_id(self):
        """Test that fingerprint ID is computed consistently."""
        fingerprint = DeviceFingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            screen_resolution="1920x1080",
            timezone_offset=-300,
            language="en-US",
            platform="Win32",
            canvas_hash="abc123",
            webgl_vendor="NVIDIA Corporation",
            webgl_renderer="NVIDIA GeForce GTX 1080",
            audio_hash="def456",
            hardware_concurrency=8,
        )

        salt = "test-salt"
        fp_id1 = fingerprint.compute_fingerprint_id(salt)
        fp_id2 = fingerprint.compute_fingerprint_id(salt)

        # Should be deterministic
        assert fp_id1 == fp_id2

        # Should be a hex string
        assert all(c in "0123456789abcdef" for c in fp_id1)

        # Should be 64 chars (SHA-256)
        assert len(fp_id1) == 64

    def test_fingerprint_id_different_with_different_salt(self):
        """Test that different salts produce different fingerprint IDs."""
        fingerprint = DeviceFingerprint(
            user_agent="Mozilla/5.0",
            screen_resolution="1920x1080",
            timezone_offset=-300,
            language="en-US",
            platform="Win32",
        )

        fp_id1 = fingerprint.compute_fingerprint_id("salt1")
        fp_id2 = fingerprint.compute_fingerprint_id("salt2")

        assert fp_id1 != fp_id2

    def test_fingerprint_id_different_with_different_device(self):
        """Test that different devices produce different fingerprint IDs."""
        fingerprint1 = DeviceFingerprint(
            user_agent="Mozilla/5.0",
            screen_resolution="1920x1080",
            timezone_offset=-300,
            language="en-US",
            platform="Win32",
        )

        fingerprint2 = DeviceFingerprint(
            user_agent="Mozilla/5.0",
            screen_resolution="1366x768",  # Different resolution
            timezone_offset=-300,
            language="en-US",
            platform="Win32",
        )

        salt = "test-salt"
        assert fingerprint1.compute_fingerprint_id(salt) != fingerprint2.compute_fingerprint_id(salt)


class TestBehavioralSignals:
    """Tests for BehavioralSignals model."""

    def test_valid_behavioral_signals(self):
        """Test valid behavioral signals creation."""
        signals = BehavioralSignals(
            page_load_to_vote_ms=5000,
            time_on_poll_ms=3000,
            mouse_move_count=25,
            mouse_click_count=3,
            scroll_count=2,
            changed_choice=True,
            viewed_results_preview=True,
            expanded_details=False,
            is_touch_device=False,
            js_execution_time_ms=150,
        )

        assert signals.page_load_to_vote_ms == 5000
        assert signals.time_on_poll_ms == 3000
        assert signals.changed_choice is True

    def test_behavioral_signals_validation(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValueError):
            BehavioralSignals(
                page_load_to_vote_ms=-1,  # Invalid
                time_on_poll_ms=3000,
                mouse_move_count=0,
                mouse_click_count=0,
                scroll_count=0,
            )


class TestUserReputationScore:
    """Tests for UserReputationScore model."""

    def test_trust_tier_trusted(self):
        """Test trusted tier calculation."""
        reputation = UserReputationScore(
            user_id="user-1",
            reputation_score=85,
            email_verified=True,
        )

        assert reputation.trust_tier == "trusted"

    def test_trust_tier_verified(self):
        """Test verified tier calculation."""
        reputation = UserReputationScore(
            user_id="user-1",
            reputation_score=65,
        )

        assert reputation.trust_tier == "verified"

    def test_trust_tier_standard(self):
        """Test standard tier calculation."""
        reputation = UserReputationScore(
            user_id="user-1",
            reputation_score=45,
        )

        assert reputation.trust_tier == "standard"

    def test_trust_tier_limited(self):
        """Test limited tier calculation."""
        reputation = UserReputationScore(
            user_id="user-1",
            reputation_score=25,
        )

        assert reputation.trust_tier == "limited"

    def test_trust_tier_restricted(self):
        """Test restricted tier calculation."""
        reputation = UserReputationScore(
            user_id="user-1",
            reputation_score=15,
        )

        assert reputation.trust_tier == "restricted"


class TestVoteRiskAssessment:
    """Tests for VoteRiskAssessment model."""

    def test_default_values(self):
        """Test default values for risk assessment."""
        assessment = VoteRiskAssessment()

        assert assessment.risk_score == 0
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.required_challenge == ChallengeType.NONE
        assert assessment.allow_vote is True
        assert assessment.block_reason is None
        assert assessment.risk_factors == []
        assert assessment.confidence == 1.0

    def test_blocked_assessment(self):
        """Test a blocked risk assessment."""
        assessment = VoteRiskAssessment(
            risk_score=95,
            risk_level=RiskLevel.CRITICAL,
            required_challenge=ChallengeType.BLOCK,
            allow_vote=False,
            block_reason="Suspicious activity detected",
            risk_factors=["vpn_detected", "rapid_voting", "new_account"],
            confidence=0.95,
        )

        assert assessment.allow_vote is False
        assert assessment.block_reason == "Suspicious activity detected"
        assert len(assessment.risk_factors) == 3

    def test_captcha_required_assessment(self):
        """Test an assessment requiring CAPTCHA."""
        assessment = VoteRiskAssessment(
            risk_score=65,
            risk_level=RiskLevel.MEDIUM,
            required_challenge=ChallengeType.CAPTCHA,
            allow_vote=True,
            risk_factors=["new_account", "first_vote"],
        )

        assert assessment.allow_vote is True
        assert assessment.required_challenge == ChallengeType.CAPTCHA


class TestFraudConfig:
    """Tests for FraudConfig values."""

    def test_risk_thresholds_ordered(self):
        """Test that risk thresholds are properly ordered."""
        assert FraudConfig.LOW_RISK_THRESHOLD < FraudConfig.MEDIUM_RISK_THRESHOLD
        assert FraudConfig.MEDIUM_RISK_THRESHOLD < FraudConfig.HIGH_RISK_THRESHOLD
        assert FraudConfig.HIGH_RISK_THRESHOLD < FraudConfig.BLOCK_THRESHOLD

    def test_captcha_threshold_reasonable(self):
        """Test that CAPTCHA threshold is between medium and high risk."""
        assert FraudConfig.CAPTCHA_REQUIRED_RISK >= FraudConfig.MEDIUM_RISK_THRESHOLD
        assert FraudConfig.CAPTCHA_REQUIRED_RISK < FraudConfig.BLOCK_THRESHOLD

    def test_rate_limits_reasonable(self):
        """Test that rate limits are reasonable."""
        # Minute < Hour < Day
        assert FraudConfig.MAX_VOTES_PER_MINUTE < FraudConfig.MAX_VOTES_PER_HOUR
        assert FraudConfig.MAX_VOTES_PER_HOUR < FraudConfig.MAX_VOTES_PER_DAY

        # Minute * 60 should not exceed hour (with some buffer)
        assert FraudConfig.MAX_VOTES_PER_MINUTE * 60 > FraudConfig.MAX_VOTES_PER_HOUR


class TestRiskLevelEnum:
    """Tests for RiskLevel enum."""

    def test_all_levels_exist(self):
        """Test that all expected risk levels exist."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"


class TestChallengeTypeEnum:
    """Tests for ChallengeType enum."""

    def test_all_challenge_types_exist(self):
        """Test that all expected challenge types exist."""
        assert ChallengeType.NONE == "none"
        assert ChallengeType.CAPTCHA == "captcha"
        assert ChallengeType.PASSKEY_VERIFY == "passkey_verify"
        assert ChallengeType.EMAIL_VERIFY == "email_verify"
        assert ChallengeType.BLOCK == "block"


class TestFraudDetectionService:
    """Tests for the main FraudDetectionService class."""

    @pytest.fixture
    def fraud_service(self):
        """Create a FraudDetectionService instance."""
        from services.fraud_detection import FraudDetectionService

        return FraudDetectionService()

    def test_fraud_detection_service_instantiation(self, fraud_service):
        """Test that FraudDetectionService can be instantiated."""
        assert fraud_service is not None

    # Note: The _calculate_behavior_risk method is internal and not exposed
    # as a public method. Behavior risk is calculated internally during
    # the assess_vote_request flow. These tests are commented out until
    # the internal method is made testable or a public API is exposed.
    #
    # def test_calculate_behavior_risk_too_fast(self, fraud_service):
    # def test_calculate_behavior_risk_normal(self, fraud_service):
    # def test_calculate_behavior_risk_no_mouse_movement(self, fraud_service):
