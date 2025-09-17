"""
💰 Pricing Configuration Models V3.0 - Budy AI Schema Compatible
Sistema de configuración de pricing adaptado al nuevo esquema pricing_configurations
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum
from uuid import UUID


# ========================
# ENUMS (Aligned with budy-ai-schema.sql)
# ========================

class PricingModelEnum(str, Enum):
    """Pricing calculation models (from budy-ai-schema.sql)"""
    PER_PERSON = "per_person"
    FIXED_PRICE = "fixed_price"
    HOURLY_RATE = "hourly_rate"
    PER_UNIT = "per_unit"
    PERCENTAGE_BASED = "percentage_based"
    TIERED_PRICING = "tiered_pricing"
    VALUE_BASED = "value_based"
    HYBRID = "hybrid"


class CoordinationTypeEnum(str, Enum):
    """Coordination calculation types"""
    PERCENTAGE = "percentage"     # Percentage of subtotal
    FIXED_AMOUNT = "fixed_amount" # Fixed amount regardless of total
    PER_PERSON = "per_person"     # Fixed amount per person
    TIERED = "tiered"             # Tiered based on total or people


class HeadcountSourceEnum(str, Enum):
    """Source of headcount information"""
    MANUAL = "manual"           # Manually entered
    EXTRACTED = "extracted"     # AI extracted from documents
    ESTIMATED = "estimated"     # AI estimated from context
    CLIENT_PROVIDED = "client_provided"  # Provided by client


class CostCalculationBaseEnum(str, Enum):
    """Base for cost per person calculations"""
    TOTAL = "total"         # Total final cost
    SUBTOTAL = "subtotal"   # Subtotal before tax
    ITEMS_ONLY = "items_only" # Only item costs, no coordination


class TaxTypeEnum(str, Enum):
    """Types of taxes"""
    VAT = "VAT"     # Value Added Tax
    IVA = "IVA"     # Impuesto al Valor Agregado
    GST = "GST"     # Goods and Services Tax
    SALES_TAX = "SALES_TAX"  # Sales Tax
    CUSTOM = "CUSTOM"   # Custom tax type


class DiscountTypeEnum(str, Enum):
    """Types of discounts"""
    PERCENTAGE = "percentage"   # Percentage discount
    FIXED_AMOUNT = "fixed_amount"  # Fixed amount discount
    BULK_DISCOUNT = "bulk_discount"  # Bulk quantity discount
    LOYALTY_DISCOUNT = "loyalty_discount"  # Loyalty customer discount
    SEASONAL = "seasonal"       # Seasonal discount


# ========================
# MAIN PRICING CONFIGURATION MODEL
# ========================

class PricingConfigurationModel(BaseModel):
    """Main pricing configuration model (aligned with budy-ai-schema.sql)"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID (updated from rfx_id)")
    
    # Main configuration
    pricing_model: PricingModelEnum = PricingModelEnum.FIXED_PRICE
    is_active: bool = True
    
    # Coordination settings
    coordination_enabled: bool = False
    coordination_rate: float = Field(0.15, ge=0, le=1, description="Coordination rate as decimal")
    coordination_type: CoordinationTypeEnum = CoordinationTypeEnum.PERCENTAGE
    coordination_minimum: Optional[float] = Field(None, ge=0)
    coordination_maximum: Optional[float] = Field(None, ge=0)
    
    # Cost per person settings
    cost_per_person_enabled: bool = False
    headcount: Optional[int] = Field(None, gt=0)
    headcount_source: HeadcountSourceEnum = HeadcountSourceEnum.MANUAL
    cost_calculation_base: CostCalculationBaseEnum = CostCalculationBaseEnum.TOTAL
    
    # Tax settings
    tax_enabled: bool = False
    tax_rate: float = Field(0.0, ge=0, le=1, description="Tax rate as decimal")
    tax_type: Optional[TaxTypeEnum] = None
    tax_jurisdiction: Optional[str] = Field(None, max_length=100)
    
    # Discount settings
    discount_enabled: bool = False
    discount_rate: float = Field(0.0, ge=0, le=1, description="Discount rate as decimal")
    discount_type: Optional[DiscountTypeEnum] = None
    discount_reason: Optional[str] = None
    
    # Margin settings
    margin_target: float = Field(0.20, ge=0, le=1, description="Target margin as decimal")
    minimum_margin: float = Field(0.10, ge=0, le=1, description="Minimum margin as decimal")
    
    # Control and metadata
    configuration_notes: Optional[str] = None
    created_by: UUID = Field(..., description="User ID who created the configuration")
    approved_by: Optional[UUID] = Field(None, description="User ID who approved the configuration")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @validator('coordination_rate', 'tax_rate', 'discount_rate', 'margin_target', 'minimum_margin')
    def validate_percentages(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Rates and margins must be between 0 and 1 (as decimal)')
        return v
    
    @validator('coordination_maximum')
    def validate_coordination_range(cls, v, values):
        if v is not None and 'coordination_minimum' in values and values['coordination_minimum'] is not None:
            if v < values['coordination_minimum']:
                raise ValueError('Coordination maximum must be greater than or equal to minimum')
        return v
    
    @validator('minimum_margin')
    def validate_margin_range(cls, v, values):
        if v is not None and 'margin_target' in values and values['margin_target'] is not None:
            if v > values['margin_target']:
                raise ValueError('Minimum margin must be less than or equal to target margin')
        return v

    def get_coordination_amount(self, subtotal: float) -> float:
        """Calculate coordination amount based on configuration"""
        if not self.coordination_enabled or subtotal <= 0:
            return 0.0
        
        if self.coordination_type == CoordinationTypeEnum.PERCENTAGE:
            amount = subtotal * self.coordination_rate
        elif self.coordination_type == CoordinationTypeEnum.FIXED_AMOUNT:
            amount = self.coordination_rate  # Using rate field for fixed amount
        elif self.coordination_type == CoordinationTypeEnum.PER_PERSON:
            amount = (self.coordination_rate * self.headcount) if self.headcount else 0.0
        else:  # TIERED - simplified implementation
            amount = subtotal * self.coordination_rate
        
        # Apply min/max limits
        if self.coordination_minimum is not None:
            amount = max(amount, self.coordination_minimum)
        if self.coordination_maximum is not None:
            amount = min(amount, self.coordination_maximum)
        
        return amount
    
    def get_tax_amount(self, taxable_amount: float) -> float:
        """Calculate tax amount based on configuration"""
        if not self.tax_enabled or taxable_amount <= 0:
            return 0.0
        return taxable_amount * self.tax_rate
    
    def get_discount_amount(self, amount: float) -> float:
        """Calculate discount amount based on configuration"""
        if not self.discount_enabled or amount <= 0:
            return 0.0
        
        if self.discount_type == DiscountTypeEnum.PERCENTAGE:
            return amount * self.discount_rate
        elif self.discount_type == DiscountTypeEnum.FIXED_AMOUNT:
            return min(self.discount_rate, amount)  # Don't exceed the amount
        else:
            return amount * self.discount_rate  # Default to percentage
    
    def get_cost_per_person(self, total_cost: float) -> Optional[float]:
        """Calculate cost per person if enabled"""
        if not self.cost_per_person_enabled or not self.headcount or self.headcount <= 0:
            return None
        return total_cost / self.headcount
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# PRICING CALCULATION MODELS
# ========================

class PricingCalculationModel(BaseModel):
    """Pricing calculation result model"""
    
    # Input values
    subtotal: float = Field(0.0, ge=0, description="Base subtotal of items")
    
    # Coordination calculations
    coordination_enabled: bool = False
    coordination_rate: Optional[float] = None
    coordination_amount: float = Field(0.0, ge=0)
    
    # Cost per person calculations  
    cost_per_person_enabled: bool = False
    headcount: Optional[int] = None
    cost_per_person: Optional[float] = Field(None, ge=0)
    
    # Tax calculations
    tax_enabled: bool = False
    tax_rate: Optional[float] = None
    tax_amount: float = Field(0.0, ge=0)
    
    # Discount calculations
    discount_enabled: bool = False
    discount_rate: Optional[float] = None
    discount_amount: float = Field(0.0, ge=0)
    
    # Final totals
    total_before_tax: float = Field(0.0, ge=0, description="Total before taxes")
    total_after_discount: float = Field(0.0, ge=0, description="Total after discounts")
    total_cost: float = Field(0.0, ge=0, description="Final total cost")
    
    # Margin calculations
    target_margin: Optional[float] = None
    actual_margin: Optional[float] = None
    margin_difference: Optional[float] = None
    
    # Metadata
    calculation_timestamp: datetime = Field(default_factory=datetime.now)
    applied_configs: List[str] = Field(default_factory=list, description="Applied configuration types")
    calculation_notes: Optional[str] = None
    
    def calculate_totals(self):
        """Calculate all totals automatically"""
        # Apply coordination to subtotal
        subtotal_with_coordination = self.subtotal + self.coordination_amount
        
        # Apply discount
        self.total_after_discount = subtotal_with_coordination - self.discount_amount
        
        # Calculate tax base (after discount)
        tax_base = self.total_after_discount
        self.total_before_tax = tax_base
        
        # Apply taxes
        self.total_cost = self.total_before_tax + self.tax_amount
        
        # Calculate cost per person
        if self.cost_per_person_enabled and self.headcount and self.headcount > 0:
            self.cost_per_person = self.total_cost / self.headcount
            
        # Calculate actual margin if target margin is provided
        if self.target_margin is not None and self.total_cost > 0:
            self.actual_margin = (self.total_cost - self.subtotal) / self.total_cost
            self.margin_difference = self.actual_margin - self.target_margin
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ========================
# PRESETS Y PLANTILLAS
# ========================

class PricingPresetModel(BaseModel):
    """Pricing preset model for reusable configurations"""
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    preset_type: str = Field("custom", description="Preset type (catering, events, etc.)")
    
    # Main configuration
    pricing_model: PricingModelEnum = PricingModelEnum.FIXED_PRICE
    
    # Coordination preset settings
    coordination_enabled: bool = False
    coordination_rate: float = Field(0.15, ge=0, le=1)
    coordination_type: CoordinationTypeEnum = CoordinationTypeEnum.PERCENTAGE
    
    # Cost per person preset settings
    cost_per_person_enabled: bool = False
    default_headcount: Optional[int] = Field(None, gt=0)
    headcount_source: HeadcountSourceEnum = HeadcountSourceEnum.MANUAL
    
    # Tax preset settings
    tax_enabled: bool = False
    default_tax_rate: float = Field(0.16, ge=0, le=1)
    default_tax_type: TaxTypeEnum = TaxTypeEnum.IVA
    
    # Discount preset settings
    discount_enabled: bool = False
    default_discount_rate: float = Field(0.0, ge=0, le=1)
    default_discount_type: DiscountTypeEnum = DiscountTypeEnum.PERCENTAGE
    
    # Margin preset settings
    margin_target: float = Field(0.20, ge=0, le=1)
    minimum_margin: float = Field(0.10, ge=0, le=1)
    
    # Metadata
    is_default: bool = False
    usage_count: int = 0
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    created_by: Optional[UUID] = None
    organization_id: Optional[UUID] = None  # Preset can be organization-specific
    
    def to_pricing_configuration(self, project_id: UUID, created_by: UUID) -> PricingConfigurationModel:
        """Convert preset to project pricing configuration"""
        return PricingConfigurationModel(
            project_id=project_id,
            created_by=created_by,
            
            # Copy main settings
            pricing_model=self.pricing_model,
            
            # Copy coordination settings
            coordination_enabled=self.coordination_enabled,
            coordination_rate=self.coordination_rate,
            coordination_type=self.coordination_type,
            
            # Copy cost per person settings
            cost_per_person_enabled=self.cost_per_person_enabled,
                    headcount=self.default_headcount,
            headcount_source=self.headcount_source,
            
            # Copy tax settings
            tax_enabled=self.tax_enabled,
                    tax_rate=self.default_tax_rate,
                    tax_type=self.default_tax_type,
            
            # Copy discount settings
            discount_enabled=self.discount_enabled,
            discount_rate=self.default_discount_rate,
            discount_type=self.default_discount_type,
            
            # Copy margin settings
            margin_target=self.margin_target,
            minimum_margin=self.minimum_margin,
            
            configuration_notes=f"Created from preset: {self.name}"
        )
    
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
    """Request to configure pricing for a project (updated from RFX)"""
    project_id: str = Field(..., min_length=1, description="Project ID (updated from rfx_id)")
    
    # Main configuration
    pricing_model: PricingModelEnum = PricingModelEnum.FIXED_PRICE
    
    # Coordination configuration
    coordination_enabled: bool = False
    coordination_rate: float = Field(0.15, ge=0, le=1)
    coordination_type: CoordinationTypeEnum = CoordinationTypeEnum.PERCENTAGE
    coordination_minimum: Optional[float] = Field(None, ge=0)
    coordination_maximum: Optional[float] = Field(None, ge=0)
    
    # Cost per person configuration
    cost_per_person_enabled: bool = False
    headcount: Optional[int] = Field(None, gt=0)
    headcount_source: HeadcountSourceEnum = HeadcountSourceEnum.MANUAL
    cost_calculation_base: CostCalculationBaseEnum = CostCalculationBaseEnum.TOTAL
    
    # Tax configuration
    tax_enabled: bool = False
    tax_rate: float = Field(0.0, ge=0, le=1)
    tax_type: Optional[TaxTypeEnum] = None
    tax_jurisdiction: Optional[str] = Field(None, max_length=100)
    
    # Discount configuration
    discount_enabled: bool = False
    discount_rate: float = Field(0.0, ge=0, le=1)
    discount_type: Optional[DiscountTypeEnum] = None
    discount_reason: Optional[str] = None
    
    # Margin configuration
    margin_target: float = Field(0.20, ge=0, le=1)
    minimum_margin: float = Field(0.10, ge=0, le=1)
    
    # Use existing preset
    use_preset_id: Optional[str] = None
    
    # Configuration notes
    configuration_notes: Optional[str] = None
    
    @validator('coordination_rate', 'tax_rate', 'discount_rate', 'margin_target', 'minimum_margin')
    def validate_rates(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Rates and margins must be between 0 and 1 (as decimal)')
        return v
    
    @validator('coordination_maximum')
    def validate_coordination_range(cls, v, values):
        if v is not None and 'coordination_minimum' in values and values['coordination_minimum'] is not None:
            if v < values['coordination_minimum']:
                raise ValueError('Coordination maximum must be greater than or equal to minimum')
        return v
    
    class Config:
        use_enum_values = True


class PricingConfigurationResponse(BaseModel):
    """Response for pricing configuration requests"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    data: Optional[PricingConfigurationModel] = None
    calculation: Optional[PricingCalculationModel] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class PricingCalculationRequest(BaseModel):
    """Request for pricing calculation"""
    project_id: str = Field(..., min_length=1)
    subtotal: float = Field(..., ge=0, description="Base subtotal for calculation")
    
    # Optional overrides (if not provided, uses project configuration)
    override_coordination_rate: Optional[float] = Field(None, ge=0, le=1)
    override_headcount: Optional[int] = Field(None, gt=0)
    override_tax_rate: Optional[float] = Field(None, ge=0, le=1)
    override_discount_rate: Optional[float] = Field(None, ge=0, le=1)
    
    class Config:
        use_enum_values = True


class PricingCalculationResponse(BaseModel):
    """Response for pricing calculations"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    calculation: Optional[PricingCalculationModel] = None
    configuration: Optional[PricingConfigurationModel] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class PricingPresetRequest(BaseModel):
    """Request to create or update pricing preset"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    preset_type: str = Field("custom", max_length=50)
    
    # Configuration settings
    pricing_model: PricingModelEnum = PricingModelEnum.FIXED_PRICE
    coordination_enabled: bool = False
    coordination_rate: float = Field(0.15, ge=0, le=1)
    cost_per_person_enabled: bool = False
    default_headcount: Optional[int] = Field(None, gt=0)
    tax_enabled: bool = False
    default_tax_rate: float = Field(0.16, ge=0, le=1)
    default_tax_type: TaxTypeEnum = TaxTypeEnum.IVA
    
    class Config:
        use_enum_values = True


# ========================
# DEFAULT PRESETS
# ========================

def get_default_presets() -> List[PricingPresetModel]:
    """Get default system presets adapted to new schema"""
    return [
        PricingPresetModel(
            name="Catering Básico",
            description="Configuración estándar para catering corporativo",
            preset_type="catering",
            pricing_model=PricingModelEnum.PER_PERSON,
            coordination_enabled=True,
            coordination_rate=0.15,
            coordination_type=CoordinationTypeEnum.PERCENTAGE,
            cost_per_person_enabled=True,
            default_headcount=50,
            is_default=True,
            margin_target=0.20,
            minimum_margin=0.10
        ),
        PricingPresetModel(
            name="Catering Premium",
            description="Configuración premium con coordinación completa",
            preset_type="catering",
            pricing_model=PricingModelEnum.HYBRID,
            coordination_enabled=True,
            coordination_rate=0.18,
            coordination_type=CoordinationTypeEnum.PERCENTAGE,
            cost_per_person_enabled=True,
            default_headcount=120,
            tax_enabled=True,
            default_tax_rate=0.16,
            default_tax_type=TaxTypeEnum.IVA,
            margin_target=0.25,
            minimum_margin=0.15
        ),
        PricingPresetModel(
            name="Eventos Corporativos",
            description="Configuración para eventos y actividades corporativas",
            preset_type="events",
            pricing_model=PricingModelEnum.VALUE_BASED,
            coordination_enabled=True,
            coordination_rate=0.20,
            coordination_type=CoordinationTypeEnum.PERCENTAGE,
            cost_per_person_enabled=True,
            default_headcount=100,
            margin_target=0.30,
            minimum_margin=0.20
        ),
        PricingPresetModel(
            name="Solo Productos",
            description="Sin coordinación, solo productos",
            preset_type="products_only",
            pricing_model=PricingModelEnum.FIXED_PRICE,
            coordination_enabled=False,
            cost_per_person_enabled=False,
            tax_enabled=False,
            margin_target=0.15,
            minimum_margin=0.05
        ),
        PricingPresetModel(
            name="Servicios por Hora",
            description="Configuración para servicios facturados por hora",
            preset_type="hourly_services",
            pricing_model=PricingModelEnum.HOURLY_RATE,
            coordination_enabled=False,
            cost_per_person_enabled=False,
            tax_enabled=True,
            default_tax_rate=0.16,
            default_tax_type=TaxTypeEnum.IVA,
            margin_target=0.40,
            minimum_margin=0.25
        )
    ]


# ========================
# LEGACY COMPATIBILITY
# ========================

# Legacy aliases for backwards compatibility
PricingConfigType = PricingModelEnum  # Map old enum to new one
CoordinationLevel = CoordinationTypeEnum  # Map old enum to new one
RFXPricingConfiguration = PricingConfigurationModel  # Map old model to new one
PricingConfig = PricingConfigurationModel  # Simplified alias
PricingCalculation = PricingCalculationModel  # Map to new calculation model
PricingPreset = PricingPresetModel  # Map to new preset model

# Legacy field mappings for migration
LEGACY_PRICING_MAPPING = {
    'rfx_id': 'project_id',
    'taxes_enabled': 'tax_enabled',
    'config_type': 'pricing_model',
    'is_enabled': 'is_active',
    'config_value': None,  # Flattened in new schema
    'coordination_level': 'coordination_type',
    'per_person_display': None,  # Not used in new schema
    'tax_type': 'tax_type'  # Direct mapping
}

# Helper functions for legacy compatibility
def map_legacy_pricing_request(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map legacy pricing request to new format"""
    mapped = {}
    
    # Direct field mappings
    for old_key, new_key in LEGACY_PRICING_MAPPING.items():
        if old_key in legacy_data and new_key:
            mapped[new_key] = legacy_data[old_key]
    
    # Handle special mappings
    if 'coordination_enabled' in legacy_data:
        mapped['coordination_enabled'] = legacy_data['coordination_enabled']
    
    if 'taxes_enabled' in legacy_data:
        mapped['tax_enabled'] = legacy_data['taxes_enabled']
    
    if 'tax_type' in legacy_data and legacy_data['tax_type']:
        # Map string to enum
        tax_type_str = legacy_data['tax_type'].upper()
        if tax_type_str in ['IVA', 'VAT', 'GST', 'SALES_TAX']:
            mapped['tax_type'] = tax_type_str
    
    return mapped
