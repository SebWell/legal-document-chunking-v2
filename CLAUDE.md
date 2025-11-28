# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Legal Document Chunking API - A FastAPI application for intelligent processing of French legal construction documents with OCR, contextual metadata, and secure authentication, optimized for RAG (Retrieval-Augmented Generation) integration.

**Primary Goal:** Transform OCR text into high-quality structured chunks with complete hierarchical context, achieving 80-95% high-quality chunks (vs. 88% low-quality in the original JavaScript system).

**Target Documents:** French legal construction documents (contracts, plans, invoices, quotes, reports, meeting minutes) with automatic type detection and metadata extraction.

## Development Commands

### Running the Application

```bash
# Local development (with hot reload)
make run
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (multi-worker)
make run-prod
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing

```bash
# Run all tests (75 tests: 61 unit + 14 integration)
make test

# Run with coverage (target: 82%+)
make test-cov

# Run specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-fast          # Skip slow tests (rate limiting)

# View coverage report in browser
make test-cov-html
```

**Test Markers:**
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Tests with rate limiting delays

### Docker

```bash
# Using Makefile
make docker-build       # Build multi-stage image (<150MB)
make docker-run         # Run container with .env file
make docker-logs        # View container logs
make docker-stop        # Stop and remove container

# Using docker-compose (recommended for production)
make compose-up         # Start services
make compose-down       # Stop services
make compose-logs       # View logs
make compose-build      # Rebuild and restart
```

### Code Quality

```bash
# Format code
black app/ tests/

# Type checking
mypy app/

# Linting
flake8 app/ tests/

# Clean artifacts
make clean
```

### Installation

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
make install
# or
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your API_SECRET_KEY (required) and MISTRAL_API_KEY (optional)
```

## Architecture Overview

### High-Level Flow

```
n8n Workflow → API (FastAPI)
     ↓              ↓
Supabase      1. Authentication (API Key)
              2. Rate Limiting (10/min per IP)
              3. Sanitization (XSS protection)
              4. Document Processing Pipeline:
                 - OCR cleaning (LaTeX, artifacts)
                 - Metadata extraction (type, parties, dates)
                 - Hierarchical outline construction
                 - Intelligent chunking with context
                 - Content enrichment (NO LLM - string manipulation only)
                 - Quality scoring (multi-dimensional)
              5. Structured JSON response
```

### Core Processing Pipeline

The document processing happens in **5 sequential stages** in `app/core/services/document_processor.py`:

1. **OCR Text Cleaning** (`clean_latex_markers`)
   - Removes LaTeX patterns: `n^\circ`, `\mathrm`, `$...$`, etc.
   - Cleans artifacts and standardizes formatting

2. **Metadata Extraction** (`extract_metadata`)
   - Document type detection (6 types: contrat, plan, facture, devis, rapport, compte-rendu)
   - Parties identification (réservant/réservataire, vendeur/acquéreur)
   - Dates, locations, references, financial amounts

3. **Hierarchical Outline** (`extract_outline`)
   - Builds tree structure from H1/H2/H3 headings
   - Assigns positions and parent-child relationships
   - Creates navigable document structure

4. **Intelligent Chunking** (`chunk_text`)
   - Splits text into semantic sections (200-800 words target)
   - Preserves legal structures (articles, clauses, tables)
   - Assigns section types: legal, financial, parties, technical, temporal, risk, description
   - Extracts keywords (French stopwords filtered)
   - Generates breadcrumbs and sibling references

5. **Quality Scoring** (`app/core/services/quality_scorer.py`)
   - Multi-dimensional scoring: context, structure, information density, legal accuracy
   - Overall grade: Excellent (90+), Très bon (80-89), Bon (70-79), Moyen (60-69), Faible (<60)
   - Issues detection and recommendations

### Content Enrichment

**IMPORTANT:** `ContentEnricher` (app/core/services/content_enricher.py) does **NOT** use any LLM.
- Pure Python string manipulation to build contextual content
- Generates breadcrumb navigation
- Creates outline with position markers ("➜" and "◄── VOUS ÊTES ICI")
- Prepares sections for RAG embedding creation

### Directory Structure

```
app/
├── main.py                          # FastAPI app, middlewares, lifecycle
├── api/v1/
│   ├── endpoints/
│   │   ├── documents.py             # POST /api/v1/documents/process-ocr (protected)
│   │   └── health.py                # GET /health, /health/live, /health/ready (public)
│   └── error_handlers.py            # Global exception handlers
├── core/
│   ├── auth.py                      # API Key authentication (X-API-Key header)
│   ├── config.py                    # Pydantic Settings (env vars)
│   ├── exceptions.py                # Custom exception hierarchy
│   ├── rate_limiter.py              # slowapi rate limiting (10/min per IP)
│   ├── security.py                  # CORS, security headers middleware
│   ├── timeouts.py                  # Request timeout middleware (180s/120s/30s)
│   ├── logging_config.py            # Structured logging with request_id
│   ├── metrics.py                   # Performance metrics tracking
│   └── services/
│       ├── document_processor.py    # Main processing pipeline
│       ├── content_enricher.py      # Context enrichment (NO LLM)
│       └── quality_scorer.py        # Multi-dimensional quality scoring
└── models/schemas/
    └── document.py                  # Pydantic v2 schemas (DocumentInput, ProcessedDocument, Section, etc.)

tests/
├── conftest.py                      # Pytest fixtures (mock_settings, test_client, sample_documents)
├── integration/
│   ├── test_endpoints.py            # API endpoint integration tests
│   └── test_health.py               # Health endpoint tests
├── test_document_processor.py       # DocumentProcessor unit tests
├── test_content_enricher.py         # ContentEnricher unit tests
└── test_quality_scorer.py           # QualityScorer unit tests
```

## Key Configuration

### Environment Variables (.env)

**Required:**
- `API_SECRET_KEY` - **CRITICAL:** Used for API Key authentication. Generate with `openssl rand -hex 32`

**Optional:**
- `MISTRAL_API_KEY` - Only used for `/api/v1/health/ready` endpoint metadata
- `ENV` - development | production (affects docs visibility)
- `REQUEST_TIMEOUT` - Global request timeout (default: 180s)
- `PROCESSING_TIMEOUT` - Document processing timeout (default: 120s)
- `ENRICHMENT_TIMEOUT` - Content enrichment timeout (default: 30s)
- `RATE_LIMIT_PER_MINUTE` - Requests per minute per IP (default: 10)
- `ALLOWED_ORIGINS` - JSON array of CORS origins (default: `["http://localhost:3000"]`)
- `LOG_LEVEL` - INFO | DEBUG | WARNING | ERROR

### Security Architecture

1. **Authentication:** Simple API Key via `X-API-Key` header
   - Designed for n8n workflow integration: Supabase (user auth) → n8n (orchestration) → API (processing)
   - Protected endpoint: POST `/api/v1/documents/process-ocr`
   - Public endpoints: `/health/*`, `/docs` (if not production)

2. **Rate Limiting:** slowapi with 10 req/min per IP (configurable)
   - Returns 429 with `Retry-After` header
   - Logs attempts in structured format

3. **Input Validation:**
   - Pydantic v2 strict schemas
   - XSS sanitization (detects `<script>`, `javascript:`, `data:`)
   - Repeated character protection (DoS prevention)

4. **Security Headers:**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000`
   - `Content-Security-Policy: default-src 'self'`

## Important Technical Details

### Request/Response Format

**Input (POST /api/v1/documents/process-ocr):**
```json
{
  "extractedText": "Full OCR text...",
  "userId": "uuid",
  "projectId": "uuid",
  "documentId": "doc-id",
  "mistralResponseTime": 1250  // Optional
}
```

**Response:**
```json
{
  "documentId": "20250930120000123",
  "documentType": "contrat",
  "documentTitle": "CONTRAT DE RESERVATION VEFA",
  "metadata": { "parties": {...}, "date": "...", "location": "..." },
  "outline": { "nodes": [...] },  // Hierarchical structure
  "sections": [
    {
      "sectionId": "section_1",
      "content": "...",
      "breadcrumb": "CONTRAT > IDENTIFICATION > Article 1",
      "h1": "IDENTIFICATION DES PARTIES",
      "title": "Article 1 - Le Réservant",
      "type": "legal",
      "keywords": ["réservant", "société", "RCS"],
      "wordCount": 65,
      "sectionPosition": 1
    }
  ],
  "qualityScore": {
    "overallScore": 0.87,
    "dimensions": { "contextCompleteness": 0.92, ... },
    "issues": [],
    "strengths": [...],
    "recommendations": []
  },
  "stats": { "totalSections": 12, "totalWords": 3450, ... },
  "processingTime": 1.45,
  "version": "3.0.0"
}
```

### Logging & Observability

- **Structured logging** with request_id context (see `app/core/logging_config.py`)
- **Request ID** added to all responses via `X-Request-ID` header
- **Health endpoints:**
  - `/api/v1/health` - Basic health check
  - `/api/v1/health/live` - Liveness probe (Kubernetes)
  - `/api/v1/health/ready` - Readiness probe (checks Mistral API)
- **Metrics tracking** via `app/core/metrics.py`

### Performance Expectations

- **Processing time:** ~1.2-1.5s per document (includes enrichment)
- **Quality scores:** 80-95% of chunks score ≥70 (vs. 88% <60 in legacy system)
- **Test coverage:** 82% (target: maintain above 80%)

### Common Patterns

**Adding a new document type:**
1. Update `DOCUMENT_TYPES` dict in `DocumentProcessor` (app/core/services/document_processor.py:53)
2. Add type-specific keywords if needed
3. Update tests in `tests/test_document_processor.py`

**Adding a new section type:**
1. Update `SECTION_TYPE_KEYWORDS` dict in `DocumentProcessor` (app/core/services/document_processor.py:63)
2. Update `_classify_section_type` method logic
3. Add test cases for new type

**Modifying timeout values:**
- Global: `REQUEST_TIMEOUT` in .env
- Processing: `PROCESSING_TIMEOUT` in .env
- Enrichment: `ENRICHMENT_TIMEOUT` in .env
- See `app/core/timeouts.py` for middleware implementation

## Deployment

### VPS Deployment
```bash
# Set environment variables
export VPS_HOST="your-vps-ip"
export API_SECRET_KEY="your-secure-key"
export MISTRAL_API_KEY="your-mistral-key"

# Deploy
./scripts/deploy_vps.sh  # Linux/Mac
.\scripts\deploy_vps.ps1  # Windows
```

See `docs/DEPLOYMENT_VPS.md` for complete deployment guide.

### n8n Integration

Workflow: Supabase trigger → n8n HTTP Request → API → Store results

See `docs/N8N_INTEGRATION.md` for:
- Complete workflow setup
- Authentication configuration
- Error handling
- Rate limiting strategies

### CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Runs on push/PR
- Executes all 75 tests
- Builds Docker image
- Uploads coverage to Codecov
- Caches dependencies for speed

## Development Guidelines

### When Adding Features

1. **Always write tests first** - Maintain 80%+ coverage
2. **Update schemas** in `app/models/schemas/document.py` if changing data structures
3. **Add logging** with structured context for debugging
4. **Consider timeouts** - Processing can be slow on large documents
5. **Update CHANGELOG.md** following Keep a Changelog format
6. **Test with real French legal documents** - OCR output varies significantly

### When Debugging

1. Check **structured logs** with request_id for request tracing
2. Use `/api/v1/health/ready` to verify external dependencies (Mistral API)
3. Enable `DEBUG=true` in .env for detailed logging
4. Review `qualityScore.issues` in response for quality problems
5. Test with `make test-fast` to skip slow rate limit tests

### Common Gotchas

- **LaTeX cleaning:** Add new patterns to `LATEX_PATTERNS` in DocumentProcessor
- **French stopwords:** Update `STOPWORDS` set for better keyword extraction
- **Rate limiting:** Use `@pytest.mark.slow` for tests that trigger rate limits
- **Pydantic v2:** Use `model_config` instead of `Config` class
- **CORS:** Whitelist origins in `ALLOWED_ORIGINS` (JSON array string)
- **Content enrichment:** NO LLM calls - pure string manipulation only

### Version History

- **v3.0.0** (Current): API Key auth, rate limiting, multi-dimensional quality scoring, 82% test coverage
- **v2.x**: Basic processing pipeline, 80-95% high-quality chunks
- **v1.x (Legacy JS)**: 88% low-quality chunks, no authentication

For detailed changes, see CHANGELOG.md.
