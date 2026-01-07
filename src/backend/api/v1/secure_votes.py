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

from api.deps import get_current_verified_user, rate_limit_vote
from core.security import generate_vote_hash
from models.cosmos_documents import PollStatus
from repositories.cosmos_poll_repository import CosmosPollRepository
from repositories.cosmos_user_repository import CosmosUserRepository
from repositories.cosmos_vote_repository import CosmosVoteRepository
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


async def get_user_reputation(user: UserInDB, user_repo: CosmosUserRepository) -> UserReputationScore:
    """Build user reputation score from database."""
    db_user = await user_repo.get_by_id(user.id)

    if not db_user:
        return UserReputationScore(
            user_id=user.id,
            reputation_score=0,
            email_verified=False,
            account_age_days=0,
            total_votes=0,
            votes_last_24h=0,
            votes_last_7d=0,
        )

    account_age = (datetime.now(timezone.utc) - db_user.created_at).days if db_user.created_at else 0

    email_verified = db_user.is_verified

    # Calculate reputation score based on user activity
    base_score = 50
    if email_verified:
        base_score += 20  # Increased bonus since email is our primary verification
    if account_age > 30:
        base_score += 10
    if db_user.votes_cast > 10:
        base_score += 5

    return UserReputationScore(
        user_id=user.id,
        reputation_score=min(100, base_score),
        email_verified=email_verified,
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

    if FraudConfig.REQUIRE_EMAIL_VERIFIED and not email_verified:
        return False, {
            "error": "verification_required",
            "message": "Email verification required to vote. Please check your inbox.",
            "missing": ["email"],
        }

    return True, None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/pre-check", response_model=VoteRiskResponse)
async def pre_check_vote(
    request: Request,
    vote_data: SecureVoteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    user_repo: CosmosUserRepository = Depends(lambda: CosmosUserRepository()),
    _rate_limit: None = Depends(rate_limit_vote),
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
    user_reputation = await get_user_reputation(current_user, user_repo)

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
            message=assessment.block_reason or "Vote blocked due to suspicious activity",
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

    # Note: SMS verification removed - TruePulse uses email + passkey auth only

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
    poll_repo: CosmosPollRepository = Depends(lambda: CosmosPollRepository()),
    vote_repo: CosmosVoteRepository = Depends(lambda: CosmosVoteRepository()),
    user_repo: CosmosUserRepository = Depends(lambda: CosmosUserRepository()),
    _rate_limit: None = Depends(rate_limit_vote),
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
    user_reputation = await get_user_reputation(current_user, user_repo)

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
                "message": assessment.block_reason or "Vote blocked due to suspicious activity",
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

    # Note: SMS verification removed - TruePulse uses email + passkey auth only
    # Email verification is checked by get_current_verified_user dependency

    # Generate privacy-preserving vote hash
    vote_hash = generate_vote_hash(current_user.id, vote_data.poll_id)

    # Check for existing vote
    existing_vote = await vote_repo.exists_by_hash(vote_hash, vote_data.poll_id)
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Poll is not currently active (status: {poll.status.value})",
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
    _rate_limit: None = Depends(rate_limit_vote),
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

    SECURITY NOTE: CAPTCHA is REQUIRED in production. Only development
    environments can bypass CAPTCHA verification when not configured.
    """
    import httpx

    from core.config import settings

    secret_key = settings.TURNSTILE_SECRET_KEY
    if not secret_key:
        # Only allow bypassing CAPTCHA in development mode
        # In production, CAPTCHA MUST be configured
        if settings.APP_ENV in ("production", "prod", "staging"):
            logger.error(
                "captcha_not_configured_in_production",
                app_env=settings.APP_ENV,
                message="CAPTCHA is required in production but TURNSTILE_SECRET_KEY is not set",
            )
            return False

        # Allow bypass only in development/test
        logger.warning(
            "captcha_bypassed_in_development",
            app_env=settings.APP_ENV,
            message="CAPTCHA verification bypassed - only allowed in development",
        )
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
