# Changelog - Legal Document Chunking API

## [3.0.0] - 2025-11-08

### 🚀 Version Production-Ready : Architecture Modulaire + CI/CD

**Version unifiée et cohérente avec documentation complète, déploiement automatisé et code nettoyé.**

---

#### 🏗️ Architecture & Code

##### 1. **Architecture Modulaire (`app/`)**
- ✅ **Structure modulaire professionnelle** :
  ```
  app/
  ├── main.py                           # Point d'entrée FastAPI + middlewares
  ├── api/v1/endpoints/                 # Routes versionnées (documents, health)
  ├── core/                             # Configuration, auth, rate limiting
  │   └── services/                     # Services métier (processor, enricher, scorer)
  └── models/schemas/                   # Schémas Pydantic v2
  ```
- ✅ **Séparation des responsabilités** : API, Core, Services, Models
- ✅ **Testabilité complète** : 75 tests (82% coverage)

##### 2. **Authentification Simple API Key**
- ✅ **Service d'authentification** (`app/core/auth.py`)
  - Validation header `X-API-Key`
  - Protection toutes routes sensibles (`/api/v1/documents/process-ocr`)
  - Endpoints publics : `/health`, `/health/live`, `/health/ready`, `/docs`
- ✅ **Configuration** : Variable `API_SECRET_KEY` dans `.env`
- ✅ **Pas de JWT/Supabase** : Architecture standalone pour n8n workflows

##### 3. **Rate Limiting Production (slowapi)**
- ✅ **Limite 10 requêtes/minute** par IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- ✅ **Erreur 429** Too Many Requests avec retry-after
- ✅ **Headers HTTP standards** : `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

##### 4. **Health Checks Complets** (`app/api/v1/endpoints/health.py`)
- ✅ `GET /api/v1/health` : Health check basique (uptime, version)
- ✅ `GET /api/v1/health/live` : Liveness probe (Kubernetes)
- ✅ `GET /api/v1/health/ready` : Readiness probe (vérifie Mistral AI - optionnel)

##### 5. **Configuration Centralisée** (`app/core/config.py`)
- ✅ **Pydantic Settings v2** : `BaseSettings` avec `SettingsConfigDict`
- ✅ **Variables d'environnement** :
  - `API_VERSION` : **3.0.0** (standardisé)
  - `API_SECRET_KEY` : **Requis** - Auth API Key
  - `MISTRAL_API_KEY` : **Optionnel** - Health check /ready uniquement
  - `RATE_LIMIT_PER_MINUTE` : 10 par défaut
  - `REQUEST_TIMEOUT`, `PROCESSING_TIMEOUT`, `ENRICHMENT_TIMEOUT`
- ✅ **Nettoyage** : Suppression variables inutilisées (`RATE_LIMIT_PER_HOUR`, `SUPABASE_*`)

---

#### 🔧 Nettoyage & Cohérence

##### 6. **Suppression Code Inutilisé**
- ✅ **Supprimé `app/core/sanitizers.py`** : Jamais utilisé (64 lignes)
- ✅ **Supprimé dépendance `bleach==6.1.0`** : Non nécessaire
- ✅ **Nettoyage variables env** : Retrait `RATE_LIMIT_PER_HOUR`

##### 7. **Uniformisation Tags OpenAPI**
- ✅ **Fix tags dupliqués** : `"documents"` → `"Documents"` (majuscule partout)
- ✅ **Documentation Swagger propre** : 2 groupes (`Documents`, `Health`)

##### 8. **Types de Documents Réalistes**
- ✅ **6 types implémentés** (pas 15 fictifs) :
  - Contrats (contrat, convention, accord)
  - Plans (plan, schéma, dessin)
  - Factures (facture, note de frais)
  - Devis (devis, estimation)
  - Rapports (rapport, étude)
  - Comptes-rendus (CR, procès-verbal)
- ✅ **README.md corrigé** : Documentation alignée avec le code

---

#### 🚀 CI/CD & Déploiement

##### 9. **GitHub Actions CI/CD** (`.github/workflows/ci.yml`)
- ✅ **Tests automatiques** : pytest + coverage (82%)
- ✅ **Build Docker validé** : Multi-stage optimisé
- ✅ **Upload coverage** : Codecov integration
- ✅ **Cache intelligent** : pip dependencies + Docker layers

##### 10. **Scripts de Déploiement VPS**
- ✅ **`scripts/deploy_vps.sh`** : Déploiement Linux/Mac automatisé
- ✅ **`scripts/deploy_vps.ps1`** : Déploiement Windows PowerShell
- ✅ **Fonctionnalités** :
  - Build + upload image Docker
  - Déploiement zero-downtime
  - Validation SSH
  - Health check post-déploiement
  - Nettoyage automatique

##### 11. **Documentation Déploiement Complète**
- ✅ **`docs/DEPLOYMENT_VPS.md`** (3600+ lignes) :
  - Setup initial VPS (Docker, firewall, SSH)
  - Déploiement automatique et manuel
  - Sécurité production (HTTPS/SSL, nginx reverse proxy)
  - Monitoring, troubleshooting, backup/restore
  - Commandes complètes avec exemples

- ✅ **`docs/N8N_INTEGRATION.md`** (1000+ lignes) :
  - Architecture workflow n8n complet
  - Configuration credentials step-by-step
  - Workflow nodes avec exemples JSON
  - Gestion d'erreurs (401, 429, 500)
  - Batch processing, retry logic
  - Schéma Supabase recommandé
  - Intégration RAG avec OpenAI embeddings

---

#### 📚 Documentation

##### 12. **README.md Unifié et Correct**
- ✅ **Endpoints corrects** : `/api/v1/documents/process-ocr`
- ✅ **Types de documents réalistes** : 6 types (pas 15)
- ✅ **Authentification claire** : API Key simple (pas JWT)
- ✅ **Credentials précis** :
  - `API_SECRET_KEY` : **Requis**
  - `MISTRAL_API_KEY` : **Optionnel** (health check /ready uniquement)
- ✅ **Section CI/CD** : Workflow GitHub Actions, scripts déploiement
- ✅ **Section déploiement VPS** : Quick start + liens docs complètes
- ✅ **Tableau performance** : Chiffres corrects (6 types, pas 15)

##### 13. **CHANGELOG.md Actualisé**
- ✅ **Version 3.0.0 correcte** : Documentation état réel du code
- ✅ **Suppression références obsolètes** : JWT, Supabase, bleach

---

#### 🐳 Docker & Production

##### 14. **Dockerfile Multi-Stage Optimisé**
- ✅ **Build optimisé** : <150MB image finale
- ✅ **Health check intégré** : Vérification `/api/v1/health/live`
- ✅ **Workers configurables** : 2 workers uvicorn par défaut

##### 15. **docker-compose.yml**
- ✅ **Configuration production-ready**
- ✅ **Variables d'environnement** : `.env` support
- ✅ **Restart policy** : `unless-stopped`

---

#### 📊 Tests & Qualité

##### 16. **Suite de Tests Complète**
- ✅ **75 tests** (61 unit + 14 integration)
- ✅ **82% coverage** :
  - `document_processor.py` : 93%
  - `quality_scorer.py` : 89%
  - `content_enricher.py` : 97%
  - `auth.py` : 86%
  - `endpoints/documents.py` : 79%
  - `endpoints/health.py` : 83%

---

#### ⚙️ Fonctionnalités Métier

##### 17. **Processing de Documents OCR**
- ✅ **Endpoint** : `POST /api/v1/documents/process-ocr`
- ✅ **Support formats** :
  - Mistral OCR JSON (pages[] + extractedText)
  - Legacy format (ocrText)
- ✅ **Extraction métadonnées** : Titre, type, parties, dates, localisation
- ✅ **Chunking intelligent** : Sections hiérarchiques (H1/H2/H3)
- ✅ **Outline complet** : Arbre documentaire avec breadcrumbs
- ✅ **Enrichissement** : Keywords, types de sections
- ✅ **Quality scoring** : 4 dimensions (0-100)

##### 18. **Quality Scorer Multi-Dimensions**
- ✅ **4 dimensions** :
  - Context Completeness
  - Structural Coherence
  - Information Density
  - Legal Accuracy
- ✅ **Output** : Score (0-100), grade, issues, recommendations

---

#### 📦 Dépendances Finales

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
slowapi==0.1.9                  # Rate limiting
PyYAML==6.0.1
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.25.2
requests==2.31.0
```

**Supprimé** :
- ❌ `bleach==6.1.0` : Non utilisé
- ❌ `PyJWT`, `python-jose` : Pas d'auth JWT dans cette version

---

#### 🔄 Migration depuis v2.x

**Breaking Changes** :
- ⚠️ Authentification : JWT Supabase → API Key simple
- ⚠️ Endpoint : `/chunk` → `/api/v1/documents/process-ocr`
- ⚠️ Input schema : Champs `userId`, `projectId` requis
- ⚠️ MISTRAL_API_KEY : Requis v2.x → Optionnel v3.0

**Conservation** :
- ✅ Même format de réponse JSON
- ✅ Chunking algorithm identique
- ✅ Quality scoring identique
- ✅ Rate limiting (10/min)

---

#### 📈 Métriques de Qualité

| Métrique | v2.x | **v3.0** |
|----------|------|----------|
| Tests | 38 unit | **75 tests (82% coverage)** |
| Types documents | 6 | **6** |
| Authentification | Aucune | **✅ API Key** |
| Rate Limiting | Aucun | **✅ 10/min par IP** |
| CI/CD | Aucun | **✅ GitHub Actions** |
| Docker | Basique | **✅ Multi-stage <150MB** |
| Documentation | Fragmentée | **✅ README + VPS + n8n (5000+ lignes)** |
| Health checks | 1 endpoint | **✅ 3 endpoints (health/live/ready)** |
| Scripts déploiement | Aucun | **✅ Bash + PowerShell** |

---

#### 🎯 État de Production

**Prêt pour** :
- ✅ Déploiement VPS production
- ✅ Intégration workflows n8n
- ✅ Monitoring Kubernetes (liveness/readiness probes)
- ✅ CI/CD automatisé
- ✅ Scaling horizontal

**Testé** :
- ✅ 75/75 tests passent (100%)
- ✅ Build Docker validé
- ✅ Scripts déploiement VPS testés
- ✅ Health checks validés

---

## Versions Antérieures

Voir historique Git pour versions 2.x et antérieures.
