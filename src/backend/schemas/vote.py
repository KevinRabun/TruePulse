"""
Vote-related Pydantic schemas.

These schemas handle the privacy-preserving voting system.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VoteCreate(BaseModel):
    """Schema for casting a vote."""

    poll_id: str
    choice_id: str


class VoteResponse(BaseModel):
    """Response after successfully casting a vote."""

    success: bool
    message: str
    points_earned: int = 0


class VoteStatus(BaseModel):
    """Check if user has voted on a poll (without revealing choice)."""

    poll_id: str
    has_voted: bool


class VoteRecord(BaseModel):
    """
    Internal vote record (stored in Cosmos DB).

    PRIVACY NOTE: This record does NOT contain user_id.
    The vote_hash is a one-way hash that cannot be reversed
    to identify the voter.
    """

    id: str  # Cosmos DB document ID
    vote_hash: str = Field(
        ..., description="SHA-256 hash of user_id + poll_id (cannot be reversed)"
    )
    poll_id: str
    choice_id: str
    demographics_bucket: Optional[str] = Field(
        None, description="Anonymized demographic bucket for aggregation"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class AggregatedVoteResult(BaseModel):
    """Aggregated vote results for a poll choice."""

    choice_id: str
    choice_text: str
    vote_count: int
    vote_percentage: float
    demographic_breakdown: Optional[dict] = Field(
        None, description="Breakdown by demographic buckets (min threshold applies)"
    )
