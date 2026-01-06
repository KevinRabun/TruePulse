"""
Poll Feedback Pydantic schemas.

Schemas for submitting and retrieving poll quality feedback.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FeedbackIssueType(str, Enum):
    """Specific quality issues users can flag."""

    # Content alignment issues
    ANSWERS_DONT_MATCH_ARTICLE = "answers_dont_match_article"
    TEMPORAL_CONFUSION = "temporal_confusion"
    MISSING_CONTEXT = "missing_context"

    # Bias and framing issues
    BIASED_QUESTION = "biased_question"
    LEADING_LANGUAGE = "leading_language"
    POLITICAL_SLANT = "political_slant"

    # Choice quality issues
    CHOICES_TOO_SIMILAR = "choices_too_similar"
    MISSING_VIEWPOINT = "missing_viewpoint"
    TOO_FEW_CHOICES = "too_few_choices"
    UNCLEAR_CHOICES = "unclear_choices"

    # Topic relevance
    TOO_LOCAL = "too_local"
    NOT_NEWSWORTHY = "not_newsworthy"
    OUTDATED_TOPIC = "outdated_topic"

    # Other
    OTHER = "other"


# Human-readable descriptions for each issue type
ISSUE_DESCRIPTIONS: dict[FeedbackIssueType, str] = {
    FeedbackIssueType.ANSWERS_DONT_MATCH_ARTICLE: "The answer choices don't align with the article content",
    FeedbackIssueType.TEMPORAL_CONFUSION: "The poll confuses past events with present (e.g., treats a historical story as current)",
    FeedbackIssueType.MISSING_CONTEXT: "Important context from the article is missing",
    FeedbackIssueType.BIASED_QUESTION: "The question seems biased or one-sided",
    FeedbackIssueType.LEADING_LANGUAGE: "The wording leads respondents toward a particular answer",
    FeedbackIssueType.POLITICAL_SLANT: "The poll has an obvious political slant",
    FeedbackIssueType.CHOICES_TOO_SIMILAR: "The answer choices are too similar to each other",
    FeedbackIssueType.MISSING_VIEWPOINT: "An important viewpoint is missing from the choices",
    FeedbackIssueType.TOO_FEW_CHOICES: "There aren't enough answer options",
    FeedbackIssueType.UNCLEAR_CHOICES: "The answer choices are unclear or confusing",
    FeedbackIssueType.TOO_LOCAL: "The topic is too local/regional for a general audience",
    FeedbackIssueType.NOT_NEWSWORTHY: "The topic isn't significant enough to be a poll",
    FeedbackIssueType.OUTDATED_TOPIC: "The topic is outdated or no longer relevant",
    FeedbackIssueType.OTHER: "Other issue (please describe)",
}


class FeedbackSubmit(BaseModel):
    """Schema for submitting poll quality feedback."""

    poll_id: str = Field(..., description="The poll being rated")
    quality_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall quality rating (1=poor, 5=excellent)",
    )
    issues: Optional[list[FeedbackIssueType]] = Field(
        None,
        max_length=5,
        description="Specific issues identified (max 5)",
    )
    feedback_text: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional free-form feedback (max 500 chars)",
    )

    @field_validator("issues")
    @classmethod
    def validate_issues(cls, v: Optional[list[FeedbackIssueType]]) -> Optional[list[FeedbackIssueType]]:
        """Ensure issues are unique and valid."""
        if v is None:
            return v
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for issue in v:
            if issue not in seen:
                seen.add(issue)
                unique.append(issue)
        return unique


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    id: str
    poll_id: str
    quality_rating: int
    issues: Optional[list[FeedbackIssueType]] = None
    feedback_text: Optional[str] = None
    created_at: datetime
    message: str = "Thank you for your feedback!"

    model_config = {"from_attributes": True}


class FeedbackIssueInfo(BaseModel):
    """Information about a feedback issue type."""

    issue_type: FeedbackIssueType
    description: str
    category: str  # "content", "bias", "choices", "relevance", "other"


class FeedbackIssuesListResponse(BaseModel):
    """List of all available feedback issue types."""

    issues: list[FeedbackIssueInfo]


class PollFeedbackSummary(BaseModel):
    """Summary of feedback for a specific poll."""

    poll_id: str
    total_feedback_count: int
    average_rating: float = Field(..., description="Average rating (1.0-5.0)")
    rating_distribution: dict[int, int] = Field(
        ...,
        description="Count of each rating (1-5)",
    )
    top_issues: list[dict[str, int | str]] = Field(
        ...,
        description="Most common issues with counts",
    )
    has_sufficient_feedback: bool = Field(
        ...,
        description="Whether there's enough feedback for reliable insights (min 10)",
    )


class CategoryFeedbackSummary(BaseModel):
    """Summary of feedback patterns for a category."""

    category: str
    total_polls_analyzed: int
    average_rating: float
    common_issues: list[dict[str, float | str]] = Field(
        ...,
        description="Common issues with frequency percentages",
    )
    improvement_suggestions: list[str] = Field(
        ...,
        description="AI-derived suggestions for improving this category",
    )


class FeedbackStatsResponse(BaseModel):
    """Overall feedback statistics for admin/analysis."""

    total_feedback_count: int
    average_rating_overall: float
    feedback_by_category: dict[str, CategoryFeedbackSummary]
    most_common_issues_global: list[dict[str, int | str]]
    recent_low_rated_polls: list[str] = Field(
        ...,
        description="Poll IDs with recent low ratings for review",
    )


class UserFeedbackHistory(BaseModel):
    """A user's feedback history (limited view for privacy)."""

    total_feedback_given: int
    average_rating_given: float
    recent_feedback: list[FeedbackResponse]
