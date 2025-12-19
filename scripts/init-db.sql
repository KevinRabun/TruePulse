-- TruePulse Database Initialization Script
-- This script runs on first container startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create enum types
DO $$ BEGIN
    CREATE TYPE poll_status AS ENUM ('draft', 'active', 'closed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE achievement_type AS ENUM (
        'first_vote',
        'streak_7',
        'streak_30',
        'streak_100',
        'votes_10',
        'votes_100',
        'votes_500',
        'votes_1000',
        'early_adopter'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE truepulse TO truepulse;

-- Output completion message
DO $$
BEGIN
    RAISE NOTICE 'TruePulse database initialized successfully!';
END $$;
