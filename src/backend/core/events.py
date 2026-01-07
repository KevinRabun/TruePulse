"""
Application lifecycle event handlers.

Manages startup and shutdown tasks for Cosmos DB connections,
Azure Table Storage initialization, background scheduler, and AI service setup.
"""

from typing import Callable

import structlog
from fastapi import FastAPI

from core.config import settings
from db.cosmos_session import close_cosmos, get_database

logger = structlog.get_logger(__name__)


def create_start_app_handler(app: FastAPI) -> Callable:
    """Create startup event handler."""

    async def start_app() -> None:
        logger.info("Starting TruePulse API...")

        # Initialize Cosmos DB connection
        try:
            await get_database()
            logger.info("Cosmos DB initialized")
        except Exception as e:
            logger.error(f"Cosmos DB initialization failed: {e}")
            raise

        # Seed required data (achievements, etc.) - safe to run multiple times
        try:
            from services.startup_seeder import seed_all

            await seed_all()
        except Exception as e:
            logger.warning(f"Startup seeder failed: {e}")
            logger.info("Achievements can be manually seeded via migration workflow")

        # Initialize Azure Table Storage (for votes, tokens, rate limiting)
        try:
            from services.table_service import get_table_service

            await get_table_service()
            logger.info("Azure Table Storage initialized")
        except Exception as e:
            logger.warning(f"Azure Table Storage initialization failed: {e}")
            logger.info("Falling back to in-memory storage for tokens")

        # Start background scheduler (poll rotation, poll generation)
        if settings.POLL_AUTO_GENERATE or settings.ENABLE_AI_POLL_GENERATION:
            try:
                from services.background_scheduler import start_scheduler

                await start_scheduler()
                logger.info("Background scheduler started successfully")
            except Exception as e:
                logger.exception("Failed to start background scheduler", error=str(e))
                logger.warning("Poll auto-generation will not work!")

        logger.info("TruePulse API started successfully")

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:
    """Create shutdown event handler."""

    async def stop_app() -> None:
        logger.info("Shutting down TruePulse API...")

        # Stop background scheduler
        try:
            from services.background_scheduler import stop_scheduler

            await stop_scheduler()
            logger.info("Background scheduler stopped")
        except Exception as e:
            logger.warning(f"Background scheduler cleanup failed: {e}")

        # Close Cosmos DB connections
        await close_cosmos()
        logger.info("Cosmos DB connections closed")

        # Close Azure Table Storage connections
        try:
            from services.table_service import close_table_service

            await close_table_service()
            logger.info("Azure Table Storage closed")
        except Exception as e:
            logger.warning(f"Azure Table Storage cleanup failed: {e}")

        logger.info("TruePulse API shutdown complete")

    return stop_app
