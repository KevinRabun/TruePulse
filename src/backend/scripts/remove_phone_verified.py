"""
Database migration script to remove phone_verified column.

This script removes the phone_verified column from the users table since
we've transitioned to passkey-only authentication and no longer need
phone verification.

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
    """Run the migration to remove phone_verified column."""
    print("=" * 60)
    print("TruePulse: Remove phone_verified Column Migration")
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

        # Drop phone_verified column if it exists
        if await check_column_exists(conn, "users", "phone_verified"):
            changes_needed.append("Drop phone_verified column from users table")
            if not dry_run:
                print("Dropping phone_verified column...")
                await conn.execute(
                    text("ALTER TABLE users DROP COLUMN IF EXISTS phone_verified")
                )
                changes_made.append("Dropped phone_verified column")
                print("✓ Dropped phone_verified column")
        else:
            print("✓ phone_verified column already removed (or never existed)")

        # Also check for phone_number column (legacy) and remove if exists
        if await check_column_exists(conn, "users", "phone_number"):
            changes_needed.append("Drop phone_number column from users table")
            if not dry_run:
                print("Dropping phone_number column...")
                await conn.execute(
                    text("ALTER TABLE users DROP COLUMN IF EXISTS phone_number")
                )
                changes_made.append("Dropped phone_number column")
                print("✓ Dropped phone_number column")
        else:
            print("✓ phone_number column already removed (or never existed)")

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
