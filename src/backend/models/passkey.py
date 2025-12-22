"""
WebAuthn/Passkey credential model for PostgreSQL storage.

Stores FIDO2 credentials for passwordless authentication.
Each user can have multiple passkeys (e.g., phone, laptop, security key).
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class PasskeyCredential(Base):
    """
    WebAuthn credential storage for passkey authentication.
    
    Each credential represents a FIDO2 authenticator (passkey) registered
    to a user account. A user can have multiple credentials for different
    devices (phone, laptop, hardware security key).
    
    Security Properties:
    - credential_id: Public identifier for the credential
    - public_key: COSE-encoded public key for signature verification
    - sign_count: Replay attack prevention counter
    - Credentials are bound to RP ID (origin), preventing phishing
    """
    
    __tablename__ = "passkey_credentials"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # WebAuthn credential data
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary,
        unique=True,
        index=True,
        comment="Base64url-decoded credential ID from authenticator",
    )
    
    public_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        comment="COSE-encoded public key for signature verification",
    )
    
    # Counter for replay attack prevention
    sign_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Signature counter, must increase on each authentication",
    )
    
    # Credential metadata
    credential_name: Mapped[str] = mapped_column(
        String(100),
        default="My Passkey",
        comment="User-friendly name for the credential",
    )
    
    # Authenticator info (for display purposes)
    authenticator_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="platform (biometric) or cross-platform (security key)",
    )
    
    device_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Device type hint (iPhone, Android, Windows Hello, etc.)",
    )
    
    # AAGUID for authenticator identification
    aaguid: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="Authenticator Attestation GUID",
    )
    
    # Transports (how authenticator communicates)
    transports: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of supported transports (usb, nfc, ble, internal, hybrid)",
    )
    
    # Attestation (optional, for enterprise use)
    attestation_object: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        nullable=True,
        comment="Raw attestation object (optional, for audit)",
    )
    
    # Backup eligibility (synced passkeys)
    is_backup_eligible: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether credential can be synced (e.g., iCloud Keychain)",
    )
    
    is_backed_up: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether credential is currently backed up/synced",
    )
    
    # Trust binding
    bound_to_phone: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this credential is bound to a verified phone",
    )
    
    bound_phone_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Hash of phone number this credential was registered with",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether credential is active and can be used",
    )
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    use_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of times this credential has been used",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationship
    user = relationship("User", back_populates="passkey_credentials")


class DeviceTrustScore(Base):
    """
    Device trust scoring for enhanced fraud prevention.
    
    Tracks device behavior over time to build a trust score.
    Higher trust = fewer challenges, smoother UX.
    Lower trust = more verification required.
    """
    
    __tablename__ = "device_trust_scores"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # Device identification (hashed fingerprint)
    device_fingerprint_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        comment="SHA256 hash of device fingerprint",
    )
    
    # Associated user (if known)
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Trust score (0-100)
    trust_score: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Current trust score (0=untrusted, 100=fully trusted)",
    )
    
    # Score components
    verification_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Score from successful verifications",
    )
    
    behavioral_score: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Score from behavioral analysis",
    )
    
    history_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Score from account history",
    )
    
    # Risk factors
    vpn_detected_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    suspicious_behavior_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    failed_auth_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    # Positive factors
    successful_votes: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    successful_auths: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    days_active: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    
    # Device info
    last_ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    
    last_user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Carrier verification (silent mobile auth)
    carrier_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether device passed carrier verification",
    )
    
    carrier_verification_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    carrier_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationship
    user = relationship("User", back_populates="device_trust_scores")
    
    def calculate_trust_score(self) -> int:
        """Calculate composite trust score from components."""
        # Weighted average of components
        score = (
            self.verification_score * 0.4 +
            self.behavioral_score * 0.3 +
            self.history_score * 0.3
        )
        
        # Apply penalties
        score -= self.vpn_detected_count * 5
        score -= self.suspicious_behavior_count * 10
        score -= self.failed_auth_count * 3
        
        # Apply bonuses
        score += min(self.successful_votes * 0.5, 20)  # Cap at 20 bonus
        score += min(self.successful_auths * 1, 10)     # Cap at 10 bonus
        score += min(self.days_active * 0.5, 15)        # Cap at 15 bonus
        
        # Carrier verification bonus
        if self.carrier_verified:
            score += 15
        
        # Clamp to valid range
        return max(0, min(100, int(score)))


class SilentMobileVerification(Base):
    """
    Records of silent mobile/carrier verification attempts.
    
    Silent mobile auth uses carrier APIs to verify that a phone number
    matches the SIM in the device making the request (no SMS needed).
    """
    
    __tablename__ = "silent_mobile_verifications"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Phone number (hashed for privacy)
    phone_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        comment="SHA256 hash of phone number",
    )
    
    # Verification result
    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    
    verification_method: Mapped[str] = mapped_column(
        String(50),
        comment="silentauth, sna, ipification, etc.",
    )
    
    # Carrier info
    carrier_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    carrier_mcc: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="Mobile Country Code",
    )
    
    carrier_mnc: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="Mobile Network Code",
    )
    
    # Request info
    ip_address: Mapped[str] = mapped_column(
        String(45),
    )
    
    device_fingerprint_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    
    # Error info (if failed)
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationship
    user = relationship("User", back_populates="silent_mobile_verifications")
