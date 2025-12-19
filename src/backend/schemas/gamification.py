"""
Gamification-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProgress(BaseModel):
    """User's gamification progress."""
    user_id: str
    total_points: int
    level: int
    level_name: str
    points_to_next_level: int
    current_streak: int
    longest_streak: int
    votes_cast: int
    polls_participated: int


class Achievement(BaseModel):
    """A gamification achievement/badge."""
    id: str
    name: str
    description: str
    icon: str
    points_reward: int
    is_unlocked: bool
    unlocked_at: Optional[datetime]
    progress: int
    target: int


class AchievementEarnedDate(BaseModel):
    """Record of when a repeatable achievement was earned."""
    earned_at: datetime
    period_key: Optional[str] = None  # e.g., "2025-01-15" for daily, "2025-01" for monthly


class AchievementWithHistory(BaseModel):
    """Achievement with full earn history for repeatable achievements."""
    id: str
    name: str
    description: str
    icon: str
    points_reward: int
    is_unlocked: bool
    unlocked_at: Optional[datetime]
    progress: int
    target: int
    tier: Optional[str] = None  # bronze, silver, gold, platinum
    category: Optional[str] = None  # voting, streak, profile, leaderboard
    is_repeatable: bool = False
    times_earned: int = 0
    earned_history: list[AchievementEarnedDate] = []


class LeaderboardEntry(BaseModel):
    """A single entry on the leaderboard."""
    rank: int
    username: str
    avatar_url: Optional[str]
    points: int
    level: int
    level_name: str


class LeaderboardResponse(BaseModel):
    """Paginated leaderboard response."""
    entries: list[LeaderboardEntry]
    period: str
    total_participants: int
    page: int
    per_page: int
    total_pages: int


class PointsTransaction(BaseModel):
    """A record of points earned or spent."""
    id: str
    action: str
    points: int
    description: str
    created_at: datetime


class ShareTrackRequest(BaseModel):
    """Request to track a share action."""
    poll_id: str
    platform: str  # twitter, facebook, linkedin, reddit, whatsapp, telegram, copy, native


class ShareTrackResponse(BaseModel):
    """Response from tracking a share action."""
    points_earned: int
    total_shares: int
    new_achievements: list[AchievementWithHistory]
    message: str
