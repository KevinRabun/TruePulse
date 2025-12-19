"""
Migration script to add ad engagement tracking columns to users table.

Run with: python -m scripts.add_ad_tracking
"""

import asyncio
from sqlalchemy import text
from db.session import async_session_maker


async def add_ad_tracking_columns():
    """Add ad engagement tracking columns to users table."""
    async with async_session_maker() as session:
        # Check if columns already exist
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('ad_views', 'ad_clicks', 'ad_view_streak', 'last_ad_view_at')
        """)
        result = await session.execute(check_query)
        existing_columns = [row[0] for row in result.fetchall()]
        
        columns_to_add = []
        
        if 'ad_views' not in existing_columns:
            columns_to_add.append("ADD COLUMN ad_views INTEGER DEFAULT 0")
            print("Adding ad_views column...")
        
        if 'ad_clicks' not in existing_columns:
            columns_to_add.append("ADD COLUMN ad_clicks INTEGER DEFAULT 0")
            print("Adding ad_clicks column...")
        
        if 'ad_view_streak' not in existing_columns:
            columns_to_add.append("ADD COLUMN ad_view_streak INTEGER DEFAULT 0")
            print("Adding ad_view_streak column...")
        
        if 'last_ad_view_at' not in existing_columns:
            columns_to_add.append("ADD COLUMN last_ad_view_at TIMESTAMP WITH TIME ZONE")
            print("Adding last_ad_view_at column...")
        
        if columns_to_add:
            alter_query = text(f"ALTER TABLE users {', '.join(columns_to_add)}")
            await session.execute(alter_query)
            await session.commit()
            print(f"\n✓ Added {len(columns_to_add)} column(s) to users table")
        else:
            print("All ad tracking columns already exist!")


if __name__ == "__main__":
    asyncio.run(add_ad_tracking_columns())
