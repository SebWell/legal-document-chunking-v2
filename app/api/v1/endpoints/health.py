"""
Health check endpoints pour monitoring.

Simplified health checks for n8n workflow integration.
Checks Mistral AI only (no Supabase dependency).
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import httpx
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("api.health")
router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check basique",
    description="Simple health check - API is responding"
)
async def health_check():
    """
    Health check simple - l'API répond.

    Utilisé par les load balancers pour routing.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.API_VERSION,
        "environment": settings.ENV
    }


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness probe",
    description="Kubernetes liveness probe - application is alive"
)
async def liveness_check():
    """
    Liveness probe - l'application est vivante.

    Utilisé par Kubernetes/Docker pour savoir si restart nécessaire.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness probe",
    description="Kubernetes readiness probe - checks Mistral AI dependency"
)
async def readiness_check():
    """
    Readiness probe - l'application est prête à servir.

    Vérifie la dépendance externe Mistral AI uniquement.
    (No Supabase check - n8n handles that upstream)

    Retourne 200 si tout OK, 503 sinon.
    """

    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }

    all_healthy = True

    # Check Mistral API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"}
            )

            if response.status_code == 200:
                health["checks"]["mistral_api"] = {
                    "status": "healthy",
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
                }
                logger.info("Mistral API health check: OK")
            else:
                health["checks"]["mistral_api"] = {
                    "status": "unhealthy",
                    "status_code": response.status_code
                }
                all_healthy = False
                logger.error(f"Mistral API health check failed: HTTP {response.status_code}")

    except Exception as e:
        health["checks"]["mistral_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        all_healthy = False
        logger.error(f"Mistral API health check failed: {str(e)}")

    # Status global
    if not all_healthy:
        health["status"] = "unhealthy"

    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content=health
    )
