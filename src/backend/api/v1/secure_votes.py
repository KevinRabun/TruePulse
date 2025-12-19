"""
Secure voting API endpoints with fraud prevention.

This module provides fraud-protected voting endpoints that:
1. Validate device fingerprints
2. Analyze behavioral signals
3. Check IP intelligence
4. Require CAPTCHA when suspicious
5. Block high-risk vote attempts
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_verified_user
from core.security import generate_vote_hash
from db.session import get_db
from models.poll import PollStatus
from repositories.poll_repository import PollRepository
from repositories.user_repository import UserRepository
from repositories.vote_repository import VoteRepository
from schemas.user import UserInDB
from services.fraud_detection import (
    BehavioralSignals,
    ChallengeType,
    DeviceFingerprint,
    RiskLevel,
    UserReputationScore,
    fraud_detection_service,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class SecureVoteRequest(BaseModel):
    """Vote request with fraud prevention data."""

    poll_id: str = Field(..., min_length=1)
    choice_id: str = Field(..., min_length=1)

    # Fraud prevention data
    fingerprint: Optional[DeviceFingerprint] = None
    behavioral_signals: Optional[BehavioralSignals] = None
    captcha_token: Optional[str] = None


class VoteRiskResponse(BaseModel):
    """Response indicating vote risk assessment."""

    allow_vote: bool
    risk_level: str
    required_challenge: str
    message: str
    challenge_data: Optional[dict] = None


class SecureVoteResponse(BaseModel):
    """Response after successful vote."""

    success: bool
    message: str
    points_earned: int = 0
    risk_level: str


# =============================================================================
# Helper Functions
# =============================================================================


def get_client_ip(request: Request) -> str:
    """Extract real client IP from request, handling proxies."""
    # Check common proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP (original client)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client:
        return request.client.host

    return "unknown"


async def get_user_reputation(user: UserInDB, db: AsyncSession) -> UserReputationScore:
    """Build user reputation score from database."""
    repo = UserRepository(db)
    db_user = await repo.get_by_id(user.id)

    if not db_user:
        return UserReputationScore(
            user_id=user.id,
            reputation_score=0,
            email_verified=False,
            phone_verified=False,
            both_verified=False,
            account_age_days=0,
            total_votes=0,
            votes_last_24h=0,
            votes_last_7d=0,
        )

    account_age = (
        (datetime.now(timezone.utc) - db_user.created_at).days
        if db_user.created_at
        else 0
    )

    email_verified = db_user.is_verified
    phone_verified = getattr(db_user, "phone_verified", False)

    # Calculate reputation score based on user activity
    base_score = 50
    if email_verified:
        base_score += 15
    if phone_verified:
        base_score += 20
    if account_age > 30:
        base_score += 10
    if db_user.votes_cast > 10:
        base_score += 5

    return UserReputationScore(
        user_id=user.id,
        reputation_score=min(100, base_score),
        email_verified=email_verified,
        phone_verified=phone_verified,
        both_verified=email_verified and phone_verified,
        account_age_days=account_age,
        total_votes=db_user.votes_cast,
        votes_last_24h=0,  # Would need separate query with time filter
        votes_last_7d=0,
    )


def check_verification_status(user: UserInDB) -> tuple[bool, Optional[dict]]:
    """
    Check if user has required verification for voting.

    Returns (is_verified, error_response) tuple.
    If is_verified is False, error_response contains the HTTPException detail.
    """
    from services.fraud_detection import FraudConfig

    email_verified = user.is_verified
    phone_verified = getattr(user, "phone_verified", False)

    missing = []

    if FraudConfig.REQUIRE_EMAIL_VERIFIED and not email_verified:
        missing.append("email")

    if FraudConfig.REQUIRE_PHONE_VERIFIED and not phone_verified:
        missing.append("phone")

    if FraudConfig.REQUIRE_BOTH_VERIFIED:
        if not email_verified:
            missing.append("email") if "email" not in missing else None
        if not phone_verified:
            missing.append("phone") if "phone" not in missing else None

    if not missing:
        return True, None

    # Build helpful error response
    if "email" in missing and "phone" in missing:
        return False, {
            "error": "verification_required",
            "missing_verifications": ["email", "phone"],
            "message": (
                "Both email and phone verification are required to vote. "
                "This ensures one person = one vote and protects poll integrity from bots."
            ),
            "actions": [
                {
                    "type": "verify_email",
                    "label": "Verify Email",
                    "url": "/settings/verify-email",
                },
                {
                    "type": "verify_phone",
                    "label": "Verify Phone",
                    "url": "/settings/verify-phone",
                },
            ],
        }
    elif "phone" in missing:
        return False, {
            "error": "phone_verification_required",
            "missing_verifications": ["phone"],
            "message": (
                "Phone verification is required to vote. "
                "This helps ensure one person = one vote."
            ),
            "actions": [
                {
                    "type": "verify_phone",
                    "label": "Verify Phone",
                    "url": "/settings/verify-phone",
                },
            ],
        }
    else:
        return False, {
            "error": "email_verification_required",
            "missing_verifications": ["email"],
            "message": "Please verify your email address to vote.",
            "actions": [
                {
                    "type": "verify_email",
                    "label": "Verify Email",
                    "url": "/settings/verify-email",
                },
            ],
        }


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/pre-check", response_model=VoteRiskResponse)
async def pre_check_vote(
    request: Request,
    vote_data: SecureVoteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> VoteRiskResponse:
    """
    Pre-check vote before submission.

    Call this before showing the vote confirmation to determine if
    the user needs to complete a CAPTCHA or other verification.

    This allows the frontend to show the CAPTCHA before the vote
    is actually submitted, improving UX.
    """
    # Early check: Verify user has required verification status
    is_verified, error_detail = check_verification_status(current_user)
    if not is_verified and error_detail:
        return VoteRiskResponse(
            allow_vote=False,
            risk_level="critical",
            required_challenge="verification",
            message=error_detail["message"],
            challenge_data=error_detail,
        )

    client_ip = get_client_ip(request)
    user_reputation = await get_user_reputation(current_user, db)

    # Perform risk assessment
    assessment = await fraud_detection_service.assess_vote_risk(
        user_id=current_user.id,
        poll_id=vote_data.poll_id,
        ip_address=client_ip,
        fingerprint=vote_data.fingerprint,
        behavioral_signals=vote_data.behavioral_signals,
        user_reputation=user_reputation,
    )

    # Determine response
    if not assessment.allow_vote:
        return VoteRiskResponse(
            allow_vote=False,
            risk_level=assessment.risk_level.value,
            required_challenge=assessment.required_challenge.value,
            message=assessment.block_reason
            or "Vote blocked due to suspicious activity",
        )

    if assessment.required_challenge == ChallengeType.CAPTCHA:
        return VoteRiskResponse(
            allow_vote=True,
            risk_level=assessment.risk_level.value,
            required_challenge="captcha",
            message="Please complete the verification challenge",
            challenge_data={
                "type": "turnstile",  # Using Cloudflare Turnstile
                "site_key": "0x4AAAAAAA...",  # Configure via environment
            },
        )

    if assessment.required_challenge == ChallengeType.SMS_VERIFY:
        return VoteRiskResponse(
            allow_vote=True,
            risk_level=assessment.risk_level.value,
            required_challenge="sms_verify",
            message="Please verify your phone number to continue",
        )

    return VoteRiskResponse(
        allow_vote=True,
        risk_level=assessment.risk_level.value,
        required_challenge="none",
        message="Ready to vote",
    )


@router.post("", response_model=SecureVoteResponse, status_code=status.HTTP_201_CREATED)
async def cast_secure_vote(
    request: Request,
    vote_data: SecureVoteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> SecureVoteResponse:
    """
    Cast a vote with full fraud prevention.

    This endpoint performs comprehensive fraud detection:
    1. Email AND phone verification check (REQUIRED)
    2. Device fingerprint validation
    3. Behavioral analysis
    4. IP intelligence check
    5. Rate limiting
    6. CAPTCHA verification (if required)

    Only votes that pass all checks are recorded.
    """
    # CRITICAL: Check verification requirements FIRST
    # This is the primary defense against bot farms
    is_verified, error_detail = check_verification_status(current_user)
    if not is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_detail,
        )

    client_ip = get_client_ip(request)
    user_reputation = await get_user_reputation(current_user, db)

    # Perform risk assessment
    assessment = await fraud_detection_service.assess_vote_risk(
        user_id=current_user.id,
        poll_id=vote_data.poll_id,
        ip_address=client_ip,
        fingerprint=vote_data.fingerprint,
        behavioral_signals=vote_data.behavioral_signals,
        user_reputation=user_reputation,
    )

    # Check if vote is blocked
    if not assessment.allow_vote:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "vote_blocked",
                "message": assessment.block_reason
                or "Vote blocked due to suspicious activity",
                "risk_level": assessment.risk_level.value,
                "factors": assessment.risk_factors[:3],  # Show top 3 reasons
            },
        )

    # Check if CAPTCHA is required but not provided
    if assessment.required_challenge == ChallengeType.CAPTCHA:
        if not vote_data.captcha_token:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail={
                    "error": "captcha_required",
                    "message": "Please complete the verification challenge",
                    "challenge_type": "captcha",
                },
            )

        # Verify CAPTCHA token
        captcha_valid = await verify_captcha_token(vote_data.captcha_token, client_ip)
        if not captcha_valid:
            # Record failed CAPTCHA
            fraud_detection_service.record_captcha_result(current_user.id, passed=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "captcha_failed",
                    "message": "Verification failed. Please try again.",
                },
            )

        # Record successful CAPTCHA
        fraud_detection_service.record_captcha_result(current_user.id, passed=True)

    # Check if phone verification is required
    if assessment.required_challenge == ChallengeType.SMS_VERIFY:
        if not getattr(current_user, "phone_verified", False):
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail={
                    "error": "phone_verification_required",
                    "message": "Please verify your phone number to vote",
                    "challenge_type": "sms_verify",
                },
            )

    # Initialize repositories
    poll_repo = PollRepository(db)
    vote_repo = VoteRepository(db)
    user_repo = UserRepository(db)

    # Generate privacy-preserving vote hash
    vote_hash = generate_vote_hash(current_user.id, vote_data.poll_id)

    # Check for existing vote
    existing_vote = await vote_repo.exists_by_hash(vote_hash)
    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted on this poll",
        )

    # Verify poll exists and is currently active
    poll = await poll_repo.get_by_id(vote_data.poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    if poll.status != PollStatus.ACTIVE:
        status_str = str(poll.status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Poll is not currently active (status: {status_str})",
        )

    # Verify choice is valid for this poll
    valid_choice_ids = [str(choice.id) for choice in poll.choices]
    if vote_data.choice_id not in valid_choice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid choice for this poll",
        )

    # Get demographics bucket for anonymized aggregation
    db_user = await user_repo.get_by_id(current_user.id)
    demographics_bucket = db_user.get_demographics_bucket() if db_user else None

    # Store vote (hash + choice only, NO user_id)
    await vote_repo.create(
        vote_hash=vote_hash,
        poll_id=vote_data.poll_id,
        choice_id=vote_data.choice_id,
        demographics_bucket=demographics_bucket,
    )

    # Update poll vote count
    await poll_repo.increment_vote_count(vote_data.poll_id, vote_data.choice_id)

    # Award gamification points (reduced if suspicious)
    points = 10
    if assessment.risk_level == RiskLevel.MEDIUM:
        points = 5  # Reduced points for suspicious activity
    elif assessment.risk_level == RiskLevel.HIGH:
        points = 0  # No points for high-risk votes

    if points > 0:
        await user_repo.award_points(current_user.id, points)

    # Update user vote count and streak
    await user_repo.increment_votes_cast(current_user.id)

    await db.commit()

    return SecureVoteResponse(
        success=True,
        message="Vote recorded successfully",
        points_earned=points,
        risk_level=assessment.risk_level.value,
    )


@router.post("/captcha/verify")
async def verify_captcha(
    request: Request,
    token: str,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify a CAPTCHA token.

    After successful verification, the user can vote without
    additional challenges for a limited time.
    """
    client_ip = get_client_ip(request)

    valid = await verify_captcha_token(token, client_ip)

    # Record result
    fraud_detection_service.record_captcha_result(current_user.id, passed=valid)

    if valid:
        return {"success": True, "message": "Verification successful"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed",
        )


# =============================================================================
# CAPTCHA Verification
# =============================================================================


async def verify_captcha_token(token: str, ip_address: str) -> bool:
    """
    Verify a Cloudflare Turnstile token.

    Turnstile is preferred over reCAPTCHA because:
    - Privacy-focused (no tracking)
    - Free for unlimited use
    - Better UX (invisible option)
    - GDPR compliant
    """
    import httpx

    from core.config import settings

    secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", None)
    if not secret_key:
        # If no CAPTCHA configured, allow (for development)
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": secret_key,
                    "response": token,
                    "remoteip": ip_address,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)

            return False
    except Exception as e:
        logger.error("captcha_verification_error", error=str(e))
        return False
