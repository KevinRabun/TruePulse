"""
Poll Feedback repository for database operations.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.poll import Poll
from models.poll_feedback import (
    CategoryFeedbackPattern,
    FeedbackAggregate,
    PollFeedback,
)


class FeedbackRepository:
    """Repository for poll feedback database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feedback(
        self,
        poll_id: str,
        vote_hash: str,
        quality_rating: int,
        issues: Optional[list[str]] = None,
        feedback_text: Optional[str] = None,
        poll_category: Optional[str] = None,
        was_ai_generated: bool = True,
    ) -> PollFeedback:
        """
        Create a new feedback record.

        Args:
            poll_id: ID of the poll being rated
            vote_hash: Privacy-preserving hash identifying the user
            quality_rating: 1-5 star rating
            issues: List of FeedbackIssueType values
            feedback_text: Optional free-form feedback
            poll_category: Category of the poll (denormalized)
            was_ai_generated: Whether the poll was AI-generated

        Returns:
            Created feedback record

        Raises:
            ValueError: If user has already submitted feedback for this poll
        """
        # Check if user already submitted feedback for this poll
        existing = await self.get_feedback_by_vote_hash(poll_id, vote_hash)
        if existing:
            raise ValueError("You have already submitted feedback for this poll")

        feedback = PollFeedback(
            id=str(uuid4()),
            poll_id=poll_id,
            vote_hash=vote_hash,
            quality_rating=quality_rating,
            issues=issues,
            feedback_text=feedback_text,
            poll_category=poll_category,
            was_ai_generated=was_ai_generated,
        )
        self.db.add(feedback)
        await self.db.flush()

        # Update aggregates asynchronously
        await self._update_poll_aggregate(poll_id)

        return feedback

    async def get_feedback_by_vote_hash(
        self,
        poll_id: str,
        vote_hash: str,
    ) -> Optional[PollFeedback]:
        """Get feedback by poll and vote hash (check if user already submitted)."""
        result = await self.db.execute(
            select(PollFeedback).where(
                and_(
                    PollFeedback.poll_id == poll_id,
                    PollFeedback.vote_hash == vote_hash,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_poll_feedback_summary(
        self,
        poll_id: str,
    ) -> dict:
        """
        Get aggregated feedback summary for a poll.

        Returns dict with:
        - total_feedback_count
        - average_rating
        - rating_distribution
        - top_issues
        """
        # Get all feedback for this poll
        result = await self.db.execute(
            select(PollFeedback).where(PollFeedback.poll_id == poll_id)
        )
        feedback_list = list(result.scalars().all())

        if not feedback_list:
            return {
                "poll_id": poll_id,
                "total_feedback_count": 0,
                "average_rating": 0.0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "top_issues": [],
                "has_sufficient_feedback": False,
            }

        # Calculate metrics
        total = len(feedback_list)
        avg_rating = sum(f.quality_rating for f in feedback_list) / total

        # Rating distribution
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedback_list:
            rating_dist[f.quality_rating] += 1

        # Issue frequency
        issue_counts: dict[str, int] = defaultdict(int)
        for f in feedback_list:
            if f.issues:
                for issue in f.issues:
                    issue_counts[issue] += 1

        # Sort issues by frequency
        top_issues = [
            {"issue": issue, "count": count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:5]
        ]

        return {
            "poll_id": poll_id,
            "total_feedback_count": total,
            "average_rating": round(avg_rating, 2),
            "rating_distribution": rating_dist,
            "top_issues": top_issues,
            "has_sufficient_feedback": total >= 10,
        }

    async def get_category_feedback_patterns(
        self,
        category: str,
    ) -> Optional[CategoryFeedbackPattern]:
        """Get learned feedback patterns for a category."""
        result = await self.db.execute(
            select(CategoryFeedbackPattern).where(
                CategoryFeedbackPattern.category == category
            )
        )
        return result.scalar_one_or_none()

    async def get_feedback_context_for_generation(
        self,
        category: str,
        lookback_days: int = 30,
    ) -> dict:
        """
        Get feedback context to improve poll generation.

        This aggregates recent feedback patterns to inform the AI
        about common issues to avoid.

        Returns:
            Dictionary with:
            - average_rating: Recent average for this category
            - common_issues: Issues that appear frequently
            - specific_guidance: Specific instructions based on patterns
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Get recent feedback for this category
        result = await self.db.execute(
            select(PollFeedback).where(
                and_(
                    PollFeedback.poll_category == category,
                    PollFeedback.created_at >= cutoff,
                    PollFeedback.was_ai_generated == True,
                )
            )
        )
        feedback_list = list(result.scalars().all())

        if len(feedback_list) < 5:
            # Not enough data for meaningful patterns
            return {
                "has_patterns": False,
                "average_rating": None,
                "common_issues": [],
                "specific_guidance": [],
            }

        # Calculate average rating
        avg_rating = sum(f.quality_rating for f in feedback_list) / len(feedback_list)

        # Count issues
        issue_counts: dict[str, int] = defaultdict(int)
        for f in feedback_list:
            if f.issues:
                for issue in f.issues:
                    issue_counts[issue] += 1

        total_feedback = len(feedback_list)
        common_issues = [
            {"issue": issue, "frequency": count / total_feedback}
            for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1])
            if count / total_feedback >= 0.1  # At least 10% occurrence
        ]

        # Generate specific guidance based on common issues
        guidance = self._generate_guidance_from_issues(common_issues)

        return {
            "has_patterns": True,
            "average_rating": round(avg_rating, 2),
            "common_issues": common_issues,
            "specific_guidance": guidance,
        }

    def _generate_guidance_from_issues(
        self,
        common_issues: list[dict],
    ) -> list[str]:
        """Generate specific guidance based on common issues."""
        guidance = []

        issue_to_guidance = {
            "temporal_confusion": (
                "TEMPORAL AWARENESS: Pay close attention to whether the article "
                "describes past events, current events, or future predictions. "
                "Frame questions appropriately - use past tense for historical events, "
                "and don't ask 'what should happen' about events that already occurred."
            ),
            "answers_dont_match_article": (
                "CONTENT ALIGNMENT: Ensure all answer choices directly relate to the "
                "specific content of the article. Don't introduce viewpoints or angles "
                "that aren't mentioned or implied in the source material."
            ),
            "missing_context": (
                "CONTEXT INCLUSION: Include relevant context from the article in the "
                "question to help respondents understand what's being asked without "
                "needing to read the full article."
            ),
            "biased_question": (
                "NEUTRALITY CHECK: Review the question for any loaded words, assumptions, "
                "or framing that could bias responses. Phrase questions to allow for "
                "genuine opinion variation."
            ),
            "leading_language": (
                "NEUTRAL LANGUAGE: Avoid words with strong positive or negative connotations. "
                "Use neutral, objective phrasing that doesn't suggest a 'correct' answer."
            ),
            "political_slant": (
                "POLITICAL BALANCE: Ensure the question and choices represent multiple "
                "political viewpoints fairly. Include moderate/centrist options."
            ),
            "choices_too_similar": (
                "CHOICE DIVERSITY: Ensure answer choices are meaningfully distinct from "
                "each other. Each choice should represent a clearly different position."
            ),
            "missing_viewpoint": (
                "COMPREHENSIVE OPTIONS: Consider all major viewpoints on the topic and "
                "ensure they're represented in the choices. Include 'Other' or "
                "'Undecided' options when appropriate."
            ),
            "unclear_choices": (
                "CLARITY: Use simple, clear language in answer choices. Avoid jargon, "
                "double negatives, or complex phrasing that could confuse respondents."
            ),
            "too_local": (
                "BROADER FRAMING: If the event is local, frame the question around the "
                "broader national or universal issue it represents rather than the "
                "specific local incident."
            ),
        }

        for issue_data in common_issues:
            issue = issue_data["issue"]
            if issue in issue_to_guidance:
                guidance.append(issue_to_guidance[issue])

        return guidance

    async def _update_poll_aggregate(self, poll_id: str) -> None:
        """Update the aggregate statistics for a poll."""
        summary = await self.get_poll_feedback_summary(poll_id)

        # Check if aggregate exists
        result = await self.db.execute(
            select(FeedbackAggregate).where(FeedbackAggregate.poll_id == poll_id)
        )
        aggregate = result.scalar_one_or_none()

        # Find most common issue
        most_common = None
        if summary["top_issues"]:
            most_common = summary["top_issues"][0]["issue"]

        # Convert issue list to counts dict
        issue_counts = {
            item["issue"]: item["count"]
            for item in summary["top_issues"]
        }

        if aggregate:
            # Update existing
            aggregate.total_feedback_count = summary["total_feedback_count"]
            aggregate.average_rating = int(summary["average_rating"] * 100)
            aggregate.issue_counts = issue_counts
            aggregate.most_common_issue = most_common
        else:
            # Create new
            aggregate = FeedbackAggregate(
                id=str(uuid4()),
                poll_id=poll_id,
                total_feedback_count=summary["total_feedback_count"],
                average_rating=int(summary["average_rating"] * 100),
                issue_counts=issue_counts,
                most_common_issue=most_common,
            )
            self.db.add(aggregate)

    async def get_low_rated_polls(
        self,
        max_rating: float = 2.5,
        limit: int = 10,
        days_back: int = 7,
    ) -> list[dict]:
        """Get recently low-rated polls for review."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        result = await self.db.execute(
            select(FeedbackAggregate)
            .where(
                and_(
                    FeedbackAggregate.average_rating <= int(max_rating * 100),
                    FeedbackAggregate.total_feedback_count >= 5,
                    FeedbackAggregate.updated_at >= cutoff,
                )
            )
            .order_by(FeedbackAggregate.average_rating.asc())
            .limit(limit)
        )
        aggregates = list(result.scalars().all())

        return [
            {
                "poll_id": a.poll_id,
                "average_rating": a.average_rating / 100,
                "feedback_count": a.total_feedback_count,
                "top_issue": a.most_common_issue,
            }
            for a in aggregates
        ]

    async def update_category_patterns(self, category: str) -> None:
        """
        Update learned patterns for a category based on accumulated feedback.

        This should be called periodically (e.g., daily) to refresh patterns.
        """
        context = await self.get_feedback_context_for_generation(category, lookback_days=90)

        if not context["has_patterns"]:
            return

        # Get or create pattern record
        result = await self.db.execute(
            select(CategoryFeedbackPattern).where(
                CategoryFeedbackPattern.category == category
            )
        )
        pattern = result.scalar_one_or_none()

        # Count total polls in this category
        poll_count_result = await self.db.execute(
            select(func.count(Poll.id)).where(Poll.category == category)
        )
        total_polls = poll_count_result.scalar() or 0

        # Extract top issues
        top_issues = [item["issue"] for item in context["common_issues"][:3]]

        # Build issue frequencies
        issue_frequencies = {
            item["issue"]: round(item["frequency"] * 100, 1)
            for item in context["common_issues"]
        }

        if pattern:
            pattern.total_polls_analyzed = total_polls
            pattern.average_rating = int((context["average_rating"] or 0) * 100)
            pattern.issue_frequencies = issue_frequencies
            pattern.top_issues = top_issues
            pattern.learned_adjustments = {"guidance": context["specific_guidance"]}
        else:
            pattern = CategoryFeedbackPattern(
                id=str(uuid4()),
                category=category,
                total_polls_analyzed=total_polls,
                average_rating=int((context["average_rating"] or 0) * 100),
                issue_frequencies=issue_frequencies,
                top_issues=top_issues,
                learned_adjustments={"guidance": context["specific_guidance"]},
            )
            self.db.add(pattern)

    async def get_user_feedback_count(self, vote_hash: str) -> int:
        """Get the number of feedback submissions by a user."""
        result = await self.db.execute(
            select(func.count(PollFeedback.id)).where(
                PollFeedback.vote_hash == vote_hash
            )
        )
        return result.scalar() or 0
