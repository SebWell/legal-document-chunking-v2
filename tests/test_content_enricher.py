"""
Tests unitaires pour ContentEnricher (format compact V2)
"""

import pytest
from app.core.services.content_enricher import ContentEnricher
from app.models.schemas.document import Section, DocumentOutline, DocumentMetadata, OutlineNode, Party


@pytest.fixture
def sample_metadata():
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
    return DocumentOutline(nodes=[
        OutlineNode(level=1, title="SECTION 1", position=1, children=[]),
        OutlineNode(level=1, title="SECTION 2", position=2, children=[
            OutlineNode(level=2, title="SUBSECTION 2.1", position=3, children=[])
        ]),
        OutlineNode(level=1, title="SECTION 3", position=4, children=[])
    ])


@pytest.fixture
def sample_section():
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
    return ContentEnricher()


def test_enrich_section_content(enricher, sample_section, sample_metadata, sample_outline):
    """Test enrichissement compact d'une section."""
    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=4
    )

    # Format compact: [Document: ... | Section X/Y]
    assert "[Document: CONTRAT PRELIMINAIRE DE RESERVATION | Section 3/4]" in enriched
    # Breadcrumb
    assert "[CONTRAT > SECTION 2 > SUBSECTION 2.1]" in enriched
    # Contenu original present
    assert "Le prix est de 100 euros." in enriched
    # Plan complet absent (V2)
    assert "Plan du document:" not in enriched
    assert "VOUS ETES ICI" not in enriched
    assert "Type de section:" not in enriched
    assert "Mots-cles:" not in enriched


def test_enrich_section_without_reference(enricher, sample_section, sample_outline):
    """Test enrichissement avec metadonnees sans reference."""
    metadata = DocumentMetadata(
        documentType="contrat",
        documentTitle="TEST",
        documentSubtitle=None,
        parties=[],
        location=None,
        date=None,
        reference=None
    )

    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=metadata,
        outline=sample_outline,
        total_sections=1
    )

    assert "[Document: TEST | Section 3/1]" in enriched
    assert "Le prix est de 100 euros." in enriched


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

    assert len(enriched_contents) == 3
    assert enriched_contents[0] != enriched_contents[1]
    assert "Content 1" in enriched_contents[0]
    assert "Content 2" in enriched_contents[1]
    assert "Content 3" in enriched_contents[2]
    assert "Section 1/3" in enriched_contents[0]
    assert "Section 2/3" in enriched_contents[1]
    assert "Section 3/3" in enriched_contents[2]


def test_enrich_empty_sections_list(enricher, sample_metadata, sample_outline):
    """Test enrichissement d'une liste vide."""
    enriched_contents = enricher.enrich_all_sections(
        sections=[],
        metadata=sample_metadata,
        outline=sample_outline
    )
    assert enriched_contents == []


def test_enriched_content_compact_format(enricher, sample_section, sample_metadata, sample_outline):
    """Test que le format est bien compact (pas de plan, pas de keywords dans le texte)."""
    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=10
    )

    lines = enriched.split('\n')
    # Ligne 1: [Document: ...]
    assert lines[0].startswith('[Document:')
    # Ligne 2: [breadcrumb]
    assert lines[1].startswith('[')
    # Ligne 3: vide
    assert lines[2] == ''
    # Reste: contenu
    assert 'Le prix est de 100 euros.' in enriched

    # L'enrichissement doit etre compact (< 300 chars d'overhead)
    overhead = len(enriched) - len(sample_section.content)
    assert overhead < 300, f"Overhead trop grand: {overhead} chars"


def test_enriched_content_no_outline(enricher, sample_section, sample_metadata, sample_outline):
    """Test que le plan du document n'est PAS inclus."""
    enriched = enricher.enrich_section_content(
        section=sample_section,
        metadata=sample_metadata,
        outline=sample_outline,
        total_sections=4
    )

    # Aucun element du plan
    assert "├─" not in enriched
    assert "└─" not in enriched
    assert "│" not in enriched
    assert "➜" not in enriched


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
