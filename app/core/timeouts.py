"""
Gestion des timeouts pour éviter les requêtes infinies.

Simplified timeout system for n8n workflow integration.
"""

import asyncio
from typing import TypeVar, Callable, Any, Coroutine
from functools import wraps
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import TimeoutError as TimeoutException
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("api")

T = TypeVar('T')


async def with_timeout(
    coroutine: Coroutine,
    timeout_seconds: int,
    operation_name: str = "operation"
) -> Any:
    """
    Exécute une coroutine avec timeout.

    Args:
        coroutine: Coroutine à exécuter
        timeout_seconds: Timeout en secondes
        operation_name: Nom de l'opération (pour logs)

    Returns:
        Résultat de la coroutine

    Raises:
        TimeoutException: Si timeout dépassé

    Example:
        result = await with_timeout(
            process_document(text),
            timeout_seconds=120,
            operation_name="document_processing"
        )
    """
    try:
        return await asyncio.wait_for(
            coroutine,
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout: {operation_name} exceeded {timeout_seconds}s"
        )
        raise TimeoutException(
            message=f"{operation_name} timed out after {timeout_seconds}s",
            details={
                "operation": operation_name,
                "timeout_seconds": timeout_seconds
            }
        )


def timeout(seconds: int, operation_name: str = None):
    """
    Décorateur pour ajouter un timeout à une fonction async.

    Usage:
        @timeout(seconds=60, operation_name="ocr_processing")
        async def process_ocr(text: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(
                func(*args, **kwargs),
                timeout_seconds=seconds,
                operation_name=op_name
            )

        return wrapper

    return decorator


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour timeout global sur toutes les requêtes.
    """

    def __init__(self, app, timeout_seconds: int = 180):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Request timeout: {request.url.path} exceeded {self.timeout_seconds}s"
            )

            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=504,
                content={
                    "error": "REQUEST_TIMEOUT",
                    "code": "REQUEST_TIMEOUT",
                    "message": f"Request exceeded {self.timeout_seconds}s timeout",
                    "details": {
                        "timeout_seconds": self.timeout_seconds,
                        "path": str(request.url.path)
                    }
                }
            )
