"""
Integration tests for multi-file API endpoint
"""
import io
import json
import pytest
from unittest.mock import Mock, patch

from flask import Flask
from backend.api.rfx import rfx_bp  # adjust if blueprint/module differs
from backend.services.rfx_processor import RFXProcessorService

@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rfx_bp, url_prefix="/api/rfx")
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def mock_processor():
    """Mock RFX processor to avoid real processing"""
    with patch('backend.api.rfx.RFXProcessorService') as mock_svc_class:
        mock_svc = Mock()
        mock_svc_class.return_value = mock_svc
        
        # Mock successful processing result
        mock_result = Mock()
        mock_result.model_dump.return_value = {
            "id": "RFX-TEST-1",
            "status": "processed",
            "products": [{"nombre": "Test Product", "cantidad": 1, "unidad": "pcs"}],
            "email": "test@example.com"
        }
        mock_svc.process_rfx_case.return_value = mock_result
        
        yield mock_svc

def test_upload_multiple_files_success(client, mock_processor, monkeypatch):
    """Test successful upload of multiple files"""
    # Force OCR off for speed
    monkeypatch.setenv("RFX_USE_OCR", "false")
    
    data = {
        "id": "RFX-TEST-1",
        "tipo_rfx": "catering",
    }
    
    # Create multipart form data
    multipart_data = {
        "id": data["id"],
        "tipo_rfx": data["tipo_rfx"],
        "files": [
            (io.BytesIO(b"%PDF-1.5 minimal content"), "specs.pdf"),
            (io.BytesIO(b"producto,cantidad,unidad\nA,2,pcs\n"), "items.csv"),
            (io.BytesIO(b"\x89PNG\r\n\x1a\n fake png data"), "logo.png"),
        ]
    }

    resp = client.post("/api/rfx/process", data=multipart_data, content_type='multipart/form-data')
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "data" in data
    assert mock_processor.process_rfx_case.called

def test_upload_single_file_legacy(client, mock_processor):
    """Test legacy single file upload still works"""
    with patch('backend.api.rfx.RFXProcessorService') as mock_svc_class:
        mock_svc = Mock()
        mock_svc_class.return_value = mock_svc
        
        # Mock the legacy method
        mock_result = Mock()
        mock_result.model_dump.return_value = {"id": "RFX-TEST-LEGACY", "status": "processed"}
        mock_svc.process_rfx_case.return_value = mock_result
        
        data = {
            "id": "RFX-TEST-LEGACY",
            "tipo_rfx": "catering",
            "pdf_file": (io.BytesIO(b"%PDF-1.5 legacy content"), "legacy.pdf")
        }

        resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        response_data = resp.get_json()
        assert response_data["status"] == "success"

def test_upload_no_files_error(client):
    """Test error when no files are provided"""
    data = {
        "id": "RFX-TEST-EMPTY",
        "tipo_rfx": "catering",
    }

    resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
    
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "No file provided" in data["message"]

def test_upload_invalid_file_type(client):
    """Test error for invalid file types"""
    data = {
        "id": "RFX-TEST-INVALID",
        "tipo_rfx": "catering",
        "files": [(io.BytesIO(b"invalid content"), "virus.exe")]
    }

    resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
    
    assert resp.status_code == 400
    response_data = resp.get_json()
    assert response_data["status"] == "error"
    assert "File type not allowed" in response_data["message"]

def test_upload_file_too_large(client):
    """Test error for files that are too large"""
    # Create a large file (17MB > 16MB limit)
    large_content = b"x" * (17 * 1024 * 1024)
    
    data = {
        "id": "RFX-TEST-LARGE",
        "tipo_rfx": "catering",
        "files": [(io.BytesIO(large_content), "large.pdf")]
    }

    resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
    
    assert resp.status_code == 413
    response_data = resp.get_json()
    assert response_data["status"] == "error"
    assert "too large" in response_data["message"]

def test_upload_total_size_too_large(client):
    """Test error when total upload size exceeds limit"""
    # Create multiple files that together exceed 32MB
    file_content = b"x" * (12 * 1024 * 1024)  # 12MB each
    
    data = {
        "id": "RFX-TEST-TOTAL-LARGE",
        "tipo_rfx": "catering",
        "files": [
            (io.BytesIO(file_content), "file1.pdf"),
            (io.BytesIO(file_content), "file2.pdf"),
            (io.BytesIO(file_content), "file3.pdf"),  # Total: 36MB > 32MB limit
        ]
    }

    resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
    
    assert resp.status_code == 413
    response_data = resp.get_json()
    assert response_data["status"] == "error"
    assert "Total upload too large" in response_data["message"]

def test_upload_empty_file(client):
    """Test handling of empty files"""
    data = {
        "id": "RFX-TEST-EMPTY-FILE",
        "tipo_rfx": "catering",
        "files": [
            (io.BytesIO(b""), "empty.pdf"),  # Empty file
            (io.BytesIO(b"%PDF-1.5 content"), "good.pdf")
        ]
    }

    # The empty file should be filtered out, leaving only the good file
    with patch('backend.api.rfx.RFXProcessorService') as mock_svc_class:
        mock_svc = Mock()
        mock_svc_class.return_value = mock_svc
        mock_result = Mock()
        mock_result.model_dump.return_value = {"id": "RFX-TEST-EMPTY-FILE", "status": "processed"}
        mock_svc.process_rfx_case.return_value = mock_result

        resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
        
        # Should succeed with only the non-empty file
        assert resp.status_code == 200
        # Verify only one file was passed to processor
        call_args = mock_svc.process_rfx_case.call_args
        valid_files = call_args[0][1]  # Second argument (blobs)
        assert len(valid_files) == 1
        assert valid_files[0]["filename"] == "good.pdf"

def test_upload_zip_expansion_flag(client, monkeypatch):
    """Test ZIP expansion with feature flag"""
    monkeypatch.setenv("RFX_USE_ZIP", "true")
    
    with patch('backend.api.rfx.RFXProcessorService') as mock_svc_class:
        mock_svc = Mock()
        mock_svc_class.return_value = mock_svc
        mock_result = Mock()
        mock_result.model_dump.return_value = {"id": "RFX-TEST-ZIP", "status": "processed"}
        mock_svc.process_rfx_case.return_value = mock_result

        data = {
            "id": "RFX-TEST-ZIP",
            "tipo_rfx": "catering",
            "files": [(io.BytesIO(b"PK\x03\x04fake zip content"), "archive.zip")]
        }

        resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        assert mock_svc.process_rfx_case.called

def test_processing_error_handling(client):
    """Test error handling when processing fails"""
    with patch('backend.api.rfx.RFXProcessorService') as mock_svc_class:
        mock_svc = Mock()
        mock_svc_class.return_value = mock_svc
        mock_svc.process_rfx_case.side_effect = ValueError("Processing failed")

        data = {
            "id": "RFX-TEST-ERROR",
            "tipo_rfx": "catering",
            "files": [(io.BytesIO(b"%PDF-1.5 content"), "test.pdf")]
        }

        resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
        
        assert resp.status_code == 500
        response_data = resp.get_json()
        assert response_data["status"] == "error"
        assert "Processing failed" in response_data["message"]

def test_supported_file_extensions(client, mock_processor):
    """Test that all supported file extensions are accepted"""
    supported_files = [
        ("specs.pdf", b"%PDF-1.5 content"),
        ("legacy.doc", b"\xd0\xcf\x11\xe0content"),
        ("modern.docx", b"PK\x03\x04content"),
        ("readme.txt", b"text content"),
        ("data.xlsx", b"excel content"),
        ("items.csv", b"csv,content"),
        ("photo.png", b"\x89PNG content"),
        ("image.jpg", b"\xff\xd8\xff\xe0content"),
        ("scan.tiff", b"II*\x00content"),
        ("archive.zip", b"PK\x03\x04zip content"),
    ]

    for filename, content in supported_files:
        data = {
            "id": f"RFX-TEST-{filename.upper()}",
            "tipo_rfx": "catering",
            "files": [(io.BytesIO(content), filename)]
        }

        resp = client.post("/api/rfx/process", data=data, content_type='multipart/form-data')
        assert resp.status_code == 200, f"Failed for {filename}"
        
        response_data = resp.get_json()
        assert response_data["status"] == "success", f"Failed processing {filename}"
