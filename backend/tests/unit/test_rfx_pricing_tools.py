from backend.services.tools.resolve_unit_packaging_tool import resolve_unit_packaging_tool
from backend.services.tools.calculate_line_price_tool import calculate_line_price_tool
from backend.services.tools.verify_pricing_totals_tool import verify_pricing_totals_tool


def test_resolve_units_kg_direct():
    res = resolve_unit_packaging_tool(2.3, "kg", "kg")
    assert res["status"] == "success"
    assert res["compatible"] is True
    assert abs(res["quantity_in_pricing_unit"] - 2.3) < 1e-9
    assert abs(res["pricing_base_qty"] - 1.0) < 1e-9


def test_resolve_pack_x10_units():
    res = resolve_unit_packaging_tool(20, "unidades", "pack x10")
    assert res["status"] == "success"
    assert res["compatible"] is True
    assert res["pricing_unit"] == "unit"
    assert abs(res["pricing_base_qty"] - 10.0) < 1e-9


def test_line_price_examples():
    kg_line = calculate_line_price_tool(2.3, 1.0, 10.0)
    assert kg_line["status"] == "success"
    assert abs(kg_line["line_total"] - 23.0) < 1e-9

    pack_line = calculate_line_price_tool(20.0, 10.0, 14.0)
    assert pack_line["status"] == "success"
    assert abs(pack_line["line_total"] - 28.0) < 1e-9


def test_verify_totals():
    result = verify_pricing_totals_tool(
        [
            {"line_total": 23.0},
            {"line_total": 28.0},
        ]
    )
    assert result["status"] == "success"
    assert result["is_valid"] is True
    assert abs(result["subtotal"] - 51.0) < 1e-9
