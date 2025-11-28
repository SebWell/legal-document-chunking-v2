# 🔄 Intégration n8n - Legal Document Chunking API

Guide complet pour intégrer l'API Legal Document Chunking dans vos workflows n8n.

## 📋 Architecture du workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow n8n complet                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Trigger (Webhook/Schedule/Supabase)                     │
│     - Réception nouveau document                             │
│     - Document ID + User ID + Project ID                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Supabase - Récupérer document                           │
│     GET /rest/v1/documents?id=eq.{documentId}               │
│     Output: { extractedText, userId, projectId }            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. HTTP Request - Legal Document Chunking API              │
│     POST /api/v1/documents/process-ocr                      │
│     Header: X-API-Key                                        │
│     Body: { extractedText, userId, projectId, documentId }  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Supabase - Sauvegarder chunks                           │
│     POST /rest/v1/document_chunks                           │
│     Body: sections[] from API response                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ Configuration n8n

### Ajouter les credentials

#### A. API Key Legal Document Chunking

1. Dans n8n : **Settings** → **Credentials** → **New**
2. Type : **Header Auth**
3. Configuration :
   ```
   Name: Legal Document Chunking API Key
   Header Name: X-API-Key
   Header Value: your-api-secret-key-here
   ```
4. **Save**

#### B. Supabase (si non configuré)

1. **Settings** → **Credentials** → **New**
2. Type : **Supabase API**
3. Configuration :
   ```
   Name: Supabase Production
   Host: your-project.supabase.co
   Service Role Secret: your-supabase-service-role-key
   ```
4. **Save**

---

## 2️⃣ Workflow complet : Process Legal Document

### Node 1 : Webhook Trigger

```json
{
  "node": "Webhook",
  "type": "n8n-nodes-base.webhook",
  "parameters": {
    "httpMethod": "POST",
    "path": "legal-document-process",
    "responseMode": "responseNode",
    "options": {}
  }
}
```

**Payload attendu** :
```json
{
  "documentId": "doc-123",
  "userId": "user-456",
  "projectId": "project-789"
}
```

### Node 2 : Supabase - Get Document

```json
{
  "node": "Supabase - Get Document",
  "type": "n8n-nodes-base.supabase",
  "credentials": "Supabase Production",
  "parameters": {
    "operation": "getAll",
    "tableId": "documents",
    "returnAll": false,
    "filters": {
      "conditions": [
        {
          "column": "id",
          "operator": "eq",
          "value": "={{ $json.documentId }}"
        }
      ]
    }
  }
}
```

### Node 3 : HTTP Request - Legal Document Chunking API

```json
{
  "node": "Process with Legal API",
  "type": "n8n-nodes-base.httpRequest",
  "credentials": "Legal Document Chunking API Key",
  "parameters": {
    "method": "POST",
    "url": "http://your-vps-ip:8000/api/v1/documents/process-ocr",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "headerAuth",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "extractedText",
          "value": "={{ $json.extracted_text }}"
        },
        {
          "name": "userId",
          "value": "={{ $('Webhook').item.json.userId }}"
        },
        {
          "name": "projectId",
          "value": "={{ $('Webhook').item.json.projectId }}"
        },
        {
          "name": "documentId",
          "value": "={{ $('Webhook').item.json.documentId }}"
        }
      ]
    },
    "options": {
      "timeout": 180000,
      "redirect": {
        "followRedirects": true
      }
    }
  }
}
```

### Node 4 : Function - Transform Sections

```javascript
// Transformer les sections pour Supabase
const response = $input.item.json;
const sections = response.sections;

const transformedSections = sections.map(section => ({
  document_id: response.documentId,
  section_id: section.sectionId,
  document_type: section.documentType,
  document_title: section.documentTitle,
  h1: section.h1,
  h2: section.h2 || null,
  h3: section.h3 || null,
  title: section.title,
  type: section.type,
  content: section.content,
  word_count: section.wordCount,
  keywords: section.keywords,
  section_position: section.sectionPosition,
  breadcrumb: section.breadcrumb,
  parent_section: section.parentSection,
  sibling_sections: section.siblingSections,
  created_at: new Date().toISOString()
}));

return transformedSections.map(item => ({ json: item }));
```

### Node 5 : Supabase - Insert Chunks

```json
{
  "node": "Supabase - Save Chunks",
  "type": "n8n-nodes-base.supabase",
  "credentials": "Supabase Production",
  "parameters": {
    "operation": "insert",
    "tableId": "document_chunks",
    "options": {
      "upsert": false
    }
  }
}
```

### Node 6 : Supabase - Update Document Status

```json
{
  "node": "Update Document Status",
  "type": "n8n-nodes-base.supabase",
  "credentials": "Supabase Production",
  "parameters": {
    "operation": "update",
    "tableId": "documents",
    "filterType": "manual",
    "matchBy": [
      {
        "column": "id",
        "value": "={{ $('Webhook').item.json.documentId }}"
      }
    ],
    "fieldsToUpdate": {
      "values": [
        {
          "column": "status",
          "value": "processed"
        },
        {
          "column": "processing_time",
          "value": "={{ $('Process with Legal API').item.json.processingTime }}"
        },
        {
          "column": "quality_score",
          "value": "={{ $('Process with Legal API').item.json.qualityScore.overallScore }}"
        },
        {
          "column": "processed_at",
          "value": "={{ new Date().toISOString() }}"
        }
      ]
    }
  }
}
```

### Node 7 : Respond to Webhook

```json
{
  "node": "Respond to Webhook",
  "type": "n8n-nodes-base.respondToWebhook",
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ JSON.stringify({\n  success: true,\n  documentId: $('Webhook').item.json.documentId,\n  sectionsCount: $('Process with Legal API').item.json.stats.totalSections,\n  qualityScore: $('Process with Legal API').item.json.qualityScore.overallScore,\n  processingTime: $('Process with Legal API').item.json.processingTime\n}) }}"
  }
}
```

---

## 3️⃣ Workflow simplifié : Test rapide

Pour tester rapidement l'API sans Supabase :

### Nodes minimum

1. **Manual Trigger** (ou Webhook)
2. **HTTP Request - Legal API**
3. **Set** (pour afficher le résultat)

### Configuration HTTP Request

```javascript
// URL
http://your-vps-ip:8000/api/v1/documents/process-ocr

// Method
POST

// Authentication
Header Auth (credential créée précédemment)

// Body (JSON)
{
  "extractedText": "CONTRAT DE RESERVATION VEFA\n\nLe réservant : SCCV LA VALLEE, société civile de construction-vente...",
  "userId": "test-user-123",
  "projectId": "test-project-456",
  "documentId": "test-doc-789"
}

// Headers
Content-Type: application/json
X-API-Key: your-api-secret-key (automatique via credential)

// Options
- Timeout: 180000ms (3 minutes)
- Follow Redirects: true
```

---

## 4️⃣ Gestion des erreurs

### Node : Error Handler

Ajouter après le node "Process with Legal API" :

```json
{
  "node": "Error Handler",
  "type": "n8n-nodes-base.if",
  "parameters": {
    "conditions": {
      "string": [
        {
          "value1": "={{ $json.status }}",
          "operation": "notEqual",
          "value2": "200"
        }
      ]
    }
  }
}
```

### Exemples d'erreurs

#### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "detail": "Invalid API key",
  "status_code": 401
}
```

**Solution** : Vérifier la credential "X-API-Key"

#### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please try again later.",
  "status_code": 429,
  "retry_after": 60
}
```

**Solution** : Ajouter un délai entre les requêtes (Rate Limit: 10/min par IP)

#### 500 Internal Server Error
```json
{
  "error": "Processing error",
  "detail": "An error occurred while processing the document",
  "request_id": "req-123",
  "status_code": 500
}
```

**Solution** : Vérifier les logs de l'API (`docker logs legal-document-chunking-api`)

---

## 5️⃣ Optimisations

### Batch Processing

Pour traiter plusieurs documents :

```javascript
// Node: Function - Batch Processor
const documents = $input.all();
const results = [];

for (const doc of documents) {
  // Appel API pour chaque document
  const result = await $http.request({
    method: 'POST',
    url: 'http://your-vps-ip:8000/api/v1/documents/process-ocr',
    headers: {
      'X-API-Key': '{{ $credentials.apiKey }}',
      'Content-Type': 'application/json'
    },
    body: {
      extractedText: doc.json.extracted_text,
      userId: doc.json.user_id,
      projectId: doc.json.project_id,
      documentId: doc.json.document_id
    }
  });

  results.push(result);

  // Attendre 6 secondes entre chaque requête (rate limit 10/min)
  await new Promise(resolve => setTimeout(resolve, 6000));
}

return results.map(r => ({ json: r }));
```

### Retry Logic

```json
{
  "node": "HTTP Request with Retry",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "...": "...",
    "options": {
      "timeout": 180000,
      "retry": {
        "enabled": true,
        "maxRetries": 3,
        "waitBetweenRetries": 5000
      }
    }
  }
}
```

### Logging avancé

```javascript
// Node: Function - Log Request
const startTime = Date.now();
const documentId = $json.documentId;

console.log(`[${documentId}] Starting processing at ${new Date().toISOString()}`);

// Faire l'appel API
const response = await $http.request({...});

const endTime = Date.now();
const duration = (endTime - startTime) / 1000;

console.log(`[${documentId}] Completed in ${duration}s - Quality: ${response.qualityScore.overallScore}`);

return [{ json: response }];
```

---

## 6️⃣ Schéma Supabase recommandé

### Table : documents

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  project_id UUID REFERENCES projects(id),
  file_name TEXT NOT NULL,
  file_url TEXT NOT NULL,
  extracted_text TEXT,
  status TEXT DEFAULT 'pending', -- pending, processing, processed, error
  processing_time FLOAT,
  quality_score FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_project_id ON documents(project_id);
CREATE INDEX idx_documents_status ON documents(status);
```

### Table : document_chunks

```sql
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  section_id TEXT NOT NULL,
  document_type TEXT,
  document_title TEXT,
  h1 TEXT,
  h2 TEXT,
  h3 TEXT,
  title TEXT,
  type TEXT, -- legal, technical, administrative, financial
  content TEXT NOT NULL,
  word_count INT,
  keywords TEXT[],
  section_position INT,
  breadcrumb TEXT,
  parent_section TEXT,
  sibling_sections TEXT[],
  embedding VECTOR(1536), -- Pour RAG avec OpenAI embeddings
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_section_id ON document_chunks(section_id);
CREATE INDEX idx_chunks_type ON document_chunks(type);

-- Index pour recherche vectorielle (pgvector)
CREATE INDEX idx_chunks_embedding ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 7️⃣ Workflow avancé : RAG Integration

### Nodes additionnels pour RAG

#### Node : OpenAI Embeddings

```json
{
  "node": "Generate Embeddings",
  "type": "n8n-nodes-base.openAi",
  "credentials": "OpenAI",
  "parameters": {
    "resource": "embedding",
    "operation": "create",
    "model": "text-embedding-3-small",
    "text": "={{ $json.content }}"
  }
}
```

#### Node : Supabase - Update with Embedding

```sql
UPDATE document_chunks
SET embedding = '{{ $json.embedding }}'::vector
WHERE id = '{{ $json.id }}';
```

### Recherche sémantique

```sql
-- Query pour recherche RAG
SELECT
  dc.*,
  1 - (dc.embedding <=> query_embedding) as similarity
FROM document_chunks dc
WHERE dc.document_id = 'doc-123'
ORDER BY dc.embedding <=> query_embedding
LIMIT 5;
```

---

## 8️⃣ Monitoring et alertes

### Node : Slack Notification (si erreur)

```json
{
  "node": "Slack Alert",
  "type": "n8n-nodes-base.slack",
  "credentials": "Slack",
  "parameters": {
    "resource": "message",
    "operation": "post",
    "channel": "#api-alerts",
    "text": "⚠️ API Error: Document {{ $('Webhook').item.json.documentId }}\nError: {{ $json.error }}\nTime: {{ new Date().toISOString() }}"
  }
}
```

### Webhook de status

```javascript
// Notifier une autre application
await $http.request({
  method: 'POST',
  url: 'https://your-app.com/api/webhooks/document-processed',
  body: {
    documentId: $json.documentId,
    status: 'success',
    qualityScore: $json.qualityScore.overallScore,
    sectionsCount: $json.stats.totalSections
  }
});
```

---

## 9️⃣ Tests et debugging

### Test endpoint depuis n8n

```javascript
// Node: Function - Health Check
const response = await $http.request({
  method: 'GET',
  url: 'http://your-vps-ip:8000/api/v1/health'
});

console.log('API Status:', response.status);
console.log('API Version:', response.version);

return [{ json: response }];
```

### Validation de la réponse API

```javascript
// Node: Function - Validate Response
const response = $json;

// Vérifications
const validations = {
  hasDocumentId: !!response.documentId,
  hasSections: Array.isArray(response.sections) && response.sections.length > 0,
  hasQualityScore: !!response.qualityScore,
  qualityScoreValid: response.qualityScore.overallScore >= 0 && response.qualityScore.overallScore <= 1,
  hasStats: !!response.stats
};

const isValid = Object.values(validations).every(v => v === true);

if (!isValid) {
  throw new Error(`Invalid API response: ${JSON.stringify(validations)}`);
}

return [{ json: { valid: isValid, checks: validations, data: response } }];
```

---

## 🔟 Exemples de payloads

### Payload minimal

```json
{
  "extractedText": "CONTRAT DE RESERVATION VEFA\n\nLe réservant : SCCV LA VALLEE...",
  "userId": "user-123",
  "projectId": "project-456",
  "documentId": "doc-789"
}
```

### Payload complet

```json
{
  "extractedText": "CONTRAT DE RESERVATION VEFA\n\nENTRE LES SOUSSIGNES :\n\nLe RESERVANT :\nSCCV LA VALLEE, société civile de construction-vente au capital de 1.000 euros, immatriculée au RCS de MEAUX sous le numéro 888 888 888...",
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "projectId": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "documentId": "doc-2025-11-08-001",
  "mistralResponseTime": 1250
}
```

### Réponse API complète

```json
{
  "documentId": "20251108120000001",
  "documentType": "contrat_vefa",
  "documentTitle": "CONTRAT DE RESERVATION VEFA",
  "documentReference": "REF-2025-001",
  "metadata": {
    "parties": {
      "reservant": "SCCV LA VALLEE",
      "reservataire": "M. DUPONT Jean"
    },
    "date": "08/11/2025",
    "location": "MONTEVRAIN (77144)",
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
      "documentType": "contrat_vefa",
      "documentTitle": "CONTRAT DE RESERVATION VEFA",
      "h1": "IDENTIFICATION DES PARTIES",
      "h2": null,
      "h3": null,
      "title": "Article 1 - Le Réservant",
      "type": "legal",
      "content": "La société SCCV LA VALLEE, société civile de construction-vente...",
      "wordCount": 65,
      "keywords": ["réservant", "société", "RCS", "MEAUX"],
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

---

## 📞 Support

**Questions fréquentes** :

- ❓ **API ne répond pas** → Vérifier URL et firewall VPS
- ❓ **401 Unauthorized** → Vérifier X-API-Key header
- ❓ **429 Rate Limit** → Attendre 60s ou espacer les requêtes (max 10/min)
- ❓ **Timeout** → Augmenter timeout à 180s minimum
- ❓ **Réponse vide** → Vérifier format extractedText (non vide)

**Ressources** :
- [README.md](../README.md) - Documentation complète API
- [DEPLOYMENT_VPS.md](./DEPLOYMENT_VPS.md) - Déploiement VPS
- [API Docs](http://your-vps-ip:8000/docs) - Documentation interactive

---

**Dernière mise à jour** : 2025-11-08
**Version** : 3.0.0
