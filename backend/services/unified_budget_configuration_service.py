"""
🎯 Unified Budget Configuration Service
Servicio centralizado que elimina inconsistencias y unifica branding + pricing
Usa las tablas existentes extendidas en lugar de crear nuevas
"""
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.core.database import get_database_client
from backend.models.pricing_models import PricingCalculation

logger = logging.getLogger(__name__)


class UnifiedBudgetConfigurationService:
    """Servicio unificado que centraliza toda la configuración de presupuestos"""
    
    def __init__(self):
        self.db_client = get_database_client()
    
    # ========================
    # CONFIGURACIÓN POR USUARIO
    # ========================
    
    def get_user_unified_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene configuración unificada completa por usuario"""
        try:
            logger.info(f"🔍 Getting unified config for user: {user_id}")
            
            # Usar función de DB optimizada
            result = self.db_client.client.rpc(
                'get_user_unified_budget_config',
                {'p_user_id': user_id}
            ).execute()
            
            if not result.data:
                logger.info(f"📝 No config found for user {user_id}, creating defaults")
                return self._create_smart_user_defaults(user_id)
            
            config_data = result.data[0]
            
            # Formatear respuesta unificada
            unified_config = {
                "user_id": user_id,
                "has_defaults": config_data.get('has_defaults', False),
                "branding": config_data.get('branding_config', {}),
                "pricing": config_data.get('pricing_config', {}),
                "document": config_data.get('document_config', {}),
                "auto_settings": config_data.get('auto_settings', {}),
                "statistics": config_data.get('statistics', {}),
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Retrieved unified config for user {user_id}")
            return unified_config
            
        except Exception as e:
            logger.error(f"❌ Error getting unified config for user {user_id}: {e}")
            return self._create_smart_user_defaults(user_id)
    
    def get_rfx_effective_config(self, rfx_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene configuración efectiva para un RFX (con herencia de usuario)"""
        try:
            logger.info(f"🔍 Getting effective config for RFX: {rfx_id}")
            
            # Verificar si el RFX existe en la base de datos primero
            rfx_check = self.db_client.client.table('rfx_v2')\
                .select('id, user_id')\
                .eq('id', rfx_id)\
                .execute()
            
            if not rfx_check.data:
                logger.warning(f"⚠️ RFX {rfx_id} no encontrado en base de datos")
                return None
            
            # Usar función de DB optimizada
            result = self.db_client.client.rpc(
                'get_rfx_effective_budget_config',
                {'p_rfx_id': rfx_id}
            ).execute()
            
            if not result.data:
                logger.warning(f"⚠️ No effective config found for RFX {rfx_id}")
                return None
            
            config_data = result.data[0]
            
            effective_config = {
                "rfx_id": rfx_id,
                "user_id": config_data.get('user_id'),
                "config": config_data.get('effective_config', {}),
                "source_info": config_data.get('source_info', {}),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Retrieved effective config for RFX {rfx_id}")
            return effective_config
            
        except Exception as e:
            logger.error(f"❌ Error getting effective config for RFX {rfx_id}: {e}")
            return None
    
    def update_user_defaults(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza configuraciones por defecto del usuario"""
        try:
            logger.info(f"🔄 Updating user defaults for: {user_id}")
            
            # Actualizar tabla principal
            update_data = {}
            
            # Mapear campos de configuración
            if 'currency' in updates:
                update_data['preferred_currency'] = updates['currency']
            if 'language' in updates:
                update_data['preferred_language'] = updates['language']
            if 'industry' in updates:
                update_data['industry_preference'] = updates['industry']
            
            # Flags de automatización
            if 'auto_apply_branding' in updates:
                update_data['auto_apply_branding'] = updates['auto_apply_branding']
            if 'auto_detect_industry' in updates:
                update_data['auto_detect_industry'] = updates['auto_detect_industry']
            
            if update_data:
                update_data['updated_at'] = datetime.now().isoformat()
                
                self.db_client.client.table('user_configuration_defaults')\
                    .update(update_data)\
                    .eq('user_id', user_id)\
                    .execute()
            
            # Actualizar configuraciones de pricing si se especifican
            if 'pricing' in updates:
                self._update_user_pricing_defaults(user_id, updates['pricing'])
            
            logger.info(f"✅ Updated user defaults for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating user defaults for {user_id}: {e}")
            return False
    
    # ========================
    # CÁLCULO INTELIGENTE
    # ========================
    
    def calculate_with_unified_config(self, rfx_id: str, base_subtotal: float) -> Optional[PricingCalculation]:
        """Calcula pricing usando configuración unificada"""
        try:
            logger.info(f"🧮 Calculating with unified config for RFX {rfx_id}")
            
            # Obtener configuración efectiva
            config = self.get_rfx_effective_config(rfx_id)
            if not config:
                logger.warning(f"⚠️ No config found for RFX {rfx_id}, using user defaults")
                # Intentar obtener configuración del usuario si el RFX no existe
                return self._calculate_with_user_defaults(rfx_id, base_subtotal)
            
            pricing_config = config['config'].get('pricing', {})
            
            # Crear objeto de cálculo
            calculation = PricingCalculation(subtotal=base_subtotal)
            
            # Aplicar coordinación
            if pricing_config.get('coordination_enabled', False):
                rate = pricing_config.get('coordination_rate', 0.18)
                calculation.coordination_enabled = True
                calculation.coordination_rate = rate
                calculation.coordination_amount = base_subtotal * rate
                calculation.applied_configs.append(f"coordination_{rate*100:.0f}%")
            
            # Aplicar costo por persona
            if pricing_config.get('cost_per_person_enabled', False):
                headcount = pricing_config.get('headcount', 50)
                calculation.cost_per_person_enabled = True
                calculation.headcount = headcount
                calculation.applied_configs.append(f"cost_per_person_{headcount}")
            
            # Aplicar impuestos
            if pricing_config.get('taxes_enabled', False):
                rate = pricing_config.get('tax_rate', 0.16)
                total_before_tax = base_subtotal + calculation.coordination_amount
                calculation.taxes_enabled = True
                calculation.tax_rate = rate
                calculation.tax_amount = total_before_tax * rate
                calculation.applied_configs.append(f"tax_{rate*100:.0f}%")
            
            # Calcular totales
            calculation.calculate_totals()
            
            logger.info(f"✅ Pricing calculated - Total: ${calculation.total_cost:.2f}")
            return calculation
            
        except Exception as e:
            logger.error(f"❌ Error calculating with unified config: {e}")
            return self._calculate_basic_pricing(base_subtotal)
    
    # ========================
    # MÉTODOS PRIVADOS
    # ========================
    
    def _create_smart_user_defaults(self, user_id: str, industry: str = None) -> Dict[str, Any]:
        """Crea configuración inteligente por defecto"""
        try:
            logger.info(f"📝 Creating smart defaults for user {user_id}")
            
            # Usar función de DB
            result = self.db_client.client.rpc(
                'create_smart_user_defaults',
                {
                    'p_user_id': user_id,
                    'p_industry': industry
                }
            ).execute()
            
            if result.data and result.data[0]:
                # Obtener configuración recién creada
                return self.get_user_unified_config(user_id)
            else:
                # Fallback básico
                return {
                    "user_id": user_id,
                    "has_defaults": False,
                    "branding": {},
                    "pricing": {
                        "coordination_enabled": True,
                        "coordination_rate": 0.18,
                        "cost_per_person_enabled": False,
                        "headcount": 50,
                        "taxes_enabled": False,
                        "tax_rate": 0.16
                    },
                    "document": {
                        "currency": "USD",
                        "language": "es"
                    },
                    "auto_settings": {
                        "auto_apply_branding": True
                    },
                    "statistics": {
                        "usage_count": 0,
                        "success_rate": 1.00
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error creating smart defaults: {e}")
            return self._get_fallback_config(user_id)
    
    def _update_user_pricing_defaults(self, user_id: str, pricing_updates: Dict[str, Any]) -> bool:
        """Actualiza configuraciones de pricing por defecto del usuario"""
        try:
            # Obtener configuración de pricing por defecto del usuario
            result = self.db_client.client.table('user_configuration_defaults')\
                .select('default_pricing_config_id')\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return False
            
            pricing_config_id = result.data[0]['default_pricing_config_id']
            if not pricing_config_id:
                return False
            
            # Actualizar configuraciones específicas
            if 'coordination_enabled' in pricing_updates or 'coordination_rate' in pricing_updates:
                self.db_client.client.table('coordination_configurations')\
                    .update({
                        'is_enabled': pricing_updates.get('coordination_enabled'),
                        'rate': pricing_updates.get('coordination_rate'),
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('pricing_config_id', pricing_config_id)\
                    .execute()
            
            if 'cost_per_person_enabled' in pricing_updates or 'headcount' in pricing_updates:
                self.db_client.client.table('cost_per_person_configurations')\
                    .update({
                        'is_enabled': pricing_updates.get('cost_per_person_enabled'),
                        'headcount': pricing_updates.get('headcount'),
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('pricing_config_id', pricing_config_id)\
                    .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating user pricing defaults: {e}")
            return False
    
    def _calculate_with_user_defaults(self, rfx_id: str, subtotal: float) -> PricingCalculation:
        """Calcula usando configuraciones por defecto del usuario o defaults del sistema"""
        try:
            # Para RFX que no existen, usar configuración por defecto del sistema
            logger.info(f"🔧 Using system defaults for calculation")
            
            calculation = PricingCalculation(subtotal=subtotal)
            
            # Aplicar configuración por defecto: coordinación habilitada con 18%
            calculation.coordination_enabled = True
            calculation.coordination_rate = 0.18
            calculation.coordination_amount = subtotal * 0.18
            calculation.applied_configs.append("coordination_18%_default")
            
            # No aplicar costo por persona por defecto
            calculation.cost_per_person_enabled = False
            
            # No aplicar impuestos por defecto
            calculation.taxes_enabled = False
            
            # Calcular totales
            calculation.calculate_totals()
            
            logger.info(f"✅ Default calculation - Total: ${calculation.total_cost:.2f}")
            return calculation
            
        except Exception as e:
            logger.error(f"❌ Error in default calculation: {e}")
            return self._calculate_basic_pricing(subtotal)
    
    def _calculate_basic_pricing(self, subtotal: float) -> PricingCalculation:
        """Cálculo básico sin configuraciones"""
        calculation = PricingCalculation(subtotal=subtotal)
        calculation.total_cost = subtotal
        calculation.calculate_totals()
        return calculation
    
    def _get_fallback_config(self, user_id: str) -> Dict[str, Any]:
        """Configuración de fallback en caso de error"""
        return {
            "user_id": user_id,
            "has_defaults": False,
            "branding": {
                "primary_color": "#2c5f7c",
                "secondary_color": "#ffffff"
            },
            "pricing": {
                "coordination_enabled": True,
                "coordination_rate": 0.18,
                "cost_per_person_enabled": False,
                "headcount": 50,
                "taxes_enabled": False,
                "tax_rate": 0.16
            },
            "document": {
                "currency": "USD",
                "language": "es"
            },
            "auto_settings": {
                "auto_apply_branding": True
            },
            "statistics": {
                "usage_count": 0,
                "success_rate": 1.00
            },
            "source": "fallback"
        }


# Instancia global del servicio
unified_budget_service = UnifiedBudgetConfigurationService()
