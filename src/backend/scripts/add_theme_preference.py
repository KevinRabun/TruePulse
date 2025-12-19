"""
Migration script to add theme_preference column to users table.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.session import engine


async def add_theme_preference_column():
    """Add theme_preference column to users table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'theme_preference'
        """))
        exists = result.fetchone() is not None
        
        if exists:
            print("Column 'theme_preference' already exists in users table.")
            return
        
        # Add the column with default value 'system'
        await conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'system' NOT NULL
        """))
        
        print("Successfully added 'theme_preference' column to users table.")


if __name__ == "__main__":
    asyncio.run(add_theme_preference_column())
