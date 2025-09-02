-- ========================
-- ESQUEMA COMPLETO V2.2 - RFX AUTOMATION SYSTEM
-- Incluye: Esquema base + Requirements + Sistema de Pricing V2.2
-- Fecha: 2024
-- Versión: 2.2 (Pricing Normalizado)
-- ========================

-- IMPORTANTE: Este es el esquema completo actual del sistema
-- Incluye todas las tablas y funcionalidades implementadas

BEGIN;

-- ========================
-- TIPOS ENUM PRINCIPALES
-- ========================

-- Estados de RFX
CREATE TYPE rfx_status AS ENUM (
    'in_progress',
    'completed',
    'cancelled',
    'on_hold'
);

-- Tipos de RFX
CREATE TYPE rfx_type AS ENUM (
    'rfq',      -- Request for Quote
    'rfp',      -- Request for Proposal  
    'rfi'       -- Request for Information
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

-- ========================
-- TIPOS ENUM PARA PRICING V2.2
-- ========================

-- Estados de configuración de pricing
CREATE TYPE pricing_config_status AS ENUM (
    'active',
    'inactive', 
    'archived'
);

-- Tipos de coordinación disponibles
CREATE TYPE coordination_type AS ENUM (
    'basic',      -- Coordinación básica
    'standard',   -- Coordinación estándar
    'premium',    -- Coordinación premium
    'custom'      -- Coordinación personalizada
);

SELECT 'All ENUM types created successfully!' as step_1_status;

-- ========================
-- TABLAS PRINCIPALES DEL SISTEMA
-- ========================

-- Empresas/Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    industry TEXT,
    size_category TEXT CHECK (size_category IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    website TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'Mexico',
    tax_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Solicitantes/Requesters  
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

-- Proveedores/Suppliers
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    specialty TEXT,
    certification_level TEXT,
    rating DECIMAL(3,2) CHECK (rating >= 0 AND rating <= 5),
    is_preferred BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Catálogo de productos
CREATE TABLE product_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    unit_of_measure TEXT DEFAULT 'unit',
    base_price DECIMAL(10,2),
    supplier_id UUID REFERENCES suppliers(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RFX V2 (Tabla principal mejorada)
CREATE TABLE rfx_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Información básica
    title TEXT NOT NULL,
    description TEXT,
    rfx_type rfx_type DEFAULT 'rfq',
    status rfx_status DEFAULT 'in_progress',
    priority priority_level DEFAULT 'medium',
    
    -- Referencias
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requester_id UUID NOT NULL REFERENCES requesters(id) ON DELETE CASCADE,
    
    -- Fechas importantes
    submission_deadline TIMESTAMPTZ,
    expected_decision_date TIMESTAMPTZ,
    project_start_date TIMESTAMPTZ,
    project_end_date TIMESTAMPTZ,
    
    -- Información del proyecto
    budget_range_min DECIMAL(15,2),
    budget_range_max DECIMAL(15,2),
    currency TEXT DEFAULT 'MXN',
    
    -- Localización del evento
    event_location TEXT,
    event_city TEXT,
    event_state TEXT,
    event_country TEXT DEFAULT 'Mexico',
    
    -- *** REQUIREMENTS FIELDS (Added) ***
    requirements TEXT,
    requirements_confidence DECIMAL(5,4) CHECK (requirements_confidence >= 0 AND requirements_confidence <= 1),
    
    -- Configuraciones y metadatos
    evaluation_criteria JSONB,
    metadata_json JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índices y constraints
    CONSTRAINT valid_budget_range CHECK (budget_range_min IS NULL OR budget_range_max IS NULL OR budget_range_min <= budget_range_max),
    CONSTRAINT valid_project_dates CHECK (project_start_date IS NULL OR project_end_date IS NULL OR project_start_date <= project_end_date)
);

-- Productos de RFX
CREATE TABLE rfx_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    product_catalog_id UUID REFERENCES product_catalog(id),
    
    -- Información del producto solicitado
    product_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    
    -- Cantidades y especificaciones
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_of_measure TEXT DEFAULT 'unit',
    specifications JSONB,
    
    -- Pricing estimado
    estimated_unit_price DECIMAL(10,2),
    total_estimated_cost DECIMAL(12,2) GENERATED ALWAYS AS (quantity * COALESCE(estimated_unit_price, 0)) STORED,
    
    -- Metadatos
    priority_order INTEGER DEFAULT 1,
    is_mandatory BOOLEAN DEFAULT true,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documentos generados
CREATE TABLE generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Información del documento
    document_type document_type NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    
    -- Metadatos de generación
    file_path TEXT,
    file_size INTEGER,
    generated_by TEXT,
    generation_method TEXT DEFAULT 'ai_assisted',
    generation_metadata JSONB,
    
    -- Pricing del documento (si aplica)
    total_cost DECIMAL(15,2),
    cost_breakdown JSONB,
    
    -- Timestamps
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historial de RFX
CREATE TABLE rfx_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Información del cambio
    changed_by TEXT,
    change_type TEXT NOT NULL,
    change_description TEXT,
    
    -- Estados anterior y nuevo
    old_values JSONB,
    new_values JSONB,
    
    -- Timestamp
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluaciones de proveedores
CREATE TABLE supplier_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    
    -- Puntuaciones
    technical_score DECIMAL(5,2) CHECK (technical_score >= 0 AND technical_score <= 100),
    commercial_score DECIMAL(5,2) CHECK (commercial_score >= 0 AND commercial_score <= 100),
    delivery_score DECIMAL(5,2) CHECK (delivery_score >= 0 AND delivery_score <= 100),
    overall_score DECIMAL(5,2) GENERATED ALWAYS AS ((technical_score + commercial_score + delivery_score) / 3) STORED,
    
    -- Información adicional
    notes TEXT,
    recommendation TEXT CHECK (recommendation IN ('approve', 'reject', 'conditional')),
    
    -- Metadatos
    evaluated_by TEXT,
    evaluation_date TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint: Un proveedor por RFX
    UNIQUE(rfx_id, supplier_id)
);

SELECT 'All main system tables created successfully!' as step_2_status;

-- ========================
-- TABLAS DE PRICING V2.2 (NORMALIZADAS)
-- ========================

-- Configuraciones principales por RFX
CREATE TABLE rfx_pricing_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Configuración general
    configuration_name TEXT NOT NULL DEFAULT 'Default Configuration',
    is_active BOOLEAN NOT NULL DEFAULT true,
    status pricing_config_status NOT NULL DEFAULT 'active',
    
    -- Información del usuario
    created_by TEXT,
    updated_by TEXT,
    applied_by TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ,
    
    -- Restricción: Solo una configuración activa por RFX
    CONSTRAINT unique_active_config_per_rfx 
        EXCLUDE (rfx_id WITH =) WHERE (is_active = true)
);

-- Tabla de configuraciones de coordinación (INDEPENDIENTE)
CREATE TABLE coordination_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración de coordinación
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    coordination_type coordination_type DEFAULT 'standard',
    
    -- Tasas y cálculos
    rate DECIMAL(5,4) NOT NULL CHECK (rate >= 0.0000 AND rate <= 1.0000),
    rate_percentage DECIMAL(6,2) GENERATED ALWAYS AS (rate * 100) STORED,
    
    -- Descripción personalizada
    description TEXT DEFAULT 'Coordinación y logística',
    internal_notes TEXT,
    
    -- Configuraciones adicionales
    apply_to_subtotal BOOLEAN DEFAULT true,
    apply_to_total BOOLEAN DEFAULT false,
    minimum_amount DECIMAL(10,2),
    maximum_amount DECIMAL(10,2),
    
    -- Metadatos
    configuration_source TEXT DEFAULT 'manual', -- 'manual', 'preset', 'ai_suggested'
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Validaciones
    CONSTRAINT coordination_amounts_check 
        CHECK (minimum_amount IS NULL OR maximum_amount IS NULL OR minimum_amount <= maximum_amount)
);

-- Tabla de configuraciones de costo por persona (INDEPENDIENTE)
CREATE TABLE cost_per_person_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración de costo por persona
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Configuración de personas
    headcount INTEGER NOT NULL CHECK (headcount > 0),
    headcount_confirmed BOOLEAN DEFAULT false,
    headcount_source TEXT DEFAULT 'manual', -- 'manual', 'extracted', 'estimated'
    
    -- Configuración de visualización
    display_in_proposal BOOLEAN DEFAULT true,
    display_format TEXT DEFAULT 'Costo por persona: ${cost} ({headcount} personas)',
    
    -- Configuraciones de cálculo
    calculation_base TEXT DEFAULT 'final_total' CHECK (calculation_base IN ('subtotal', 'subtotal_with_coordination', 'final_total')),
    round_to_cents BOOLEAN DEFAULT true,
    
    -- Información adicional
    description TEXT DEFAULT 'Cálculo de costo individual',
    internal_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de configuraciones de impuestos (EXTENSIBLE)
CREATE TABLE tax_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Configuración de impuestos
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Configuración del impuesto
    tax_name TEXT NOT NULL DEFAULT 'IVA',
    tax_rate DECIMAL(5,4) NOT NULL CHECK (tax_rate >= 0.0000 AND tax_rate <= 1.0000),
    tax_percentage DECIMAL(6,2) GENERATED ALWAYS AS (tax_rate * 100) STORED,
    
    -- Configuración de aplicación
    apply_to_subtotal BOOLEAN DEFAULT false,
    apply_to_subtotal_with_coordination BOOLEAN DEFAULT true,
    
    -- Información adicional
    tax_jurisdiction TEXT, -- 'Nacional', 'Estatal', 'Municipal'
    description TEXT,
    internal_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de historial de configuraciones de pricing
CREATE TABLE pricing_configuration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pricing_config_id UUID NOT NULL REFERENCES rfx_pricing_configurations(id) ON DELETE CASCADE,
    
    -- Información del cambio
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'updated', 'activated', 'deactivated', 'deleted')),
    changed_by TEXT,
    change_reason TEXT,
    
    -- Valores anteriores y nuevos (JSONB para flexibilidad)
    old_values JSONB,
    new_values JSONB,
    
    -- Contexto del cambio
    change_source TEXT DEFAULT 'manual', -- 'manual', 'api', 'migration', 'system'
    
    -- Timestamp
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT 'All pricing configuration tables created successfully!' as step_3_status;

-- ========================
-- ÍNDICES PARA PERFORMANCE
-- ========================

-- Índices principales del sistema
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_industry ON companies(industry);

CREATE INDEX idx_requesters_company_id ON requesters(company_id);
CREATE INDEX idx_requesters_email ON requesters(email);

CREATE INDEX idx_suppliers_company_id ON suppliers(company_id);
CREATE INDEX idx_suppliers_rating ON suppliers(rating DESC);

CREATE INDEX idx_product_catalog_category ON product_catalog(category);
CREATE INDEX idx_product_catalog_name ON product_catalog(name);

CREATE INDEX idx_rfx_v2_company_id ON rfx_v2(company_id);
CREATE INDEX idx_rfx_v2_requester_id ON rfx_v2(requester_id);
CREATE INDEX idx_rfx_v2_status ON rfx_v2(status);
CREATE INDEX idx_rfx_v2_type ON rfx_v2(rfx_type);
CREATE INDEX idx_rfx_v2_created_at ON rfx_v2(created_at DESC);
CREATE INDEX idx_rfx_v2_deadline ON rfx_v2(submission_deadline);

CREATE INDEX idx_rfx_products_rfx_id ON rfx_products(rfx_id);
CREATE INDEX idx_rfx_products_category ON rfx_products(category);

CREATE INDEX idx_generated_documents_rfx_id ON generated_documents(rfx_id);
CREATE INDEX idx_generated_documents_type ON generated_documents(document_type);
CREATE INDEX idx_generated_documents_generated_at ON generated_documents(generated_at DESC);

CREATE INDEX idx_rfx_history_rfx_id ON rfx_history(rfx_id);
CREATE INDEX idx_rfx_history_changed_at ON rfx_history(changed_at DESC);

CREATE INDEX idx_supplier_evaluations_rfx_id ON supplier_evaluations(rfx_id);
CREATE INDEX idx_supplier_evaluations_supplier_id ON supplier_evaluations(supplier_id);
CREATE INDEX idx_supplier_evaluations_overall_score ON supplier_evaluations(overall_score DESC);

-- Índices para pricing
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

SELECT 'All indexes created successfully!' as step_4_status;

-- ========================
-- FUNCIONES Y TRIGGERS
-- ========================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a todas las tablas que tienen updated_at
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_requesters_updated_at BEFORE UPDATE ON requesters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_product_catalog_updated_at BEFORE UPDATE ON product_catalog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_v2_updated_at BEFORE UPDATE ON rfx_v2 FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_products_updated_at BEFORE UPDATE ON rfx_products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_generated_documents_updated_at BEFORE UPDATE ON generated_documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Triggers para pricing
CREATE TRIGGER update_coordination_configs_updated_at BEFORE UPDATE ON coordination_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cost_per_person_configs_updated_at BEFORE UPDATE ON cost_per_person_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tax_configs_updated_at BEFORE UPDATE ON tax_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rfx_pricing_configurations_updated_at BEFORE UPDATE ON rfx_pricing_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para registrar cambios automáticamente en pricing
CREATE OR REPLACE FUNCTION log_pricing_configuration_changes()
RETURNS TRIGGER AS $$
DECLARE
    changed_by_value TEXT := 'system';
BEGIN
    -- Solo registrar si hay cambios reales
    IF TG_OP = 'UPDATE' AND OLD IS NOT DISTINCT FROM NEW THEN
        RETURN NEW;
    END IF;
    
    -- Determinar quien hizo el cambio dependiendo de la tabla
    IF TG_TABLE_NAME = 'rfx_pricing_configurations' THEN
        -- Esta tabla SÍ tiene updated_by
        changed_by_value := COALESCE(
            CASE WHEN TG_OP != 'DELETE' THEN NEW.updated_by ELSE NULL END,
            CASE WHEN TG_OP != 'INSERT' THEN OLD.updated_by ELSE NULL END,
            'system'
        );
    ELSE
        -- Las otras tablas NO tienen updated_by, usar valor por defecto
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

-- Aplicar triggers de auditoría a pricing
CREATE TRIGGER coordination_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON coordination_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

CREATE TRIGGER cost_per_person_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON cost_per_person_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

CREATE TRIGGER tax_config_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON tax_configurations
    FOR EACH ROW EXECUTE FUNCTION log_pricing_configuration_changes();

SELECT 'All triggers created successfully!' as step_5_status;

-- ========================
-- VISTAS OPTIMIZADAS
-- ========================

-- Vista completa de configuraciones por RFX
CREATE VIEW rfx_pricing_summary AS
SELECT 
    rpc.rfx_id,
    rpc.id as pricing_config_id,
    rpc.configuration_name,
    rpc.is_active,
    rpc.status,
    
    -- Coordinación
    cc.is_enabled as coordination_enabled,
    cc.rate as coordination_rate,
    cc.rate_percentage as coordination_percentage,
    cc.coordination_type,
    cc.description as coordination_description,
    
    -- Costo por persona
    cpp.is_enabled as cost_per_person_enabled,
    cpp.headcount,
    cpp.headcount_confirmed,
    cpp.display_in_proposal as show_cost_per_person,
    cpp.calculation_base as cost_calculation_base,
    
    -- Impuestos
    tc.is_enabled as taxes_enabled,
    tc.tax_name,
    tc.tax_rate,
    tc.tax_percentage,
    
    -- Timestamps
    rpc.created_at,
    rpc.updated_at,
    rpc.applied_at
    
FROM rfx_pricing_configurations rpc
LEFT JOIN coordination_configurations cc ON rpc.id = cc.pricing_config_id
LEFT JOIN cost_per_person_configurations cpp ON rpc.id = cpp.pricing_config_id  
LEFT JOIN tax_configurations tc ON rpc.id = tc.pricing_config_id
WHERE rpc.is_active = true;

-- Vista de configuraciones activas simplificada
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

-- Vista de resumen de RFX con información básica
CREATE VIEW rfx_summary AS
SELECT 
    r.id,
    r.title,
    r.description,
    r.rfx_type,
    r.status,
    r.priority,
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
JOIN companies c ON r.company_id = c.id
JOIN requesters req ON r.requester_id = req.id;

SELECT 'All views created successfully!' as step_6_status;

-- ========================
-- STORED PROCEDURES PARA PRICING V2.2
-- ========================

-- Función: Obtener configuración completa de pricing
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
        
        -- Coordinación
        COALESCE(cc.is_enabled, false) as coordination_enabled,
        cc.rate as coordination_rate,
        cc.rate_percentage as coordination_percentage,
        cc.coordination_type::TEXT,
        cc.description as coordination_description,
        
        -- Costo por persona
        COALESCE(cpp.is_enabled, false) as cost_per_person_enabled,
        cpp.headcount,
        COALESCE(cpp.headcount_confirmed, false) as headcount_confirmed,
        COALESCE(cpp.headcount_source, 'manual') as headcount_source,
        COALESCE(cpp.calculation_base, 'final_total') as calculation_base,
        COALESCE(cpp.display_in_proposal, true) as display_in_proposal,
        
        -- Impuestos
        COALESCE(tc.is_enabled, false) as taxes_enabled,
        tc.tax_name,
        tc.tax_rate,
        tc.tax_percentage,
        
        -- Timestamps
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

-- Función: Cálculo rápido de pricing
CREATE OR REPLACE FUNCTION calculate_rfx_pricing(
    rfx_uuid UUID,
    base_subtotal DECIMAL
)
RETURNS TABLE (
    subtotal DECIMAL,
    coordination_enabled BOOLEAN,
    coordination_rate DECIMAL,
    coordination_amount DECIMAL,
    cost_per_person_enabled BOOLEAN,
    headcount INTEGER,
    cost_per_person DECIMAL,
    taxes_enabled BOOLEAN,
    tax_rate DECIMAL,
    tax_amount DECIMAL,
    total_before_tax DECIMAL,
    final_total DECIMAL
) AS $$
DECLARE
    config_record RECORD;
    calc_coordination_amount DECIMAL := 0;
    calc_tax_amount DECIMAL := 0;
    calc_total_before_tax DECIMAL;
    calc_final_total DECIMAL;
    calc_cost_per_person DECIMAL;
BEGIN
    -- Obtener configuración activa
    SELECT * INTO config_record
    FROM active_rfx_pricing
    WHERE rfx_id = rfx_uuid;
    
    -- Si no hay configuración, usar valores por defecto
    IF config_record IS NULL THEN
        RETURN QUERY SELECT 
            base_subtotal,
            false, 0::DECIMAL, 0::DECIMAL,
            false, 0, 0::DECIMAL,
            false, 0::DECIMAL, 0::DECIMAL,
            base_subtotal, base_subtotal;
        RETURN;
    END IF;
    
    -- Calcular coordinación
    IF config_record.coordination_enabled THEN
        calc_coordination_amount := base_subtotal * config_record.coordination_rate;
    END IF;
    
    -- Calcular total antes de impuestos
    calc_total_before_tax := base_subtotal + calc_coordination_amount;
    
    -- Calcular impuestos
    IF config_record.taxes_enabled THEN
        calc_tax_amount := calc_total_before_tax * config_record.tax_rate;
    END IF;
    
    -- Calcular total final
    calc_final_total := calc_total_before_tax + calc_tax_amount;
    
    -- Calcular costo por persona
    IF config_record.cost_per_person_enabled AND config_record.headcount > 0 THEN
        calc_cost_per_person := calc_final_total / config_record.headcount;
    END IF;
    
    RETURN QUERY SELECT 
        base_subtotal,
        COALESCE(config_record.coordination_enabled, false),
        COALESCE(config_record.coordination_rate, 0),
        calc_coordination_amount,
        COALESCE(config_record.cost_per_person_enabled, false),
        COALESCE(config_record.headcount, 0),
        COALESCE(calc_cost_per_person, 0),
        COALESCE(config_record.taxes_enabled, false),
        COALESCE(config_record.tax_rate, 0),
        calc_tax_amount,
        calc_total_before_tax,
        calc_final_total;
END;
$$ LANGUAGE plpgsql;

-- Función: Estadísticas de uso de pricing
CREATE OR REPLACE FUNCTION get_pricing_usage_stats()
RETURNS TABLE (
    total_rfx INTEGER,
    rfx_with_coordination INTEGER,
    rfx_with_cost_per_person INTEGER,
    rfx_with_both INTEGER,
    rfx_with_neither INTEGER,
    avg_coordination_rate DECIMAL,
    avg_headcount DECIMAL,
    most_common_coordination_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE coordination_enabled) as coord_count,
            COUNT(*) FILTER (WHERE cost_per_person_enabled) as cpp_count,
            COUNT(*) FILTER (WHERE coordination_enabled AND cost_per_person_enabled) as both_count,
            COUNT(*) FILTER (WHERE NOT coordination_enabled AND NOT cost_per_person_enabled) as neither_count,
            AVG(coordination_rate) FILTER (WHERE coordination_enabled) as avg_coord_rate,
            AVG(headcount) FILTER (WHERE cost_per_person_enabled) as avg_head_count
        FROM active_rfx_pricing
    ),
    common_type AS (
        SELECT cc.coordination_type::TEXT as most_common_type
        FROM coordination_configurations cc
        JOIN rfx_pricing_configurations rpc ON cc.pricing_config_id = rpc.id
        WHERE cc.is_enabled = true AND rpc.is_active = true
        GROUP BY cc.coordination_type
        ORDER BY COUNT(*) DESC
        LIMIT 1
    )
    SELECT 
        s.total::INTEGER,
        s.coord_count::INTEGER,
        s.cpp_count::INTEGER,
        s.both_count::INTEGER,
        s.neither_count::INTEGER,
        s.avg_coord_rate,
        s.avg_head_count,
        COALESCE(ct.most_common_type, 'standard')
    FROM stats s
    CROSS JOIN common_type ct;
END;
$$ LANGUAGE plpgsql;

SELECT 'All stored procedures created successfully!' as step_7_status;

-- ========================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- ========================

-- Comentarios de tablas principales
COMMENT ON TABLE rfx_v2 IS 'Tabla principal de RFX (Request for X) con información completa del proyecto';
COMMENT ON TABLE companies IS 'Empresas participantes en el sistema';
COMMENT ON TABLE requesters IS 'Personas que solicitan RFX dentro de las empresas';
COMMENT ON TABLE suppliers IS 'Proveedores que pueden responder a RFX';
COMMENT ON TABLE product_catalog IS 'Catálogo de productos y servicios disponibles';
COMMENT ON TABLE rfx_products IS 'Productos específicos solicitados en cada RFX';
COMMENT ON TABLE generated_documents IS 'Documentos generados por el sistema (propuestas, cotizaciones, etc.)';

-- Comentarios de pricing
COMMENT ON TABLE rfx_pricing_configurations IS 'Configuraciones principales de pricing por RFX';
COMMENT ON TABLE coordination_configurations IS 'Configuraciones independientes de coordinación y logística';
COMMENT ON TABLE cost_per_person_configurations IS 'Configuraciones independientes de costo por persona';
COMMENT ON TABLE tax_configurations IS 'Configuraciones de impuestos y tasas adicionales';
COMMENT ON TABLE pricing_configuration_history IS 'Historial completo de cambios en configuraciones de pricing';

-- Comentarios de campos importantes
COMMENT ON COLUMN rfx_v2.requirements IS 'Requerimientos extraídos del texto del RFX';
COMMENT ON COLUMN rfx_v2.requirements_confidence IS 'Nivel de confianza en la extracción de requerimientos (0-1)';
COMMENT ON COLUMN coordination_configurations.rate IS 'Tasa de coordinación como decimal (0.18 = 18%)';
COMMENT ON COLUMN coordination_configurations.rate_percentage IS 'Tasa calculada automáticamente como porcentaje para display';
COMMENT ON COLUMN cost_per_person_configurations.calculation_base IS 'Base de cálculo: subtotal, subtotal_with_coordination, o final_total';
COMMENT ON COLUMN cost_per_person_configurations.headcount_source IS 'Fuente del headcount: manual, extracted (AI), o estimated';

-- Comentarios de funciones
COMMENT ON FUNCTION get_rfx_pricing_config(UUID) IS 'Obtiene configuración completa de pricing para un RFX específico';
COMMENT ON FUNCTION calculate_rfx_pricing(UUID, DECIMAL) IS 'Calcula pricing completo basado en configuraciones activas';
COMMENT ON FUNCTION get_pricing_usage_stats() IS 'Obtiene estadísticas de uso del sistema de pricing';

COMMIT;

-- ========================
-- VERIFICACIÓN FINAL
-- ========================

SELECT 'Schema V2.2 Complete!' as status;
SELECT 
    'Tables created: ' || COUNT(*) as tables_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

SELECT 
    'Views created: ' || COUNT(*) as views_count
FROM information_schema.views 
WHERE table_schema = 'public';

SELECT 
    'Functions created: ' || COUNT(*) as functions_count
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_type = 'FUNCTION';

SELECT '🎉 ESQUEMA COMPLETO V2.2 CREADO EXITOSAMENTE 🎉' as final_message;
