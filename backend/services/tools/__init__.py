"""
LangChain Tools para Chat Agent - Fase 2

Tools disponibles:
- get_request_data_tool: Consultar datos actuales del request ✅
- add_products_tool: Insertar productos ✅
- update_product_tool: Actualizar productos ✅
- delete_product_tool: Eliminar productos ✅
- modify_request_details_tool: Modificar detalles del request ✅
- parse_file_tool: Ayudar a extraer productos de archivos ✅

AI Learning System Tools:
- get_pricing_preference_tool: Consultar preferencias de pricing ✅
- get_frequent_products_tool: Consultar productos frecuentes ✅
- save_pricing_preference_tool: Guardar preferencias de pricing ✅
- save_product_usage_tool: Registrar uso de productos ✅
- save_price_correction_tool: Registrar correcciones de precio ✅
- log_learning_event_tool: Registrar eventos de aprendizaje ✅
"""

from backend.services.tools.get_request_data_tool import get_request_data_tool
from backend.services.tools.add_products_tool import add_products_tool
from backend.services.tools.update_product_tool import update_product_tool
from backend.services.tools.delete_product_tool import delete_product_tool
from backend.services.tools.modify_request_details_tool import modify_request_details_tool
from backend.services.tools.parse_file_tool import parse_file_tool

# AI Learning System Tools
from backend.services.tools.get_pricing_preference_tool import get_pricing_preference_tool
from backend.services.tools.get_frequent_products_tool import get_frequent_products_tool
from backend.services.tools.save_pricing_preference_tool import save_pricing_preference_tool
from backend.services.tools.save_product_usage_tool import save_product_usage_tool
from backend.services.tools.save_price_correction_tool import save_price_correction_tool
from backend.services.tools.log_learning_event_tool import log_learning_event_tool

__all__ = [
    # Chat Agent Tools
    "get_request_data_tool",
    "add_products_tool",
    "update_product_tool",
    "delete_product_tool",
    "modify_request_details_tool",
    "parse_file_tool",
    # AI Learning System Tools
    "get_pricing_preference_tool",
    "get_frequent_products_tool",
    "save_pricing_preference_tool",
    "save_product_usage_tool",
    "save_price_correction_tool",
    "log_learning_event_tool",
]
