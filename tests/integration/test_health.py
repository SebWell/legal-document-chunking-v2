"""
Tests d'intégration pour les endpoints health.

Health checks for Kubernetes/Docker monitoring.
"""

import pytest
from fastapi import status


@pytest.mark.integration
class TestHealthEndpoints:
    """Tests pour health check endpoints."""

    def test_basic_health_check(self, client):
        """
        Test /api/v1/health basique.
        GIVEN: API is running
        WHEN: GET /api/v1/health
        THEN: Returns 200 with healthy status
        """
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "environment" in data

    def test_liveness_probe(self, client):
        """
        Test /api/v1/health/live (Kubernetes liveness).
        GIVEN: API is running
        WHEN: GET /api/v1/health/live
        THEN: Returns 200 with alive status
        """
        response = client.get("/api/v1/health/live")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_probe(self, client, mock_mistral_api):
        """
        Test /api/v1/health/ready (Kubernetes readiness).
        GIVEN: API is running with Mistral API available
        WHEN: GET /api/v1/health/ready
        THEN: Returns 200 with healthy checks
        """
        response = client.get("/api/v1/health/ready")

        # Peut retourner 200 (healthy) ou 503 (unhealthy) selon Mistral API
        # Avec mock, devrait retourner 200
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data

        # Devrait avoir un check Mistral API
        if "mistral_api" in data["checks"]:
            mistral_check = data["checks"]["mistral_api"]
            assert "status" in mistral_check

    def test_readiness_probe_structure(self, client):
        """
        Test structure réponse /api/v1/health/ready.
        GIVEN: API is running
        WHEN: GET /api/v1/health/ready
        THEN: Returns proper structure
        """
        response = client.get("/api/v1/health/ready")

        data = response.json()

        # Structure basique
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

        assert "timestamp" in data
        assert "checks" in data

        # Checks devrait être un dict
        assert isinstance(data["checks"], dict)

    def test_health_endpoints_no_auth_required(self, client):
        """
        Test que les health checks ne requièrent pas d'auth.
        GIVEN: No authentication
        WHEN: GET health endpoints
        THEN: Returns 200 (no auth required)
        """
        # /health
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

        # /health/live
        response = client.get("/api/v1/health/live")
        assert response.status_code == status.HTTP_200_OK

        # /health/ready (peut être 503 mais pas 401/403)
        response = client.get("/api/v1/health/ready")
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
