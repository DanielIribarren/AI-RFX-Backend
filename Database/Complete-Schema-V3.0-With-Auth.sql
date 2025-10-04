-- ========================
-- ESQUEMA COMPLETO DEFINITIVO V3.0 FINAL
-- Sistema RFX con Autenticación de Usuarios y Branding Personal
-- Fecha: 2024-10-04
-- Este es el SOURCE OF TRUTH - Usar para validar código Python
-- ========================

-- IMPORTANTE: Este script asume base de datos limpia
-- Si ya tienes datos, usar scripts de migración separados

BEGIN;

-- ========================
-- SECCIÓN 1: TIPOS ENUM
-- ========================

-- Estados de usuario
CREATE TYPE user_status AS ENUM (
    'active',
    'inactive',
    'pending_verification'
);

-- Estados de RFX
CREATE TYPE rfx_status AS ENUM (
    'in_progress',
    'completed',
    'cancelled',
    'on_hold'
);

-- Tipos de RFX
CREATE TYPE rfx_type AS ENUM (
    'rfq',
    'rfp',
    'rfi'
);

-- Tipos de documentos
CREATE TYPE document_type AS ENUM (
    'proposal',
    'quote',
    'contract',
    'evaluation'
);

-- Niveles de prioridad
CREATE TYPE priority_level AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
);

-- Estados de configuración de pricing
CREATE TYPE pricing_config_status AS ENUM (
    'active',
    'inactive',
    'archived'
);

-- Tipos de coordinación
CREATE TYPE coordination_type AS ENUM (
    'basic',
    'standard',
    'premium',
    'custom'
);

-- ========================
-- SECCIÓN 2: TABLA USERS (Core del sistema)
-- ========================

CREATE TABLE users (
    -- Identificador
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Autenticación
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMPTZ,
    
    -- Perfil
    full_name TEXT NOT NULL,
    company_name TEXT,
    phone TEXT,
    
    -- Estado y seguridad
    status user_status DEFAULT 'pending_verification',
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    
    -- Preparado para teams (NULL por ahora)
    default_team_id UUID,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT email_lowercase CHECK (email = LOWER(email)),
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

COMMENT ON TABLE users IS 'Usuarios del sistema con autenticación JWT';
COMMENT ON COLUMN users.default_team_id IS 'Preparado para migración futura a teams - NULL por ahora';

-- ========================
-- SECCIÓN 3: TABLAS DE AUTENTICACIÓN
-- ========================

CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 hour'),
    used_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE password_resets IS 'Tokens para recuperación de contraseña';

CREATE TABLE email_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE email_verifications IS 'Tokens para verificación de email';

-- ========================
-- SECCIÓN 4: TABLAS PRINCIPALES DEL NEGOCIO
-- ========================

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ownership (CRÍTICO para multi-tenancy)
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID,  -- NULL por ahora, preparado para teams
    
    -- Información básica
    name TEXT NOT NULL,
    industry TEXT,
    size_category TEXT CHECK (size_category IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    
    -- Contacto
    website TEXT,
    phone TEXT,
    email TEXT,
    
    -- Ubicación
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'Mexico',
    
    -- Legal
    tax_id TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE companies IS 'Empresas/clientes del usuario - datos aislados por user_id';
COMMENT ON COLUMN companies.user_id IS 'Usuario dueño de este cliente';
COMMENT ON COLUMN companies.team_id IS 'Preparado para teams - NULL por ahora';

CREATE TABLE requesters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    position TEXT,
    department TEXT,
    is_primary_contact BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE requesters IS 'Personas de contacto en las empresas cliente';

CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ownership
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID,
    
    -- Relación con empresa
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Información
    specialty TEXT,
    certification_level TEXT,
    rating DECIMAL(3,2) CHECK (rating >= 0 AND rating <= 5),
    is_preferred BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE suppliers IS 'Proveedores - aislados por user_id';

CREATE TABLE product_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ownership
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID,
    
    -- Información del producto
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    unit_of_measure TEXT DEFAULT 'unit',
    base_price DECIMAL(10,2),
    
    -- Proveedor opcional
    supplier_id UUID REFERENCES suppliers(id),
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE product_catalog IS 'Catálogo de productos - aislado por user_id';

-- ========================
-- SECCIÓN 5: TABLA RFX (Principal)
-- ========================

CREATE TABLE rfx_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- OWNERSHIP (CRÍTICO)
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id UUID,  -- NULL por ahora
    
    -- Información básica
    title TEXT NOT NULL,
    description TEXT,
    rfx_type rfx_type DEFAULT 'rfq',
    status rfx_status DEFAULT 'in_progress',
    priority priority_level DEFAULT 'medium',
    
    -- Referencias
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requester_id UUID NOT NULL REFERENCES requesters(id) ON DELETE CASCADE,
    
    -- Fechas
    submission_deadline TIMESTAMPTZ,
    expected_decision_date TIMESTAMPTZ,
    project_start_date TIMESTAMPTZ,
    project_end_date TIMESTAMPTZ,
    
    -- Presupuesto
    budget_range_min DECIMAL(15,2),
    budget_range_max DECIMAL(15,2),
    currency TEXT DEFAULT 'MXN',
    
    -- Localización del evento
    event_location TEXT,
    event_city TEXT,
    event_state TEXT,
    event_country TEXT DEFAULT 'Mexico',
    
    -- Requirements (extraídos por IA)
    requirements TEXT,
    requirements_confidence DECIMAL(5,4) CHECK (requirements_confidence >= 0 AND requirements_confidence <= 1),
    
    -- Configuraciones
    evaluation_criteria JSONB,
    metadata_json JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_budget_range CHECK (budget_range_min IS NULL OR budget_range_max IS NULL OR budget_range_min <= budget_range_max),
    CONSTRAINT valid_project_dates CHECK (project_start_date IS NULL OR project_end_date IS NULL OR project_start_date <= project_end_date)
);

COMMENT ON TABLE rfx_v2 IS 'RFX principal - DEBE tener user_id para aislamiento de datos';
COMMENT ON COLUMN rfx_v2.user_id IS 'Usuario que creó este RFX - CRÍTICO para seguridad';
COMMENT ON COLUMN rfx_v2.company_id IS 'Cliente que solicitó el RFX (distinto al usuario del sistema)';

CREATE TABLE rfx_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    product_catalog_id UUID REFERENCES product_catalog(id),
    
    -- Información del producto
    product_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    
    -- Cantidades
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_of_measure TEXT DEFAULT 'unit',
    specifications JSONB,
    
    -- Pricing
    estimated_unit_price DECIMAL(10,2),
    total_estimated_cost DECIMAL(12,2) GENERATED ALWAYS AS (quantity * COALESCE(estimated_unit_price, 0)) STORED,
    
    -- Metadatos
    priority_order INTEGER DEFAULT 1,
    is_mandatory BOOLEAN DEFAULT true,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rfx_products IS 'Productos en cada RFX';

CREATE TABLE generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Información del documento
    document_type document_type NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    
    -- Archivos
    file_path TEXT,
    file_size INTEGER,
    
    -- Metadatos de generación
    generated_by TEXT,
    generation_method TEXT DEFAULT 'ai_assisted',
    generation_metadata JSONB,
    
    -- Pricing
    total_cost DECIMAL(15,2),
    cost_breakdown JSONB,
    
    -- Timestamps
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE generated_documents IS 'Documentos generados (propuestas, cotizaciones)';

CREATE TABLE rfx_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    changed_by TEXT,
    change_type TEXT NOT NULL,
    change_description TEXT,
    old_values JSONB,
    new_values JSONB,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rfx_history IS 'Historial de cambios en RFX';

CREATE TABLE supplier_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    
    -- Puntuaciones
    technical_score DECIMAL(5,2) CHECK (technical_score >= 0 AND technical_score <= 100),
    commercial_score DECIMAL(5,2) CHECK (commercial_score >= 0 AND commercial_score <= 100),
    delivery_score DECIMAL(5,2) CHECK (delivery_score >= 0 AND delivery_score <= 100),
    overall_score DECIMAL(5,2) GENERATED ALWAYS AS ((technical_score + commercial_score + delivery_score) / 3) STORED,
    
    -- Información
    notes TEXT,
    recommendation TEXT CHECK (recommendation IN ('approve', 'reject', 'conditional')),
    evaluated_by TEXT,
    evaluation_date TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint
    UNIQUE(rfx_id, supplier_id)
);

COMMENT ON TABLE supplier_evaluations IS 'Evaluaciones de proveedores por RFX';

-- ========================
-- SECCIÓN 6: SISTEMA DE PRICING V2.2
-- ========================

CREATE TABLE rfx_pricing_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Configuración
    configuration_name TEXT NOT NULL DEFAULT 'Default Configuration',
    is_active BOOLEAN NOT NULL DEFAULT true,
    status pricing_config_status NOT NULL DEFAULT 'active',
    
    -- Usuarios
    created_by TEXT,
    updated_by TEXT,
    applied_by TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ,
    
    -- Constraint: solo una configuración activa por RFX
    CONSTRAINT unique_active_config_per_rfx 
        EXCLUDE (rfx_id WITH =) WHERE (is_active = true)
);

COMMENT ON TABLE rfx_pricing_configurations IS 'Configuraciones de pricing por RFX';

CREATE TABLE coordination_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    coordination_type coordination_type DEFAULT 'standard',
    
    -- Tasas
    rate DECIMAL(5,4) NOT NULL CHECK (rate >= 0.0000 AND rate <= 1.0000),
    rate_percentage DECIMAL(6,2) GENERATED ALWAYS AS (rate * 100) STORED,
    
    -- Descripción
    description TEXT DEFAULT 'Coordinación y logística',
    internal_notes TEXT,
    
    -- Configuraciones adicionales
    apply_to_subtotal BOOLEAN DEFAULT true,
    apply_to_total BOOLEAN DEFAULT false,
    minimum_amount DECIMAL(10,2),
    maximum_amount DECIMAL(10,2),
    
    -- Metadatos
    configuration_source TEXT DEFAULT 'manual',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Validaciones
    CONSTRAINT coordination_amounts_check 
        CHECK (minimum_amount IS NULL OR maximum_amount IS NULL OR minimum_amount <= maximum_amount)
);

COMMENT ON TABLE coordination_configurations IS 'Configuración de coordinación independiente';

CREATE TABLE cost_per_person_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Personas
    headcount INTEGER NOT NULL CHECK (headcount > 0),
    headcount_confirmed BOOLEAN DEFAULT false,
    headcount_source TEXT DEFAULT 'manual',
    
    -- Visualización
    display_in_proposal BOOLEAN DEFAULT true,
    display_format TEXT DEFAULT 'Costo por persona: ${cost} ({headcount} personas)',
    
    -- Cálculo
    calculation_base TEXT DEFAULT 'final_total' CHECK (calculation_base IN ('subtotal', 'subtotal_with_coordination', 'final_total')),
    round_to_cents BOOLEAN DEFAULT true,
    
    -- Información
    description TEXT DEFAULT 'Cálculo de costo individual',
    internal_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE cost_per_person_configurations IS 'Configuración de costo por persona';

CREATE TABLE tax_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Impuesto
    tax_name TEXT NOT NULL DEFAULT 'IVA',
    tax_rate DECIMAL(5,4) NOT NULL CHECK (tax_rate >= 0.0000 AND tax_rate <= 1.0000),
    tax_percentage DECIMAL(6,2) GENERATED ALWAYS AS (tax_rate * 100) STORED,
    
    -- Aplicación
    apply_to_subtotal BOOLEAN DEFAULT false,
    apply_to_subtotal_with_coordination BOOLEAN DEFAULT true,
    
    -- Información
    tax_jurisdiction TEXT,
    description TEXT,
    internal_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE tax_configurations IS 'Configuración de impuestos';

CREATE TABLE pricing_configuration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Cambio
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'updated', 'activated', 'deactivated', 'deleted')),
    changed_by TEXT,
    change_reason TEXT,
    
    -- Valores
    old_values JSONB,
    new_values JSONB,
    
    -- Contexto
    change_source TEXT DEFAULT 'manual',
    
    -- Timestamp
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE pricing_configuration_history IS 'Historial de cambios en pricing';

-- ========================
-- SECCIÓN 7: BRANDING POR USUARIO
-- ========================

CREATE TABLE company_branding_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- OWNERSHIP (Cambio crítico V3.0)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID,  -- NULL por ahora, preparado para teams
    
    -- Logo
    logo_filename TEXT,
    logo_path TEXT,
    logo_url TEXT,
    logo_uploaded_at TIMESTAMPTZ,
    
    -- Análisis de logo (JSONB cacheado)
    logo_analysis JSONB DEFAULT '{}',
    
    -- Template
    template_filename TEXT,
    template_path TEXT,
    template_url TEXT,
    template_uploaded_at TIMESTAMPTZ,
    
    -- Análisis de template (JSONB cacheado)
    template_analysis JSONB DEFAULT '{}',
    
    -- Estado del análisis
    analysis_status TEXT DEFAULT 'pending' CHECK (analysis_status IN ('pending', 'analyzing', 'completed', 'failed')),
    analysis_error TEXT,
    analysis_started_at TIMESTAMPTZ,
    
    -- Configuración
    is_active BOOLEAN DEFAULT true,
    
    -- Metadatos
    created_by TEXT,
    updated_by TEXT,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint: Una configuración por usuario
    CONSTRAINT unique_user_branding UNIQUE(user_id)
);

COMMENT ON TABLE company_branding_assets IS 'Branding por USUARIO (no por company). Logo y template personalizados.';
COMMENT ON COLUMN company_branding_assets.user_id IS 'Usuario dueño - CRÍTICO para aislamiento';
COMMENT ON COLUMN company_branding_assets.team_id IS 'Preparado para teams';
COMMENT ON COLUMN company_branding_assets.logo_analysis IS 'Análisis cacheado del logo con Pillow';
COMMENT ON COLUMN company_branding_assets.template_analysis IS 'Análisis cacheado del template con GPT-4 Vision';

-- ========================
-- SECCIÓN 8: ÍNDICES PARA PERFORMANCE
-- ========================

-- Índices de users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_email_verified ON users(email_verified);

-- Índices de autenticación
CREATE INDEX idx_password_resets_token ON password_resets(token) WHERE used_at IS NULL;
CREATE INDEX idx_password_resets_user ON password_resets(user_id);
CREATE INDEX idx_email_verifications_token ON email_verifications(token) WHERE verified_at IS NULL;
CREATE INDEX idx_email_verifications_user ON email_verifications(user_id);

-- Índices de ownership (CRÍTICOS para multi-tenancy)
CREATE INDEX idx_rfx_user ON rfx_v2(user_id);
CREATE INDEX idx_rfx_team ON rfx_v2(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_companies_user ON companies(user_id);
CREATE INDEX idx_companies_team ON companies(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_suppliers_user ON suppliers(user_id);
CREATE INDEX idx_suppliers_team ON suppliers(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_products_user ON product_catalog(user_id);
CREATE INDEX idx_products_team ON product_catalog(team_id) WHERE team_id IS NOT NULL;

-- Índices principales
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_requesters_company_id ON requesters(company_id);
CREATE INDEX idx_requesters_email ON requesters(email);
CREATE INDEX idx_suppliers_company_id ON suppliers(company_id);
CREATE INDEX idx_suppliers_rating ON suppliers(rating DESC);
CREATE INDEX idx_product_catalog_category ON product_catalog(category);
CREATE INDEX idx_product_catalog_name ON product_catalog(name);

-- Índices de RFX
CREATE INDEX idx_rfx_v2_company_id ON rfx_v2(company_id);
CREATE INDEX idx_rfx_v2_requester_id ON rfx_v2(requester_id);
CREATE INDEX idx_rfx_v2_status ON rfx_v2(status);
CREATE INDEX idx_rfx_v2_type ON rfx_v2(rfx_type);
CREATE INDEX idx_rfx_v2_created_at ON rfx_v2(created_at DESC);
CREATE INDEX idx_rfx_v2_deadline ON rfx_v2(submission_deadline);

-- Índices de productos y documentos
CREATE INDEX idx_rfx_products_rfx_id ON rfx_products(rfx_id);
CREATE INDEX idx_rfx_products_category ON rfx_products(category);
CREATE INDEX idx_generated_documents_rfx_id ON generated_documents(rfx_id);
CREATE INDEX idx_generated_documents_type ON generated_documents(document_type);
CREATE INDEX idx_generated_documents_generated_at ON generated_documents(generated_at DESC);

-- Índices de historial y evaluaciones
CREATE INDEX idx_rfx_history_rfx_id ON rfx_history(rfx_id);
CREATE INDEX idx_rfx_history_changed_at ON rfx_history(changed_at DESC);
CREATE INDEX idx_supplier_evaluations_rfx_id ON supplier_evaluations(rfx_id);
CREATE INDEX idx_supplier_evaluations_supplier_id ON supplier_evaluations(supplier_id);
CREATE INDEX idx_supplier_evaluations_overall_score ON supplier_evaluations(overall_score DESC);

-- Índices de pricing
CREATE INDEX idx_rfx_pricing_configurations_rfx_id ON rfx_pricing_configurations(rfx_id);
CREATE INDEX idx_rfx_pricing_configurations_active ON rfx_pricing_configurations(rfx_id, is_active) WHERE is_active = true;
CREATE INDEX idx_coordination_configs_pricing_id ON coordination_configurations(pricing_config_id);
CREATE INDEX idx_coordination_configs_enabled ON coordination_configurations(pricing_config_id, is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_cost_per_person_configs_pricing_id ON cost_per_person_configurations(pricing_config_id);
CREATE INDEX idx_cost_per_person_configs_enabled ON cost_per_person_configurations(pricing_config_id, is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_tax_configs_pricing_id ON tax_configurations(pricing_config_id);
CREATE INDEX idx_tax_configs_enabled ON tax_configurations(pricing_config_id, is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_pricing_history_config_id ON pricing_configuration_history(pricing_config_id);
CREATE INDEX idx_pricing_history_changed_at ON pricing_configuration_history(changed_at);

-- Índices de branding
CREATE INDEX idx_user_branding_user_id ON company_branding_assets(user_id);
CREATE INDEX idx_user_branding_active ON company_branding_assets(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_team_branding_team_id ON company_branding_assets(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_company_branding_status ON company_branding_assets(analysis_status);

-- Índices GIN para JSONB (búsquedas avanzadas)
CREATE INDEX idx_company_branding_logo_analysis ON company_branding_assets USING GIN (logo_analysis);
CREATE INDEX idx_company_branding_template_analysis ON company_branding_assets USING GIN (template_analysis);

-- ========================
-- SECCIÓN 9: FUNCIONES Y TRIGGERS
-- ========================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a todas las tablas con updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_requesters_updated_at BEFORE UPDATE ON requesters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_product_catalog_updated_at BEFORE UPDATE ON product_catalog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_v2_updated_at BEFORE UPDATE ON rfx_v2 FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_products_updated_at BEFORE UPDATE ON rfx_products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_generated_documents_updated_at BEFORE UPDATE ON generated_documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_coordination_configs_updated_at BEFORE UPDATE ON coordination_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cost_per_person_configs_updated_at BEFORE UPDATE ON cost_per_person_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tax_configs_updated_at BEFORE UPDATE ON tax_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_pricing_configurations_updated_at BEFORE UPDATE ON rfx_pricing_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_company_branding_updated_at BEFORE UPDATE ON company_branding_assets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para generar tokens seguros
CREATE OR REPLACE FUNCTION generate_secure_token()
RETURNS TEXT AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Función para verificar email
CREATE OR REPLACE FUNCTION verify_user_email(verification_token TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_expires_at TIMESTAMPTZ;
BEGIN
    SELECT user_id, expires_at INTO v_user_id, v_expires_at
    FROM email_verifications
    WHERE token = verification_token
    AND verified_at IS NULL;
    
    IF v_user_id IS NULL THEN
        RETURN false;
    END IF;
    
    IF v_expires_at < NOW() THEN
        RETURN false;
    END IF;
    
    UPDATE email_verifications
    SET verified_at = NOW()
    WHERE token = verification_token;
    
    UPDATE users
    SET email_verified = true,
        email_verified_at = NOW(),
        status = 'active'
    WHERE id = v_user_id;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Función para limpiar tokens expirados
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS TABLE (
    password_resets_cleaned INTEGER,
    email_verifications_cleaned INTEGER
) AS $$
DECLARE
    pr_count INTEGER;
    ev_count INTEGER;
BEGIN
    DELETE FROM password_resets WHERE expires_at < NOW() AND used_at IS NULL;
    GET DIAGNOSTICS pr_count = ROW_COUNT;
    
    DELETE FROM email_verifications WHERE expires_at < NOW() AND verified_at IS NULL;
    GET DIAGNOSTICS ev_count = ROW_COUNT;
    
    RETURN QUERY SELECT pr_count, ev_count;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener branding del usuario
CREATE OR REPLACE FUNCTION get_user_branding(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    logo_url TEXT,
    template_url TEXT,
    logo_analysis JSONB,
    template_analysis JSONB,
    analysis_status TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cba.id,
        cba.user_id,
        cba.logo_url,
        cba.template_url,
        cba.logo_analysis,
        cba.template_analysis,
        cba.analysis_status,
        cba.is_active,
        cba.created_at,
        cba.updated_at
    FROM company_branding_assets cba
    WHERE cba.user_id = user_uuid 
    AND cba.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Función para verificar si usuario tiene branding
CREATE OR REPLACE FUNCTION has_branding_configured(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM company_branding_assets 
        WHERE user_id = user_uuid 
        AND is_active = true
        AND analysis_status = 'completed'
    );
END;
$$ LANGUAGE plpgsql;

-- Función para obtener perfil completo del usuario
CREATE OR REPLACE FUNCTION get_user_profile(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    email TEXT,
    full_name TEXT,
    company_name TEXT,
    phone TEXT,
    status TEXT,
    email_verified BOOLEAN,
    last_login_at TIMESTAMPTZ,
    has_branding BOOLEAN,
    rfx_count BIGINT,
    companies_count BIGINT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.email,
        u.full_name,
        u.company_name,
        u.phone,
        u.status::TEXT,
        u.email_verified,
        u.last_login_at,
        has_branding_configured(u.id) as has_branding,
        COUNT(DISTINCT r.id) as rfx_count,
        COUNT(DISTINCT c.id) as companies_count,
        u.created_at
    FROM users u
    LEFT JOIN rfx_v2 r ON u.id = r.user_id
    LEFT JOIN companies c ON u.id = c.user_id
    WHERE u.id = user_uuid
    GROUP BY u.id;
END;
$$ LANGUAGE plpgsql;

-- Funciones de pricing (de V2.2)
CREATE OR REPLACE FUNCTION get_rfx_pricing_config(rfx_uuid UUID)
RETURNS TABLE (
    pricing_config_id UUID,
    configuration_name TEXT,
    is_active BOOLEAN,
    status TEXT,
    coordination_enabled BOOLEAN,
    coordination_rate DECIMAL,
    coordination_percentage DECIMAL,
    coordination_type TEXT,
    coordination_description TEXT,
    cost_per_person_enabled BOOLEAN,
    headcount INTEGER,
    headcount_confirmed BOOLEAN,
    headcount_source TEXT,
    calculation_base TEXT,
    display_in_proposal BOOLEAN,
    taxes_enabled BOOLEAN,
    tax_name TEXT,
    tax_rate DECIMAL,
    tax_percentage DECIMAL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rpc.id as pricing_config_id,
        rpc.configuration_name,
        rpc.is_active,
        rpc.status::TEXT,
        COALESCE(cc.is_enabled, false) as coordination_enabled,
        cc.rate as coordination_rate,
        cc.rate_percentage as coordination_percentage,
        cc.coordination_type::TEXT,
        cc.description as coordination_description,
        COALESCE(cpp.is_enabled, false) as cost_per_person_enabled,
        cpp.headcount,
        COALESCE(cpp.headcount_confirmed, false) as headcount_confirmed,
        COALESCE(cpp.headcount_source, 'manual') as headcount_source,
        COALESCE(cpp.calculation_base, 'final_total') as calculation_base,
        COALESCE(cpp.display_in_proposal, true) as display_in_proposal,
        COALESCE(tc.is_enabled, false) as taxes_enabled,
        tc.tax_name,
        tc.tax_rate,
        tc.tax_percentage,
        rpc.created_at,
        rpc.updated_at
    FROM rfx_pricing_configurations rpc
    LEFT JOIN coordination_configurations cc ON rpc.id = cc.pricing_config_id
    LEFT JOIN cost_per_person_configurations cpp ON rpc.id = cpp.pricing_config_id
    LEFT JOIN tax_configurations tc ON rpc.id = tc.pricing_config_id
    WHERE rpc.rfx_id = rfx_uuid 
    AND rpc.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Función para auditoría de pricing
CREATE OR REPLACE FUNCTION log_pricing_configuration_changes()
RETURNS TRIGGER AS $$
DECLARE
    changed_by_value TEXT := 'system';
BEGIN
    IF TG_OP = 'UPDATE' AND OLD IS NOT DISTINCT FROM NEW THEN
        RETURN NEW;
    END IF;
    
    IF TG_TABLE_NAME = 'rfx_pricing_configurations' THEN
        changed_by_value := COALESCE(
            CASE WHEN TG_OP != 'DELETE' THEN NEW.updated_by ELSE NULL END,
            CASE WHEN TG_OP != 'INSERT' THEN OLD.updated_by ELSE NULL END,
            'system'
        );
    ELSE
        changed_by_value := 'system';
    END IF;
    
    INSERT INTO pricing_configuration_history (
        pricing_config_id,
        change_type,
        changed_by,
        old_values,
        new_values,
        change_source
    ) VALUES (
        COALESCE(NEW.pricing_config_id, OLD.pricing_config_id),
        CASE 
            WHEN TG_OP = 'INSERT' THEN 'created'
            WHEN TG_OP = 'UPDATE' THEN 'updated'
            WHEN TG_OP = 'DELETE' THEN 'deleted'
        END,
        changed_by_value,
        CASE WHEN TG_OP != 'INSERT' THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP != 'DELETE' THEN to_jsonb(NEW) ELSE NULL END,
        'trigger'
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers de auditoría
CREATE TRIGGER coordination_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON coordination_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

CREATE TRIGGER cost_per_person_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON cost_per_person_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

CREATE TRIGGER tax_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON tax_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

-- ========================
-- SECCIÓN 10: VISTAS ÚTILES
-- ========================

CREATE VIEW users_summary AS
SELECT 
    u.id,
    u.email,
    u.full_name,
    u.company_name,
    u.status,
    u.email_verified,
    u.last_login_at,
    COUNT(DISTINCT r.id) as rfx_count,
    COUNT(DISTINCT c.id) as companies_count,
    COUNT(DISTINCT s.id) as suppliers_count,
    EXISTS(SELECT 1 FROM company_branding_assets WHERE user_id = u.id AND is_active = true) as has_branding,
    u.created_at
FROM users u
LEFT JOIN rfx_v2 r ON u.id = r.user_id
LEFT JOIN companies c ON u.id = c.user_id
LEFT JOIN suppliers s ON u.id = s.user_id
GROUP BY u.id;

COMMENT ON VIEW users_summary IS 'Resumen de usuarios con estadísticas';

CREATE VIEW rfx_pricing_summary AS
SELECT 
    rpc.rfx_id,
    rpc.id as pricing_config_id,
    rpc.configuration_name,
    rpc.is_active,
    rpc.status,
    cc.is_enabled as coordination_enabled,
    cc.rate as coordination_rate,
    cc.rate_percentage as coordination_percentage,
    cc.coordination_type,
    cc.description as coordination_description,
    cpp.is_enabled as cost_per_person_enabled,
    cpp.headcount,
    cpp.headcount_confirmed,
    cpp.display_in_proposal as show_cost_per_person,
    cpp.calculation_base as cost_calculation_base,
    tc.is_enabled as taxes_enabled,
    tc.tax_name,
    tc.tax_rate,
    tc.tax_percentage,
    rpc.created_at,
    rpc.updated_at,
    rpc.applied_at
FROM rfx_pricing_configurations rpc
LEFT JOIN coordination_configurations cc ON rpc.id = cc.pricing_config_id
LEFT JOIN cost_per_person_configurations cpp ON rpc.id = cpp.pricing_config_id  
LEFT JOIN tax_configurations tc ON rpc.id = tc.pricing_config_id
WHERE rpc.is_active = true;

COMMENT ON VIEW rfx_pricing_summary IS 'Resumen completo de pricing por RFX';

CREATE VIEW active_rfx_pricing AS
SELECT 
    rfx_id,
    coordination_enabled,
    coordination_rate,
    coordination_percentage,
    cost_per_person_enabled,
    headcount,
    taxes_enabled,
    tax_rate,
    tax_percentage
FROM rfx_pricing_summary
WHERE is_active = true;

COMMENT ON VIEW active_rfx_pricing IS 'Configuraciones activas simplificadas';

CREATE VIEW rfx_summary AS
SELECT 
    r.id,
    r.title,
    r.description,
    r.rfx_type,
    r.status,
    r.priority,
    r.user_id,
    u.full_name as creator_name,
    u.email as creator_email,
    c.name as company_name,
    req.name as requester_name,
    req.email as requester_email,
    r.submission_deadline,
    r.budget_range_min,
    r.budget_range_max,
    r.currency,
    r.event_location,
    r.requirements,
    r.requirements_confidence,
    (SELECT COUNT(*) FROM rfx_products WHERE rfx_id = r.id) as products_count,
    (SELECT COUNT(*) FROM generated_documents WHERE rfx_id = r.id) as documents_count,
    r.created_at,
    r.updated_at
FROM rfx_v2 r
JOIN users u ON r.user_id = u.id
JOIN companies c ON r.company_id = c.id
JOIN requesters req ON r.requester_id = req.id;

COMMENT ON VIEW rfx_summary IS 'Vista completa de RFX con información relacionada';

COMMIT;

-- ========================
-- VERIFICACIÓN FINAL
-- ========================

SELECT 'Complete Schema V3.0 Created Successfully!' as status;

-- Contar tablas creadas
SELECT 
    'Tables created: ' || COUNT(*) as info
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

-- Contar vistas creadas
SELECT 
    'Views created: ' || COUNT(*) as info
FROM information_schema.views 
WHERE table_schema = 'public';

-- Contar funciones creadas
SELECT 
    'Functions created: ' || COUNT(*) as info
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_type = 'FUNCTION';

-- Contar índices creados
SELECT 
    'Indexes created: ' || COUNT(*) as info
FROM pg_indexes
WHERE schemaname = 'public';

-- Verificar tablas críticas con user_id
SELECT 
    table_name,
    column_name,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND column_name IN ('user_id', 'team_id')
ORDER BY table_name, column_name;

SELECT 'SCHEMA V3.0 FINAL - SOURCE OF TRUTH' as final_message;