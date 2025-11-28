"""
Simple API Key Authentication

Simplified authentication system using a shared secret API key
instead of JWT tokens. Designed for n8n workflow integration
where authentication is already handled upstream by Supabase.
"""

from fastapi import Header
import logging

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()
logger = logging.getLogger("api")


async def verify_api_key(x_api_key: str = Header(..., description="API Key for authentication")) -> None:
    """
    Verify the API key from the X-API-Key header.

    Args:
        x_api_key: The API key provided in the request header

    Raises:
        AuthenticationError: If the API key is invalid or missing

    Usage:
        @app.get("/protected")
        async def route(api_key: None = Depends(verify_api_key)):
            # API key has been validated
            pass
    """
    if not settings.API_SECRET_KEY:
        logger.error("API_SECRET_KEY not configured")
        raise AuthenticationError(
            message="API authentication not configured",
            details={"error": "Server configuration error"}
        )

    if x_api_key != settings.API_SECRET_KEY:
        logger.warning(f"Invalid API key attempt from header")
        raise AuthenticationError(
            message="Invalid API key",
            details={"error": "The provided API key is invalid"}
        )

    # Authentication successful
    logger.debug("API key authentication successful")
