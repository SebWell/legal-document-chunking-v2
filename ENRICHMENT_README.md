# ContentEnricher - Enrichissement contextuel des sections

Service Python pur (0€, pas de LLM) qui enrichit les sections de documents avec leur contexte hiérarchique avant la création d'embeddings dans n8n.

## 🎯 Objectif

Préparer les sections pour l'embedding en ajoutant du contexte:
- Position dans le document (breadcrumb)
- Plan hiérarchique avec marqueur de position
- Métadonnées du document
- Type de section et mots-clés

## 📦 Architecture

```
FastAPI (/process-ocr)
    ↓
ContentEnricher (Python pur, 0€)
    ↓
enrichedContents (liste de strings)
    ↓
n8n → Mistral AI embeddings → Supabase pgvector
```

## 🚀 Utilisation

### 1. Appeler l'API

```bash
curl -X POST "http://localhost:8000/api/v1/documents/process-ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "extractedText": "# CONTRAT...",
    "userId": "user-uuid",
    "projectId": "project-uuid"
  }'
```

### 2. Réponse JSON

```json
{
  "documentId": "doc-xxx",
  "userId": "user-uuid",
  "projectId": "project-uuid",
  "metadata": {...},
  "documentOutline": {...},
  "sections": [...],
  "enrichedContents": [
    "Document: CONTRAT PRELIMINAIRE (contrat)\nRéférence: 531074169\n\nPosition: CONTRAT > SECTION 1 > SUBSECTION 1.1\nSection 5 sur 36\n\nPlan:\n   1. CONTRAT\n   ➜ 2. SECTION 1 ◄── VOUS ÊTES ICI\n      ├─ SUBSECTION 1.1 ◄── VOUS ÊTES ICI\n\nType: financial\nMots-clés: prix, euros\n\nContenu:\nLe prix est de 100 euros...",
    "..."
  ],
  "stats": {...}
}
```

### 3. Dans n8n

```javascript
// Étape 1: Appeler l'API FastAPI
const response = await $http.post('http://api/process-ocr', {
  extractedText: mistralOcrOutput.extractedText,
  userId: userId,
  projectId: projectId
});

// Étape 2: Créer embeddings avec Mistral AI
const embeddings = [];
for (const enrichedContent of response.enrichedContents) {
  const embedding = await $http.post('https://api.mistral.ai/v1/embeddings', {
    model: 'mistral-embed',
    input: [enrichedContent]
  }, {
    headers: { 'Authorization': 'Bearer ' + $env.MISTRAL_API_KEY }
  });

  embeddings.push(embedding.data[0].embedding);
}

// Étape 3: Stocker dans Supabase
for (let i = 0; i < response.sections.length; i++) {
  await $http.post('https://your-supabase.supabase.co/rest/v1/document_sections', {
    document_id: response.documentId,
    section_position: response.sections[i].sectionPosition,
    content: response.sections[i].content,
    enriched_content: response.enrichedContents[i],
    embedding: embeddings[i],
    metadata: response.sections[i]
  }, {
    headers: {
      'apikey': $env.SUPABASE_KEY,
      'Content-Type': 'application/json'
    }
  });
}
```

## 📊 Format du contenu enrichi

Chaque élément de `enrichedContents` contient:

```
Document: [Titre du document] ([Type])
Référence: [Numéro de référence]

Position dans le document:
[Breadcrumb complet]
Section [X] sur [Total]

Plan du document:
[Plan hiérarchique avec marqueur ➜ ... ◄── VOUS ÊTES ICI]

Type de section: [financial|legal|technical|...]
Mots-clés: [liste, de, mots-clés]

Contenu:
[Contenu original de la section]
```

## 🧪 Tests

```bash
# Tests unitaires du ContentEnricher
pytest tests/test_content_enricher.py -v
# Résultat: 9 tests passed ✅

# Test d'intégration
python test_content_enrichment.py
# Résultat: ✅ TOUS LES TESTS SONT PASSÉS!
```

## 🎨 Service ContentEnricher

```python
from app.core.services.content_enricher import ContentEnricher

enricher = ContentEnricher()

# Enrichir toutes les sections
enriched_contents = enricher.enrich_all_sections(
    sections=processed.sections,
    metadata=processed.metadata,
    outline=processed.documentOutline
)

# enriched_contents = ["Document: ...", "Document: ...", ...]
```

### Méthodes disponibles

**`generate_outline_text_with_marker(outline, current_position)`**
- Génère le plan textuel avec marqueur de position
- Retourne: string avec arborescence

**`enrich_section_content(section, metadata, outline, total_sections)`**
- Enrichit une section avec son contexte
- Retourne: string enrichi

**`enrich_all_sections(sections, metadata, outline)`**
- Enrichit toutes les sections
- Retourne: List[str]

## 💡 Avantages

1. **0€** - Python pur, pas d'appel API
2. **Rapide** - Traitement en mémoire
3. **Contexte riche** - Améliore la qualité des embeddings
4. **Flexible** - Compatible avec n'importe quel service d'embedding
5. **GDPR-compliant** - Pas de données envoyées à OpenAI

## 🔧 Configuration Supabase

```sql
-- Table pour stocker les sections avec embeddings
CREATE TABLE document_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL,
  section_position INT NOT NULL,
  content TEXT NOT NULL,
  enriched_content TEXT NOT NULL,
  embedding VECTOR(1024) NOT NULL,  -- Mistral embeddings = 1024 dimensions
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche vectorielle
CREATE INDEX idx_embedding ON document_sections
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## 📈 Workflow complet

```
1. Mistral OCR (n8n)
   ↓ extractedText
2. FastAPI /process-ocr
   ↓ enrichedContents
3. Mistral AI embeddings (n8n)
   ↓ embeddings (1024 dimensions)
4. Supabase pgvector
   ↓
5. RAG queries
```

## 🎯 Exemple de recherche

```typescript
// Requête utilisateur
const query = "Quel est le prix du bien?";

// Créer embedding de la query
const queryEmbedding = await mistralAI.embed(query);

// Chercher dans Supabase
const { data } = await supabase.rpc('match_sections', {
  query_embedding: queryEmbedding,
  match_threshold: 0.7,
  match_count: 5
});

// Résultats incluent le contexte enrichi
data.forEach(section => {
  console.log(section.enriched_content);
  // Document: CONTRAT...
  // Position: ...
  // Plan: ...
  // Contenu: Le prix est de 100 000 euros...
});
```

## 📚 Documentation complète

- Tests: `tests/test_content_enricher.py`
- Code source: `app/core/services/content_enricher.py`
- Schémas: `app/models/schemas/document.py`
- Endpoint: `app/api/v1/endpoints/documents.py`
