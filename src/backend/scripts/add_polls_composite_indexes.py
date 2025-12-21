"""
Migration script to add composite index on polls table.

This index optimizes the scheduler queries that find polls
based on status and scheduled_start time.
"""

import asyncio
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from db.session import engine


async def add_polls_composite_indexes():
    """Add composite indexes to polls table if they don't exist."""
    async with engine.begin() as conn:
        # Check if index exists
        result = await conn.execute(
            text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'polls'
            AND indexname = 'ix_polls_status_scheduled_start'
        """)
        )
        exists = result.fetchone() is not None

        if exists:
            print("Index 'ix_polls_status_scheduled_start' already exists.")
        else:
            # Create the composite index for status + scheduled_start
            await conn.execute(
                text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_polls_status_scheduled_start
                ON polls (status, scheduled_start)
            """)
            )
            print("Created index 'ix_polls_status_scheduled_start'.")

        # Check for status + poll_type index
        result = await conn.execute(
            text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'polls'
            AND indexname = 'ix_polls_status_poll_type'
        """)
        )
        exists = result.fetchone() is not None

        if exists:
            print("Index 'ix_polls_status_poll_type' already exists.")
        else:
            # Create the composite index for status + poll_type
            await conn.execute(
                text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_polls_status_poll_type
                ON polls (status, poll_type)
            """)
            )
            print("Created index 'ix_polls_status_poll_type'.")

        print("Composite indexes migration completed.")


if __name__ == "__main__":
    asyncio.run(add_polls_composite_indexes())
