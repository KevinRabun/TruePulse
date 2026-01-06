"""
Poll feedback endpoints.

Allows users to submit feedback on poll quality to improve AI generation.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_verified_user
from core.security import generate_vote_hash
from db.session import get_db
from repositories.feedback_repository import FeedbackRepository
from repositories.poll_repository import PollRepository
from schemas.feedback import (
    ISSUE_DESCRIPTIONS,
    FeedbackIssueInfo,
    FeedbackIssuesListResponse,
    FeedbackIssueType,
    FeedbackResponse,
    FeedbackSubmit,
    PollFeedbackSummary,
)
from schemas.user import UserInDB

router = APIRouter()


@router.get("/issues", response_model=FeedbackIssuesListResponse)
async def list_feedback_issues() -> FeedbackIssuesListResponse:
    """
    Get list of all available feedback issue types.

    Returns descriptions for each issue type to display in the UI.
    """
    issues = []

    # Categorize issues
    issue_categories = {
        FeedbackIssueType.ANSWERS_DONT_MATCH_ARTICLE: "content",
        FeedbackIssueType.TEMPORAL_CONFUSION: "content",
        FeedbackIssueType.MISSING_CONTEXT: "content",
        FeedbackIssueType.BIASED_QUESTION: "bias",
        FeedbackIssueType.LEADING_LANGUAGE: "bias",
        FeedbackIssueType.POLITICAL_SLANT: "bias",
        FeedbackIssueType.CHOICES_TOO_SIMILAR: "choices",
        FeedbackIssueType.MISSING_VIEWPOINT: "choices",
        FeedbackIssueType.TOO_FEW_CHOICES: "choices",
        FeedbackIssueType.UNCLEAR_CHOICES: "choices",
        FeedbackIssueType.TOO_LOCAL: "relevance",
        FeedbackIssueType.NOT_NEWSWORTHY: "relevance",
        FeedbackIssueType.OUTDATED_TOPIC: "relevance",
        FeedbackIssueType.OTHER: "other",
    }

    for issue_type in FeedbackIssueType:
        issues.append(
            FeedbackIssueInfo(
                issue_type=issue_type,
                description=ISSUE_DESCRIPTIONS[issue_type],
                category=issue_categories.get(issue_type, "other"),
            )
        )

    return FeedbackIssuesListResponse(issues=issues)


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: FeedbackSubmit,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit feedback on a poll's quality.

    Requirements:
    - User must be authenticated
    - User must have voted on this poll
    - User can only submit feedback once per poll

    The feedback is linked to the user's vote using the same privacy-preserving
    hash, ensuring anonymity while preventing duplicate submissions.
    """
    poll_repo = PollRepository(db)
    feedback_repo = FeedbackRepository(db)

    # Verify poll exists
    poll = await poll_repo.get_by_id(feedback_data.poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    # Generate the same vote hash used for voting
    vote_hash = generate_vote_hash(str(current_user.id), feedback_data.poll_id)

    # Check if user already submitted feedback
    existing = await feedback_repo.get_feedback_by_vote_hash(
        feedback_data.poll_id, vote_hash
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted feedback for this poll",
        )

    # Convert issues enum to string list for storage
    issues_list = None
    if feedback_data.issues:
        issues_list = [issue.value for issue in feedback_data.issues]

    # Create feedback
    try:
        feedback = await feedback_repo.create_feedback(
            poll_id=feedback_data.poll_id,
            vote_hash=vote_hash,
            quality_rating=feedback_data.quality_rating,
            issues=issues_list,
            feedback_text=feedback_data.feedback_text,
            poll_category=poll.category,
            was_ai_generated=poll.ai_generated,
        )
        await db.commit()

        # Convert issues back to enum for response
        response_issues = None
        if feedback.issues:
            response_issues = [FeedbackIssueType(i) for i in feedback.issues]

        return FeedbackResponse(
            id=feedback.id,
            poll_id=feedback.poll_id,
            quality_rating=feedback.quality_rating,
            issues=response_issues,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at,
            message="Thank you for your feedback! It helps us improve poll quality.",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/{poll_id}/summary", response_model=PollFeedbackSummary)
async def get_poll_feedback_summary(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
) -> PollFeedbackSummary:
    """
    Get aggregated feedback summary for a poll.

    This is a public endpoint that shows aggregate statistics
    without revealing individual feedback.
    """
    poll_repo = PollRepository(db)
    feedback_repo = FeedbackRepository(db)

    # Verify poll exists
    poll = await poll_repo.get_by_id(poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    summary = await feedback_repo.get_poll_feedback_summary(poll_id)

    return PollFeedbackSummary(**summary)


@router.get("/{poll_id}/my-feedback", response_model=FeedbackResponse)
async def get_my_feedback(
    poll_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """
    Get the current user's feedback for a specific poll.

    Returns 404 if user hasn't submitted feedback for this poll.
    """
    poll_repo = PollRepository(db)
    feedback_repo = FeedbackRepository(db)

    # Verify poll exists
    poll = await poll_repo.get_by_id(poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    vote_hash = generate_vote_hash(str(current_user.id), poll_id)
    feedback = await feedback_repo.get_feedback_by_vote_hash(poll_id, vote_hash)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't submitted feedback for this poll",
        )

    # Convert issues to enum for response
    response_issues = None
    if feedback.issues:
        response_issues = [FeedbackIssueType(i) for i in feedback.issues]

    return FeedbackResponse(
        id=feedback.id,
        poll_id=feedback.poll_id,
        quality_rating=feedback.quality_rating,
        issues=response_issues,
        feedback_text=feedback.feedback_text,
        created_at=feedback.created_at,
        message="",
    )
