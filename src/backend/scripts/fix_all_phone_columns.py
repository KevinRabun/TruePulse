"""Quick migration to drop all legacy phone-related columns."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine


async def drop_columns():
    """Drop all legacy phone-related columns."""
    columns = [
        "daily_poll_sms",
        "flash_poll_sms",
        "phone_carrier",
        "phone_verification_code",
        "phone_verification_sent_at",
        "phone_verified",
        "phone_number",
        "sms_notifications",
    ]

    print("Dropping legacy phone-related columns...")

    async with engine.begin() as conn:
        for col in columns:
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name = :col
                    )
                """),
                {"col": col},
            )
            exists = result.scalar()

            if exists:
                await conn.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}"))
                print(f"✓ Dropped {col}")
            else:
                print(f"- {col} doesn't exist")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(drop_columns())
