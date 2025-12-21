"""
Migration script to add unique constraint on polls table.

This constraint prevents duplicate polls from being created for the same
poll_type and scheduled_start time window. It fixes a race condition where
concurrent scheduler invocations could create multiple identical polls.

The constraint ensures:
- Only ONE poll per poll_type per time window
- Database-level enforcement (cannot be bypassed by application race conditions)
- IntegrityError raised on duplicate insert attempts

Run this script to add the constraint to existing databases.
"""

import asyncio
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from db.session import engine


async def add_polls_unique_constraint():
    """Add unique constraint on (poll_type, scheduled_start) to polls table."""
    print("Starting polls unique constraint migration...")
    print("This prevents duplicate polls per time window (fixes race condition).")

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
            print("Table 'polls' does not exist. Skipping constraint creation.")
            return

        # Check if unique constraint already exists
        result = await conn.execute(
            text("""
            SELECT conname
            FROM pg_constraint
            WHERE conname = 'uq_polls_type_scheduled_start'
            AND conrelid = 'polls'::regclass
        """)
        )
        exists = result.fetchone() is not None

        if exists:
            print("✅ Unique constraint 'uq_polls_type_scheduled_start' already exists.")
            return

        # First, check for and report any existing duplicates
        print("\nChecking for existing duplicate polls...")
        result = await conn.execute(
            text("""
            SELECT poll_type, scheduled_start, COUNT(*) as count
            FROM polls
            WHERE scheduled_start IS NOT NULL
            GROUP BY poll_type, scheduled_start
            HAVING COUNT(*) > 1
            ORDER BY scheduled_start DESC
            LIMIT 20
        """)
        )
        duplicates = result.fetchall()

        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate poll combinations:")
            for dup in duplicates:
                print(f"   - {dup[0]}: {dup[1]} ({dup[2]} polls)")
            print("\nYou must delete duplicates before adding the constraint.")
            print("Keeping the oldest poll for each duplicate combination...")

            # Delete duplicates, keeping the oldest poll (smallest created_at)
            delete_result = await conn.execute(
                text("""
                WITH duplicates AS (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY poll_type, scheduled_start
                               ORDER BY created_at ASC
                           ) as rn
                    FROM polls
                    WHERE scheduled_start IS NOT NULL
                )
                DELETE FROM polls
                WHERE id IN (
                    SELECT id FROM duplicates WHERE rn > 1
                )
                RETURNING id
            """)
            )
            deleted_ids = delete_result.fetchall()
            print(f"✅ Deleted {len(deleted_ids)} duplicate polls.")

        # Now add the unique constraint
        print("\nAdding unique constraint on (poll_type, scheduled_start)...")
        await conn.execute(
            text("""
            ALTER TABLE polls
            ADD CONSTRAINT uq_polls_type_scheduled_start
            UNIQUE (poll_type, scheduled_start)
        """)
        )
        print("✅ Unique constraint 'uq_polls_type_scheduled_start' created successfully!")

    print("\n🎉 Migration complete!")
    print("The scheduler will now prevent duplicate polls via database constraint.")


def main():
    """Run the migration."""
    asyncio.run(add_polls_unique_constraint())


if __name__ == "__main__":
    main()
