"""
✍️ Save Price Correction Tool
Registra correcciones de precio significativas
"""
import logging
from typing import Dict, Any
from datetime import datetime
from langchain.tools import tool
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@tool
def save_price_correction_tool(
    user_id: str,
    organization_id: str,
    product_name: str,
    original_price: float,
    corrected_price: float,
    rfx_id: str
) -> Dict[str, Any]:
    """
    Registra una corrección de precio significativa (>5% cambio).
    
    Returns:
        Dict con resultado del guardado
    """
    try:
        # Validar que el cambio sea significativo
        diff = abs(corrected_price - original_price)
        percentage = diff / original_price
        
        if percentage < 0.05:  # 5% threshold
            logger.warning(f"⚠️ Price change below threshold: {percentage*100:.1f}%")
            return {
                "success": False,
                "reason": f"Price change below 5% threshold (current: {percentage*100:.1f}%)"
            }
        
        db = get_database_client()
        
        # Guardar en price_corrections
        response = db.table("price_corrections").insert({
            "user_id": user_id,
            "organization_id": organization_id,
            "product_name": product_name,
            "original_price": original_price,
            "corrected_price": corrected_price,
            "price_difference": diff,
            "percentage_change": percentage,
            "rfx_id": rfx_id,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        direction = "increase" if corrected_price > original_price else "decrease"
        
        logger.info(f"✅ Price correction saved: {product_name}, {percentage*100:.1f}% {direction}")
        
        return {
            "success": True,
            "correction_id": response.data[0]["id"],
            "price_difference": diff,
            "percentage_change": percentage * 100,
            "direction": direction
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving price correction: {e}")
        return {
            "success": False,
            "error": str(e)
        }
