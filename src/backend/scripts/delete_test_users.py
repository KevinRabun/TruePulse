"""Delete test users created during registration testing."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.session import engine

TEST_EMAILS = [
    "testfinal@test.com",
    "test123@test.com",
    "testdomain@test.com",
]


async def delete_test_users():
    """Delete test users by email."""
    print("Deleting test users...")

    async with engine.begin() as conn:
        for email in TEST_EMAILS:
            result = await conn.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": email},
            )
            if result.rowcount > 0:
                print(f"✓ Deleted {email}")
            else:
                print(f"- {email} not found")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(delete_test_users())
