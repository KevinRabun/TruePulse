"""
Database migration script to remove phone-related columns.

This script removes phone-related columns from the users table since
we've transitioned to passkey-only authentication and no longer need
phone verification or SMS notifications.

Columns removed:
- phone_verified: Legacy phone verification status
- phone_number: Legacy phone number field
- sms_notifications: Legacy SMS notification preference

Run with: python -m scripts.remove_phone_verified

To check current schema without making changes:
    python -m scripts.remove_phone_verified --dry-run
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine


async def check_column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            )
        """),
        {"table": table, "column": column},
    )
    return result.scalar()


async def check_table_exists(conn, table: str) -> bool:
    """Check if a table exists."""
    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table
            )
        """),
        {"table": table},
    )
    return result.scalar()


async def run_migration(dry_run: bool = False) -> None:
    """Run the migration to remove phone-related columns."""
    print("=" * 60)
    print("TruePulse: Remove Phone-Related Columns Migration")
    print("=" * 60)
    print()

    if dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")
        print()

    async with engine.begin() as conn:
        # Check if users table exists
        if not await check_table_exists(conn, "users"):
            print("ERROR: users table does not exist. Run initial setup first.")
            return

        changes_needed = []
        changes_made = []

        # List of phone-related columns to remove
        phone_columns = ["phone_verified", "phone_number", "sms_notifications"]

        for column in phone_columns:
            if await check_column_exists(conn, "users", column):
                changes_needed.append(f"Drop {column} column from users table")
                if not dry_run:
                    print(f"Dropping {column} column...")
                    await conn.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {column}"))
                    changes_made.append(f"Dropped {column} column")
                    print(f"✓ Dropped {column} column")
            else:
                print(f"✓ {column} column already removed (or never existed)")

        # Summary
        print()
        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)

        if dry_run:
            if changes_needed:
                print(f"\nChanges that would be made ({len(changes_needed)}):")
                for change in changes_needed:
                    print(f"  - {change}")
            else:
                print("\nNo changes needed - database schema is up to date!")
        else:
            if changes_made:
                print(f"\nChanges made ({len(changes_made)}):")
                for change in changes_made:
                    print(f"  ✓ {change}")
            else:
                print("\nNo changes needed - database schema is up to date!")

        print()
        print("Migration complete!")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_migration(dry_run=dry_run))
