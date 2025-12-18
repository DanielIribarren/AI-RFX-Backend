"""
LangChain Tools para Chat Agent - Fase 2

Tools disponibles:
- get_request_data_tool: Consultar datos actuales del request ✅
- add_products_tool: Insertar productos ✅
- update_product_tool: Actualizar productos ✅
- delete_product_tool: Eliminar productos ✅
- modify_request_details_tool: Modificar detalles del request ✅
- parse_file_tool: Ayudar a extraer productos de archivos ✅
"""

from backend.services.tools.get_request_data_tool import get_request_data_tool
from backend.services.tools.add_products_tool import add_products_tool
from backend.services.tools.update_product_tool import update_product_tool
from backend.services.tools.delete_product_tool import delete_product_tool
from backend.services.tools.modify_request_details_tool import modify_request_details_tool
from backend.services.tools.parse_file_tool import parse_file_tool

__all__ = [
    "get_request_data_tool",
    "add_products_tool",
    "update_product_tool",
    "delete_product_tool",
    "modify_request_details_tool",
    "parse_file_tool",
]
