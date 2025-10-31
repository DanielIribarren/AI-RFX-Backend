"""
🎯 RFX Data Models V2.0 - English Schema Compatible
Fully updated for new normalized database structure
"""
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID


# ========================
# ENUMS (English)
# ========================

class RFXType(str, Enum):
    """RFX types/categories"""
    CATERING = "catering"
    EVENTS = "events"
    SUPPLIES = "supplies"
    SERVICES = "services"
    CONSTRUCTION = "construction"
    MAINTENANCE = "maintenance"


class RFXStatus(str, Enum):
    """RFX processing status"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PriorityLevel(str, Enum):
    """Priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DocumentType(str, Enum):
    """Generated document types"""
    PROPOSAL = "proposal"
    QUOTE = "quote"
    CONTRACT = "contract"
    INVOICE = "invoice"


# ========================
# CORE ENTITY MODELS
# ========================

class CompanyModel(BaseModel):
    """Company/Client organization model"""
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(None, pattern=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

    class Config:
        use_enum_values = True


class RequesterModel(BaseModel):
    """Individual requester within a company"""
    id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(None, pattern=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    is_primary_contact: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

    class Config:
        use_enum_values = True


class SupplierModel(BaseModel):
    """Supplier/Vendor model"""
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=200)
    contact_person: Optional[str] = None
    email: Optional[str] = Field(None, pattern=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
    phone: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    delivery_time: Optional[str] = None
    payment_terms: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    is_active: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ========================
# PRODUCT MODELS
# ========================

class ProductCatalogItem(BaseModel):
    """Product catalog item from suppliers"""
    id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    sku: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = Field(None, ge=0)
    unit: str = Field(..., min_length=1, max_length=50)
    minimum_quantity: int = Field(1, ge=1)
    is_active: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

    @validator('unit')
    def validate_unit(cls, v):
        return v.strip().lower()

    class Config:
        use_enum_values = True


class RFXProductRequest(BaseModel):
    """Individual product request within an RFX"""
    id: Optional[UUID] = None
    rfx_id: Optional[UUID] = None
    product_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    quantity: int = Field(..., ge=1)
    unit: str = Field(..., min_length=1, max_length=50)
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    unit_cost: Optional[float] = Field(None, ge=0)  # Costo del proveedor ⭐ NUEVO
    precio_unitario: Optional[float] = Field(None, ge=0)  # Alias para compatibilidad con extracción
    costo_unitario: Optional[float] = Field(None, ge=0)  # Alias para compatibilidad con extracción ⭐ NUEVO
    total_estimated_cost: Optional[float] = Field(None, ge=0)
    supplier_id: Optional[UUID] = None
    catalog_product_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    @validator('product_name')
    def validate_name(cls, v):
        return v.strip()

    @validator('unit')
    def validate_unit(cls, v):
        return v.strip().lower()

    class Config:
        use_enum_values = True


# ========================
# MAIN RFX MODELS
# ========================

class RFXInput(BaseModel):
    """Input data for processing an RFX"""
    id: str = Field(..., min_length=1)
    rfx_type: RFXType = RFXType.CATERING
    pdf_url: Optional[str] = None
    extracted_content: Optional[str] = None
    # 🆕 MVP: Campo opcional para requirements específicos del cliente
    requirements: Optional[str] = Field(None, max_length=2000, description="Specific client requirements or instructions")

    class Config:
        use_enum_values = True


class RFXProcessed(BaseModel):
    """Processed RFX data (output from processing)"""
    id: UUID
    company_id: Optional[UUID] = None
    requester_id: Optional[UUID] = None
    rfx_type: RFXType = RFXType.CATERING
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=300)
    delivery_date: Optional[date] = None
    delivery_time: Optional[time] = None
    estimated_budget: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    status: RFXStatus = RFXStatus.IN_PROGRESS
    priority: PriorityLevel = PriorityLevel.MEDIUM
    
    # Original document data
    original_pdf_text: Optional[str] = None
    requested_products: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    
    # Processing metadata
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    processing_notes: Optional[str] = None
    
    # 🆕 MVP: Requirements específicos del cliente extraídos por IA
    requirements: Optional[str] = Field(None, max_length=2000, description="Client-specific requirements extracted from document")
    requirements_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence score for requirements extraction")
    
    # Timestamps
    received_at: Optional[datetime] = Field(default_factory=datetime.now)
    deadline: Optional[date] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    # Extracted entity data (for compatibility)
    email: Optional[str] = None
    requester_name: Optional[str] = None  # Updated from nombre_solicitante
    company_name: Optional[str] = None
    products: Optional[List[RFXProductRequest]] = Field(default_factory=list)

    @validator('location')
    def validate_location(cls, v):
        if v:
            return v.strip()
        return v

    @validator('title')
    def validate_title(cls, v):
        if v:
            return v.strip()
        return v

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class RFXResponse(BaseModel):
    """Standard response for RFX endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    data: Optional[RFXProcessed] = None
    proposal_id: Optional[str] = None
    proposal_url: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class RFXHistoryItem(BaseModel):
    """RFX history list item"""
    id: UUID
    company_id: Optional[UUID] = None
    requester_id: Optional[UUID] = None
    company_name: Optional[str] = None
    requester_name: Optional[str] = None
    rfx_type: RFXType
    title: Optional[str] = None
    status: RFXStatus
    priority: PriorityLevel = PriorityLevel.MEDIUM
    estimated_budget: Optional[float] = None
    actual_cost: Optional[float] = None
    received_at: Optional[datetime] = None
    delivery_date: Optional[date] = None
    location: Optional[str] = None
    product_count: int = 0
    
    # Legacy compatibility fields
    cliente_id: Optional[str] = None  # For backwards compatibility
    nombre_solicitante: Optional[str] = None  # For backwards compatibility
    pdf_url: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# DOCUMENT MODELS
# ========================

class GeneratedDocument(BaseModel):
    """Generated document (proposal, quote, etc.)"""
    id: Optional[UUID] = None
    rfx_id: UUID
    document_type: DocumentType = DocumentType.PROPOSAL
    version: int = 1
    title: Optional[str] = None
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    
    # Cost breakdown
    itemized_costs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    subtotal: Optional[float] = Field(None, ge=0)
    tax_amount: Optional[float] = Field(None, ge=0)
    total_cost: Optional[float] = Field(None, ge=0)
    
    # Document metadata
    template_used: Optional[str] = None
    generated_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # File storage
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# HISTORY & AUDIT MODELS
# ========================

class RFXHistoryEvent(BaseModel):
    """RFX history/audit event"""
    id: Optional[UUID] = None
    rfx_id: UUID
    event_type: str
    description: str
    old_values: Optional[Dict[str, Any]] = Field(default_factory=dict)
    new_values: Optional[Dict[str, Any]] = Field(default_factory=dict)
    performed_by: Optional[str] = None
    performed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class SupplierEvaluation(BaseModel):
    """Supplier performance evaluation"""
    id: Optional[UUID] = None
    supplier_id: UUID
    rfx_id: Optional[UUID] = None
    evaluator_name: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    delivery_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    service_rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    would_recommend: Optional[bool] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ========================
# PAGINATION MODELS
# ========================

class PaginationInfo(BaseModel):
    """Pagination information for API responses"""
    page: Optional[int] = None
    limit: int = 10
    offset: int = 0
    total_items: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RFXListResponse(BaseModel):
    """Response model for RFX list endpoints with pagination"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    data: List[RFXHistoryItem] = Field(default_factory=list)
    pagination: PaginationInfo
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class LoadMoreRequest(BaseModel):
    """Request model for load-more pagination"""
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=10, ge=1, le=50, description="Number of items to retrieve")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 50:
            raise ValueError('Limit cannot exceed 50 items')
        return v


# ========================
# LEGACY COMPATIBILITY
# ========================

# Keep legacy aliases for backwards compatibility
TipoRFX = RFXType
EstadoRFX = RFXStatus
ProductoRFX = RFXProductRequest

# Legacy field mappings for migration
LEGACY_FIELD_MAPPING = {
    'nombre_solicitante': 'requester_name',
    'nombre_cliente': 'requester_name', 
    'tipo': 'rfx_type',
    'estado': 'status',
    'fecha': 'delivery_date',
    'hora_entrega': 'delivery_time',
    'lugar': 'location',
    'productos': 'products',
    'fecha_recepcion': 'received_at',
    'metadatos': 'metadata_json'
}