#!/bin/bash
# TruePulse API - Docker Entrypoint
# Handles optional database migrations before starting the application

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "TruePulse API Container Starting"
echo "=========================================="
echo "Environment: ${ENVIRONMENT:-unknown}"
echo "Run Migration: ${RUN_MIGRATION:-none}"
echo "=========================================="

# Check if we need to run a migration
if [ -n "$RUN_MIGRATION" ] && [ "$RUN_MIGRATION" != "none" ]; then
    echo -e "${YELLOW}Migration mode detected!${NC}"
    echo "Running migration script: $RUN_MIGRATION"
    echo ""
    
    SCRIPT_PATH="/app/scripts/$RUN_MIGRATION"
    
    if [ -f "$SCRIPT_PATH" ]; then
        echo "Executing: python $SCRIPT_PATH"
        echo "=========================================="
        
        # Run the migration script
        if python "$SCRIPT_PATH"; then
            echo ""
            echo -e "${GREEN}✅ Migration completed successfully!${NC}"
        else
            EXIT_CODE=$?
            echo ""
            echo -e "${RED}❌ Migration failed with exit code: $EXIT_CODE${NC}"
            # In migration mode, we want to exit so the revision can be rolled back
            exit $EXIT_CODE
        fi
        
        echo "=========================================="
        echo ""
    else
        echo -e "${RED}Error: Migration script not found: $SCRIPT_PATH${NC}"
        echo "Available scripts:"
        ls -la /app/scripts/*.py 2>/dev/null || echo "No scripts found"
        exit 1
    fi
fi

# Start the main application
# Use WEB_CONCURRENCY env var if set, otherwise default to 1 worker for limited memory
WORKERS=${WEB_CONCURRENCY:-1}
echo "Starting uvicorn server with $WORKERS workers..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers $WORKERS
