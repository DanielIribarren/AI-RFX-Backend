"""
Tool: add_products_tool

Propósito: Insertar productos al request
Wrapper de: DatabaseClient.create_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import List, Dict, Any
import logging

from backend.core.database import get_database_client

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
        
        if not products or len(products) == 0:
            logger.warning("⚠️ No products provided")
            return {
                "status": "error",
                "message": "No se proporcionaron productos para agregar",
                "products_added": 0,
                "product_ids": []
            }
        
        db = get_database_client()
        added_ids = []
        added_products = []
        
        # Insertar cada producto
        for i, product in enumerate(products, 1):
            # Validar campos requeridos
            if not product.get('name'):
                logger.warning(f"⚠️ Product {i} missing 'name' field, skipping")
                continue
            
            if product.get('quantity') is None or product.get('quantity') <= 0:
                logger.warning(f"⚠️ Product {i} has invalid quantity, skipping")
                continue
            
            # Preparar datos del producto
            product_data = {
                "product_name": product.get('name'),
                "quantity": product.get('quantity'),
                "estimated_unit_price": product.get('price_unit', 0),
                "unit": product.get('unit', 'unidades'),
                "description": product.get('description'),
                "notes": product.get('notes')
            }
            
            # Insertar en BD
            try:
                inserted = db.insert_rfx_products(request_id, [product_data])
                if inserted and len(inserted) > 0:
                    product_id = inserted[0].get('id')
                    added_ids.append(product_id)
                    added_products.append(inserted[0])
                    logger.info(f"✅ Product added: {product.get('name')} (ID: {product_id})")
            except Exception as e:
                logger.error(f"❌ Error adding product {product.get('name')}: {e}")
                continue
        
        # Retornar JSON raw estructurado
        if len(added_ids) > 0:
            logger.info(f"✅ Successfully added {len(added_ids)} products to request {request_id}")
            return {
                "status": "success",
                "message": f"Se agregaron {len(added_ids)} producto(s) exitosamente",
                "products_added": len(added_ids),
                "product_ids": added_ids,
                "products": added_products
            }
        else:
            logger.warning(f"⚠️ No products were added to request {request_id}")
            return {
                "status": "error",
                "message": "No se pudo agregar ningún producto (verifica los datos)",
                "products_added": 0,
                "product_ids": []
            }
    
    except Exception as e:
        error_msg = f"Error adding products: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
