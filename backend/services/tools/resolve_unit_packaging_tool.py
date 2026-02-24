"""
Tool: resolve_unit_packaging_tool

Propósito: Resolver equivalencia entre unidad solicitada y unidad/precio del catálogo.
No calcula dinero final, solo devuelve parámetros de conversión.
"""

from typing import Any, Dict
import logging
import re

logger = logging.getLogger(__name__)


_UNIT_ALIASES = {
    "unidad": "unit",
    "unidades": "unit",
    "unit": "unit",
    "units": "unit",
    "pieza": "unit",
    "piezas": "unit",
    "ea": "unit",
    "each": "unit",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    "g": "g",
    "gr": "g",
    "gramo": "g",
    "gramos": "g",
    "l": "l",
    "lt": "l",
    "litro": "l",
    "litros": "l",
    "ml": "ml",
    "docena": "dozen",
    "docenas": "dozen",
    "dozen": "dozen",
}


def _canonical(unit: str) -> str:
    u = (unit or "").strip().lower()
    return _UNIT_ALIASES.get(u, u or "unit")


def _parse_packaging(unit_label: str) -> Dict[str, Any]:
    label = (unit_label or "").strip().lower()

    # pack x10 / paquete x 10 / caja x 12
    m = re.search(r"(?:pack|paquete|caja)\s*x\s*(\d+(?:\.\d+)?)", label)
    if m:
        return {"base_qty": float(m.group(1)), "base_unit": "unit", "source": "pack_regex"}

    # "10 unidades"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:unidades|unidad|unit|units|piezas|pieza)", label)
    if m:
        return {"base_qty": float(m.group(1)), "base_unit": "unit", "source": "counted_units"}

    c = _canonical(label)
    if c == "dozen":
        return {"base_qty": 12.0, "base_unit": "unit", "source": "dozen"}

    return {"base_qty": 1.0, "base_unit": c, "source": "default"}


def _convert_quantity(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    f = _canonical(from_unit)
    t = _canonical(to_unit)

    if f == t:
        return {"ok": True, "value": float(value), "factor": 1.0}

    # weight
    if f == "g" and t == "kg":
        return {"ok": True, "value": float(value) / 1000.0, "factor": 0.001}
    if f == "kg" and t == "g":
        return {"ok": True, "value": float(value) * 1000.0, "factor": 1000.0}

    # volume
    if f == "ml" and t == "l":
        return {"ok": True, "value": float(value) / 1000.0, "factor": 0.001}
    if f == "l" and t == "ml":
        return {"ok": True, "value": float(value) * 1000.0, "factor": 1000.0}

    return {"ok": False, "value": None, "factor": None}


def resolve_unit_packaging_tool(
    requested_quantity: float,
    requested_unit: str,
    catalog_unit: str,
) -> Dict[str, Any]:
    """
    Resuelve equivalencia de unidades/packaging.

    Returns:
      - quantity_in_pricing_unit
      - pricing_base_qty
      - pricing_unit
      - compatible / requires_clarification
    """
    try:
        qty = float(requested_quantity or 0)
        if qty <= 0:
            return {
                "status": "error",
                "message": "requested_quantity must be > 0",
                "compatible": False,
                "requires_clarification": True,
            }

        req_unit = _canonical(requested_unit)
        parsed_catalog = _parse_packaging(catalog_unit)
        pricing_base_qty = float(parsed_catalog["base_qty"])
        pricing_unit = parsed_catalog["base_unit"]

        converted = _convert_quantity(qty, req_unit, pricing_unit)
        if not converted["ok"]:
            return {
                "status": "success",
                "compatible": False,
                "requires_clarification": True,
                "message": f"Incompatible units: requested={req_unit}, catalog={pricing_unit}",
                "requested_quantity": qty,
                "requested_unit": req_unit,
                "pricing_base_qty": pricing_base_qty,
                "pricing_unit": pricing_unit,
                "quantity_in_pricing_unit": None,
                "conversion_factor": None,
            }

        return {
            "status": "success",
            "compatible": True,
            "requires_clarification": False,
            "message": "Units resolved",
            "requested_quantity": qty,
            "requested_unit": req_unit,
            "pricing_base_qty": pricing_base_qty,
            "pricing_unit": pricing_unit,
            "quantity_in_pricing_unit": float(converted["value"]),
            "conversion_factor": float(converted["factor"]),
            "packaging_source": parsed_catalog["source"],
        }

    except Exception as e:
        logger.error(f"❌ resolve_unit_packaging_tool failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "compatible": False,
            "requires_clarification": True,
        }
