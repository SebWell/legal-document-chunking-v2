"""
OCR Document Processing Service.

This module handles the complete OCR document processing pipeline:
- LaTeX cleaning
- Metadata extraction
- Hierarchical chunking
- Semantic enrichment
- Keyword extraction
"""

import re
import time
import random
import string
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from collections import Counter

from app.models.schemas.document import (
    DocumentMetadata,
    Party,
    Section,
    ProcessingStats,
    ProcessedDocument,
    OutlineNode,
    ProcessedDocument,
    OutlineNode,
    DocumentOutline
)
from app.core.exceptions import DocumentStructureError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing OCR documents and extracting structured information."""

    # LaTeX patterns to clean
    LATEX_PATTERNS = [
        (r'n\^\\circ', 'n°'),  # Handles n^\circ without curly braces (e.g., Permis n^\circ 123)
        (r'\^\{\\circ\}', '°'),  # Handles ^\{circ} pattern (more general case)
        (r'\$\\mathrm\{n\}\^\{\\circ\}\$', 'n°'),
        (r'n\^\{\\circ\}', 'n°'),
        (r'\$?(\d+)\s*\\%\$?', r'\1%'),
        (r'\$\\quad\$', ' '),
        (r'\\square', '☐'),
        (r'\\mathrm\{([^}]+)\}', r'\1'),
        (r'\\\s', ' '),
        (r'\$([^$]+)\$', r'\1'),
        (r'\{([^}]*)\}', r'\1'),
    ]

    # Document type keywords
    DOCUMENT_TYPES = {
        'contrat': ['contrat', 'convention', 'accord', 'engagement'],
        'plan': ['plan', 'schema', 'schéma', 'dessin', 'croquis'],
        'facture': ['facture', 'note de frais', 'avoir'],
        'devis': ['devis', 'estimation', 'cotation'],
        'rapport': ['rapport', 'étude', 'analyse'],
        'compte-rendu': ['compte rendu', 'compte-rendu', 'CR', 'procès-verbal', 'PV'],
    }

    # Section type keywords
    SECTION_TYPE_KEYWORDS = {
        'financial': ['prix', 'montant', 'euros', 'tva', 'paiement', '€', 'facture', 'tarif', 'coût', 'somme'],
        'legal': ['article', 'code civil', 'loi', 'décret', 'condition', 'juridique', 'clause', 'obligation', 'droit'],
        'parties': ['réservant', 'réservataire', 'société', 'siren', 'parties', 'représenté', 'vendeur', 'acquéreur'],
        'temporal': ['date', 'délai', 'trimestre', 'achèvement', 'livraison', 'échéance', 'durée', 'période'],
        'technical': ['travaux', 'construction', 'immeuble', 'bâtiment', 'permis', 'édifier', 'technique', 'ouvrage'],
        'risk': ['garantie', 'risque', 'assurance', 'prévention', 'responsabilité', 'sinistre', 'caution'],
        'description': ['projet', 'programme', 'résidence', 'description', 'désignation', 'caractéristique', 'situation'],
    }

    # French stopwords
    STOPWORDS = {
        'être', 'avoir', 'faire', 'cette', 'tous', 'dans', 'pour', 'avec', 'sans',
        'plus', 'sous', 'entre', 'après', 'avant', 'autre', 'leurs', 'notre', 'votre',
        'cette', 'celui', 'celle', 'ceux', 'celles', 'quel', 'quelle', 'quels', 'quelles',
        'sont', 'sera', 'seront', 'était', 'étaient', 'peut', 'peuvent', 'doit', 'doivent',
        'leur', 'elle', 'elles', 'nous', 'vous', 'dont', 'mais', 'donc', 'aussi'
    }

    def __init__(self):
        """Initialize the document processor."""
        self.version = "4.1"  # Version 4.1: Added French legal patterns (CHAPITRE, Article, X.X.X)
        self.ocr_engine = "pymupdf-paddleocr"

    def _normalize_markdown_headers(self, text: str) -> str:
        """
        Normalize markdown headers that are on the same line.

        Mistral OCR sometimes returns headers on the same line, like:
        "# TITLE ## SUBTITLE ### Section"

        This function separates them onto individual lines:
        "# TITLE
        ## SUBTITLE
        ### Section"

        Args:
            text: Text with potentially inline markdown headers

        Returns:
            Text with headers on separate lines

        Example:
            >>> processor = DocumentProcessor()
            >>> processor._normalize_markdown_headers("# Title ## Subtitle")
            '# Title\\n## Subtitle'
        """
        # Replace markdown headers that appear inline (after text/spaces)
        # Do this in order: ### first, then ##, then # to avoid matching substrings

        # Pattern 1: Space followed by ### (H3 header inline)
        text = re.sub(r'(\S)\s+(###\s+)', r'\1\n\2', text)

        # Pattern 2: Space followed by ## (H2 header inline, not part of ###)
        text = re.sub(r'(\S)\s+(##\s+(?!#))', r'\1\n\2', text)

        # Pattern 3: Space followed by # (H1 header inline, not part of ## or ###)
        text = re.sub(r'(\S)\s+(#\s+(?!#))', r'\1\n\2', text)

        return text

    def clean_html_markers(self, text: str) -> str:
        """
        Remove HTML tags and markdown artifacts from OCR text.

        Args:
            text: Text with HTML tags

        Returns:
            Cleaned text without HTML markers

        Example:
            >>> processor = DocumentProcessor()
            >>> processor.clean_html_markers("Titre <br> suite")
            'Titre\\nsuite'
        """
        cleaned = text

        # Remove PyMuPDF4LLM picture placeholders BEFORE HTML cleaning
        # Format: **==> picture [W x H] intentionally omitted <==**
        # Must be done first because <==** triggers the HTML regex across lines
        cleaned = re.sub(r'\*?\*?=*>?\s*picture\s*\[[^\]]*\]\s*intentionally\s+omitted\s*<?=*\*?\*?', '', cleaned)

        # Replace <br> with newline to preserve line structure for markdown headers
        # IMPORTANT: Use \n instead of space to keep headers on separate lines
        cleaned = re.sub(r'<br\s*/?>', '\n', cleaned)  # <br> or <br/> → newline

        # Remove HTML tags: only match proper tags starting with a letter (not <== or <= operators)
        cleaned = re.sub(r'<(?!br)/?[a-zA-Z][^>]*>', '', cleaned)

        # Remove markdown image references
        cleaned = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', cleaned)  # ![alt](image.jpg)

        # Remove empty markdown table cells (series of | | |)
        cleaned = re.sub(r'\|\s+\|\s+\|', '', cleaned)

        # Normalize multiple spaces (but preserve newlines)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

        # Normalize multiple newlines (keep max 2 for paragraph separation)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        return cleaned.strip()

    def clean_html_entities(self, text: str) -> str:
        """
        Decode HTML entities: &amp; → &, &nbsp; → space, &#8212; → —, etc.
        """
        import html as html_module
        return html_module.unescape(text)

    def clean_markdown_tables(self, text: str) -> str:
        """
        Convert markdown tables to natural language text.
        Keeps the data but removes the pipe/separator noise.

        | Header1 | Header2 |       →  Header1 : val1. Header2 : val2.
        | --- | --- |
        | val1 | val2 |
        """
        lines = text.split('\n')
        result = []
        table_block: list[str] = []
        in_table = False

        def flush_table():
            if not table_block:
                return
            # Extract headers from first row
            headers: list[str] = []
            data_rows: list[list[str]] = []

            for row in table_block:
                cells = [c.strip() for c in row.strip().strip('|').split('|')]
                cells = [c for c in cells if c]
                # Skip separator rows (all cells are --- or similar)
                if all(re.match(r'^-+:?$|^:?-+:?$|^:?-+$', c) for c in cells):
                    continue
                if not headers:
                    headers = cells
                else:
                    data_rows.append(cells)

            if not headers:
                return

            # If no data rows, just output headers as a list
            if not data_rows:
                result.append(', '.join(headers) + '.')
                return

            # Convert each data row to natural text
            for row in data_rows:
                parts = []
                for i, val in enumerate(row):
                    if not val or val == '-':
                        continue
                    if i < len(headers) and headers[i] and headers[i] != val:
                        parts.append(f"{headers[i]} : {val}")
                    else:
                        parts.append(val)
                if parts:
                    result.append('. '.join(parts) + '.')

        for line in lines:
            stripped = line.strip()
            # Detect table lines: starts and ends with | or has multiple |
            is_table_line = (stripped.startswith('|') and stripped.endswith('|')) or stripped.count('|') >= 2

            if is_table_line:
                if not in_table:
                    in_table = True
                    table_block = []
                table_block.append(stripped)
            else:
                if in_table:
                    flush_table()
                    table_block = []
                    in_table = False
                result.append(line)

        # Flush last table block
        if in_table:
            flush_table()

        return '\n'.join(result)

    def remove_repeated_headers(self, text: str) -> str:
        """
        Remove lines that appear more than 3 times in the text (page headers/footers).
        """
        lines = text.split('\n')
        # Count occurrences of each non-empty line
        line_counts: Counter = Counter()
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 5:  # Ignore very short lines
                line_counts[stripped] += 1

        # Find lines repeated more than 3 times
        repeated = {line for line, count in line_counts.items() if count > 3}

        if repeated:
            logger.info(f"Removing {len(repeated)} repeated header/footer lines")
            lines = [line for line in lines if line.strip() not in repeated]

        return '\n'.join(lines)

    def clean_noise(self, text: str) -> str:
        """
        Remove control characters, normalize whitespace.
        """
        # Remove control characters except newline and tab
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        # Normalize multiple spaces (preserve newlines)
        cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
        # Max 2 consecutive empty lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def clean_latex(self, text: str) -> str:
        """
        Remove LaTeX markers from OCR text.

        Args:
            text: Raw OCR text with LaTeX markers

        Returns:
            Cleaned text without LaTeX markers

        Example:
            >>> processor = DocumentProcessor()
            >>> processor.clean_latex("Permis n^{\\circ} 123 avec 5 \\% de TVA")
            'Permis n° 123 avec 5% de TVA'
        """
        cleaned = text
        for pattern, replacement in self.LATEX_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned)

        # Remove orphan braces and backslashes
        cleaned = re.sub(r'\{\}', '', cleaned)
        cleaned = re.sub(r'\\\\', '', cleaned)

        # Normalize multiple spaces (but preserve newlines!)
        # IMPORTANT: Only match spaces and tabs, NOT newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        return cleaned.strip()

    def extract_metadata(self, text: str) -> DocumentMetadata:
        """
        Extract document metadata from the first 50 lines.

        Args:
            text: Cleaned OCR text

        Returns:
            DocumentMetadata object with extracted information
        """
        lines = text.split('\n')[:50]
        header_text = '\n'.join(lines)
        full_text_lower = text.lower()

        # Extract document type
        doc_type = self._detect_document_type(full_text_lower)

        # Extract title (first H1)
        title = self._extract_title(text)

        # Extract subtitle (first H2)
        subtitle = self._extract_subtitle(text)

        # Extract parties
        parties = self._extract_parties(header_text)

        # Extract location
        location = self._extract_location(header_text)

        # Extract date
        date = self._extract_date(header_text)

        # Extract reference
        reference = self._extract_reference(header_text)

        return DocumentMetadata(
            documentType=doc_type,
            documentTitle=title,
            documentSubtitle=subtitle,
            parties=parties,
            location=location,
            date=date,
            reference=reference
        )

    def _detect_document_type(self, text_lower: str) -> str:
        """Detect document type based on keywords."""
        for doc_type, keywords in self.DOCUMENT_TYPES.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return doc_type
        return 'document'

    def _extract_title(self, text: str) -> str:
        """Extract the first H1 markdown title."""
        match = re.search(r'^#\s+([^\n]+)', text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            return title[:150]  # Limit to 150 characters

        # Fallback: first line if no markdown
        first_line = text.split('\n')[0].strip()
        return first_line[:150] if first_line else "Document sans titre"

    def _extract_subtitle(self, text: str) -> Optional[str]:
        """Extract the first H2 markdown subtitle."""
        match = re.search(r'^##\s+([^\n]+)', text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_parties(self, text: str) -> List[Party]:
        """Extract parties from the document."""
        parties = []

        # Pattern: "Société dénommée [NAME] au capital"
        pattern1 = r'[Ss]ociété\s+dénommée\s+([A-Z][A-Za-z0-9\s\-\']+?)\s+au\s+capital'
        matches = re.finditer(pattern1, text)
        for match in matches:
            name = match.group(1).strip()
            parties.append(Party(role="vendor", name=name))

        # Pattern: SIREN number
        pattern2 = r'SIREN\s+(?:sous\s+le\s+numéro\s+)?(\d{9})'
        matches = re.finditer(pattern2, text, re.IGNORECASE)
        for match in matches:
            siren = match.group(1)
            # Try to find company name near SIREN
            context_start = max(0, match.start() - 100)
            context = text[context_start:match.start()]
            name_match = re.search(r'([A-Z][A-Za-z0-9\s\-\']{5,})', context)
            if name_match:
                parties.append(Party(role="other", name=name_match.group(1).strip()))

        # Deduplicate parties
        seen = set()
        unique_parties = []
        for party in parties:
            if party.name not in seen:
                seen.add(party.name)
                unique_parties.append(party)

        return unique_parties

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from the document."""
        patterns = [
            r'se\s+situe\s+à\s+([A-Z][a-zA-Z\s\-]+)',
            r'située?\s+à\s+([A-Z][a-zA-Z\s\-]+)',
            r'[Ss]itué\s+à\s+([A-Z][a-zA-Z\s\-]+)',
            r'localisée?\s+à\s+([A-Z][a-zA-Z\s\-]+)',
            r'sis\s+à\s+([A-Z][a-zA-Z\s\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Remove trailing words that are not part of location
                location = re.sub(r'\s+(dans|sur|par|pour).*$', '', location)
                # Remove newlines and text after them
                location = location.split('\n')[0].strip()
                return location[:50]  # Limit length

        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from the document."""
        # Pattern: DD/MM/YYYY
        match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if match:
            return match.group(1)

        # Pattern: DD-MM-YYYY
        match = re.search(r'\b(\d{2}-\d{2}-\d{4})\b', text)
        if match:
            return match.group(1)

        # Pattern: YYYY-MM-DD
        match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        if match:
            return match.group(1)

        return None

    def _extract_reference(self, text: str) -> Optional[str]:
        """Extract reference number from the document."""
        # SIREN number
        match = re.search(r'SIREN\s+(?:sous\s+le\s+numéro\s+)?(\d{9})', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Permis de construire
        match = re.search(r'[Pp]ermis\s+(?:de\s+construire\s+)?n°?\s*([A-Z0-9\-]+)', text)
        if match:
            return match.group(1)

        # Generic reference
        match = re.search(r'[Rr]éférence\s*:?\s*([A-Z0-9\-]+)', text)
        if match:
            return match.group(1)

        # Generic n° pattern
        match = re.search(r'n°\s*([A-Z0-9\-]{5,})', text)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from text length using configured ratio."""
        settings = get_settings()
        return int(len(text) / settings.TOKEN_ESTIMATION_RATIO)

    def _should_split(self, content: str) -> bool:
        """Check if content exceeds max chunk size (chars or tokens)."""
        settings = get_settings()
        return (len(content) > settings.MAX_CHUNK_CHARS or
                self._estimate_tokens(content) > settings.MAX_CHUNK_TOKENS)

    def _split_large_section(
        self,
        content: str,
        metadata: DocumentMetadata,
        h1: Optional[str],
        h2: Optional[str],
        h3: Optional[str],
    ) -> List[Section]:
        """
        Split a section that exceeds MAX_CHUNK_CHARS or MAX_CHUNK_TOKENS
        into smaller chunks by splitting on paragraph boundaries.
        """
        settings = get_settings()
        max_chars = settings.MAX_CHUNK_CHARS
        parts = []
        paragraphs = content.split('\n\n')
        current = ''
        part_index = 0

        for para in paragraphs:
            candidate = current + para + '\n\n'
            if current and (len(candidate) > max_chars or self._estimate_tokens(candidate) > settings.MAX_CHUNK_TOKENS):
                parts.append((current.strip(), part_index))
                current = ''
                part_index += 1
            current += para + '\n\n'

        if current.strip():
            parts.append((current.strip(), part_index))

        sections = []
        for part_content, idx in parts:
            word_count = len(part_content.split())
            if word_count < 10:
                continue

            title_parts = []
            if h1:
                title_parts.append(h1)
            if h2:
                title_parts.append(h2)
            if h3:
                title_parts.append(h3)
            suffix = f" (suite {idx})" if idx > 0 else ""
            title = (' > '.join(title_parts) if title_parts else 'Section sans titre') + suffix

            sections.append(Section(
                documentType=metadata.documentType,
                documentTitle=metadata.documentTitle,
                documentReference=metadata.reference,
                h1=h1,
                h2=h2,
                h3=h3 + suffix if h3 else (h2 + suffix if h2 and idx > 0 else h3),
                title=title,
                type=self._classify_section_type(part_content),
                content=part_content,
                wordCount=word_count,
                tokenCount=self._estimate_tokens(part_content),
                keywords=self._extract_keywords(part_content),
                sectionPosition=1,
                breadcrumb="",
                parentSection=None,
                siblingSections=[]
            ))

        return sections

    def chunk_hierarchically(self, text: str, metadata: DocumentMetadata) -> List[Section]:
        """
        Chunk text into hierarchical sections based on:
        - Markdown headers (#, ##, ###, ####, #####, ######)
        - French legal patterns (CHAPITRE, Article, numbered sections)

        PyMuPDF4LLM often assigns unexpected header levels (e.g. H4 for TITRE,
        H6 for CHAPITRE in PLU documents). We normalize all markdown header
        levels into H1/H2/H3 buckets to ensure proper chunking.

        Mapping:
        - # and #### → H1 (top-level sections / TITRE)
        - ## and ##### → H2 (chapters / ARTICLE)
        - ### and ###### → H3 (sub-sections)

        Args:
            text: Cleaned text
            metadata: Extracted document metadata

        Returns:
            List of Section objects
        """
        sections = []
        lines = text.split('\n')
        rejected_sections = 0  # Track sections rejected due to word count

        current_h1 = None
        current_h2 = None
        current_h3 = None
        content_buffer = []
        headers_found = False

        def save_section():
            """Save current section if it has enough content."""
            nonlocal rejected_sections

            if not content_buffer:
                return

            content = '\n'.join(content_buffer).strip()
            word_count = len(content.split())

            # Only save sections with at least 10 words (reduced from 25 for legal documents)
            # Legal documents often have short but important sections like "D'UNE PART", clauses, etc.
            # Skip table of contents / sommaire (no RAG value)
            section_title = (current_h1 or '').upper()
            if section_title in ('SOMMAIRE', 'TABLE DES MATIERES', 'TABLE DES MATIÈRES',
                                 'TABLE OF CONTENTS', 'INDEX', 'CONTENTS'):
                rejected_sections += 1
                logger.debug(f"Rejected sommaire section: {section_title}")
                return

            if word_count < 10:
                rejected_sections += 1
                logger.debug(f"Rejected section (only {word_count} words): {current_h1 or current_h2 or current_h3 or 'Unknown'}")
                return

            # Build hierarchical title
            title_parts = []
            if current_h1:
                title_parts.append(current_h1)
            if current_h2:
                title_parts.append(current_h2)
            if current_h3:
                title_parts.append(current_h3)

            title = ' > '.join(title_parts) if title_parts else 'Section sans titre'

            # Classify section type
            section_type = self._classify_section_type(content)

            # Extract keywords
            keywords = self._extract_keywords(content)

            # If section is too large, split it
            if self._should_split(content):
                sub_sections = self._split_large_section(
                    content, metadata, current_h1, current_h2, current_h3
                )
                sections.extend(sub_sections)
                return

            section = Section(
                documentType=metadata.documentType,
                documentTitle=metadata.documentTitle,
                documentReference=metadata.reference,
                h1=current_h1,
                h2=current_h2,
                h3=current_h3,
                title=title,
                type=section_type,
                content=content,
                wordCount=word_count,
                tokenCount=self._estimate_tokens(content),
                keywords=keywords,
                # Temporary values - will be enriched later
                sectionPosition=1,  # Placeholder, will be updated by enrich_sections_with_outline_context()
                breadcrumb="",
                parentSection=None,
                siblingSections=[]
            )

            sections.append(section)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # === MARKDOWN HEADERS (all levels) ===
            # Detect any markdown header and extract level + title
            md_header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            # === FRENCH LEGAL PATTERNS ===
            # H1: CHAPITRE 1, CHAPITRE 2, Chapitre 1 (with optional title after dash/colon)
            # Also match "CHAPITRE I –" with Roman numerals or text after dash
            chapitre_match = re.match(r'^(?:\*{0,2})(CHAPITRE|Chapitre)\s+([IVXLCDM\d]+)\s*[-–:]?\s*(.*?)(?:\*{0,2})$', line, re.IGNORECASE)

            # H2: Article 1.1, ARTICLE 2.3, Article 3.0 (with optional title after dash)
            # Also match "ARTICLE Ua 1" or "ARTICLE N 2" (PLU zone articles)
            article_match = re.match(r'^(?:\*{0,2})(Article|ARTICLE)\s+([A-Za-z0-9\s]+?\.?\d*)\s*[-–:]?\s*(.*?)(?:\*{0,2})$', line, re.IGNORECASE)

            # H3: 2.3.1, 3.11.2.1 (numbered subsections at start of line with text after)
            subsection_match = re.match(r'^(\d+\.\d+\.\d+(?:\.\d+)?)\s*[-–:]?\s*(.+)$', line)

            # H1 alternative: 1/ TITRE, 2/ TITRE (existing pattern)
            h1_numbered = re.match(r'^\d+/\s+([A-Z\s]{3,80})$', line)

            # Determine effective header level from markdown headers
            # Normalize H4→H1, H5→H2, H6→H3 for documents where PyMuPDF4LLM
            # assigns deep header levels (common in PLU/legal documents)
            effective_level = None
            header_title = None

            if md_header_match:
                raw_level = len(md_header_match.group(1))
                header_title = md_header_match.group(2).strip()
                # Remove bold markers (**text**)
                header_title = re.sub(r'\*{1,2}', '', header_title).strip()
                header_title = header_title[:100]

                # Map: 1,4 → H1 | 2,5 → H2 | 3,6 → H3
                if raw_level in (1, 4):
                    effective_level = 1
                elif raw_level in (2, 5):
                    effective_level = 2
                else:  # 3 or 6
                    effective_level = 3

            # Process H1-level headers (markdown H1/H4 or CHAPITRE or numbered)
            if effective_level == 1 or chapitre_match or h1_numbered:
                headers_found = True
                save_section()
                content_buffer = []

                if chapitre_match:
                    num = chapitre_match.group(2)
                    title = chapitre_match.group(3).strip() if chapitre_match.group(3) else ""
                    title = re.sub(r'\*{1,2}', '', title).strip()
                    current_h1 = f"CHAPITRE {num}" + (f" - {title}" if title else "")
                    current_h1 = current_h1[:100]
                elif h1_numbered:
                    current_h1 = h1_numbered.group(1).strip()[:100]
                else:
                    current_h1 = header_title

                current_h2 = None
                current_h3 = None
                continue

            # Process H2-level headers (markdown H2/H5 or Article)
            if effective_level == 2 or article_match:
                headers_found = True
                save_section()
                content_buffer = []

                if article_match:
                    num = article_match.group(2).strip()
                    title = article_match.group(3).strip() if article_match.group(3) else ""
                    title = re.sub(r'\*{1,2}', '', title).strip()
                    current_h2 = f"Article {num}" + (f" – {title}" if title else "")
                    current_h2 = current_h2[:100]
                else:
                    current_h2 = header_title

                current_h3 = None
                continue

            # Process H3-level headers (markdown H3/H6 or numbered subsections)
            if effective_level == 3 or subsection_match:
                headers_found = True
                save_section()
                content_buffer = []

                if subsection_match:
                    num = subsection_match.group(1)
                    title = subsection_match.group(2).strip() if subsection_match.group(2) else ""
                    current_h3 = f"{num}" + (f" – {title}" if title else "")
                    current_h3 = current_h3[:100]
                else:
                    current_h3 = header_title

                continue

            # Add to content buffer
            content_buffer.append(line)

        # Save last section
        save_section()

        # Log chunking results
        logger.info(
            f"Hierarchical chunking complete: {len(sections)} sections created, "
            f"{rejected_sections} sections rejected (< 10 words)"
        )

        if not headers_found:
            logger.warning(
                f"No headers found! Text has {len(lines)} lines. "
                f"First 5 lines: {lines[:5]}"
            )
            raise DocumentStructureError(
                message="Le document ne contient pas la structure hiérarchique attendue (titres Markdown ou patterns français).",
                details={
                    "line_count": len(lines),
                    "first_lines": lines[:5]
                }
            )

        # Consolidate small adjacent sections when there are too many headers
        # PyMuPDF4LLM can produce excessive ## headers (every bold line becomes H2),
        # creating hundreds of micro-sections. Merge adjacent small sections to produce
        # meaningful chunks while preserving document structure.
        if len(sections) > 50:
            sections = self._consolidate_small_sections(sections, metadata)

        return sections

    def _consolidate_small_sections(
        self,
        sections: List[Section],
        metadata: DocumentMetadata,
        min_words: int = 50,
        max_words: int = 400
    ) -> List[Section]:
        """
        Merge adjacent small sections into larger ones.

        When PyMuPDF4LLM produces excessive H2 headers (bold lines → ##),
        many sections end up with < 50 words. This method merges them with
        the next section at the same hierarchy level to produce meaningful chunks.

        Args:
            sections: List of sections from hierarchical chunking
            metadata: Document metadata
            min_words: Sections below this threshold get merged with the next
            max_words: Maximum word count for a merged section

        Returns:
            Consolidated list of sections
        """
        if not sections:
            return sections

        consolidated = []
        i = 0

        while i < len(sections):
            current = sections[i]

            # If section is large enough, keep as-is
            if current.wordCount >= min_words:
                consolidated.append(current)
                i += 1
                continue

            # Small section: try to merge with following small sections at same H1 level
            merged_content_parts = [current.content]
            merged_word_count = current.wordCount
            merged_end_char = current.endChar if hasattr(current, 'endChar') else 0
            j = i + 1

            while j < len(sections):
                next_sec = sections[j]
                # Stop merging if we'd exceed max_words
                if merged_word_count + next_sec.wordCount > max_words:
                    break
                # Stop merging if H1 changes (different chapter)
                if next_sec.h1 != current.h1:
                    break
                # Merge
                merged_content_parts.append(next_sec.content)
                merged_word_count += next_sec.wordCount
                if hasattr(next_sec, 'endChar'):
                    merged_end_char = next_sec.endChar
                j += 1
                # Stop if merged section is now large enough
                if merged_word_count >= min_words:
                    break

            if j > i + 1:
                # Build merged section
                merged_content = '\n\n'.join(merged_content_parts)
                section_dict = current.model_dump()
                section_dict.update({
                    'content': merged_content,
                    'wordCount': merged_word_count,
                    'keywords': self._extract_keywords(merged_content),
                    'type': self._classify_section_type(merged_content),
                })
                if 'endChar' in section_dict:
                    section_dict['endChar'] = merged_end_char
                consolidated.append(Section(**section_dict))
            else:
                consolidated.append(current)

            i = j

        logger.info(
            f"Consolidated {len(sections)} sections into {len(consolidated)} "
            f"(merged {len(sections) - len(consolidated)} small sections)"
        )
        return consolidated

    def _classify_section_type(self, content: str) -> str:
        """
        Classify section type based on keywords.

        Args:
            content: Section content

        Returns:
            Section type (financial, legal, parties, temporal, technical, risk, description, general)
        """
        content_lower = content.lower()
        scores = {}

        for section_type, keywords in self.SECTION_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            scores[section_type] = score

        if not scores or max(scores.values()) == 0:
            return 'general'

        return max(scores, key=scores.get)

    def _extract_keywords(self, content: str, top_n: int = 5) -> List[str]:
        """
        Extract top N keywords from content.

        Args:
            content: Section content
            top_n: Number of keywords to extract

        Returns:
            List of top keywords
        """
        # Tokenize (lowercase, words > 4 characters)
        words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿçæœ]{5,}\b', content.lower())

        # Filter stopwords
        filtered_words = [w for w in words if w not in self.STOPWORDS]

        # Count frequency
        word_counts = Counter(filtered_words)

        # Return top N
        return [word for word, count in word_counts.most_common(top_n)]

    def build_document_outline(self, sections: List[Section]) -> DocumentOutline:
        """
        Build hierarchical document outline from flat list of sections.

        This method constructs a tree structure representing the document's hierarchy:
        - H1 sections are top-level nodes
        - H2 sections are nested under their parent H1
        - H3 sections are nested under their parent H2

        Algorithm:
        1. Iterate through sections sequentially
        2. Track current H1, H2, H3 nodes using maps
        3. Create new nodes when headings change
        4. Nest H2 under H1, H3 under H2
        5. Assign position = index + 1

        Args:
            sections: List of processed sections

        Returns:
            DocumentOutline with nested structure

        Example:
            >>> sections = [
            ...     Section(h1="INTRO", h2=None, h3=None, ...),
            ...     Section(h1="INTRO", h2="Background", h3=None, ...),
            ...     Section(h1="INTRO", h2="Background", h3="History", ...)
            ... ]
            >>> outline = processor.build_document_outline(sections)
            >>> len(outline.nodes)  # One H1 node
            1
            >>> len(outline.nodes[0].children)  # One H2 node
            1
            >>> len(outline.nodes[0].children[0].children)  # One H3 node
            1
        """
        outline_nodes = []
        h1_map = {}  # {h1_title: OutlineNode}
        h2_map = {}  # {f"{h1_title}::{h2_title}": OutlineNode}

        for position, section in enumerate(sections, start=1):
            # Create or retrieve H1 node
            if section.h1 and section.h1 not in h1_map:
                h1_node = OutlineNode(
                    level=1,
                    title=section.h1,
                    position=position,
                    children=[]
                )
                h1_map[section.h1] = h1_node
                outline_nodes.append(h1_node)

            # Create or retrieve H2 node if exists
            if section.h2 and section.h1:
                h2_key = f"{section.h1}::{section.h2}"
                if h2_key not in h2_map:
                    h2_node = OutlineNode(
                        level=2,
                        title=section.h2,
                        position=position,
                        children=[]
                    )
                    h2_map[h2_key] = h2_node
                    h1_map[section.h1].children.append(h2_node)

                # Create H3 node if exists
                if section.h3:
                    h3_node = OutlineNode(
                        level=3,
                        title=section.h3,
                        position=position,
                        children=[]
                    )
                    h2_map[h2_key].children.append(h3_node)

        logger.info(f"Built document outline: {len(outline_nodes)} H1 nodes")
        return DocumentOutline(nodes=outline_nodes)

    def enrich_sections_with_outline_context(
        self,
        sections: List[Section],
        metadata: DocumentMetadata
    ) -> List[Section]:
        """
        Enrich each section with hierarchical context information.

        This method adds contextual information to each section:
        - sectionPosition: Position in document (1-indexed)
        - breadcrumb: Full navigation path from document title to section
        - parentSection: Title of parent section (H1 if this is H2, H2 if this is H3)
        - siblingSections: Titles of sections at same hierarchical level

        Args:
            sections: List of sections to enrich
            metadata: Document metadata

        Returns:
            Enriched sections with breadcrumb, position, parent, siblings

        Example:
            >>> sections = [Section(h1="INTRO", h2="Background", h3=None, ...)]
            >>> enriched = processor.enrich_sections_with_outline_context(sections, metadata)
            >>> enriched[0].breadcrumb
            'CONTRAT > INTRO > Background'
            >>> enriched[0].parentSection
            'INTRO'
        """
        enriched_sections = []

        for position, section in enumerate(sections, start=1):
            # Build breadcrumb
            breadcrumb_parts = [metadata.documentTitle]
            if section.h1:
                breadcrumb_parts.append(section.h1)
            if section.h2:
                breadcrumb_parts.append(section.h2)
            if section.h3:
                breadcrumb_parts.append(section.h3)
            breadcrumb = " > ".join(breadcrumb_parts)

            # Find parent section
            parent_section = None
            if section.h3:
                parent_section = section.h2
            elif section.h2:
                parent_section = section.h1

            # Find sibling sections (same H1, same H2 level)
            sibling_sections = []
            for s in sections:
                if s == section:
                    continue

                # Check if sibling at same level
                same_h1 = s.h1 == section.h1
                same_h2 = s.h2 == section.h2

                # Both are H3 sections (under same H2)
                if section.h3 and s.h3 and same_h1 and same_h2:
                    sibling_sections.append(s.h3)

                # Both are H2 sections (under same H1, no H3)
                elif section.h2 and s.h2 and not section.h3 and not s.h3 and same_h1:
                    sibling_sections.append(s.h2)

                # Both are H1-only sections (no H2)
                elif section.h1 and s.h1 and not section.h2 and not s.h2:
                    sibling_sections.append(s.h1)

            # Create enriched section by unpacking existing data and adding new fields
            section_dict = section.model_dump()
            section_dict.update({
                'sectionPosition': position,
                'breadcrumb': breadcrumb,
                'parentSection': parent_section,
                'siblingSections': sibling_sections
            })

            enriched_section = Section(**section_dict)
            enriched_sections.append(enriched_section)

        logger.info(f"Enriched {len(enriched_sections)} sections with outline context")
        return enriched_sections

    def generate_document_id(self) -> str:
        """
        Generate a unique document ID.

        Returns:
            Document ID in format: doc-{timestamp}-{random}
        """
        timestamp = int(time.time() * 1000)
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"doc-{timestamp}-{random_suffix}"

    def calculate_stats(
        self,
        sections: List[Section],
        ocr_source: str = "pymupdf"
    ) -> ProcessingStats:
        """
        Calculate processing statistics.

        Args:
            sections: List of processed sections
            ocr_source: OCR engine used ("pymupdf" or "paddleocr")

        Returns:
            ProcessingStats object
        """
        total_sections = len(sections)
        total_words = sum(s.wordCount for s in sections)
        total_tokens = sum(s.tokenCount for s in sections)
        avg_words = round(total_words / total_sections) if total_sections > 0 else 0
        avg_tokens = round(total_tokens / total_sections) if total_sections > 0 else 0

        return ProcessingStats(
            totalSections=total_sections,
            totalWords=total_words,
            totalTokens=total_tokens,
            avgWordsPerSection=avg_words,
            avgTokensPerSection=avg_tokens,
            processingDate=datetime.now(timezone.utc).isoformat(),
            ocrEngine=ocr_source,
            version=self.version
        )

    def process_ocr_document(
        self,
        ocr_text: str,
        user_id: str,
        project_id: str,
        document_id: Optional[str] = None,
        ocr_source: str = "pymupdf",
        ocr_confidence: Optional[float] = None
    ) -> ProcessedDocument:
        """
        Main processing function that orchestrates the entire OCR document processing pipeline.

        Args:
            ocr_text: Raw OCR text from PyMuPDF or PaddleOCR
            user_id: User UUID from Supabase
            project_id: Project UUID from Supabase
            document_id: Optional document UUID from Supabase (auto-generated if not provided)
            ocr_source: OCR engine used ("pymupdf" or "paddleocr")
            ocr_confidence: OCR confidence score (0-100)

        Returns:
            ProcessedDocument with all metadata, sections, and statistics

        Raises:
            ValueError: If input is invalid
            Exception: For any processing errors
        """
        start_time = time.time()

        try:
            # Validate input
            if not ocr_text or not ocr_text.strip():
                raise ValueError("OCR text cannot be empty")

            if not user_id or not project_id:
                raise ValueError("User ID and Project ID are required")

            # Step 1: Clean HTML markers (br, img, etc.)
            logger.info("Cleaning HTML markers from OCR text")
            cleaned_text = self.clean_html_markers(ocr_text)

            # Step 1b: Decode HTML entities (&amp; → &, &nbsp; → space)
            cleaned_text = self.clean_html_entities(cleaned_text)

            # Step 1c: Convert markdown tables to natural language text
            cleaned_text = self.clean_markdown_tables(cleaned_text)

            # Step 1d: Remove repeated headers/footers (page noise)
            cleaned_text = self.remove_repeated_headers(cleaned_text)

            # Step 1e: Fix markdown headers on same line
            cleaned_text = self._normalize_markdown_headers(cleaned_text)

            # Step 2: Clean LaTeX markers
            cleaned_text = self.clean_latex(cleaned_text)

            # Step 2b: Clean noise (control chars, whitespace)
            cleaned_text = self.clean_noise(cleaned_text)

            logger.info(f"Text cleaned: {len(ocr_text)} → {len(cleaned_text)} chars ({len(ocr_text) - len(cleaned_text)} removed)")

            # Step 3: Extract metadata
            logger.info("Extracting document metadata")
            metadata = self.extract_metadata(cleaned_text)

            # Step 4: Chunk hierarchically
            logger.info("Chunking document hierarchically")
            sections = self.chunk_hierarchically(cleaned_text, metadata)
            logger.info(f"Created {len(sections)} sections from hierarchical chunking")

            # Step 5: Build document outline (NEW)
            logger.info("Building document outline")
            outline = self.build_document_outline(sections)

            # Step 6: Enrich sections with outline context (NEW)
            logger.info("Enriching sections with outline context")
            enriched_sections = self.enrich_sections_with_outline_context(sections, metadata)

            # Step 7: Calculate statistics
            logger.info("Calculating processing statistics")
            stats = self.calculate_stats(enriched_sections, ocr_source)

            # Step 8: Use provided document ID or generate new one
            if document_id:
                logger.info(f"Using provided document ID: {document_id}")
                final_document_id = document_id
            else:
                final_document_id = self.generate_document_id()
                logger.info(f"Generated document ID: {final_document_id}")

            # Log performance
            processing_time = (time.time() - start_time) * 1000
            logger.info(
                f"Document processed successfully: {final_document_id} | "
                f"Sections: {len(enriched_sections)} | "
                f"Words: {stats.totalWords} | "
                f"Time: {processing_time:.0f}ms"
            )

            return ProcessedDocument(
                documentId=final_document_id,
                userId=user_id,
                projectId=project_id,
                metadata=metadata,
                documentOutline=outline,
                sections=enriched_sections,
                stats=stats
            )

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            raise Exception(f"Failed to process OCR document: {str(e)}")
