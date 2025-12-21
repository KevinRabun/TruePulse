"""
Migration script to create distributed_locks table.

This table is used for coordinating background jobs across multiple
Container App replicas using optimistic locking.
"""

import asyncio
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from db.session import engine


async def create_distributed_locks_table():
    """Create distributed_locks table if it doesn't exist."""
    print("Starting distributed_locks table migration...")

    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'distributed_locks'
            )
        """)
        )
        exists = result.scalar()

        if exists:
            print("✅ Table 'distributed_locks' already exists.")
            return

        # Create the table
        await conn.execute(
            text("""
            CREATE TABLE distributed_locks (
                id SERIAL PRIMARY KEY,
                lock_name VARCHAR(100) NOT NULL UNIQUE,
                locked_by VARCHAR(255),
                locked_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                is_locked BOOLEAN NOT NULL DEFAULT FALSE,
                last_run_at TIMESTAMPTZ,
                last_run_result TEXT,
                version INTEGER NOT NULL DEFAULT 0
            )
        """)
        )
        print("✅ Created 'distributed_locks' table.")

        # Create indexes
        await conn.execute(
            text("""
            CREATE INDEX ix_distributed_locks_lock_name
            ON distributed_locks (lock_name)
        """)
        )
        print("✅ Created index 'ix_distributed_locks_lock_name'.")

        await conn.execute(
            text("""
            CREATE INDEX ix_distributed_locks_name_locked
            ON distributed_locks (lock_name, is_locked)
        """)
        )
        print("✅ Created index 'ix_distributed_locks_name_locked'.")

        # Pre-populate with known job lock names
        await conn.execute(
            text("""
            INSERT INTO distributed_locks (lock_name, is_locked, version)
            VALUES
                ('poll_rotation', FALSE, 0),
                ('poll_generation', FALSE, 0)
        """)
        )

        print("✅ Pre-populated with lock entries: poll_rotation, poll_generation")
        print("✅ Distributed locks migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(create_distributed_locks_table())
