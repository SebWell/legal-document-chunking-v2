import pytest
from app.core.services.document_processor import DocumentProcessor
from app.core.exceptions import DocumentStructureError
from app.models.schemas.document import DocumentMetadata

class TestExplicitFailure:
    def test_raise_structure_error_no_headers(self):
        """Test that DocumentStructureError is raised when no headers are present."""
        processor = DocumentProcessor()
        
        # Create text without any markdown headers
        text = "word " * 100  # 100 words, no headers
        
        metadata = DocumentMetadata(
            documentType="test",
            documentTitle="Test Doc",
            documentSubtitle=None,
            parties=[],
            location=None,
            date=None,
            reference=None
        )
        
        # Verify exception is raised
        with pytest.raises(DocumentStructureError) as excinfo:
            processor.chunk_hierarchically(text, metadata)
        
        assert excinfo.value.code == "STRUCTURE_NOT_DETECTED"
        assert excinfo.value.status_code == 422
        assert "Le document ne contient pas la structure hiérarchique attendue" in excinfo.value.message

    def test_valid_structure_no_error(self):
        """Test that no error is raised when structure is present."""
        processor = DocumentProcessor()
        
        text = "# Title\nContent"
        
        metadata = DocumentMetadata(
            documentType="test",
            documentTitle="Test Doc",
            documentSubtitle=None,
            parties=[],
            location=None,
            date=None,
            reference=None
        )
        
        sections = processor.chunk_hierarchically(text, metadata)
        assert len(sections) > 0
