"""
Learning Agent - Aprende de RFX completados
Approach simple: LLM analiza + llamadas directas a BD
"""
import logging
from typing import Dict, Any
from datetime import datetime
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class LearningAgent:
    """Agente que aprende de RFX completados"""
    
    def __init__(self):
        self.db = get_database_client()
        logger.info("✅ Learning Agent initialized")
    
    def learn_from_completed_rfx(
        self,
        rfx_id: str,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Aprende de un RFX completado.
        
        Args:
            rfx_id: UUID del RFX
            user_id: UUID del usuario
            organization_id: UUID de la organización
            
        Returns:
            Dict con resultado del aprendizaje
        """
        try:
            logger.info(f"🧠 Learning from RFX: {rfx_id}")
            
            # 1. Obtener datos del RFX
            rfx_data = self._get_rfx_data(rfx_id)
            if not rfx_data:
                return {"success": False, "reason": "RFX not found"}
            
            # 2. Aprender configuración de pricing
            pricing_learned = self._learn_pricing_config(
                rfx_id, user_id, organization_id, rfx_data
            )
            
            # 3. Aprender productos
            products_learned = self._learn_products(
                rfx_id, user_id, organization_id, rfx_data
            )
            
            # 4. Registrar evento de aprendizaje
            self._log_learning_event(
                user_id=user_id,
                organization_id=organization_id,
                rfx_id=rfx_id,
                event_type="rfx_completed_learning",
                context={
                    "pricing_learned": pricing_learned,
                    "products_count": len(products_learned)
                }
            )
            
            logger.info(f"✅ Learning completed for RFX {rfx_id}")
            return {
                "success": True,
                "pricing_learned": pricing_learned,
                "products_learned": products_learned
            }
            
        except Exception as e:
            logger.error(f"❌ Learning failed for RFX {rfx_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_rfx_data(self, rfx_id: str) -> Dict[str, Any]:
        """Obtiene datos del RFX"""
        try:
            result = self.db.table("rfx_v2").select("*").eq("id", rfx_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting RFX data: {e}")
            return None
    
    def _learn_pricing_config(
        self,
        rfx_id: str,
        user_id: str,
        organization_id: str,
        rfx_data: Dict[str, Any]
    ) -> bool:
        """Aprende configuración de pricing"""
        try:
            # Obtener configuración de pricing del RFX
            pricing_result = self.db.table("pricing_configurations").select(
                "*"
            ).eq("rfx_id", rfx_id).eq("is_active", True).execute()
            
            if not pricing_result.data:
                return False
            
            pricing_config = pricing_result.data[0]
            
            # Guardar preferencia de pricing
            self.db.table("user_preferences").upsert({
                "user_id": user_id,
                "organization_id": organization_id,
                "preference_type": "pricing",
                "preference_key": "default_config",
                "preference_value": {
                    "coordination_enabled": pricing_config.get("coordination_enabled", False),
                    "coordination_rate": pricing_config.get("coordination_rate", 0.18),
                    "taxes_enabled": pricing_config.get("taxes_enabled", True),
                    "tax_rate": pricing_config.get("tax_rate", 0.16),
                    "cost_per_person_enabled": pricing_config.get("cost_per_person_enabled", False)
                },
                "usage_count": 1,
                "last_used": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="user_id,organization_id,preference_type,preference_key").execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error learning pricing config: {e}")
            return False
    
    def _learn_products(
        self,
        rfx_id: str,
        user_id: str,
        organization_id: str,
        rfx_data: Dict[str, Any]
    ) -> list:
        """Aprende productos usados"""
        try:
            # Obtener productos del RFX
            products_result = self.db.table("rfx_products").select(
                "*"
            ).eq("rfx_id", rfx_id).execute()
            
            if not products_result.data:
                return []
            
            learned_products = []
            
            for product in products_result.data:
                # Guardar uso del producto
                self.db.table("user_preferences").upsert({
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "preference_type": "product",
                    "preference_key": product.get("product_name", ""),
                    "preference_value": {
                        "quantity": product.get("quantity", 0),
                        "unit_price": product.get("unit_price", 0),
                        "unit_cost": product.get("unit_cost", 0)
                    },
                    "usage_count": 1,
                    "last_used": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }, on_conflict="user_id,organization_id,preference_type,preference_key").execute()
                
                learned_products.append(product.get("product_name", ""))
            
            return learned_products
            
        except Exception as e:
            logger.error(f"Error learning products: {e}")
            return []
    
    def _log_learning_event(
        self,
        user_id: str,
        organization_id: str,
        rfx_id: str,
        event_type: str,
        context: Dict[str, Any]
    ):
        """Registra evento de aprendizaje"""
        try:
            self.db.table("learning_events").insert({
                "user_id": user_id,
                "organization_id": organization_id,
                "rfx_id": rfx_id,
                "event_type": event_type,
                "context": context,
                "action_taken": {"learned": True},
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error logging learning event: {e}")


# Instancia global del agente
learning_agent = LearningAgent()
