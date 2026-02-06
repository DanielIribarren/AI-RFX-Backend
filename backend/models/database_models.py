"""
🗄️ Database Models - Complete Pydantic Models for All Tables
Single Source of Truth for database schema with type safety and validation

Based on:
- Complete-Schema-V3.0-With-Auth.sql
- migrations/003_create_product_catalog.sql
- migrations/004_allow_null_organization_catalog.sql
- migrations/005_add_unit_cost_to_rfx_products.sql
- Sistema de organizaciones implementado

Version: 3.1 (Actualizado con estado real de BD)
Date: 2026-02-05
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from enum import Enum
from decimal import Decimal


# ========================
# ENUMS
# ========================

class UserStatus(str, Enum):
    """Estados de usuario"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"


class UserRole(str, Enum):
    """Roles de usuario en organización"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class RFXStatus(str, Enum):
    """Estados de RFX"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class RFXType(str, Enum):
    """Tipos de RFX"""
    RFQ = "rfq"
    RFP = "rfp"
    RFI = "rfi"


class DocumentType(str, Enum):
    """Tipos de documentos"""
    PROPOSAL = "proposal"
    QUOTE = "quote"
    CONTRACT = "contract"
    EVALUATION = "evaluation"


class PriorityLevel(str, Enum):
    """Niveles de prioridad"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class PricingConfigStatus(str, Enum):
    """Estados de configuración de pricing"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class CoordinationType(str, Enum):
    """Tipos de coordinación"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class PlanTier(str, Enum):
    """Planes de organización"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AnalysisStatus(str, Enum):
    """Estados de análisis de branding"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# ========================
# BASE MODELS
# ========================

class TimestampMixin(BaseModel):
    """Mixin para timestamps comunes"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# ========================
# ORGANIZATIONS SYSTEM
# ========================

class Organization(TimestampMixin):
    """
    Tabla: organizations
    Sistema multi-tenant con planes y créditos
    """
    id: UUID
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    
    # Plan y límites
    plan_tier: PlanTier = Field(default=PlanTier.FREE)
    max_users: int = Field(default=5)
    max_rfx_per_month: int = Field(default=50)
    
    # Sistema de créditos
    credits_total: int = Field(default=100)
    credits_used: int = Field(default=0)
    credits_reset_date: Optional[datetime] = None
    
    # Trial
    trial_ends_at: Optional[datetime] = None
    
    # Estado
    is_active: bool = Field(default=True)

    @field_validator('slug')
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class CreditTransaction(TimestampMixin):
    """
    Tabla: credit_transactions
    Historial de uso de créditos
    """
    id: UUID
    organization_id: UUID
    
    # Transacción
    amount: int
    transaction_type: str = Field(..., max_length=50)  # 'purchase', 'usage', 'refund', 'reset'
    description: Optional[str] = None
    
    # Referencia
    reference_id: Optional[UUID] = None  # rfx_id, proposal_id, etc.
    reference_type: Optional[str] = Field(None, max_length=50)
    
    # Usuario que ejecutó
    performed_by: Optional[UUID] = None


# ========================
# USERS
# ========================

class User(TimestampMixin):
    """
    Tabla: users
    Usuarios del sistema con autenticación JWT
    """
    id: UUID
    
    # Autenticación
    email: EmailStr
    password_hash: str
    email_verified: bool = Field(default=False)
    email_verified_at: Optional[datetime] = None
    
    # Perfil
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    
    # Organización (multi-tenant)
    organization_id: Optional[UUID] = None
    role: Optional[UserRole] = None
    
    # Estado y seguridad
    status: UserStatus = Field(default=UserStatus.PENDING_VERIFICATION)
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = None
    
    # Preparado para teams (NULL por ahora)
    default_team_id: Optional[UUID] = None

    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()


# ========================
# COMPANIES & REQUESTERS
# ========================

class Company(TimestampMixin):
    """
    Tabla: companies
    Empresas/clientes - aislados por user_id o organization_id
    """
    id: UUID
    
    # Ownership (multi-tenant)
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    team_id: Optional[UUID] = None  # Preparado para futuro
    
    # Información básica
    name: str
    industry: Optional[str] = None
    size_category: Optional[str] = None  # 'startup', 'small', 'medium', 'large', 'enterprise'
    
    # Contacto
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    
    # Ubicación
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = Field(default="Mexico")
    
    # Legal
    tax_id: Optional[str] = None


class Requester(TimestampMixin):
    """
    Tabla: requesters
    Personas de contacto en las empresas cliente
    """
    id: UUID
    company_id: UUID
    
    name: str
    email: EmailStr
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    is_primary_contact: bool = Field(default=False)


# ========================
# SUPPLIERS & PRODUCTS
# ========================

class Supplier(TimestampMixin):
    """
    Tabla: suppliers
    Proveedores - aislados por user_id o organization_id
    """
    id: UUID
    
    # Ownership
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    
    # Relación
    company_id: UUID
    
    # Información
    specialty: Optional[str] = None
    certification_level: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)
    is_preferred: bool = Field(default=False)


class ProductCatalog(TimestampMixin):
    """
    Tabla: product_catalog
    Catálogo de productos - aislado por organization_id O user_id
    
    IMPORTANTE: Basado en migrations/003 y 004 (NO en schema V3.0)
    """
    id: UUID
    
    # Ownership (organization_id O user_id, no ambos NULL)
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None  # Preparado para futuro
    
    # Información del producto
    product_name: str = Field(..., max_length=255)  # ✅ Correcto según migración
    product_code: Optional[str] = Field(None, max_length=100)
    
    # Pricing (al menos uno requerido)
    unit_cost: Optional[Decimal] = Field(None, decimal_places=2)  # Lo que pagamos
    unit_price: Optional[Decimal] = Field(None, decimal_places=2)  # Lo que cobramos
    
    # Metadata
    unit: str = Field(default="unit", max_length=50)
    is_active: bool = Field(default=True)
    
    # Proveedor opcional
    supplier_id: Optional[UUID] = None

    @field_validator('unit_cost', 'unit_price')
    @classmethod
    def positive_values(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v


# ========================
# RFX SYSTEM
# ========================

class RFX(TimestampMixin):
    """
    Tabla: rfx_v2
    RFX principal - DEBE tener user_id o organization_id para aislamiento
    
    IMPORTANTE: NO tiene campo 'received_at', solo 'created_at'
    """
    id: UUID
    
    # OWNERSHIP (CRÍTICO para multi-tenancy)
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    team_id: Optional[UUID] = None  # Preparado para futuro
    
    # Información básica
    title: str
    description: Optional[str] = None
    rfx_type: RFXType = Field(default=RFXType.RFQ)
    status: RFXStatus = Field(default=RFXStatus.IN_PROGRESS)
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM)
    
    # Referencias
    company_id: UUID
    requester_id: UUID
    
    # Fechas
    submission_deadline: Optional[datetime] = None
    expected_decision_date: Optional[datetime] = None
    project_start_date: Optional[datetime] = None
    project_end_date: Optional[datetime] = None
    
    # Presupuesto
    budget_range_min: Optional[Decimal] = Field(None, decimal_places=2)
    budget_range_max: Optional[Decimal] = Field(None, decimal_places=2)
    currency: str = Field(default="MXN")
    
    # Localización del evento
    event_location: Optional[str] = None
    event_city: Optional[str] = None
    event_state: Optional[str] = None
    event_country: str = Field(default="Mexico")
    
    # Requirements (extraídos por IA)
    requirements: Optional[str] = None
    requirements_confidence: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=4)
    
    # Configuraciones
    evaluation_criteria: Optional[Dict[str, Any]] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class RFXProduct(TimestampMixin):
    """
    Tabla: rfx_products
    Productos en cada RFX
    
    IMPORTANTE: Incluye unit_cost (agregado en migración 005)
    """
    id: UUID
    rfx_id: UUID
    product_catalog_id: Optional[UUID] = None
    
    # Información del producto
    product_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    # Cantidades
    quantity: int = Field(..., gt=0)
    unit_of_measure: str = Field(default="unit")
    specifications: Optional[Dict[str, Any]] = None
    
    # Pricing
    estimated_unit_price: Optional[Decimal] = Field(None, decimal_places=2)
    unit_cost: Optional[Decimal] = Field(None, decimal_places=2)  # ✅ Agregado migración 005
    # total_estimated_cost es GENERATED column en BD
    
    # Metadatos
    priority_order: int = Field(default=1)
    is_mandatory: bool = Field(default=True)
    notes: Optional[str] = None


class GeneratedDocument(TimestampMixin):
    """
    Tabla: generated_documents
    Documentos generados (propuestas, cotizaciones)
    """
    id: UUID
    rfx_id: UUID
    
    # Información del documento
    document_type: DocumentType
    title: str
    content: Optional[str] = None
    
    # Archivos
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    
    # Metadatos de generación
    generated_by: Optional[str] = None
    generation_method: str = Field(default="ai_assisted")
    generation_metadata: Optional[Dict[str, Any]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Pricing
    total_cost: Optional[Decimal] = Field(None, decimal_places=2)
    cost_breakdown: Optional[Dict[str, Any]] = None


class RFXHistory(BaseModel):
    """
    Tabla: rfx_history
    Historial de cambios en RFX
    """
    id: UUID
    rfx_id: UUID
    
    changed_by: Optional[str] = None
    change_type: str
    change_description: Optional[str] = None
    
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    
    changed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# ========================
# PRICING SYSTEM V2.2
# ========================

class RFXPricingConfiguration(TimestampMixin):
    """
    Tabla: rfx_pricing_configurations
    Configuraciones de pricing por RFX
    """
    id: UUID
    rfx_id: UUID
    
    # Configuración
    configuration_name: str = Field(default="Default Configuration")
    is_active: bool = Field(default=True)
    status: PricingConfigStatus = Field(default=PricingConfigStatus.ACTIVE)
    
    # Usuarios
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    applied_by: Optional[str] = None
    applied_at: Optional[datetime] = None


class CoordinationConfiguration(TimestampMixin):
    """
    Tabla: coordination_configurations
    Configuración de coordinación independiente
    """
    id: UUID
    pricing_config_id: UUID
    
    # Configuración
    is_enabled: bool = Field(default=False)
    coordination_type: CoordinationType = Field(default=CoordinationType.STANDARD)
    
    # Tasas
    rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    # rate_percentage es GENERATED column en BD
    
    # Descripción
    description: str = Field(default="Coordinación y logística")
    internal_notes: Optional[str] = None
    
    # Configuraciones adicionales
    apply_to_subtotal: bool = Field(default=True)
    apply_to_total: bool = Field(default=False)
    minimum_amount: Optional[Decimal] = Field(None, decimal_places=2)
    maximum_amount: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Metadatos
    configuration_source: str = Field(default="manual")


class CostPerPersonConfiguration(TimestampMixin):
    """
    Tabla: cost_per_person_configurations
    Configuración de costo por persona
    """
    id: UUID
    pricing_config_id: UUID
    
    # Configuración
    is_enabled: bool = Field(default=False)
    
    # Personas
    headcount: int = Field(..., gt=0)
    headcount_confirmed: bool = Field(default=False)
    headcount_source: str = Field(default="manual")
    
    # Visualización
    display_in_proposal: bool = Field(default=True)
    display_format: str = Field(default="Costo por persona: ${cost} ({headcount} personas)")
    
    # Cálculo
    calculation_base: str = Field(default="final_total")  # 'subtotal', 'subtotal_with_coordination', 'final_total'
    round_to_cents: bool = Field(default=True)
    
    # Información
    description: str = Field(default="Cálculo de costo individual")
    internal_notes: Optional[str] = None


class TaxConfiguration(TimestampMixin):
    """
    Tabla: tax_configurations
    Configuración de impuestos
    """
    id: UUID
    pricing_config_id: UUID
    
    # Configuración
    is_enabled: bool = Field(default=False)
    
    # Impuesto
    tax_name: str = Field(default="IVA")
    tax_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    # tax_percentage es GENERATED column en BD
    
    # Aplicación
    apply_to_subtotal: bool = Field(default=False)
    apply_to_subtotal_with_coordination: bool = Field(default=True)
    
    # Información
    tax_jurisdiction: Optional[str] = None
    description: Optional[str] = None
    internal_notes: Optional[str] = None


# ========================
# BRANDING SYSTEM
# ========================

class CompanyBrandingAssets(TimestampMixin):
    """
    Tabla: company_branding_assets
    Branding por USUARIO (no por company). Logo y template personalizados.
    """
    id: UUID
    
    # OWNERSHIP (Cambio crítico V3.0)
    user_id: UUID
    team_id: Optional[UUID] = None  # Preparado para futuro
    
    # Logo
    logo_filename: Optional[str] = None
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None
    logo_uploaded_at: Optional[datetime] = None
    
    # Análisis de logo (JSONB cacheado)
    logo_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Template
    template_filename: Optional[str] = None
    template_path: Optional[str] = None
    template_url: Optional[str] = None
    template_uploaded_at: Optional[datetime] = None
    
    # Análisis de template (JSONB cacheado)
    template_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Template HTML generado (Sistema de 3 Agentes AI)
    html_template: Optional[str] = None
    
    # Estado del análisis
    analysis_status: AnalysisStatus = Field(default=AnalysisStatus.PENDING)
    analysis_error: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    
    # Configuración
    is_active: bool = Field(default=True)
    
    # Metadatos
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    notes: Optional[str] = None


# ========================
# RFX PROCESSING STATUS
# ========================

class RFXProcessingStatus(TimestampMixin):
    """
    Tabla: rfx_processing_status
    Estado de procesamiento y regeneraciones de RFX
    """
    id: UUID
    rfx_id: UUID
    organization_id: Optional[UUID] = None
    
    # Contadores
    total_regenerations: int = Field(default=0)
    free_regenerations_used: int = Field(default=0)
    paid_regenerations_used: int = Field(default=0)
    
    # Estado
    last_regeneration_at: Optional[datetime] = None
    processing_status: str = Field(default="pending")
    error_message: Optional[str] = None


# ========================
# EXPORT ALL MODELS
# ========================

__all__ = [
    # Enums
    "UserStatus",
    "UserRole",
    "RFXStatus",
    "RFXType",
    "DocumentType",
    "PriorityLevel",
    "PricingConfigStatus",
    "CoordinationType",
    "PlanTier",
    "AnalysisStatus",
    
    # Organizations
    "Organization",
    "CreditTransaction",
    
    # Users
    "User",
    
    # Companies
    "Company",
    "Requester",
    
    # Suppliers & Products
    "Supplier",
    "ProductCatalog",
    
    # RFX
    "RFX",
    "RFXProduct",
    "GeneratedDocument",
    "RFXHistory",
    
    # Pricing
    "RFXPricingConfiguration",
    "CoordinationConfiguration",
    "CostPerPersonConfiguration",
    "TaxConfiguration",
    
    # Branding
    "CompanyBrandingAssets",
    
    # Processing
    "RFXProcessingStatus",
]
