"""
✍️ Save Pricing Preference Tool
Guarda preferencias de pricing aprendidas
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def save_pricing_preference_tool(
    user_id: str,
    organization_id: str,
    coordination_enabled: bool,
    coordination_rate: float = None,
    taxes_enabled: bool = True,
    tax_rate: float = None,
    cost_per_person_enabled: bool = False,
    rfx_type: str = None
) -> Dict[str, Any]:
    """
    Guarda configuración de pricing como preferencia aprendida.
    
    Returns:
        Dict con resultado del guardado
    """
    try:
        db = get_database_client()
        
        # Construir preference_key
        preference_key = f"pricing_{rfx_type}" if rfx_type else "pricing_default"
        
        # Construir preference_value
        preference_value = {
            "coordination_enabled": coordination_enabled,
            "coordination_rate": coordination_rate or 0.18,
            "taxes_enabled": taxes_enabled,
            "tax_rate": tax_rate or 0.16,
            "cost_per_person_enabled": cost_per_person_enabled
        }
        
        # Verificar si ya existe
        existing = db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).eq("organization_id", organization_id).eq(
            "preference_type", "pricing"
        ).eq("preference_key", preference_key).execute()
        
        if existing.data:
            # Actualizar existente (incrementar usage_count)
            current = existing.data[0]
            new_usage_count = current.get("usage_count", 0) + 1
            
            response = db.table("user_preferences").update({
                "preference_value": preference_value,
                "usage_count": new_usage_count,
                "last_used_at": datetime.utcnow().isoformat()
            }).eq("id", current["id"]).execute()
            
            logger.info(f"✅ Updated pricing preference: usage_count={new_usage_count}")
            
            return {
                "success": True,
                "preference_id": current["id"],
                "usage_count": new_usage_count,
                "action": "updated"
            }
        else:
            # Crear nuevo
            response = db.table("user_preferences").insert({
                "user_id": user_id,
                "organization_id": organization_id,
                "preference_type": "pricing",
                "preference_key": preference_key,
                "preference_value": preference_value,
                "usage_count": 1,
                "last_used_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"✅ Created new pricing preference")
            
            return {
                "success": True,
                "preference_id": response.data[0]["id"],
                "usage_count": 1,
                "action": "created"
            }
        
    except Exception as e:
        logger.error(f"❌ Error saving pricing preference: {e}")
        return {
            "success": False,
            "error": str(e)
        }
