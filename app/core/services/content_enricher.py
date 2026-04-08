"""
Service d'enrichissement contextuel des sections de document.
Utilise pour preparer le contenu avant creation des embeddings.
AUCUN LLM utilise - uniquement manipulation de strings Python.

V2 (2026-04): Format compact — 2 lignes de contexte + contenu brut.
Le plan complet du document n'est plus repete dans chaque chunk.
Les metadata (h1/h2/h3, breadcrumb, keywords, type) sont dans le JSONB.
"""

from typing import List
import logging

from app.models.schemas.document import Section, DocumentOutline, DocumentMetadata

logger = logging.getLogger(__name__)


class ContentEnricher:
    """
    Service pour enrichir les sections avec leur contexte hierarchique.

    Format enrichi compact:
        [Document: {titre} | Section {position}/{total}]
        [{breadcrumb}]

        {contenu original}

    L'overhead est de ~150 chars au lieu de ~800 dans l'ancienne version.
    Les metadata completes (h1, h2, h3, keywords, type) restent dans le JSONB.
    """

    def enrich_section_content(
        self,
        section: Section,
        metadata: DocumentMetadata,
        outline: DocumentOutline,
        total_sections: int
    ) -> str:
        """
        Enrichit le contenu d'une section avec un contexte compact.

        Args:
            section: Section a enrichir
            metadata: Metadonnees du document
            outline: Plan hierarchique (non utilise dans le format compact)
            total_sections: Nombre total de sections

        Returns:
            Contenu enrichi pret pour l'embedding
        """
        title = metadata.documentTitle or 'Document'
        position = section.sectionPosition or 0
        breadcrumb = section.breadcrumb or section.title or ''

        enriched = f"[Document: {title} | Section {position}/{total_sections}]\n"
        enriched += f"[{breadcrumb}]\n\n"
        enriched += section.content

        return enriched.strip()

    def enrich_all_sections(
        self,
        sections: List[Section],
        metadata: DocumentMetadata,
        outline: DocumentOutline
    ) -> List[str]:
        """
        Enrichit toutes les sections d'un document.

        Args:
            sections: Liste des sections a enrichir
            metadata: Metadonnees du document
            outline: Plan hierarchique du document

        Returns:
            Liste des contenus enrichis (meme ordre que sections)
        """
        total_sections = len(sections)

        logger.info(f"Enriching {total_sections} sections (compact format)")

        enriched_contents = [
            self.enrich_section_content(
                section=section,
                metadata=metadata,
                outline=outline,
                total_sections=total_sections
            )
            for section in sections
        ]

        logger.info(f"Successfully enriched {len(enriched_contents)} sections")

        return enriched_contents
