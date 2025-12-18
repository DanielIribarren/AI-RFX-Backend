"""
Tool: get_request_data_tool

Propósito: Consultar datos actuales del request (productos, totales, detalles)
Wrapper de: DatabaseClient.get_rfx_products() y DatabaseClient.get_rfx_by_id()

Fase 2 - Sprint 1
"""

from langchain.tools import tool
from typing import Dict, Any
import logging

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def get_request_data_tool(data_type: str, request_id: str) -> Dict[str, Any]:
    """
    Consulta datos actuales del request.
    
    Esta tool permite al agente acceder a información actualizada del request
    almacenada en la base de datos.
    
    Args:
        data_type: Tipo de datos a consultar. Opciones:
            - "products": Lista completa de productos actuales
            - "summary": Resumen con total y cantidad de productos
            - "details": Detalles del request (fechas, ubicación, etc.)
        request_id: ID del request (rfx_id) a consultar
    
    Returns:
        Diccionario con los datos solicitados:
        
        Para "products": Retorna lista de productos con sus detalles
        
        Para "summary":
            {
                "product_count": 10,
                "total": 5000.0,
                "currency": "MXN"
            }
        
        Para "details":
            {
                "title": "Evento Corporativo",
                "event_date": "2025-12-15",
                "location": "Hotel Marriott",
                "city": "CDMX",
                "status": "draft"
            }
    
    Ejemplos de uso:
        Usuario: "¿Cuántos productos tengo?"
        Agente: get_request_data_tool("summary", request_id)
        
        Usuario: "Muéstrame todos los productos"
        Agente: get_request_data_tool("products", request_id)
        
        Usuario: "¿Cuál es la ubicación del evento?"
        Agente: get_request_data_tool("details", request_id)
    """
    
    try:
        logger.info(f"🔍 get_request_data_tool called: data_type={data_type}, request_id={request_id}")
        
        db = get_database_client()
        
        if data_type == "products":
            # Obtener lista completa de productos
            products = db.get_rfx_products(request_id)
            
            logger.info(f"✅ Retrieved {len(products)} products for request {request_id}")
            
            # Retornar JSON raw estructurado (como endpoint)
            return {
                "status": "success",
                "products": products,
                "count": len(products)
            }
        
        elif data_type == "summary":
            # Obtener resumen: total y cantidad
            products = db.get_rfx_products(request_id)
            
            # Calcular total
            total = sum(
                p.get('estimated_unit_price', 0) * p.get('quantity', 0) 
                for p in products
            )
            
            logger.info(f"✅ Summary for request {request_id}: {len(products)} products, total ${total}")
            
            # Retornar JSON raw estructurado
            return {
                "status": "success",
                "product_count": len(products),
                "total": total,
                "currency": "MXN"
            }
        
        elif data_type == "details":
            # Obtener detalles del request
            rfx = db.get_rfx_by_id(request_id)
            
            if not rfx:
                logger.warning(f"⚠️ Request {request_id} not found")
                return {
                    "status": "error",
                    "error": f"Request {request_id} not found"
                }
            
            # Retornar JSON raw estructurado
            details = {
                "status": "success",
                "title": rfx.get('title'),
                "event_date": rfx.get('project_start_date'),
                "location": rfx.get('event_location'),
                "city": rfx.get('event_city'),
                "status_value": rfx.get('status'),
                "description": rfx.get('description')
            }
            
            logger.info(f"✅ Retrieved details for request {request_id}")
            
            return details
        
        else:
            # Tipo de dato inválido
            error_msg = f"Invalid data_type: {data_type}. Valid options: 'products', 'summary', 'details'"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }
    
    except Exception as e:
        error_msg = f"Error retrieving request data: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "error": error_msg
        }
