"""
🔍 Get Pricing Preference Tool
Consulta preferencias de pricing aprendidas del usuario
"""
import logging
from typing import Dict, Any
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def get_pricing_preference_tool(
    user_id: str,
    organization_id: str,
    rfx_type: str = None
) -> Dict[str, Any]:
    """
    Obtiene la configuración de pricing preferida por el usuario.
    
    Returns:
        Dict con configuración de pricing y confidence score
    """
    try:
        db = get_database_client()
        
        # Construir filtros
        query = db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).eq("organization_id", organization_id).eq(
            "preference_type", "pricing"
        )
        
        # Filtrar por rfx_type si se proporciona
        if rfx_type:
            query = query.eq("preference_key", f"pricing_{rfx_type}")
        else:
            query = query.eq("preference_key", "pricing_default")
        
        response = query.order("last_used_at", desc=True).limit(1).execute()
        
        if not response.data:
            logger.info(f"⚠️ No pricing preference found for user {user_id}, returning defaults")
            return {
                "coordination_enabled": True,
                "coordination_rate": 0.18,
                "taxes_enabled": True,
                "tax_rate": 0.16,
                "cost_per_person_enabled": False,
                "confidence": 0.0,
                "usage_count": 0,
                "last_used": None,
                "source": "default"
            }
        
        pref = response.data[0]
        value = pref.get("preference_value", {})
        
        # Calcular confidence basado en usage_count
        usage_count = pref.get("usage_count", 0)
        base_confidence = min(usage_count / 10.0, 1.0)  # Max 1.0 con 10+ usos
        
        result = {
            "coordination_enabled": value.get("coordination_enabled", True),
            "coordination_rate": value.get("coordination_rate", 0.18),
            "taxes_enabled": value.get("taxes_enabled", True),
            "tax_rate": value.get("tax_rate", 0.16),
            "cost_per_person_enabled": value.get("cost_per_person_enabled", False),
            "confidence": base_confidence,
            "usage_count": usage_count,
            "last_used": pref.get("last_used_at"),
            "source": "learned"
        }
        
        logger.info(f"✅ Pricing preference retrieved: confidence={base_confidence:.2f}, usage={usage_count}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing preference: {e}")
        return {
            "coordination_enabled": True,
            "coordination_rate": 0.18,
            "taxes_enabled": True,
            "tax_rate": 0.16,
            "cost_per_person_enabled": False,
            "confidence": 0.0,
            "usage_count": 0,
            "last_used": None,
            "source": "default",
            "error": str(e)
        }
