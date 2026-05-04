import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.services.catalog_search_service_sync import CatalogSearchServiceSync


def test_sort_scope_priority_moves_active_business_unit_products_first():
    service = CatalogSearchServiceSync(db_client=None, redis_client=None, openai_client=None)
    products = [
        {"id": "shared", "business_unit_id": None},
        {"id": "unit-specific", "business_unit_id": "bu-1"},
    ]

    ordered = service._sort_scope_priority(products, "bu-1")

    assert ordered[0]["id"] == "unit-specific"
    assert ordered[1]["id"] == "shared"
