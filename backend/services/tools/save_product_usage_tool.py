"""
✍️ Save Product Usage Tool
Registra uso de productos para aprendizaje
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def save_product_usage_tool(
    user_id: str,
    organization_id: str,
    product_name: str,
    quantity: int,
    unit_price: float,
    unit_cost: float,
    rfx_type: str = None
) -> Dict[str, Any]:
    """
    Registra el uso de un producto para aprendizaje.
    
    Returns:
        Dict con resultado del guardado
    """
    try:
        db = get_database_client()
        
        # Verificar si ya existe
        existing = db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).eq("organization_id", organization_id).eq(
            "preference_type", "product"
        ).eq("preference_key", product_name).execute()
        
        if existing.data:
            # Actualizar existente (calcular promedio)
            current = existing.data[0]
            current_value = current.get("preference_value", {})
            current_usage = current.get("usage_count", 0)
            
            # Calcular nuevos promedios
            new_usage_count = current_usage + 1
            current_avg_qty = current_value.get("avg_quantity", 0)
            new_avg_quantity = ((current_avg_qty * current_usage) + quantity) / new_usage_count
            
            new_value = {
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "avg_quantity": new_avg_quantity,
                "last_quantity": quantity,
                "rfx_type": rfx_type
            }
            
            response = db.table("user_preferences").update({
                "preference_value": new_value,
                "usage_count": new_usage_count,
                "last_used_at": datetime.utcnow().isoformat()
            }).eq("id", current["id"]).execute()
            
            logger.info(f"✅ Updated product usage: {product_name}, usage={new_usage_count}")
            
            return {
                "success": True,
                "frequency": new_usage_count,
                "avg_quantity": new_avg_quantity
            }
        else:
            # Crear nuevo
            response = db.table("user_preferences").insert({
                "user_id": user_id,
                "organization_id": organization_id,
                "preference_type": "product",
                "preference_key": product_name,
                "preference_value": {
                    "unit_price": unit_price,
                    "unit_cost": unit_cost,
                    "avg_quantity": quantity,
                    "last_quantity": quantity,
                    "rfx_type": rfx_type
                },
                "usage_count": 1,
                "last_used_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"✅ Created product usage: {product_name}")
            
            return {
                "success": True,
                "frequency": 1,
                "avg_quantity": quantity
            }
        
    except Exception as e:
        logger.error(f"❌ Error saving product usage: {e}")
        return {
            "success": False,
            "error": str(e)
        }
