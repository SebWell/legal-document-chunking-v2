"""
Métriques de performance simples (en mémoire).

Simplified metrics system for n8n workflow integration.
Basic metrics only: count, avg, min, max (no percentiles).
"""

import time
from typing import Optional, Dict, Any
from functools import wraps
from contextvars import ContextVar
import asyncio
import statistics

# Storage simple en mémoire
metrics_storage: Dict[str, list] = {}
current_operation_ctx: ContextVar[Optional[str]] = ContextVar('current_operation', default=None)


class Timer:
    """
    Context manager pour mesurer des durées.

    Usage:
        with Timer("document_processing"):
            process_document(text)
    """

    def __init__(self, operation_name: str, log: bool = False):
        self.operation_name = operation_name
        self.log = log
        self.start_time = None
        self.end_time = None
        self.duration_ms = None

    def __enter__(self):
        self.start_time = time.time()
        current_operation_ctx.set(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        current_operation_ctx.set(None)

        # Log if enabled
        if self.log:
            import logging
            logger = logging.getLogger("api.metrics")

            if exc_type is None:
                logger.info(
                    f"Operation completed: {self.operation_name} ({self.duration_ms:.2f}ms)"
                )
            else:
                logger.error(
                    f"Operation failed: {self.operation_name} ({self.duration_ms:.2f}ms) - {exc_type.__name__}"
                )

        # Store metric
        if self.operation_name not in metrics_storage:
            metrics_storage[self.operation_name] = []

        metrics_storage[self.operation_name].append({
            "duration_ms": self.duration_ms,
            "timestamp": self.end_time,
            "success": exc_type is None
        })

        # Keep only last 1000
        if len(metrics_storage[self.operation_name]) > 1000:
            metrics_storage[self.operation_name] = metrics_storage[self.operation_name][-1000:]


def timed(operation_name: str = None, log: bool = False):
    """
    Décorateur pour mesurer la durée d'une fonction.

    Usage:
        @timed("document_processing", log=True)
        async def process_document(text: str):
            ...
    """
    def decorator(func):
        op_name = operation_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with Timer(op_name, log=log):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with Timer(op_name, log=log):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_metrics_summary() -> Dict[str, Any]:
    """
    Retourne un résumé des métriques (simplifié).

    Returns:
        Dict with basic metrics: count, avg, min, max, success_rate
    """

    summary = {}

    for operation, measurements in metrics_storage.items():
        if not measurements:
            continue

        durations = [m["duration_ms"] for m in measurements]
        successes = [m["success"] for m in measurements]

        summary[operation] = {
            "count": len(durations),
            "avg_ms": round(statistics.mean(durations), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "success_rate": round(sum(successes) / len(successes), 3)
        }

    return summary


def clear_metrics():
    """Efface toutes les métriques (utile pour tests)."""
    metrics_storage.clear()
