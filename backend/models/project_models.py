"""
📋 Project Data Models V3.0 - Budy AI Schema Compatible  
Fully adapted to the new budy-ai-schema.sql normalized structure
"""
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID


# ========================
# ENUMS (Aligned with budy-ai-schema.sql)
# ========================

class PlanTypeEnum(str, Enum):
    """Organization subscription plans"""
    FREE = "free"
    BASIC = "basic" 
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class CurrencyEnum(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    MXN = "MXN"
    COP = "COP"
    PEN = "PEN"
    CLP = "CLP"
    VES = "VES"


class UserRoleEnum(str, Enum):
    """User roles in organizations"""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"
    GUEST = "guest"


class MembershipStatusEnum(str, Enum):
    """User membership status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class ProjectTypeEnum(str, Enum):
    """Project types/categories"""
    CATERING = "catering"
    CONSULTING = "consulting"
    CONSTRUCTION = "construction"
    EVENTS = "events"
    MARKETING = "marketing"
    TECHNOLOGY = "technology"
    GENERAL = "general"


class ProjectStatusEnum(str, Enum):
    """Project status stages"""
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class PricingModelEnum(str, Enum):
    """Pricing calculation models"""
    PER_PERSON = "per_person"
    FIXED_PRICE = "fixed_price"
    HOURLY_RATE = "hourly_rate"
    PER_UNIT = "per_unit"
    PERCENTAGE_BASED = "percentage_based"
    TIERED_PRICING = "tiered_pricing"
    VALUE_BASED = "value_based"
    HYBRID = "hybrid"


class BudgetRangeEnum(str, Enum):
    """Budget size categories"""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"
    MEGA = "mega"


class ClientTypeEnum(str, Enum):
    """Client organization types"""
    INDIVIDUAL = "individual"
    STARTUP = "startup"
    SMALL_BUSINESS = "small_business"
    MEDIUM_BUSINESS = "medium_business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"


class WorkflowStageEnum(str, Enum):
    """Workflow processing stages"""
    DOCUMENT_UPLOADED = "document_uploaded"
    CONTEXT_ANALYSIS = "context_analysis"
    INTELLIGENT_EXTRACTION = "intelligent_extraction"
    HUMAN_REVIEW = "human_review"
    CONFIGURATION_SETUP = "configuration_setup"
    QUOTE_GENERATION = "quote_generation"
    QUALITY_CHECK = "quality_check"
    READY_FOR_DELIVERY = "ready_for_delivery"


class DocumentTypeEnum(str, Enum):
    """Document types"""
    RFP = "rfp"
    REQUIREMENTS = "requirements"
    SPECIFICATION = "specification"
    BRIEF = "brief"
    CONTRACT = "contract"
    REFERENCE = "reference"
    ATTACHMENT = "attachment"


class QuoteStatusEnum(str, Enum):
    """Quote status stages"""
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ========================
# ORGANIZATION MODELS
# ========================

class OrganizationModel(BaseModel):
    """Organization/Company model (updated from CompanyModel)"""
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$')
    
    # Plan and limits
    plan_type: PlanTypeEnum = PlanTypeEnum.FREE
    monthly_projects_limit: int = Field(3, gt=0)
    documents_per_project_limit: int = Field(2, gt=0)
    users_limit: int = Field(1, gt=0)
    
    # Configuration
    default_currency: CurrencyEnum = CurrencyEnum.USD
    timezone: str = Field("UTC", max_length=50)
    business_sector: Optional[str] = Field(None, max_length=100)
    company_size: Optional[int] = Field(None, gt=0)
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    language_preference: str = Field("es", max_length=10)
    
    # Status
    is_active: bool = True
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @validator('name', 'slug')
    def validate_strings(cls, v):
        return v.strip() if v else v

    @validator('slug')
    def validate_slug_format(cls, v):
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters and hyphens')
        return v.lower() if v else v

    class Config:
        use_enum_values = True


# ========================
# USER MODELS  
# ========================

class UserModel(BaseModel):
    """User model (updated from RequesterModel)"""
    id: Optional[UUID] = None
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password_hash: Optional[str] = None
    
    # Personal information
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=100)
    
    # Preferences
    language_preference: str = Field("es", max_length=10)
    timezone: str = Field("UTC", max_length=50)
    
    # Authentication
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    
    # Session control
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    is_active: bool = True
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        return v.strip() if v else v

    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()

    class Config:
        use_enum_values = True


class OrganizationUserModel(BaseModel):
    """Organization-User relationship model"""
    id: Optional[UUID] = None
    organization_id: UUID = Field(..., description="Organization ID")
    user_id: UUID = Field(..., description="User ID")
    
    # Role and permissions
    role: UserRoleEnum = UserRoleEnum.USER
    status: MembershipStatusEnum = MembershipStatusEnum.ACTIVE
    
    # Specific permissions
    can_create_projects: bool = True
    can_manage_users: bool = False
    can_manage_billing: bool = False
    can_manage_templates: bool = False
    
    # Metadata
    invited_by: Optional[UUID] = None
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = Field(default_factory=datetime.now)
    last_activity_at: Optional[datetime] = None
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ========================
# PROJECT MODELS
# ========================

class ProjectModel(BaseModel):
    """Main project model (updated from RFXProcessed)"""
    id: Optional[UUID] = None
    organization_id: UUID = Field(..., description="Organization ID")
    project_number: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Z0-9-]+$')
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Client information
    client_name: Optional[str] = Field(None, max_length=255)
    client_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    client_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    client_type: Optional[ClientTypeEnum] = None
    
    # Project details
    project_type: ProjectTypeEnum = ProjectTypeEnum.GENERAL
    status: ProjectStatusEnum = ProjectStatusEnum.DRAFT
    
    # Service/Event details
    service_date: Optional[datetime] = None
    service_location: Optional[str] = None
    estimated_attendees: Optional[int] = Field(None, gt=0)
    service_duration_hours: Optional[float] = Field(None, gt=0)
    
    # Financial
    estimated_budget: Optional[float] = Field(None, ge=0)
    budget_range: Optional[BudgetRangeEnum] = None
    currency: CurrencyEnum = CurrencyEnum.USD
    
    # Workflow
    workflow_enabled: bool = True
    auto_progression: bool = True
    requires_approval: bool = False
    
    # Assignment
    created_by: UUID = Field(..., description="User ID who created the project")
    assigned_to: Optional[UUID] = Field(None, description="User ID assigned to the project")
    approved_by: Optional[UUID] = Field(None, description="User ID who approved the project")
    
    # Dates
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(3, ge=1, le=5, description="Priority level 1-5")
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @validator('name', 'client_name')
    def validate_names(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ProjectContextModel(BaseModel):
    """AI analysis context for project"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID")
    
    # AI Analysis
    detected_project_type: Optional[ProjectTypeEnum] = None
    detected_client_type: Optional[ClientTypeEnum] = None
    detected_budget_range: Optional[BudgetRangeEnum] = None
    complexity_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Structured insights
    key_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    implicit_needs: List[Dict[str, Any]] = Field(default_factory=list)
    market_context: Dict[str, Any] = Field(default_factory=dict)
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)
    opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Strategy
    extraction_strategy: Dict[str, Any] = Field(default_factory=dict)
    expected_deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_pricing_model: Optional[PricingModelEnum] = None
    
    # Analysis metadata
    analysis_confidence: Optional[float] = Field(None, ge=0, le=1)
    analysis_reasoning: Optional[str] = None
    ai_model_used: str = Field("gpt-4o", max_length=50)
    tokens_consumed: int = 0
    analysis_duration_seconds: Optional[int] = None
    
    # Timestamps
    analyzed_at: Optional[datetime] = Field(default_factory=datetime.now)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class WorkflowStateModel(BaseModel):
    """Workflow state for project"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID")
    
    # Current state
    current_stage: WorkflowStageEnum = WorkflowStageEnum.DOCUMENT_UPLOADED
    stage_progress: float = Field(0.0, ge=0, le=100)
    overall_progress: float = Field(0.0, ge=0, le=100)
    
    # History
    stage_history: List[Dict[str, Any]] = Field(default_factory=list)
    stage_durations: Dict[str, float] = Field(default_factory=dict)
    
    # Human intervention
    requires_human_review: bool = False
    human_review_reason: Optional[str] = None
    human_review_notes: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    
    # Quality
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    quality_gates_passed: int = 0
    quality_gates_total: int = 7
    validation_issues: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Decisions
    ai_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    human_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    workflow_version: str = Field("3.0", max_length=20)
    estimated_completion: Optional[datetime] = None
    
    # Timestamps
    started_at: Optional[datetime] = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ========================
# PROJECT ITEM MODELS
# ========================

class ProjectItemModel(BaseModel):
    """Project item model (updated from RFXProductRequest)"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID")
    
    # Item information
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    
    # Quantities
    quantity: float = Field(1.0, gt=0)
    unit_of_measure: str = Field("pieces", max_length=50)
    
    # Prices
    unit_price: Optional[float] = Field(None, ge=0)
    total_price: Optional[float] = Field(None, ge=0)
    cost_basis: Optional[str] = None
    
    # Source
    extracted_from_ai: bool = False
    source_document_id: Optional[UUID] = None
    source_section: Optional[str] = None
    
    # Quality
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1)
    extraction_method: Optional[str] = Field(None, max_length=100)
    
    # Validation
    is_validated: bool = False
    validated_by: Optional[UUID] = None
    validation_notes: Optional[str] = None
    
    # Configuration
    is_optional: bool = False
    is_included: bool = True
    sort_order: int = 0
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @validator('name')
    def validate_name(cls, v):
        return v.strip() if v else v

    @validator('total_price')
    def validate_total_price(cls, v, values):
        if v is not None and 'quantity' in values and 'unit_price' in values:
            if values['unit_price'] is not None:
                expected = values['quantity'] * values['unit_price']
                if abs(v - expected) > 0.01:  # 1 cent tolerance
                    raise ValueError('Total price does not match quantity × unit price')
        return v

    class Config:
        use_enum_values = True


# ========================
# PROJECT DOCUMENT MODELS
# ========================

class ProjectDocumentModel(BaseModel):
    """Project document model"""
    id: Optional[UUID] = None
    project_id: UUID = Field(..., description="Project ID")
    
    # File
    filename: str = Field(..., min_length=1, max_length=255)
    original_filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1)
    file_size_bytes: int = Field(..., gt=0)
    file_type: str = Field(..., min_length=1, max_length=100)
    mime_type: Optional[str] = Field(None, max_length=255)
    
    # Classification
    document_type: DocumentTypeEnum = DocumentTypeEnum.ATTACHMENT
    document_category: Optional[str] = Field(None, max_length=100)
    is_primary: bool = False
    
    # Processing
    is_processed: bool = False
    processing_status: str = Field("pending", max_length=50)
    processing_error: Optional[str] = None
    extracted_text: Optional[str] = None
    
    # Content metadata
    page_count: Optional[int] = Field(None, gt=0)
    word_count: Optional[int] = Field(None, gt=0)
    character_count: Optional[int] = Field(None, gt=0)
    language_detected: Optional[str] = Field(None, max_length=10)
    
    # Analysis
    content_summary: Optional[str] = None
    key_sections: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Versions
    version: int = 1
    replaced_by: Optional[UUID] = None
    
    # Security
    is_sensitive: bool = False
    access_level: str = Field("organization", max_length=50)
    
    # Control
    uploaded_by: UUID = Field(..., description="User ID who uploaded the document")
    processed_by: Optional[UUID] = None
    uploaded_at: Optional[datetime] = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ========================
# REQUEST/RESPONSE MODELS
# ========================

class ProjectCreateRequest(BaseModel):
    """Request to create a new project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: ProjectTypeEnum = ProjectTypeEnum.GENERAL
    
    # Client info (optional)
    client_name: Optional[str] = Field(None, max_length=255)
    client_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    client_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    client_type: Optional[ClientTypeEnum] = None
    
    # Service details (optional)
    service_date: Optional[datetime] = None
    service_location: Optional[str] = None
    estimated_attendees: Optional[int] = Field(None, gt=0)
    estimated_budget: Optional[float] = Field(None, ge=0)
    currency: CurrencyEnum = CurrencyEnum.USD
    
    # Assignment (optional)
    assigned_to: Optional[UUID] = None
    deadline: Optional[datetime] = None
    priority: int = Field(3, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)

    @validator('name', 'client_name')
    def validate_names(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True


class ProjectUpdateRequest(BaseModel):
    """Request to update project data"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatusEnum] = None
    
    # Client info updates
    client_name: Optional[str] = Field(None, max_length=255)
    client_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    client_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    client_type: Optional[ClientTypeEnum] = None
    
    # Service details
    service_date: Optional[datetime] = None
    service_location: Optional[str] = None
    estimated_attendees: Optional[int] = Field(None, gt=0)
    estimated_budget: Optional[float] = Field(None, ge=0)
    
    # Assignment
    assigned_to: Optional[UUID] = None
    deadline: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None

    @validator('name', 'client_name')
    def validate_names(cls, v):
        return v.strip() if v else v

    class Config:
        use_enum_values = True


class ProjectResponse(BaseModel):
    """Standard response for project endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    project: Optional[ProjectModel] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ProjectListResponse(BaseModel):
    """Response for project list endpoints"""
    status: str = Field(..., pattern=r'^(success|error)$')
    message: str
    projects: List[ProjectModel] = Field(default_factory=list)
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
# LEGACY COMPATIBILITY
# ========================

# Legacy aliases for backwards compatibility
RFXType = ProjectTypeEnum
RFXStatus = ProjectStatusEnum
CompanyModel = OrganizationModel
RequesterModel = UserModel
RFXProductRequest = ProjectItemModel

# Additional aliases needed by APIs
ProjectInput = ProjectCreateRequest
RFXInput = ProjectCreateRequest
RFXResponse = ProjectResponse

# Legacy field mappings for migration
LEGACY_PROJECT_MAPPING = {
    'rfx_type': 'project_type',
    'company_id': 'organization_id',
    'requester_id': 'created_by',
    'company_name': 'client_company',
    'requester_name': 'client_name',
    'delivery_date': 'service_date',
    'delivery_time': 'service_date',
    'location': 'service_location'
}

LEGACY_ITEM_MAPPING = {
    'rfx_id': 'project_id',
    'product_name': 'name',
    'estimated_unit_price': 'unit_price',
    'total_estimated_cost': 'total_price',
    'unit': 'unit_of_measure'
}
