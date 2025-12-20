"""
Frontend-only access middleware.

Ensures API requests can only come from the official TruePulse frontend,
preventing unauthorized third-party access to the API.
"""

from typing import Callable
from urllib.parse import urlparse

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class FrontendOnlyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict API access to the official frontend only.

    This provides defense-in-depth beyond CORS:
    - Validates Origin/Referer headers
    - Checks for frontend API secret header
    - Blocks direct API access from non-browser clients

    Note: This is not foolproof (headers can be spoofed), but combined with
    JWT authentication, it provides a strong barrier against casual misuse.
    """

    # Paths that don't require frontend validation (health checks, etc.)
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: Callable, enforce: bool = True):
        super().__init__(app)
        self.enforce = enforce
        self.allowed_origins = set(settings.allowed_origins_list)
        self.frontend_secret = settings.FRONTEND_API_SECRET

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate frontend origin."""
        # Skip validation if not enforced (e.g., local development)
        if not self.enforce:
            return await call_next(request)

        # Skip validation for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Validate the request origin
        if not self._is_valid_request(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Access denied. This API is only accessible from the official TruePulse application."
                },
            )

        return await call_next(request)

    def _is_valid_request(self, request: Request) -> bool:
        """
        Validate that the request comes from an authorized frontend.

        Checks:
        1. X-Frontend-Secret header matches
        2. Origin or Referer header is from allowed origins
        """
        # Check frontend secret header
        frontend_secret = request.headers.get("X-Frontend-Secret")
        if frontend_secret != self.frontend_secret:
            return False

        # Check Origin header
        origin = request.headers.get("Origin")
        if origin:
            return self._is_allowed_origin(origin)

        # Fall back to Referer header
        referer = request.headers.get("Referer")
        if referer:
            return self._is_allowed_origin(referer)

        # No origin information - reject
        return False

    def _is_allowed_origin(self, url: str) -> bool:
        """Check if a URL's origin is in the allowed list."""
        try:
            parsed = urlparse(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            return origin in self.allowed_origins
        except Exception:
            return False
