"""
FastAPI endpoint for OCR document processing.

This module provides the REST API endpoint for processing OCR documents
from PyMuPDF/PaddleOCR and returning structured chunks for n8n/Supabase.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.models.schemas.document import (
    OCRInput,
    DocumentMetadata
)
from app.core.services.document_processor import DocumentProcessor
from app.core.services.content_enricher import ContentEnricher
from app.core.auth import verify_api_key
from app.core.rate_limiter import limiter
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create router for document endpoints
router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Initialize services (singletons)
document_processor = DocumentProcessor()
content_enricher = ContentEnricher()


@router.post(
    "/process-ocr",
    status_code=status.HTTP_200_OK,
    summary="Process OCR document and return chunks (API Key Required)",
    description="""
    Process OCR text from PyMuPDF or PaddleOCR and return structured chunks
    ready for insertion into Supabase `vector_documents` table.

    **Authentication:** Requires API Key in X-API-Key header.

    **Rate Limiting:** Maximum 10 requests per minute.

    **Input Format (PyMuPDF/PaddleOCR via n8n):**
    ```json
    {
      "ocrText": "# CONTRAT PRELIMINAIRE\\n\\nLe présent contrat...",
      "userId": "550e8400-e29b-41d4-a716-446655440000",
      "projectId": "660e8400-e29b-41d4-a716-446655440000",
      "documentId": "doc-uuid-from-supabase",
      "source": "pymupdf",
      "pageCount": 13,
      "confidence": 98.5
    }
    ```

    **Output Format (array for n8n direct iteration):**
    ```json
    [
      {
        "chunk_id": "chunk-doc-123-001",
        "document_id": "doc-123",
        "user_id": "user-uuid",
        "project_id": "project-uuid",
        "content": "Raw chunk content...",
        "enriched_content": "Enriched content with context...",
        "metadata": {...}
      },
      ...
    ]
    ```

    **n8n Usage:**
    1. Call this endpoint with OCR text
    2. Each chunk is a separate item - no Split needed
    3. Insert each chunk into Supabase `vector_documents` table using $json.chunk_id, $json.content, etc.

    **Minimum Requirements:**
    - Valid API Key in X-API-Key header
    - User ID required
    - Project ID required
    - OCR text must be non-empty (>50 chars)
    """,
    response_description="Array of chunks ready for Supabase insertion"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_ocr_document(
    request: Request,
    body: Dict[str, Any] = Body(...),
    _: None = Depends(verify_api_key)
) -> JSONResponse:
    """
    Process OCR document and return chunks as array for n8n/Supabase.

    Args:
        request: Starlette Request object (required by slowapi)
        body: Dictionary containing OCR text and metadata
        _: API key validation (verified by verify_api_key dependency)

    Returns:
        JSONResponse with array of chunks ready for direct Supabase insertion

    Raises:
        HTTPException 400: Invalid input (empty text, missing IDs)
        HTTPException 500: Processing error
    """
    start_time = time.time()

    try:
        # Extract fields from request body
        ocr_text = body.get("ocrText", "")
        user_id = body.get("userId", "")
        project_id = body.get("projectId", "")
        document_id = body.get("documentId")
        ocr_source = body.get("source", "pymupdf")
        page_count = body.get("pageCount")
        ocr_confidence = body.get("confidence")

        # Log request
        logger.info(
            f"Processing OCR document | User: {user_id} | "
            f"Project: {project_id} | Source: {ocr_source} | "
            f"Text length: {len(ocr_text)} | "
            f"Document ID: {document_id or 'auto-generate'}"
        )

        # Validate input
        if not ocr_text or not ocr_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ocrText cannot be empty"
            )

        if len(ocr_text) < 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OCR text too short ({len(ocr_text)} characters, minimum 50 required)"
            )

        if not user_id or not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="userId and projectId are required"
            )

        # Process document (get sections and metadata)
        result = document_processor.process_ocr_document(
            ocr_text=ocr_text,
            user_id=user_id,
            project_id=project_id,
            document_id=document_id,
            ocr_source=ocr_source,
            ocr_confidence=ocr_confidence
        )

        # Enrich sections with contextual information
        enriched_contents = content_enricher.enrich_all_sections(
            sections=result.sections,
            metadata=result.metadata,
            outline=result.documentOutline
        )

        # Build flat array of chunks for N8N direct iteration
        # Each chunk is formatted for direct insertion into vector_documents table
        chunks_for_supabase: List[Dict[str, Any]] = []
        total_words = 0
        total_tokens = 0

        # Token estimation helper
        token_ratio = 3.5  # chars per token for French

        for idx, section in enumerate(result.sections):
            chunk_id = f"chunk-{result.documentId}-{idx:03d}"
            enriched = enriched_contents[idx] if idx < len(enriched_contents) else section.content
            enriched_token_count = int(len(enriched) / token_ratio)

            # Build chunk with snake_case keys matching Supabase columns
            chunk_for_db = {
                "chunk_id": chunk_id,
                "document_id": result.documentId,
                "user_id": user_id,
                "project_id": project_id,
                "content": section.content,
                "enriched_content": enriched,
                "metadata": {
                    "chunkIndex": idx,
                    "h1": section.h1,
                    "h2": section.h2,
                    "h3": section.h3,
                    "title": section.title,
                    "type": section.type,
                    "wordCount": section.wordCount,
                    "tokenCount": section.tokenCount,
                    "enrichedTokenCount": enriched_token_count,
                    "keywords": section.keywords,
                    "breadcrumb": section.breadcrumb,
                    "sectionPosition": section.sectionPosition,
                    "documentType": section.documentType,
                    "documentTitle": section.documentTitle,
                    "documentReference": section.documentReference,
                    "ocrSource": ocr_source,
                    "ocrConfidence": ocr_confidence,
                    "parentSection": section.parentSection,
                    "siblingSections": section.siblingSections
                }
            }

            chunks_for_supabase.append(chunk_for_db)
            total_words += section.wordCount
            total_tokens += section.tokenCount

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log success
        avg_tokens = total_tokens // max(len(chunks_for_supabase), 1)
        logger.info(
            f"Document chunked successfully | ID: {result.documentId} | "
            f"Chunks: {len(chunks_for_supabase)} | Words: {total_words} | "
            f"Tokens: {total_tokens} (avg {avg_tokens}/chunk) | "
            f"Time: {processing_time_ms}ms"
        )

        # Return array directly for N8N to iterate over each chunk as separate item
        return JSONResponse(content=chunks_for_supabase)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected errors
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


def _build_chunks_response(
    result,
    user_id: str,
    project_id: str,
    ocr_source: str,
    ocr_confidence=None,
    page_numbers: Optional[Dict[int, int]] = None,
    confidence_scores: Optional[Dict[int, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Shared helper: turn ProcessedDocument + enriched contents into the flat
    chunk array expected by the Cloudflare Worker.  No embeddings — the Worker
    generates them via Workers AI bge-m3.
    """
    enriched_contents = content_enricher.enrich_all_sections(
        sections=result.sections,
        metadata=result.metadata,
        outline=result.documentOutline,
    )
    token_ratio = 3.5
    chunks: List[Dict[str, Any]] = []
    for idx, section in enumerate(result.sections):
        chunk_id = f"chunk-{result.documentId}-{idx:03d}"
        enriched = enriched_contents[idx] if idx < len(enriched_contents) else section.content
        enriched_token_count = int(len(enriched) / token_ratio)

        meta: Dict[str, Any] = {
            "chunkIndex": idx,
            "h1": section.h1,
            "h2": section.h2,
            "h3": section.h3,
            "title": section.title,
            "type": section.type,
            "wordCount": section.wordCount,
            "tokenCount": section.tokenCount,
            "enrichedTokenCount": enriched_token_count,
            "keywords": section.keywords,
            "breadcrumb": section.breadcrumb,
            "sectionPosition": section.sectionPosition,
            "documentType": section.documentType,
            "documentTitle": section.documentTitle,
            "documentReference": section.documentReference,
            "ocrSource": ocr_source,
            "ocrConfidence": ocr_confidence,
            "parentSection": section.parentSection,
            "siblingSections": section.siblingSections,
            "source": ocr_source,
        }
        if page_numbers and idx in page_numbers:
            meta["page_number"] = page_numbers[idx]
        if confidence_scores and idx in confidence_scores:
            meta["confidence"] = confidence_scores[idx]

        chunks.append({
            "chunk_id": chunk_id,
            "document_id": result.documentId,
            "user_id": user_id,
            "project_id": project_id,
            "content": section.content,
            "enriched_content": enriched,
            "metadata": meta,
        })
    return chunks


# ---------------------------------------------------------------------------
# NEW: /process-pymupdf  — called by Cloudflare Worker (PyMuPDF source)
# ---------------------------------------------------------------------------

@router.post(
    "/process-pymupdf",
    status_code=status.HTTP_200_OK,
    summary="Process PyMuPDF markdown and return chunks (no embeddings)",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_pymupdf(
    request: Request,
    body: Dict[str, Any] = Body(...),
    _: None = Depends(verify_api_key),
) -> JSONResponse:
    """
    Accept raw markdown from PyMuPDF, chunk it, and return structured chunks.
    Embeddings are NOT included — the Cloudflare Worker generates them via
    Workers AI bge-m3.

    Input: { text, document_id, user_id, project_id, metadata: { document_name, mop_phase, module } }
    Output: ChunkResult[] (same schema as /process-ocr but without embedding field)
    """
    start_time = time.time()
    try:
        text = body.get("text", "")
        document_id = body.get("document_id")
        user_id = body.get("user_id", "")
        project_id = body.get("project_id", "")
        meta = body.get("metadata", {})

        if not text or len(text) < 50:
            raise HTTPException(status_code=400, detail=f"text too short ({len(text)} chars, min 50)")
        if not user_id or not project_id:
            raise HTTPException(status_code=400, detail="user_id and project_id required")

        result = document_processor.process_ocr_document(
            ocr_text=text,
            user_id=user_id,
            project_id=project_id,
            document_id=document_id,
            ocr_source="pymupdf",
        )

        chunks = _build_chunks_response(result, user_id, project_id, ocr_source="pymupdf")
        logger.info(f"process-pymupdf done | {len(chunks)} chunks | {int((time.time()-start_time)*1000)}ms")
        return JSONResponse(content=chunks)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"process-pymupdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# NEW: /process-mistral-ocr  — called by Cloudflare Worker (Mistral OCR 3)
# ---------------------------------------------------------------------------

@router.post(
    "/process-mistral-ocr",
    status_code=status.HTTP_200_OK,
    summary="Process Mistral OCR 3 structured response and return chunks",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_mistral_ocr(
    request: Request,
    body: Dict[str, Any] = Body(...),
    _: None = Depends(verify_api_key),
) -> JSONResponse:
    """
    Accept a full Mistral OCR 3 response (pages array with structured markdown),
    flatten + clean it, chunk it, and return structured chunks.

    Embeddings are NOT included — the Worker generates them via Workers AI bge-m3.

    Input:
      {
        ocr_response: { pages: [{ index, markdown, confidence_scores, ... }], ... },
        document_id, user_id, project_id,
        metadata: { document_name, mop_phase, module }
      }
    Output: ChunkResult[]
    """
    start_time = time.time()
    try:
        ocr_response = body.get("ocr_response", {})
        document_id = body.get("document_id")
        user_id = body.get("user_id", "")
        project_id = body.get("project_id", "")

        pages = ocr_response.get("pages", [])
        if not pages:
            raise HTTPException(status_code=400, detail="ocr_response.pages is empty")
        if not user_id or not project_id:
            raise HTTPException(status_code=400, detail="user_id and project_id required")

        # ── Flatten OCR pages to a single markdown string ──────────
        # Mistral OCR 3 returns rich markdown per page. We clean and merge.
        page_markdowns: List[str] = []
        page_confidences: List[float] = []
        for page in pages:
            md = page.get("markdown", "")
            if not md or not md.strip():
                continue
            # Clean image references (no value for RAG embedding)
            md = re.sub(r'!\[.*?\]\(.*?\)', '', md)
            # Convert HTML tables to markdown tables if present
            md = _html_tables_to_markdown(md)
            # Simple LaTeX to text
            md = re.sub(r'\$([^$]+)\$', r'\1', md)
            page_markdowns.append(md.strip())
            # Track confidence per page
            cs = page.get("confidence_scores", {})
            if cs:
                page_confidences.append(cs.get("average_page_confidence_score", 0))

        full_text = "\n\n".join(page_markdowns)
        if len(full_text) < 50:
            raise HTTPException(status_code=400, detail=f"OCR text too short after flatten ({len(full_text)} chars)")

        avg_confidence = sum(page_confidences) / len(page_confidences) if page_confidences else None

        result = document_processor.process_ocr_document(
            ocr_text=full_text,
            user_id=user_id,
            project_id=project_id,
            document_id=document_id,
            ocr_source="mistral-ocr-3",
            ocr_confidence=avg_confidence,
        )

        chunks = _build_chunks_response(
            result, user_id, project_id,
            ocr_source="mistral-ocr-3",
            ocr_confidence=avg_confidence,
        )
        logger.info(
            f"process-mistral-ocr done | {len(chunks)} chunks | "
            f"pages: {len(pages)} | confidence: {avg_confidence:.1f}% | "
            f"{int((time.time()-start_time)*1000)}ms"
        )
        return JSONResponse(content=chunks)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"process-mistral-ocr error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _html_tables_to_markdown(text: str) -> str:
    """Convert simple HTML tables in text to markdown table format."""
    import re as _re

    def _convert_table(match):
        html = match.group(0)
        rows = _re.findall(r'<tr[^>]*>(.*?)</tr>', html, _re.DOTALL)
        if not rows:
            return html
        md_rows = []
        for i, row in enumerate(rows):
            cells = _re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, _re.DOTALL)
            cells = [c.strip() for c in cells]
            md_rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                md_rows.append("|" + "|".join(["---"] * len(cells)) + "|")
        return "\n".join(md_rows)

    return _re.sub(r'<table[^>]*>.*?</table>', _convert_table, text, flags=_re.DOTALL)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for document processing service",
    description="Check if the document processing service is running and healthy"
)
async def health_check():
    """
    Health check endpoint for the document processing service.

    Returns:
        JSON with service status and version information
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "Document Chunking API",
            "version": document_processor.version,
            "ocr_engines": ["pymupdf", "paddleocr"]
        }
    )
