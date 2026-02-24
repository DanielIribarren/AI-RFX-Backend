"""
RFX Pricing Orchestrator Agent

Orquestador LLM-first con function-calling:
- El LLM decide qué tools usar
- Las tools ejecutan operaciones de catálogo, unidad y pricing
- La salida final es JSON estricto para integración con RFXProcessor
"""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from backend.prompts.rfx_orchestrator_system_prompt import RFX_ORCHESTRATOR_SYSTEM_PROMPT
from backend.services.tools.search_catalog_variants_tool import search_catalog_variants_tool
from backend.services.tools.resolve_unit_packaging_tool import resolve_unit_packaging_tool
from backend.services.tools.calculate_line_price_tool import calculate_line_price_tool
from backend.services.tools.verify_pricing_totals_tool import verify_pricing_totals_tool

logger = logging.getLogger(__name__)


class RFXOrchestratorAgent:
    """LLM orchestrator for product matching and pricing."""

    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o-mini"):
        self.openai_client = openai_client
        self.model = model
        self.max_rounds = 10

    def orchestrate(
        self,
        products: List[Dict[str, Any]],
        organization_id: Optional[str],
        rfx_context: Optional[Dict[str, Any]],
        catalog_search,
    ) -> Dict[str, Any]:
        if not products:
            return {"status": "success", "items": [], "summary": {"matched": 0, "clarifications": 0}}

        user_payload = {
            "organization_id": organization_id,
            "rfx_context": rfx_context or {},
            "products": products,
        }

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": RFX_ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
        ]

        tools = self._tools_schema()

        for _ in range(self.max_rounds):
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0,
                max_tokens=2200,
            )

            msg = response.choices[0].message
            tool_calls = msg.tool_calls or []

            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [tc.model_dump() for tc in tool_calls],
                    }
                )

                for tc in tool_calls:
                    tool_name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}

                    result = self._execute_tool(tool_name, args, organization_id, catalog_search)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=True),
                        }
                    )
                continue

            final_text = msg.content or "{}"
            parsed = self._safe_parse_json(final_text)
            if parsed.get("status") == "success" and isinstance(parsed.get("items"), list):
                return parsed

            logger.warning("⚠️ Orchestrator returned non-parseable final content, using fallback")
            break

        return self._fallback(products, organization_id, catalog_search)

    def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        organization_id: Optional[str],
        catalog_search,
    ) -> Dict[str, Any]:
        if tool_name == "search_catalog_variants_tool":
            return search_catalog_variants_tool(
                product_name=args.get("product_name", ""),
                organization_id=organization_id,
                catalog_search=catalog_search,
                max_variants=int(args.get("max_variants", 5)),
            )

        if tool_name == "resolve_unit_packaging_tool":
            return resolve_unit_packaging_tool(
                requested_quantity=float(args.get("requested_quantity", 0) or 0),
                requested_unit=args.get("requested_unit", "unit"),
                catalog_unit=args.get("catalog_unit", "unit"),
            )

        if tool_name == "calculate_line_price_tool":
            return calculate_line_price_tool(
                quantity_in_pricing_unit=float(args.get("quantity_in_pricing_unit", 0) or 0),
                pricing_base_qty=float(args.get("pricing_base_qty", 1) or 1),
                unit_price=float(args.get("unit_price", 0) or 0),
                rounding_decimals=int(args.get("rounding_decimals", 2)),
            )

        if tool_name == "verify_pricing_totals_tool":
            return verify_pricing_totals_tool(items=args.get("items", []))

        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    def _tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_catalog_variants_tool",
                    "description": "Search matching variants for a product in catalog",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "max_variants": {"type": "integer", "default": 5},
                        },
                        "required": ["product_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "resolve_unit_packaging_tool",
                    "description": "Resolve requested units against catalog pricing unit and packaging",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "requested_quantity": {"type": "number"},
                            "requested_unit": {"type": "string"},
                            "catalog_unit": {"type": "string"},
                        },
                        "required": ["requested_quantity", "requested_unit", "catalog_unit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_line_price_tool",
                    "description": "Deterministically calculate line total from resolved pricing params",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "quantity_in_pricing_unit": {"type": "number"},
                            "pricing_base_qty": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "rounding_decimals": {"type": "integer", "default": 2},
                        },
                        "required": ["quantity_in_pricing_unit", "pricing_base_qty", "unit_price"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_pricing_totals_tool",
                    "description": "Verify line totals and return subtotal",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"type": "object"},
                            }
                        },
                        "required": ["items"],
                    },
                },
            },
        ]

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except Exception:
            pass

        try:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
        except Exception:
            pass

        return {}

    def _fallback(
        self,
        products: List[Dict[str, Any]],
        organization_id: Optional[str],
        catalog_search,
    ) -> Dict[str, Any]:
        """Fallback conservador: primera variante + cálculo básico."""
        items: List[Dict[str, Any]] = []
        matched = 0
        clarifications = 0

        for p in products:
            name = p.get("nombre", "")
            qty = float(p.get("cantidad", 1) or 1)
            unit = p.get("unidad", "unit")
            unit_price = float(p.get("precio_unitario") or p.get("unit_price") or 0)
            unit_cost = float(p.get("costo_unitario") or p.get("unit_cost") or 0)
            catalog_name = None
            catalog_conf = 0.0
            catalog_match = False
            formula = None
            requires_clarification = False

            if catalog_search and name:
                result = search_catalog_variants_tool(
                    product_name=name,
                    organization_id=organization_id,
                    catalog_search=catalog_search,
                    max_variants=1,
                )
                variants = result.get("variants", [])
                if variants:
                    top = variants[0]
                    unit_price = float(top.get("unit_price") or unit_price or 0)
                    unit_cost = float(top.get("unit_cost") or unit_cost or 0)
                    catalog_name = top.get("product_name")
                    catalog_conf = float(top.get("confidence") or 0.0)
                    catalog_match = catalog_conf >= 0.75
                    if catalog_match:
                        matched += 1

                    unit_res = resolve_unit_packaging_tool(
                        requested_quantity=qty,
                        requested_unit=unit,
                        catalog_unit=top.get("unit", "unit"),
                    )
                    if unit_res.get("compatible"):
                        price_calc = calculate_line_price_tool(
                            quantity_in_pricing_unit=unit_res.get("quantity_in_pricing_unit", qty),
                            pricing_base_qty=unit_res.get("pricing_base_qty", 1),
                            unit_price=unit_price,
                        )
                        line_total = float(price_calc.get("line_total") or 0)
                        formula = price_calc.get("formula")
                    else:
                        line_total = round(qty * unit_price, 2)
                        requires_clarification = True
                        clarifications += 1
                else:
                    line_total = round(qty * unit_price, 2)
            else:
                line_total = round(qty * unit_price, 2)

            items.append(
                {
                    **p,
                    "precio_unitario": unit_price,
                    "costo_unitario": unit_cost,
                    "line_total": line_total,
                    "catalog_match": catalog_match,
                    "catalog_product_name": catalog_name,
                    "catalog_confidence": catalog_conf,
                    "pricing_source": "fallback_orchestrator",
                    "requires_clarification": requires_clarification,
                    "formula": formula or f"{qty} * {unit_price}",
                }
            )

        verify = verify_pricing_totals_tool(items)
        return {
            "status": "success",
            "items": items,
            "summary": {
                "matched": matched,
                "clarifications": clarifications,
                "subtotal": verify.get("subtotal", 0),
            },
        }
