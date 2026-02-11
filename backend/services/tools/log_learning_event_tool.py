"""
✍️ Log Learning Event Tool
Registra eventos de aprendizaje en el historial
"""
import logging
from typing import Dict, Any
from datetime import datetime
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def log_learning_event_tool(
    user_id: str,
    organization_id: str,
    event_type: str,
    rfx_id: str,
    context: Dict[str, Any],
    action_taken: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Registra un evento de aprendizaje en el historial.
    
    Returns:
        Dict con resultado del guardado
    """
    try:
        db = get_database_client()
        
        # Guardar en learning_events
        response = db.table("learning_events").insert({
            "user_id": user_id,
            "organization_id": organization_id,
            "event_type": event_type,
            "rfx_id": rfx_id,
            "event_context": context,
            "action_taken": action_taken,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        logger.info(f"✅ Learning event logged: {event_type} for RFX {rfx_id}")
        
        return {
            "success": True,
            "event_id": response.data[0]["id"],
            "timestamp": response.data[0]["created_at"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error logging learning event: {e}")
        return {
            "success": False,
            "error": str(e)
        }
