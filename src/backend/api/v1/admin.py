"""
Admin endpoints for system management.

These endpoints require admin authentication and are used for:
- Manual poll rotation triggers
- Poll generation triggers
- System health checks
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user
from schemas.user import UserInDB

router = APIRouter()


class RotationResult(BaseModel):
    """Result of a poll rotation cycle."""

    closed_count: int
    activated_count: int
    generated_poll: dict | None = None


class GenerationResult(BaseModel):
    """Result of a poll generation attempt."""

    success: bool
    poll_id: str | None = None
    question: str | None = None
    scheduled_start: str | None = None
    error: str | None = None


class SchedulerStatus(BaseModel):
    """Status of the background scheduler."""

    running: bool
    jobs: list[dict]


def require_admin(current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserInDB:
    """Dependency to require admin access."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/poll-rotation", response_model=RotationResult)
async def trigger_poll_rotation(
    _admin: Annotated[UserInDB, Depends(require_admin)],
) -> RotationResult:
    """
    Manually trigger a poll rotation cycle.

    This will:
    1. Close any expired polls
    2. Activate any scheduled polls whose time has come
    3. Generate new polls from current events if needed

    Requires admin authentication.
    """
    from services.background_scheduler import trigger_poll_rotation

    result = await trigger_poll_rotation()

    return RotationResult(
        closed_count=result.get("closed_count", 0),
        activated_count=result.get("activated_count", 0),
        generated_poll={"id": result["generated_poll"].id, "question": result["generated_poll"].question}
        if result.get("generated_poll")
        else None,
    )


@router.post("/poll-generation", response_model=GenerationResult)
async def trigger_poll_generation(
    _admin: Annotated[UserInDB, Depends(require_admin)],
) -> GenerationResult:
    """
    Manually trigger poll generation from current events.

    This will:
    1. Fetch trending news events
    2. Generate an unbiased poll question using AI
    3. Schedule the poll for the next available window

    Requires admin authentication.
    """
    from services.background_scheduler import trigger_poll_generation

    result = await trigger_poll_generation()

    return GenerationResult(**result)


@router.get("/scheduler-status", response_model=SchedulerStatus)
async def get_scheduler_status(
    _admin: Annotated[UserInDB, Depends(require_admin)],
) -> SchedulerStatus:
    """
    Get the status of the background scheduler.

    Returns information about:
    - Whether the scheduler is running
    - List of scheduled jobs and their next run times

    Requires admin authentication.
    """
    from services.background_scheduler import get_scheduler

    scheduler = get_scheduler()

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )

    return SchedulerStatus(
        running=scheduler.running,
        jobs=jobs,
    )


@router.post("/fix-poll-types")
async def fix_poll_types() -> dict:
    """
    One-time fix to convert standard polls to pulse type.
    No auth required for initial setup - remove after use.
    """
    from sqlalchemy import update

    from db.session import get_db_session
    from models.poll import Poll

    async with get_db_session() as db:
        result = await db.execute(
            update(Poll).where(Poll.poll_type == "standard").values(poll_type="pulse")
        )
        await db.commit()
        return {"updated": result.rowcount}
