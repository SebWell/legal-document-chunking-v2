"""
Configuration sécurité : CORS, headers.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("api")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware security headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


def configure_security(app: FastAPI) -> None:
    """Configure middlewares sécurité."""

    allowed_origins = settings.get_allowed_origins()
    allowed_hosts = settings.get_allowed_hosts()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        max_age=3600,
        expose_headers=["X-Request-ID"]
    )

    logger.info(f"CORS: {allowed_origins}")

    # Trusted Host (production only)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("Security configured")
