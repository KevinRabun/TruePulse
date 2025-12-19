"""
Poll management endpoints.

Implements the hourly poll rotation system where:
- New poll starts at the top of each hour
- Only authenticated users can vote
- Previous poll results shown on main page
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_verified_user
from core.config import settings
from db.session import get_db
from models.poll import Poll as PollModel, PollChoice as PollChoiceModel, PollStatus
from repositories.poll_repository import PollRepository
from schemas.poll import (
    Poll,
    PollCreate,
    PollListResponse,
    PollWithResults,
    PollChoice,
    PollChoiceWithResults,
    PollStatusEnum,
    PollTypeEnum,
)
from schemas.user import UserInDB

router = APIRouter()


def poll_model_to_schema(poll: PollModel) -> Poll:
    """Convert database model to Pydantic schema."""
    return Poll(
        id=str(poll.id),
        question=poll.question,
        choices=[
            PollChoice(id=str(c.id), text=c.text, order=c.order)
            for c in sorted(poll.choices, key=lambda x: x.order)
        ],
        category=poll.category,
        source_event=poll.source_event,
        status=PollStatusEnum(poll.status),
        created_at=poll.created_at,
        expires_at=poll.expires_at,
        scheduled_start=poll.scheduled_start,
        scheduled_end=poll.scheduled_end,
        is_active=poll.is_active,
        is_special=poll.is_special,
        duration_hours=poll.duration_hours,
        total_votes=poll.total_votes,
        is_featured=poll.is_featured,
        ai_generated=poll.ai_generated,
        poll_type=PollTypeEnum(poll.poll_type) if poll.poll_type else PollTypeEnum.STANDARD,
        time_remaining_seconds=poll.time_remaining_seconds,
    )


def poll_model_to_results_schema(poll: PollModel) -> PollWithResults:
    """Convert database model to results schema with vote counts."""
    total = poll.total_votes or 0
    
    return PollWithResults(
        id=str(poll.id),
        question=poll.question,
        choices=[
            PollChoiceWithResults(
                id=str(c.id),
                text=c.text,
                order=c.order,
                vote_count=c.vote_count,
                vote_percentage=(c.vote_count / total * 100) if total > 0 else 0.0,
            )
            for c in sorted(poll.choices, key=lambda x: x.order)
        ],
        category=poll.category,
        source_event=poll.source_event,
        status=PollStatusEnum(poll.status),
        created_at=poll.created_at,
        expires_at=poll.expires_at,
        scheduled_start=poll.scheduled_start,
        scheduled_end=poll.scheduled_end,
        is_active=poll.is_active,
        is_special=poll.is_special,
        duration_hours=poll.duration_hours,
        total_votes=total,
        is_featured=poll.is_featured,
        ai_generated=poll.ai_generated,
        poll_type=PollTypeEnum(poll.poll_type) if poll.poll_type else PollTypeEnum.STANDARD,
        time_remaining_seconds=poll.time_remaining_seconds,
        demographic_breakdown=poll.demographic_results,
        confidence_interval=poll.confidence_interval,
    )


# ============================================================================
# Current/Previous Poll Endpoints (Main Page)
# ============================================================================

@router.get("/current", response_model=Optional[Poll])
async def get_current_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[Poll]:
    """
    Get the currently active poll.
    
    This is the main poll displayed on the homepage that users can vote on.
    Polls rotate at the top of each hour (configurable via POLL_DURATION_HOURS).
    
    Returns:
        The current active poll, or None if no poll is active
    """
    repo = PollRepository(db)
    
    # Update poll statuses (close expired, activate scheduled)
    await repo.close_expired_polls()
    await repo.activate_scheduled_polls()
    
    poll = await repo.get_current_poll()
    if not poll:
        return None
    
    return poll_model_to_schema(poll)


@router.get("/previous", response_model=Optional[PollWithResults])
async def get_previous_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[PollWithResults]:
    """
    Get the most recently closed poll with its results.
    
    This is displayed on the main page to show what users voted on previously.
    
    Returns:
        The previous poll with aggregated results, or None
    """
    repo = PollRepository(db)
    poll = await repo.get_previous_poll()
    
    if not poll:
        return None
    
    return poll_model_to_results_schema(poll)


@router.get("/upcoming", response_model=list[Poll])
async def get_upcoming_polls(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[Poll]:
    """
    Get polls scheduled for future time windows.
    
    Shows users what polls are coming up next.
    """
    repo = PollRepository(db)
    polls = await repo.get_upcoming_polls(limit=limit)
    
    return [poll_model_to_schema(p) for p in polls]


# ============================================================================
# Pulse Poll Endpoints (Daily 12-hour polls, 8am-8pm ET)
# ============================================================================

@router.get("/pulse/current", response_model=Optional[Poll])
async def get_current_pulse_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[Poll]:
    """
    Get the current daily Pulse Poll if active.
    
    Pulse Polls run daily from 8am-8pm ET (12 hours).
    They are featured, high-visibility polls on important topics.
    
    Returns:
        The current Pulse Poll, or None if outside the 8am-8pm ET window
    """
    repo = PollRepository(db)
    
    # Update poll statuses
    await repo.close_expired_polls()
    await repo.activate_scheduled_polls()
    
    poll = await repo.get_current_poll_by_type("pulse")
    if not poll:
        return None
    
    return poll_model_to_schema(poll)


@router.get("/pulse/previous", response_model=Optional[PollWithResults])
async def get_previous_pulse_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[PollWithResults]:
    """
    Get the most recently closed Pulse Poll with results.
    """
    repo = PollRepository(db)
    poll = await repo.get_previous_poll_by_type("pulse")
    
    if not poll:
        return None
    
    return poll_model_to_results_schema(poll)


@router.get("/pulse/history", response_model=PollListResponse)
async def get_pulse_poll_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> PollListResponse:
    """
    Get historical Pulse Polls with results.
    """
    repo = PollRepository(db)
    polls, total = await repo.list_polls_by_type(
        poll_type="pulse",
        page=page,
        per_page=per_page,
        active_only=False,
    )
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    return PollListResponse(
        polls=[poll_model_to_schema(p) for p in polls],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# ============================================================================
# Flash Poll Endpoints (Quick 1-hour polls every 2-3 hours)
# ============================================================================

@router.get("/flash/current", response_model=Optional[Poll])
async def get_current_flash_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[Poll]:
    """
    Get the current Flash Poll if active.
    
    Flash Polls are quick 1-hour polls that run every 2-3 hours, 24/7.
    They cover breaking news and rapid-response topics.
    
    Returns:
        The current Flash Poll, or None if between flash polls
    """
    repo = PollRepository(db)
    
    # Update poll statuses
    await repo.close_expired_polls()
    await repo.activate_scheduled_polls()
    
    poll = await repo.get_current_poll_by_type("flash")
    if not poll:
        return None
    
    return poll_model_to_schema(poll)


@router.get("/flash/previous", response_model=Optional[PollWithResults])
async def get_previous_flash_poll(
    db: AsyncSession = Depends(get_db),
) -> Optional[PollWithResults]:
    """
    Get the most recently closed Flash Poll with results.
    """
    repo = PollRepository(db)
    poll = await repo.get_previous_poll_by_type("flash")
    
    if not poll:
        return None
    
    return poll_model_to_results_schema(poll)


@router.get("/flash/upcoming", response_model=list[Poll])
async def get_upcoming_flash_polls(
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> list[Poll]:
    """
    Get upcoming scheduled Flash Polls.
    """
    repo = PollRepository(db)
    polls = await repo.get_upcoming_polls_by_type("flash", limit=limit)
    
    return [poll_model_to_schema(p) for p in polls]


@router.get("/flash/history", response_model=PollListResponse)
async def get_flash_poll_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> PollListResponse:
    """
    Get historical Flash Polls.
    """
    repo = PollRepository(db)
    polls, total = await repo.list_polls_by_type(
        poll_type="flash",
        page=page,
        per_page=per_page,
        active_only=False,
    )
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    return PollListResponse(
        polls=[poll_model_to_schema(p) for p in polls],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# ============================================================================
# General Poll Endpoints
# ============================================================================

@router.get("", response_model=PollListResponse)
async def list_polls(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    active_only: bool = Query(True),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PollListResponse:
    """
    List available polls.
    
    Public endpoint - no authentication required.
    Returns paginated list of polls with basic information.
    """
    repo = PollRepository(db)
    polls, total = await repo.list_polls(
        page=page,
        per_page=per_page,
        active_only=active_only,
        category=category,
    )
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    return PollListResponse(
        polls=[poll_model_to_schema(p) for p in polls],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/daily", response_model=list[Poll])
async def get_daily_polls(
    db: AsyncSession = Depends(get_db),
) -> list[Poll]:
    """
    Get today's featured polls.
    
    Returns the curated set of daily polls generated from current events.
    """
    repo = PollRepository(db)
    
    # Get polls scheduled/active for today
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    polls, _ = await repo.list_polls(page=1, per_page=24, active_only=False)
    
    # Filter to today's polls
    daily = [
        p for p in polls
        if p.scheduled_start and today_start <= p.scheduled_start < today_end
    ]
    
    return [poll_model_to_schema(p) for p in daily]


@router.get("/{poll_id}", response_model=Poll)
async def get_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Get a specific poll by ID.
    
    Public endpoint - returns poll details without revealing individual votes.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )
    
    return poll_model_to_schema(poll)


@router.get("/{poll_id}/results", response_model=PollWithResults)
async def get_poll_results(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
) -> PollWithResults:
    """
    Get aggregated results for a poll.
    
    Public endpoint - returns percentage breakdown and total votes.
    Individual votes are never exposed.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )
    
    return poll_model_to_results_schema(poll)


@router.get("/{poll_id}/demographics")
async def get_poll_demographics(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get demographic breakdown of votes for a poll.
    
    Returns aggregated vote counts by demographic categories.
    Privacy-preserving: only returns counts, never individual votes.
    """
    from repositories.vote_repository import VoteRepository
    
    poll_repo = PollRepository(db)
    vote_repo = VoteRepository(db)
    
    poll = await poll_repo.get_by_id(poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )
    
    # Get raw demographic breakdown from votes
    raw_breakdown = await vote_repo.get_demographic_breakdown(poll_id)
    
    # Create choice lookup
    choice_lookup = {str(c.id): c.text for c in poll.choices}
    
    # Parse and aggregate by category
    demographics = {
        "age_range": {},
        "gender": {},
        "country": {},
        "state_province": {},
        "city": {},
        "education_level": {},
        "employment_status": {},
        "political_leaning": {},
    }
    
    for bucket, choice_counts in raw_breakdown.items():
        if not bucket or bucket == "unknown":
            continue
            
        # Parse bucket: "age_25-34|gender_male|country_US|state_California|city_Los Angeles"
        parts = bucket.split("|")
        for part in parts:
            if "_" not in part:
                continue
            # Split only on first underscore to handle values like "25-34" or "New York"
            prefix, value = part.split("_", 1)
            
            category_map = {
                "age": "age_range",
                "gender": "gender",
                "country": "country",
                "state": "state_province",
                "city": "city",
                "education": "education_level",
                "employment": "employment_status",
                "political": "political_leaning",
            }
            
            category = category_map.get(prefix)
            if not category:
                continue
            
            if value not in demographics[category]:
                demographics[category][value] = {
                    "total": 0,
                    "choices": {text: 0 for text in choice_lookup.values()}
                }
            
            for choice_id, count in choice_counts.items():
                choice_text = choice_lookup.get(choice_id, "Unknown")
                demographics[category][value]["total"] += count
                demographics[category][value]["choices"][choice_text] += count
    
    # Transform to frontend-friendly format
    result = {
        "poll_id": poll_id,
        "total_votes": poll.total_votes or 0,
        "breakdowns": []
    }
    
    category_labels = {
        "age_range": "Age Range",
        "gender": "Gender",
        "country": "Country",
        "state_province": "State/Province",
        "city": "City",
        "education_level": "Education",
        "employment_status": "Employment",
        "political_leaning": "Political Leaning",
    }
    
    for category, segments in demographics.items():
        if not segments:
            continue
            
        breakdown = {
            "category": category,
            "label": category_labels.get(category, category),
            "segments": []
        }
        
        for segment_name, data in segments.items():
            segment = {
                "name": segment_name,
                "votes": data["total"],
                "choices": [
                    {
                        "choice_text": choice_text,
                        "count": count,
                        "percentage": round(count / data["total"] * 100, 1) if data["total"] > 0 else 0
                    }
                    for choice_text, count in data["choices"].items()
                    if count > 0
                ]
            }
            breakdown["segments"].append(segment)
        
        if breakdown["segments"]:
            result["breakdowns"].append(breakdown)
    
    return result


@router.post("", response_model=Poll, status_code=status.HTTP_201_CREATED)
async def create_poll(
    poll_data: PollCreate,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Create a new poll (admin only).
    
    Note: Most polls are auto-generated by AI from current events.
    This endpoint is for manual poll creation by administrators.
    """
    # Check admin permissions
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    repo = PollRepository(db)
    
    # Calculate scheduling
    now = datetime.now(timezone.utc)
    scheduled_start = poll_data.scheduled_start or now
    scheduled_end = scheduled_start + timedelta(hours=poll_data.duration_hours)
    
    poll = await repo.create(
        question=poll_data.question,
        choices=[c.text for c in poll_data.choices],
        category=poll_data.category,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        source_event=poll_data.source_event,
        is_featured=poll_data.is_featured,
        ai_generated=False,
    )
    
    return poll_model_to_schema(poll)


@router.get("/categories/list", response_model=list[str])
async def list_categories() -> list[str]:
    """
    List available poll categories.
    """
    return [
        "Politics",
        "Technology",
        "Environment",
        "Economy",
        "Healthcare",
        "Education",
        "Entertainment",
        "Sports",
        "Science",
        "Workplace",
        "Social Issues",
        "International",
    ]
