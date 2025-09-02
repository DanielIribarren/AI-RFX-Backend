"""
⚙️ Pricing Configuration Service - Servicio de configuración de pricing
Se integra con la estructura existente de base de datos para manejar configuraciones
de coordinación, costo por persona y otras opciones de pricing
"""
import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.models.pricing_models import (
    PricingConfig, PricingConfigType, RFXPricingConfiguration, 
    PricingConfigurationRequest, PricingCalculation, PricingPreset,
    get_default_presets, PricingConfigValue
)
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class PricingConfigurationService:
    """Servicio para manejar configuraciones de pricing de RFX"""
    
    def __init__(self):
        self.db_client = get_database_client()
    
    # ========================
    # CONFIGURACIÓN POR RFX
    # ========================
    
    def get_rfx_pricing_configuration(self, rfx_id: str) -> Optional[RFXPricingConfiguration]:
        """Obtener configuración de pricing para un RFX específico"""
        try:
            logger.info(f"🔍 Getting pricing configuration for RFX: {rfx_id}")
            
            # Verificar que el RFX existe
            rfx_record = self.db_client.get_rfx_by_id(rfx_id)
            if not rfx_record:
                logger.warning(f"⚠️ RFX not found: {rfx_id}")
                return None
            
            # Buscar configuraciones existentes
            try:
                # Usamos query directo ya que no existe tabla específica en V2.0
                # Almacenaremos las configuraciones en metadata_json del RFX
                metadata = rfx_record.get("metadata_json", {}) or {}
                pricing_config_data = metadata.get("pricing_configuration", {})
                
                if not pricing_config_data:
                    logger.info(f"📝 No pricing configuration found for RFX {rfx_id}, using defaults")
                    return self._create_default_configuration(rfx_id)
                
                # Convertir datos JSON a modelo Pydantic
                config = self._json_to_pricing_configuration(rfx_id, pricing_config_data)
                logger.info(f"✅ Retrieved pricing configuration for RFX {rfx_id}")
                return config
                
            except Exception as e:
                logger.error(f"❌ Error parsing pricing configuration for RFX {rfx_id}: {e}")
                return self._create_default_configuration(rfx_id)
                
        except Exception as e:
            logger.error(f"❌ Error getting pricing configuration for RFX {rfx_id}: {e}")
            return None
    
    def save_rfx_pricing_configuration(self, config: RFXPricingConfiguration) -> bool:
        """Guardar configuración de pricing para un RFX"""
        try:
            rfx_id = str(config.rfx_id)
            logger.info(f"💾 Saving pricing configuration for RFX: {rfx_id}")
            
            # Convertir configuración a JSON para almacenar en metadata
            config_json = self._pricing_configuration_to_json(config)
            
            # Obtener metadata actual del RFX
            rfx_record = self.db_client.get_rfx_by_id(rfx_id)
            if not rfx_record:
                logger.error(f"❌ RFX not found: {rfx_id}")
                return False
            
            current_metadata = rfx_record.get("metadata_json", {}) or {}
            
            # Actualizar solo la sección de pricing_configuration
            current_metadata["pricing_configuration"] = config_json
            current_metadata["pricing_last_updated"] = datetime.now().isoformat()
            
            # Guardar metadata actualizada
            success = self.db_client.update_rfx_data(rfx_id, {
                "metadata_json": current_metadata
            })
            
            if success:
                logger.info(f"✅ Pricing configuration saved for RFX {rfx_id}")
                
                # Registrar evento en historial
                history_event = {
                    "rfx_id": rfx_id,
                    "event_type": "pricing_configuration_updated",
                    "description": "Configuración de pricing actualizada por el usuario",
                    "new_values": {
                        "coordination_enabled": config.has_coordination(),
                        "cost_per_person_enabled": config.has_cost_per_person(),
                        "coordination_rate": config.get_coordination_rate(),
                        "headcount": config.get_headcount()
                    },
                    "performed_by": "user"
                }
                self.db_client.insert_rfx_history(history_event)
                
                return True
            else:
                logger.error(f"❌ Failed to save pricing configuration for RFX {rfx_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving pricing configuration: {e}")
            return False
    
    def update_rfx_pricing_from_request(self, request: PricingConfigurationRequest) -> Optional[RFXPricingConfiguration]:
        """Actualizar configuración de pricing desde un request"""
        try:
            rfx_id = request.rfx_id
            logger.info(f"🔄 Updating pricing configuration for RFX: {rfx_id}")
            
            # Si se especifica un preset, usarlo como base
            if request.use_preset_id:
                preset = self.get_preset_by_id(request.use_preset_id)
                if preset:
                    config = preset.to_rfx_configuration(uuid.UUID(rfx_id))
                else:
                    config = RFXPricingConfiguration(rfx_id=uuid.UUID(rfx_id))
            else:
                # Obtener configuración existente o crear nueva
                config = self.get_rfx_pricing_configuration(rfx_id)
                if not config:
                    config = RFXPricingConfiguration(rfx_id=uuid.UUID(rfx_id))
            
            # Actualizar configuración de coordinación
            if request.coordination_enabled:
                coordination_rate = request.coordination_rate or 0.18  # Default 18%
                config.coordination = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.COORDINATION,
                    is_enabled=True,
                    config_value=PricingConfigValue(
                        rate=coordination_rate,
                        level=request.coordination_level,
                        description="Coordinación y logística"
                    )
                )
            else:
                config.coordination = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.COORDINATION,
                    is_enabled=False,
                    config_value=PricingConfigValue()
                )
            
            # Actualizar configuración de costo por persona
            if request.cost_per_person_enabled and request.headcount:
                config.cost_per_person = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.COST_PER_PERSON,
                    is_enabled=True,
                    config_value=PricingConfigValue(
                        headcount=request.headcount,
                        per_person_display=request.per_person_display,
                        description=f"Cálculo para {request.headcount} personas"
                    )
                )
            else:
                config.cost_per_person = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.COST_PER_PERSON,
                    is_enabled=False,
                    config_value=PricingConfigValue()
                )
            
            # Actualizar configuración de impuestos
            if request.taxes_enabled and request.tax_rate:
                config.taxes = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.TAXES,
                    is_enabled=True,
                    config_value=PricingConfigValue(
                        tax_rate=request.tax_rate,
                        tax_type=request.tax_type or "IVA",
                        description=f"Impuestos ({request.tax_type or 'IVA'})"
                    )
                )
            else:
                config.taxes = PricingConfig(
                    rfx_id=uuid.UUID(rfx_id),
                    config_type=PricingConfigType.TAXES,
                    is_enabled=False,
                    config_value=PricingConfigValue()
                )
            
            # Actualizar timestamp
            config.updated_at = datetime.now()
            
            # Guardar configuración
            success = self.save_rfx_pricing_configuration(config)
            if success:
                logger.info(f"✅ Pricing configuration updated for RFX {rfx_id}")
                return config
            else:
                logger.error(f"❌ Failed to save updated pricing configuration for RFX {rfx_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error updating pricing configuration: {e}")
            return None
    
    # ========================
    # CÁLCULOS DE PRICING
    # ========================
    
    def calculate_pricing(self, rfx_id: str, base_subtotal: float) -> PricingCalculation:
        """Calcular pricing total aplicando todas las configuraciones"""
        try:
            logger.info(f"🧮 Calculating pricing for RFX {rfx_id}, subtotal: ${base_subtotal:.2f}")
            
            # Obtener configuración del RFX
            config = self.get_rfx_pricing_configuration(rfx_id)
            if not config:
                logger.warning(f"⚠️ No pricing configuration for RFX {rfx_id}, using defaults")
                config = self._create_default_configuration(rfx_id)
            
            # Inicializar cálculo
            calculation = PricingCalculation(subtotal=base_subtotal)
            
            # Aplicar coordinación
            if config.has_coordination():
                coordination_rate = config.get_coordination_rate()
                calculation.coordination_enabled = True
                calculation.coordination_rate = coordination_rate
                calculation.coordination_amount = base_subtotal * coordination_rate
                calculation.applied_configs.append(f"coordination_{coordination_rate*100:.0f}%")
                logger.info(f"📊 Applied coordination: {coordination_rate*100:.1f}% = ${calculation.coordination_amount:.2f}")
            
            # Aplicar costo por persona
            if config.has_cost_per_person():
                headcount = config.get_headcount()
                calculation.cost_per_person_enabled = True
                calculation.headcount = headcount
                calculation.applied_configs.append(f"cost_per_person_{headcount}")
                logger.info(f"👥 Cost per person calculation enabled for {headcount} people")
            
            # Aplicar impuestos (si están configurados)
            if config.taxes and config.taxes.is_enabled:
                tax_rate = config.taxes.config_value.tax_rate or 0
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
            # Return safe default calculation
            calculation = PricingCalculation(subtotal=base_subtotal)
            calculation.total_cost = base_subtotal
            return calculation
    
    # ========================
    # GESTIÓN DE PRESETS
    # ========================
    
    def get_available_presets(self) -> List[PricingPreset]:
        """Obtener presets disponibles (por ahora solo los por defecto)"""
        try:
            logger.info("📋 Getting available pricing presets")
            presets = get_default_presets()
            logger.info(f"✅ Found {len(presets)} available presets")
            return presets
        except Exception as e:
            logger.error(f"❌ Error getting presets: {e}")
            return []
    
    def get_preset_by_id(self, preset_id: str) -> Optional[PricingPreset]:
        """Obtener preset específico por ID (simplified para MVP)"""
        try:
            presets = self.get_available_presets()
            for preset in presets:
                if preset.name.lower().replace(" ", "_") == preset_id.lower():
                    return preset
            return None
        except Exception as e:
            logger.error(f"❌ Error getting preset {preset_id}: {e}")
            return None
    
    # ========================
    # MÉTODOS PRIVADOS/UTILITARIOS
    # ========================
    
    def _create_default_configuration(self, rfx_id: str) -> RFXPricingConfiguration:
        """Crear configuración por defecto para un RFX"""
        try:
            rfx_uuid = uuid.UUID(rfx_id) if isinstance(rfx_id, str) else rfx_id
            
            config = RFXPricingConfiguration(rfx_id=rfx_uuid)
            
            # Configuración por defecto: coordinación deshabilitada
            config.coordination = PricingConfig(
                rfx_id=rfx_uuid,
                config_type=PricingConfigType.COORDINATION,
                is_enabled=False,
                config_value=PricingConfigValue(rate=0.18, description="Coordinación y logística")
            )
            
            # Costo por persona deshabilitado por defecto
            config.cost_per_person = PricingConfig(
                rfx_id=rfx_uuid,
                config_type=PricingConfigType.COST_PER_PERSON,
                is_enabled=False,
                config_value=PricingConfigValue(headcount=50, description="Cálculo por persona")
            )
            
            logger.info(f"📝 Created default pricing configuration for RFX {rfx_id}")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error creating default configuration: {e}")
            return RFXPricingConfiguration(rfx_id=uuid.UUID(rfx_id))
    
    def _pricing_configuration_to_json(self, config: RFXPricingConfiguration) -> Dict[str, Any]:
        """Convertir configuración Pydantic a JSON para almacenar en DB"""
        try:
            return {
                "rfx_id": str(config.rfx_id),
                "coordination": config.coordination.model_dump() if config.coordination else None,
                "cost_per_person": config.cost_per_person.model_dump() if config.cost_per_person else None,
                "taxes": config.taxes.model_dump() if config.taxes else None,
                "discount": config.discount.model_dump() if config.discount else None,
                "service_fee": config.service_fee.model_dump() if config.service_fee else None,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                "created_by": config.created_by
            }
        except Exception as e:
            logger.error(f"❌ Error converting pricing configuration to JSON: {e}")
            return {}
    
    def _json_to_pricing_configuration(self, rfx_id: str, config_json: Dict[str, Any]) -> RFXPricingConfiguration:
        """Convertir JSON de DB a configuración Pydantic"""
        try:
            rfx_uuid = uuid.UUID(rfx_id)
            
            config = RFXPricingConfiguration(rfx_id=rfx_uuid)
            
            # Convertir cada configuración
            if config_json.get("coordination"):
                coordination_data = config_json["coordination"]
                coordination_data["rfx_id"] = str(rfx_uuid)  # Ensure consistency
                config.coordination = PricingConfig(**coordination_data)
            
            if config_json.get("cost_per_person"):
                cost_per_person_data = config_json["cost_per_person"]
                cost_per_person_data["rfx_id"] = str(rfx_uuid)  # Ensure consistency
                config.cost_per_person = PricingConfig(**cost_per_person_data)
            
            if config_json.get("taxes"):
                taxes_data = config_json["taxes"]
                taxes_data["rfx_id"] = str(rfx_uuid)  # Ensure consistency
                config.taxes = PricingConfig(**taxes_data)
            
            # Timestamps
            if config_json.get("created_at"):
                config.created_at = datetime.fromisoformat(config_json["created_at"])
            if config_json.get("updated_at"):
                config.updated_at = datetime.fromisoformat(config_json["updated_at"])
            
            config.created_by = config_json.get("created_by")
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error converting JSON to pricing configuration: {e}")
            return self._create_default_configuration(rfx_id)
    
    def get_pricing_summary_for_rfx(self, rfx_id: str) -> Dict[str, Any]:
        """Obtener resumen de configuración de pricing para mostrar en frontend"""
        try:
            config = self.get_rfx_pricing_configuration(rfx_id)
            if not config:
                return {
                    "coordination_enabled": False,
                    "cost_per_person_enabled": False,
                    "has_pricing_configuration": False
                }
            
            summary = {
                "has_pricing_configuration": True,
                "coordination_enabled": config.has_coordination(),
                "coordination_rate": config.get_coordination_rate() if config.has_coordination() else None,
                "cost_per_person_enabled": config.has_cost_per_person(),
                "headcount": config.get_headcount() if config.has_cost_per_person() else None,
                "taxes_enabled": config.taxes and config.taxes.is_enabled if config.taxes else False,
                "enabled_configs": [cfg.config_type.value for cfg in config.get_enabled_configs()],
                "last_updated": config.updated_at.isoformat() if config.updated_at else None
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting pricing summary for RFX {rfx_id}: {e}")
            return {"has_pricing_configuration": False, "error": str(e)}
