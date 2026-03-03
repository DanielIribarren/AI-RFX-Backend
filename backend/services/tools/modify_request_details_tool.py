"""
Tool: modify_request_details_tool

Propósito: Actualizar detalles del request (fechas, ubicación, cliente, etc.)
Wrapper de: DatabaseClient.update_rfx()

Fase 2 - Sprint 3
"""

from langchain.tools import tool
from typing import Dict, Any
import logging

from backend.core.database import get_database_client
from backend.services.rfx_processing_session_service import RFXProcessingSessionService

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
        
        if not updates or len(updates) == 0:
            logger.warning("⚠️ No updates provided")
            return {
                "status": "error",
                "request_id": request_id,
                "updated_fields": [],
                "message": "No se proporcionaron campos para actualizar"
            }
        
        db = get_database_client()
        session_service = RFXProcessingSessionService()
        session = session_service.get_session(request_id)
        
        # Verificar que el request existe
        if session:
            preview_data = session.get("preview_data") or {}
            validated_data = session.get("validated_data") or {}
        else:
            rfx = db.get_rfx_by_id(request_id)
            if not rfx:
                logger.warning(f"⚠️ Request {request_id} not found")
                return {
                    "status": "error",
                    "request_id": request_id,
                    "updated_fields": [],
                    "message": f"Request con ID {request_id} no encontrado"
                }
        
        # Mapear nombres de campos (tool → BD)
        field_mapping = {
            "title": "title",
            "event_date": "project_start_date",
            "location": "location",  # Campo correcto en BD
            "delivery_location": "location",
            "city": "city",
            "client_name": "client_name",
            "requester_name": "client_name",
            "company_name": "company_name",
            "delivery_date": "delivery_date",
            "notes": "notes",
            "status": "status",
            "description": "description",
            "requirements": "requirements",
            "estimated_budget": "estimated_budget",
            "priority": "priority",
            "client_email": "email",
            "requester_email": "email",
        }
        
        # Preparar datos para actualización
        update_data = {}
        for key, value in updates.items():
            db_field = field_mapping.get(key, key)
            update_data[db_field] = value
        
        if session:
            preview_mapping = {
                "title": "title",
                "delivery_date": "delivery_date",
                "event_date": "delivery_date",
                "location": "location",
                "delivery_location": "location",
                "client_name": "requester_name",
                "requester_name": "requester_name",
                "company_name": "company_name",
                "client_email": "email",
                "requester_email": "email",
                "description": "requirements",
                "requirements": "requirements",
            }
            for key, value in updates.items():
                target_key = preview_mapping.get(key, key)
                preview_data[target_key] = value

            validated_mapping = {
                "delivery_date": "fecha",
                "event_date": "fecha",
                "location": "lugar",
                "delivery_location": "lugar",
                "client_name": "nombre_solicitante",
                "requester_name": "nombre_solicitante",
                "company_name": "nombre_empresa",
                "client_email": "email",
                "requester_email": "email",
                "requirements": "requirements",
                "description": "requirements",
            }
            for key, value in updates.items():
                validated_key = validated_mapping.get(key)
                if validated_key:
                    validated_data[validated_key] = value

            session_service.update_session(
                request_id,
                {
                    "preview_data": preview_data,
                    "validated_data": validated_data,
                }
            )
            updated_fields = list(updates.keys())
            return {
                "status": "success",
                "request_id": request_id,
                "updated_fields": updated_fields,
                "message": f"Detalles de sesión actualizados ({', '.join(updated_fields)})",
                "source": "processing_session",
            }

        # Actualizar en BD
        try:
            db.update_rfx_data(request_id, update_data)
            
            updated_fields = list(updates.keys())
            logger.info(f"✅ Request {request_id} details updated successfully: {updated_fields}")
            
            return {
                "status": "success",
                "request_id": request_id,
                "updated_fields": updated_fields,
                "message": f"Detalles del request actualizados exitosamente ({', '.join(updated_fields)})"
            }
        
        except Exception as e:
            logger.error(f"❌ Error updating request {request_id}: {e}")
            return {
                "status": "error",
                "request_id": request_id,
                "updated_fields": [],
                "message": f"Error al actualizar request: {str(e)}"
            }
    
    except Exception as e:
        error_msg = f"Error updating request details: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
