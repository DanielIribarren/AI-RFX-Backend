"""
Tool: calculate_line_price_tool

Propósito: Calcular total de línea de forma determinista a partir de parámetros
resueltos por unidad/packaging.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def calculate_line_price_tool(
    quantity_in_pricing_unit: float,
    pricing_base_qty: float,
    unit_price: float,
    rounding_decimals: int = 2,
) -> Dict[str, Any]:
    """Calcula total de línea con fórmula auditable."""
    try:
        qty = float(quantity_in_pricing_unit)
        base_qty = float(pricing_base_qty)
        price = float(unit_price)

        if qty <= 0 or base_qty <= 0 or price < 0:
            return {
                "status": "error",
                "message": "Invalid inputs for pricing calculation",
            }

        billable_units = qty / base_qty
        line_total_raw = billable_units * price
        line_total = round(line_total_raw, rounding_decimals)

        effective_unit_price = round(price / base_qty, 6)

        return {
            "status": "success",
            "billable_units": billable_units,
            "line_total": line_total,
            "line_total_raw": line_total_raw,
            "effective_unit_price": effective_unit_price,
            "formula": f"({qty} / {base_qty}) * {price}",
            "rounding_decimals": rounding_decimals,
        }

    except Exception as e:
        logger.error(f"❌ calculate_line_price_tool failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
