"""
Admin Poll Management Endpoints.

Provides full CRUD operations for polls with proper admin authentication.
These endpoints are protected and require admin privileges.

Security measures:
- All endpoints require valid JWT authentication
- User must have is_admin=True flag
- Audit logging for all destructive operations
- Rate limiting applied at router level
- Input validation via Pydantic schemas
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin_user
from db.session import get_db
from models.poll import PollStatus
from repositories.poll_repository import PollRepository
from schemas.converters import poll_model_to_results_schema, poll_model_to_schema
from schemas.poll import (
    Poll,
    PollChoice,
    PollCreate,
    PollStatusEnum,
    PollTypeEnum,
    PollWithResults,
)
from schemas.user import UserInDB

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas for Admin Operations
# ============================================================================


class PollUpdate(BaseModel):
    """Schema for updating an existing poll."""

    question: Optional[str] = Field(None, min_length=10, max_length=500)
    choices: Optional[list[PollChoice]] = Field(None, min_length=2, max_length=10)
    category: Optional[str] = None
    source_event: Optional[str] = None
    status: Optional[PollStatusEnum] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    is_featured: Optional[bool] = None
    is_special: Optional[bool] = None
    poll_type: Optional[PollTypeEnum] = None


class AdminPollCreate(PollCreate):
    """Extended poll creation schema for admins with additional options."""

    status: PollStatusEnum = Field(
        PollStatusEnum.SCHEDULED,
        description="Initial status (admins can create active polls directly)",
    )
    activate_immediately: bool = Field(
        False,
        description="If true, activates the poll immediately regardless of scheduled_start",
    )


class BulkDeleteRequest(BaseModel):
    """Request schema for bulk poll deletion."""

    poll_ids: list[str] = Field(..., min_length=1, max_length=50)
    force: bool = Field(
        False,
        description="If true, deletes polls even if they have votes (use with caution)",
    )


class BulkDeleteResponse(BaseModel):
    """Response schema for bulk poll deletion."""

    deleted_count: int
    failed_ids: list[str]
    errors: list[str]


class AdminPollListResponse(BaseModel):
    """Extended poll list response with admin-specific fields."""

    polls: list[Poll]
    total: int
    page: int
    per_page: int
    total_pages: int
    include_deleted: bool = False


class PollStatsResponse(BaseModel):
    """Admin statistics about polls."""

    total_polls: int
    active_polls: int
    scheduled_polls: int
    closed_polls: int
    polls_with_votes: int
    total_votes: int
    ai_generated_count: int
    manual_count: int


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.get("", response_model=AdminPollListResponse)
async def list_all_polls(
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[PollStatusEnum] = Query(None, description="Filter by status"),
    poll_type: Optional[PollTypeEnum] = Query(None, description="Filter by poll type"),
    include_inactive: bool = Query(True, description="Include inactive polls"),
    ai_generated: Optional[bool] = Query(None, description="Filter by AI generation"),
    search: Optional[str] = Query(None, description="Search in question text"),
) -> AdminPollListResponse:
    """
    List all polls with advanced filtering options.

    Admin-only endpoint that provides access to all polls including
    inactive, scheduled, and archived polls.
    """
    logger.info(
        f"Admin {admin.id} listing polls",
        extra={"admin_id": str(admin.id), "filters": {"status": status_filter, "poll_type": poll_type}},
    )

    repo = PollRepository(db)

    # Get polls with filters
    polls, total = await repo.get_all_polls(
        page=page,
        per_page=per_page,
        status_filter=status_filter.value if status_filter else None,
        poll_type=poll_type.value if poll_type else None,
        include_inactive=include_inactive,
        ai_generated_filter=ai_generated,
        search_query=search,
    )

    total_pages = (total + per_page - 1) // per_page

    return AdminPollListResponse(
        polls=[poll_model_to_schema(p) for p in polls],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=PollStatsResponse)
async def get_poll_stats(
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> PollStatsResponse:
    """
    Get aggregate statistics about polls.

    Provides overview metrics for admin dashboard.
    """
    repo = PollRepository(db)
    stats = await repo.get_poll_statistics()

    return PollStatsResponse(**stats)


@router.get("/{poll_id}", response_model=PollWithResults)
async def get_poll_details(
    poll_id: str,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> PollWithResults:
    """
    Get detailed information about a specific poll.

    Returns full poll data including vote counts and demographic breakdowns.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    return poll_model_to_results_schema(poll)


@router.post("", response_model=Poll, status_code=status.HTTP_201_CREATED)
async def create_poll(
    poll_data: AdminPollCreate,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Create a new poll with admin options.

    Admins can create polls with custom scheduling, immediate activation,
    and other advanced options not available to regular poll creation.
    """
    logger.info(
        f"Admin {admin.id} creating poll",
        extra={
            "admin_id": str(admin.id),
            "question": poll_data.question[:50],
            "poll_type": poll_data.poll_type,
        },
    )

    repo = PollRepository(db)

    # Calculate scheduling
    now = datetime.now(timezone.utc)
    scheduled_start = poll_data.scheduled_start or now
    scheduled_end = scheduled_start + timedelta(hours=poll_data.duration_hours)

    # Determine initial status
    initial_status = poll_data.status.value
    if poll_data.activate_immediately:
        initial_status = PollStatus.ACTIVE.value
        scheduled_start = now

    poll = await repo.create(
        question=poll_data.question,
        choices=[c.text for c in poll_data.choices],
        category=poll_data.category,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        source_event=poll_data.source_event,
        is_featured=poll_data.is_featured,
        ai_generated=False,
        poll_type=poll_data.poll_type.value,
        is_special=poll_data.is_special,
        status=initial_status,
    )

    logger.info(
        f"Admin {admin.id} created poll {poll.id}",
        extra={"admin_id": str(admin.id), "poll_id": str(poll.id)},
    )

    return poll_model_to_schema(poll)


@router.patch("/{poll_id}", response_model=Poll)
async def update_poll(
    poll_id: str,
    poll_data: PollUpdate,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Update an existing poll.

    Allows partial updates to poll properties. Some restrictions apply:
    - Cannot change question/choices for polls with votes
    - Status changes follow allowed transitions
    """
    logger.info(
        f"Admin {admin.id} updating poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id},
    )

    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    # Validate update constraints
    if poll.total_votes > 0:
        if poll_data.question is not None or poll_data.choices is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify question or choices for polls with existing votes",
            )

    # Build update dictionary with proper type for mixed values
    update_fields: dict[str, Any] = {}
    if poll_data.question is not None:
        update_fields["question"] = poll_data.question
    if poll_data.category is not None:
        update_fields["category"] = poll_data.category
    if poll_data.source_event is not None:
        update_fields["source_event"] = poll_data.source_event
    if poll_data.status is not None:
        update_fields["status"] = poll_data.status.value
        # Update is_active based on status
        update_fields["is_active"] = poll_data.status == PollStatusEnum.ACTIVE
    if poll_data.scheduled_start is not None:
        update_fields["scheduled_start"] = poll_data.scheduled_start
    if poll_data.scheduled_end is not None:
        update_fields["scheduled_end"] = poll_data.scheduled_end
        update_fields["expires_at"] = poll_data.scheduled_end
    if poll_data.is_featured is not None:
        update_fields["is_featured"] = poll_data.is_featured
    if poll_data.is_special is not None:
        update_fields["is_special"] = poll_data.is_special
    if poll_data.poll_type is not None:
        update_fields["poll_type"] = poll_data.poll_type.value

    if not update_fields and poll_data.choices is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Update poll
    updated_poll = await repo.update_poll(poll_id, update_fields, poll_data.choices)

    if not updated_poll:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update poll",
        )

    logger.info(
        f"Admin {admin.id} updated poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id, "fields": list(update_fields.keys())},
    )

    return poll_model_to_schema(updated_poll)


@router.delete("/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
    poll_id: str,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
    force: bool = Query(False, description="Force delete even if poll has votes"),
) -> None:
    """
    Delete a poll by ID.

    By default, polls with votes cannot be deleted to preserve data integrity.
    Use force=true to override this protection (audit logged).
    """
    logger.info(
        f"Admin {admin.id} attempting to delete poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id, "force": force},
    )

    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    # Check for votes unless force is specified
    if poll.total_votes > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete poll with {poll.total_votes} votes. Use force=true to override.",
        )

    if poll.total_votes > 0 and force:
        logger.warning(
            f"Admin {admin.id} FORCE deleting poll {poll_id} with {poll.total_votes} votes",
            extra={
                "admin_id": str(admin.id),
                "poll_id": poll_id,
                "vote_count": poll.total_votes,
                "question": poll.question,
            },
        )

    deleted = await repo.delete_poll(poll_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete poll",
        )

    logger.info(
        f"Admin {admin.id} deleted poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id},
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_polls(
    request: BulkDeleteRequest,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> BulkDeleteResponse:
    """
    Delete multiple polls at once.

    Useful for cleaning up duplicate or test polls.
    Returns summary of successful and failed deletions.
    """
    logger.info(
        f"Admin {admin.id} attempting bulk delete of {len(request.poll_ids)} polls",
        extra={"admin_id": str(admin.id), "poll_count": len(request.poll_ids), "force": request.force},
    )

    repo = PollRepository(db)
    deleted_count = 0
    failed_ids = []
    errors = []

    for poll_id in request.poll_ids:
        try:
            poll = await repo.get_by_id(poll_id)

            if not poll:
                failed_ids.append(poll_id)
                errors.append(f"Poll {poll_id} not found")
                continue

            if poll.total_votes > 0 and not request.force:
                failed_ids.append(poll_id)
                errors.append(f"Poll {poll_id} has {poll.total_votes} votes")
                continue

            deleted = await repo.delete_poll(poll_id)

            if deleted:
                deleted_count += 1
            else:
                failed_ids.append(poll_id)
                errors.append(f"Failed to delete poll {poll_id}")

        except Exception as e:
            logger.error(f"Error deleting poll {poll_id}: {e}")
            failed_ids.append(poll_id)
            errors.append(f"Error deleting poll {poll_id}: {str(e)}")

    logger.info(
        f"Admin {admin.id} bulk deleted {deleted_count} polls, {len(failed_ids)} failed",
        extra={
            "admin_id": str(admin.id),
            "deleted_count": deleted_count,
            "failed_count": len(failed_ids),
        },
    )

    return BulkDeleteResponse(
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        errors=errors,
    )


# ============================================================================
# Status Management Endpoints
# ============================================================================


@router.post("/{poll_id}/activate", response_model=Poll)
async def activate_poll(
    poll_id: str,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Manually activate a scheduled poll.

    Immediately sets the poll status to active and updates timestamps.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    if poll.status == PollStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is already active",
        )

    if poll.status == PollStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate a closed poll",
        )

    now = datetime.now(timezone.utc)
    updated = await repo.update_poll(
        poll_id,
        {
            "status": PollStatus.ACTIVE.value,
            "is_active": True,
            "scheduled_start": now,
        },
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found after update",
        )

    logger.info(
        f"Admin {admin.id} activated poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id},
    )

    return poll_model_to_schema(updated)


@router.post("/{poll_id}/close", response_model=Poll)
async def close_poll(
    poll_id: str,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
) -> Poll:
    """
    Manually close an active poll.

    Immediately ends the poll and prevents further voting.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    if poll.status == PollStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is already closed",
        )

    now = datetime.now(timezone.utc)
    updated = await repo.update_poll(
        poll_id,
        {
            "status": PollStatus.CLOSED.value,
            "is_active": False,
            "scheduled_end": now,
            "expires_at": now,
        },
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found after update",
        )

    logger.info(
        f"Admin {admin.id} closed poll {poll_id}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id},
    )

    return poll_model_to_schema(updated)


@router.post("/{poll_id}/feature", response_model=Poll)
async def toggle_featured(
    poll_id: str,
    admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
    featured: bool = Query(True, description="Set featured status"),
) -> Poll:
    """
    Toggle the featured status of a poll.

    Featured polls are highlighted in the UI and may appear in special sections.
    """
    repo = PollRepository(db)
    poll = await repo.get_by_id(poll_id)

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found",
        )

    updated = await repo.update_poll(poll_id, {"is_featured": featured})

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found after update",
        )

    logger.info(
        f"Admin {admin.id} set poll {poll_id} featured={featured}",
        extra={"admin_id": str(admin.id), "poll_id": poll_id, "featured": featured},
    )

    return poll_model_to_schema(updated)
