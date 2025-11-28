"""
Fixtures globales pour tous les tests.

Simplified fixtures for n8n workflow integration (API Key auth).
"""

import pytest
import os
from fastapi.testclient import TestClient
from typing import Dict

from app.main import app
from app.core.config import get_settings

settings = get_settings()


# ===== CONFIGURATION ENVIRONNEMENT =====

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Configure l'environnement de test avant tous les tests.
    Autouse = True signifie que ce fixture s'exécute automatiquement.
    """
    # Set API Key for tests (safe test value, not a real secret)
    test_api_key = "test-api-key-do-not-use-in-production"
    os.environ["API_SECRET_KEY"] = test_api_key

    # Reload settings to pick up environment variable
    from app.core.config import get_settings
    settings = get_settings()
    settings.API_SECRET_KEY = test_api_key

    yield

    # Cleanup after all tests
    if "API_SECRET_KEY" in os.environ:
        del os.environ["API_SECRET_KEY"]


# ===== FIXTURES CLIENT =====

@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    Client de test FastAPI (scope session).
    Créé une seule fois pour tous les tests.
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def client() -> TestClient:
    """
    Client de test FastAPI (scope function).
    Créé pour chaque test.
    """
    return TestClient(app)


# ===== FIXTURES AUTH (API KEY) =====

@pytest.fixture(scope="session")
def api_key() -> str:
    """API Key valide pour les tests (safe test value, not a real secret)."""
    return "test-api-key-do-not-use-in-production"


@pytest.fixture(scope="session")
def invalid_api_key() -> str:
    """API Key invalide pour les tests."""
    return "invalid-key-123"


@pytest.fixture(scope="function")
def auth_headers(api_key: str) -> Dict[str, str]:
    """
    Headers avec authentification API Key valide.
    """
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def invalid_auth_headers(invalid_api_key: str) -> Dict[str, str]:
    """
    Headers avec API Key invalide.
    """
    return {
        "X-API-Key": invalid_api_key,
        "Content-Type": "application/json"
    }


# ===== FIXTURES DATA =====

@pytest.fixture(scope="session")
def test_user_id() -> str:
    """ID utilisateur de test."""
    return "test-user-123"


@pytest.fixture(scope="session")
def test_project_id() -> str:
    """ID projet de test."""
    return "test-project-456"


@pytest.fixture(scope="session")
def test_document_id() -> str:
    """ID document de test."""
    return "test-doc-789"


@pytest.fixture(scope="session")
def sample_ocr_text() -> str:
    """
    Texte OCR de test (document valide).
    """
    return """
# CONTRAT PRELIMINAIRE DE RESERVATION

**PROGRAMME** : Résidence LES JARDINS DE MONTEVRAIN

## Article 1 - Objet du contrat

Le présent contrat a pour objet la réservation d'un bien immobilier situé dans le programme
LES JARDINS DE MONTEVRAIN, composé d'un appartement de type T3 au 2ème étage.

## Article 2 - Prix de vente

Le prix de vente est fixé à la somme de **250 000 euros TTC** (deux cent cinquante mille euros),
décomposé comme suit :
- Prix du logement : 240 000 euros
- Prix du parking : 10 000 euros

## Article 3 - Conditions suspensives

La vente est soumise aux conditions suspensives suivantes :
- Obtention du permis de construire définitif
- Obtention du financement bancaire par l'acquéreur dans un délai de 45 jours
- Purge du droit de préemption urbain

## Article 4 - Délai de réalisation

La livraison du bien est prévue pour le **4ème trimestre 2024**.
Les travaux débuteront au 1er trimestre 2023 sous réserve d'obtention du permis de construire.

## Article 5 - Garanties

Le vendeur s'engage à fournir les garanties suivantes :
- Garantie de parfait achèvement (1 an)
- Garantie biennale (2 ans)
- Garantie décennale (10 ans)
- Assurance dommages-ouvrage

Fait à Montevrain, le 15 septembre 2025
En deux exemplaires originaux

**LE RESERVANT** : SCCV LES JARDINS DE MONTEVRAIN
**LE RESERVATAIRE** : M. Jean DUPONT
"""


@pytest.fixture(scope="function")
def sample_request_body(
    sample_ocr_text: str,
    test_user_id: str,
    test_project_id: str,
    test_document_id: str
) -> Dict:
    """
    Corps de requête valide pour POST /api/v1/documents/process-ocr.
    """
    return {
        "extractedText": sample_ocr_text,
        "userId": test_user_id,
        "projectId": test_project_id,
        "documentId": test_document_id,
        "mistralResponseTime": 1250
    }


# ===== FIXTURES MOCKS =====

@pytest.fixture
def mock_mistral_api(mocker):
    """
    Mock de l'API Mistral pour tests sans appels réels.
    """
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Mocked enrichment content"
                }
            }
        ]
    }

    return mocker.patch(
        "httpx.AsyncClient.post",
        return_value=mock_response
    )


# ===== CONFIGURATION PYTEST =====

def pytest_configure(config):
    """Configuration globale pytest."""
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (rate limiting, etc.)"
    )
