"""
Tool: add_products_tool

Propósito: Insertar productos al request
Wrapper de: DatabaseClient.create_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import List, Dict, Any
import logging
import requests
import os

logger = logging.getLogger(__name__)


@tool
def add_products_tool(request_id: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agrega productos al request.
    
    Esta tool permite al agente insertar uno o múltiples productos
    en el request actual.
    
    Args:
        request_id: ID del request (rfx_id) donde agregar productos
        products: Lista de productos a agregar. Cada producto debe tener:
            - name (str): Nombre del producto
            - quantity (int): Cantidad
            - price_unit (float): Precio unitario
            - category (str, opcional): Categoría del producto
            - unit (str, opcional): Unidad de medida (default: "unidades")
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "products_added": int,
            "product_ids": List[str],
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Agrega 10 sillas a $150 cada una"
        Agente: Llama a esta tool con una lista de productos
        
        Usuario: "Inserta los productos del archivo que te pasé"
        Agente: Extrae productos del archivo y llama a esta tool
    """
    
    try:
        logger.info(f"🔧 add_products_tool called: request_id={request_id}, products_count={len(products)}")
        
        # Base URL del backend (mismo servidor)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        url = f"{base_url}/api/rfx/{request_id}/products"
        
        # El endpoint POST /api/rfx/<rfx_id>/products acepta UN producto a la vez
        # Necesitamos hacer un loop para agregar múltiples productos
        added_products = []
        errors = []
        
        for product in products:
            # Mapear campos al formato que espera el endpoint
            payload = {
                "nombre": product.get("name"),
                "cantidad": product.get("quantity", 1),
                "unidad": product.get("unit", "unidades"),
                "precio_unitario": product.get("price_unit", 0),
                "categoria": product.get("category"),
                "descripcion": product.get("description"),
                "notas": product.get("notes")
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                added_products.append(data.get("data", {}).get("product", {}))
                logger.info(f"✅ Product added: {product.get('name')}")
            else:
                error_msg = f"Failed to add {product.get('name')}: {response.text}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        # Retornar resultado consolidado
        if len(added_products) > 0:
            return {
                "status": "success",
                "message": f"Se agregaron {len(added_products)} producto(s) exitosamente",
                "products": added_products,
                "errors": errors if errors else None
            }
        else:
            return {
                "status": "error",
                "message": "No se pudo agregar ningún producto",
                "errors": errors
            }
    
    except Exception as e:
        error_msg = f"Error adding products: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
