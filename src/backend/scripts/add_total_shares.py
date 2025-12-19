"""
Migration script to add total_shares column to users table.
This supports the sharing achievements feature.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.session import engine


async def add_total_shares_column():
    """Add total_shares column to users table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'total_shares'
        """))
        exists = result.fetchone() is not None
        
        if exists:
            print("Column 'total_shares' already exists in users table.")
            return
        
        # Add the column with default value 0
        await conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN total_shares INTEGER DEFAULT 0 NOT NULL
        """))
        
        print("Successfully added 'total_shares' column to users table.")


if __name__ == "__main__":
    asyncio.run(add_total_shares_column())
