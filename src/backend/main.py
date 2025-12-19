"""
TruePulse Backend Application

A privacy-first polling platform with AI-powered poll generation.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.v1 import router as api_v1_router
from core.config import settings
from core.events import create_start_app_handler, create_stop_app_handler
from core.middleware import FrontendOnlyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    await create_start_app_handler(app)()
    yield
    # Shutdown
    await create_stop_app_handler(app)()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="Privacy-first polling platform with AI-powered poll generation",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Add middleware
    # Frontend-only middleware should be added first (processed last in request chain)
    application.add_middleware(
        FrontendOnlyMiddleware,
        enforce=settings.ENFORCE_FRONTEND_ONLY,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    # Include routers
    application.include_router(api_v1_router, prefix="/api/v1")

    return application


app = create_application()


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "service": "truepulse-api"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
    }
