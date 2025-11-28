"""
Point d'entrée API.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import uuid

from app.core.config import get_settings
from app.core.exceptions import DocumentProcessingException
from app.core.security import configure_security
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.timeouts import TimeoutMiddleware
from app.core.logging_config import setup_logging, request_id_ctx, StructuredLogger
from app.api.v1.error_handlers import (
    document_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.api.v1.endpoints import documents, health
from slowapi.errors import RateLimitExceeded

# Setup logging AVANT tout le reste
setup_logging()

settings = get_settings()
logger = StructuredLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle."""
    logger.info(
        "API starting",
        version=settings.API_VERSION,
        environment=settings.ENV,
        request_timeout=settings.REQUEST_TIMEOUT,
        processing_timeout=settings.PROCESSING_TIMEOUT
    )
    yield
    logger.info("API shutting down")


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="API de chunking de documents pour PyMuPDF/PaddleOCR - Compatible n8n/Supabase",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None
)

# Sécurité
configure_security(app)

# Timeout global sur toutes les requêtes
app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.REQUEST_TIMEOUT)
logger.info("Request timeout configured", timeout_seconds=settings.REQUEST_TIMEOUT)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Error handlers
app.add_exception_handler(DocumentProcessingException, document_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# Middleware logs avec contexte structuré
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requêtes avec contexte structuré."""

    request_id = str(uuid.uuid4())
    request_id_ctx.set(request_id)
    request.state.request_id = request_id

    start = time.time()

    logger.info(
        "Request started",
        method=request.method,
        path=str(request.url.path),
        client_ip=request.client.host if request.client else "unknown"
    )

    response = await call_next(request)

    duration_ms = (time.time() - start) * 1000

    logger.info(
        "Request completed",
        method=request.method,
        path=str(request.url.path),
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2)
    )

    response.headers["X-Request-ID"] = request_id

    return response


# Routes
app.include_router(
    documents.router,
    prefix="/api/v1",
    tags=["Documents"]
)

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["Health"]
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
