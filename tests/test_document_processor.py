"""
Unit tests for DocumentProcessor service.

This module contains comprehensive tests for all OCR document processing functions.
"""

import pytest
import textwrap
from app.core.services.document_processor import DocumentProcessor
from app.models.schemas.document import DocumentMetadata, Section


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing."""
        return DocumentProcessor()

    # ========== LaTeX Cleaning Tests ==========

    def test_clean_latex_numero(self, processor):
        """Test cleaning of n° LaTeX markers."""
        input_text = "Permis n^{\\circ} 123"
        expected = "Permis n° 123"
        assert processor.clean_latex(input_text) == expected

    def test_clean_latex_percentage(self, processor):
        """Test cleaning of percentage LaTeX markers."""
        input_text = "TVA de 5 \\% applicable"
        expected = "TVA de 5% applicable"
        assert processor.clean_latex(input_text) == expected

    def test_clean_latex_quad(self, processor):
        """Test cleaning of \\quad spacing."""
        input_text = "Texte$\\quad$suite"
        expected = "Texte suite"
        assert processor.clean_latex(input_text) == expected

    def test_clean_latex_square(self, processor):
        """Test cleaning of \\square checkbox."""
        input_text = "\\square Case à cocher"
        expected = "☐ Case à cocher"
        assert processor.clean_latex(input_text) == expected

    def test_clean_latex_mathrm(self, processor):
        """Test cleaning of \\mathrm{}."""
        input_text = "\\mathrm{TOTAL}"
        expected = "TOTAL"
        assert processor.clean_latex(input_text) == expected

    def test_clean_latex_combined(self, processor):
        """Test cleaning of multiple LaTeX markers."""
        input_text = "Permis n^{\\circ} 123 avec 5 \\% de TVA$\\quad$Total"
        expected = "Permis n° 123 avec 5% de TVA Total"
        result = processor.clean_latex(input_text)
        assert "n°" in result
        assert "5%" in result
        assert "\\circ" not in result
        assert "\\%" not in result

    # ========== Document Type Detection Tests ==========

    def test_detect_document_type_contrat(self, processor):
        """Test detection of contract document type."""
        text = "CONTRAT DE VENTE entre les parties suivantes"
        result = processor._detect_document_type(text.lower())
        assert result == "contrat"

    def test_detect_document_type_plan(self, processor):
        """Test detection of plan document type."""
        text = "PLAN DE CONSTRUCTION niveau 1"
        result = processor._detect_document_type(text.lower())
        assert result == "plan"

    def test_detect_document_type_facture(self, processor):
        """Test detection of invoice document type."""
        text = "FACTURE n° 12345"
        result = processor._detect_document_type(text.lower())
        assert result == "facture"

    def test_detect_document_type_devis(self, processor):
        """Test detection of estimate document type."""
        text = "DEVIS ESTIMATIF travaux"
        result = processor._detect_document_type(text.lower())
        assert result == "devis"

    def test_detect_document_type_default(self, processor):
        """Test default document type when no match."""
        text = "Texte quelconque sans mot-clé"
        result = processor._detect_document_type(text.lower())
        assert result == "document"

    # ========== Metadata Extraction Tests ==========

    def test_extract_metadata_complete(self, processor):
        """Test extraction of complete metadata."""
        text = textwrap.dedent("""\
            # CONTRAT DE VENTE
            ## Programme Résidentiel XYZ
            Société dénommée ACME CORP au capital de 10000 euros
            SIREN sous le numéro 123456789
            Le bien se situe à PARIS
            Date: 15/03/2023
            """)
        metadata = processor.extract_metadata(text)

        assert metadata.documentType == "contrat"
        assert metadata.documentTitle == "CONTRAT DE VENTE"
        assert metadata.documentSubtitle == "Programme Résidentiel XYZ"
        assert len(metadata.parties) >= 1
        assert metadata.location == "PARIS"
        assert metadata.date == "15/03/2023"
        assert metadata.reference == "123456789"

    def test_extract_title_markdown(self, processor):
        """Test title extraction from markdown H1."""
        text = "# CONTRAT PRELIMINAIRE DE RESERVATION\nContenu..."
        title = processor._extract_title(text)
        assert title == "CONTRAT PRELIMINAIRE DE RESERVATION"

    def test_extract_title_truncation(self, processor):
        """Test that long titles are truncated to 150 characters."""
        long_title = "A" * 200
        text = f"# {long_title}\nContenu..."
        title = processor._extract_title(text)
        assert len(title) <= 150

    def test_extract_subtitle(self, processor):
        """Test subtitle extraction from markdown H2."""
        text = "# Titre\n## Sous-titre Important\nContenu..."
        subtitle = processor._extract_subtitle(text)
        assert subtitle == "Sous-titre Important"

    def test_extract_parties(self, processor):
        """Test extraction of parties."""
        text = "Société dénommée ACME CORP au capital de 10000 euros"
        parties = processor._extract_parties(text)
        assert len(parties) == 1
        assert parties[0].name == "ACME CORP"
        assert parties[0].role == "vendor"

    def test_extract_location(self, processor):
        """Test location extraction."""
        text = "Le bien se situe à MONTEVRAIN dans le département"
        location = processor._extract_location(text)
        assert location == "MONTEVRAIN"

    def test_extract_date_formats(self, processor):
        """Test extraction of various date formats."""
        # DD/MM/YYYY format
        text1 = "Date: 08/01/1993"
        assert processor._extract_date(text1) == "08/01/1993"

        # DD-MM-YYYY format
        text2 = "Date: 08-01-1993"
        assert processor._extract_date(text2) == "08-01-1993"

        # YYYY-MM-DD format
        text3 = "Date: 1993-01-08"
        assert processor._extract_date(text3) == "1993-01-08"

    def test_extract_reference_siren(self, processor):
        """Test extraction of SIREN reference."""
        text = "SIREN sous le numéro 123456789"
        reference = processor._extract_reference(text)
        assert reference == "123456789"

    # ========== Hierarchical Chunking Tests ==========

    def test_chunk_hierarchically_simple(self, processor):
        """Test simple hierarchical chunking."""
        text = textwrap.dedent("""\
            # Section 1
            Contenu de la section 1 avec suffisamment de mots pour atteindre le minimum requis de vingt-cinq mots dans cette section de test.

            ## Sous-section 1.1
            Contenu de la sous-section 1.1 avec suffisamment de mots pour atteindre le minimum requis de vingt-cinq mots dans cette section.
            """)
        metadata = DocumentMetadata(
            documentType="contrat",
            documentTitle="Test Document",
            parties=[]
        )

        sections = processor.chunk_hierarchically(text, metadata)

        assert len(sections) >= 1
        assert sections[0].h1 == "Section 1"
        if len(sections) > 1:
            assert sections[1].h2 == "Sous-section 1.1"

    def test_chunk_hierarchically_minimum_words(self, processor):
        """Test that sections with less than 25 words are ignored."""
        text = textwrap.dedent("""\
            # Section Courte
            Trop court.

            # Section Longue
            Ceci est une section avec suffisamment de mots pour être conservée car elle dépasse largement le minimum requis de vingt-cinq mots nécessaires.
            """)
        metadata = DocumentMetadata(
            documentType="document",
            documentTitle="Test",
            parties=[]
        )

        sections = processor.chunk_hierarchically(text, metadata)

        # Only the long section should be kept
        assert len(sections) == 1
        assert sections[0].h1 == "Section Longue"

    def test_chunk_hierarchically_numbered_h1(self, processor):
        """Test detection of numbered H1 (1/ TITLE format)."""
        text = textwrap.dedent("""\
            1/ SITUATION DU TERRAIN
            Ceci est une section avec suffisamment de mots pour être conservée car elle dépasse largement le minimum requis de vingt-cinq mots nécessaires pour validation.
            """)
        metadata = DocumentMetadata(
            documentType="document",
            documentTitle="Test",
            parties=[]
        )

        sections = processor.chunk_hierarchically(text, metadata)

        assert len(sections) >= 1
        assert sections[0].h1 == "SITUATION DU TERRAIN"

    def test_chunk_hierarchically_title_construction(self, processor):
        """Test that hierarchical titles are properly constructed."""
        text = textwrap.dedent("""\
            # Niveau 1
            ## Niveau 2
            ### Niveau 3
            Contenu avec suffisamment de mots pour être conservé car cette section dépasse largement le minimum requis de vingt-cinq mots nécessaires pour la validation du test.
            """)
        metadata = DocumentMetadata(
            documentType="document",
            documentTitle="Test",
            parties=[]
        )

        sections = processor.chunk_hierarchically(text, metadata)

        assert len(sections) >= 1
        assert "Niveau 1" in sections[0].title
        assert "Niveau 2" in sections[0].title
        assert "Niveau 3" in sections[0].title
        assert ">" in sections[0].title  # Check separator

    # ========== Section Type Classification Tests ==========

    def test_classify_section_type_financial(self, processor):
        """Test classification of financial sections."""
        content = "Le prix total est de 250000 euros avec une TVA de 20% et un paiement échelonné"
        section_type = processor._classify_section_type(content)
        assert section_type == "financial"

    def test_classify_section_type_legal(self, processor):
        """Test classification of legal sections."""
        content = "Conformément à l'article 1234 du code civil et aux conditions juridiques applicables"
        section_type = processor._classify_section_type(content)
        assert section_type == "legal"

    def test_classify_section_type_temporal(self, processor):
        """Test classification of temporal sections."""
        content = "Les travaux débuteront dans un délai de trois trimestres avec livraison prévue en décembre"
        section_type = processor._classify_section_type(content)
        assert section_type == "temporal"

    def test_classify_section_type_technical(self, processor):
        """Test classification of technical sections."""
        content = "Les travaux de construction concernent un bâtiment de 5 étages avec permis de construire"
        section_type = processor._classify_section_type(content)
        assert section_type == "technical"

    def test_classify_section_type_general(self, processor):
        """Test default classification when no keywords match."""
        content = "Texte quelconque sans mots-clés spécifiques reconnus par le système"
        section_type = processor._classify_section_type(content)
        assert section_type == "general"

    # ========== Keyword Extraction Tests ==========

    def test_extract_keywords_basic(self, processor):
        """Test basic keyword extraction."""
        content = """
        Le projet immobilier immobilier immobilier à MONTEVRAIN inclut
        construction construction de résidences résidences modernes modernes
        """
        keywords = processor._extract_keywords(content, top_n=3)

        assert len(keywords) <= 3
        assert all(len(word) >= 5 for word in keywords)
        # Check that most frequent words appear
        assert any(word in ['immobilier', 'construction', 'résidences', 'modernes'] for word in keywords)

    def test_extract_keywords_filters_stopwords(self, processor):
        """Test that stopwords are filtered out."""
        content = "avoir avoir avoir projet projet construction"
        keywords = processor._extract_keywords(content, top_n=5)

        # "avoir" is a stopword and should be filtered
        assert "avoir" not in keywords
        assert "projet" in keywords or "construction" in keywords

    def test_extract_keywords_minimum_length(self, processor):
        """Test that only words with 5+ characters are extracted."""
        content = "test test aaa bbb construction construction"
        keywords = processor._extract_keywords(content, top_n=5)

        # "test", "aaa", "bbb" are too short (< 5 chars)
        assert all(len(word) >= 5 for word in keywords)

    # ========== Document ID Generation Tests ==========

    def test_generate_document_id_format(self, processor):
        """Test document ID format."""
        doc_id = processor.generate_document_id()

        assert doc_id.startswith("doc-")
        parts = doc_id.split("-")
        assert len(parts) == 3
        assert parts[1].isdigit()  # timestamp
        assert len(parts[2]) == 8  # random suffix

    def test_generate_document_id_unique(self, processor):
        """Test that generated IDs are unique."""
        id1 = processor.generate_document_id()
        id2 = processor.generate_document_id()

        assert id1 != id2

    # ========== Statistics Calculation Tests ==========

    def test_calculate_stats(self, processor):
        """Test statistics calculation."""
        sections = [
            Section(
                documentType="contrat",
                documentTitle="Test",
                documentReference=None,
                h1="Section 1",
                title="Section 1",
                type="general",
                content="Content",
                wordCount=100,
                keywords=["word1", "word2"],
                sectionPosition=1,
                breadcrumb="Test > Section 1",
                parentSection=None,
                siblingSections=[]
            ),
            Section(
                documentType="contrat",
                documentTitle="Test",
                documentReference=None,
                h1="Section 2",
                title="Section 2",
                type="general",
                content="Content",
                wordCount=200,
                keywords=["word3", "word4"],
                sectionPosition=2,
                breadcrumb="Test > Section 2",
                parentSection=None,
                siblingSections=[]
            ),
        ]

        stats = processor.calculate_stats(sections)

        assert stats.totalSections == 2
        assert stats.totalWords == 300
        assert stats.avgWordsPerSection == 150
        assert stats.ocrEngine == "pymupdf"
        assert stats.totalTokens >= 0
        assert stats.avgTokensPerSection >= 0

    def test_calculate_stats_empty(self, processor):
        """Test statistics calculation with empty sections."""
        sections = []
        stats = processor.calculate_stats(sections)

        assert stats.totalSections == 0
        assert stats.totalWords == 0
        assert stats.avgWordsPerSection == 0

    # ========== Full Pipeline Tests ==========

    def test_process_ocr_document_complete(self, processor):
        """Test complete OCR document processing pipeline."""
        ocr_text = textwrap.dedent("""\
            # CONTRAT DE VENTE
            ## Programme Résidentiel

            Société dénommée ACME CORP au capital de 50000 euros
            SIREN: 123456789
            Situé à PARIS

            # DESCRIPTION DU PROJET
            Le projet comprend la construction d'un immeuble moderne avec tous les équipements nécessaires pour répondre aux besoins des futurs résidents et acquéreurs dans le cadre du programme immobilier.

            # CONDITIONS FINANCIERES
            Le prix de vente s'élève à 250000 euros TTC avec paiement échelonné selon les conditions définies au contrat et conformément aux dispositions légales applicables.
            """)
        result = processor.process_ocr_document(
            ocr_text=ocr_text,
            user_id="test-user-123",
            project_id="test-project-456"
        )

        # Check document ID
        assert result.documentId.startswith("doc-")

        # Check user/project IDs
        assert result.userId == "test-user-123"
        assert result.projectId == "test-project-456"

        # Check metadata
        assert result.metadata.documentType == "contrat"
        assert result.metadata.documentTitle is not None

        # Check sections
        assert len(result.sections) >= 1
        assert all(section.wordCount >= 10 for section in result.sections)  # Minimum 10 words for legal documents

        # Check stats
        assert result.stats.totalSections == len(result.sections)
        assert result.stats.totalWords > 0

    def test_process_ocr_document_empty_text(self, processor):
        """Test processing with empty text raises ValueError."""
        with pytest.raises(ValueError, match="OCR text cannot be empty"):
            processor.process_ocr_document(
                ocr_text="",
                user_id="test-user",
                project_id="test-project"
            )

    def test_process_ocr_document_missing_ids(self, processor):
        """Test processing without user/project ID raises ValueError."""
        with pytest.raises(ValueError, match="User ID and Project ID are required"):
            processor.process_ocr_document(
                ocr_text="Some text",
                user_id="",
                project_id=""
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
