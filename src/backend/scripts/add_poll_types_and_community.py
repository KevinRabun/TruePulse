"""
Migration script to add poll types, notification preferences, and community achievements.

Run with: python -m scripts.add_poll_types_and_community
"""

import asyncio
from sqlalchemy import text
from db.session import async_session_maker


async def add_poll_type_column():
    """Add poll_type column to polls table."""
    async with async_session_maker() as session:
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'polls' 
            AND column_name = 'poll_type'
        """)
        result = await session.execute(check_query)
        if result.fetchone():
            print("poll_type column already exists in polls table")
            return
        
        # Add the column
        alter_query = text("""
            ALTER TABLE polls 
            ADD COLUMN poll_type VARCHAR(20) DEFAULT 'standard'
        """)
        await session.execute(alter_query)
        
        # Create index
        index_query = text("""
            CREATE INDEX IF NOT EXISTS ix_polls_poll_type ON polls (poll_type)
        """)
        await session.execute(index_query)
        
        await session.commit()
        print("✓ Added poll_type column to polls table")


async def add_notification_preferences():
    """Add notification preference columns to users table."""
    async with async_session_maker() as session:
        columns_to_add = [
            ("pulse_poll_notifications", "BOOLEAN DEFAULT TRUE"),
            ("flash_poll_notifications", "BOOLEAN DEFAULT TRUE"),
            ("flash_polls_per_day", "INTEGER DEFAULT 5"),
            ("flash_polls_notified_today", "INTEGER DEFAULT 0"),
            ("flash_notification_reset_date", "TIMESTAMP WITH TIME ZONE"),
            ("pulse_polls_voted", "INTEGER DEFAULT 0"),
            ("flash_polls_voted", "INTEGER DEFAULT 0"),
            ("pulse_poll_streak", "INTEGER DEFAULT 0"),
            ("longest_pulse_streak", "INTEGER DEFAULT 0"),
            ("last_pulse_vote_date", "TIMESTAMP WITH TIME ZONE"),
        ]
        
        for col_name, col_type in columns_to_add:
            check_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = '{col_name}'
            """)
            result = await session.execute(check_query)
            if result.fetchone():
                print(f"  {col_name} already exists")
                continue
            
            alter_query = text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            await session.execute(alter_query)
            print(f"  Added {col_name}")
        
        await session.commit()
        print("✓ Added notification preference columns to users table")


async def create_community_achievement_tables():
    """Create community achievement tables."""
    async with async_session_maker() as session:
        # Check if main table exists
        check_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'community_achievements'
        """)
        result = await session.execute(check_query)
        if result.fetchone():
            print("Community achievement tables already exist")
            return
        
        # Create community_achievements table
        create_community_achievements = text("""
            CREATE TABLE community_achievements (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                icon VARCHAR(10) NOT NULL,
                badge_icon VARCHAR(10) NOT NULL,
                goal_type VARCHAR(50) NOT NULL,
                target_count INTEGER NOT NULL,
                time_window_hours INTEGER,
                points_reward INTEGER DEFAULT 0,
                bonus_multiplier FLOAT DEFAULT 1.0,
                is_recurring BOOLEAN DEFAULT TRUE,
                cooldown_hours INTEGER,
                tier VARCHAR(20) DEFAULT 'gold',
                category VARCHAR(50) DEFAULT 'community',
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        await session.execute(create_community_achievements)
        print("  Created community_achievements table")
        
        # Create community_achievement_events table
        create_events = text("""
            CREATE TABLE community_achievement_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                achievement_id VARCHAR(50) REFERENCES community_achievements(id) ON DELETE CASCADE,
                triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                final_count INTEGER NOT NULL,
                participant_count INTEGER DEFAULT 0,
                context_type VARCHAR(50),
                context_id VARCHAR(100),
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP WITH TIME ZONE
            )
        """)
        await session.execute(create_events)
        
        # Create indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_community_events_achievement_id 
            ON community_achievement_events (achievement_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_community_events_triggered_at 
            ON community_achievement_events (triggered_at)
        """))
        print("  Created community_achievement_events table")
        
        # Create community_achievement_participants table
        create_participants = text("""
            CREATE TABLE community_achievement_participants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_id UUID REFERENCES community_achievement_events(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                contributed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                contribution_count INTEGER DEFAULT 1,
                points_awarded INTEGER DEFAULT 0,
                badge_awarded BOOLEAN DEFAULT FALSE,
                UNIQUE (event_id, user_id)
            )
        """)
        await session.execute(create_participants)
        
        # Create indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_community_participants_event_id 
            ON community_achievement_participants (event_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_community_participants_user_id 
            ON community_achievement_participants (user_id)
        """))
        print("  Created community_achievement_participants table")
        
        await session.commit()
        print("✓ Created all community achievement tables")


async def run_migration():
    """Run all migrations."""
    print("Starting migration for poll types and community achievements...\n")
    
    await add_poll_type_column()
    await add_notification_preferences()
    await create_community_achievement_tables()
    
    print("\n✓ All migrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
