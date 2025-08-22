"""
Unit tests for content type detection in multi-file RFX processing
"""
import io
import pytest

from backend.services.rfx_processor import RFXProcessorService

@pytest.fixture
def svc():
    return RFXProcessorService()

def test_detect_pdf_magic(svc):
    """Test PDF detection by magic bytes"""
    kind = svc._detect_content_type(b"%PDF-1.5 ...", "specs.unknown")
    assert kind == "pdf"

def test_detect_docx_zip_magic(svc):
    """Test DOCX detection by ZIP magic bytes and extension"""
    kind = svc._detect_content_type(b"PK\x03\x04...", "rfq.docx")
    assert kind == "docx"

def test_detect_xlsx_by_ext(svc):
    """Test XLSX detection by file extension"""
    kind = svc._detect_content_type(b"RANDOM", "items.xlsx")
    assert kind == "xlsx"

def test_detect_csv_by_ext(svc):
    """Test CSV detection by file extension"""
    kind = svc._detect_content_type(b"name,qty\nx,1\n", "items.csv")
    assert kind == "csv"

def test_detect_image_by_ext(svc):
    """Test image detection by file extension"""
    kind = svc._detect_content_type(b"\x89PNG....", "pic.png")
    assert kind == "image"

def test_detect_jpg_image(svc):
    """Test JPEG image detection"""
    kind = svc._detect_content_type(b"\xff\xd8\xff\xe0JFIF", "photo.jpg")
    assert kind == "image"

def test_detect_tiff_image(svc):
    """Test TIFF image detection"""
    kind = svc._detect_content_type(b"II*\x00", "scan.tiff")
    assert kind == "image"

def test_detect_zip_by_ext(svc):
    """Test ZIP detection by file extension"""
    kind = svc._detect_content_type(b"PK\x03\x04", "archive.zip")
    assert kind == "zip"

def test_detect_doc_by_ext(svc):
    """Test DOC detection by file extension"""
    kind = svc._detect_content_type(b"\xd0\xcf\x11\xe0", "legacy.doc")
    assert kind == "doc"

def test_detect_markdown_as_text(svc):
    """Test Markdown detection as text"""
    kind = svc._detect_content_type(b"# Title\nContent", "readme.md")
    assert kind == "text"

def test_fallback_text(svc):
    """Test fallback to text for unknown files"""
    kind = svc._detect_content_type(b"hello", "readme.txt")
    assert kind == "text"

def test_detect_by_mimetype_fallback(svc):
    """Test detection using mimetypes fallback"""
    # This tests the mimetypes.guess_type fallback
    kind = svc._detect_content_type(b"binary data", "photo.gif")
    assert kind == "image"

def test_empty_filename(svc):
    """Test handling of empty filename"""
    kind = svc._detect_content_type(b"%PDF-1.4", "")
    assert kind == "pdf"  # Should still detect by magic bytes

def test_case_insensitive_extensions(svc):
    """Test case insensitive extension detection"""
    kind = svc._detect_content_type(b"data", "FILE.PDF")
    assert kind == "pdf"
    
    kind = svc._detect_content_type(b"data", "DATA.XLSX")
    assert kind == "xlsx"
