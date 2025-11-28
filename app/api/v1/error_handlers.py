"""
Gestionnaires d'erreurs globaux.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime

from app.core.exceptions import DocumentProcessingException, RateLimitError

logger = logging.getLogger("api")


async def document_exception_handler(
    request: Request,
    exc: DocumentProcessingException
) -> JSONResponse:
    """Gestionnaire exceptions métier."""

    logger.error(
        f"Exception: {exc.code}",
        extra={
            "error_code": exc.code,
            "error_message": exc.message,
            "details": exc.details,
            "path": str(request.url),
            "method": request.method
        }
    )

    content = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    }

    if exc.details:
        content["error"]["details"] = exc.details

    headers = {}
    if isinstance(exc, RateLimitError) and exc.details.get("retry_after"):
        headers["Retry-After"] = str(exc.details["retry_after"])

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Gestionnaire erreurs validation."""

    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "Validation error",
        extra={"errors": errors, "path": str(request.url)}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
                "validation_errors": errors
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Gestionnaire erreurs génériques."""

    logger.exception(
        "Unhandled exception",
        extra={
            "exception_type": type(exc).__name__,
            "path": str(request.url)
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path)
            }
        }
    )
