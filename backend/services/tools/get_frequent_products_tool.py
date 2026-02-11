"""
🔍 Get Frequent Products Tool
Consulta productos que el usuario usa frecuentemente
"""
import logging
from typing import Dict, Any, List
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def get_frequent_products_tool(
    user_id: str,
    organization_id: str,
    rfx_type: str = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Obtiene productos que el usuario usa frecuentemente.
    
    Returns:
        Lista de productos frecuentes con confidence scores
    """
    try:
        db = get_database_client()
        
        # Construir query
        query = db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).eq("organization_id", organization_id).eq(
            "preference_type", "product"
        )
        
        # Filtrar por rfx_type si se proporciona
        if rfx_type:
            query = query.ilike("preference_key", f"%{rfx_type}%")
        
        response = query.order("usage_count", desc=True).limit(limit).execute()
        
        if not response.data:
            logger.info(f"⚠️ No frequent products found for user {user_id}")
            return []
        
        products = []
        for pref in response.data:
            value = pref.get("preference_value", {})
            usage_count = pref.get("usage_count", 0)
            
            # Calcular confidence
            base_confidence = min(usage_count / 10.0, 1.0)
            
            products.append({
                "product_name": pref.get("preference_key"),
                "frequency": usage_count,
                "avg_quantity": value.get("avg_quantity", 0),
                "last_price": value.get("unit_price", 0),
                "last_cost": value.get("unit_cost", 0),
                "confidence": base_confidence
            })
        
        logger.info(f"✅ Retrieved {len(products)} frequent products")
        return products
        
    except Exception as e:
        logger.error(f"❌ Error getting frequent products: {e}")
        return []
