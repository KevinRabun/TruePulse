"""
Migration script to add display_name column to users table.
Also deletes all existing users to ensure clean data.

Run with: python -m scripts.add_display_name
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import async_engine


async def add_display_name_column():
    """Add display_name column to users table and delete existing users."""
    async with async_engine.begin() as conn:
        # First, delete all existing users (cascades to related tables)
        print("Deleting all existing users...")

        # Delete in order to respect foreign key constraints
        # Delete passkey-related data first
        await conn.execute(text("DELETE FROM silent_mobile_verifications"))
        print("  - Deleted silent_mobile_verifications")

        await conn.execute(text("DELETE FROM device_trust_scores"))
        print("  - Deleted device_trust_scores")

        await conn.execute(text("DELETE FROM passkey_credentials"))
        print("  - Deleted passkey_credentials")

        # Delete user achievements
        await conn.execute(text("DELETE FROM user_achievements"))
        print("  - Deleted user_achievements")

        # Delete votes and vote history
        await conn.execute(text("DELETE FROM user_vote_history"))
        print("  - Deleted user_vote_history")

        await conn.execute(text("DELETE FROM votes"))
        print("  - Deleted votes")

        # Finally delete users
        result = await conn.execute(text("DELETE FROM users"))
        print(f"  - Deleted {result.rowcount} users")

        # Check if display_name column exists
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'display_name'
            """)
        )
        column_exists = result.fetchone() is not None

        if column_exists:
            print("display_name column already exists in users table")
        else:
            # Add the display_name column
            print("Adding display_name column to users table...")
            await conn.execute(
                text("""
                    ALTER TABLE users
                    ADD COLUMN display_name VARCHAR(100) NULL
                """)
            )
            print("Successfully added display_name column")

        print("\nMigration complete!")
        print("All users have been deleted. New registrations will have proper display names.")


if __name__ == "__main__":
    asyncio.run(add_display_name_column())
