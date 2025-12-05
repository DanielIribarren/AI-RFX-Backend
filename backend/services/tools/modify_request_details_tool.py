"""
Tool: modify_request_details_tool

Propósito: Actualizar detalles del request (fechas, ubicación, cliente, etc.)
Wrapper de: DatabaseClient.update_rfx()

Fase 2 - Sprint 3
"""

from langchain.tools import tool
from typing import Dict, Any
import logging
import requests
import os

logger = logging.getLogger(__name__)


@tool
def modify_request_details_tool(request_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza detalles generales del request (fechas, ubicación, cliente, etc.).
    
    Esta tool permite al agente modificar información del request que NO son productos.
    
    Args:
        request_id: ID del request (rfx_id) a actualizar
        updates: Diccionario con campos a actualizar:
            - title (str, opcional): Título del request
            - event_date (str, opcional): Fecha del evento (ISO format)
            - location (str, opcional): Ubicación del evento
            - city (str, opcional): Ciudad del evento
            - client_name (str, opcional): Nombre del cliente
            - delivery_date (str, opcional): Fecha de entrega
            - notes (str, opcional): Notas adicionales
            - status (str, opcional): Estado del request
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "request_id": str,
            "updated_fields": List[str],
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Cambia la fecha del evento al 15 de diciembre"
        Agente: modify_request_details_tool(request_id, {
            "event_date": "2025-12-15"
        })
        
        Usuario: "El evento será en el Hotel Marriott de CDMX"
        Agente: modify_request_details_tool(request_id, {
            "location": "Hotel Marriott",
            "city": "Ciudad de México"
        })
        
        Usuario: "El cliente se llama Corporativo XYZ"
        Agente: modify_request_details_tool(request_id, {
            "client_name": "Corporativo XYZ"
        })
    """
    
    try:
        logger.info(f"🔧 modify_request_details_tool called: request_id={request_id}, updates={updates}")
        
        # Base URL del backend (mismo servidor)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        
        # Llamar al endpoint PUT /api/rfx/<rfx_id>/data
        url = f"{base_url}/api/rfx/{request_id}/data"
        
        response = requests.put(url, json=updates)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Request {request_id} details updated successfully")
            return data  # Retornar JSON raw del endpoint
        else:
            logger.error(f"❌ Error calling endpoint: {response.status_code}")
            return {
                "status": "error",
                "message": f"Failed to update request details: {response.text}"
            }
    
    except Exception as e:
        error_msg = f"Error updating request details: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
