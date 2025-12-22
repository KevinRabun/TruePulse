"""
Fraud Detection and Bot Prevention Service for TruePulse.

Multi-layered approach to ensure vote integrity:
1. Device Fingerprinting - Detect same device voting multiple times
2. Behavioral Analysis - Detect bot-like voting patterns
3. IP Intelligence - Detect VPNs, proxies, data centers, Tor
4. Rate Limiting - Prevent rapid-fire voting
5. Challenge System - CAPTCHA for suspicious activity
6. Reputation Scoring - Track user trustworthiness over time

This service is critical for maintaining public trust in poll results.
"""

import hashlib
import hmac
import ipaddress
import math
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx
import structlog
from pydantic import BaseModel, Field

from core.config import settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class FraudConfig:
    """Fraud detection configuration."""

    # Device fingerprint settings
    FINGERPRINT_SALT = getattr(settings, "FINGERPRINT_SALT", settings.SECRET_KEY)

    # Verification Requirements - CRITICAL for bot farm resistance
    # These can be configured via environment variables
    REQUIRE_EMAIL_VERIFIED = getattr(settings, "FRAUD_REQUIRE_EMAIL_VERIFIED", True)
    REQUIRE_PHONE_VERIFIED = getattr(settings, "FRAUD_REQUIRE_PHONE_VERIFIED", True)
    REQUIRE_BOTH_VERIFIED = getattr(settings, "FRAUD_REQUIRE_BOTH_VERIFIED", True)

    # IP Intelligence
    BLOCK_VPN = True
    BLOCK_PROXY = True
    BLOCK_TOR = True
    BLOCK_DATACENTER = True
    ALLOW_RESIDENTIAL_VPN = False  # Some users have legitimate reasons

    # Behavioral thresholds
    MIN_TIME_ON_POLL_SECONDS = 2.0  # Humans need time to read
    MAX_VOTES_PER_MINUTE = 5  # Reasonable human rate
    MAX_VOTES_PER_HOUR = 30
    MAX_VOTES_PER_DAY = 100

    # Suspicious patterns
    SUSPICIOUS_VOTE_SPEED_MS = 500  # Voting faster than 500ms is suspicious
    SUSPICIOUS_CHOICE_PATTERN_THRESHOLD = 0.95  # Always picking same position

    # Risk score thresholds (0-100)
    LOW_RISK_THRESHOLD = 20
    MEDIUM_RISK_THRESHOLD = 50
    HIGH_RISK_THRESHOLD = 75
    BLOCK_THRESHOLD = 90

    # CAPTCHA triggers
    CAPTCHA_REQUIRED_RISK = 60
    CAPTCHA_COOLDOWN_MINUTES = 30  # How long a passed CAPTCHA is valid


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChallengeType(str, Enum):
    """Types of challenges to verify humanity."""

    NONE = "none"
    CAPTCHA = "captcha"
    EMAIL_VERIFY = "email_verify"
    PASSKEY_VERIFY = "passkey_verify"  # Replaces SMS verification
    BLOCK = "block"


# =============================================================================
# Schemas
# =============================================================================


class DeviceFingerprint(BaseModel):
    """Device fingerprint data collected from client."""

    # Browser/JS fingerprint
    user_agent: str
    screen_resolution: str  # "1920x1080"
    timezone_offset: int  # Minutes from UTC
    language: str
    platform: str  # "Win32", "MacIntel", etc.

    # Canvas fingerprint hash (computed client-side)
    canvas_hash: Optional[str] = None

    # WebGL fingerprint
    webgl_vendor: Optional[str] = None
    webgl_renderer: Optional[str] = None

    # Audio fingerprint hash
    audio_hash: Optional[str] = None

    # Hardware
    hardware_concurrency: Optional[int] = None
    device_memory: Optional[float] = None  # GB

    # Touch support
    touch_support: bool = False
    max_touch_points: int = 0

    # Additional signals
    plugins_hash: Optional[str] = None
    fonts_hash: Optional[str] = None

    def compute_fingerprint_id(self, salt: str) -> str:
        """Compute a stable fingerprint ID from device attributes."""
        # Combine stable attributes (avoid frequently changing ones)
        stable_data = "|".join(
            [
                self.user_agent,
                self.screen_resolution,
                str(self.timezone_offset),
                self.platform,
                self.canvas_hash or "",
                self.webgl_vendor or "",
                self.webgl_renderer or "",
                self.audio_hash or "",
                str(self.hardware_concurrency or 0),
            ]
        )

        # HMAC with salt to prevent fingerprint forgery
        return hmac.new(salt.encode(), stable_data.encode(), hashlib.sha256).hexdigest()


class BehavioralSignals(BaseModel):
    """Behavioral signals from vote interaction."""

    # Time measurements (milliseconds)
    page_load_to_vote_ms: int = Field(..., ge=0)
    time_on_poll_ms: int = Field(..., ge=0)

    # Mouse/touch movements (count of events)
    mouse_move_count: int = Field(0, ge=0)
    mouse_click_count: int = Field(0, ge=0)
    scroll_count: int = Field(0, ge=0)

    # Interaction patterns
    changed_choice: bool = False  # Did user change their mind?
    viewed_results_preview: bool = False
    expanded_details: bool = False

    # Touch vs mouse (mobile detection)
    is_touch_device: bool = False

    # JavaScript execution time (anti-headless)
    js_execution_time_ms: Optional[int] = None


class IPIntelligence(BaseModel):
    """IP intelligence data."""

    ip_address: str
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    is_datacenter: bool = False
    is_residential: bool = True

    # Geolocation
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None

    # ISP/ASN info
    asn: Optional[int] = None
    asn_org: Optional[str] = None
    isp: Optional[str] = None

    # Risk score from IP service
    ip_risk_score: int = 0

    # Fraud signals
    recent_abuse_reports: int = 0
    is_known_attacker: bool = False


class VoteRiskAssessment(BaseModel):
    """Complete risk assessment for a vote attempt."""

    # Overall risk
    risk_score: int = 0  # 0-100 scale
    risk_level: RiskLevel = RiskLevel.LOW

    # Required action
    required_challenge: ChallengeType = ChallengeType.NONE

    # Should vote be allowed?
    allow_vote: bool = True
    block_reason: Optional[str] = None

    # Individual risk factors
    risk_factors: list[str] = Field(default_factory=list)

    # Confidence in assessment (0-1)
    confidence: float = 1.0

    # Debugging info (not exposed to client)
    debug_info: dict = Field(default_factory=dict)


class UserReputationScore(BaseModel):
    """User's reputation/trust score over time."""

    user_id: str

    # Core reputation (0-100, starts at 50)
    reputation_score: int = 50

    # Verification status - BOTH required for voting
    email_verified: bool = False
    phone_verified: bool = False
    both_verified: bool = False  # Computed: email AND phone both verified
    has_profile_photo: bool = False

    # Account age factors
    account_age_days: int = 0
    first_vote_date: Optional[datetime] = None

    # Voting history
    total_votes: int = 0
    votes_last_24h: int = 0
    votes_last_7d: int = 0

    # Challenge history
    captcha_passes: int = 0
    captcha_fails: int = 0
    last_captcha_pass: Optional[datetime] = None

    # Flags
    flagged_count: int = 0
    false_positive_appeals: int = 0  # Times user was wrongly flagged

    # Computed trust tier
    @property
    def trust_tier(self) -> str:
        """Compute trust tier from reputation score."""
        if self.reputation_score >= 80:
            return "trusted"
        elif self.reputation_score >= 60:
            return "verified"
        elif self.reputation_score >= 40:
            return "standard"
        elif self.reputation_score >= 20:
            return "limited"
        else:
            return "restricted"


# =============================================================================
# IP Intelligence Service
# =============================================================================


class IPIntelligenceService:
    """
    Service to check IP addresses for VPN/proxy/bot indicators.

    Uses multiple providers for redundancy:
    - IPInfo.io (free tier: 50k/month)
    - IP-API.com (free tier: 45 req/min)
    - AbuseIPDB (free tier: 1000/day)

    For production, consider:
    - MaxMind GeoIP2
    - IPQualityScore
    - Sift Science
    """

    def __init__(self):
        self.ipinfo_token = getattr(settings, "IPINFO_TOKEN", None)
        self.abuseipdb_key = getattr(settings, "ABUSEIPDB_KEY", None)

        # Known datacenter/cloud IP ranges (sample - expand in production)
        self._datacenter_ranges = self._load_datacenter_ranges()

        # Known Tor exit nodes (refresh periodically)
        self._tor_exit_nodes: set[str] = set()

    def _load_datacenter_ranges(self) -> list[ipaddress.IPv4Network]:
        """Load known datacenter IP ranges."""
        # Sample ranges - in production, use a comprehensive list
        # from providers like MaxMind or ip2location
        ranges = [
            # AWS
            "3.0.0.0/8",
            "52.0.0.0/8",
            # Google Cloud
            "35.0.0.0/8",
            # Azure
            "40.0.0.0/8",
            "52.0.0.0/8",
            # DigitalOcean
            "104.131.0.0/16",
            "167.99.0.0/16",
            # Linode
            "45.33.0.0/16",
            # Vultr
            "45.32.0.0/16",
        ]
        return [ipaddress.IPv4Network(r) for r in ranges]

    def _is_datacenter_ip(self, ip: str) -> bool:
        """Check if IP belongs to known datacenter."""
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            return any(ip_obj in network for network in self._datacenter_ranges)
        except (ipaddress.AddressValueError, ValueError):
            return False

    async def check_ip(self, ip_address: str) -> IPIntelligence:
        """
        Check an IP address for fraud indicators.

        Combines multiple data sources for accurate assessment.
        """
        result = IPIntelligence(ip_address=ip_address)

        # Check datacenter ranges locally (fast)
        result.is_datacenter = self._is_datacenter_ip(ip_address)

        # Check Tor exit nodes locally (fast)
        result.is_tor = ip_address in self._tor_exit_nodes

        # Query external IP intelligence (if configured)
        try:
            if self.ipinfo_token:
                await self._query_ipinfo(ip_address, result)
        except Exception as e:
            logger.warning("ipinfo_query_failed", ip=ip_address[:8], error=str(e))

        try:
            if self.abuseipdb_key:
                await self._query_abuseipdb(ip_address, result)
        except Exception as e:
            logger.warning("abuseipdb_query_failed", ip=ip_address[:8], error=str(e))

        # Calculate IP risk score
        result.ip_risk_score = self._calculate_ip_risk_score(result)

        return result

    async def _query_ipinfo(self, ip: str, result: IPIntelligence) -> None:
        """Query ipinfo.io for IP data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://ipinfo.io/{ip}/json",
                params={"token": self.ipinfo_token},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                result.country_code = data.get("country")
                result.region = data.get("region")
                result.city = data.get("city")
                result.asn_org = data.get("org")

                # IPInfo privacy detection (paid feature)
                privacy = data.get("privacy", {})
                result.is_vpn = privacy.get("vpn", False)
                result.is_proxy = privacy.get("proxy", False)
                result.is_tor = privacy.get("tor", False) or result.is_tor

    async def _query_abuseipdb(self, ip: str, result: IPIntelligence) -> None:
        """Query AbuseIPDB for abuse reports."""
        if not self.abuseipdb_key:
            return

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip, "maxAgeInDays": 90},
                headers={"Key": str(self.abuseipdb_key), "Accept": "application/json"},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                result.recent_abuse_reports = data.get("totalReports", 0)
                result.ip_risk_score = max(result.ip_risk_score, data.get("abuseConfidenceScore", 0))

    def _calculate_ip_risk_score(self, result: IPIntelligence) -> int:
        """Calculate overall IP risk score."""
        score = 0

        if result.is_tor:
            score += 80  # High risk
        if result.is_datacenter:
            score += 60
        if result.is_proxy:
            score += 50
        if result.is_vpn:
            score += 40  # Some users have legitimate VPN use
        if result.recent_abuse_reports > 10:
            score += 30
        if result.recent_abuse_reports > 0:
            score += 10
        if result.is_known_attacker:
            score = 100

        return min(score, 100)


# =============================================================================
# Behavioral Analysis Service
# =============================================================================


class BehavioralAnalysisService:
    """
    Analyze user behavior patterns to detect bots.

    Bots typically exhibit:
    - Instant voting (no reading time)
    - No mouse movements
    - Perfect timing patterns
    - Sequential choice patterns
    """

    def analyze(
        self,
        signals: BehavioralSignals,
        user_history: Optional[list[dict]] = None,
    ) -> tuple[int, list[str]]:
        """
        Analyze behavioral signals and return (risk_score, risk_factors).

        Risk score: 0-100
        """
        score = 0
        factors = []

        # Check time on poll
        time_on_poll_s = signals.time_on_poll_ms / 1000
        if time_on_poll_s < FraudConfig.MIN_TIME_ON_POLL_SECONDS:
            score += 40
            factors.append(f"Voted too quickly ({time_on_poll_s:.1f}s)")
        elif time_on_poll_s < 1.0:
            score += 60
            factors.append("Suspiciously fast voting (<1s)")

        # Check mouse/touch activity
        total_interaction = signals.mouse_move_count + signals.mouse_click_count + signals.scroll_count

        if total_interaction == 0:
            # Desktop with no mouse movement is suspicious
            if not signals.is_touch_device:
                score += 30
                factors.append("No mouse activity detected")

        # Check for natural behavior indicators
        if signals.changed_choice:
            score -= 10  # Humans change their minds
        if signals.viewed_results_preview:
            score -= 5  # Engagement is good
        if signals.expanded_details:
            score -= 5

        # Check JS execution time (headless browsers are often faster)
        if signals.js_execution_time_ms and signals.js_execution_time_ms < 50:
            score += 20
            factors.append("Abnormally fast JS execution")

        # Analyze historical patterns if available
        if user_history:
            pattern_score, pattern_factors = self._analyze_history(user_history)
            score += pattern_score
            factors.extend(pattern_factors)

        return max(0, min(score, 100)), factors

    def _analyze_history(
        self,
        history: list[dict],
    ) -> tuple[int, list[str]]:
        """Analyze voting history for patterns."""
        score = 0
        factors = []

        if len(history) < 5:
            return 0, []  # Not enough data

        # Check for same-position voting pattern
        # (Always picking option 1, 2, etc.)
        positions = [v.get("choice_position", 0) for v in history[-20:]]
        if positions:
            most_common = max(set(positions), key=positions.count)
            frequency = positions.count(most_common) / len(positions)
            if frequency > FraudConfig.SUSPICIOUS_CHOICE_PATTERN_THRESHOLD:
                score += 30
                factors.append(f"Suspicious voting pattern (same position {frequency:.0%})")

        # Check for regular timing patterns (bot-like consistency)
        timestamps = [v.get("timestamp") for v in history[-20:] if v.get("timestamp")]
        if len(timestamps) >= 3:
            # Calculate intervals
            intervals: list[float] = []
            for i in range(1, len(timestamps)):
                ts_current = timestamps[i]
                ts_prev = timestamps[i - 1]
                if isinstance(ts_current, datetime) and isinstance(ts_prev, datetime):
                    intervals.append((ts_current - ts_prev).total_seconds())

            if intervals:
                # Check for suspiciously consistent timing
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
                std_dev = math.sqrt(variance)

                # Very low variance suggests automation
                if std_dev < 1.0 and avg_interval < 60:  # Within 1 second of each other
                    score += 40
                    factors.append("Machine-like voting timing pattern")

        return score, factors


# =============================================================================
# Device Fingerprint Service
# =============================================================================


class DeviceFingerprintService:
    """
    Service for device fingerprint management and detection.

    Tracks device fingerprints to detect:
    - Same device voting from multiple accounts
    - Device spoofing attempts
    - Virtual machine/emulator usage
    """

    def __init__(self):
        self.salt = FraudConfig.FINGERPRINT_SALT
        # In production, use Redis for fingerprint storage
        self._fingerprint_store: dict[str, dict] = {}

    def generate_fingerprint_id(self, fingerprint: DeviceFingerprint) -> str:
        """Generate stable fingerprint ID."""
        return fingerprint.compute_fingerprint_id(self.salt)

    async def check_fingerprint(
        self,
        fingerprint: DeviceFingerprint,
        user_id: str,
        poll_id: str,
    ) -> tuple[int, list[str]]:
        """
        Check fingerprint for fraud indicators.

        Returns (risk_score, risk_factors).
        """
        score = 0
        factors = []

        fingerprint_id = self.generate_fingerprint_id(fingerprint)

        # Check for VM/emulator indicators
        vm_score, vm_factors = self._check_vm_indicators(fingerprint)
        score += vm_score
        factors.extend(vm_factors)

        # Check for headless browser indicators
        headless_score, headless_factors = self._check_headless_indicators(fingerprint)
        score += headless_score
        factors.extend(headless_factors)

        # Check if this fingerprint has voted on this poll before (different user)
        fingerprint_key = f"{fingerprint_id}:{poll_id}"
        existing = self._fingerprint_store.get(fingerprint_key)

        if existing and existing.get("user_id") != user_id:
            # Same device, different user - very suspicious
            score += 70
            factors.append("Device already voted on this poll with different account")

        # Check how many different users this device has been associated with
        device_users = self._get_device_user_history(fingerprint_id)
        if len(device_users) > 3:
            score += 40
            factors.append(f"Device associated with {len(device_users)} different accounts")

        # Store this vote attempt
        self._fingerprint_store[fingerprint_key] = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return min(score, 100), factors

    def _check_vm_indicators(
        self,
        fingerprint: DeviceFingerprint,
    ) -> tuple[int, list[str]]:
        """Check for VM/emulator indicators."""
        score = 0
        factors = []

        # Check WebGL renderer for VM signatures
        if fingerprint.webgl_renderer:
            vm_signatures = [
                "swiftshader",
                "llvmpipe",
                "virtualbox",
                "vmware",
                "parallels",
                "microsoft basic",
            ]
            renderer_lower = fingerprint.webgl_renderer.lower()
            if any(sig in renderer_lower for sig in vm_signatures):
                score += 30
                factors.append("VM/emulator detected via WebGL")

        # Suspicious hardware specs
        if fingerprint.hardware_concurrency == 1:
            score += 10
            factors.append("Single CPU core (unusual)")

        if fingerprint.device_memory and fingerprint.device_memory < 2:
            score += 10
            factors.append("Very low device memory")

        return score, factors

    def _check_headless_indicators(
        self,
        fingerprint: DeviceFingerprint,
    ) -> tuple[int, list[str]]:
        """Check for headless browser indicators."""
        score = 0
        factors = []

        # Missing typical browser fingerprint data
        if not fingerprint.canvas_hash:
            score += 15
            factors.append("Missing canvas fingerprint")

        if not fingerprint.audio_hash:
            score += 10
            factors.append("Missing audio fingerprint")

        # Check for Puppeteer/Playwright user agent patterns
        ua_lower = fingerprint.user_agent.lower()
        headless_patterns = ["headless", "puppeteer", "playwright", "selenium"]
        if any(p in ua_lower for p in headless_patterns):
            score += 50
            factors.append("Headless browser detected in user agent")

        # Check for automation indicators in platform
        if fingerprint.platform == "":
            score += 20
            factors.append("Empty platform string")

        return score, factors

    def _get_device_user_history(self, fingerprint_id: str) -> set[str]:
        """Get all users associated with this device."""
        users = set()
        for key, value in self._fingerprint_store.items():
            if key.startswith(fingerprint_id):
                users.add(value.get("user_id", ""))
        return users


# =============================================================================
# Main Fraud Detection Service
# =============================================================================


class FraudDetectionService:
    """
    Main fraud detection orchestrator.

    Combines all signals to make a final risk assessment for each vote.
    """

    def __init__(self):
        self.ip_service = IPIntelligenceService()
        self.behavioral_service = BehavioralAnalysisService()
        self.fingerprint_service = DeviceFingerprintService()

        # In production, use Redis
        self._rate_limit_store: dict[str, list[float]] = {}
        self._challenge_store: dict[str, dict] = {}

    async def assess_vote_risk(
        self,
        user_id: str,
        poll_id: str,
        ip_address: str,
        fingerprint: Optional[DeviceFingerprint] = None,
        behavioral_signals: Optional[BehavioralSignals] = None,
        user_reputation: Optional[UserReputationScore] = None,
    ) -> VoteRiskAssessment:
        """
        Perform comprehensive risk assessment for a vote attempt.

        This is the main entry point for vote validation.
        """
        assessment = VoteRiskAssessment()
        risk_score = 0

        # 1. Check rate limits
        rate_limited, rate_factors = self._check_rate_limits(user_id)
        if rate_limited:
            assessment.allow_vote = False
            assessment.block_reason = "Rate limit exceeded"
            assessment.risk_score = 100
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.risk_factors = rate_factors
            return assessment

        # 2. IP Intelligence check
        ip_intel = await self.ip_service.check_ip(ip_address)

        if ip_intel.is_tor and FraudConfig.BLOCK_TOR:
            risk_score += 80
            assessment.risk_factors.append("Tor exit node detected")
        elif ip_intel.is_datacenter and FraudConfig.BLOCK_DATACENTER:
            risk_score += 60
            assessment.risk_factors.append("Datacenter IP detected")
        elif ip_intel.is_proxy and FraudConfig.BLOCK_PROXY:
            risk_score += 50
            assessment.risk_factors.append("Proxy detected")
        elif ip_intel.is_vpn and FraudConfig.BLOCK_VPN:
            # VPNs are common, so only add moderate risk
            risk_score += 30
            assessment.risk_factors.append("VPN detected")

        if ip_intel.recent_abuse_reports > 10:
            risk_score += 20
            assessment.risk_factors.append(f"IP has {ip_intel.recent_abuse_reports} abuse reports")

        # 3. Device fingerprint check
        if fingerprint:
            fp_score, fp_factors = await self.fingerprint_service.check_fingerprint(fingerprint, user_id, poll_id)
            risk_score += fp_score
            assessment.risk_factors.extend(fp_factors)
        else:
            # Missing fingerprint is suspicious
            risk_score += 20
            assessment.risk_factors.append("No device fingerprint provided")

        # 4. Behavioral analysis
        if behavioral_signals:
            behav_score, behav_factors = self.behavioral_service.analyze(behavioral_signals)
            risk_score += behav_score
            assessment.risk_factors.extend(behav_factors)

        # 5. CRITICAL: Verification requirements check
        # This is the primary defense against bot farms
        verification_block = self._check_verification_requirements(user_reputation, assessment)
        if verification_block:
            return assessment

        # 6. User reputation adjustment (only if verification passed)
        if user_reputation:
            reputation_adjustment = self._calculate_reputation_adjustment(user_reputation)
            risk_score += reputation_adjustment

            # Bonus for fully verified users (both email + phone)
            if user_reputation.email_verified and user_reputation.phone_verified:
                risk_score -= 30  # Significant bonus for dual verification
                assessment.debug_info["dual_verified_bonus"] = -30
            elif user_reputation.phone_verified:
                risk_score -= 20
                assessment.debug_info["phone_verified_bonus"] = -20
            elif user_reputation.email_verified:
                risk_score -= 10
                assessment.debug_info["email_verified_bonus"] = -10

            if user_reputation.account_age_days > 30:
                risk_score -= 10
                assessment.debug_info["account_age_bonus"] = -10

            if user_reputation.total_votes > 50 and user_reputation.flagged_count == 0:
                risk_score -= 15
                assessment.debug_info["good_history_bonus"] = -15

        # 6. Check if CAPTCHA was recently passed
        if self._has_valid_captcha_pass(user_id):
            risk_score -= 30
            assessment.debug_info["recent_captcha_pass"] = True

        # Clamp risk score
        risk_score = max(0, min(risk_score, 100))
        assessment.risk_score = risk_score

        # Determine risk level and required action
        if risk_score >= FraudConfig.BLOCK_THRESHOLD:
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.allow_vote = False
            assessment.block_reason = "Risk score too high"
            assessment.required_challenge = ChallengeType.BLOCK
        elif risk_score >= FraudConfig.HIGH_RISK_THRESHOLD:
            assessment.risk_level = RiskLevel.HIGH
            assessment.required_challenge = ChallengeType.CAPTCHA
        elif risk_score >= FraudConfig.MEDIUM_RISK_THRESHOLD:
            assessment.risk_level = RiskLevel.MEDIUM
            if not user_reputation or not user_reputation.phone_verified:
                assessment.required_challenge = ChallengeType.CAPTCHA
        else:
            assessment.risk_level = RiskLevel.LOW
            assessment.required_challenge = ChallengeType.NONE

        # Store debug info
        assessment.debug_info["ip_risk"] = ip_intel.ip_risk_score
        assessment.debug_info["ip_country"] = ip_intel.country_code

        # Update rate limit tracking
        self._record_vote_attempt(user_id)

        return assessment

    def _check_rate_limits(self, user_id: str) -> tuple[bool, list[str]]:
        """Check if user has exceeded rate limits."""
        now = time.time()
        factors = []

        # Get user's recent vote timestamps
        timestamps = self._rate_limit_store.get(user_id, [])

        # Clean old entries
        timestamps = [t for t in timestamps if now - t < 86400]  # Keep last 24h

        # Check limits
        votes_last_minute = sum(1 for t in timestamps if now - t < 60)
        votes_last_hour = sum(1 for t in timestamps if now - t < 3600)
        votes_last_day = len(timestamps)

        if votes_last_minute >= FraudConfig.MAX_VOTES_PER_MINUTE:
            factors.append(f"Exceeded {FraudConfig.MAX_VOTES_PER_MINUTE} votes/minute")
            return True, factors

        if votes_last_hour >= FraudConfig.MAX_VOTES_PER_HOUR:
            factors.append(f"Exceeded {FraudConfig.MAX_VOTES_PER_HOUR} votes/hour")
            return True, factors

        if votes_last_day >= FraudConfig.MAX_VOTES_PER_DAY:
            factors.append(f"Exceeded {FraudConfig.MAX_VOTES_PER_DAY} votes/day")
            return True, factors

        return False, factors

    def _record_vote_attempt(self, user_id: str) -> None:
        """Record a vote attempt for rate limiting."""
        now = time.time()
        if user_id not in self._rate_limit_store:
            self._rate_limit_store[user_id] = []
        self._rate_limit_store[user_id].append(now)

    def _calculate_reputation_adjustment(
        self,
        reputation: UserReputationScore,
    ) -> int:
        """Calculate risk adjustment based on user reputation."""
        if reputation.reputation_score >= 80:
            return -30  # Trusted users get a bonus
        elif reputation.reputation_score >= 60:
            return -15
        elif reputation.reputation_score <= 20:
            return 30  # Low reputation users get penalty
        return 0

    def _has_valid_captcha_pass(self, user_id: str) -> bool:
        """Check if user has a recent valid CAPTCHA pass."""
        record = self._challenge_store.get(user_id)
        if not record:
            return False

        passed_at = record.get("passed_at")
        if not passed_at:
            return False

        # Check if within cooldown period
        cooldown = timedelta(minutes=FraudConfig.CAPTCHA_COOLDOWN_MINUTES)
        if datetime.now(timezone.utc) - passed_at < cooldown:
            return True

        return False

    def record_captcha_result(self, user_id: str, passed: bool) -> None:
        """Record CAPTCHA attempt result."""
        self._challenge_store[user_id] = {
            "passed": passed,
            "passed_at": datetime.now(timezone.utc) if passed else None,
            "attempted_at": datetime.now(timezone.utc),
        }

    def _check_verification_requirements(
        self,
        user_reputation: Optional[UserReputationScore],
        assessment: VoteRiskAssessment,
    ) -> bool:
        """
        Check if user meets verification requirements for voting.

        This is THE MOST IMPORTANT check for bot farm resistance.
        Bot farms struggle to:
        1. Verify email addresses at scale (somewhat easy to bypass)
        2. Verify phone numbers at scale (VERY hard - costs money per number)
        3. Have BOTH verified on the same account (multiplicative difficulty)

        Returns True if voting should be blocked (verification missing).
        """
        if not user_reputation:
            assessment.allow_vote = False
            assessment.block_reason = "User verification status unknown"
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.required_challenge = ChallengeType.BLOCK
            assessment.risk_factors.append("no_user_reputation")
            return True

        missing_verifications = []

        # Check email verification requirement
        if FraudConfig.REQUIRE_EMAIL_VERIFIED and not user_reputation.email_verified:
            missing_verifications.append("email")

        # Check phone verification requirement
        if FraudConfig.REQUIRE_PHONE_VERIFIED and not user_reputation.phone_verified:
            missing_verifications.append("phone")

        # If both are required, check that BOTH are present
        if FraudConfig.REQUIRE_BOTH_VERIFIED:
            if not user_reputation.email_verified or not user_reputation.phone_verified:
                if not missing_verifications:
                    # This handles edge case where individual requirements are disabled
                    # but REQUIRE_BOTH_VERIFIED is True
                    if not user_reputation.email_verified:
                        missing_verifications.append("email")
                    if not user_reputation.phone_verified:
                        missing_verifications.append("phone")

        if missing_verifications:
            assessment.allow_vote = False

            if "phone" in missing_verifications and "email" in missing_verifications:
                assessment.block_reason = (
                    "Both email and phone verification required. "
                    "This ensures one person = one vote and protects poll integrity."
                )
                assessment.required_challenge = ChallengeType.BLOCK
                assessment.risk_factors.append("missing_email_verification")
                assessment.risk_factors.append("missing_phone_verification")
            elif "phone" in missing_verifications:
                assessment.block_reason = "Phone verification required. This helps ensure one person = one vote."
                assessment.required_challenge = ChallengeType.SMS_VERIFY
                assessment.risk_factors.append("missing_phone_verification")
            else:
                assessment.block_reason = "Email verification required. Please check your inbox and verify your email."
                assessment.required_challenge = ChallengeType.BLOCK
                assessment.risk_factors.append("missing_email_verification")

            assessment.risk_level = RiskLevel.CRITICAL
            assessment.debug_info["missing_verifications"] = missing_verifications
            return True

        # User is properly verified
        assessment.debug_info["verification_passed"] = True
        assessment.debug_info["both_verified"] = user_reputation.email_verified and user_reputation.phone_verified
        return False


# =============================================================================
# Singleton instance
# =============================================================================

fraud_detection_service = FraudDetectionService()
