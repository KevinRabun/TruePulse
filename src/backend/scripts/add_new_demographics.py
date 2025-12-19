"""
Migration script to add new demographic columns to users table.

Adds:
- marital_status
- religious_affiliation
- ethnicity
- household_income
- parental_status
- housing_status
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.session import engine


NEW_COLUMNS = [
    ("marital_status", "VARCHAR(50)"),
    ("religious_affiliation", "VARCHAR(100)"),
    ("ethnicity", "VARCHAR(100)"),
    ("household_income", "VARCHAR(50)"),
    ("parental_status", "VARCHAR(50)"),
    ("housing_status", "VARCHAR(50)"),
]


async def add_new_demographic_columns():
    """Add new demographic columns to users table if they don't exist."""
    async with engine.begin() as conn:
        for column_name, column_type in NEW_COLUMNS:
            # Check if column exists
            result = await conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = :column_name
            """), {"column_name": column_name})
            exists = result.fetchone() is not None
            
            if exists:
                print(f"Column '{column_name}' already exists in users table.")
                continue
            
            # Add the column (nullable by default)
            await conn.execute(text(f"""
                ALTER TABLE users 
                ADD COLUMN {column_name} {column_type} NULL
            """))
            
            print(f"Successfully added '{column_name}' column to users table.")
    
    print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(add_new_demographic_columns())
