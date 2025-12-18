"""
Tool: delete_product_tool

Propósito: Eliminar producto del request
Wrapper de: DatabaseClient.delete_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import Dict, Any
import logging

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def delete_product_tool(request_id: str, product_id: str) -> Dict[str, Any]:
    """
    Elimina un producto del request.
    
    Esta tool permite al agente eliminar un producto específico del request.
    
    Args:
        request_id: ID del request (rfx_id)
        product_id: ID del producto a eliminar
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "product_id": str,
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Elimina las sillas"
        Agente:
          1. get_request_data_tool("products", request_id)
          2. Encuentra producto "Sillas" con id=123
          3. delete_product_tool(request_id, "123")
        
        Usuario: "Quita las mesas del presupuesto"
        Agente:
          1. Busca producto "Mesas"
          2. delete_product_tool(request_id, product_id)
    """
    
    try:
        logger.info(f"🔧 delete_product_tool called: request_id={request_id}, product_id={product_id}")
        
        db = get_database_client()
        
        # Verificar que el producto existe
        products = db.get_rfx_products(request_id)
        product = next((p for p in products if p.get('id') == product_id), None)
        
        if not product:
            logger.warning(f"⚠️ Product {product_id} not found in request {request_id}")
            return {
                "status": "error",
                "product_id": product_id,
                "message": f"Producto con ID {product_id} no encontrado"
            }
        
        product_name = product.get('product_name', 'Unknown')
        
        # Eliminar de BD
        try:
            db.delete_rfx_product(request_id, product_id)
            
            logger.info(f"✅ Product {product_id} ({product_name}) deleted successfully")
            
            return {
                "status": "success",
                "product_id": product_id,
                "message": f"Producto '{product_name}' eliminado exitosamente"
            }
        
        except Exception as e:
            logger.error(f"❌ Error deleting product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "message": f"Error al eliminar producto: {str(e)}"
            }
    
    except Exception as e:
        error_msg = f"Error deleting product: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
