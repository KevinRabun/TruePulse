"""
Database migration script for adding passkey challenges table.

This script adds the passkey_challenges table for storing WebAuthn challenges
in the database instead of in-memory. This supports multi-worker deployments
where each worker has its own memory space.

Run with: python -m scripts.add_passkey_challenges
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine


async def run_migration() -> None:
    """Run the passkey challenges migration."""
    print("Starting passkey challenges migration...")

    async with engine.begin() as conn:
        # Check if passkey_challenges table already exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'passkey_challenges'
                )
            """)
        )
        table_exists = result.scalar()

        if table_exists:
            print("Migration already applied (passkey_challenges table exists)")
            return

        print("Creating passkey_challenges table...")
        await conn.execute(
            text("""
                CREATE TABLE passkey_challenges (
                    id UUID PRIMARY KEY,
                    challenge VARCHAR(64) NOT NULL,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    operation VARCHAR(30) NOT NULL,
                    device_info TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )

        print("Creating indexes for passkey_challenges...")
        await conn.execute(
            text("""
                CREATE INDEX ix_passkey_challenges_user_id ON passkey_challenges(user_id);
                CREATE INDEX ix_passkey_challenges_expires_at ON passkey_challenges(expires_at);
            """)
        )

        print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
