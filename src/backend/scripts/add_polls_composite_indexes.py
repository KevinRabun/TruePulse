"""
Migration script to add composite index on polls table.

This index optimizes the scheduler queries that find polls
based on status and scheduled_start time.

Note: Cannot use CREATE INDEX CONCURRENTLY inside a transaction,
so we use regular CREATE INDEX which will briefly lock the table.
For production with large tables, run during low-traffic periods.
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
    print("Starting polls composite indexes migration...")

    async with engine.begin() as conn:
        # Check if polls table exists first
        result = await conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'polls'
            )
        """)
        )
        table_exists = result.scalar()

        if not table_exists:
            print("Table 'polls' does not exist. Skipping index creation.")
            return

        # Check if status + scheduled_start index exists
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
            print("✅ Index 'ix_polls_status_scheduled_start' already exists.")
        else:
            # Create the composite index for status + scheduled_start
            # Note: Using regular CREATE INDEX (not CONCURRENTLY) as we're in a transaction
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS ix_polls_status_scheduled_start
                ON polls (status, scheduled_start)
            """)
            )
            print("✅ Created index 'ix_polls_status_scheduled_start'.")

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
            print("✅ Index 'ix_polls_status_poll_type' already exists.")
        else:
            # Create the composite index for status + poll_type
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS ix_polls_status_poll_type
                ON polls (status, poll_type)
            """)
            )
            print("✅ Created index 'ix_polls_status_poll_type'.")

        print("✅ Composite indexes migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(add_polls_composite_indexes())
