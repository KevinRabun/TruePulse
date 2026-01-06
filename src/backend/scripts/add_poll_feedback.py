"""
Database migration script for adding poll feedback tables.

This script adds the following tables:
- poll_feedback: Individual feedback records linked to votes
- poll_feedback_aggregates: Pre-computed statistics per poll
- category_feedback_patterns: Learned patterns by category for AI improvement

Run with: python -m scripts.add_poll_feedback
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine


async def run_migration() -> None:
    """Run the poll feedback migration."""
    print("Starting poll feedback migration...")

    async with engine.begin() as conn:
        # Check if poll_feedback table already exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'poll_feedback'
                )
            """)
        )
        table_exists = result.scalar()

        if table_exists:
            print("Migration already applied (poll_feedback table exists)")
            return

        print("Creating poll_feedback table...")
        await conn.execute(
            text("""
                CREATE TABLE poll_feedback (
                    id UUID PRIMARY KEY,
                    poll_id UUID NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
                    vote_hash VARCHAR(64) NOT NULL,
                    quality_rating INTEGER NOT NULL CHECK (quality_rating >= 1 AND quality_rating <= 5),
                    issues JSONB,
                    feedback_text TEXT,
                    poll_category VARCHAR(100),
                    was_ai_generated BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(poll_id, vote_hash)
                )
            """)
        )

        print("Creating indexes for poll_feedback...")
        await conn.execute(
            text("""
                CREATE INDEX ix_poll_feedback_poll_id ON poll_feedback(poll_id);
                CREATE INDEX ix_poll_feedback_vote_hash ON poll_feedback(vote_hash);
                CREATE INDEX ix_poll_feedback_category ON poll_feedback(poll_category);
                CREATE INDEX ix_poll_feedback_created_at ON poll_feedback(created_at);
                CREATE INDEX ix_poll_feedback_ai_generated ON poll_feedback(was_ai_generated);
            """)
        )

        print("Creating poll_feedback_aggregates table...")
        await conn.execute(
            text("""
                CREATE TABLE poll_feedback_aggregates (
                    id UUID PRIMARY KEY,
                    poll_id UUID NOT NULL UNIQUE REFERENCES polls(id) ON DELETE CASCADE,
                    total_feedback INTEGER NOT NULL DEFAULT 0,
                    average_rating FLOAT NOT NULL DEFAULT 0.0,
                    rating_counts JSONB NOT NULL DEFAULT '{"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}'::jsonb,
                    issue_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
                    last_feedback_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )

        print("Creating indexes for poll_feedback_aggregates...")
        await conn.execute(
            text("""
                CREATE INDEX ix_poll_feedback_aggregates_poll_id ON poll_feedback_aggregates(poll_id);
                CREATE INDEX ix_poll_feedback_aggregates_avg_rating ON poll_feedback_aggregates(average_rating);
            """)
        )

        print("Creating category_feedback_patterns table...")
        await conn.execute(
            text("""
                CREATE TABLE category_feedback_patterns (
                    id UUID PRIMARY KEY,
                    category VARCHAR(100) NOT NULL UNIQUE,
                    total_feedback INTEGER NOT NULL DEFAULT 0,
                    average_rating FLOAT NOT NULL DEFAULT 0.0,
                    common_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
                    learned_adjustments JSONB NOT NULL DEFAULT '[]'::jsonb,
                    last_analyzed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )

        print("Creating indexes for category_feedback_patterns...")
        await conn.execute(
            text("""
                CREATE INDEX ix_category_feedback_patterns_category ON category_feedback_patterns(category);
                CREATE INDEX ix_category_feedback_patterns_avg_rating ON category_feedback_patterns(average_rating);
            """)
        )

        print("Poll feedback migration completed successfully!")


async def rollback_migration() -> None:
    """Rollback the poll feedback migration."""
    print("Rolling back poll feedback migration...")

    async with engine.begin() as conn:
        print("Dropping tables...")
        await conn.execute(text("DROP TABLE IF EXISTS poll_feedback CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS poll_feedback_aggregates CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS category_feedback_patterns CASCADE"))

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Poll feedback migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration())
