import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.services.business_unit_context import get_industry_profile


def test_get_industry_profile_returns_expected_profile_for_known_context():
    profile = get_industry_profile("food_safety_testing")

    assert profile["extraction_context"] == "food safety inspection and laboratory analysis services"
    assert profile["default_product_label"] == "Analysis Service"
    assert profile["default_unit"] == "service"


def test_get_industry_profile_falls_back_to_services():
    profile = get_industry_profile("unknown-context")

    assert profile["extraction_context"] == "professional services requests"
    assert profile["default_product_label"] == "Service"
    assert profile["default_unit"] == "service"
