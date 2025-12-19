"""
Vote management endpoints.

Implements privacy-preserving voting using cryptographic hashing.
Only authenticated users can vote, and only on currently active polls.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_verified_user
from core.security import generate_vote_hash
from db.session import get_db
from models.poll import PollStatus
from models.user_vote_history import UserVoteHistory
from repositories.poll_repository import PollRepository
from repositories.vote_repository import VoteRepository
from repositories.user_repository import UserRepository
from services.achievement_service import AchievementService
from schemas.user import UserInDB
from schemas.vote import VoteCreate, VoteResponse, VoteStatus

router = APIRouter()


def get_demographics_bucket(user: UserInDB) -> str | None:
    """
    Create an anonymized demographics bucket for aggregation.
    
    Format: "age_{range}|gender_{value}|country_{code}|state_{state}|city_{city}|education_{level}|employment_{status}|political_{leaning}"
    Only includes fields that the user has provided.
    Returns None if user hasn't opted in or no demographics available.
    """
    # Check if user has opted in to share anonymous demographics
    if not getattr(user, 'share_anonymous_demographics', True):
        return None
    
    parts = []
    
    if user.age_range:
        parts.append(f"age_{user.age_range}")
    if user.gender:
        parts.append(f"gender_{user.gender}")
    if user.country:
        parts.append(f"country_{user.country}")
    if user.state_province:
        parts.append(f"state_{user.state_province}")
    if user.city:
        parts.append(f"city_{user.city}")
    if user.education_level:
        parts.append(f"education_{user.education_level}")
    if user.employment_status:
        parts.append(f"employment_{user.employment_status}")
    if user.political_leaning:
        parts.append(f"political_{user.political_leaning}")
    
    return "|".join(parts) if parts else None


@router.post("", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def cast_vote(
    vote_data: VoteCreate,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    """
    Cast a vote on a poll.
    
    Requirements:
    - User must be authenticated (enforced by dependency)
    - Poll must be currently active (within voting window)
    - User cannot vote twice on the same poll
    
    Privacy-preserving implementation:
    1. Generate a one-way hash from user_id + poll_id
    2. Check if hash already exists (duplicate vote)
    3. Store only the hash and choice (not user_id)
    4. Update aggregated results
    5. Award gamification points
    
    The user_id is NEVER stored with the vote choice.
    """
    poll_repo = PollRepository(db)
    vote_repo = VoteRepository(db)
    user_repo = UserRepository(db)
    
    # Verify poll exists and is currently active
    poll = await poll_repo.get_by_id(vote_data.poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )
    
    # Check if poll is in active status and within voting window
    now = datetime.now(timezone.utc)
    if poll.status != PollStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This poll is not currently accepting votes",
        )
    
    if poll.scheduled_start and now < poll.scheduled_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This poll has not started yet",
        )
    
    if poll.scheduled_end and now >= poll.scheduled_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This poll has ended",
        )
    
    # Verify choice exists in this poll
    valid_choice_ids = [str(c.id) for c in poll.choices]
    if vote_data.choice_id not in valid_choice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid choice for this poll",
        )
    
    # Generate privacy-preserving vote hash
    vote_hash = generate_vote_hash(current_user.id, vote_data.poll_id)
    
    # Check for existing vote
    if await vote_repo.exists_by_hash(vote_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted on this poll",
        )
    
    # Store vote (hash + choice only, NO user_id)
    demographics_bucket = get_demographics_bucket(current_user)
    await vote_repo.create(
        vote_hash=vote_hash,
        poll_id=vote_data.poll_id,
        choice_id=vote_data.choice_id,
        demographics_bucket=demographics_bucket,
    )
    
    # Record in user's voting history (for activity tracking, NOT vote content)
    vote_history = UserVoteHistory(
        user_id=current_user.id,
        poll_id=vote_data.poll_id,
    )
    db.add(vote_history)
    
    # Update aggregated results
    await poll_repo.increment_vote_count(vote_data.poll_id, vote_data.choice_id)
    
    # Award gamification points (10 points per vote)
    points_earned = 10
    await user_repo.award_points(current_user.id, points_earned)
    await user_repo.increment_votes_cast(current_user.id)
    
    # Check and award achievements
    # Refresh user to get updated vote count and streak
    user = await user_repo.get_by_id(current_user.id)
    if user:
        achievement_service = AchievementService(db)
        await achievement_service.check_and_award_voting_achievements(user)
        await achievement_service.check_and_award_streak_achievements(user)
    
    return VoteResponse(
        success=True,
        message="Vote recorded successfully",
        points_earned=points_earned,
    )


@router.get("/status/{poll_id}", response_model=VoteStatus)
async def check_vote_status(
    poll_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> VoteStatus:
    """
    Check if the current user has voted on a poll.
    
    Uses the same hash mechanism to check without revealing vote choice.
    """
    vote_repo = VoteRepository(db)
    vote_hash = generate_vote_hash(current_user.id, poll_id)
    
    has_voted = await vote_repo.exists_by_hash(vote_hash)
    
    return VoteStatus(
        poll_id=poll_id,
        has_voted=has_voted,
    )


@router.delete("/{poll_id}")
async def retract_vote(
    poll_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Retract a vote from a poll (if allowed).
    
    Note: Vote retraction is only allowed while the poll is still active.
    """
    poll_repo = PollRepository(db)
    vote_repo = VoteRepository(db)
    
    # Verify poll exists
    poll = await poll_repo.get_by_id(poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )
    
    # Check if poll is still active (retraction only allowed during active voting)
    if poll.status != PollStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vote retraction is only allowed while the poll is active",
        )
    
    vote_hash = generate_vote_hash(current_user.id, poll_id)
    
    # Check if vote exists
    vote = await vote_repo.delete_by_hash(vote_hash)
    if not vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vote not found",
        )
    
    # Update aggregated results
    await poll_repo.decrement_vote_count(poll_id, vote.choice_id)
    
    return {"message": "Vote retracted successfully"}
