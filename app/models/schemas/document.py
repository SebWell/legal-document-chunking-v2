"""
Pydantic models for OCR document processing.

This module contains all request/response schemas for the OCR processing endpoint.
Adapted for PyMuPDF + PaddleOCR workflow (replaces Mistral OCR).
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Any, Dict, Literal
from datetime import datetime


class OCRInput(BaseModel):
    """Input model for PyMuPDF/PaddleOCR text (from n8n workflow)."""

    ocrText: str = Field(..., min_length=50, description="OCR extracted text")
    userId: str = Field(..., description="User UUID from Supabase")
    projectId: str = Field(..., description="Project UUID from Supabase")
    documentId: Optional[str] = Field(None, description="Document UUID from Supabase (optional)")
    source: Literal["pymupdf", "paddleocr"] = Field("pymupdf", description="OCR source engine")
    pageCount: Optional[int] = Field(None, description="Number of pages processed")
    confidence: Optional[float] = Field(None, ge=0, le=100, description="OCR confidence score (0-100)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "ocrText": "# CONTRAT PRELIMINAIRE DE RESERVATION\n\nLe présent contrat...",
                "userId": "550e8400-e29b-41d4-a716-446655440000",
                "projectId": "660e8400-e29b-41d4-a716-446655440000",
                "documentId": "doc-123456789",
                "source": "pymupdf",
                "pageCount": 13,
                "confidence": 98.5
            }
        }
    )


class Party(BaseModel):
    """Model for a party in a document (vendor, client, contractor, etc.)."""

    role: str = Field(..., description="Party role: vendor|client|contractor|other")
    name: str = Field(..., description="Company or person name")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "role": "vendor",
                "name": "SCCV LA VALLEE MONTEVRAIN HOTEL"
            }
        }
    )


class DocumentMetadata(BaseModel):
    """Extracted metadata from the document."""

    documentType: str = Field(..., description="Document type classification")
    documentTitle: str = Field(..., description="Main document title")
    documentSubtitle: Optional[str] = Field(None, description="Document subtitle")
    parties: List[Party] = Field(default_factory=list, description="List of parties involved")
    location: Optional[str] = Field(None, description="Document location")
    date: Optional[str] = Field(None, description="Document date")
    reference: Optional[str] = Field(None, description="Document reference number")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "documentType": "contrat",
                "documentTitle": "CONTRAT PRELIMINAIRE DE RESERVATION",
                "documentSubtitle": "Résidence Urbaine «LE NEST»",
                "parties": [
                    {
                        "role": "vendor",
                        "name": "SCCV LA VALLEE MONTEVRAIN HOTEL"
                    }
                ],
                "location": "MONTEVRAIN",
                "date": "08/01/1993",
                "reference": "531074169"
            }
        }
    )


class OutlineNode(BaseModel):
    """Represents a node in the document outline hierarchy."""

    level: int = Field(..., description="Heading level (1=H1, 2=H2, 3=H3)", ge=1, le=3)
    title: str = Field(..., description="Section title")
    position: int = Field(..., description="Position in document (1-indexed)", ge=1)
    children: List['OutlineNode'] = Field(default_factory=list, description="Nested subsections")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "level": 1,
                "title": "CONTRAT PRELIMINAIRE DE RESERVATION",
                "position": 1,
                "children": [
                    {
                        "level": 2,
                        "title": "PROGRAMME : Résidence Urbaine «LE NEST»",
                        "position": 1,
                        "children": []
                    }
                ]
            }
        }
    )


class DocumentOutline(BaseModel):
    """Complete hierarchical outline of the document."""

    nodes: List[OutlineNode] = Field(..., description="Top-level H1 sections")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "level": 1,
                        "title": "CONTRAT PRELIMINAIRE DE RESERVATION",
                        "position": 1,
                        "children": []
                    }
                ]
            }
        }
    )


class Section(BaseModel):
    """A hierarchical section of the document."""

    documentType: str = Field(..., description="Document type")
    documentTitle: str = Field(..., description="Document title")
    documentReference: Optional[str] = Field(None, description="Document reference")
    h1: Optional[str] = Field(None, description="H1 heading")
    h2: Optional[str] = Field(None, description="H2 heading")
    h3: Optional[str] = Field(None, description="H3 heading")
    title: str = Field(..., description="Full hierarchical title (H1 > H2 > H3)")
    type: str = Field(..., description="Semantic section type")
    content: str = Field(..., description="Section content")
    wordCount: int = Field(..., description="Number of words in section")
    tokenCount: int = Field(0, description="Estimated token count (content only)")
    enrichedTokenCount: int = Field(0, description="Estimated token count (enriched content)")
    keywords: List[str] = Field(..., description="Top 5 keywords from content")

    # NEW: Outline context fields
    sectionPosition: int = Field(..., description="Position in document (1-indexed)", ge=1)
    breadcrumb: str = Field(..., description="Full navigation path from document title to this section")
    parentSection: Optional[str] = Field(None, description="Title of parent section (H1 if this is H2, H2 if this is H3)")
    siblingSections: List[str] = Field(default_factory=list, description="Titles of sections at same hierarchical level")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "documentType": "contrat",
                "documentTitle": "CONTRAT PRELIMINAIRE DE RESERVATION",
                "documentReference": "531074169",
                "h1": "SITUATION DU TERRAIN",
                "h2": "PROJET DE CONSTRUCTION",
                "h3": "ZAC des Fresnes",
                "title": "SITUATION DU TERRAIN > PROJET DE CONSTRUCTION > ZAC des Fresnes",
                "type": "technical",
                "content": "Le conseil municipal de la Ville de MONTEVRAIN...",
                "wordCount": 154,
                "keywords": ["montevrain", "aménagement", "conseil", "municipal", "ville"],
                "sectionPosition": 5,
                "breadcrumb": "CONTRAT PRELIMINAIRE DE RESERVATION > SITUATION DU TERRAIN > PROJET DE CONSTRUCTION > ZAC des Fresnes",
                "parentSection": "PROJET DE CONSTRUCTION",
                "siblingSections": ["Projet de construction"]
            }
        }
    )


class ProcessingStats(BaseModel):
    """Statistics about the document processing."""

    totalSections: int = Field(..., description="Total number of sections created")
    totalWords: int = Field(..., description="Total word count across all sections")
    totalTokens: int = Field(0, description="Total estimated token count across all sections")
    avgWordsPerSection: int = Field(..., description="Average words per section")
    avgTokensPerSection: int = Field(0, description="Average estimated tokens per section")
    processingDate: str = Field(..., description="ISO 8601 UTC timestamp")
    ocrEngine: str = Field(..., description="OCR engine used")
    version: str = Field(..., description="Processing version")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "totalSections": 24,
                "totalWords": 4832,
                "avgWordsPerSection": 201,
                "processingDate": "2025-11-06T09:33:58.828Z",
                "ocrEngine": "mistral-ocr",
                "version": "3.0"
            }
        }
    )


class ProcessedDocument(BaseModel):
    """Complete processed document with all sections and metadata."""

    documentId: str = Field(..., description="Unique document identifier")
    userId: str = Field(..., description="User UUID")
    projectId: str = Field(..., description="Project UUID")
    metadata: DocumentMetadata = Field(..., description="Extracted document metadata")
    documentOutline: DocumentOutline = Field(..., description="Hierarchical structure of the document")
    sections: List[Section] = Field(..., description="List of hierarchical sections")
    stats: ProcessingStats = Field(..., description="Processing statistics")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "documentId": "doc-1762421638828-y17nem3",
                "userId": "550e8400-e29b-41d4-a716-446655440000",
                "projectId": "660e8400-e29b-41d4-a716-446655440000",
                "metadata": {
                    "documentType": "contrat",
                    "documentTitle": "CONTRAT PRELIMINAIRE DE RESERVATION",
                    "documentSubtitle": "Résidence Urbaine «LE NEST»",
                    "parties": [
                        {
                            "role": "vendor",
                            "name": "SCCV LA VALLEE MONTEVRAIN HOTEL"
                        }
                    ],
                    "location": "MONTEVRAIN",
                    "date": "08/01/1993",
                    "reference": "531074169"
                },
                "documentOutline": {
                    "nodes": [
                        {
                            "level": 1,
                            "title": "CONTRAT PRELIMINAIRE DE RESERVATION",
                            "position": 1,
                            "children": []
                        }
                    ]
                },
                "sections": [],
                "stats": {
                    "totalSections": 24,
                    "totalWords": 4832,
                    "avgWordsPerSection": 201,
                    "processingDate": "2025-11-06T09:33:58.828Z",
                    "ocrEngine": "mistral-ocr",
                    "version": "3.0"
                }
            }
        }
    )


class QualityIssue(BaseModel):
    """Represents a quality issue detected during document processing."""

    severity: str = Field(..., description="Issue severity: error|warning|info")
    category: str = Field(..., description="Issue category: ocr|structure|metadata|content|coherence")
    message: str = Field(..., description="Human-readable issue description")
    impact: Optional[str] = Field(None, description="Score impact (e.g., '-3 points')")
    sections_affected: Optional[List[int]] = Field(None, description="List of section positions affected")
    details: Optional[List[str]] = Field(None, description="Additional details or examples")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "severity": "warning",
                "category": "content",
                "message": "3 sections trop courtes (<50 mots)",
                "impact": "-0.9 points",
                "sections_affected": [12, 14, 26],
                "details": None
            }
        }
    )


class QualityScore(BaseModel):
    """Complete quality assessment of a processed document."""

    overall_score: float = Field(..., description="Overall quality score (0-100)", ge=0, le=100)
    grade: str = Field(..., description="Quality grade: Excellent|Bon|Moyen|Mauvais|Erreur")
    needs_review: bool = Field(..., description="Whether manual review is recommended")
    scores: Dict[str, float] = Field(..., description="Detailed scores by category")
    issues: List[QualityIssue] = Field(..., description="List of detected issues")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    metrics: Dict[str, Any] = Field(..., description="Detailed metrics for analysis")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "overall_score": 85.0,
                "grade": "Bon",
                "needs_review": False,
                "scores": {
                    "ocr_quality": 28.0,
                    "structure_quality": 22.0,
                    "metadata_completeness": 18.0,
                    "content_quality": 12.0,
                    "coherence": 9.0
                },
                "issues": [
                    {
                        "severity": "warning",
                        "category": "content",
                        "message": "3 sections trop courtes (<50 mots)",
                        "impact": "-0.9 points",
                        "sections_affected": [12, 14, 26]
                    }
                ],
                "recommendations": [
                    "✅ Document bien traité - aucune action requise"
                ],
                "metrics": {
                    "total_sections": 24,
                    "total_words": 4832,
                    "avg_words_per_section": 201.3,
                    "hierarchy_depth": 3
                }
            }
        }
    )


# Rebuild OutlineNode to handle forward reference for recursive children field
OutlineNode.model_rebuild()


# ============================================================================
# NEW: Output models for n8n/Supabase integration
# ============================================================================

class ChunkMetadata(BaseModel):
    """Metadata for a single chunk, stored as JSON in Supabase."""

    chunkIndex: int = Field(..., description="Position of chunk in document (0-indexed)")
    h1: Optional[str] = Field(None, description="H1 heading")
    h2: Optional[str] = Field(None, description="H2 heading")
    h3: Optional[str] = Field(None, description="H3 heading")
    title: str = Field(..., description="Full hierarchical title (H1 > H2 > H3)")
    type: str = Field(..., description="Semantic section type")
    wordCount: int = Field(..., description="Number of words in chunk")
    keywords: List[str] = Field(default_factory=list, description="Top keywords from content")
    breadcrumb: str = Field(..., description="Full navigation path")
    sectionPosition: int = Field(..., description="Position in document (1-indexed)")
    documentType: str = Field(..., description="Document type classification")
    documentTitle: str = Field(..., description="Main document title")
    documentReference: Optional[str] = Field(None, description="Document reference number")
    ocrSource: str = Field(..., description="OCR engine used (pymupdf/paddleocr)")
    ocrConfidence: Optional[float] = Field(None, description="OCR confidence score")
    parentSection: Optional[str] = Field(None, description="Title of parent section")
    siblingSections: List[str] = Field(default_factory=list, description="Titles of sibling sections")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "chunkIndex": 0,
                "h1": "SITUATION DU TERRAIN",
                "h2": "PROJET DE CONSTRUCTION",
                "h3": None,
                "title": "SITUATION DU TERRAIN > PROJET DE CONSTRUCTION",
                "type": "technical",
                "wordCount": 154,
                "keywords": ["montevrain", "aménagement", "conseil"],
                "breadcrumb": "CONTRAT > SITUATION DU TERRAIN > PROJET DE CONSTRUCTION",
                "sectionPosition": 5,
                "documentType": "contrat",
                "documentTitle": "CONTRAT DE VENTE",
                "documentReference": "531074169",
                "ocrSource": "pymupdf",
                "ocrConfidence": 98.5,
                "parentSection": "SITUATION DU TERRAIN",
                "siblingSections": ["Descriptif technique"]
            }
        }
    )


class Chunk(BaseModel):
    """A single chunk ready for insertion into Supabase vector_documents table."""

    id: str = Field(..., description="Unique chunk identifier")
    documentId: str = Field(..., description="Parent document ID")
    userId: str = Field(..., description="User UUID")
    projectId: str = Field(..., description="Project UUID")
    content: str = Field(..., description="Raw chunk content")
    enrichedContent: str = Field(..., description="Enriched content with context for embedding")
    metadata: ChunkMetadata = Field(..., description="Chunk metadata as JSON")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "chunk-doc123-001",
                "documentId": "doc-123456789",
                "userId": "550e8400-e29b-41d4-a716-446655440000",
                "projectId": "660e8400-e29b-41d4-a716-446655440000",
                "content": "Le conseil municipal de la Ville de MONTEVRAIN...",
                "enrichedContent": "[Document: CONTRAT DE VENTE | Type: contrat | Section: SITUATION DU TERRAIN > PROJET DE CONSTRUCTION]\n\nLe conseil municipal de la Ville de MONTEVRAIN...",
                "metadata": {}
            }
        }
    )


class ChunkingStats(BaseModel):
    """Statistics about the chunking process."""

    totalChunks: int = Field(..., description="Total number of chunks created")
    totalWords: int = Field(..., description="Total word count across all chunks")
    avgWordsPerChunk: int = Field(..., description="Average words per chunk")
    processingTimeMs: int = Field(..., description="Processing time in milliseconds")
    ocrSource: str = Field(..., description="OCR engine used")
    ocrConfidence: Optional[float] = Field(None, description="OCR confidence score if available")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "totalChunks": 15,
                "totalWords": 2340,
                "avgWordsPerChunk": 156,
                "processingTimeMs": 234,
                "ocrSource": "pymupdf",
                "ocrConfidence": 98.5
            }
        }
    )


class ChunkingResponse(BaseModel):
    """Response model for chunking endpoint - ready for n8n iteration."""

    success: bool = Field(..., description="Whether processing succeeded")
    documentId: str = Field(..., description="Document identifier")
    chunks: List[Chunk] = Field(..., description="List of chunks ready for Supabase insertion")
    stats: ChunkingStats = Field(..., description="Processing statistics")
    metadata: DocumentMetadata = Field(..., description="Extracted document metadata")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "success": True,
                "documentId": "doc-123456789",
                "chunks": [],
                "stats": {
                    "totalChunks": 15,
                    "totalWords": 2340,
                    "avgWordsPerChunk": 156,
                    "processingTimeMs": 234,
                    "ocrSource": "pymupdf",
                    "ocrConfidence": 98.5
                },
                "metadata": {
                    "documentType": "contrat",
                    "documentTitle": "CONTRAT DE VENTE",
                    "documentSubtitle": None,
                    "parties": [],
                    "location": "MONTEVRAIN",
                    "date": "08/01/2024",
                    "reference": "531074169"
                }
            }
        }
    )
