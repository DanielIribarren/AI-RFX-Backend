"""
⚙️ Pricing Configuration Service V2.2 - Database-First Approach
Usa las nuevas tablas de pricing en lugar de metadata_json
Coordinación y costo por persona completamente independientes
"""
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.models.pricing_models import (
    PricingConfig, PricingConfigType, RFXPricingConfiguration, 
    PricingConfigurationRequest, PricingCalculation, PricingPreset,
    get_default_presets, PricingConfigValue, CoordinationLevel
)
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

# 🧠 AI Learning System Integration
try:
    from backend.services.recommendation_service import recommendation_service
    LEARNING_ENABLED = True
    logger.info("✅ AI Learning System enabled for pricing recommendations")
except ImportError:
    LEARNING_ENABLED = False
    logger.warning("⚠️ AI Learning System not available - using defaults only")


class PricingConfigurationServiceV2:
    """Servicio V2.2 que usa las nuevas tablas de pricing directamente"""
    
    def __init__(self):
        self.db_client = get_database_client()
    
    # ========================
    # CONFIGURACIÓN POR RFX
    # ========================
    
    def get_rfx_pricing_configuration(self, rfx_id: str) -> Optional[RFXPricingConfiguration]:
        """Obtener configuración de pricing desde las nuevas tablas"""
        try:
            logger.info(f"🔍 Getting pricing configuration for RFX: {rfx_id} (from DB tables)")
            
            # Usar la vista optimizada para obtener configuración completa
            response = self.db_client.client.rpc(
                'get_rfx_pricing_config',
                {'rfx_uuid': rfx_id}
            ).execute()
            
            if not response.data:
                logger.info(f"📝 No pricing configuration found for RFX {rfx_id}")
                # 🧠 Try to get user preferences from learning system
                return self._create_default_configuration(rfx_id, use_learning=True)
            
            config_data = response.data[0]
            config = self._map_db_data_to_model(rfx_id, config_data)
            
            logger.info(f"✅ Retrieved pricing configuration for RFX {rfx_id}")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error getting pricing configuration for RFX {rfx_id}: {e}")
            # Fallback a configuración por defecto
            return self._create_default_configuration(rfx_id)
    
    def update_rfx_pricing_from_request(self, request: PricingConfigurationRequest) -> Optional[RFXPricingConfiguration]:
        """Actualizar configuración de pricing para un RFX usando tablas normalizadas (V2.2)

        Crea o encuentra la configuración activa en `rfx_pricing_configurations` y
        upsertea las tablas hijas: `coordination_configurations`, `cost_per_person_configurations`
        y `tax_configurations` según los flags del request.
        """
        try:
            rfx_id = request.rfx_id
            logger.info(f"🔄 [V2] Updating pricing configuration (DB-first) for RFX: {rfx_id}")

            # 1) Obtener o crear configuración principal activa
            pricing_config_id = self._get_or_create_active_pricing_config_id(rfx_id)

            # 2) Upsert coordinación
            desired_coord_rate = request.coordination_rate if request.coordination_rate is not None else 0.18
            # Normalización de coordination_level/coordination_type a enum permitido
            allowed_coord_types = {'basic', 'standard', 'premium', 'custom'}
            if request.coordination_level is not None and hasattr(request.coordination_level, 'value'):
                desired_coord_type = str(request.coordination_level.value)
            elif request.coordination_level is not None:
                desired_coord_type = str(request.coordination_level).lower()
            else:
                desired_coord_type = 'standard'
            if desired_coord_type not in allowed_coord_types:
                desired_coord_type = 'standard'

            coord_existing = self.db_client.client.table('coordination_configurations')\
                .select('id, rate, coordination_type')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()

            if coord_existing.data:
                self.db_client.client.table('coordination_configurations')\
                    .update({
                        'is_enabled': bool(request.coordination_enabled),
                        'rate': float(desired_coord_rate),
                        'coordination_type': str(desired_coord_type),
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('id', coord_existing.data[0]['id'])\
                    .execute()
            else:
                self.db_client.client.table('coordination_configurations')\
                    .insert({
                        'pricing_config_id': pricing_config_id,
                        'is_enabled': bool(request.coordination_enabled),
                        'rate': float(desired_coord_rate),
                        'coordination_type': str(desired_coord_type),
                        'description': 'Coordinación y logística'
                    })\
                    .execute()

            # 3) Upsert costo por persona (headcount es NOT NULL en la tabla)
            desired_headcount = request.headcount if (request.headcount and request.headcount > 0) else 120
            cpp_existing = self.db_client.client.table('cost_per_person_configurations')\
                .select('id, headcount')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()

            if cpp_existing.data:
                preserved_headcount = cpp_existing.data[0].get('headcount') or desired_headcount
                self.db_client.client.table('cost_per_person_configurations')\
                    .update({
                        'is_enabled': bool(request.cost_per_person_enabled),
                        'headcount': int(desired_headcount if request.cost_per_person_enabled else preserved_headcount),
                        'display_in_proposal': bool(request.per_person_display),
                        'calculation_base': 'final_total',
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('id', cpp_existing.data[0]['id'])\
                    .execute()
            else:
                self.db_client.client.table('cost_per_person_configurations')\
                    .insert({
                        'pricing_config_id': pricing_config_id,
                        'is_enabled': bool(request.cost_per_person_enabled),
                        'headcount': int(desired_headcount),
                        'display_in_proposal': bool(request.per_person_display),
                        'calculation_base': 'final_total',
                        'description': 'Cálculo de costo individual'
                    })\
                    .execute()

            # 4) Upsert impuestos (la fila puede no existir si está deshabilitado)
            tax_existing = self.db_client.client.table('tax_configurations')\
                .select('id, tax_rate, tax_name')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()

            if request.taxes_enabled:
                desired_tax_rate = request.tax_rate if request.tax_rate is not None else 0.16
                desired_tax_name = request.tax_type or 'IVA'
                if tax_existing.data:
                    self.db_client.client.table('tax_configurations')\
                        .update({
                            'is_enabled': True,
                            'tax_rate': float(desired_tax_rate),
                            'tax_name': str(desired_tax_name),
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', tax_existing.data[0]['id'])\
                        .execute()
                else:
                    self.db_client.client.table('tax_configurations')\
                        .insert({
                            'pricing_config_id': pricing_config_id,
                            'is_enabled': True,
                            'tax_rate': float(desired_tax_rate),
                            'tax_name': str(desired_tax_name)
                        })\
                        .execute()
            else:
                # Si existe, marcar como deshabilitado manteniendo valores obligatorios
                if tax_existing.data:
                    preserved_tax_rate = tax_existing.data[0].get('tax_rate') or 0.16
                    preserved_tax_name = tax_existing.data[0].get('tax_name') or 'IVA'
                    self.db_client.client.table('tax_configurations')\
                        .update({
                            'is_enabled': False,
                            'tax_rate': float(preserved_tax_rate),
                            'tax_name': str(preserved_tax_name),
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', tax_existing.data[0]['id'])\
                        .execute()

            # 5) Marcar quién actualizó la configuración principal (opcional)
            try:
                self.db_client.client.table('rfx_pricing_configurations')\
                    .update({'updated_by': 'user', 'updated_at': datetime.now().isoformat()})\
                    .eq('id', pricing_config_id)\
                    .execute()
            except Exception as e:
                logger.warning(f"⚠️ Could not set updated_by on rfx_pricing_configurations: {e}")

            # 6) Log y retorno de configuración actualizada
            updated_config = self.get_rfx_pricing_configuration(rfx_id)
            if updated_config:
                self._log_configuration_change(rfx_id, 'configuration_updated', updated_config)
            logger.info(f"✅ [V2] Pricing configuration updated for RFX {rfx_id}")
            
            # 🧠 Guardar como preferencia del usuario (aprendizaje)
            if LEARNING_ENABLED:
                try:
                    rfx_data = self.db_client.client.table('rfx_v2')\
                        .select('user_id, organization_id')\
                        .eq('id', rfx_id)\
                        .single()\
                        .execute()
                    
                    if rfx_data.data:
                        user_id = rfx_data.data.get('user_id')
                        org_id = rfx_data.data.get('organization_id')
                        
                        if user_id and org_id:
                            from backend.services.learning_service import learning_service
                            
                            pricing_preference = {
                                'coordination_enabled': bool(request.coordination_enabled),
                                'coordination_rate': float(desired_coord_rate),
                                'taxes_enabled': bool(request.taxes_enabled),
                                'tax_rate': float(desired_tax_rate),
                                'cost_per_person_enabled': bool(request.cost_per_person_enabled)
                            }
                            
                            learning_service.save_pricing_preference(
                                user_id=user_id,
                                organization_id=org_id,
                                pricing_config=pricing_preference
                            )
                            logger.info(f"🧠 Saved pricing preference for user {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not save pricing preference: {e}")
            
            return updated_config

        except Exception as e:
            logger.error(f"❌ [V2] Error updating pricing configuration for RFX {request.rfx_id}: {e}")
            return None

    def save_rfx_pricing_configuration(self, config: RFXPricingConfiguration) -> bool:
        """Guardar configuración de pricing en las nuevas tablas"""
        try:
            rfx_id = str(config.rfx_id)
            logger.info(f"💾 Saving pricing configuration for RFX: {rfx_id} (to DB tables)")
            
            # Usar stored procedure para guardar atomically
            response = self.db_client.client.rpc(
                'save_rfx_pricing_config',
                {
                    'rfx_uuid': rfx_id,
                    'config_data': self._model_to_db_data(config)
                }
            ).execute()
            
            if response.data and response.data[0].get('success'):
                logger.info(f"✅ Pricing configuration saved for RFX {rfx_id}")
                
                # Registrar en historial usando método directo
                self._log_configuration_change(rfx_id, 'configuration_updated', config)
                
                return True
            else:
                logger.error(f"❌ Failed to save pricing configuration for RFX {rfx_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving pricing configuration: {e}")
            return False
    
    def update_coordination_only(self, rfx_id: str, enabled: bool, 
                                  rate: Optional[float] = None, 
                                  level: Optional[str] = None) -> Optional[RFXPricingConfiguration]:
        """Actualizar SOLO configuración de coordinación (método simplificado)"""
        try:
            logger.info(f"🔧 [Independent] Updating coordination only for RFX {rfx_id}: enabled={enabled}")
            
            # 1) Obtener o crear configuración principal activa
            pricing_config_id = self._get_or_create_active_pricing_config_id(rfx_id)
            
            # 2) Valores por defecto
            desired_rate = rate if rate is not None else 0.18
            desired_level = level if level else 'standard'
            
            # Normalizar nivel
            allowed_levels = {'basic', 'standard', 'premium', 'custom'}
            if desired_level.lower() not in allowed_levels:
                desired_level = 'standard'
            
            # 3) Upsert coordinación
            coord_existing = self.db_client.client.table('coordination_configurations')\
                .select('id')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()
            
            if coord_existing.data:
                self.db_client.client.table('coordination_configurations')\
                    .update({
                        'is_enabled': bool(enabled),
                        'rate': float(desired_rate),
                        'coordination_type': str(desired_level),
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('id', coord_existing.data[0]['id'])\
                    .execute()
            else:
                self.db_client.client.table('coordination_configurations')\
                    .insert({
                        'pricing_config_id': pricing_config_id,
                        'is_enabled': bool(enabled),
                        'rate': float(desired_rate),
                        'coordination_type': str(desired_level),
                        'description': 'Coordinación y logística'
                    })\
                    .execute()
            
            logger.info(f"✅ Coordination config updated independently for RFX {rfx_id}")
            return self.get_rfx_pricing_configuration(rfx_id)
            
        except Exception as e:
            logger.error(f"❌ Error updating coordination only: {e}")
            return None
    
    def update_cost_per_person_only(self, rfx_id: str, enabled: bool,
                                     headcount: Optional[int] = None,
                                     display_in_proposal: bool = True) -> Optional[RFXPricingConfiguration]:
        """Actualizar SOLO configuración de costo por persona (método simplificado)"""
        try:
            logger.info(f"👥 [Independent] Updating cost per person only for RFX {rfx_id}: enabled={enabled}")
            
            # 1) Obtener o crear configuración principal activa
            pricing_config_id = self._get_or_create_active_pricing_config_id(rfx_id)
            
            # 2) Valor por defecto
            desired_headcount = headcount if (headcount and headcount > 0) else 120
            
            # 3) Upsert costo por persona
            cpp_existing = self.db_client.client.table('cost_per_person_configurations')\
                .select('id, headcount')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()
            
            if cpp_existing.data:
                preserved_headcount = cpp_existing.data[0].get('headcount') or desired_headcount
                self.db_client.client.table('cost_per_person_configurations')\
                    .update({
                        'is_enabled': bool(enabled),
                        'headcount': int(desired_headcount if enabled else preserved_headcount),
                        'display_in_proposal': bool(display_in_proposal),
                        'calculation_base': 'final_total',
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('id', cpp_existing.data[0]['id'])\
                    .execute()
            else:
                self.db_client.client.table('cost_per_person_configurations')\
                    .insert({
                        'pricing_config_id': pricing_config_id,
                        'is_enabled': bool(enabled),
                        'headcount': int(desired_headcount),
                        'display_in_proposal': bool(display_in_proposal),
                        'calculation_base': 'final_total',
                        'description': 'Cálculo de costo individual'
                    })\
                    .execute()
            
            logger.info(f"✅ Cost per person config updated independently for RFX {rfx_id}")
            return self.get_rfx_pricing_configuration(rfx_id)
            
        except Exception as e:
            logger.error(f"❌ Error updating cost per person only: {e}")
            return None
    
    def update_taxes_only(self, rfx_id: str, enabled: bool,
                          tax_rate: Optional[float] = None,
                          tax_type: Optional[str] = None) -> Optional[RFXPricingConfiguration]:
        """Actualizar SOLO configuración de impuestos (método simplificado)"""
        try:
            logger.info(f"💵 [Independent] Updating taxes only for RFX {rfx_id}: enabled={enabled}")
            
            # 1) Obtener o crear configuración principal activa
            pricing_config_id = self._get_or_create_active_pricing_config_id(rfx_id)
            
            # 2) Valores por defecto
            desired_tax_rate = tax_rate if tax_rate is not None else 0.16
            desired_tax_type = tax_type or 'IVA'
            
            # 3) Upsert impuestos
            tax_existing = self.db_client.client.table('tax_configurations')\
                .select('id')\
                .eq('pricing_config_id', pricing_config_id)\
                .limit(1)\
                .execute()
            
            if enabled:
                if tax_existing.data:
                    self.db_client.client.table('tax_configurations')\
                        .update({
                            'is_enabled': True,
                            'tax_rate': float(desired_tax_rate),
                            'tax_name': str(desired_tax_type),
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', tax_existing.data[0]['id'])\
                        .execute()
                else:
                    self.db_client.client.table('tax_configurations')\
                        .insert({
                            'pricing_config_id': pricing_config_id,
                            'is_enabled': True,
                            'tax_rate': float(desired_tax_rate),
                            'tax_name': str(desired_tax_type)
                        })\
                        .execute()
            else:
                # Deshabilitar si existe
                if tax_existing.data:
                    self.db_client.client.table('tax_configurations')\
                        .update({
                            'is_enabled': False,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', tax_existing.data[0]['id'])\
                        .execute()
            
            logger.info(f"✅ Taxes config updated independently for RFX {rfx_id}")
            return self.get_rfx_pricing_configuration(rfx_id)
            
        except Exception as e:
            logger.error(f"❌ Error updating taxes only: {e}")
            return None
    
    def update_coordination_config(self, rfx_id: str, enabled: bool, rate: float = 0.18, 
                                 coordination_type: str = 'standard', updated_by: str = 'user') -> bool:
        """Actualizar solo la configuración de coordinación (método legacy)"""
        try:
            logger.info(f"🤝 Updating coordination config for RFX {rfx_id}: enabled={enabled}, rate={rate}")
            
            # Query directo a la tabla de coordinación
            query = """
            UPDATE coordination_configurations cc
            SET 
                is_enabled = %s,
                rate = %s,
                coordination_type = %s,
                updated_at = NOW()
            FROM rfx_pricing_configurations rpc
            WHERE cc.pricing_config_id = rpc.id 
            AND rpc.rfx_id = %s 
            AND rpc.is_active = true
            RETURNING cc.id
            """
            
            result = self.db_client.client.rpc(
                'execute_coordination_update',
                {
                    'enabled': enabled,
                    'rate_value': rate,
                    'coord_type': coordination_type,
                    'rfx_uuid': rfx_id,
                    'updated_by_user': updated_by
                }
            ).execute()
            
            success = bool(result.data and result.data[0].get('updated'))
            
            if success:
                logger.info(f"✅ Coordination configuration updated for RFX {rfx_id}")
                # Log específico para coordinación
                self._log_coordination_change(rfx_id, enabled, rate, updated_by)
            else:
                logger.error(f"❌ Failed to update coordination config for RFX {rfx_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating coordination config: {e}")
            return False
    
    def update_cost_per_person_config(self, rfx_id: str, enabled: bool, headcount: int = 120,
                                    calculation_base: str = 'final_total', updated_by: str = 'user') -> bool:
        """Actualizar solo la configuración de costo por persona"""
        try:
            logger.info(f"👥 Updating cost per person config for RFX {rfx_id}: enabled={enabled}, headcount={headcount}")
            
            result = self.db_client.client.rpc(
                'execute_cost_per_person_update',
                {
                    'enabled': enabled,
                    'headcount_value': headcount,
                    'calc_base': calculation_base,
                    'rfx_uuid': rfx_id,
                    'updated_by_user': updated_by
                }
            ).execute()
            
            success = bool(result.data and result.data[0].get('updated'))
            
            if success:
                logger.info(f"✅ Cost per person configuration updated for RFX {rfx_id}")
                # Log específico para costo por persona
                self._log_cost_per_person_change(rfx_id, enabled, headcount, updated_by)
            else:
                logger.error(f"❌ Failed to update cost per person config for RFX {rfx_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating cost per person config: {e}")
            return False
    
    # ========================
    # CÁLCULOS DE PRICING OPTIMIZADOS
    # ========================
    
    def calculate_pricing(self, rfx_id: str, base_subtotal: float) -> PricingCalculation:
        """Calcular pricing usando datos de las nuevas tablas"""
        try:
            logger.info(f"🧮 Calculating pricing for RFX {rfx_id}, subtotal: ${base_subtotal:.2f} (from DB)")
            
            # Obtener configuración activa usando vista optimizada
            result = self.db_client.client.table('active_rfx_pricing')\
                .select('*')\
                .eq('rfx_id', rfx_id)\
                .execute()
            
            if not result.data:
                logger.warning(f"⚠️ No active pricing configuration for RFX {rfx_id}")
                return self._calculate_basic_pricing(base_subtotal)
            
            config_data = result.data[0]
            
            # Inicializar cálculo
            calculation = PricingCalculation(subtotal=base_subtotal)
            
            # Aplicar coordinación
            if config_data.get('coordination_enabled'):
                coordination_rate = config_data.get('coordination_rate', 0)
                calculation.coordination_enabled = True
                calculation.coordination_rate = coordination_rate
                calculation.coordination_amount = base_subtotal * coordination_rate
                calculation.applied_configs.append(f"coordination_{coordination_rate*100:.0f}%")
                logger.info(f"📊 Applied coordination: {coordination_rate*100:.1f}% = ${calculation.coordination_amount:.2f}")
            
            # Aplicar costo por persona
            if config_data.get('cost_per_person_enabled'):
                headcount = config_data.get('headcount', 50)
                calculation.cost_per_person_enabled = True
                calculation.headcount = headcount
                calculation.applied_configs.append(f"cost_per_person_{headcount}")
                logger.info(f"👥 Cost per person calculation enabled for {headcount} people")
            
            # Aplicar impuestos
            if config_data.get('taxes_enabled'):
                tax_rate = config_data.get('tax_rate', 0)
                total_before_tax = base_subtotal + calculation.coordination_amount
                calculation.taxes_enabled = True
                calculation.tax_rate = tax_rate
                calculation.tax_amount = total_before_tax * tax_rate
                calculation.applied_configs.append(f"tax_{tax_rate*100:.0f}%")
                logger.info(f"💰 Applied taxes: {tax_rate*100:.1f}% = ${calculation.tax_amount:.2f}")
            
            # Calcular totales
            calculation.calculate_totals()
            
            logger.info(f"✅ Pricing calculation completed:")
            logger.info(f"   Subtotal: ${calculation.subtotal:.2f}")
            logger.info(f"   Coordination: ${calculation.coordination_amount:.2f}")
            logger.info(f"   Taxes: ${calculation.tax_amount:.2f}")
            logger.info(f"   Total: ${calculation.total_cost:.2f}")
            if calculation.cost_per_person:
                logger.info(f"   Cost per person: ${calculation.cost_per_person:.2f}")
            
            return calculation
            
        except Exception as e:
            logger.error(f"❌ Error calculating pricing for RFX {rfx_id}: {e}")
            return self._calculate_basic_pricing(base_subtotal)
    
    def get_pricing_breakdown(self, rfx_id: str) -> Dict[str, Any]:
        """Obtener desglose detallado de pricing desde DB"""
        try:
            # Usar vista de resumen completo
            result = self.db_client.client.table('rfx_pricing_summary')\
                .select('*')\
                .eq('rfx_id', rfx_id)\
                .execute()
            
            if not result.data:
                return {"error": "No pricing configuration found"}
            
            data = result.data[0]
            
            breakdown = {
                "rfx_id": rfx_id,
                "configuration": {
                    "name": data.get('configuration_name'),
                    "status": data.get('status'),
                    "last_updated": data.get('updated_at')
                },
                "coordination": {
                    "enabled": data.get('coordination_enabled', False),
                    "rate": data.get('coordination_rate'),
                    "percentage": data.get('coordination_percentage'),
                    "type": data.get('coordination_type'),
                    "description": data.get('coordination_description')
                },
                "cost_per_person": {
                    "enabled": data.get('cost_per_person_enabled', False),
                    "headcount": data.get('headcount'),
                    "confirmed": data.get('headcount_confirmed'),
                    "calculation_base": data.get('cost_calculation_base'),
                    "show_in_proposal": data.get('show_cost_per_person')
                },
                "taxes": {
                    "enabled": data.get('taxes_enabled', False),
                    "name": data.get('tax_name'),
                    "rate": data.get('tax_rate'),
                    "percentage": data.get('tax_percentage')
                }
            }
            
            return breakdown
            
        except Exception as e:
            logger.error(f"❌ Error getting pricing breakdown for RFX {rfx_id}: {e}")
            return {"error": str(e)}
    
    # ========================
    # GESTIÓN DE PRESETS Y BULK OPERATIONS
    # ========================
    
    def apply_preset_to_rfx(self, rfx_id: str, preset_name: str, updated_by: str = 'user') -> bool:
        """Aplicar preset de configuración a un RFX"""
        try:
            logger.info(f"🎛️ Applying preset '{preset_name}' to RFX {rfx_id}")
            
            # Obtener preset
            presets = get_default_presets()
            preset = next((p for p in presets if p.name.lower().replace(" ", "_") == preset_name.lower()), None)
            
            if not preset:
                logger.error(f"❌ Preset '{preset_name}' not found")
                return False
            
            # Convertir preset a configuración
            config = preset.to_rfx_configuration(uuid.UUID(rfx_id))
            
            # Guardar configuración
            success = self.save_rfx_pricing_configuration(config)
            
            if success:
                logger.info(f"✅ Preset '{preset_name}' applied to RFX {rfx_id}")
                self._log_preset_application(rfx_id, preset_name, updated_by)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error applying preset to RFX {rfx_id}: {e}")
            return False
    
    def bulk_update_coordination(self, rfx_ids: List[str], enabled: bool, rate: float, 
                               updated_by: str = 'bulk_operation') -> Dict[str, bool]:
        """Actualizar coordinación para múltiples RFX"""
        try:
            logger.info(f"🔄 Bulk updating coordination for {len(rfx_ids)} RFX records")
            
            results = {}
            for rfx_id in rfx_ids:
                try:
                    success = self.update_coordination_config(rfx_id, enabled, rate, 'standard', updated_by)
                    results[rfx_id] = success
                except Exception as e:
                    logger.error(f"❌ Failed to update coordination for RFX {rfx_id}: {e}")
                    results[rfx_id] = False
            
            successful_updates = sum(1 for success in results.values() if success)
            logger.info(f"✅ Bulk coordination update: {successful_updates}/{len(rfx_ids)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in bulk coordination update: {e}")
            return {rfx_id: False for rfx_id in rfx_ids}
    
    # ========================
    # MÉTODOS PRIVADOS/UTILITARIOS
    # ========================
    
    def _get_or_create_active_pricing_config_id(self, rfx_id: str) -> str:
        """Obtener el ID de configuración activa para un RFX o crearla si no existe."""
        try:
            existing = self.db_client.client.table('rfx_pricing_configurations')\
                .select('id')\
                .eq('rfx_id', rfx_id)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()

            if existing.data:
                return existing.data[0]['id']

            # Crear configuración principal por defecto activa
            new_id = str(uuid.uuid4())
            insert_resp = self.db_client.client.table('rfx_pricing_configurations')\
                .insert({
                    'id': new_id,
                    'rfx_id': str(rfx_id),
                    'configuration_name': 'Default Configuration',
                    'is_active': True,
                    'status': 'active',
                    'created_by': 'user'
                })\
                .execute()

            return new_id
        except Exception as e:
            logger.error(f"❌ Error ensuring active pricing configuration for RFX {rfx_id}: {e}")
            # Como fallback, intentar crear igualmente
            new_id = str(uuid.uuid4())
            try:
                self.db_client.client.table('rfx_pricing_configurations')\
                    .insert({
                        'id': new_id,
                        'rfx_id': str(rfx_id),
                        'configuration_name': 'Default Configuration',
                        'is_active': True,
                        'status': 'active',
                        'created_by': 'system'
                    })\
                    .execute()
            except Exception:
                pass
            return new_id

    def _create_default_configuration(self, rfx_id: str, use_learning: bool = False) -> RFXPricingConfiguration:
        """Crear configuración por defecto usando las nuevas tablas
        
        Args:
            rfx_id: ID del RFX
            use_learning: Si True, intenta usar recomendaciones del learning system
        """
        try:
            rfx_uuid = uuid.UUID(rfx_id) if isinstance(rfx_id, str) else rfx_id
            
            # 🧠 Intentar obtener recomendación del learning system
            recommended_config = None
            if use_learning and LEARNING_ENABLED:
                try:
                    # Obtener user_id y rfx_type del RFX
                    rfx_data = self.db_client.client.table('rfx_v2')\
                        .select('user_id, rfx_type')\
                        .eq('id', str(rfx_uuid))\
                        .single()\
                        .execute()
                    
                    if rfx_data.data:
                        user_id = rfx_data.data.get('user_id')
                        rfx_type = rfx_data.data.get('rfx_type')
                        
                        if user_id:
                            recommended_config = recommendation_service.recommend_pricing_config(
                                user_id=user_id,
                                rfx_type=rfx_type
                            )
                            
                            if recommended_config:
                                logger.info(f"🧠 Using learned pricing config (confidence: {recommended_config.get('confidence', 0)}, source: {recommended_config.get('source', 'unknown')})")
                except Exception as e:
                    logger.warning(f"⚠️ Could not get pricing recommendation: {e}")
            
            # Valores por defecto (o recomendados)
            if recommended_config:
                coord_enabled = recommended_config.get('coordination_enabled', False)
                coord_rate = recommended_config.get('coordination_rate', 0.18)
                tax_enabled = recommended_config.get('taxes_enabled', False)
                tax_rate = recommended_config.get('tax_rate', 0.16)
                cpp_enabled = recommended_config.get('cost_per_person_enabled', False)
                source = f"learned_{recommended_config.get('source', 'unknown')}"
            else:
                coord_enabled = False
                coord_rate = 0.18
                tax_enabled = False
                tax_rate = 0.16
                cpp_enabled = False
                source = 'default'
            
            # Crear configuración principal
            main_config_id = str(uuid.uuid4())
            
            # Insertar en rfx_pricing_configurations
            self.db_client.client.table('rfx_pricing_configurations').insert({
                'id': main_config_id,
                'rfx_id': str(rfx_uuid),
                'configuration_name': 'Default Configuration' if not recommended_config else 'Learned Configuration',
                'is_active': True,
                'status': 'active',
                'created_by': 'system'
            }).execute()
            
            # Crear configuraciones (con valores aprendidos si existen)
            self.db_client.client.table('coordination_configurations').insert({
                'pricing_config_id': main_config_id,
                'is_enabled': coord_enabled,
                'rate': coord_rate,
                'description': 'Coordinación y logística',
                'configuration_source': source
            }).execute()
            
            self.db_client.client.table('cost_per_person_configurations').insert({
                'pricing_config_id': main_config_id,
                'is_enabled': cpp_enabled,
                'headcount': 120,
                'headcount_source': source,
                'description': 'Cálculo de costo individual'
            }).execute()
            
            # Crear modelo de respuesta
            config = RFXPricingConfiguration(rfx_id=rfx_uuid)
            config.coordination = PricingConfig(
                rfx_id=rfx_uuid,
                config_type=PricingConfigType.COORDINATION,
                is_enabled=coord_enabled,
                config_value=PricingConfigValue(rate=coord_rate, description="Coordinación y logística")
            )
            config.cost_per_person = PricingConfig(
                rfx_id=rfx_uuid,
                config_type=PricingConfigType.COST_PER_PERSON,
                is_enabled=cpp_enabled,
                config_value=PricingConfigValue(headcount=120, description="Cálculo por persona")
            )
            
            logger.info(f"📝 Created {'learned' if recommended_config else 'default'} pricing configuration for RFX {rfx_id} in DB")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error creating default configuration: {e}")
            return RFXPricingConfiguration(rfx_id=uuid.UUID(rfx_id))
    
    def _calculate_basic_pricing(self, subtotal: float) -> PricingCalculation:
        """Cálculo básico sin configuraciones"""
        calculation = PricingCalculation(subtotal=subtotal)
        calculation.total_cost = subtotal
        calculation.calculate_totals()
        return calculation
    
    def _map_db_data_to_model(self, rfx_id: str, db_data: Dict[str, Any]) -> RFXPricingConfiguration:
        """Mapear datos de DB a modelo Pydantic"""
        try:
            rfx_uuid = uuid.UUID(rfx_id)
            config = RFXPricingConfiguration(rfx_id=rfx_uuid)
            
            # Mapear coordinación
            if db_data.get('coordination_enabled') is not None:
                # Mapear coordination_type de DB a CoordinationLevel
                coord_type_from_db = db_data.get('coordination_type', 'standard')
                try:
                    coordination_level = CoordinationLevel(coord_type_from_db)
                except ValueError:
                    coordination_level = CoordinationLevel.STANDARD
                
                config.coordination = PricingConfig(
                    rfx_id=rfx_uuid,
                    config_type=PricingConfigType.COORDINATION,
                    is_enabled=db_data.get('coordination_enabled', False),
                    config_value=PricingConfigValue(
                        rate=db_data.get('coordination_rate', 0.18),
                        level=coordination_level,
                        description=db_data.get('coordination_description', 'Coordinación y logística')
                    )
                )
            
            # Mapear costo por persona
            if db_data.get('cost_per_person_enabled') is not None:
                config.cost_per_person = PricingConfig(
                    rfx_id=rfx_uuid,
                    config_type=PricingConfigType.COST_PER_PERSON,
                    is_enabled=db_data.get('cost_per_person_enabled', False),
                    config_value=PricingConfigValue(
                        headcount=db_data.get('headcount', 50),
                        description='Cálculo de costo individual'
                    )
                )
            
            # Mapear impuestos
            if db_data.get('taxes_enabled') is not None:
                config.taxes = PricingConfig(
                    rfx_id=rfx_uuid,
                    config_type=PricingConfigType.TAXES,
                    is_enabled=db_data.get('taxes_enabled', False),
                    config_value=PricingConfigValue(
                        tax_rate=db_data.get('tax_rate', 0.16),
                        tax_type=db_data.get('tax_name', 'IVA'),
                        description=f"Impuestos ({db_data.get('tax_name', 'IVA')})"
                    )
                )
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error mapping DB data to model: {e}")
            return RFXPricingConfiguration(rfx_id=uuid.UUID(rfx_id))
    
    def _model_to_db_data(self, config: RFXPricingConfiguration) -> Dict[str, Any]:
        """Convertir modelo Pydantic a formato para DB"""
        try:
            return {
                "rfx_id": str(config.rfx_id),
                "coordination": {
                    "enabled": config.has_coordination(),
                    "rate": config.get_coordination_rate(),
                    "type": config.coordination.config_value.level.value if (config.coordination and config.coordination.config_value.level) else 'standard'
                } if config.coordination else None,
                "cost_per_person": {
                    "enabled": config.has_cost_per_person(),
                    "headcount": config.get_headcount()
                } if config.cost_per_person else None,
                "taxes": {
                    "enabled": config.taxes and config.taxes.is_enabled,
                    "rate": config.taxes.config_value.tax_rate if config.taxes else None,
                    "type": config.taxes.config_value.tax_type if config.taxes else None
                } if config.taxes else None
            }
        except Exception as e:
            logger.error(f"❌ Error converting model to DB data: {e}")
            return {}
    
    def _log_configuration_change(self, rfx_id: str, change_type: str, config: RFXPricingConfiguration):
        """Log cambio de configuración en historial"""
        try:
            # Registrar en tabla de historial (alineado con esquema rfx_history)
            history_event = {
                "rfx_id": str(rfx_id),
                "change_type": change_type,
                "change_description": f"Pricing configuration {change_type.replace('_', ' ')}",
                "new_values": {
                    "coordination_enabled": bool(config.has_coordination()),
                    "cost_per_person_enabled": bool(config.has_cost_per_person()),
                    "coordination_rate": float(config.get_coordination_rate() or 0),
                    "headcount": int(config.get_headcount() or 0),
                    "timestamp": datetime.now().isoformat()
                },
                "changed_by": "user"
            }
            self.db_client.insert_rfx_history(history_event)
        except Exception as e:
            logger.error(f"❌ Error logging configuration change: {e}")
    
    def _log_coordination_change(self, rfx_id: str, enabled: bool, rate: float, updated_by: str):
        """Log cambio específico de coordinación"""
        try:
            self.db_client.insert_rfx_history({
                "rfx_id": rfx_id,
                "change_type": "coordination_updated",
                "change_description": f"Coordination {'enabled' if enabled else 'disabled'}" + 
                             (f" at {rate*100:.1f}%" if enabled else ""),
                "new_values": {"enabled": bool(enabled), "rate": float(rate)},
                "changed_by": updated_by
            })
        except Exception as e:
            logger.error(f"❌ Error logging coordination change: {e}")
    
    def _log_cost_per_person_change(self, rfx_id: str, enabled: bool, headcount: int, updated_by: str):
        """Log cambio específico de costo por persona"""
        try:
            self.db_client.insert_rfx_history({
                "rfx_id": rfx_id,
                "change_type": "cost_per_person_updated",
                "change_description": f"Cost per person {'enabled' if enabled else 'disabled'}" + 
                             (f" for {headcount} people" if enabled else ""),
                "new_values": {"enabled": bool(enabled), "headcount": int(headcount)},
                "changed_by": updated_by
            })
        except Exception as e:
            logger.error(f"❌ Error logging cost per person change: {e}")
    
    def _log_preset_application(self, rfx_id: str, preset_name: str, updated_by: str):
        """Log aplicación de preset"""
        try:
            self.db_client.insert_rfx_history({
                "rfx_id": rfx_id,
                "change_type": "preset_applied",
                "change_description": f"Applied pricing preset: {preset_name}",
                "new_values": {"preset_name": preset_name},
                "changed_by": updated_by
            })
        except Exception as e:
            logger.error(f"❌ Error logging preset application: {e}")
    
    def get_available_presets(self) -> List[PricingPreset]:
        """Obtener presets disponibles (usando defaults del modelo)"""
        try:
            logger.info("📋 Getting available pricing presets")
            presets = get_default_presets()
            logger.info(f"✅ Retrieved {len(presets)} pricing presets")
            return presets
        except Exception as e:
            logger.error(f"❌ Error getting available presets: {e}")
            return []

    def get_pricing_summary_for_rfx(self, rfx_id: str) -> Dict[str, Any]:
        """Obtener resumen de configuración desde nuevas tablas"""
        try:
            breakdown = self.get_pricing_breakdown(rfx_id)
            if "error" in breakdown:
                return {
                    "coordination_enabled": False,
                    "cost_per_person_enabled": False,
                    "has_pricing_configuration": False
                }
            
            return {
                "has_pricing_configuration": True,
                "coordination_enabled": breakdown["coordination"]["enabled"],
                "coordination_rate": breakdown["coordination"]["rate"],
                "cost_per_person_enabled": breakdown["cost_per_person"]["enabled"],
                "headcount": breakdown["cost_per_person"]["headcount"],
                "taxes_enabled": breakdown["taxes"]["enabled"],
                "last_updated": breakdown["configuration"]["last_updated"],
                "enabled_configs": [
                    config for config in ["coordination", "cost_per_person", "taxes"] 
                    if breakdown.get(config, {}).get("enabled", False)
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting pricing summary for RFX {rfx_id}: {e}")
            return {"has_pricing_configuration": False, "error": str(e)}
