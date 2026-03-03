"""
ProductResolutionService

Servicio compartido para resolver productos en ambos flujos:
- Extracción inicial (RFXProcessor)
- Edición conversacional (Chat tools)

Objetivo: una sola lógica para matching + unidad + pricing + bundles.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from backend.services.tools.search_catalog_variants_tool import search_catalog_variants_tool
from backend.services.tools.resolve_complex_bundle_tool import resolve_complex_bundle_tool
from backend.services.tools.resolve_unit_packaging_tool import resolve_unit_packaging_tool
from backend.services.tools.calculate_line_price_tool import calculate_line_price_tool
from backend.services.tools.verify_pricing_totals_tool import verify_pricing_totals_tool

logger = logging.getLogger(__name__)


class ProductResolutionService:
    """
    Resolver central de productos.

    Reglas:
    - No inventar precios.
    - Si no hay match confiable: mantener precio explícito del usuario o 0.
    - Si detecta composición (sabores/toppings), construir breakdown inferido.
    """

    def __init__(self, catalog_search=None, rfx_orchestrator_agent=None):
        self.catalog_search = catalog_search
        self.rfx_orchestrator_agent = rfx_orchestrator_agent
        self.catalog_confidence_min = 0.75

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def resolve_for_rfx_extraction(
        self,
        products: List[Dict[str, Any]],
        organization_id: Optional[str],
        user_id: Optional[str] = None,
        rfx_context: Optional[Dict[str, Any]] = None,
        fallback_resolver: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Resolución para pipeline de extracción.
        Prioriza orquestador LLM; fallback a resolver legacy o determinista.
        """
        if not products:
            return []

        rfx_context = rfx_context or {}

        if not self.rfx_orchestrator_agent:
            logger.warning("⚠️ Product resolver without orchestrator agent - using fallback/deterministic")
            if fallback_resolver:
                return fallback_resolver(products)
            return self.resolve_for_chat_products(products, organization_id, user_id=user_id, rfx_context=rfx_context)

        try:
            result = self.rfx_orchestrator_agent.orchestrate(
                products=products,
                organization_id=organization_id,
                rfx_context=rfx_context,
                catalog_search=self.catalog_search,
            )

            if result.get("status") != "success":
                raise RuntimeError(f"orchestrator status={result.get('status')}")

            items = result.get("items", [])
            if not isinstance(items, list) or not items:
                raise RuntimeError("orchestrator returned empty items")

            normalized = self._normalize_orchestrated_items(
                original_products=products,
                orchestrated_items=items,
                organization_id=organization_id,
                user_id=user_id,
            )

            return self._apply_hybrid_bundle_inference(normalized, organization_id, user_id, rfx_context)

        except Exception as e:
            logger.error(f"❌ Product resolver orchestrator failed: {e}")
            if fallback_resolver:
                return fallback_resolver(products)
            return self.resolve_for_chat_products(products, organization_id, user_id=user_id, rfx_context=rfx_context)

    def resolve_for_chat_products(
        self,
        products: List[Dict[str, Any]],
        organization_id: Optional[str],
        user_id: Optional[str] = None,
        rfx_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Resolución determinista para flujo conversacional.
        Usa tools compartidas para asegurar consistencia con extracción.
        """
        if not products:
            return []

        rfx_context = rfx_context or {}
        resolved: List[Dict[str, Any]] = []

        for product in products:
            resolved.append(
                self._resolve_single_product_deterministic(
                    product=product,
                    organization_id=organization_id,
                    user_id=user_id,
                    rfx_context=rfx_context,
                )
            )

        verify = verify_pricing_totals_tool([{"line_total": p.get("estimated_line_total", 0)} for p in resolved])
        logger.info(
            "✅ Chat product resolution done: items=%s subtotal=%s",
            len(resolved),
            verify.get("subtotal", 0),
        )
        return self._apply_hybrid_bundle_inference(resolved, organization_id, user_id, rfx_context)

    # ------------------------------------------------------------------
    # Internal helpers (shared behavior)
    # ------------------------------------------------------------------
    def _normalize_orchestrated_items(
        self,
        original_products: List[Dict[str, Any]],
        orchestrated_items: List[Dict[str, Any]],
        organization_id: Optional[str],
        user_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        normalized_products: List[Dict[str, Any]] = []
        clarifications = 0

        for idx, original in enumerate(original_products):
            item = orchestrated_items[idx] if idx < len(orchestrated_items) else {}
            qty = item.get("cantidad", original.get("cantidad", 1))
            price = item.get("precio_unitario", original.get("precio_unitario", original.get("unit_price")))
            cost = item.get("costo_unitario", original.get("costo_unitario", original.get("unit_cost")))
            line_total = item.get("line_total")
            requires_clarification = bool(item.get("requires_clarification"))

            # Determinismo en ambigüedad: top confidence variant
            product_name = original.get("nombre", "")
            should_force_top_confidence = (
                requires_clarification or price in (None, 0, 0.0) or cost in (None, 0, 0.0)
            )
            if self.catalog_search and product_name and should_force_top_confidence:
                try:
                    variants = self.catalog_search.search_product_variants(
                        query=product_name,
                        organization_id=organization_id,
                        user_id=user_id,
                        max_variants=5,
                    )
                    if variants:
                        best_variant = variants[0]
                        best_conf = float(best_variant.get("confidence") or 0.0)
                        price = best_variant.get("unit_price") if best_variant.get("unit_price") is not None else price
                        cost = best_variant.get("unit_cost") if best_variant.get("unit_cost") is not None else cost
                        item["catalog_match"] = best_conf >= 0.75
                        item["catalog_product_name"] = best_variant.get("product_name")
                        item["catalog_confidence"] = best_conf
                        item["pricing_source"] = "top_confidence_variant"
                        requires_clarification = False
                except Exception as variant_err:
                    logger.warning(f"⚠️ Top-confidence fallback failed for '{product_name}': {variant_err}")

            bundle_breakdown = item.get("bundle_breakdown")
            specs = item.get("specifications") or {}
            if bundle_breakdown and not specs:
                specs = {
                    "is_bundle": True,
                    "inferred_bundle": False,
                    "requires_clarification": requires_clarification,
                    "bundle_breakdown": bundle_breakdown,
                }

            if requires_clarification:
                clarifications += 1

            normalized_products.append(
                {
                    **original,
                    **item,
                    "cantidad": qty,
                    "precio_unitario": float(price or 0),
                    "costo_unitario": float(cost or 0),
                    "estimated_line_total": float(line_total or 0),
                    "requires_clarification": requires_clarification,
                    "pricing_source": item.get("pricing_source", "llm_orchestrated_tools"),
                    "bundle_breakdown": bundle_breakdown or specs.get("bundle_breakdown") or [],
                    "specifications": specs or {
                        "is_bundle": False,
                        "inferred_bundle": False,
                        "requires_clarification": requires_clarification,
                        "bundle_breakdown": [],
                    },
                }
            )

        logger.info(
            "✅ LLM orchestration normalized: items=%s clarifications=%s",
            len(normalized_products),
            clarifications,
        )
        return normalized_products

    def _resolve_single_product_deterministic(
        self,
        product: Dict[str, Any],
        organization_id: Optional[str],
        user_id: Optional[str],
        rfx_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        name = str(
            product.get("nombre")
            or product.get("name")
            or product.get("product_name")
            or ""
        ).strip()
        qty = float(product.get("cantidad") or product.get("quantity") or 1)
        req_unit = str(product.get("unidad") or product.get("unit") or "unidades").strip().lower()
        description = str(product.get("descripcion") or product.get("description") or "").strip()
        notes = str(product.get("notas") or product.get("notes") or "").strip()
        raw_specs_value = product.get("specifications")
        if raw_specs_value is None:
            raw_specs_value = product.get("especificaciones")

        explicit_price = self._extract_explicit_number(
            product,
            keys=("precio_unitario", "price_unit", "unit_price", "estimated_unit_price"),
        )
        explicit_cost = self._extract_explicit_number(
            product,
            keys=("costo_unitario", "unit_cost"),
        )
        provided_specs = raw_specs_value or {}
        if not isinstance(provided_specs, dict):
            provided_specs = {}
        specs_text = ""
        if isinstance(raw_specs_value, str):
            specs_text = raw_specs_value.strip()
        elif isinstance(raw_specs_value, dict):
            details = raw_specs_value.get("details")
            if isinstance(details, str):
                specs_text = details.strip()
        provided_breakdown = self._normalize_breakdown_items(
            product.get("bundle_breakdown") or provided_specs.get("bundle_breakdown") or []
        )
        if provided_breakdown:
            provided_breakdown = self._enrich_breakdown_with_catalog_prices(
                breakdown=provided_breakdown,
                organization_id=organization_id,
                user_id=user_id,
            )

        catalog_variant: Optional[Dict[str, Any]] = None
        if self.catalog_search and name:
            variants_result = search_catalog_variants_tool(
                product_name=name,
                organization_id=organization_id,
                user_id=user_id,
                catalog_search=self.catalog_search,
                max_variants=5,
            )
            variants = variants_result.get("variants", [])
            if variants:
                catalog_variant = variants[0]

        catalog_unit = req_unit
        catalog_confidence = 0.0
        catalog_match = False
        catalog_product_name = None
        pricing_source = "chat_resolver_no_catalog"
        unit_price = float(explicit_price or 0)
        unit_cost = float(explicit_cost or 0)
        requires_clarification = bool(provided_specs.get("requires_clarification", False))
        bundle_breakdown: List[Dict[str, Any]] = provided_breakdown
        inferred_bundle = bool(provided_specs.get("inferred_bundle", False))

        if catalog_variant:
            catalog_product_name = catalog_variant.get("product_name")
            catalog_confidence = float(catalog_variant.get("confidence") or 0.0)
            catalog_match = catalog_confidence >= 0.75
            if catalog_confidence >= self.catalog_confidence_min:
                catalog_unit = str(catalog_variant.get("unit") or req_unit)

                if explicit_price <= 0:
                    unit_price = float(catalog_variant.get("unit_price") or unit_price or 0)
                if explicit_cost <= 0:
                    unit_cost = float(catalog_variant.get("unit_cost") or unit_cost or 0)

                pricing_source = "chat_resolver_catalog" if catalog_match else "chat_resolver_low_conf_catalog"

                product_type = str(catalog_variant.get("product_type") or "simple")
                bundle_schema = catalog_variant.get("bundle_schema") or {}
                if (not bundle_breakdown) and product_type in {"complex_bundle", "service_bundle"} and bundle_schema:
                    hints = self._build_requirement_hints(name, description, notes, specs_text, rfx_context)
                    bundle_result = resolve_complex_bundle_tool(
                        bundle_schema=bundle_schema,
                        requirement_hints=hints,
                        fallback_policy="ask_user",
                    )
                    bundle_breakdown = self._normalize_breakdown_items(bundle_result.get("breakdown") or [])
                    requires_clarification = requires_clarification or bool(bundle_result.get("requires_clarification"))
                    pricing_source = "chat_resolver_catalog_bundle"
            else:
                pricing_source = "chat_resolver_low_conf_catalog_ignored"
                requires_clarification = True

        # Si el usuario solo dio costo explícito y no hay precio comercial, usarlo como precio base.
        if unit_price <= 0 and explicit_cost > 0:
            catalog_has_price = float((catalog_variant or {}).get("unit_price") or 0.0) > 0
            if not catalog_has_price:
                unit_price = float(explicit_cost)
                if pricing_source.startswith("chat_resolver_catalog"):
                    pricing_source = "chat_resolver_catalog_cost_fallback_as_price"
                else:
                    pricing_source = "chat_resolver_explicit_cost_as_price"

        if not bundle_breakdown:
            inferred = self._infer_composite_breakdown(
                name=name,
                description=description,
                notes=f"{notes} {specs_text}".strip(),
            )
            if inferred:
                bundle_breakdown = inferred
                inferred_bundle = True
                pricing_source = "chat_resolver_inferred_bundle"

        # Si llegó un breakdown explícito con precios por subitem y no hay precio del padre,
        # derivar precio del padre sin inventar.
        if unit_price <= 0 and bundle_breakdown:
            breakdown_total = 0.0
            for item in bundle_breakdown:
                b_qty = self._safe_float(item.get("cantidad") or item.get("quantity") or item.get("qty"), 0.0)
                b_price = self._safe_float(
                    item.get("precio_unitario") or item.get("unit_price") or item.get("price") or item.get("price_unit"),
                    0.0,
                )
                if b_qty > 0 and b_price > 0:
                    breakdown_total += (b_qty * b_price)
            if breakdown_total > 0:
                unit_price = round(breakdown_total / (qty if qty > 0 else 1.0), 4)
                pricing_source = "chat_resolver_breakdown_price_sum"

        unit_res = resolve_unit_packaging_tool(
            requested_quantity=qty,
            requested_unit=req_unit,
            catalog_unit=catalog_unit,
        )
        if unit_res.get("compatible"):
            calc = calculate_line_price_tool(
                quantity_in_pricing_unit=float(unit_res.get("quantity_in_pricing_unit") or qty),
                pricing_base_qty=float(unit_res.get("pricing_base_qty") or 1),
                unit_price=float(unit_price),
            )
            line_total = float(calc.get("line_total") or 0)
            formula = calc.get("formula")
        else:
            line_total = round(qty * unit_price, 2)
            formula = f"{qty} * {unit_price}"
            requires_clarification = True

        if unit_price <= 0:
            requires_clarification = True

        specs = {
            "is_bundle": bool(bundle_breakdown),
            "inferred_bundle": inferred_bundle,
            "requires_clarification": requires_clarification,
            "bundle_breakdown": bundle_breakdown,
        }

        return {
            "nombre": name,
            "descripcion": description,
            "cantidad": qty,
            "unidad": req_unit,
            "precio_unitario": float(unit_price or 0),
            "costo_unitario": float(unit_cost or 0),
            "estimated_line_total": float(line_total or 0),
            "catalog_match": catalog_match,
            "catalog_product_name": catalog_product_name,
            "catalog_confidence": catalog_confidence,
            "pricing_source": pricing_source,
            "requires_clarification": requires_clarification,
            "formula": formula,
            "bundle_breakdown": bundle_breakdown,
            "specifications": specs,
            "notas": notes,
        }

    def _apply_hybrid_bundle_inference(
        self,
        products: List[Dict[str, Any]],
        organization_id: Optional[str],
        user_id: Optional[str],
        rfx_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Modo híbrido:
        1) Si existe bundle padre en catálogo (menú semanal), usarlo.
        2) Si no existe, crear bundle inferido seguro.
        """
        if not products:
            return products

        source_text = str(rfx_context.get("source_text") or "")
        lowered = source_text.lower()

        menu_keywords = [
            "menu ejecutivo", "menú ejecutivo",
            "menu saludable", "menú saludable",
            "menu de la semana", "menú de la semana",
            "plan semanal", "semana",
        ]
        weekday_tokens = ["lunes", "martes", "miercoles", "miércoles", "jueves", "viernes"]
        weekday_hits = sum(1 for d in weekday_tokens if d in lowered)
        explicit_menu_signal = any(k in lowered for k in menu_keywords)
        candidate_signal = explicit_menu_signal and weekday_hits >= 2

        if not candidate_signal:
            return products

        # Caso crítico: el extractor ya devolvió un solo "menú semanal".
        # Aquí enriquecemos el mismo ítem con breakdown y precio explícito del texto.
        if len(products) == 1:
            base = dict(products[0] or {})
            qty = float(base.get("cantidad") or 1.0)
            explicit_bundle_price = self._extract_explicit_bundle_price(source_text)
            current_price = float(base.get("precio_unitario") or 0.0)
            current_cost = float(base.get("costo_unitario") or 0.0)
            resolved_price = current_price or explicit_bundle_price or current_cost
            resolved_cost = current_cost or current_price or resolved_price
            breakdown = self._build_weekly_breakdown(products, source_text)
            requires_clarification = resolved_price <= 0.0

            specs = base.get("specifications") or base.get("especificaciones") or {}
            if not isinstance(specs, dict):
                specs = {}
            specs.update(
                {
                    "is_bundle": True,
                    "inferred_bundle": True,
                    "requires_clarification": requires_clarification,
                    "bundle_breakdown": breakdown,
                }
            )

            base.update(
                {
                    "nombre": base.get("nombre") or "Menú semanal",
                    "descripcion": base.get("descripcion") or "Producto bundle detectado en solicitud semanal",
                    "cantidad": qty,
                    "unidad": base.get("unidad") or "plan",
                    "precio_unitario": float(resolved_price or 0.0),
                    "costo_unitario": float(resolved_cost or 0.0),
                    "estimated_line_total": round(float(resolved_price or 0.0) * qty, 2),
                    "requires_clarification": requires_clarification,
                    "pricing_source": base.get("pricing_source") or "single_menu_bundle_enrichment",
                    "bundle_breakdown": breakdown,
                    "specifications": specs,
                }
            )
            return [base]

        # Con múltiples productos detectados, también consolidar en bundle semanal.
        if len(products) < 2:
            return products

        parent_variant = None
        if self.catalog_search:
            parent_queries = [
                "Menú Ejecutivo",
                "Menu Ejecutivo",
                "Menú Saludable de la Semana",
                "Menu Saludable de la Semana",
                "Plan Semanal",
            ]
            for query in parent_queries:
                try:
                    variants = self.catalog_search.search_product_variants(
                        query=query,
                        organization_id=organization_id,
                        user_id=user_id,
                        max_variants=3,
                    )
                    if variants:
                        top = variants[0]
                        if top.get("product_type") in {"complex_bundle", "service_bundle"}:
                            parent_variant = top
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Parent bundle search failed for '{query}': {e}")

        breakdown = self._build_weekly_breakdown(products, source_text)

        if parent_variant:
            price = float(parent_variant.get("unit_price") or 0.0)
            cost = float(parent_variant.get("unit_cost") or 0.0)
            requires_clarification = price <= 0.0
            return [
                {
                    "nombre": parent_variant.get("product_name") or "Menú semanal",
                    "descripcion": "Producto bundle detectado automáticamente desde solicitud del cliente",
                    "cantidad": 1.0,
                    "unidad": parent_variant.get("unit") or "plan",
                    "precio_unitario": price,
                    "costo_unitario": cost,
                    "estimated_line_total": round(price, 2),
                    "catalog_match": True,
                    "catalog_product_name": parent_variant.get("product_name"),
                    "catalog_confidence": float(parent_variant.get("confidence") or 0.0),
                    "pricing_source": "catalog_parent_bundle",
                    "requires_clarification": requires_clarification,
                    "bundle_breakdown": breakdown,
                    "specifications": {
                        "is_bundle": True,
                        "inferred_bundle": False,
                        "requires_clarification": requires_clarification,
                        "bundle_breakdown": breakdown,
                    },
                    "notas": "Bundle resuelto con producto padre del inventario",
                }
            ]

        # Fallback bundle inferido (sin inventar precio)
        sum_known_sales = 0.0
        sum_known_cost = 0.0
        known_price_items = 0
        for p in products:
            unit_price = float(p.get("precio_unitario") or 0.0)
            unit_cost = float(p.get("costo_unitario") or 0.0)
            qty = float(p.get("cantidad") or 0.0)
            if unit_price > 0 and qty > 0:
                sum_known_sales += unit_price * qty
                sum_known_cost += unit_cost * qty
                known_price_items += 1

        explicit_bundle_price = self._extract_explicit_bundle_price(source_text)
        inferred_price = (
            explicit_bundle_price
            if explicit_bundle_price is not None
            else (round(sum_known_sales, 2) if known_price_items > 0 else 0.0)
        )
        inferred_cost = round(sum_known_cost, 2) if known_price_items > 0 else 0.0
        requires_clarification = (known_price_items == 0) and (explicit_bundle_price is None)

        return [
            {
                "nombre": "Menú semanal (inferido)",
                "descripcion": "Bundle inferido por IA desde solicitud de menú semanal",
                "cantidad": 1.0,
                "unidad": "plan",
                "precio_unitario": inferred_price,
                "costo_unitario": inferred_cost,
                "estimated_line_total": inferred_price,
                "catalog_match": False,
                "catalog_product_name": None,
                "catalog_confidence": 0.0,
                "pricing_source": "inferred_bundle",
                "requires_clarification": requires_clarification,
                "bundle_breakdown": breakdown,
                "specifications": {
                    "is_bundle": True,
                    "inferred_bundle": True,
                    "requires_clarification": requires_clarification,
                    "pricing_policy": "sum_known_components_or_clarify",
                    "bundle_breakdown": breakdown,
                },
                "notas": (
                    "Bundle inferido automáticamente. Requiere confirmación del cliente antes de propuesta final."
                    if requires_clarification
                    else (
                        "Bundle inferido automáticamente con precio explícito detectado en solicitud."
                        if explicit_bundle_price is not None
                        else "Bundle inferido automáticamente con suma de componentes conocidos."
                    )
                ),
            }
        ]

    def _build_weekly_breakdown(self, products: List[Dict[str, Any]], source_text: str) -> List[Dict[str, Any]]:
        day_order = ["lunes", "martes", "miércoles", "miercoles", "jueves", "viernes"]
        text = source_text or ""
        breakdown: List[Dict[str, Any]] = []

        for day in day_order:
            pattern = (
                rf"(?is)\b{day}\b\s*:?\s*"
                rf"(.*?)(?=\b(?:lunes|martes|miercoles|miércoles|jueves|viernes)\b\s*:|$)"
            )
            m = re.search(pattern, text)
            if m:
                selected = m.group(1).strip(" \n\t;,.")
                if selected:
                    breakdown.append({"slot": day, "selected": {"name": selected, "source": "parsed_text"}})

        if not breakdown:
            for idx, product in enumerate(products[:5]):
                slot = day_order[idx] if idx < len(day_order) else f"dia_{idx+1}"
                breakdown.append(
                    {
                        "slot": slot,
                        "selected": {
                            "name": product.get("nombre") or product.get("product_name") or "producto",
                            "source": "product_order",
                        },
                    }
                )

        return breakdown

    def _build_requirement_hints(
        self,
        name: str,
        description: str,
        notes: str,
        specs_text: str,
        rfx_context: Dict[str, Any],
    ) -> List[str]:
        source_text = str(rfx_context.get("source_text") or "")
        hints = [name, description, notes, specs_text, source_text]
        return [h for h in hints if h and h.strip()]

    def _infer_composite_breakdown(self, name: str, description: str, notes: str) -> List[Dict[str, Any]]:
        """
        Infiere breakdown para productos compuestos aunque no exista bundle en catálogo.
        Caso target: "papas integrales cheddar y pepper".
        """
        text = " ".join([name, description, notes]).strip()
        lowered = text.lower()
        if not lowered:
            return []

        # 1) Patrones explícitos: "X con a, b y c"
        split_tokens = [r"\s+con\s+", r"\s*:\s*"]
        for token in split_tokens:
            parts = re.split(token, lowered, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                options = self._split_options(parts[1])
                if len(options) >= 2:
                    return self._to_breakdown(options)

        # 2) Heurística por sabores/toppings conocidos cuando vienen inline
        known_options = [
            "cheddar", "pepper", "queso", "bbq", "bacon", "jalapeño", "jalapeno",
            "pimienta", "paprika", "mostaza", "mayo", "miel mostaza",
        ]
        found = []
        for opt in known_options:
            if re.search(rf"\b{re.escape(opt)}\b", lowered):
                found.append(opt)
        # preservar orden de aparición en texto
        found = sorted(set(found), key=lambda o: lowered.find(o))
        if len(found) >= 2:
            return self._to_breakdown(found)

        return []

    def _split_options(self, raw: str) -> List[str]:
        cleaned = re.sub(r"[()]", " ", raw.lower())
        cleaned = cleaned.replace("/", ",").replace("|", ",").replace("+", ",")
        cleaned = re.sub(r"\s+y\s+", ",", cleaned)
        parts = [p.strip(" .,-") for p in cleaned.split(",") if p.strip(" .,-")]
        dedup: List[str] = []
        for p in parts:
            if p not in dedup:
                dedup.append(p)
        return dedup

    def _to_breakdown(self, options: List[str]) -> List[Dict[str, Any]]:
        return [
            {
                "slot": f"opcion_{idx + 1}",
                "selected": {"name": opt.title(), "source": "inferred_hints"},
                "required": True,
            }
            for idx, opt in enumerate(options)
        ]

    def _extract_explicit_number(self, data: Dict[str, Any], keys: tuple[str, ...]) -> float:
        for key in keys:
            if key in data and data.get(key) is not None:
                try:
                    return max(0.0, float(data.get(key)))
                except (TypeError, ValueError):
                    continue
        return 0.0

    def _extract_explicit_bundle_price(self, source_text: str) -> Optional[float]:
        """
        Busca precio explícito de plan/menu semanal en texto.
        Ejemplos soportados: "$75", "75$", "vale 75", "precio: 75".
        """
        text = (source_text or "").lower()
        if not text:
            return None

        patterns = [
            r"(?:men[uú]\s+\w+\s+de\s+la\s+semana|men[uú]\s+semanal|plan\s+semanal|men[uú]\s+ejecutivo)[^$\d]{0,80}\$\s*([0-9]+(?:[.,][0-9]{1,2})?)",
            r"(?:men[uú]\s+\w+\s+de\s+la\s+semana|men[uú]\s+semanal|plan\s+semanal|men[uú]\s+ejecutivo)[^$\d]{0,80}([0-9]+(?:[.,][0-9]{1,2})?)\s*\$",
            r"(?:vale|precio|cuesta|monto)\s*[:=]?\s*\$?\s*([0-9]+(?:[.,][0-9]{1,2})?)",
            r"(?:precio(?:\s+total)?|monto(?:\s+total)?|total)\s*[:=]?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:usd|d[oó]lares|\$)",
            r"([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:usd|d[oó]lares)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            raw = match.group(1).replace(",", ".")
            try:
                value = float(raw)
                if value > 0:
                    return round(value, 2)
            except Exception:
                continue
        return None

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _normalize_breakdown_items(self, raw_items: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_items, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            row = dict(item)
            selected = row.get("selected")
            name = (
                row.get("nombre")
                or row.get("name")
                or row.get("option")
                or row.get("plato")
                or row.get("day")
                or (selected.get("name") if isinstance(selected, dict) else None)
                or (selected if isinstance(selected, str) else None)
            )
            qty = row.get("cantidad")
            if qty is None:
                qty = row.get("quantity")
            if qty is None:
                qty = row.get("qty")
            price = row.get("precio_unitario")
            if price is None:
                price = row.get("unit_price")
            if price is None:
                price = row.get("price")
            if price is None:
                price = row.get("price_unit")

            if name:
                row["nombre"] = str(name).strip()
            if qty is not None:
                row["cantidad"] = self._safe_float(qty, 0.0)
            if price is not None:
                row["precio_unitario"] = self._safe_float(price, 0.0)
            if not row.get("unidad") and row.get("unit"):
                row["unidad"] = row.get("unit")

            normalized.append(row)

        return normalized

    def _enrich_breakdown_with_catalog_prices(
        self,
        breakdown: List[Dict[str, Any]],
        organization_id: Optional[str],
        user_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not breakdown:
            return []

        if not self.catalog_search or not (organization_id or user_id):
            return breakdown

        enriched: List[Dict[str, Any]] = []
        for item in breakdown:
            row = dict(item)
            name = str(
                row.get("nombre")
                or row.get("name")
                or (row.get("selected", {}).get("name") if isinstance(row.get("selected"), dict) else "")
            ).strip()
            current_price = self._safe_float(
                row.get("precio_unitario")
                or row.get("unit_price")
                or row.get("price")
                or row.get("price_unit"),
                0.0,
            )

            if name and current_price <= 0:
                try:
                    variants = self.catalog_search.search_product_variants(
                        query=name,
                        organization_id=organization_id,
                        user_id=user_id,
                        max_variants=3,
                    )
                except Exception:
                    variants = []
                if variants:
                    top = variants[0]
                    confidence = self._safe_float(top.get("confidence"), 0.0)
                    candidate_price = self._safe_float(top.get("unit_price"), 0.0)
                    if confidence >= self.catalog_confidence_min and candidate_price > 0:
                        row["precio_unitario"] = candidate_price

            enriched.append(row)

        return enriched
