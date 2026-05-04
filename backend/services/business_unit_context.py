"""
Business unit industry context profiles.

Small, static resolver used by legacy services to remove catering-first
assumptions without adding more service-layer complexity.
"""

from __future__ import annotations

from typing import Dict


INDUSTRY_PROFILES: Dict[str, Dict[str, str]] = {
    "corporate_catering": {
        "extraction_context": "corporate catering and food service requests",
        "default_product_label": "Catering Service",
        "default_unit": "service",
    },
    "food_safety_testing": {
        "extraction_context": "food safety inspection and laboratory analysis services",
        "default_product_label": "Analysis Service",
        "default_unit": "service",
    },
    "industrial_food_management": {
        "extraction_context": "industrial food management and facility services",
        "default_product_label": "Management Service",
        "default_unit": "service",
    },
    "services": {
        "extraction_context": "professional services requests",
        "default_product_label": "Service",
        "default_unit": "service",
    },
}


def get_industry_profile(industry_context: str | None) -> Dict[str, str]:
    normalized = str(industry_context or "services").strip().lower()
    return INDUSTRY_PROFILES.get(normalized, INDUSTRY_PROFILES["services"])
