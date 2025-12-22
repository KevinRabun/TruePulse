"""
Database migration script for passkey-only authentication.

This script handles the transition from password-based to passkey-only authentication:
1. Drops the hashed_password column from users table (no longer needed)
2. Ensures passkey_only column exists and defaults to True
3. Adds any missing columns that may have been added since initial deployment

Run with: python -m scripts.migrate_to_passkey_only

To check current schema without making changes:
    python -m scripts.migrate_to_passkey_only --dry-run
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
    """Run the passkey-only migration."""
    print("=" * 60)
    print("TruePulse Passkey-Only Migration")
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

        # 1. Check and drop hashed_password column
        if await check_column_exists(conn, "users", "hashed_password"):
            changes_needed.append("Drop hashed_password column from users table")
            if not dry_run:
                print("Dropping hashed_password column...")
                await conn.execute(
                    text("ALTER TABLE users DROP COLUMN IF EXISTS hashed_password")
                )
                changes_made.append("Dropped hashed_password column")
        else:
            print("✓ hashed_password column already removed")

        # 2. Ensure passkey_only column exists
        if not await check_column_exists(conn, "users", "passkey_only"):
            changes_needed.append("Add passkey_only column to users table")
            if not dry_run:
                print("Adding passkey_only column...")
                await conn.execute(
                    text("""
                        ALTER TABLE users
                        ADD COLUMN passkey_only BOOLEAN NOT NULL DEFAULT TRUE
                    """)
                )
                changes_made.append("Added passkey_only column (default: TRUE)")
        else:
            print("✓ passkey_only column exists")

        # 3. Ensure passkey-related tables exist
        passkey_tables = [
            ("passkey_credentials", "WebAuthn credentials storage"),
            ("device_trust_scores", "Device trust scoring"),
            ("silent_mobile_verifications", "Carrier verification records"),
        ]

        for table_name, description in passkey_tables:
            if not await check_table_exists(conn, table_name):
                changes_needed.append(f"Create {table_name} table ({description})")
                print(f"WARNING: {table_name} table does not exist!")
                print(f"  Run: python -m scripts.add_passkey_auth")
            else:
                print(f"✓ {table_name} table exists")

        # 4. Ensure email_verified column exists (may be missing in old deployments)
        if not await check_column_exists(conn, "users", "email_verified"):
            changes_needed.append("Add email_verified column to users table")
            if not dry_run:
                print("Adding email_verified column...")
                await conn.execute(
                    text("""
                        ALTER TABLE users
                        ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                )
                changes_made.append("Added email_verified column (default: FALSE)")
        else:
            print("✓ email_verified column exists")

        # 5. Ensure flash poll notification columns exist
        flash_poll_columns = [
            ("pulse_poll_notifications", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("flash_poll_notifications", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("flash_polls_per_day", "INTEGER NOT NULL DEFAULT 5"),
            ("flash_polls_notified_today", "INTEGER NOT NULL DEFAULT 0"),
            ("flash_notification_reset_date", "TIMESTAMP WITH TIME ZONE"),
            ("pulse_polls_voted", "INTEGER NOT NULL DEFAULT 0"),
            ("flash_polls_voted", "INTEGER NOT NULL DEFAULT 0"),
            ("pulse_poll_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("longest_pulse_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("last_pulse_vote_date", "TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, column_def in flash_poll_columns:
            if not await check_column_exists(conn, "users", column_name):
                changes_needed.append(f"Add {column_name} column to users table")
                if not dry_run:
                    print(f"Adding {column_name} column...")
                    await conn.execute(
                        text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column_name} {column_def}")
                    )
                    changes_made.append(f"Added {column_name} column")
            else:
                print(f"✓ {column_name} column exists")

        # 6. Ensure ad tracking columns exist
        ad_tracking_columns = [
            ("ad_views", "INTEGER NOT NULL DEFAULT 0"),
            ("ad_clicks", "INTEGER NOT NULL DEFAULT 0"),
            ("ad_view_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("last_ad_view_at", "TIMESTAMP WITH TIME ZONE"),
        ]

        for column_name, column_def in ad_tracking_columns:
            if not await check_column_exists(conn, "users", column_name):
                changes_needed.append(f"Add {column_name} column to users table")
                if not dry_run:
                    print(f"Adding {column_name} column...")
                    await conn.execute(
                        text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column_name} {column_def}")
                    )
                    changes_made.append(f"Added {column_name} column")
            else:
                print(f"✓ {column_name} column exists")

        # 7. Ensure total_shares column exists
        if not await check_column_exists(conn, "users", "total_shares"):
            changes_needed.append("Add total_shares column to users table")
            if not dry_run:
                print("Adding total_shares column...")
                await conn.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_shares INTEGER NOT NULL DEFAULT 0")
                )
                changes_made.append("Added total_shares column")
        else:
            print("✓ total_shares column exists")

        # Print summary
        print()
        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)

        if dry_run:
            if changes_needed:
                print(f"\nChanges that would be made ({len(changes_needed)}):")
                for change in changes_needed:
                    print(f"  • {change}")
                print("\nRun without --dry-run to apply these changes.")
            else:
                print("\n✓ Database schema is up to date. No changes needed.")
        else:
            if changes_made:
                print(f"\nChanges applied ({len(changes_made)}):")
                for change in changes_made:
                    print(f"  ✓ {change}")
            else:
                print("\n✓ Database schema is up to date. No changes needed.")

        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Passkey-only migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what changes would be made without applying them",
    )
    args = parser.parse_args()

    asyncio.run(run_migration(dry_run=args.dry_run))
