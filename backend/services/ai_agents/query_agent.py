"""
Query Agent - Consulta información aprendida
Approach simple: consultas directas a BD
"""
import logging
from typing import Dict, Any, List
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class QueryAgent:
    """Agente que consulta preferencias aprendidas"""
    
    def __init__(self):
        self.db = get_database_client()
        logger.info("✅ Query Agent initialized")
    
    def get_learned_preferences(
        self,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Obtiene preferencias aprendidas del usuario.
        
        Args:
            user_id: UUID del usuario
            organization_id: UUID de la organización
            
        Returns:
            Dict con preferencias de pricing y productos frecuentes
        """
        try:
            logger.info(f"🔍 Querying preferences for user: {user_id}")
            
            # 1. Obtener preferencias de pricing
            pricing_prefs = self._get_pricing_preferences(user_id, organization_id)
            
            # 2. Obtener productos frecuentes
            frequent_products = self._get_frequent_products(user_id, organization_id)
            
            result = {
                "success": True,
                "pricing_preferences": pricing_prefs,
                "frequent_products": frequent_products,
                "has_learned_data": bool(pricing_prefs or frequent_products)
            }
            
            logger.info(f"✅ Query completed - Found {len(frequent_products)} products")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pricing_preferences": self._get_default_pricing(),
                "frequent_products": [],
                "has_learned_data": False
            }
    
    def _get_pricing_preferences(
        self,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Obtiene preferencias de pricing"""
        try:
            result = self.db.table("user_preferences").select(
                "*"
            ).eq("user_id", user_id).eq(
                "organization_id", organization_id
            ).eq("preference_type", "pricing").eq(
                "preference_key", "default_config"
            ).order("last_used", desc=True).limit(1).execute()
            
            if result.data:
                pref = result.data[0]
                value = pref.get("preference_value", {})
                return {
                    "coordination_enabled": value.get("coordination_enabled", False),
                    "coordination_rate": value.get("coordination_rate", 0.18),
                    "taxes_enabled": value.get("taxes_enabled", True),
                    "tax_rate": value.get("tax_rate", 0.16),
                    "cost_per_person_enabled": value.get("cost_per_person_enabled", False),
                    "confidence": min(pref.get("usage_count", 0) / 10.0, 1.0),
                    "usage_count": pref.get("usage_count", 0),
                    "source": "learned"
                }
            
            return self._get_default_pricing()
            
        except Exception as e:
            logger.error(f"Error getting pricing preferences: {e}")
            return self._get_default_pricing()
    
    def _get_frequent_products(
        self,
        user_id: str,
        organization_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Obtiene productos frecuentes"""
        try:
            result = self.db.table("user_preferences").select(
                "*"
            ).eq("user_id", user_id).eq(
                "organization_id", organization_id
            ).eq("preference_type", "product").order(
                "usage_count", desc=True
            ).limit(limit).execute()
            
            products = []
            for pref in result.data:
                value = pref.get("preference_value", {})
                products.append({
                    "product_name": pref.get("preference_key", ""),
                    "quantity": value.get("quantity", 0),
                    "unit_price": value.get("unit_price", 0),
                    "unit_cost": value.get("unit_cost", 0),
                    "usage_count": pref.get("usage_count", 0),
                    "confidence": min(pref.get("usage_count", 0) / 5.0, 1.0)
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting frequent products: {e}")
            return []
    
    def _get_default_pricing(self) -> Dict[str, Any]:
        """Retorna configuración de pricing por defecto"""
        return {
            "coordination_enabled": False,
            "coordination_rate": 0.18,
            "taxes_enabled": True,
            "tax_rate": 0.16,
            "cost_per_person_enabled": False,
            "confidence": 0.0,
            "usage_count": 0,
            "source": "default"
        }


# Instancia global del agente
query_agent = QueryAgent()
