"""
🧠 AI Learning System - Pydantic Models
Validación estricta de datos para tools de LangChain
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# INPUT MODELS (para tools)
# ============================================

class GetPricingPreferenceInput(BaseModel):
    """Input para get_pricing_preference_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    rfx_type: Optional[str] = Field(None, description="Tipo de RFX")


class GetFrequentProductsInput(BaseModel):
    """Input para get_frequent_products_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    rfx_type: Optional[str] = Field(None, description="Tipo de RFX")
    limit: int = Field(10, ge=1, le=50, description="Número máximo de productos")


class SavePricingPreferenceInput(BaseModel):
    """Input para save_pricing_preference_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    coordination_enabled: bool = Field(..., description="Si coordinación está habilitada")
    coordination_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Tasa de coordinación")
    taxes_enabled: bool = Field(..., description="Si impuestos están habilitados")
    tax_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Tasa de impuestos")
    cost_per_person_enabled: bool = Field(..., description="Si costo por persona está habilitado")
    rfx_type: Optional[str] = Field(None, description="Tipo de RFX")


class SaveProductUsageInput(BaseModel):
    """Input para save_product_usage_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    product_name: str = Field(..., min_length=1, description="Nombre del producto")
    quantity: int = Field(..., gt=0, description="Cantidad usada")
    unit_price: float = Field(..., ge=0, description="Precio unitario")
    unit_cost: float = Field(..., ge=0, description="Costo unitario")
    rfx_type: Optional[str] = Field(None, description="Tipo de RFX")


class SavePriceCorrectionInput(BaseModel):
    """Input para save_price_correction_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    product_name: str = Field(..., min_length=1, description="Nombre del producto")
    original_price: float = Field(..., gt=0, description="Precio original")
    corrected_price: float = Field(..., gt=0, description="Precio corregido")
    rfx_id: str = Field(..., description="UUID del RFX")

    @validator('corrected_price')
    def validate_price_change(cls, v, values):
        """Validar que el cambio sea significativo (>5%)"""
        if 'original_price' in values:
            original = values['original_price']
            diff = abs(v - original)
            percentage = diff / original
            if percentage < 0.05:  # 5% threshold
                raise ValueError(f"Price change must be >5% (current: {percentage*100:.1f}%)")
        return v


class LogLearningEventInput(BaseModel):
    """Input para log_learning_event_tool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    event_type: str = Field(..., description="Tipo de evento")
    rfx_id: str = Field(..., description="UUID del RFX")
    context: Dict[str, Any] = Field(..., description="Contexto del evento")
    action_taken: Dict[str, Any] = Field(..., description="Acción tomada")


# ============================================
# OUTPUT MODELS
# ============================================

class PricingPreference(BaseModel):
    """Preferencia de pricing aprendida"""
    coordination_enabled: bool
    coordination_rate: float
    taxes_enabled: bool
    tax_rate: float
    cost_per_person_enabled: bool
    confidence: float
    usage_count: int
    last_used: Optional[str]
    source: str = "learned"  # "learned" o "default"


class FrequentProduct(BaseModel):
    """Producto frecuente"""
    product_name: str
    frequency: int
    avg_quantity: float
    last_price: float
    last_cost: float
    confidence: float


class LearnedContext(BaseModel):
    """Contexto completo aprendido para un usuario"""
    pricing: PricingPreference
    suggested_products: List[FrequentProduct]
    overall_confidence: float


class LearningResult(BaseModel):
    """Resultado del proceso de aprendizaje"""
    success: bool
    learned: Dict[str, Any]
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
