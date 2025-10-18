-- 🎯 Migration: Sistema Unificado de Configuración de Presupuestos
-- Versión: 3.1 - Unified Budget Configuration System
-- Fecha: 2025-10-10
-- Descripción: Elimina inconsistencias y crea sistema inteligente centralizado

-- =====================================================
-- TABLA PRINCIPAL: user_budget_configurations
-- =====================================================

CREATE TABLE IF NOT EXISTS user_budget_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- BRANDING CONFIGURATION
    use_custom_branding BOOLEAN DEFAULT false,
    branding_asset_id UUID REFERENCES company_branding_assets(id),
    primary_color VARCHAR(7) DEFAULT '#2c5f7c',
    secondary_color VARCHAR(7) DEFAULT '#ffffff',
    logo_position VARCHAR(20) DEFAULT 'top-left',
    template_layout VARCHAR(50) DEFAULT 'header-client-products-totals',
    
    -- PRICING CONFIGURATION DEFAULTS
    default_coordination_enabled BOOLEAN DEFAULT true,
    default_coordination_rate DECIMAL(4,3) DEFAULT 0.18,
    default_coordination_type VARCHAR(20) DEFAULT 'standard',
    
    default_cost_per_person_enabled BOOLEAN DEFAULT false,
    default_headcount INTEGER DEFAULT 50,
    default_headcount_source VARCHAR(20) DEFAULT 'manual',
    
    default_taxes_enabled BOOLEAN DEFAULT false,
    default_tax_rate DECIMAL(4,3) DEFAULT 0.16,
    default_tax_name VARCHAR(50) DEFAULT 'IVA',
    
    -- DOCUMENT CONFIGURATION
    preferred_currency VARCHAR(3) DEFAULT 'USD',
    preferred_language VARCHAR(5) DEFAULT 'es',
    industry_template VARCHAR(50),
    document_style VARCHAR(20) DEFAULT 'professional',
    
    -- SMART LEARNING FEATURES
    auto_apply_branding BOOLEAN DEFAULT true,
    auto_detect_industry BOOLEAN DEFAULT true,
    auto_detect_currency BOOLEAN DEFAULT true,
    learn_from_usage BOOLEAN DEFAULT true,
    
    -- METADATA Y TRACKING
    configuration_source VARCHAR(20) DEFAULT 'user_setup',
    is_active BOOLEAN DEFAULT true,
    last_applied_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.00,
    
    -- TIMESTAMPS
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- CONSTRAINTS
    UNIQUE(user_id) WHERE is_active = true,
    
    -- VALIDATIONS
    CONSTRAINT valid_coordination_rate CHECK (default_coordination_rate >= 0 AND default_coordination_rate <= 1),
    CONSTRAINT valid_tax_rate CHECK (default_tax_rate >= 0 AND default_tax_rate <= 1),
    CONSTRAINT valid_headcount CHECK (default_headcount > 0),
    CONSTRAINT valid_success_rate CHECK (success_rate >= 0 AND success_rate <= 1)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_user_budget_config_user_id ON user_budget_configurations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_budget_config_active ON user_budget_configurations(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_user_budget_config_branding ON user_budget_configurations(branding_asset_id) WHERE branding_asset_id IS NOT NULL;

-- =====================================================
-- TABLA DE OVERRIDES: rfx_configuration_overrides  
-- =====================================================

CREATE TABLE IF NOT EXISTS rfx_configuration_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    user_config_id UUID REFERENCES user_budget_configurations(id),
    
    -- OVERRIDE FLAGS
    override_branding BOOLEAN DEFAULT false,
    override_pricing BOOLEAN DEFAULT false,
    override_currency BOOLEAN DEFAULT false,
    override_language BOOLEAN DEFAULT false,
    
    -- BRANDING OVERRIDES
    custom_primary_color VARCHAR(7),
    custom_logo_position VARCHAR(20),
    custom_template_layout VARCHAR(50),
    
    -- PRICING OVERRIDES
    coordination_enabled_override BOOLEAN,
    coordination_rate_override DECIMAL(4,3),
    cost_per_person_enabled_override BOOLEAN,
    headcount_override INTEGER,
    taxes_enabled_override BOOLEAN,
    tax_rate_override DECIMAL(4,3),
    
    -- DOCUMENT OVERRIDES
    currency_override VARCHAR(3),
    language_override VARCHAR(5),
    
    -- METADATA
    override_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'user',
    
    -- CONSTRAINTS
    UNIQUE(rfx_id),
    
    -- VALIDATIONS
    CONSTRAINT valid_coordination_rate_override CHECK (coordination_rate_override IS NULL OR (coordination_rate_override >= 0 AND coordination_rate_override <= 1)),
    CONSTRAINT valid_tax_rate_override CHECK (tax_rate_override IS NULL OR (tax_rate_override >= 0 AND tax_rate_override <= 1)),
    CONSTRAINT valid_headcount_override CHECK (headcount_override IS NULL OR headcount_override > 0)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_rfx_config_overrides_rfx_id ON rfx_configuration_overrides(rfx_id);
CREATE INDEX IF NOT EXISTS idx_rfx_config_overrides_user_config ON rfx_configuration_overrides(user_config_id);

-- =====================================================
-- TABLA DE TEMPLATES POR INDUSTRIA
-- =====================================================

CREATE TABLE IF NOT EXISTS industry_budget_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_name VARCHAR(50) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    
    -- CONFIGURACIONES PREDETERMINADAS POR INDUSTRIA
    default_coordination_enabled BOOLEAN DEFAULT true,
    default_coordination_rate DECIMAL(4,3) DEFAULT 0.18,
    default_cost_per_person_enabled BOOLEAN DEFAULT false,
    default_headcount INTEGER DEFAULT 50,
    
    -- CONFIGURACIONES DE DISEÑO
    recommended_colors JSONB DEFAULT '{"primary": "#2c5f7c", "secondary": "#ffffff"}',
    layout_preferences JSONB DEFAULT '{"structure": "header-client-products-totals"}',
    section_priorities JSONB DEFAULT '[]',
    
    -- REGLAS DE NEGOCIO
    business_rules JSONB DEFAULT '{}',
    calculation_rules JSONB DEFAULT '{}',
    
    -- METADATA
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(industry_name, template_name)
);

-- Datos iniciales de industrias
INSERT INTO industry_budget_templates (industry_name, template_name, default_coordination_enabled, default_coordination_rate, default_cost_per_person_enabled, default_headcount, business_rules) VALUES
('catering', 'Catering Corporativo', true, 0.18, true, 50, '{"include_logistics": true, "cost_per_person_priority": "high", "categories": ["appetizers", "main_course", "beverages", "desserts"]}'),
('construction', 'Construcción y Obras', true, 0.15, false, 0, '{"include_logistics": true, "material_categories": true, "labor_separate": true}'),
('events', 'Eventos y Celebraciones', true, 0.20, true, 100, '{"include_logistics": true, "cost_per_person_priority": "high", "venue_coordination": true}'),
('technology', 'Servicios Tecnológicos', false, 0.10, false, 0, '{"include_logistics": false, "hourly_rates": true, "project_phases": true}'),
('logistics', 'Logística y Transporte', true, 0.15, false, 0, '{"include_logistics": true, "distance_based": true, "vehicle_types": true}'),
('consulting', 'Consultoría Profesional', false, 0.05, false, 0, '{"include_logistics": false, "hourly_rates": true, "expertise_levels": true}');

-- =====================================================
-- VISTAS OPTIMIZADAS
-- =====================================================

-- Vista unificada de configuración completa por usuario
CREATE OR REPLACE VIEW user_complete_budget_config AS
SELECT 
    u.id as user_id,
    u.email,
    u.full_name,
    
    -- Configuración unificada
    ubc.id as config_id,
    ubc.use_custom_branding,
    ubc.primary_color,
    ubc.secondary_color,
    ubc.logo_position,
    ubc.template_layout,
    
    -- Pricing defaults
    ubc.default_coordination_enabled,
    ubc.default_coordination_rate,
    ubc.default_cost_per_person_enabled,
    ubc.default_headcount,
    ubc.default_taxes_enabled,
    ubc.default_tax_rate,
    ubc.default_tax_name,
    
    -- Document config
    ubc.preferred_currency,
    ubc.preferred_language,
    ubc.industry_template,
    ubc.document_style,
    
    -- Branding assets (si existe)
    ba.logo_url,
    ba.template_url,
    ba.logo_analysis,
    ba.template_analysis,
    ba.analysis_status,
    
    -- Estadísticas
    ubc.usage_count,
    ubc.success_rate,
    ubc.last_applied_at,
    ubc.created_at,
    ubc.updated_at
    
FROM users u
LEFT JOIN user_budget_configurations ubc ON u.id = ubc.user_id AND ubc.is_active = true
LEFT JOIN company_branding_assets ba ON ubc.branding_asset_id = ba.id AND ba.is_active = true;

-- Vista de configuración final por RFX (con overrides aplicados)
CREATE OR REPLACE VIEW rfx_final_budget_config AS
SELECT 
    r.id as rfx_id,
    r.user_id,
    
    -- Configuración final (con overrides aplicados)
    CASE 
        WHEN rco.override_branding = true THEN rco.custom_primary_color
        ELSE ubc.primary_color 
    END as final_primary_color,
    
    CASE 
        WHEN rco.override_branding = true THEN rco.custom_logo_position
        ELSE ubc.logo_position 
    END as final_logo_position,
    
    CASE 
        WHEN rco.override_pricing = true THEN rco.coordination_enabled_override
        ELSE ubc.default_coordination_enabled 
    END as final_coordination_enabled,
    
    CASE 
        WHEN rco.override_pricing = true AND rco.coordination_rate_override IS NOT NULL THEN rco.coordination_rate_override
        ELSE ubc.default_coordination_rate 
    END as final_coordination_rate,
    
    CASE 
        WHEN rco.override_pricing = true THEN rco.cost_per_person_enabled_override
        ELSE ubc.default_cost_per_person_enabled 
    END as final_cost_per_person_enabled,
    
    CASE 
        WHEN rco.override_pricing = true AND rco.headcount_override IS NOT NULL THEN rco.headcount_override
        ELSE ubc.default_headcount 
    END as final_headcount,
    
    CASE 
        WHEN rco.override_currency = true THEN rco.currency_override
        ELSE COALESCE(r.currency, ubc.preferred_currency)
    END as final_currency,
    
    -- Metadata
    ubc.use_custom_branding,
    ubc.branding_asset_id,
    rco.id as has_overrides,
    rco.override_reason,
    
    -- Timestamps
    GREATEST(ubc.updated_at, COALESCE(rco.created_at, '1970-01-01'::timestamp)) as config_last_updated
    
FROM rfx_v2 r
LEFT JOIN user_budget_configurations ubc ON r.user_id = ubc.user_id AND ubc.is_active = true
LEFT JOIN rfx_configuration_overrides rco ON r.id = rco.rfx_id;

-- =====================================================
-- FUNCIONES UTILITARIAS
-- =====================================================

-- Función para obtener configuración unificada por usuario
CREATE OR REPLACE FUNCTION get_user_unified_config(p_user_id UUID)
RETURNS TABLE (
    config_id UUID,
    branding_config JSONB,
    pricing_config JSONB,
    document_config JSONB,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ubc.id as config_id,
        
        -- Branding config
        jsonb_build_object(
            'use_custom_branding', ubc.use_custom_branding,
            'branding_asset_id', ubc.branding_asset_id,
            'primary_color', ubc.primary_color,
            'secondary_color', ubc.secondary_color,
            'logo_position', ubc.logo_position,
            'template_layout', ubc.template_layout,
            'logo_url', ba.logo_url,
            'template_url', ba.template_url,
            'logo_analysis', ba.logo_analysis,
            'template_analysis', ba.template_analysis
        ) as branding_config,
        
        -- Pricing config
        jsonb_build_object(
            'coordination_enabled', ubc.default_coordination_enabled,
            'coordination_rate', ubc.default_coordination_rate,
            'coordination_type', ubc.default_coordination_type,
            'cost_per_person_enabled', ubc.default_cost_per_person_enabled,
            'headcount', ubc.default_headcount,
            'taxes_enabled', ubc.default_taxes_enabled,
            'tax_rate', ubc.default_tax_rate,
            'tax_name', ubc.default_tax_name
        ) as pricing_config,
        
        -- Document config
        jsonb_build_object(
            'currency', ubc.preferred_currency,
            'language', ubc.preferred_language,
            'industry_template', ubc.industry_template,
            'document_style', ubc.document_style
        ) as document_config,
        
        -- Metadata
        jsonb_build_object(
            'usage_count', ubc.usage_count,
            'success_rate', ubc.success_rate,
            'last_applied_at', ubc.last_applied_at,
            'auto_apply_branding', ubc.auto_apply_branding,
            'learn_from_usage', ubc.learn_from_usage
        ) as metadata
        
    FROM user_budget_configurations ubc
    LEFT JOIN company_branding_assets ba ON ubc.branding_asset_id = ba.id
    WHERE ubc.user_id = p_user_id AND ubc.is_active = true;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener configuración final por RFX (con overrides)
CREATE OR REPLACE FUNCTION get_rfx_final_config(p_rfx_id UUID)
RETURNS TABLE (
    rfx_id UUID,
    user_id UUID,
    final_config JSONB,
    has_overrides BOOLEAN,
    override_reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id as rfx_id,
        r.user_id,
        
        jsonb_build_object(
            'branding', jsonb_build_object(
                'primary_color', CASE WHEN rco.override_branding = true THEN rco.custom_primary_color ELSE ubc.primary_color END,
                'secondary_color', ubc.secondary_color,
                'logo_position', CASE WHEN rco.override_branding = true THEN rco.custom_logo_position ELSE ubc.logo_position END,
                'template_layout', CASE WHEN rco.override_branding = true THEN rco.custom_template_layout ELSE ubc.template_layout END,
                'logo_url', ba.logo_url,
                'template_analysis', ba.template_analysis
            ),
            'pricing', jsonb_build_object(
                'coordination_enabled', CASE WHEN rco.override_pricing = true THEN rco.coordination_enabled_override ELSE ubc.default_coordination_enabled END,
                'coordination_rate', CASE WHEN rco.override_pricing = true AND rco.coordination_rate_override IS NOT NULL THEN rco.coordination_rate_override ELSE ubc.default_coordination_rate END,
                'cost_per_person_enabled', CASE WHEN rco.override_pricing = true THEN rco.cost_per_person_enabled_override ELSE ubc.default_cost_per_person_enabled END,
                'headcount', CASE WHEN rco.override_pricing = true AND rco.headcount_override IS NOT NULL THEN rco.headcount_override ELSE ubc.default_headcount END,
                'taxes_enabled', CASE WHEN rco.override_pricing = true THEN rco.taxes_enabled_override ELSE ubc.default_taxes_enabled END,
                'tax_rate', CASE WHEN rco.override_pricing = true AND rco.tax_rate_override IS NOT NULL THEN rco.tax_rate_override ELSE ubc.default_tax_rate END
            ),
            'document', jsonb_build_object(
                'currency', CASE WHEN rco.override_currency = true THEN rco.currency_override ELSE COALESCE(r.currency, ubc.preferred_currency) END,
                'language', CASE WHEN rco.override_language = true THEN rco.language_override ELSE ubc.preferred_language END,
                'industry', ubc.industry_template
            )
        ) as final_config,
        
        (rco.id IS NOT NULL) as has_overrides,
        rco.override_reason
        
    FROM rfx_v2 r
    LEFT JOIN user_budget_configurations ubc ON r.user_id = ubc.user_id AND ubc.is_active = true
    LEFT JOIN company_branding_assets ba ON ubc.branding_asset_id = ba.id
    LEFT JOIN rfx_configuration_overrides rco ON r.id = rco.rfx_id
    WHERE r.id = p_rfx_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS PARA MANTENIMIENTO AUTOMÁTICO
-- =====================================================

-- Trigger para actualizar timestamp en user_budget_configurations
CREATE OR REPLACE FUNCTION update_user_budget_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_budget_config_update_timestamp
    BEFORE UPDATE ON user_budget_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_user_budget_config_timestamp();

-- Trigger para incrementar usage_count cuando se aplica una configuración
CREATE OR REPLACE FUNCTION increment_config_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE user_budget_configurations 
    SET 
        usage_count = usage_count + 1,
        last_applied_at = NOW()
    WHERE user_id = (SELECT user_id FROM rfx_v2 WHERE id = NEW.rfx_id);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger cuando se crea un nuevo documento generado
CREATE TRIGGER increment_config_usage_on_generation
    AFTER INSERT ON generated_documents
    FOR EACH ROW
    EXECUTE FUNCTION increment_config_usage();

-- =====================================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- =====================================================

COMMENT ON TABLE user_budget_configurations IS 'Configuración unificada de presupuestos por usuario - elimina fragmentación y duplicación';
COMMENT ON TABLE rfx_configuration_overrides IS 'Overrides específicos por RFX cuando se necesita personalización granular';
COMMENT ON TABLE industry_budget_templates IS 'Templates predefinidos por industria para configuración automática inteligente';

COMMENT ON FUNCTION get_user_unified_config(UUID) IS 'Obtiene configuración completa unificada por usuario con branding y pricing';
COMMENT ON FUNCTION get_rfx_final_config(UUID) IS 'Obtiene configuración final por RFX aplicando overrides cuando existen';

-- =====================================================
-- GRANT PERMISSIONS (ajustar según necesidades)
-- =====================================================

-- Dar permisos a la aplicación (ajustar el rol según tu configuración)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_budget_configurations TO app_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rfx_configuration_overrides TO app_role;
-- GRANT SELECT ON industry_budget_templates TO app_role;
-- GRANT EXECUTE ON FUNCTION get_user_unified_config(UUID) TO app_role;
-- GRANT EXECUTE ON FUNCTION get_rfx_final_config(UUID) TO app_role;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

-- Log de migración
INSERT INTO migration_log (migration_name, version, description, executed_at) VALUES 
('Migration-Unified-Budget-Configuration', '3.1', 'Sistema Unificado de Configuración de Presupuestos - Elimina inconsistencias y crea flujo inteligente', NOW())
ON CONFLICT (migration_name) DO UPDATE SET 
    version = EXCLUDED.version,
    description = EXCLUDED.description,
    executed_at = EXCLUDED.executed_at;
