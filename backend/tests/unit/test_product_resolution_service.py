from backend.services.product_resolution_service import ProductResolutionService


class _CatalogMock:
    def __init__(self, variants=None):
        self._variants = variants or []

    def search_product_variants(self, query, organization_id=None, max_variants=5):
        return self._variants


def test_chat_resolver_infers_composite_breakdown_without_catalog_bundle():
    service = ProductResolutionService(catalog_search=None, rfx_orchestrator_agent=None)

    items = service.resolve_for_chat_products(
        products=[
            {
                "nombre": "Papas integrales cheddar y pepper",
                "cantidad": 1,
                "unidad": "unidades",
                "precio_unitario": 0,
            }
        ],
        organization_id=None,
        rfx_context={},
    )

    assert len(items) == 1
    item = items[0]
    specs = item.get("specifications") or {}
    assert specs.get("is_bundle") is True
    assert specs.get("inferred_bundle") is True
    names = [b.get("selected", {}).get("name", "").lower() for b in specs.get("bundle_breakdown", [])]
    assert "cheddar" in names
    assert "pepper" in names


def test_chat_resolver_uses_catalog_complex_bundle_schema():
    variants = [
        {
            "id": "cat-1",
            "product_name": "Papas Integrales",
            "unit_cost": 6.0,
            "unit_price": 10.0,
            "unit": "unidades",
            "confidence": 0.95,
            "product_type": "complex_bundle",
            "bundle_schema": {
                "slots": [
                    {
                        "slot": "sabor_1",
                        "required": True,
                        "options": [
                            {"name": "Cheddar", "tags": ["cheddar"]},
                            {"name": "BBQ", "tags": ["bbq"]},
                        ],
                    },
                    {
                        "slot": "sabor_2",
                        "required": True,
                        "options": [
                            {"name": "Pepper", "tags": ["pepper"]},
                            {"name": "Queso", "tags": ["queso"]},
                        ],
                    },
                ]
            },
        }
    ]

    service = ProductResolutionService(catalog_search=_CatalogMock(variants), rfx_orchestrator_agent=None)

    items = service.resolve_for_chat_products(
        products=[
            {
                "nombre": "Papas integrales cheddar y pepper",
                "cantidad": 1,
                "unidad": "unidades",
            }
        ],
        organization_id="org-test",
        rfx_context={},
    )

    assert len(items) == 1
    item = items[0]
    specs = item.get("specifications") or {}
    assert specs.get("is_bundle") is True
    assert specs.get("inferred_bundle") is False
    breakdown = specs.get("bundle_breakdown") or []
    assert len(breakdown) == 2
    selected_names = [b.get("selected", {}).get("name", "").lower() for b in breakdown]
    assert "cheddar" in selected_names
    assert "pepper" in selected_names


def test_extraction_resolver_uses_fallback_when_orchestrator_missing():
    service = ProductResolutionService(catalog_search=None, rfx_orchestrator_agent=None)

    products = [{"nombre": "Tequeños", "cantidad": 10, "unidad": "unidades"}]

    called = {"fallback": False}

    def _fallback(items):
        called["fallback"] = True
        return [{**items[0], "pricing_source": "fallback_test"}]

    result = service.resolve_for_rfx_extraction(
        products=products,
        organization_id=None,
        rfx_context={},
        fallback_resolver=_fallback,
    )

    assert called["fallback"] is True
    assert result[0]["pricing_source"] == "fallback_test"


def test_chat_resolver_preserves_and_normalizes_explicit_bundle_breakdown():
    service = ProductResolutionService(catalog_search=None, rfx_orchestrator_agent=None)

    items = service.resolve_for_chat_products(
        products=[
            {
                "nombre": "Refresco Orgánico 200g",
                "cantidad": 30,
                "unidad": "unidades",
                "specifications": {
                    "is_bundle": True,
                    "inferred_bundle": True,
                    "bundle_breakdown": [
                        {"name": "Seven Up", "quantity": 15, "price_unit": 2.0},
                        {"name": "Coca Cola Zero", "quantity": 15, "price_unit": 2.5},
                    ],
                },
            }
        ],
        organization_id="org-test",
        rfx_context={},
    )

    assert len(items) == 1
    item = items[0]
    specs = item.get("specifications") or {}
    breakdown = specs.get("bundle_breakdown") or []
    assert len(breakdown) == 2
    assert all(b.get("nombre") for b in breakdown)
    assert all(b.get("cantidad") for b in breakdown)
    assert all(float(b.get("precio_unitario") or 0) > 0 for b in breakdown)
    assert float(item.get("precio_unitario") or 0) > 0
    assert bool(item.get("requires_clarification")) is False


def test_chat_resolver_ignores_low_confidence_catalog_variant_for_pricing():
    variants = [
        {
            "id": "wrong-1",
            "product_name": "Aluminio Eco 600ml",
            "unit_cost": 50.0,
            "unit_price": 80.0,
            "unit": "unidades",
            "confidence": 0.50,
            "product_type": "simple",
        }
    ]
    service = ProductResolutionService(catalog_search=_CatalogMock(variants), rfx_orchestrator_agent=None)

    items = service.resolve_for_chat_products(
        products=[
            {
                "nombre": "Mini empanadas",
                "cantidad": 10,
                "unidad": "unidades",
                "precio_unitario": 0,
            }
        ],
        organization_id="org-test",
        rfx_context={},
    )

    assert len(items) == 1
    item = items[0]
    assert item.get("pricing_source") == "chat_resolver_low_conf_catalog_ignored"
    assert float(item.get("precio_unitario") or 0) == 0.0
    assert bool(item.get("requires_clarification")) is True
