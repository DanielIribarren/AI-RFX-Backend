"""
💰 Pricing Configuration Models - Sistema de configuración de pricing flexible
Se integra con la estructura existente de RFX para opciones de coordinación y costo por persona
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum
from uuid import UUID


# ========================
# ENUMS PARA CONFIGURACIONES
# ========================

class PricingConfigType(str, Enum):
    """Tipos de configuración de pricing disponibles"""
    COORDINATION = "coordination"          # Coordinación y logística
    COST_PER_PERSON = "cost_per_person"   # Costo por persona
    TAXES = "taxes"                       # Impuestos (IVA, etc.)


class CoordinationLevel(str, Enum):
    """Niveles de coordinación disponibles (alineado con DB V2.2)"""
    BASIC = "basic"           # Coordinación básica
    STANDARD = "standard"     # Coordinación estándar
    PREMIUM = "premium"       # Coordinación premium
    CUSTOM = "custom"         # Coordinación personalizada


# ========================
# CONFIGURACIÓN BASE
# ========================

class PricingConfigValue(BaseModel):
    """Valor de configuración de pricing (alineado con esquema DB V2.2)"""
    
    # Para coordinación
    rate: Optional[float] = Field(None, ge=0, le=1, description="Porcentaje como decimal (ej: 0.18 para 18%)")
    level: Optional[CoordinationLevel] = None
    
    # Para costo por persona
    headcount: Optional[int] = Field(None, ge=1, description="Número de personas")
    per_person_display: Optional[bool] = Field(True, description="Mostrar costo por persona en propuesta")
    
    # Para impuestos
    tax_rate: Optional[float] = Field(None, ge=0, le=1, description="Tasa de impuesto como decimal")
    tax_type: Optional[str] = Field(None, description="Tipo de impuesto (IVA, Tax, etc.)")
    
    # Campos adicionales para flexibilidad
    description: Optional[str] = Field(None, description="Descripción de la configuración")
    notes: Optional[str] = Field(None, description="Notas adicionales")
    
    @validator('rate', 'tax_rate')
    def validate_percentages(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Rates must be between 0 and 1 (as decimal)')
        return v
    
    class Config:
        use_enum_values = True


class PricingConfig(BaseModel):
    """Configuración de pricing individual"""
    id: Optional[UUID] = None
    rfx_id: Optional[UUID] = None
    config_type: PricingConfigType
    is_enabled: bool = Field(False, description="Si esta configuración está activa")
    config_value: PricingConfigValue = Field(default_factory=PricingConfigValue)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# CONFIGURACIONES POR RFX
# ========================

class RFXPricingConfiguration(BaseModel):
    """Configuración completa de pricing para un RFX específico (alineado con DB V2.2)"""
    rfx_id: UUID
    
    # Configuraciones específicas (solo las implementadas en DB V2.2)
    coordination: Optional[PricingConfig] = None
    cost_per_person: Optional[PricingConfig] = None
    taxes: Optional[PricingConfig] = None
    
    # Metadata
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    created_by: Optional[str] = Field(None, description="Usuario que creó la configuración")
    
    @model_validator(mode='after')
    def validate_rfx_consistency(self):
        """Validar que todos los configs tengan el mismo rfx_id"""
        configs = [self.coordination, self.cost_per_person, self.taxes]
        for config in configs:
            if config and config.rfx_id and config.rfx_id != self.rfx_id:
                raise ValueError('Inconsistent rfx_id in pricing configuration')
        return self
    
    def get_enabled_configs(self) -> List[PricingConfig]:
        """Obtener solo las configuraciones habilitadas"""
        enabled = []
        for config in [self.coordination, self.cost_per_person, self.taxes]:
            if config and config.is_enabled:
                enabled.append(config)
        return enabled
    
    def has_coordination(self) -> bool:
        """Verificar si tiene coordinación habilitada"""
        return self.coordination and self.coordination.is_enabled
    
    def has_cost_per_person(self) -> bool:
        """Verificar si tiene costo por persona habilitado"""
        return self.cost_per_person and self.cost_per_person.is_enabled
    
    def get_coordination_rate(self) -> float:
        """Obtener tasa de coordinación o 0 si no está habilitada"""
        if self.has_coordination() and self.coordination.config_value.rate:
            return self.coordination.config_value.rate
        return 0.0
    
    def get_headcount(self) -> Optional[int]:
        """Obtener número de personas o None si no está configurado"""
        if self.has_cost_per_person() and self.cost_per_person.config_value.headcount:
            return self.cost_per_person.config_value.headcount
        return None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# PRESETS Y PLANTILLAS
# ========================

class PricingPreset(BaseModel):
    """Preset de configuración de pricing para reutilización"""
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    preset_type: str = Field("custom", description="Tipo de preset (catering, events, etc.)")
    
    # Configuraciones del preset
    coordination_enabled: bool = False
    coordination_rate: Optional[float] = Field(None, ge=0, le=1)
    
    cost_per_person_enabled: bool = False
    default_headcount: Optional[int] = Field(None, ge=1)
    
    taxes_enabled: bool = False
    default_tax_rate: Optional[float] = Field(None, ge=0, le=1)
    default_tax_type: Optional[str] = "IVA"
    
    # Metadata
    is_default: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    def to_rfx_configuration(self, rfx_id: UUID) -> RFXPricingConfiguration:
        """Convertir preset a configuración de RFX"""
        config = RFXPricingConfiguration(rfx_id=rfx_id)
        
        if self.coordination_enabled:
            config.coordination = PricingConfig(
                rfx_id=rfx_id,
                config_type=PricingConfigType.COORDINATION,
                is_enabled=True,
                config_value=PricingConfigValue(
                    rate=self.coordination_rate,
                    description="Coordinación y logística"
                )
            )
        
        if self.cost_per_person_enabled:
            config.cost_per_person = PricingConfig(
                rfx_id=rfx_id,
                config_type=PricingConfigType.COST_PER_PERSON,
                is_enabled=True,
                config_value=PricingConfigValue(
                    headcount=self.default_headcount,
                    description="Cálculo de costo por persona"
                )
            )
        
        if self.taxes_enabled:
            config.taxes = PricingConfig(
                rfx_id=rfx_id,
                config_type=PricingConfigType.TAXES,
                is_enabled=True,
                config_value=PricingConfigValue(
                    tax_rate=self.default_tax_rate,
                    tax_type=self.default_tax_type,
                    description=f"Impuestos ({self.default_tax_type})"
                )
            )
        
        return config
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# REQUEST/RESPONSE MODELS
# ========================

class PricingConfigurationRequest(BaseModel):
    """Request para configurar pricing de un RFX"""
    rfx_id: str = Field(..., min_length=1)
    
    # Configuración de coordinación
    coordination_enabled: bool = False
    coordination_rate: Optional[float] = Field(None, ge=0, le=1)
    coordination_level: Optional[CoordinationLevel] = None
    
    # Configuración de costo por persona
    cost_per_person_enabled: bool = False
    headcount: Optional[int] = Field(None, ge=1)
    per_person_display: bool = True
    
    # Configuración de impuestos
    taxes_enabled: bool = False
    tax_rate: Optional[float] = Field(None, ge=0, le=1)
    tax_type: Optional[str] = "IVA"
    
    # Usar preset existente
    use_preset_id: Optional[str] = None
    
    @validator('coordination_rate', 'tax_rate')
    def validate_rates(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Rates must be between 0 and 1 (as decimal)')
        return v
    
    class Config:
        use_enum_values = True


class PricingConfigurationResponse(BaseModel):
    """Response de configuración de pricing"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    data: Optional[RFXPricingConfiguration] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# MODELOS DE CÁLCULO
# ========================

class PricingCalculation(BaseModel):
    """Resultado de cálculos de pricing aplicados"""
    
    # Valores base
    subtotal: float = Field(0.0, ge=0, description="Subtotal de productos")
    
    # Cálculos de coordinación
    coordination_enabled: bool = False
    coordination_rate: Optional[float] = None
    coordination_amount: float = Field(0.0, ge=0)
    
    # Cálculos de costo por persona
    cost_per_person_enabled: bool = False
    headcount: Optional[int] = None
    cost_per_person: Optional[float] = Field(None, ge=0)
    
    # Cálculos de impuestos
    taxes_enabled: bool = False
    tax_rate: Optional[float] = None
    tax_amount: float = Field(0.0, ge=0)
    
    # Totales
    total_before_tax: float = Field(0.0, ge=0, description="Total antes de impuestos")
    total_cost: float = Field(0.0, ge=0, description="Total final")
    
    # Metadata del cálculo
    calculation_timestamp: datetime = Field(default_factory=datetime.now)
    applied_configs: List[str] = Field(default_factory=list, description="Configuraciones aplicadas")
    
    def calculate_totals(self):
        """Calcular todos los totales automáticamente"""
        # Total antes de impuestos (subtotal + coordinación)
        self.total_before_tax = self.subtotal + self.coordination_amount
        
        # Total final (incluye impuestos)
        self.total_cost = self.total_before_tax + self.tax_amount
        
        # Costo por persona
        if self.cost_per_person_enabled and self.headcount and self.headcount > 0:
            self.cost_per_person = self.total_cost / self.headcount
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ========================
# PRESETS POR DEFECTO
# ========================

def get_default_presets() -> List[PricingPreset]:
    """Obtener presets por defecto del sistema"""
    return [
        PricingPreset(
            name="Catering Básico",
            description="Configuración estándar para catering corporativo",
            preset_type="catering",
            coordination_enabled=True,
            coordination_rate=0.15,
            cost_per_person_enabled=True,
            default_headcount=50,
            is_default=True
        ),
        PricingPreset(
            name="Catering Premium",
            description="Configuración premium con coordinación completa",
            preset_type="catering",
            coordination_enabled=True,
            coordination_rate=0.18,
            cost_per_person_enabled=True,
            default_headcount=120,
            taxes_enabled=True,
            default_tax_rate=0.16,
            default_tax_type="IVA"
        ),
        PricingPreset(
            name="Eventos Corporativos",
            description="Configuración para eventos y actividades corporativas",
            preset_type="events",
            coordination_enabled=True,
            coordination_rate=0.20,
            cost_per_person_enabled=True,
            default_headcount=100
        ),
        PricingPreset(
            name="Solo Productos",
            description="Sin coordinación, solo productos",
            preset_type="products_only",
            coordination_enabled=False,
            cost_per_person_enabled=False,
            taxes_enabled=False
        )
    ]
