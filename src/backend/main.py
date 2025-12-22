"""
TruePulse Backend Application

A privacy-first polling platform with AI-powered poll generation.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api.v1 import router as api_v1_router
from core.config import settings
from core.events import create_start_app_handler, create_stop_app_handler
from core.middleware import FrontendOnlyMiddleware, SecurityHeadersMiddleware

logger = structlog.get_logger(__name__)


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

    # Add middleware (order matters - processed in reverse)
    # 1. Security headers - added to all responses
    application.add_middleware(SecurityHeadersMiddleware)

    # 2. Frontend-only middleware - validates request origin
    application.add_middleware(
        FrontendOnlyMiddleware,
        enforce=settings.ENFORCE_FRONTEND_ONLY,
    )

    # 3. CORS - restricted to specific methods and headers
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Frontend-Secret",
            "X-Request-ID",
        ],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-Request-ID",
        ],
    )

    # 4. GZip compression for responses
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    # Include routers
    application.include_router(api_v1_router, prefix="/api/v1")

    # Add global exception handler to ensure CORS headers are present on error responses
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Global exception handler to catch unhandled exceptions.

        This ensures that even when unexpected errors occur, the response includes
        proper CORS headers (added by the CORS middleware) and a structured JSON response.
        Without this, 500 errors may not have CORS headers, causing browser errors.
        """
        logger.exception(
            "Unhandled exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )

        # Return a proper JSON response - CORS middleware will add headers
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "error_type": type(exc).__name__ if settings.DEBUG else "InternalServerError",
            },
        )

    return application


app = create_application()


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "service": "truepulse-api"}


@app.get("/health/services", tags=["Health"])
async def service_status() -> dict:
    """
    Service configuration status endpoint for deployment validation.
    
    Returns the configuration status of all external services.
    Used by smoke tests to verify deployment completeness.
    """
    from services.email_service import email_service
    
    services = {
        "email": {
            "configured": email_service.is_configured,
            "details": {
                "has_connection_string": email_service._client is not None,
                "has_sender_address": email_service._sender_address is not None,
                "sender_address": email_service._sender_address[:20] + "..." if email_service._sender_address else None,
            }
        },
        "database": {
            "configured": bool(settings.DATABASE_URL),
            "details": {
                "host": settings.POSTGRES_HOST or "not set",
            }
        },
        "openai": {
            "configured": bool(settings.AZURE_OPENAI_ENDPOINT),
            "details": {
                "endpoint": settings.AZURE_OPENAI_ENDPOINT[:30] + "..." if settings.AZURE_OPENAI_ENDPOINT else None,
            }
        },
    }
    
    all_configured = all(svc["configured"] for svc in services.values())
    
    return {
        "status": "healthy" if all_configured else "degraded",
        "all_services_configured": all_configured,
        "services": services,
    }


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
    }
