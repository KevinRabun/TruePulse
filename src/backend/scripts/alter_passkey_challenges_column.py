"""
Database migration script for altering passkey_challenges.challenge column size.

The original VARCHAR(64) was too small for base64url-encoded WebAuthn challenges
which can be up to 86 characters for 64-byte challenges.

Run with: python -m scripts.alter_passkey_challenges_column
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine


async def run_migration() -> None:
    """Run the column alteration migration."""
    print("Starting passkey_challenges column alteration migration...")

    async with engine.begin() as conn:
        # Check if passkey_challenges table exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'passkey_challenges'
                )
            """)
        )
        table_exists = result.scalar()

        if not table_exists:
            print("passkey_challenges table does not exist - nothing to migrate")
            return

        # Check current column size
        result = await conn.execute(
            text("""
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'passkey_challenges'
                AND column_name = 'challenge'
            """)
        )
        current_length = result.scalar()

        if current_length and current_length >= 256:
            print(f"Column already has sufficient size ({current_length})")
            return

        print(f"Current challenge column size: {current_length}")
        print("Altering challenge column to VARCHAR(256)...")

        await conn.execute(
            text("ALTER TABLE passkey_challenges ALTER COLUMN challenge TYPE VARCHAR(256)")
        )

        print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
