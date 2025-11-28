"""
FastAPI endpoint for OCR document processing.

This module provides the REST API endpoint for processing OCR documents
from PyMuPDF/PaddleOCR and returning structured chunks for n8n/Supabase.
"""

import logging
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.models.schemas.document import (
    OCRInput,
    ChunkingResponse,
    Chunk,
    ChunkMetadata,
    ChunkingStats,
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
    response_model=ChunkingResponse,
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

    **Output Format (for n8n iteration):**
    ```json
    {
      "success": true,
      "documentId": "doc-123",
      "chunks": [
        {
          "id": "chunk-001",
          "documentId": "doc-123",
          "userId": "user-uuid",
          "projectId": "project-uuid",
          "content": "Raw chunk content...",
          "enrichedContent": "Enriched content with context...",
          "metadata": {...}
        }
      ],
      "stats": {...},
      "metadata": {...}
    }
    ```

    **n8n Usage:**
    1. Call this endpoint with OCR text
    2. Use "Split In Batches" node on `chunks` array
    3. Insert each chunk into Supabase `vector_documents` table

    **Minimum Requirements:**
    - Valid API Key in X-API-Key header
    - User ID required
    - Project ID required
    - OCR text must be non-empty (>50 chars)
    """,
    response_description="Chunked document ready for Supabase insertion"
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def process_ocr_document(
    request: Request,
    body: Dict[str, Any] = Body(...),
    _: None = Depends(verify_api_key)
) -> ChunkingResponse:
    """
    Process OCR document and return chunks for n8n/Supabase.

    Args:
        request: Starlette Request object (required by slowapi)
        body: Dictionary containing OCR text and metadata
        _: API key validation (verified by verify_api_key dependency)

    Returns:
        ChunkingResponse with chunks ready for Supabase insertion

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

        # Convert sections to chunks for n8n/Supabase
        chunks: List[Chunk] = []
        total_words = 0

        for idx, section in enumerate(result.sections):
            chunk_id = f"chunk-{result.documentId}-{idx:03d}"

            # Build chunk metadata
            chunk_metadata = ChunkMetadata(
                chunkIndex=idx,
                h1=section.h1,
                h2=section.h2,
                h3=section.h3,
                title=section.title,
                type=section.type,
                wordCount=section.wordCount,
                keywords=section.keywords,
                breadcrumb=section.breadcrumb,
                sectionPosition=section.sectionPosition,
                documentType=section.documentType,
                documentTitle=section.documentTitle,
                documentReference=section.documentReference,
                ocrSource=ocr_source,
                ocrConfidence=ocr_confidence,
                parentSection=section.parentSection,
                siblingSections=section.siblingSections
            )

            # Build chunk with enriched content
            chunk = Chunk(
                id=chunk_id,
                documentId=result.documentId,
                userId=user_id,
                projectId=project_id,
                content=section.content,
                enrichedContent=enriched_contents[idx] if idx < len(enriched_contents) else section.content,
                metadata=chunk_metadata
            )

            chunks.append(chunk)
            total_words += section.wordCount

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build stats
        stats = ChunkingStats(
            totalChunks=len(chunks),
            totalWords=total_words,
            avgWordsPerChunk=total_words // len(chunks) if chunks else 0,
            processingTimeMs=processing_time_ms,
            ocrSource=ocr_source,
            ocrConfidence=ocr_confidence
        )

        # Log success
        logger.info(
            f"Document chunked successfully | ID: {result.documentId} | "
            f"Chunks: {len(chunks)} | Words: {total_words} | "
            f"Time: {processing_time_ms}ms"
        )

        return ChunkingResponse(
            success=True,
            documentId=result.documentId,
            chunks=chunks,
            stats=stats,
            metadata=result.metadata
        )

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
