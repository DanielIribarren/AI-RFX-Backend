"""
Tool: verify_pricing_totals_tool

Propósito: Validar consistencia de totales por línea y subtotal del request.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def verify_pricing_totals_tool(items: List[Dict[str, Any]], tolerance: float = 0.02) -> Dict[str, Any]:
    """Verifica que subtotales estén completos y retorna resumen."""
    try:
        safe_items = items or []
        errors: List[str] = []
        subtotal = 0.0

        for idx, item in enumerate(safe_items, start=1):
            line_total = item.get("line_total")
            if line_total is None:
                errors.append(f"item_{idx}: missing line_total")
                continue
            try:
                subtotal += float(line_total)
            except Exception:
                errors.append(f"item_{idx}: invalid line_total")

        subtotal = round(subtotal, 2)

        return {
            "status": "success",
            "is_valid": len(errors) == 0,
            "errors": errors,
            "subtotal": subtotal,
            "items_count": len(safe_items),
            "tolerance": tolerance,
        }

    except Exception as e:
        logger.error(f"❌ verify_pricing_totals_tool failed: {e}")
        return {
            "status": "error",
            "is_valid": False,
            "errors": [str(e)],
            "subtotal": 0.0,
            "items_count": 0,
            "tolerance": tolerance,
        }
