"""
Tool: update_product_tool

Propósito: Actualizar producto existente del request
Wrapper de: DatabaseClient.update_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import Dict, Any
import logging
import requests
import os

logger = logging.getLogger(__name__)


@tool
def update_product_tool(request_id: str, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza un producto existente del request.
    
    Esta tool permite al agente modificar campos de un producto específico.
    
    Args:
        request_id: ID del request (rfx_id)
        product_id: ID del producto a actualizar
        updates: Diccionario con campos a actualizar:
            - name (str, opcional): Nuevo nombre
            - quantity (int, opcional): Nueva cantidad
            - price_unit (float, opcional): Nuevo precio unitario
            - category (str, opcional): Nueva categoría
            - unit (str, opcional): Nueva unidad de medida
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "product_id": str,
            "updated_fields": List[str],
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Cambia la cantidad de sillas a 20"
        Agente: Primero obtiene el product_id y luego llama a esta tool
        
        Usuario: "Actualiza el precio de las mesas a $350"
        Agente: Primero obtiene el product_id y luego llama a esta tool
    """
    
    try:
        logger.info(f"🔧 update_product_tool called: request_id={request_id}, product_id={product_id}, updates={updates}")
        
        if not updates or len(updates) == 0:
            logger.warning("⚠️ No updates provided")
            return {
                "status": "error",
                "product_id": product_id,
                "updated_fields": [],
                "message": "No se proporcionaron campos para actualizar"
            }
        
        # Base URL del backend (mismo servidor)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        
        # Llamar al endpoint PUT /api/rfx/<rfx_id>/products/<product_id>
        url = f"{base_url}/api/rfx/{request_id}/products/{product_id}"
        
        response = requests.put(url, json=updates)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Product {product_id} updated successfully")
            return data  # Retornar JSON raw del endpoint
        else:
            logger.error(f"❌ Error calling endpoint: {response.status_code}")
            return {
                "status": "error",
                "message": f"Failed to update product: {response.text}"
            }
    
    except Exception as e:
        error_msg = f"Error updating product: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
