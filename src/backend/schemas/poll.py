"""
Poll-related Pydantic schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PollStatusEnum(str, Enum):
    """Poll lifecycle status."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class PollTypeEnum(str, Enum):
    """Type of poll with different durations and behaviors."""

    PULSE = "pulse"  # Daily poll, 12 hours (8am-8pm ET)
    FLASH = "flash"  # Quick poll, 1 hour duration, every 2-3 hours
    STANDARD = "standard"  # Regular hourly polls


class PollChoice(BaseModel):
    """A single choice option in a poll."""

    id: str
    text: str
    order: int = 0
    vote_count: Optional[int] = Field(None, description="Vote count (included in closed poll results)")


class PollChoiceWithResults(PollChoice):
    """Poll choice with aggregated vote results."""

    vote_count: int = 0
    vote_percentage: float = 0.0


class PollBase(BaseModel):
    """Base poll schema."""

    question: str = Field(..., min_length=10, max_length=500)
    choices: list[PollChoice] = Field(..., min_length=2, max_length=10)
    category: str
    source_event: Optional[str] = Field(None, description="The current event that inspired this poll")
    source_event_url: Optional[str] = Field(None, description="URL to the source article")


class PollCreate(PollBase):
    """Schema for creating a new poll."""

    duration_hours: int = Field(1, ge=1, le=168)  # 1 hour to 1 week (default: 1 hour)
    scheduled_start: Optional[datetime] = Field(
        None, description="When to start the poll (defaults to next available slot)"
    )
    is_featured: bool = False
    is_special: bool = Field(False, description="Special polls can have custom durations beyond the standard")
    poll_type: PollTypeEnum = Field(
        PollTypeEnum.STANDARD,
        description="Type of poll: pulse (12hr), flash (1hr), or standard",
    )


class Poll(PollBase):
    """Schema for poll responses."""

    id: str
    status: PollStatusEnum = PollStatusEnum.SCHEDULED
    created_at: datetime
    expires_at: datetime
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    is_active: bool
    is_special: bool = False
    duration_hours: int = 1
    total_votes: int = 0
    is_featured: bool = False
    ai_generated: bool = False
    poll_type: PollTypeEnum = PollTypeEnum.STANDARD
    time_remaining_seconds: Optional[int] = Field(None, description="Seconds remaining until poll closes")

    model_config = {"from_attributes": True}


class PollWithResults(BaseModel):
    """Poll with aggregated voting results."""

    id: str
    question: str
    choices: list[PollChoiceWithResults]
    category: str
    source_event: Optional[str] = None
    source_event_url: Optional[str] = None
    status: PollStatusEnum = PollStatusEnum.CLOSED
    created_at: datetime
    expires_at: datetime
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    is_active: bool = False
    is_special: bool = False
    duration_hours: int = 1
    total_votes: int = 0
    is_featured: bool = False
    ai_generated: bool = False
    poll_type: PollTypeEnum = PollTypeEnum.STANDARD
    time_remaining_seconds: Optional[int] = None
    demographic_breakdown: Optional[dict] = Field(
        None, description="Aggregated results by demographic (if sufficient data)"
    )
    confidence_interval: Optional[float] = Field(None, description="Statistical confidence interval for results")

    model_config = {"from_attributes": True}


class PollListResponse(BaseModel):
    """Paginated list of polls."""

    polls: list[Poll]
    total: int
    page: int
    per_page: int
    total_pages: int


class DailyPollSet(BaseModel):
    """A set of daily featured polls."""

    date: datetime
    polls: list[Poll]
    theme: Optional[str] = None
