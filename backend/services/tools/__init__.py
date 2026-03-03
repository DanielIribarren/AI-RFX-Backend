"""
LangChain Tools para Chat Agent.

Nota:
- Este módulo usa lazy imports para evitar dependencias circulares entre
  tools y servicios de resolución compartidos.
"""

from importlib import import_module


_TOOL_IMPORTS = {
    "get_request_data_tool": "backend.services.tools.get_request_data_tool",
    "add_products_tool": "backend.services.tools.add_products_tool",
    "update_product_tool": "backend.services.tools.update_product_tool",
    "delete_product_tool": "backend.services.tools.delete_product_tool",
    "modify_request_details_tool": "backend.services.tools.modify_request_details_tool",
    "parse_file_tool": "backend.services.tools.parse_file_tool",
    "search_catalog_variants_tool": "backend.services.tools.search_catalog_variants_tool",
    "resolve_unit_packaging_tool": "backend.services.tools.resolve_unit_packaging_tool",
    "calculate_line_price_tool": "backend.services.tools.calculate_line_price_tool",
    "verify_pricing_totals_tool": "backend.services.tools.verify_pricing_totals_tool",
    "resolve_complex_bundle_tool": "backend.services.tools.resolve_complex_bundle_tool",
    "get_pricing_preference_tool": "backend.services.tools.get_pricing_preference_tool",
    "get_frequent_products_tool": "backend.services.tools.get_frequent_products_tool",
    "save_pricing_preference_tool": "backend.services.tools.save_pricing_preference_tool",
    "save_product_usage_tool": "backend.services.tools.save_product_usage_tool",
    "save_price_correction_tool": "backend.services.tools.save_price_correction_tool",
    "log_learning_event_tool": "backend.services.tools.log_learning_event_tool",
}


def __getattr__(name):
    module_path = _TOOL_IMPORTS.get(name)
    if not module_path:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module = import_module(module_path)
    return getattr(module, name)

__all__ = [
    # Chat Agent Tools
    "get_request_data_tool",
    "add_products_tool",
    "update_product_tool",
    "delete_product_tool",
    "modify_request_details_tool",
    "parse_file_tool",
    "search_catalog_variants_tool",
    "resolve_unit_packaging_tool",
    "calculate_line_price_tool",
    "verify_pricing_totals_tool",
    "resolve_complex_bundle_tool",
    # AI Learning System Tools
    "get_pricing_preference_tool",
    "get_frequent_products_tool",
    "save_pricing_preference_tool",
    "save_product_usage_tool",
    "save_price_correction_tool",
    "log_learning_event_tool",
]
