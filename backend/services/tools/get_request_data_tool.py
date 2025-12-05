"""
Tool: get_request_data_tool

Propósito: Consultar datos actuales del request (productos, totales, detalles)
Wrapper de: DatabaseClient.get_rfx_products() y DatabaseClient.get_rfx_by_id()

Fase 2 - Sprint 1
"""

from langchain.tools import tool
from typing import Dict, Any
import logging
import requests
import os

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
        
        # Base URL del backend (mismo servidor)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        
        if data_type == "products":
            # Llamar al endpoint GET /api/rfx/<rfx_id>/products
            url = f"{base_url}/api/rfx/{request_id}/products"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved products for request {request_id}")
                return data  # Retornar JSON raw del endpoint
            else:
                logger.error(f"❌ Error calling endpoint: {response.status_code}")
                return {"error": f"Failed to get products: {response.text}"}
        
        elif data_type == "summary":
            # Llamar al endpoint GET /api/rfx/<rfx_id>/products para obtener productos
            url = f"{base_url}/api/rfx/{request_id}/products"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                # Calcular resumen
                total = sum(
                    p.get('precio', 0) * p.get('cantidad', 0) 
                    for p in products
                )
                
                summary = {
                    "product_count": len(products),
                    "total": total,
                    "currency": data.get('currency', 'MXN')
                }
                
                logger.info(f"✅ Summary for request {request_id}: {len(products)} products, total ${total}")
                return summary
            else:
                logger.error(f"❌ Error calling endpoint: {response.status_code}")
                return {"error": f"Failed to get summary: {response.text}"}
        
        elif data_type == "details":
            # Llamar al endpoint GET /api/rfx/<rfx_id>
            url = f"{base_url}/api/rfx/{request_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved details for request {request_id}")
                return data  # Retornar JSON raw del endpoint
            else:
                logger.error(f"❌ Error calling endpoint: {response.status_code}")
                return {"error": f"Failed to get details: {response.text}"}
        
        else:
            # Tipo de dato inválido
            error_msg = f"Invalid data_type: {data_type}. Valid options: 'products', 'summary', 'details'"
            logger.error(f"❌ {error_msg}")
            return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Error retrieving request data: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"error": error_msg}
