"""
Unit tests for spreadsheet parsing in multi-file RFX processing
"""
import io
import os
import pytest

from backend.services.rfx_processor import RFXProcessorService

pandas = pytest.importorskip("pandas")  # skip if pandas not installed

@pytest.fixture
def svc():
    return RFXProcessorService()

def test_parse_csv_items(svc):
    """Test parsing CSV with standard columns"""
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,200,pcs\nPantalon,50,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2
    assert out["items"][0]["nombre"] == "Camiseta"
    assert out["items"][0]["cantidad"] == 200
    assert out["items"][0]["unidad"] == "pcs"
    assert out["items"][1]["nombre"] == "Pantalon"
    assert out["items"][1]["cantidad"] == 50

def test_parse_csv_english_columns(svc):
    """Test parsing CSV with English column names"""
    csv_bytes = b"product,quantity,unit\nShirt,10,pieces\nPants,5,pieces\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2
    assert out["items"][0]["nombre"] == "Shirt"
    assert out["items"][0]["cantidad"] == 10
    assert out["items"][0]["unidad"] == "pieces"

def test_parse_csv_alternative_columns(svc):
    """Test parsing CSV with alternative column names"""
    csv_bytes = b"item,qty,uom\nWidget,100,units\nGadget,25,boxes\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2
    assert out["items"][0]["nombre"] == "Widget"
    assert out["items"][0]["cantidad"] == 100
    assert out["items"][0]["unidad"] == "units"

def test_parse_xlsx_items(svc):
    """Test parsing XLSX file"""
    import pandas as pd
    from io import BytesIO
    
    df = pd.DataFrame({
        "Producto": ["A", "B"], 
        "Cantidad": [3, 7], 
        "Unidad": ["u", "u"]
    })
    buf = BytesIO()
    
    with pytest.importorskip("openpyxl"):
        df.to_excel(buf, index=False)
    
    out = svc._parse_spreadsheet_items("items.xlsx", buf.getvalue())
    assert len(out["items"]) == 2
    assert out["items"][0]["nombre"] == "A"
    assert out["items"][0]["cantidad"] == 3
    assert out["items"][1]["nombre"] == "B"
    assert out["items"][1]["cantidad"] == 7

def test_parse_csv_missing_columns(svc):
    """Test parsing CSV with missing optional columns"""
    csv_bytes = b"producto\nCamiseta\nPantalon\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2
    assert out["items"][0]["nombre"] == "Camiseta"
    assert out["items"][0]["cantidad"] == 1  # default
    assert out["items"][0]["unidad"] == "unidades"  # default

def test_parse_csv_empty_rows(svc):
    """Test parsing CSV with empty rows"""
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,200,pcs\n,0,\nPantalon,50,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2  # empty row skipped
    assert out["items"][0]["nombre"] == "Camiseta"
    assert out["items"][1]["nombre"] == "Pantalon"

def test_parse_csv_nan_values(svc):
    """Test parsing CSV with NaN/null values"""
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,200,pcs\nnan,50,pcs\nNone,30,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 1  # only valid row
    assert out["items"][0]["nombre"] == "Camiseta"

def test_parse_csv_invalid_quantity(svc):
    """Test parsing CSV with invalid quantity values"""
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,abc,pcs\nPantalon,50.5,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert len(out["items"]) == 2
    assert out["items"][0]["cantidad"] == 1  # fallback for invalid
    assert out["items"][1]["cantidad"] == 50  # rounded down

def test_parse_csv_text_output(svc):
    """Test that text output is generated correctly"""
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,200,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert "ITEMS_FROM_SPREADSHEET (CANONICAL)" in out["text"]
    assert "nombre,cantidad,unidad" in out["text"]
    assert "Camiseta,200,pcs" in out["text"]

def test_parse_invalid_csv(svc):
    """Test parsing invalid CSV content"""
    csv_bytes = b"invalid csv content with\x00binary\x01data"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert out["items"] == []
    assert out["text"] == ""

def test_parse_empty_csv(svc):
    """Test parsing empty CSV file"""
    csv_bytes = b""
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert out["items"] == []
    assert out["text"] == ""

def test_pandas_not_available(svc, monkeypatch):
    """Test behavior when pandas is not available"""
    def mock_import_error(*args, **kwargs):
        raise ImportError("pandas not installed")
    
    monkeypatch.setattr("builtins.__import__", mock_import_error)
    
    csv_bytes = b"producto,cantidad,unidad\nCamiseta,200,pcs\n"
    out = svc._parse_spreadsheet_items("items.csv", csv_bytes)
    assert out["items"] == []
    assert out["text"] == ""
