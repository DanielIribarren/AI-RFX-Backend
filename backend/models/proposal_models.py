"""
📄 Proposal/Quote Data Models V3.0 - Budy AI Schema Compatible
Updated for new budy-ai-schema.sql structure with quotes and templates tables
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID
from .project_models import ProjectTypeEnum, CurrencyEnum


# ========================
# ENUMS (Aligned with budy-ai-schema.sql)
# ========================

class QuoteStatusEnum(str, Enum):
    """Quote status stages (from budy-ai-schema.sql)"""
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TemplateTypeEnum(str, Enum):
    """Template types (from budy-ai-schema.sql)"""
    QUOTE = "quote"
    PROPOSAL = "proposal"
    INVOICE = "invoice"
    CONTRACT = "contract"


class GenerationMethodEnum(str, Enum):
    """Quote generation methods"""
    AI_ASSISTED = "ai_assisted"
    MANUAL = "manual"
    TEMPLATE_BASED = "template_based"
    HYBRID = "hybrid"


class ServiceModality(str, Enum):
    """Service delivery modalities (legacy support)"""
    BUFFET = "buffet"
    FULL_SERVICE = "full_service"
    SELF_SERVICE = "self_service"
    SIMPLE_DELIVERY = "simple_delivery"


# ========================
# QUOTE COMPONENTS (UPDATED FROM PROPOSAL)
# ========================

class QuoteNotes(BaseModel):
    """Additional notes for quote customization"""
    service_modality: ServiceModality = ServiceModality.BUFFET
    modality_description: str = Field(default="", max_length=500)
    coordination_notes: str = Field(default="", max_length=500)
    payment_terms: str = Field(default="", max_length=1000)
    terms_and_conditions: str = Field(default="", max_length=2000)
    additional_notes: str = Field(default="", max_length=1000)

    class Config:
        use_enum_values = True


class ItemizedCost(BaseModel):
    """Individual item cost in quote (updated from ProductCost)"""
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    total_price: float = Field(..., ge=0)
    
    # Additional fields aligned with project_items
    unit_of_measure: str = Field("pieces", max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    notes: Optional[str] = None
    
    # Source information
    is_optional: bool = False
    extracted_from_ai: bool = False

    @validator('total_price')
    def validate_total_price(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            expected = values['quantity'] * values['unit_price']
            if abs(v - expected) > 0.01:  # 1 cent tolerance
                raise ValueError('Total price does not match quantity × unit price')
        return v

    @validator('item_name')
    def validate_item_name(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True


# ========================
# REQUEST MODELS
# ========================

class QuoteRequest(BaseModel):
    """
    🎯 UNIFIED Quote Request Model
    Consolidates ProposalRequest + QuoteRequest with backward compatibility
    """
    # Core identification (supporting both project_id and rfx_id)
    project_id: str = Field(..., min_length=1, description="Project/RFX ID")
    organization_id: Optional[str] = Field(None, min_length=1, description="Organization ID")
    template_id: Optional[str] = Field(None, description="Template ID to use")
    
    # Quote content
    title: str = Field(..., min_length=1, max_length=255, description="Quote title")
    description: Optional[str] = Field(None, max_length=2000)
    
    # Cost information (unified from both models)
    itemized_costs: List[ItemizedCost] = Field(default_factory=list, description="Itemized cost breakdown")
    item_costs: List[ItemizedCost] = Field(default_factory=list, description="Legacy alias for itemized_costs")
    subtotal: float = Field(..., ge=0, description="Subtotal before taxes/coordination")
    coordination_amount: float = Field(0.0, ge=0, description="Coordination fee amount")
    tax_amount: float = Field(0.0, ge=0, description="Tax amount")
    discount_amount: float = Field(0.0, ge=0, description="Discount amount")
    total_amount: float = Field(..., ge=0, description="Final total amount")
    currency: CurrencyEnum = CurrencyEnum.USD
    
    # Quote metadata and notes
    notes: Optional[QuoteNotes] = Field(default_factory=QuoteNotes, description="Additional notes")
    generation_method: GenerationMethodEnum = GenerationMethodEnum.AI_ASSISTED
    version: int = Field(1, description="Quote version number")
    
    # Business terms
    payment_terms: Optional[str] = Field(None, max_length=1000, description="Payment terms")
    terms_and_conditions: Optional[str] = Field(None, max_length=2000, description="Terms and conditions")
    valid_until: Optional[datetime] = Field(None, description="Quote validity date")
    
    # Generation options
    include_itemized_costs: bool = Field(True, description="Include itemized cost breakdown")
    include_terms_conditions: bool = Field(True, description="Include terms and conditions")
    custom_template_content: Optional[str] = Field(None, max_length=10000, description="Custom template content")
    
    # Legacy compatibility properties
    @property
    def rfx_id(self) -> str:
        """Legacy compatibility: rfx_id → project_id"""
        return self.project_id
    
    @rfx_id.setter
    def rfx_id(self, value: str):
        """Legacy compatibility: rfx_id ← project_id"""
        self.project_id = value
    
    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        """Validate that total_amount matches calculated total"""
        if all(key in values for key in ['subtotal', 'coordination_amount', 'tax_amount', 'discount_amount']):
            expected = values['subtotal'] + values['coordination_amount'] + values['tax_amount'] - values['discount_amount']
            if abs(v - expected) > 0.01:  # 1 cent tolerance
                raise ValueError('Total amount does not match calculated total')
        return v
    
    @validator('item_costs', always=True)
    def sync_item_costs(cls, v, values):
        """Sync item_costs with itemized_costs for backward compatibility"""
        if not v and 'itemized_costs' in values and values['itemized_costs']:
            return values['itemized_costs']
        elif v and not values.get('itemized_costs'):
            # Update itemized_costs if item_costs is provided
            values['itemized_costs'] = v
        return v
    
    @validator('itemized_costs', always=True)
    def sync_itemized_costs(cls, v, values):
        """Sync itemized_costs with item_costs for backward compatibility"""
        if not v and 'item_costs' in values and values['item_costs']:
            return values['item_costs']
        elif v and not values.get('item_costs'):
            # Update item_costs if itemized_costs is provided
            values['item_costs'] = v
        return v

    @validator('title')
    def validate_title(cls, v):
        """Clean and validate title"""
        return v.strip() if v else v

    class Config:
        use_enum_values = True


# ========================
# MAIN QUOTE MODEL (UPDATED FROM GENERATED PROPOSAL)
# ========================

class QuoteModel(BaseModel):
    """Main quote model aligned with budy-ai-schema.sql quotes table"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID (updated from rfx_id)")
    organization_id: UUID = Field(..., description="Organization ID")
    template_id: Optional[UUID] = Field(None, description="Template used")
    
    # Quote identification
    quote_number: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Z0-9-]+$')
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: QuoteStatusEnum = QuoteStatusEnum.DRAFT
    version: int = 1
    
    # Financial information
    subtotal: float = Field(..., ge=0)
    coordination_amount: float = Field(0.0, ge=0)
    tax_amount: float = Field(0.0, ge=0)
    discount_amount: float = Field(0.0, ge=0)
    total_amount: float = Field(..., ge=0)
    currency: CurrencyEnum = CurrencyEnum.USD
    
    # Snapshots for audit trail
    pricing_config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    items_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Generated content
    html_content: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_size_bytes: Optional[int] = Field(None, gt=0)
    
    # Generation metadata
    generation_method: GenerationMethodEnum = GenerationMethodEnum.AI_ASSISTED
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    generation_duration_seconds: Optional[int] = Field(None, gt=0)
    tokens_used: int = 0
    
    # Business terms
    valid_until: Optional[datetime] = None
    payment_terms: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    
    # Interaction tracking
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    
    # Control
    created_by: UUID = Field(..., description="User ID who created the quote")
    sent_by: Optional[UUID] = Field(None, description="User ID who sent the quote")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator('quote_number')
    def validate_quote_number(cls, v):
        return v.strip().upper() if v else v

    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v

    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        # Verify total matches components
        if all(key in values for key in ['subtotal', 'coordination_amount', 'tax_amount', 'discount_amount']):
            expected = values['subtotal'] + values['coordination_amount'] + values['tax_amount'] - values['discount_amount']
            if abs(v - expected) > 0.01:  # 1 cent tolerance
                raise ValueError('Total amount does not match calculated total')
        return v

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class QuoteResponse(BaseModel):
    """Standard response for quote endpoints (updated from ProposalResponse)"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    quote_id: Optional[UUID] = None
    quote_number: Optional[str] = None
    pdf_url: Optional[str] = None
    quote: Optional[QuoteModel] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class QuoteListResponse(BaseModel):
    """Response for quote list endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    quotes: List[QuoteModel] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    limit: int = 50
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# DOCUMENT MANAGEMENT
# ========================

class GeneratedDocument(BaseModel):
    """PDF/Document generated and stored"""
    id: UUID
    rfx_id: UUID
    document_type: str = "commercial_proposal"
    file_name: str
    download_url: str
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    
    # File metadata
    file_size_bytes: Optional[int] = None
    mime_type: str = "application/pdf"
    
    # Access control
    created_at: datetime = Field(default_factory=datetime.now)
    expiration_date: Optional[datetime] = None
    downloaded: bool = False
    download_count: int = 0
    
    # V2.0 additions
    version: int = 1
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# COST CALCULATION MODELS (DEPRECATED)
# ========================

# NOTE: CostBreakdown removed - its functionality is now covered by 
# PricingCalculationModel in pricing_models.py for better separation of concerns


# ========================
# TEMPLATE MODELS (ALIGNED WITH BUDY-AI-SCHEMA)
# ========================

class TemplateModel(BaseModel):
    """Template model aligned with budy-ai-schema.sql templates table"""
    id: Optional[UUID] = None
    organization_id: UUID = Field(..., description="Organization ID")
    
    # Template information
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_type: TemplateTypeEnum = TemplateTypeEnum.QUOTE
    
    # Configuration
    project_types: List[ProjectTypeEnum] = Field(default_factory=list, description="Applicable project types")
    is_default: bool = False
    is_active: bool = True
    
    # Content
    html_content: str = Field(..., min_length=1, description="Template HTML content")
    css_styles: Optional[str] = None
    javascript_code: Optional[str] = None
    
    # Layout and design
    layout_structure: Dict[str, Any] = Field(default_factory=dict)
    design_settings: Dict[str, Any] = Field(default_factory=dict)
    responsive_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Customization
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    branding_options: Dict[str, Any] = Field(default_factory=dict)
    color_scheme: Dict[str, Any] = Field(default_factory=dict)
    
    # Usage tracking
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    
    # Control
    created_by: UUID = Field(..., description="User ID who created the template")
    updated_by: Optional[UUID] = Field(None, description="User ID who last updated the template")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator('name')
    def validate_name(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TemplateRequest(BaseModel):
    """Request to create or update a template"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_type: TemplateTypeEnum = TemplateTypeEnum.QUOTE
    
    # Content
    html_content: str = Field(..., min_length=1)
    css_styles: Optional[str] = None
    
    # Configuration
    project_types: List[ProjectTypeEnum] = Field(default_factory=list)
    is_default: bool = False
    is_active: bool = True
    
    # Customization
    branding_options: Dict[str, Any] = Field(default_factory=dict)
    color_scheme: Dict[str, Any] = Field(default_factory=dict)

    @validator('name')
    def validate_name(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True


class TemplateResponse(BaseModel):
    """Response for template endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    template: Optional[TemplateModel] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# LEGACY COMPATIBILITY & ALIASES
# ========================

# IMPORTANT: Legacy aliases for backward compatibility during migration
# These ensure existing code continues working with new models

# Direct model aliases (new -> old mappings for external use)
ProposalRequest = QuoteRequest
GeneratedProposal = QuoteModel
ProposalResponse = QuoteResponse
ProductCost = ItemizedCost
ProposalNotes = QuoteNotes
ProposalStatus = QuoteStatusEnum
ProposalTemplate = TemplateModel

# Legacy Spanish names for backward compatibility (common in existing codebase)
TipoModalidad = ServiceModality  # Spanish for ServiceModality
EstadoPropuesta = QuoteStatusEnum  # Spanish for QuoteStatusEnum
NotasPropuesta = QuoteNotes   # Spanish for QuoteNotes
CostoProducto = ItemizedCost      # Spanish for ItemizedCost
PropuestaGenerada = QuoteModel  # Spanish for QuoteModel
SolicitudPropuesta = QuoteRequest  # Spanish for QuoteRequest
RespuestaPropuesta = QuoteResponse  # Spanish for QuoteResponse
DocumentoGenerado = QuoteModel  # Spanish for QuoteModel (old GeneratedDocument concept now in QuoteModel)


# Helper function to map legacy proposal status values
def map_legacy_proposal_status(status_value: str) -> QuoteStatusEnum:
    """Map legacy Spanish status values to new enum values"""
    legacy_mapping = {
        'borrador': QuoteStatusEnum.DRAFT,
        'generada': QuoteStatusEnum.GENERATED,
        'enviada': QuoteStatusEnum.SENT,
        'vista': QuoteStatusEnum.VIEWED,
        'aceptada': QuoteStatusEnum.ACCEPTED,
        'rechazada': QuoteStatusEnum.REJECTED,
        'expirada': QuoteStatusEnum.EXPIRED,
        'cancelada': QuoteStatusEnum.CANCELLED,
        # English mappings too
        'draft': QuoteStatusEnum.DRAFT,
        'generated': QuoteStatusEnum.GENERATED,
        'sent': QuoteStatusEnum.SENT,
        'viewed': QuoteStatusEnum.VIEWED,
        'accepted': QuoteStatusEnum.ACCEPTED,
        'rejected': QuoteStatusEnum.REJECTED,
        'expired': QuoteStatusEnum.EXPIRED,
        'cancelled': QuoteStatusEnum.CANCELLED
    }
    return legacy_mapping.get(status_value.lower(), QuoteStatusEnum.DRAFT)


def map_legacy_quote_request(legacy_data: Dict[str, Any]) -> QuoteRequest:
    """Map legacy proposal request data to QuoteRequest"""
    mapped_data = legacy_data.copy()
    
    # Handle RFX -> Project mapping
    if 'rfx_id' in legacy_data and 'project_id' not in legacy_data:
        mapped_data['project_id'] = legacy_data['rfx_id']
    
    # Handle company -> organization mapping
    if 'company_id' in legacy_data:
        mapped_data['organization_id'] = legacy_data['company_id']
    
    # Handle status mapping
    if 'estado' in legacy_data:
        mapped_data['status'] = map_legacy_proposal_status(legacy_data['estado'])
    elif 'status' in legacy_data:
        mapped_data['status'] = map_legacy_proposal_status(legacy_data['status'])
    
    # Handle products -> items mapping
    if 'products' in legacy_data:
        mapped_data['itemized_costs'] = []
        for product in legacy_data['products']:
            item_cost = {
                'item_name': product.get('name', product.get('nombre', '')),
                'description': product.get('description', product.get('descripcion', '')),
                'unit_of_measure': product.get('unit', product.get('unidad', 'unidad')),
                'quantity': product.get('quantity', product.get('cantidad', 1)),
                'unit_price': product.get('unit_price', product.get('precio_unitario', 0)),
                'total_price': product.get('total_cost', product.get('costo_total', 0))
            }
            mapped_data['itemized_costs'].append(item_cost)
    
    # Legacy field mappings for Spanish -> English
    field_mapping = {
        'modalidad': 'service_modality',
        'notas_adicionales': 'notes',
        'costo_total': 'total_amount',
        'fecha_validez': 'valid_until',
        'terminos_pago': 'payment_terms',
        'terminos_condiciones': 'terms_and_conditions'
    }
    
    for old_field, new_field in field_mapping.items():
        if old_field in legacy_data:
            mapped_data[new_field] = legacy_data[old_field]
    
    # Copy other fields as-is
    common_fields = [
        'notes', 'service_modality', 'subtotal', 'coordination_amount',
        'tax_amount', 'discount_amount', 'total_amount', 'currency',
        'valid_until', 'payment_terms', 'terms_and_conditions'
    ]
    
    for field in common_fields:
        if field in legacy_data:
            mapped_data[field] = legacy_data[field]
    
    # Create and return QuoteRequest instance
    return QuoteRequest(**mapped_data)

# ========================
# LEGACY ALIASES FOR BACKWARD COMPATIBILITY
# ========================

# Legacy class aliases to maintain import compatibility
ProposalRequest = QuoteRequest
PropuestaGenerada = QuoteModel

# Legacy notes alias
NotasPropuesta = QuoteNotes

# Legacy response models for backward compatibility
class ProposalResponse(BaseModel):
    """Legacy Proposal Response wrapper"""
    status: str = "success"
    data: Optional[QuoteModel] = None
    message: Optional[str] = None
    error: Optional[str] = None

class QuoteResponse(BaseModel):
    """Modern Quote Response"""
    status: str = "success"
    data: Optional[QuoteModel] = None
    message: Optional[str] = None
    error: Optional[str] = None