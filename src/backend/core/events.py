"""
Application lifecycle event handlers.

Manages startup and shutdown tasks for database connections,
Azure Table Storage initialization, and AI service setup.
"""

import logging
from typing import Callable

from fastapi import FastAPI

from db.session import close_db, init_db

logger = logging.getLogger(__name__)


def create_start_app_handler(app: FastAPI) -> Callable:
    """Create startup event handler."""

    async def start_app() -> None:
        logger.info("Starting TruePulse API...")

        # Initialize database connections
        await init_db()
        logger.info("Database initialized")

        # Initialize Azure Table Storage (for votes, tokens, rate limiting)
        try:
            from services.table_service import get_table_service

            await get_table_service()
            logger.info("Azure Table Storage initialized")
        except Exception as e:
            logger.warning(f"Azure Table Storage initialization failed: {e}")
            logger.info("Falling back to in-memory storage for tokens")

        # Initialize AI services
        # await init_ai_services()

        # Initialize telemetry
        # await init_telemetry()

        logger.info("TruePulse API started successfully")

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:
    """Create shutdown event handler."""

    async def stop_app() -> None:
        logger.info("Shutting down TruePulse API...")

        # Close database connections
        await close_db()

        # Close Azure Table Storage connections
        try:
            from services.table_service import close_table_service

            await close_table_service()
            logger.info("Azure Table Storage closed")
        except Exception as e:
            logger.warning(f"Azure Table Storage cleanup failed: {e}")

        # Cleanup AI services
        # await cleanup_ai_services()

        logger.info("TruePulse API shutdown complete")

    return stop_app
