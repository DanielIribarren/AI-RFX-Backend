"""
Tool: search_catalog_variants_tool

Propósito: Buscar variantes de un producto en catálogo para que el orquestador LLM
pueda decidir el mejor match con trazabilidad.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def search_catalog_variants_tool(
    product_name: str,
    organization_id: Optional[str],
    catalog_search,
    max_variants: int = 5,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Busca variantes en catálogo usando el servicio híbrido existente."""
    try:
        if not product_name:
            return {
                "status": "error",
                "message": "product_name is required",
                "variants": [],
            }

        if not catalog_search:
            return {
                "status": "error",
                "message": "catalog_search service unavailable",
                "variants": [],
            }

        variants = catalog_search.search_product_variants(
            query=product_name,
            organization_id=organization_id,
            user_id=user_id,
            max_variants=max_variants,
        )

        normalized: List[Dict[str, Any]] = []
        for v in variants or []:
            normalized.append(
                {
                    "id": v.get("id"),
                    "product_name": v.get("product_name"),
                    "unit": v.get("unit", "unit"),
                    "unit_price": v.get("unit_price"),
                    "unit_cost": v.get("unit_cost"),
                    "product_type": v.get("product_type", "simple"),
                    "bundle_schema": v.get("bundle_schema") or {},
                    "constraint_rules": v.get("constraint_rules") or {},
                    "semantic_tags": v.get("semantic_tags") or [],
                    "confidence": float(v.get("confidence") or 0.0),
                    "match_type": v.get("match_type", "unknown"),
                }
            )

        return {
            "status": "success",
            "message": f"Found {len(normalized)} variants",
            "variants": normalized,
        }

    except Exception as e:
        logger.error(f"❌ search_catalog_variants_tool failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "variants": [],
        }
