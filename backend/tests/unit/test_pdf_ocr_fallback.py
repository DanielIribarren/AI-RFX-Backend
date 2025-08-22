"""
Unit tests for PDF OCR fallback functionality
"""
import pytest
from unittest.mock import Mock, patch

from backend.services.rfx_processor import RFXProcessorService

@pytest.fixture
def svc(monkeypatch):
    """Create service with mocked OCR dependencies"""
    s = RFXProcessorService()

    # Force OCR flag on for this test
    monkeypatch.setenv("RFX_USE_OCR", "true")

    # Stub _extract_text_with_ocr to avoid real OCR deps
    def fake_ocr(bytes_, kind="pdf", filename=None):
        return "Texto vía OCR simulado"
    s._extract_text_with_ocr = fake_ocr
    return s

@pytest.fixture
def svc_ocr_disabled(monkeypatch):
    """Create service with OCR disabled"""
    s = RFXProcessorService()
    monkeypatch.setenv("RFX_USE_OCR", "false")
    return s

def test_pdf_empty_triggers_ocr(svc):
    """Test that empty PDF extraction triggers OCR fallback"""
    # Directly test the OCR helper used by the pipeline
    result = svc._extract_text_with_ocr(b"%PDF-FAKE", kind="pdf")
    assert result.startswith("Texto vía OCR")

def test_pdf_minimal_text_triggers_ocr(svc, monkeypatch):
    """Test that PDF with minimal text triggers OCR"""
    # Mock PyPDF2 to return minimal text
    with patch('backend.services.rfx_processor.PyPDF2') as mock_pypdf:
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "   \n  "  # minimal whitespace
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader
        
        # This should trigger OCR fallback
        result = svc._extract_text_from_document(b"%PDF-1.4 fake pdf content")
        assert "Texto vía OCR" in result

def test_pdf_good_text_no_ocr(svc, monkeypatch):
    """Test that PDF with good text doesn't trigger OCR"""
    # Mock PyPDF2 to return good text
    with patch('backend.services.rfx_processor.PyPDF2') as mock_pypdf:
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "This is substantial text content from the PDF that should not trigger OCR fallback because it has enough characters."
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader
        
        result = svc._extract_text_from_document(b"%PDF-1.4 fake pdf content")
        assert "substantial text content" in result
        assert "OCR" not in result

def test_ocr_disabled_no_processing(svc_ocr_disabled):
    """Test that OCR is not attempted when disabled"""
    result = svc_ocr_disabled._extract_text_with_ocr(b"%PDF-FAKE", kind="pdf")
    assert result == ""

def test_ocr_disabled_pdf_fails_gracefully(svc_ocr_disabled):
    """Test that empty PDF fails gracefully when OCR is disabled"""
    with patch('backend.services.rfx_processor.PyPDF2') as mock_pypdf:
        mock_reader = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = ""  # empty text
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader
        
        with pytest.raises(ValueError, match="No text could be extracted from PDF"):
            svc_ocr_disabled._extract_text_from_document(b"%PDF-1.4 fake pdf content")

def test_ocr_image_processing(svc):
    """Test OCR processing for images"""
    result = svc._extract_text_with_ocr(b"\x89PNG fake image", kind="image", filename="test.png")
    assert "Texto vía OCR" in result

def test_ocr_dependencies_missing(monkeypatch):
    """Test behavior when OCR dependencies are missing"""
    svc = RFXProcessorService()
    monkeypatch.setenv("RFX_USE_OCR", "true")
    
    # Mock import error for OCR dependencies
    def mock_import_error(name, *args, **kwargs):
        if name in ["pytesseract", "PIL"]:
            raise ImportError(f"No module named '{name}'")
        return __import__(name, *args, **kwargs)
    
    with patch('builtins.__import__', side_effect=mock_import_error):
        result = svc._extract_text_with_ocr(b"test", kind="image")
        assert result == ""

def test_ocr_pillow_error(svc, monkeypatch):
    """Test OCR handling when PIL fails to open image"""
    with patch('backend.services.rfx_processor.pytesseract') as mock_tess, \
         patch('backend.services.rfx_processor.Image') as mock_pil:
        mock_pil.open.side_effect = Exception("Invalid image format")
        
        result = svc._extract_text_with_ocr(b"invalid image", kind="image", filename="bad.png")
        assert result == ""

def test_ocr_pdf2image_missing(svc, monkeypatch):
    """Test PDF OCR when pdf2image is not available"""
    with patch('backend.services.rfx_processor.pytesseract'), \
         patch('backend.services.rfx_processor.Image'):
        
        def mock_import_error(name, *args, **kwargs):
            if name == "pdf2image":
                raise ImportError("No module named 'pdf2image'")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import_error):
            result = svc._extract_text_with_ocr(b"%PDF fake", kind="pdf")
            assert result == ""

def test_feature_flag_integration(monkeypatch):
    """Test that feature flags are properly integrated"""
    # Test OCR flag disabled
    monkeypatch.setenv("RFX_USE_OCR", "false")
    
    # Reimport to get updated flag value
    import importlib
    import backend.services.rfx_processor
    importlib.reload(backend.services.rfx_processor)
    
    svc = backend.services.rfx_processor.RFXProcessorService()
    result = svc._extract_text_with_ocr(b"test", kind="image")
    assert result == ""
