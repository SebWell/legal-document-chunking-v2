"""
Service d'enrichissement contextuel des sections de document.
Utilisé pour préparer le contenu avant création des embeddings.
AUCUN LLM utilisé - uniquement manipulation de strings Python.
"""

from typing import List
import logging

from app.models.schemas.document import Section, DocumentOutline, DocumentMetadata, OutlineNode

logger = logging.getLogger(__name__)


class ContentEnricher:
    """
    Service pour enrichir les sections avec leur contexte hiérarchique.

    Enrichit chaque section avec:
    - Métadonnées du document
    - Position dans le document (breadcrumb)
    - Plan hiérarchique avec marqueur de position
    - Type de section et mots-clés
    - Contenu original

    Le contenu enrichi est optimisé pour créer des embeddings contextualisés
    qui permettent une meilleure recherche sémantique.
    """

    def generate_outline_text_with_marker(
        self,
        outline: DocumentOutline,
        current_position: int,
        max_depth: int = 3
    ) -> str:
        """
        Génère une représentation textuelle du plan du document
        avec un marqueur visuel sur la position actuelle.

        Args:
            outline: Plan hiérarchique du document
            current_position: Position de la section actuelle (1-indexed)
            max_depth: Profondeur maximale d'affichage (défaut: 3 pour H1/H2/H3)

        Returns:
            String représentant le plan avec marqueur "➜" et "◄── VOUS ÊTES ICI"

        Example:
            >>> outline = DocumentOutline(nodes=[...])
            >>> enricher = ContentEnricher()
            >>> plan = enricher.generate_outline_text_with_marker(outline, 5)
            >>> print(plan)
            1. CONTRAT PRELIMINAIRE
               ├─ PROGRAMME
               ├─ EXPOSE
            2. SITUATION DU TERRAIN
               ➜ ├─ PROJET DE CONSTRUCTION ◄── VOUS ÊTES ICI
                  │  ├─ ZAC des Fresnes ◄── VOUS ÊTES ICI
            3. PRIX
        """
        lines = []

        def _build_outline_lines(
            nodes: List[OutlineNode],
            indent: int = 0,
            parent_prefix: str = ""
        ):
            """Fonction récursive pour construire les lignes du plan"""
            for i, node in enumerate(nodes):
                # Déterminer si c'est le dernier enfant
                is_last = (i == len(nodes) - 1)

                # Choisir le préfixe de branche
                if indent == 0:
                    # Racine : numérotation simple
                    branch = f"{node.position}. "
                else:
                    # Enfants : utiliser des symboles d'arbre
                    branch = "└─ " if is_last else "├─ "

                # Indentation
                prefix = parent_prefix + ("  " if indent > 0 else "")

                # Marquer la position actuelle
                if node.position == current_position:
                    marker = "➜ "
                    suffix = " ◄── VOUS ÊTES ICI"
                else:
                    marker = "   "
                    suffix = ""

                # Construire la ligne
                line = f"{prefix}{marker}{branch}{node.title}{suffix}"
                lines.append(line)

                # Récursion pour les enfants (si pas trop profond)
                if node.children and indent < max_depth - 1:
                    child_prefix = parent_prefix
                    if indent > 0:
                        child_prefix += ("│  " if not is_last else "   ")

                    _build_outline_lines(
                        node.children,
                        indent + 1,
                        child_prefix
                    )

        _build_outline_lines(outline.nodes)
        return "\n".join(lines)

    def enrich_section_content(
        self,
        section: Section,
        metadata: DocumentMetadata,
        outline: DocumentOutline,
        total_sections: int
    ) -> str:
        """
        Enrichit le contenu d'une section avec son contexte complet.

        Args:
            section: Section à enrichir
            metadata: Métadonnées du document
            outline: Plan hiérarchique du document
            total_sections: Nombre total de sections dans le document

        Returns:
            Contenu enrichi prêt pour l'embedding

        Format du contenu enrichi:
            Document: [Titre] ([Type])
            Référence: [Ref]

            Position dans le document:
            [Breadcrumb complet]
            Section [X] sur [Total]

            Plan du document:
            [Plan avec marqueur de position]

            Type de section: [type]
            Mots-clés: [keywords]

            Contenu:
            [Contenu original de la section]

        Example:
            >>> enriched = enricher.enrich_section_content(section, metadata, outline, 36)
            >>> "VOUS ÊTES ICI" in enriched
            True
            >>> "Section 5 sur 36" in enriched
            True
        """

        # Générer le plan avec marqueur
        outline_text = self.generate_outline_text_with_marker(
            outline,
            section.sectionPosition
        )

        # Construire le contenu enrichi
        enriched_content = f"""Document: {metadata.documentTitle} ({metadata.documentType})
Référence: {metadata.reference or 'N/A'}

Position dans le document:
{section.breadcrumb}
Section {section.sectionPosition} sur {total_sections}

Plan du document:
{outline_text}

Type de section: {section.type}
Mots-clés: {', '.join(section.keywords) if section.keywords else 'N/A'}

Contenu:
{section.content}
"""

        return enriched_content.strip()

    def enrich_all_sections(
        self,
        sections: List[Section],
        metadata: DocumentMetadata,
        outline: DocumentOutline
    ) -> List[str]:
        """
        Enrichit toutes les sections d'un document.

        Args:
            sections: Liste des sections à enrichir
            metadata: Métadonnées du document
            outline: Plan hiérarchique du document

        Returns:
            Liste des contenus enrichis (même ordre que sections)

        Example:
            >>> sections = [section1, section2, section3]
            >>> enriched = enricher.enrich_all_sections(sections, metadata, outline)
            >>> len(enriched) == len(sections)
            True
            >>> all(isinstance(content, str) for content in enriched)
            True
        """
        total_sections = len(sections)

        logger.info(f"Enriching {total_sections} sections with contextual information")

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
