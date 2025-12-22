"""
Database migration script for adding passkey authentication support.

This script adds the following tables:
- passkey_credentials: WebAuthn credentials for passwordless auth
- device_trust_scores: Device trust scoring for fraud prevention
- silent_mobile_verifications: Records of carrier-verified phone checks

And modifies:
- users: Makes hashed_password nullable, adds passkey_only flag

Run with: python -m scripts.add_passkey_auth
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import engine, get_db


async def run_migration() -> None:
    """Run the passkey authentication migration."""
    print("Starting passkey authentication migration...")

    async with engine.begin() as conn:
        # Check if passkey_credentials table already exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'passkey_credentials'
                )
            """)
        )
        table_exists = result.scalar()

        if table_exists:
            print("Migration already applied (passkey_credentials table exists)")
            return

        print("Creating passkey_credentials table...")
        await conn.execute(
            text("""
                CREATE TABLE passkey_credentials (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    credential_id VARCHAR(512) NOT NULL UNIQUE,
                    public_key TEXT NOT NULL,
                    sign_count INTEGER NOT NULL DEFAULT 0,
                    device_name VARCHAR(255),
                    transports TEXT,
                    backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
                    backup_state BOOLEAN NOT NULL DEFAULT FALSE,
                    bound_phone_hash VARCHAR(64),
                    aaguid VARCHAR(36),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_used_at TIMESTAMP WITH TIME ZONE
                )
            """)
        )

        print("Creating indexes for passkey_credentials...")
        await conn.execute(
            text("""
                CREATE INDEX ix_passkey_credentials_user_id ON passkey_credentials(user_id);
                CREATE INDEX ix_passkey_credentials_credential_id ON passkey_credentials(credential_id);
            """)
        )

        print("Creating device_trust_scores table...")
        await conn.execute(
            text("""
                CREATE TABLE device_trust_scores (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    device_fingerprint VARCHAR(128) NOT NULL,
                    trust_score INTEGER NOT NULL DEFAULT 50,
                    verification_score INTEGER NOT NULL DEFAULT 50,
                    behavioral_score INTEGER NOT NULL DEFAULT 50,
                    history_score INTEGER NOT NULL DEFAULT 50,
                    carrier_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    successful_verifications INTEGER NOT NULL DEFAULT 0,
                    failed_verifications INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, device_fingerprint)
                )
            """)
        )

        print("Creating indexes for device_trust_scores...")
        await conn.execute(
            text("""
                CREATE INDEX ix_device_trust_scores_user_id ON device_trust_scores(user_id);
                CREATE INDEX ix_device_trust_scores_fingerprint ON device_trust_scores(device_fingerprint);
            """)
        )

        print("Creating silent_mobile_verifications table...")
        await conn.execute(
            text("""
                CREATE TABLE silent_mobile_verifications (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    phone_hash VARCHAR(64) NOT NULL,
                    verification_success BOOLEAN NOT NULL DEFAULT FALSE,
                    carrier_name VARCHAR(100),
                    mcc_mnc VARCHAR(10),
                    client_ip_hash VARCHAR(64),
                    device_fingerprint VARCHAR(128),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )

        print("Creating indexes for silent_mobile_verifications...")
        await conn.execute(
            text("""
                CREATE INDEX ix_silent_mobile_verifications_user_id ON silent_mobile_verifications(user_id);
                CREATE INDEX ix_silent_mobile_verifications_phone_hash ON silent_mobile_verifications(phone_hash);
            """)
        )

        print("Modifying users table...")
        # Make hashed_password nullable (for passkey-only users)
        await conn.execute(
            text("""
                ALTER TABLE users
                ALTER COLUMN hashed_password DROP NOT NULL
            """)
        )

        # Add passkey_only flag
        await conn.execute(
            text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS passkey_only BOOLEAN NOT NULL DEFAULT FALSE
            """)
        )

        print("Migration completed successfully!")
        print("")
        print("New tables created:")
        print("  - passkey_credentials: WebAuthn credentials storage")
        print("  - device_trust_scores: Device trust scoring")
        print("  - silent_mobile_verifications: Carrier verification records")
        print("")
        print("Modified tables:")
        print("  - users: hashed_password is now nullable, added passkey_only flag")


async def rollback_migration() -> None:
    """Rollback the passkey authentication migration."""
    print("Rolling back passkey authentication migration...")

    async with engine.begin() as conn:
        # Drop tables in reverse order (due to foreign keys)
        print("Dropping silent_mobile_verifications table...")
        await conn.execute(text("DROP TABLE IF EXISTS silent_mobile_verifications CASCADE"))

        print("Dropping device_trust_scores table...")
        await conn.execute(text("DROP TABLE IF EXISTS device_trust_scores CASCADE"))

        print("Dropping passkey_credentials table...")
        await conn.execute(text("DROP TABLE IF EXISTS passkey_credentials CASCADE"))

        print("Reverting users table changes...")
        # Note: We don't make hashed_password NOT NULL again because existing
        # passkey-only users would fail. This is a one-way migration.
        await conn.execute(
            text("""
                ALTER TABLE users
                DROP COLUMN IF EXISTS passkey_only
            """)
        )

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Passkey authentication migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration instead of applying it",
    )
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration())
