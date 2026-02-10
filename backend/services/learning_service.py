"""
🧠 Learning Service - AI Learning System
Filosofía KISS: Mínimo código, máxima funcionalidad
Responsabilidad: Aprender y aplicar preferencias de usuario
"""
import logging
from typing import Dict, Any, Optional
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class LearningService:
    """Servicio de aprendizaje de preferencias de usuario"""
    
    def __init__(self):
        self.db = get_database_client()
    
    # ============================================
    # PRICING PREFERENCES
    # ============================================
    
    def get_pricing_preference(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración de pricing más usada por el usuario
        
        Returns:
            {
                'coordination_enabled': bool,
                'coordination_rate': float,
                'taxes_enabled': bool,
                'tax_rate': float,
                'cost_per_person_enabled': bool
            } o None si no hay preferencias
        """
        try:
            result = self.db.client.table("user_preferences")\
                .select("preference_value, usage_count")\
                .eq("user_id", user_id)\
                .eq("preference_type", "pricing")\
                .order("usage_count", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Found pricing preference for user {user_id}")
                return result.data[0]['preference_value']
            
            logger.info(f"📭 No pricing preferences found for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting pricing preference: {e}")
            return None
    
    def save_pricing_preference(
        self, 
        user_id: str, 
        organization_id: str,
        pricing_config: Dict[str, Any]
    ) -> bool:
        """
        Guarda configuración de pricing como preferencia
        
        Args:
            pricing_config: {
                'coordination_enabled': bool,
                'coordination_rate': float,
                'taxes_enabled': bool,
                'tax_rate': float,
                'cost_per_person_enabled': bool
            }
        """
        try:
            # Upsert: si existe, incrementa usage_count; si no, crea
            self.db.client.table("user_preferences").upsert({
                "user_id": user_id,
                "organization_id": organization_id,
                "preference_type": "pricing",
                "preference_key": "default_config",
                "preference_value": pricing_config,
                "usage_count": 1,
                "last_used_at": "now()"
            }, on_conflict="user_id,preference_type,preference_key").execute()
            
            logger.info(f"✅ Saved pricing preference for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving pricing preference: {e}")
            return False
    
    # ============================================
    # PRODUCT PREFERENCES
    # ============================================
    
    def get_frequent_products(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Obtiene productos más usados por el usuario
        
        Returns:
            [
                {'product_name': str, 'usage_count': int},
                ...
            ]
        """
        try:
            result = self.db.client.table("user_preferences")\
                .select("preference_key, preference_value, usage_count")\
                .eq("user_id", user_id)\
                .eq("preference_type", "product")\
                .order("usage_count", desc=True)\
                .limit(limit)\
                .execute()
            
            products = [
                {
                    'product_name': row['preference_key'],
                    'usage_count': row['usage_count'],
                    'details': row['preference_value']
                }
                for row in result.data
            ]
            
            logger.info(f"✅ Found {len(products)} frequent products for user {user_id}")
            return products
            
        except Exception as e:
            logger.error(f"❌ Error getting frequent products: {e}")
            return []
    
    def save_product_usage(
        self,
        user_id: str,
        organization_id: str,
        product_name: str,
        product_details: Dict[str, Any]
    ) -> bool:
        """Registra uso de un producto"""
        try:
            self.db.client.table("user_preferences").upsert({
                "user_id": user_id,
                "organization_id": organization_id,
                "preference_type": "product",
                "preference_key": product_name,
                "preference_value": product_details,
                "usage_count": 1,
                "last_used_at": "now()"
            }, on_conflict="user_id,preference_type,preference_key").execute()
            
            logger.info(f"✅ Saved product usage: {product_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving product usage: {e}")
            return False
    
    # ============================================
    # PRICE CORRECTIONS
    # ============================================
    
    def record_price_correction(
        self,
        user_id: str,
        organization_id: str,
        product_name: str,
        original_price: float,
        corrected_price: float,
        rfx_id: Optional[str] = None,
        quantity: Optional[int] = None,
        context: Optional[Dict] = None
    ) -> bool:
        """Registra una corrección de precio"""
        try:
            self.db.client.table("price_corrections").insert({
                "user_id": user_id,
                "organization_id": organization_id,
                "product_name": product_name,
                "original_price": original_price,
                "corrected_price": corrected_price,
                "rfx_id": rfx_id,
                "quantity": quantity,
                "context": context or {}
            }).execute()
            
            logger.info(f"✅ Recorded price correction: {product_name} ${original_price} → ${corrected_price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording price correction: {e}")
            return False
    
    def get_learned_price(
        self,
        user_id: str,
        product_name: str,
        quantity: Optional[int] = None
    ) -> Optional[float]:
        """
        Obtiene precio aprendido para un producto
        Busca correcciones previas similares
        """
        try:
            query = self.db.client.table("price_corrections")\
                .select("corrected_price, quantity")\
                .eq("user_id", user_id)\
                .eq("product_name", product_name)\
                .order("created_at", desc=True)
            
            # Si hay cantidad, buscar correcciones con cantidad similar (±20%)
            if quantity:
                query = query.gte("quantity", int(quantity * 0.8))\
                             .lte("quantity", int(quantity * 1.2))
            
            result = query.limit(1).execute()
            
            if result.data:
                learned_price = result.data[0]['corrected_price']
                logger.info(f"✅ Found learned price for {product_name}: ${learned_price}")
                return float(learned_price)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting learned price: {e}")
            return None
    
    # ============================================
    # PRODUCT CO-OCCURRENCES
    # ============================================
    
    def get_related_products(
        self,
        organization_id: str,
        product_name: str,
        min_confidence: float = 0.3,
        limit: int = 5
    ) -> list[str]:
        """
        Obtiene productos que frecuentemente van con este producto
        
        Returns:
            ['Producto B', 'Producto C', ...]
        """
        try:
            # Buscar donde product_name es A o B
            result_a = self.db.client.table("product_co_occurrences")\
                .select("product_b, confidence")\
                .eq("organization_id", organization_id)\
                .eq("product_a", product_name)\
                .gte("confidence", min_confidence)\
                .order("confidence", desc=True)\
                .limit(limit)\
                .execute()
            
            result_b = self.db.client.table("product_co_occurrences")\
                .select("product_a, confidence")\
                .eq("organization_id", organization_id)\
                .eq("product_b", product_name)\
                .gte("confidence", min_confidence)\
                .order("confidence", desc=True)\
                .limit(limit)\
                .execute()
            
            related = []
            related.extend([row['product_b'] for row in result_a.data])
            related.extend([row['product_a'] for row in result_b.data])
            
            logger.info(f"✅ Found {len(related)} related products for {product_name}")
            return related[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error getting related products: {e}")
            return []


# Singleton instance
learning_service = LearningService()
