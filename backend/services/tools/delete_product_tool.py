"""
Tool: delete_product_tool

Propósito: Eliminar producto del request
Wrapper de: DatabaseClient.delete_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import Dict, Any
import logging
import requests
import os

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
        
        # Base URL del backend (mismo servidor)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        
        # Llamar al endpoint DELETE /api/rfx/<rfx_id>/products/<product_id>
        url = f"{base_url}/api/rfx/{request_id}/products/{product_id}"
        
        response = requests.delete(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Product {product_id} deleted successfully")
            return data  # Retornar JSON raw del endpoint
        else:
            logger.error(f"❌ Error calling endpoint: {response.status_code}")
            return {
                "status": "error",
                "message": f"Failed to delete product: {response.text}"
            }
    
    except Exception as e:
        error_msg = f"Error deleting product: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
