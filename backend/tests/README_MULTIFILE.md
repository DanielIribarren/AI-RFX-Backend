# Multi-File RFX Processing Test Suite

This test suite covers the new multi-file RFX ingestion pipeline that supports PDF, DOCX, TXT, XLSX, CSV, images, and ZIP files.

## 🧪 Test Structure

### Unit Tests

- **`test_content_detection.py`**: Tests file type detection by magic bytes and extensions
- **`test_spreadsheet_parser.py`**: Tests CSV/XLSX parsing with pandas (requires pandas)
- **`test_pdf_ocr_fallback.py`**: Tests OCR fallback for scanned PDFs and images

### Integration Tests

- **`test_api_multiple_files.py`**: Tests the `/api/rfx/process` endpoint with multiple files

## 🚀 Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-mock requests
```

Optional dependencies for full feature testing:

```bash
pip install pandas openpyxl pytesseract pillow pdf2image
```

### Run All Tests

```bash
# From project root
pytest backend/tests/ -v

# Run specific test categories
pytest backend/tests/unit/ -v
pytest backend/tests/integration/ -v
```

### Run with Feature Flags

```bash
# Test with OCR disabled
RFX_USE_OCR=false pytest backend/tests/ -v

# Test with ZIP expansion disabled
RFX_USE_ZIP=false pytest backend/tests/ -v

# Test with both disabled
RFX_USE_OCR=false RFX_USE_ZIP=false pytest backend/tests/ -v
```

## 🎯 Test Coverage

### Content Detection Tests

- ✅ PDF detection by magic bytes (`%PDF`)
- ✅ DOCX detection by ZIP magic + extension
- ✅ Image format detection (PNG, JPG, TIFF)
- ✅ Spreadsheet detection (XLSX, CSV)
- ✅ Text file fallback
- ✅ Case-insensitive extensions
- ✅ MIME type fallback

### Spreadsheet Parser Tests

- ✅ CSV parsing with standard columns
- ✅ XLSX parsing with pandas/openpyxl
- ✅ Alternative column name mapping
- ✅ Missing column handling
- ✅ Empty row filtering
- ✅ Invalid data handling
- ✅ Graceful pandas unavailability

### OCR Fallback Tests

- ✅ Empty PDF triggers OCR
- ✅ Minimal text triggers OCR
- ✅ Good text bypasses OCR
- ✅ Feature flag disable
- ✅ Dependency unavailability
- ✅ Image OCR processing

### API Integration Tests

- ✅ Multi-file upload success
- ✅ Legacy single file compatibility
- ✅ File type validation
- ✅ File size limits (16MB per file, 32MB total)
- ✅ Empty file handling
- ✅ Error response formatting
- ✅ All supported extensions

## 🏗️ Feature Flags

The test suite validates both enabled and disabled states:

### `RFX_USE_OCR` (default: true)

- **Enabled**: OCR processing for scanned PDFs and images
- **Disabled**: Skip OCR, return empty strings for OCR calls

### `RFX_USE_ZIP` (default: true)

- **Enabled**: Expand ZIP files and process contents
- **Disabled**: Treat ZIP files as regular binary files

## 🔧 Mock Strategy

Tests use strategic mocking to avoid external dependencies:

1. **OCR Dependencies**: Mock `pytesseract`, `PIL`, `pdf2image`
2. **Pandas**: Skip tests when unavailable, mock import errors
3. **File Processing**: Mock service methods for isolated testing
4. **API Calls**: Mock RFXProcessorService for endpoint testing

## 📊 Test Data

Tests use minimal, realistic test data:

- **PDF**: Minimal valid PDF structure
- **CSV**: Product lists with various column formats
- **Images**: Fake image headers with correct magic bytes
- **ZIP**: Simulated ZIP content for expansion testing

## 🐛 Debugging Failed Tests

### Common Issues

1. **Pandas ImportError**: Install pandas and openpyxl
2. **OCR ImportError**: Install pytesseract, pillow, pdf2image
3. **API Connection**: Ensure Flask app is configured correctly
4. **Feature Flag**: Check environment variables are set

### Debug Commands

```bash
# Run with detailed output
pytest backend/tests/ -v -s

# Run specific test
pytest backend/tests/unit/test_content_detection.py::test_detect_pdf_magic -v

# Show test coverage
pytest --cov=backend.services.rfx_processor backend/tests/unit/
```

## 🎭 Mock Examples

### Mocking OCR Dependencies

```python
def test_ocr_unavailable(monkeypatch):
    def mock_import_error(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError("No module named 'pytesseract'")
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import_error)
    # Test code here
```

### Mocking Service Methods

```python
def test_with_mocked_service():
    with patch('backend.api.rfx.RFXProcessorService') as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance
        # Test code here
```

## 📈 Performance Considerations

- Tests use minimal file sizes to run quickly
- OCR dependencies are mocked to avoid slow processing
- Optional dependencies are gracefully skipped
- Feature flags allow testing without expensive operations

## 🔒 Security Testing

The test suite validates:

- File type restrictions
- File size limits
- Malicious file handling
- Input sanitization
- Error message security (no sensitive data exposure)
