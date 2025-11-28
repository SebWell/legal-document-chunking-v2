# Legal Document Chunking API

API FastAPI pour le traitement intelligent de documents juridiques français avec OCR, métadonnées contextuelles complètes et système d'authentification sécurisé, optimisée pour le secteur de la construction et l'intégration RAG.

## 🎯 Objectif

Transformer un système JavaScript n8n produisant 88% de chunks de faible qualité en une solution Python moderne atteignant <20% de chunks de faible qualité avec préservation du contexte documentaire, authentification JWT et rate limiting.

**Résultats obtenus v3.0** : 5-15% de chunks de faible qualité + 80-95% de chunks haute qualité + contexte complet préservé + sécurité production-ready

## 🏗️ Types de documents supportés

### 📋 Détection automatique de 6 types :

- **Contrats** - Contrats, conventions, accords, engagements
- **Plans** - Plans, schémas, dessins, croquis
- **Factures** - Factures, notes de frais, avoirs
- **Devis** - Devis, estimations, cotations
- **Rapports** - Rapports, études, analyses
- **Comptes-rendus** - Comptes-rendus, procès-verbaux (PV)

### 🔍 Extraction intelligente :
- **Métadonnées documentaires** : Titre, type, référence
- **Parties contractuelles** : Identification automatique des parties
- **Dates clés** : Dates de signature, création, échéances
- **Références légales** : Articles de loi, code civil, etc.
- **Montants financiers** : Détection des montants et conditions de paiement
- **Localisation** : Extraction des lieux et adresses

## 🚀 Installation

### 💻 Installation locale (développement)

```bash
# Cloner le repository
git clone https://github.com/SebWell/legal-document-chunking.git
cd legal-document-chunking

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos credentials

# Lancer l'API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 🐳 Installation Docker

```bash
# Cloner le repository
git clone https://github.com/SebWell/legal-document-chunking.git
cd legal-document-chunking

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos credentials

# Option 1: Docker Compose (recommandé)
docker-compose up -d

# Option 2: Docker simple
make docker-build
make docker-run

# Vérifier les logs
docker-compose logs -f api
# ou
make docker-logs

# Arrêter
docker-compose down
# ou
make docker-stop
```

**Avantages Docker** :
- ✅ Build reproductible
- ✅ Isolation complète
- ✅ Multi-stage optimisé (<150MB)
- ✅ Health checks automatiques
- ✅ Prêt pour production

### 🌐 Déploiement VPS (production)

Pour déployer l'API sur un VPS en production :

```bash
# Configuration
export VPS_HOST="your-vps-ip"
export API_SECRET_KEY="your-secure-api-key"
export MISTRAL_API_KEY="your-mistral-api-key"

# Déploiement automatique
./scripts/deploy_vps.sh

# Ou sur Windows
.\scripts\deploy_vps.ps1
```

**Documentation complète** :
- 📚 [Guide de déploiement VPS](docs/DEPLOYMENT_VPS.md) - Setup complet, sécurité, monitoring
- 🔄 [Intégration n8n](docs/N8N_INTEGRATION.md) - Workflows complets, exemples, troubleshooting

### 🔑 Configuration requise (.env)

```env
# Application
ENV=development
LOG_LEVEL=DEBUG
PORT=8000

# Authentication (API Key pour n8n workflow - REQUIRED)
# IMPORTANT: Generate a secure random key for production!
# Example: openssl rand -hex 32
API_SECRET_KEY=your-secure-api-key-replace-this-in-production

# Mistral AI (Optional - used only for health check /ready)
MISTRAL_API_KEY=your_mistral_api_key_here

# Timeouts (seconds)
REQUEST_TIMEOUT=180
PROCESSING_TIMEOUT=120
ENRICHMENT_TIMEOUT=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
```

**⚠️ Credentials** :
1. `API_SECRET_KEY` : **Requis** - Clé secrète pour authentification API Key
2. `MISTRAL_API_KEY` : **Optionnel** - Clé API Mistral AI (https://console.mistral.ai/) - Utilisée uniquement pour le health check `/api/v1/health/ready`

## 📡 API Endpoints

### 🔐 Authentification

Tous les endpoints de processing nécessitent une clé API valide dans le header `X-API-Key`.

**Endpoints protégés** :
- ✅ `POST /api/v1/documents/process-ocr` - Requiert authentification

**Endpoints publics** (pas d'authentification) :
- 🔓 `GET /api/v1/health` - Health check basique
- 🔓 `GET /api/v1/health/live` - Liveness probe
- 🔓 `GET /api/v1/health/ready` - Readiness probe (vérifie Mistral AI)
- 🔓 `GET /docs` - Documentation interactive Swagger

**Header requis** :
```bash
X-API-Key: <votre_api_secret_key>
```

**Architecture** : L'API est conçue pour être intégrée dans un workflow n8n sécurisé (Supabase → n8n → API).

**Rate Limiting** : 10 requêtes/minute par IP (configurable via `RATE_LIMIT_PER_MINUTE`)

### POST `/api/v1/documents/process-ocr`

Traitement OCR intelligent d'un document avec chunking, métadonnées et scoring qualité.

**Headers** :
```json
{
  "X-API-Key": "<your_api_secret_key>",
  "Content-Type": "application/json"
}
```

**Payload** :
```json
{
  "extractedText": "Votre texte de document juridique...",
  "userId": "uuid-user-123",
  "projectId": "uuid-project-456",
  "documentId": "doc-789",
  "mistralResponseTime": 1250
}
```

**Réponse** :
```json
{
  "documentId": "20250930120000123",
  "documentType": "contrat",
  "documentTitle": "CONTRAT DE RESERVATION VEFA",
  "documentReference": "REF-2025-001",
  "metadata": {
    "parties": {
      "reservant": "SCCV LA VALLEE",
      "reservataire": "M. DUPONT"
    },
    "date": "30/09/2025",
    "location": "MONTEVRAIN",
    "project": "LE NEST"
  },
  "outline": {
    "nodes": [
      {
        "id": "node_1",
        "level": 1,
        "title": "IDENTIFICATION DES PARTIES",
        "position": 0
      }
    ]
  },
  "sections": [
    {
      "sectionId": "section_1",
      "documentType": "contrat",
      "documentTitle": "CONTRAT DE RESERVATION VEFA",
      "h1": "IDENTIFICATION DES PARTIES",
      "title": "Article 1 - Le Réservant",
      "type": "legal",
      "content": "La société SCCV LA VALLEE, inscrite au RCS...",
      "wordCount": 65,
      "keywords": ["réservant", "société", "RCS"],
      "sectionPosition": 1,
      "breadcrumb": "CONTRAT > IDENTIFICATION DES PARTIES > Article 1",
      "parentSection": null,
      "siblingSections": ["section_2", "section_3"]
    }
  ],
  "stats": {
    "totalSections": 12,
    "totalWords": 3450,
    "avgWordsPerSection": 287,
    "minWords": 45,
    "maxWords": 650,
    "uniqueKeywords": 85
  },
  "qualityScore": {
    "overallScore": 0.87,
    "dimensions": {
      "contextCompleteness": 0.92,
      "structuralCoherence": 0.85,
      "informationDensity": 0.84,
      "legalAccuracy": 0.88
    },
    "issues": [],
    "strengths": [
      "Complete hierarchical context",
      "High information density",
      "Strong legal terminology"
    ],
    "recommendations": []
  },
  "processingTime": 1.45,
  "version": "3.0.0"
}
```

### GET `/health`

Vérification de l'état de l'API (pas d'authentification requise).

### GET `/docs`

Documentation interactive Swagger/OpenAPI (pas d'authentification requise).

## 🔒 Sécurité v3.0

### 🔐 Authentification API Key
- ✅ Simple API Key authentication pour workflow n8n
- ✅ Validation du header `X-API-Key`
- ✅ Protection de toutes les routes sensibles
- ✅ Architecture: Supabase (auth) → n8n (orchestration) → API (processing)

### 🚦 Rate Limiting (slowapi)
- ✅ **10 requêtes/minute** par adresse IP (configurable)
- ✅ Protection contre abus et surcharge
- ✅ Réponse 429 avec header `Retry-After` si limite dépassée
- ✅ Logging des tentatives de dépassement

### 🛡️ Protection des Entrées
- ✅ **Sanitization XSS** : Détection patterns dangereux (script tags, javascript:, data:)
- ✅ **Validation Pydantic v2** : Validation stricte des schémas
- ✅ **Limite répétitions** : Protection DoS sur caractères répétés

### 🌐 CORS et Headers Sécurisés
- ✅ **CORS strict** : Origines whitelistées uniquement (pas de `allow_origins=["*"]`)
- ✅ **Security Headers** :
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000`
  - `Content-Security-Policy: default-src 'self'`

### 📋 Gestion d'Erreurs Structurée
- ✅ Exception hierarchy personnalisée
- ✅ Codes d'erreur standardisés (AUTH_ERROR, VALIDATION_ERROR, RATE_LIMIT_EXCEEDED, etc.)
- ✅ Logging structuré avec request_id pour traçabilité
- ✅ Réponses JSON cohérentes avec timestamps

## 🔧 Architecture v3.0

### 📁 Structure Modulaire

```
app/
├── main.py                          # Point d'entrée FastAPI + middlewares
├── api/v1/
│   ├── endpoints/
│   │   └── documents.py            # Routes /api/v1/documents/*
│   └── error_handlers.py           # Handlers globaux d'exceptions
├── core/
│   ├── auth.py                     # Service d'authentification JWT
│   ├── config.py                   # Configuration Pydantic Settings
│   ├── exceptions.py               # Hiérarchie d'exceptions custom
│   ├── rate_limiter.py             # Rate limiting (slowapi)
│   ├── sanitizers.py               # Sanitization XSS
│   ├── security.py                 # Middlewares CORS/Headers
│   └── services/
│       ├── content_enricher.py     # Enrichissement contenu (Mistral AI)
│       ├── document_processor.py   # Chunking + extraction métadonnées
│       └── quality_scorer.py       # Scoring qualité multi-dimensions
└── models/schemas/
    └── document.py                 # Schémas Pydantic v2
```

### 🔄 Flux de Traitement

1. **Authentification** : Vérification API Key (header X-API-Key)
2. **Rate Limiting** : Contrôle 10 req/min par IP
3. **Sanitization** : Nettoyage entrées XSS
4. **Validation** : Schémas Pydantic v2
5. **Processing** :
   - Nettoyage OCR (LaTeX, artefacts)
   - Extraction métadonnées (type, parties, dates, localisation)
   - Construction outline hiérarchique
   - Chunking intelligent avec contexte
   - Enrichissement contenu (Mistral AI)
   - Scoring qualité multi-dimensions
6. **Response** : JSON structuré avec qualité + stats + métriques

## 🎯 Fonctionnalités

### 🧠 Chunking Intelligent
- Segmentation basée sur les phrases avec contexte sémantique
- Respect des structures juridiques (articles, clauses, tableaux)
- Préservation du contexte avec outline hiérarchique
- Adaptation automatique selon le type de document

### 📋 Extraction de Métadonnées Avancées
- **Identification automatique** de 15 types de documents juridiques
- **Extraction des parties** (réservant/réservataire, bailleur/locataire, etc.)
- **Dates principales** (signature, création, échéances)
- **Localisation** et projets immobiliers
- **ID standardisé** pour traçabilité complète

### 🔍 Reconnaissance de Patterns Juridiques
- Clauses contractuelles et articles de loi
- Références légales (Code civil, CCH, etc.)
- Montants financiers et échéanciers
- Obligations et responsabilités des parties
- Terminologie spécialisée du bâtiment

### ⚡ Optimisation RAG
- **Structure JSON optimisée** pour l'intégration RAG
- **Contexte hiérarchique complet** dans chaque section (breadcrumb, outline)
- **Références sources professionnelles** sans numéros internes
- **Traçabilité utilisateur/projet** pour chaque section
- **Métadonnées enrichies** (entités, qualité, classification)

### 📊 Scoring Qualité Multi-Dimensions
- **Overall Score** (0-100) : Score global de qualité
- **Grade** : "Excellent" (90+), "Très bon" (80-89), "Bon" (70-79), "Moyen" (60-69), "Faible" (<60)
- **Metrics** : Statistiques détaillées (sections, mots, keywords, hiérarchie)
- **Issues** : Liste des problèmes détectés avec impact (OCR, contenu, structure, métadonnées)
- **Needs Review** : Flag indiquant si une révision manuelle est recommandée

## 📊 Performance

| Métrique | Ancien JS | v2.x | **v3.0** | Amélioration |
|----------|-----------|------|----------|--------------|
| **Chunks haute qualité (≥70)** | 0% | 80-95% | **80-95%** | **+95%** |
| **Score qualité moyen** | 12/100 | 75-80 | **75-85** | **+525%** |
| **Chunks faible qualité** | 88% | 5-15% | **5-10%** | **-88%** |
| **Types de documents** | 0 | 6 | **6** | **+600%** |
| **Authentification** | ❌ Aucune | ❌ Aucune | **✅ API Key** | **Nouveau** |
| **Rate Limiting** | ❌ Aucun | ❌ Aucun | **✅ 10/min par IP** | **Nouveau** |
| **Tests** | ❌ Aucun | 38 unit | **75 tests (82% coverage)** | **Nouveau** |
| **Observabilité** | ❌ Basique | ❌ Basique | **✅ Logging + Health + Metrics** | **Nouveau** |
| **Docker** | ❌ Non | ❌ Non | **✅ Multi-stage (<150MB)** | **Nouveau** |
| **Architecture** | Monolithique | Monolithique | **✅ Modulaire** | **Nouveau** |
| **Scoring qualité** | ❌ Aucun | Simple | **✅ Grade + Issues + Metrics** | **Nouveau** |
| **Enrichissement IA** | ❌ Aucun | ❌ Aucun | **✅ Mistral AI** | **Nouveau** |
| **Timeouts** | ❌ Aucun | ❌ Aucun | **✅ 3 niveaux (180s/120s/30s)** | **Nouveau** |
| **Pydantic** | v1 | v1 | **✅ v2** | **Nouveau** |
| **Temps de traitement** | Variable | ~100ms | **~1.2-1.5s** | (Enrichissement IA) |
| **Contexte préservé** | 0% | ✅ 100% | **✅ 100%** | **Maintenu** |

## 🛠️ Développement

### Tests
```bash
# Lancer tous les tests
make test
# ou
pytest tests/ -v

# Tests avec couverture
make test-cov

# Tests unitaires uniquement
make test-unit

# Tests d'intégration uniquement
make test-integration

# Tests rapides (sans rate limiting)
make test-fast
```

**Statut** : ✅ **75/75 tests passent** (61 unit + 14 integration) | **82% coverage**

**Couverture par module** :
- `document_processor.py`: 93%
- `quality_scorer.py`: 89%
- `content_enricher.py`: 97%
- `auth.py`: 86%
- `endpoints/documents.py`: 79%
- `endpoints/health.py`: 83%

### Linting
```bash
# Format code
black app/ tests/

# Check types
mypy app/

# Lint
flake8 app/ tests/
```

## 📝 Licence

MIT License

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez créer une issue ou une pull request.

## 📞 Support

Pour toute question ou problème, créez une issue sur ce repository.

## 🔄 CI/CD et Déploiement

### GitHub Actions

Le projet inclut un workflow CI/CD automatique :

- ✅ **Tests automatiques** sur chaque push/PR
- ✅ **Build Docker** validé à chaque commit
- ✅ **Coverage reports** uploadés sur Codecov
- ✅ **Cache intelligent** pour accélérer les builds

Workflow : [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

### Scripts de déploiement

Scripts prêts à l'emploi pour déployer sur VPS :

- 🐧 **Linux/Mac** : `scripts/deploy_vps.sh`
- 🪟 **Windows** : `scripts/deploy_vps.ps1`

**Fonctionnalités** :
- Build et upload automatique de l'image Docker
- Déploiement zero-downtime
- Vérification de santé post-déploiement
- Nettoyage automatique des anciennes images

---

## 🗺️ Roadmap

### v3.1.0 (Court terme)
- [x] Docker multi-stage optimisé
- [x] Tests complets (75 tests, 82% coverage)
- [x] Observabilité (logging, health, metrics, timeouts)
- [x] CI/CD GitHub Actions
- [x] Scripts de déploiement VPS
- [x] Documentation déploiement et intégration n8n
- [ ] Endpoint batch processing
- [ ] Export métriques Prometheus

### v3.2.0 (Moyen terme)
- [ ] Cache Redis pour rate limiting distribué
- [ ] Webhook notifications
- [ ] API versioning avancé
- [ ] Support multi-langues (anglais)

### v4.0.0 (Long terme)
- [ ] ML classification avancée
- [ ] Auto-apprentissage avec feedback loop
- [ ] GraphQL API
- [ ] Microservices architecture
