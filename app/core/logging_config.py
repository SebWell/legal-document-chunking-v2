"""
Configuration du logging structuré JSON.

Simplified structured logging for n8n workflow integration.
No user tracking (API Key auth), only request_id tracing.
"""

import logging
import json
import sys
from datetime import datetime
from contextvars import ContextVar
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

# Context var pour tracer les requêtes (request_id uniquement)
request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')


class JSONFormatter(logging.Formatter):
    """
    Formatter JSON pour logs structurés.

    Format production:
        {
            "timestamp": "2024-01-01T12:00:00.000Z",
            "level": "INFO",
            "logger": "api",
            "message": "Request started",
            "request_id": "abc-123"
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""

        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Context (request_id)
        request_id = request_id_ctx.get()
        if request_id:
            log_obj["request_id"] = request_id

        # Source location (dev only)
        if not settings.is_production:
            log_obj["source"] = {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }

        # Extra fields
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)

        # Exception info
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_obj, ensure_ascii=False)


class PrettyFormatter(logging.Formatter):
    """
    Formatter pretty pour développement.

    Format:
        2024-01-01 12:00:00 | INFO | api | Request started | request_id=abc-123
    """

    # Couleurs ANSI
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""

        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Base message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        base = f"{timestamp} | {color}{record.levelname:8}{reset} | {record.name:15} | {record.getMessage()}"

        # Context
        extras = []
        request_id = request_id_ctx.get()
        if request_id:
            extras.append(f"request_id={request_id}")

        if hasattr(record, "extra_fields"):
            for key, value in record.extra_fields.items():
                extras.append(f"{key}={value}")

        if extras:
            base += f" | {' '.join(extras)}"

        # Exception
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def setup_logging() -> None:
    """
    Configure le logging pour l'application.

    - Production : JSON structuré
    - Development : Pretty avec couleurs
    """

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Choose formatter based on environment
    if settings.is_production:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(PrettyFormatter())

    root_logger.addHandler(handler)

    # Configure specific loggers
    logging.getLogger("api").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class StructuredLogger:
    """
    Helper pour logger avec champs structurés.

    Usage:
        logger = StructuredLogger("api")
        logger.info(
            "Document processed",
            document_id="doc-123",
            sections_count=42,
            duration_ms=1234.5
        )
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs):
        """Log avec champs extra."""
        extra = {"extra_fields": kwargs} if kwargs else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
