"""
Rate limiting pour protéger l'API.

Simplified rate limiting by IP address for n8n workflow integration.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger("api")


# Simple rate limiting by IP address
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Gestionnaire rate limit - retourne une réponse HTTP 429.
    """

    logger.warning(
        "Rate limit exceeded",
        extra={
            "path": str(request.url.path),
            "ip": get_remote_address(request)
        }
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "details": {
                    "limit": str(exc)
                }
            }
        },
        headers={"Retry-After": "60"}
    )
