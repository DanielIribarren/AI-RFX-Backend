"""
Tool: update_product_tool

Propósito: Actualizar producto existente del request
Wrapper de: DatabaseClient.update_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import Dict, Any
import logging

from backend.core.database import get_database_client

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
        
        db = get_database_client()
        
        # Mapear nombres de campos (tool → BD)
        field_mapping = {
            "name": "product_name",
            "quantity": "quantity",
            "price_unit": "estimated_unit_price",
            "unit": "unit",
            "description": "description",
            "notes": "notes"
        }
        
        # Convertir updates al formato de BD
        db_updates = {}
        for key, value in updates.items():
            db_key = field_mapping.get(key, key)
            db_updates[db_key] = value
        
        # Actualizar en BD
        try:
            # CORRECTO: product_id primero, rfx_id segundo
            success = db.update_rfx_product(product_id, request_id, db_updates)
            
            if success:
                logger.info(f"✅ Product {product_id} updated successfully")
                return {
                    "status": "success",
                    "product_id": product_id,
                    "updated_fields": list(updates.keys()),
                    "message": f"Producto actualizado: {', '.join(updates.keys())}"
                }
            else:
                logger.error(f"❌ Failed to update product {product_id}")
                return {
                    "status": "error",
                    "product_id": product_id,
                    "updated_fields": [],
                    "message": "No se pudo actualizar el producto"
                }
        except Exception as e:
            logger.error(f"❌ Error updating product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "updated_fields": [],
                "message": f"Error al actualizar: {str(e)}"
            }
    
    except Exception as e:
        error_msg = f"Error updating product: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
