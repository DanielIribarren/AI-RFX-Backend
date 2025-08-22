"""
📄 Proposal Data Models V2.0 - English Schema Compatible
Updated for new normalized database structure
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID
from .rfx_models import DocumentType


# ========================
# ENUMS (English)
# ========================

class ServiceModality(str, Enum):
    """Service delivery modalities"""
    BUFFET = "buffet"
    FULL_SERVICE = "full_service"
    SELF_SERVICE = "self_service"
    SIMPLE_DELIVERY = "simple_delivery"


class ProposalStatus(str, Enum):
    """Proposal status stages"""
    DRAFT = "draft"
    GENERATED = "generated"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ========================
# PROPOSAL COMPONENTS
# ========================

class ProposalNotes(BaseModel):
    """Additional notes for proposal customization"""
    modality: ServiceModality = ServiceModality.BUFFET
    modality_description: str = Field(default="", max_length=500)
    coordination: str = Field(default="", max_length=500)
    additional_notes: str = Field(default="", max_length=1000)

    class Config:
        use_enum_values = True


class ProductCost(BaseModel):
    """Individual product cost in proposal"""
    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    subtotal: float = Field(..., ge=0)
    
    # New fields for V2.0
    unit: Optional[str] = "piece"
    category: Optional[str] = None
    supplier_name: Optional[str] = None
    notes: Optional[str] = None

    @validator('subtotal')
    def validate_subtotal(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            expected = values['quantity'] * values['unit_price']
            if abs(v - expected) > 0.01:  # 1 cent tolerance
                raise ValueError('Subtotal does not match quantity × unit price')
        return v

    @validator('product_name')
    def validate_product_name(cls, v):
        return v.strip()

    class Config:
        use_enum_values = True


# ========================
# REQUEST MODELS
# ========================

class ProposalRequest(BaseModel):
    """Request to generate a proposal"""
    rfx_id: str = Field(..., min_length=1)
    costs: List[float] = Field(..., min_items=1)
    history: str = Field(default="", max_length=2000)
    notes: Optional[ProposalNotes] = Field(default_factory=ProposalNotes)
    custom_template: Optional[str] = Field(None, max_length=5000)
    
    # New V2.0 fields
    document_type: DocumentType = DocumentType.PROPOSAL
    version: int = 1
    include_itemized_costs: bool = True
    include_terms_conditions: bool = True

    @validator('costs')
    def validate_costs(cls, v):
        if any(cost < 0 for cost in v):
            raise ValueError('Costs must be positive')
        return v

    class Config:
        use_enum_values = True


# ========================
# RESPONSE MODELS
# ========================

class GeneratedProposal(BaseModel):
    """Generated proposal with V2.0 architecture - HTML is primary"""
    id: UUID
    rfx_id: UUID
    document_type: DocumentType = DocumentType.PROPOSAL
    version: int = 1
    title: Optional[str] = None
    
    # Content (HTML is primary)
    content_html: str = Field(..., min_length=1)
    content_markdown: Optional[str] = None  # Optional, legacy support
    
    # Cost breakdown
    itemized_costs: Optional[List[ProductCost]] = Field(default_factory=list)
    subtotal: Optional[float] = Field(None, ge=0)
    tax_amount: Optional[float] = Field(None, ge=0)
    total_cost: float = Field(default=0.0, ge=0)
    
    # Proposal metadata
    notes: Optional[ProposalNotes] = Field(default_factory=ProposalNotes)
    status: ProposalStatus = ProposalStatus.GENERATED
    template_used: Optional[str] = None

    
    # File handling
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    pdf_url: Optional[str] = None  # Legacy compatibility
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ProposalResponse(BaseModel):
    """Standard response for proposal endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    document_id: Optional[UUID] = None
    pdf_url: Optional[str] = None
    proposal: Optional[GeneratedProposal] = None
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
# COST CALCULATION MODELS
# ========================

class CostBreakdown(BaseModel):
    """Detailed cost breakdown for proposals"""
    products: List[ProductCost] = Field(default_factory=list)
    subtotal: float = Field(0.0, ge=0)
    
    # Tax and fees
    tax_rate: float = Field(0.0, ge=0, le=1)  # As decimal (e.g., 0.16 for 16%)
    tax_amount: float = Field(0.0, ge=0)
    service_fee: float = Field(0.0, ge=0)
    delivery_fee: float = Field(0.0, ge=0)
    
    # Discounts
    discount_percentage: float = Field(0.0, ge=0, le=1)
    discount_amount: float = Field(0.0, ge=0)
    
    # Final totals
    total_before_tax: float = Field(0.0, ge=0)
    total_cost: float = Field(0.0, ge=0)
    
    # Additional info
    currency: str = "USD"
    notes: Optional[str] = None

    @validator('tax_amount')
    def validate_tax_amount(cls, v, values):
        if 'subtotal' in values and 'tax_rate' in values:
            expected = values['subtotal'] * values['tax_rate']
            if abs(v - expected) > 0.01:
                raise ValueError('Tax amount does not match subtotal × tax rate')
        return v

    class Config:
        use_enum_values = True


# ========================
# TEMPLATE MODELS
# ========================

class ProposalTemplate(BaseModel):
    """Proposal template definition"""
    id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    template_html: str = Field(..., min_length=1)
    template_variables: List[str] = Field(default_factory=list)
    
    # Template metadata
    category: Optional[str] = None  # e.g., "catering", "events"
    is_active: bool = True
    is_default: bool = False
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# LEGACY COMPATIBILITY
# ========================

# Keep legacy aliases for backwards compatibility
TipoModalidad = ServiceModality
EstadoPropuesta = ProposalStatus
NotasPropuesta = ProposalNotes
CostoProducto = ProductCost
PropuestaGenerada = GeneratedProposal
DocumentoGenerado = GeneratedDocument

# Legacy field mappings
LEGACY_PROPOSAL_MAPPING = {
    'modalidad': 'modality',
    'descripcion_modalidad': 'modality_description',
    'coordinacion': 'coordination',
    'notas_adicionales': 'additional_notes',
    'producto_nombre': 'product_name',
    'precio_unitario': 'unit_price',
    'contenido_html': 'content_html',
    'contenido_markdown': 'content_markdown',
    'costos_desglosados': 'itemized_costs',
    'costo_total': 'total_cost',
    'fecha_creacion': 'created_at',
    'fecha_actualizacion': 'updated_at',
    'url_pdf': 'pdf_url',
    'metadatos': 'metadata',
    'documento_id': 'document_id',
    'nombre_archivo': 'file_name',
    'url_descarga': 'download_url',
    'tamaño_bytes': 'file_size_bytes',
    'fecha_expiracion': 'expiration_date',
    'descargado': 'downloaded',
    'numero_descargas': 'download_count'
}