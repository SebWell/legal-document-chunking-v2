"""
Tests unitaires pour ContentEnricher
"""

import pytest
from app.core.services.content_enricher import ContentEnricher
from app.models.schemas.document import Section, DocumentOutline, DocumentMetadata, OutlineNode, Party


@pytest.fixture
def sample_metadata():
    """Fixture providing sample document metadata."""
    return DocumentMetadata(
        documentType="contrat",
        documentTitle="CONTRAT PRELIMINAIRE DE RESERVATION",
        documentSubtitle="Test",
        parties=[Party(role="vendor", name="SCCV TEST")],
        location="MONTEVRAIN",
        date=None,
        reference="531074169"
    )


@pytest.fixture
def sample_outline():
    """Fixture providing sample document outline."""
    return DocumentOutline(nodes=[
        OutlineNode(level=1, title="SECTION 1", position=1, children=[]),
        OutlineNode(level=1, title="SECTION 2", position=2, children=[
            OutlineNode(level=2, title="SUBSECTION 2.1", position=3, children=[])
        ]),
        OutlineNode(level=1, title="SECTION 3", position=4, children=[])
    ])


@pytest.fixture
def sample_section():
    """Fixture providing sample section."""
    return Section(
        documentType="contrat",
        documentTitle="CONTRAT PRELIMINAIRE",
        documentReference="531074169",
        h1="SECTION 2",
        h2="SUBSECTION 2.1",
        h3=None,
        title="SECTION 2 > SUBSECTION 2.1",
        type="financial",
        content="Le prix est de 100 euros.",
        wordCount=6,
        keywords=["prix", "euros"],
        sectionPosition=3,
        breadcrumb="CONTRAT > SECTION 2 > SUBSECTION 2.1",
        parentSection="SECTION 2",
        siblingSections=[]
    )


@pytest.fixture
def enricher():
    """Fixture providing ContentEnricher instance."""
    return ContentEnricher()


def test_generate_outline_with_marker(enricher, sample_outline):
    """Test génération du plan avec marqueur."""
    outline_text = enricher.generate_outline_text_with_marker(
        outline=sample_outline,
        current_position=3
    )

    # Vérifier que le marqueur est présent
    assert "➜" in outline_text
    assert "◄── VOUS ÊTES ICI" in outline_text
    assert "SUBSECTION 2.1" in outline_text

    # Vérifier la structure (positions basées sur le document, pas sur l'index)
    assert "1. SECTION 1" in outline_text
    assert "2. SECTION 2" in outline_text
    assert "4. SECTION 3" in outline_text  # Position 4 dans le document


def test_generate_outline_marker_on_h1(enricher, sample_outline):
    """Test génération du plan avec marqueur sur H1."""
    outline_text = enricher.generate_outline_text_with_marker(
        outline=sample_outline,
        current_position=1
    )

    # Le marqueur doit être sur SECTION 1
    lines = outline_text.split('\n')
    first_line = lines[0]
    assert "➜" in first_line
    assert "SECTION 1" in first_line
    assert "◄── VOUS ÊTES ICI" in first_line


def test_enrich_section_content(enricher, sample_section, sample_metadata, sample_outline):
    """Test enrichissement d'une section."""
    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=4
    )

    # Vérifier présence des éléments clés
    assert "CONTRAT PRELIMINAIRE DE RESERVATION" in enriched
    assert "531074169" in enriched
    assert "CONTRAT > SECTION 2 > SUBSECTION 2.1" in enriched
    assert "Section 3 sur 4" in enriched
    assert "Type de section: financial" in enriched
    assert "Mots-clés: prix, euros" in enriched
    assert "Le prix est de 100 euros." in enriched

    # Vérifier présence du plan avec marqueur
    assert "Plan du document:" in enriched
    assert "➜" in enriched
    assert "◄── VOUS ÊTES ICI" in enriched


def test_enrich_section_without_keywords(enricher, sample_metadata, sample_outline):
    """Test enrichissement d'une section sans mots-clés."""
    section = Section(
        documentType="contrat",
        documentTitle="TEST",
        documentReference="123",
        h1="H1",
        h2=None,
        h3=None,
        title="H1",
        type="general",
        content="Content without keywords",
        wordCount=3,
        keywords=[],  # Empty keywords
        sectionPosition=1,
        breadcrumb="TEST > H1",
        parentSection=None,
        siblingSections=[]
    )

    enriched = enricher.enrich_section_content(
        section=section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=1
    )

    # Vérifier que N/A est utilisé pour les mots-clés vides
    assert "Mots-clés: N/A" in enriched


def test_enrich_section_without_reference(enricher, sample_section, sample_outline):
    """Test enrichissement avec métadonnées sans référence."""
    metadata = DocumentMetadata(
        documentType="contrat",
        documentTitle="TEST",
        documentSubtitle=None,
        parties=[],
        location=None,
        date=None,
        reference=None  # No reference
    )

    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=metadata,
        outline=sample_outline,
        total_sections=1
    )

    # Vérifier que N/A est utilisé pour référence manquante
    assert "Référence: N/A" in enriched


def test_enrich_all_sections(enricher, sample_metadata, sample_outline):
    """Test enrichissement de plusieurs sections."""
    sections = [
        Section(
            documentType="contrat",
            documentTitle="TEST",
            documentReference="123",
            h1="H1",
            h2=None,
            h3=None,
            title="H1",
            type="general",
            content=f"Content {i}",
            wordCount=2,
            keywords=["test"],
            sectionPosition=i,
            breadcrumb=f"TEST > H1",
            parentSection=None,
            siblingSections=[]
        )
        for i in range(1, 4)
    ]

    enriched_contents = enricher.enrich_all_sections(
        sections=sections,
        metadata=sample_metadata,
        outline=sample_outline
    )

    # Vérifier qu'on a bien 3 contenus enrichis
    assert len(enriched_contents) == 3

    # Vérifier que chaque contenu est unique
    assert enriched_contents[0] != enriched_contents[1]
    assert enriched_contents[1] != enriched_contents[2]

    # Vérifier que les contenus sont différents
    assert "Content 1" in enriched_contents[0]
    assert "Content 2" in enriched_contents[1]
    assert "Content 3" in enriched_contents[2]

    # Vérifier que chaque section a son marqueur à la bonne position
    for i, content in enumerate(enriched_contents, 1):
        assert f"Section {i} sur 3" in content
        # Chaque section doit avoir le marqueur "VOUS ÊTES ICI"
        assert "◄── VOUS ÊTES ICI" in content


def test_enrich_empty_sections_list(enricher, sample_metadata, sample_outline):
    """Test enrichissement d'une liste vide."""
    enriched_contents = enricher.enrich_all_sections(
        sections=[],
        metadata=sample_metadata,
        outline=sample_outline
    )

    assert enriched_contents == []


def test_outline_text_structure(enricher):
    """Test structure du plan textuel."""
    outline = DocumentOutline(nodes=[
        OutlineNode(
            level=1,
            title="PART 1",
            position=1,
            children=[
                OutlineNode(level=2, title="Section 1.1", position=2, children=[]),
                OutlineNode(level=2, title="Section 1.2", position=3, children=[])
            ]
        ),
        OutlineNode(level=1, title="PART 2", position=4, children=[])
    ])

    outline_text = enricher.generate_outline_text_with_marker(outline, current_position=2)

    # Vérifier la hiérarchie
    assert "1. PART 1" in outline_text
    assert "├─ Section 1.1" in outline_text or "└─ Section 1.1" in outline_text
    assert "4. PART 2" in outline_text

    # Vérifier le marqueur sur Section 1.1 (position 2)
    assert "Section 1.1" in outline_text
    lines_with_marker = [line for line in outline_text.split('\n') if "Section 1.1" in line]
    assert any("➜" in line for line in lines_with_marker)


def test_enriched_content_format(enricher, sample_section, sample_metadata, sample_outline):
    """Test format du contenu enrichi."""
    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=10
    )

    # Vérifier les sections principales
    sections = enriched.split('\n\n')

    # Doit avoir au moins: Document, Position, Plan, Type, Contenu
    assert len(sections) >= 5

    # Vérifier l'ordre des sections
    assert enriched.index("Document:") < enriched.index("Position dans le document:")
    assert enriched.index("Position dans le document:") < enriched.index("Plan du document:")
    assert enriched.index("Plan du document:") < enriched.index("Type de section:")
    assert enriched.index("Type de section:") < enriched.index("Contenu:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
