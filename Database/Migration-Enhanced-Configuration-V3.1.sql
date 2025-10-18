-- 🎯 Migration V3.1: Extensión Inteligente del Sistema de Configuración Existente
-- Versión: 3.1 - Enhanced Configuration System
-- Fecha: 2025-10-10
-- Descripción: Extiende tablas existentes en lugar de crear nuevas, elimina inconsistencias

-- =====================================================
-- EXTENSIÓN DE TABLAS EXISTENTES
-- =====================================================

-- 1. Extender company_branding_assets para mejores defaults por usuario
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS use_as_default BOOLEAN DEFAULT true;
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS primary_color_extracted VARCHAR(7);
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS secondary_color_extracted VARCHAR(7);
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS dominant_colors_extracted JSONB DEFAULT '[]';
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS template_layout_detected VARCHAR(50);
ALTER TABLE company_branding_assets ADD COLUMN IF NOT EXISTS industry_detected VARCHAR(50);

-- 2. Extender rfx_pricing_configurations para configuraciones por usuario
ALTER TABLE rfx_pricing_configurations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE rfx_pricing_configurations ADD COLUMN IF NOT EXISTS is_user_default BOOLEAN DEFAULT false;
ALTER TABLE rfx_pricing_configurations ADD COLUMN IF NOT EXISTS auto_applied BOOLEAN DEFAULT false;
ALTER TABLE rfx_pricing_configurations ADD COLUMN IF NOT EXISTS configuration_source VARCHAR(50) DEFAULT 'manual';

-- 3. Agregar campos de inteligencia a las configuraciones existentes
ALTER TABLE coordination_configurations ADD COLUMN IF NOT EXISTS auto_detected BOOLEAN DEFAULT false;
ALTER TABLE coordination_configurations ADD COLUMN IF NOT EXISTS industry_rule VARCHAR(50);
ALTER TABLE coordination_configurations ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2) DEFAULT 1.00;

ALTER TABLE cost_per_person_configurations ADD COLUMN IF NOT EXISTS auto_detected BOOLEAN DEFAULT false;
ALTER TABLE cost_per_person_configurations ADD COLUMN IF NOT EXISTS headcount_auto_source VARCHAR(50);
ALTER TABLE cost_per_person_configurations ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2) DEFAULT 1.00;

-- =====================================================
-- TABLA NUEVA: user_configuration_defaults (Mínima)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_configuration_defaults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Referencias a configuraciones existentes
    default_pricing_config_id UUID REFERENCES rfx_pricing_configurations(id),
    default_branding_asset_id UUID REFERENCES company_branding_assets(id),
    
    -- Configuraciones básicas por usuario
    preferred_currency VARCHAR(3) DEFAULT 'USD',
    preferred_language VARCHAR(5) DEFAULT 'es',
    industry_preference VARCHAR(50),
    
    -- Flags de automatización
    auto_apply_branding BOOLEAN DEFAULT true,
    auto_detect_industry BOOLEAN DEFAULT true,
    auto_detect_currency BOOLEAN DEFAULT true,
    learn_from_usage BOOLEAN DEFAULT true,
    
    -- Estadísticas
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.00,
    last_applied_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_user_config_defaults_user_id ON user_configuration_defaults(user_id);
CREATE INDEX IF NOT EXISTS idx_user_config_defaults_pricing ON user_configuration_defaults(default_pricing_config_id);
CREATE INDEX IF NOT EXISTS idx_user_config_defaults_branding ON user_configuration_defaults(default_branding_asset_id);

-- =====================================================
-- TABLA DE TEMPLATES POR INDUSTRIA (Simplificada)
-- =====================================================

CREATE TABLE IF NOT EXISTS industry_configuration_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_name VARCHAR(50) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    
    -- Configuraciones recomendadas
    coordination_enabled BOOLEAN DEFAULT true,
    coordination_rate DECIMAL(4,3) DEFAULT 0.18,
    cost_per_person_enabled BOOLEAN DEFAULT false,
    default_headcount INTEGER DEFAULT 50,
    
    -- Reglas de negocio básicas
    business_rules JSONB DEFAULT '{}',
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(industry_name, template_name)
);

-- Insertar templates básicos
INSERT INTO industry_configuration_templates (industry_name, template_name, coordination_enabled, coordination_rate, cost_per_person_enabled, default_headcount, business_rules) VALUES
('catering', 'Catering Corporativo', true, 0.18, true, 50, '{"include_logistics": true, "cost_per_person_priority": true}'),
('construction', 'Construcción', true, 0.15, false, 0, '{"include_logistics": true, "material_focused": true}'),
('events', 'Eventos', true, 0.20, true, 100, '{"include_logistics": true, "cost_per_person_priority": true}'),
('technology', 'Tecnología', false, 0.10, false, 0, '{"include_logistics": false, "hourly_based": true}'),
('logistics', 'Logística', true, 0.15, false, 0, '{"include_logistics": true, "transport_focused": true}'),
('consulting', 'Consultoría', false, 0.05, false, 0, '{"include_logistics": false, "expertise_based": true}')
ON CONFLICT (industry_name, template_name) DO UPDATE SET
    coordination_rate = EXCLUDED.coordination_rate,
    business_rules = EXCLUDED.business_rules,
    updated_at = NOW();

-- =====================================================
-- VISTAS OPTIMIZADAS USANDO TABLAS EXISTENTES
-- =====================================================

-- Vista unificada: usuario con su configuración completa
CREATE OR REPLACE VIEW user_unified_configuration AS
SELECT 
    u.id as user_id,
    u.email,
    u.full_name,
    
    -- Configuración por defecto del usuario
    ucd.id as default_config_id,
    ucd.preferred_currency,
    ucd.preferred_language,
    ucd.industry_preference,
    ucd.auto_apply_branding,
    ucd.usage_count,
    ucd.success_rate,
    
    -- Branding assets por defecto
    ba.id as branding_asset_id,
    ba.logo_url,
    ba.template_url,
    ba.logo_analysis,
    ba.template_analysis,
    ba.analysis_status,
    ba.primary_color_extracted,
    ba.secondary_color_extracted,
    ba.template_layout_detected,
    ba.industry_detected,
    
    -- Configuración de pricing por defecto
    rpc.id as pricing_config_id,
    rpc.configuration_name,
    rpc.is_active as pricing_active,
    
    -- Configuración de coordinación
    cc.is_enabled as coordination_enabled,
    cc.rate as coordination_rate,
    cc.coordination_type,
    cc.auto_detected as coordination_auto_detected,
    
    -- Configuración de costo per persona
    cpp.is_enabled as cost_per_person_enabled,
    cpp.headcount,
    cpp.headcount_source,
    cpp.auto_detected as cpp_auto_detected,
    
    -- Configuración de impuestos
    tc.is_enabled as taxes_enabled,
    tc.tax_rate,
    tc.tax_name,
    
    -- Timestamps
    GREATEST(
        COALESCE(ucd.updated_at, '1970-01-01'::timestamp),
        COALESCE(ba.updated_at, '1970-01-01'::timestamp),
        COALESCE(rpc.updated_at, '1970-01-01'::timestamp)
    ) as last_config_update
    
FROM users u
LEFT JOIN user_configuration_defaults ucd ON u.id = ucd.user_id
LEFT JOIN company_branding_assets ba ON ucd.default_branding_asset_id = ba.id AND ba.is_active = true
LEFT JOIN rfx_pricing_configurations rpc ON ucd.default_pricing_config_id = rpc.id AND rpc.is_active = true
LEFT JOIN coordination_configurations cc ON rpc.id = cc.pricing_config_id
LEFT JOIN cost_per_person_configurations cpp ON rpc.id = cpp.pricing_config_id  
LEFT JOIN tax_configurations tc ON rpc.id = tc.pricing_config_id;

-- Vista para configuración final por RFX (hereda defaults del usuario)
CREATE OR REPLACE VIEW rfx_effective_configuration AS
SELECT 
    r.id as rfx_id,
    r.user_id,
    r.currency as rfx_currency,
    
    -- Configuración efectiva (RFX specific o user default)
    COALESCE(rfx_rpc.id, ucd.default_pricing_config_id) as effective_pricing_config_id,
    COALESCE(rfx_ba.id, ucd.default_branding_asset_id) as effective_branding_asset_id,
    
    -- Moneda efectiva (RFX > User > Default)
    COALESCE(r.currency, ucd.preferred_currency, 'USD') as effective_currency,
    
    -- Branding efectivo
    COALESCE(rfx_ba.logo_url, user_ba.logo_url) as effective_logo_url,
    COALESCE(rfx_ba.primary_color_extracted, user_ba.primary_color_extracted, '#2c5f7c') as effective_primary_color,
    COALESCE(rfx_ba.template_analysis, user_ba.template_analysis) as effective_template_analysis,
    
    -- Pricing efectivo
    COALESCE(rfx_cc.is_enabled, user_cc.is_enabled, false) as effective_coordination_enabled,
    COALESCE(rfx_cc.rate, user_cc.rate, 0.18) as effective_coordination_rate,
    COALESCE(rfx_cpp.is_enabled, user_cpp.is_enabled, false) as effective_cost_per_person_enabled,
    COALESCE(rfx_cpp.headcount, user_cpp.headcount, 50) as effective_headcount,
    COALESCE(rfx_tc.is_enabled, user_tc.is_enabled, false) as effective_taxes_enabled,
    COALESCE(rfx_tc.tax_rate, user_tc.tax_rate, 0.16) as effective_tax_rate,
    
    -- Flags de origen
    (rfx_rpc.id IS NOT NULL) as has_rfx_specific_pricing,
    (rfx_ba.id IS NOT NULL) as has_rfx_specific_branding,
    (ucd.id IS NOT NULL) as has_user_defaults,
    
    -- Auto-detection flags
    COALESCE(rfx_cc.auto_detected, user_cc.auto_detected, false) as coordination_auto_detected,
    COALESCE(rfx_cpp.auto_detected, user_cpp.auto_detected, false) as cpp_auto_detected
    
FROM rfx_v2 r
LEFT JOIN user_configuration_defaults ucd ON r.user_id = ucd.user_id

-- RFX-specific configurations
LEFT JOIN rfx_pricing_configurations rfx_rpc ON r.id = rfx_rpc.rfx_id AND rfx_rpc.is_active = true AND rfx_rpc.is_user_default = false
LEFT JOIN coordination_configurations rfx_cc ON rfx_rpc.id = rfx_cc.pricing_config_id
LEFT JOIN cost_per_person_configurations rfx_cpp ON rfx_rpc.id = rfx_cpp.pricing_config_id
LEFT JOIN tax_configurations rfx_tc ON rfx_rpc.id = rfx_tc.pricing_config_id

-- User default configurations
LEFT JOIN rfx_pricing_configurations user_rpc ON ucd.default_pricing_config_id = user_rpc.id AND user_rpc.is_active = true
LEFT JOIN coordination_configurations user_cc ON user_rpc.id = user_cc.pricing_config_id
LEFT JOIN cost_per_person_configurations user_cpp ON user_rpc.id = user_cpp.pricing_config_id
LEFT JOIN tax_configurations user_tc ON user_rpc.id = user_tc.pricing_config_id

-- Branding assets
LEFT JOIN company_branding_assets rfx_ba ON r.user_id = rfx_ba.user_id AND rfx_ba.is_active = true AND rfx_ba.use_as_default = false
LEFT JOIN company_branding_assets user_ba ON ucd.default_branding_asset_id = user_ba.id AND user_ba.is_active = true;

-- =====================================================
-- FUNCIONES PARA EL SERVICIO UNIFICADO
-- =====================================================

-- Función para obtener configuración unificada por usuario
CREATE OR REPLACE FUNCTION get_user_unified_budget_config(p_user_id UUID)
RETURNS TABLE (
    user_id UUID,
    has_defaults BOOLEAN,
    branding_config JSONB,
    pricing_config JSONB,
    document_config JSONB,
    auto_settings JSONB,
    statistics JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        uuc.user_id,
        (uuc.default_config_id IS NOT NULL) as has_defaults,
        
        -- Branding configuration
        jsonb_build_object(
            'logo_url', uuc.logo_url,
            'template_url', uuc.template_url,
            'primary_color', COALESCE(uuc.primary_color_extracted, '#2c5f7c'),
            'secondary_color', COALESCE(uuc.secondary_color_extracted, '#ffffff'),
            'template_analysis', uuc.template_analysis,
            'template_layout', uuc.template_layout_detected,
            'industry_detected', uuc.industry_detected,
            'analysis_status', uuc.analysis_status
        ) as branding_config,
        
        -- Pricing configuration
        jsonb_build_object(
            'coordination_enabled', COALESCE(uuc.coordination_enabled, false),
            'coordination_rate', COALESCE(uuc.coordination_rate, 0.18),
            'coordination_type', uuc.coordination_type,
            'cost_per_person_enabled', COALESCE(uuc.cost_per_person_enabled, false),
            'headcount', COALESCE(uuc.headcount, 50),
            'headcount_source', uuc.headcount_source,
            'taxes_enabled', COALESCE(uuc.taxes_enabled, false),
            'tax_rate', COALESCE(uuc.tax_rate, 0.16),
            'tax_name', COALESCE(uuc.tax_name, 'IVA')
        ) as pricing_config,
        
        -- Document configuration
        jsonb_build_object(
            'currency', COALESCE(uuc.preferred_currency, 'USD'),
            'language', COALESCE(uuc.preferred_language, 'es'),
            'industry', uuc.industry_preference
        ) as document_config,
        
        -- Auto settings
        jsonb_build_object(
            'auto_apply_branding', COALESCE(uuc.auto_apply_branding, true),
            'coordination_auto_detected', COALESCE(uuc.coordination_auto_detected, false),
            'cpp_auto_detected', COALESCE(uuc.cpp_auto_detected, false)
        ) as auto_settings,
        
        -- Statistics
        jsonb_build_object(
            'usage_count', COALESCE(uuc.usage_count, 0),
            'success_rate', COALESCE(uuc.success_rate, 1.00),
            'last_config_update', uuc.last_config_update
        ) as statistics
        
    FROM user_unified_configuration uuc
    WHERE uuc.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener configuración efectiva por RFX
CREATE OR REPLACE FUNCTION get_rfx_effective_budget_config(p_rfx_id UUID)
RETURNS TABLE (
    rfx_id UUID,
    user_id UUID,
    effective_config JSONB,
    source_info JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rec.rfx_id,
        rec.user_id,
        
        -- Configuración efectiva final
        jsonb_build_object(
            'branding', jsonb_build_object(
                'logo_url', rec.effective_logo_url,
                'primary_color', rec.effective_primary_color,
                'template_analysis', rec.effective_template_analysis
            ),
            'pricing', jsonb_build_object(
                'coordination_enabled', rec.effective_coordination_enabled,
                'coordination_rate', rec.effective_coordination_rate,
                'cost_per_person_enabled', rec.effective_cost_per_person_enabled,
                'headcount', rec.effective_headcount,
                'taxes_enabled', rec.effective_taxes_enabled,
                'tax_rate', rec.effective_tax_rate
            ),
            'document', jsonb_build_object(
                'currency', rec.effective_currency
            )
        ) as effective_config,
        
        -- Información de origen
        jsonb_build_object(
            'has_rfx_specific_pricing', rec.has_rfx_specific_pricing,
            'has_rfx_specific_branding', rec.has_rfx_specific_branding,
            'has_user_defaults', rec.has_user_defaults,
            'coordination_auto_detected', rec.coordination_auto_detected,
            'cpp_auto_detected', rec.cpp_auto_detected
        ) as source_info
        
    FROM rfx_effective_configuration rec
    WHERE rec.rfx_id = p_rfx_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNCIONES DE INTELIGENCIA Y AUTOMATIZACIÓN
-- =====================================================

-- Función para crear configuración por defecto inteligente para un usuario
CREATE OR REPLACE FUNCTION create_smart_user_defaults(p_user_id UUID, p_industry VARCHAR(50) DEFAULT NULL)
RETURNS UUID AS $$
DECLARE
    v_config_id UUID;
    v_pricing_config_id UUID;
    v_template_config RECORD;
BEGIN
    -- Obtener template de industria si se especifica
    IF p_industry IS NOT NULL THEN
        SELECT * INTO v_template_config 
        FROM industry_configuration_templates 
        WHERE industry_name = p_industry AND is_active = true
        LIMIT 1;
    END IF;
    
    -- Crear configuración de pricing por defecto
    INSERT INTO rfx_pricing_configurations (
        user_id,
        configuration_name,
        is_user_default,
        auto_applied,
        configuration_source
    ) VALUES (
        p_user_id,
        COALESCE(v_template_config.template_name, 'Default User Configuration'),
        true,
        true,
        COALESCE('industry_template_' || p_industry, 'smart_default')
    ) RETURNING id INTO v_pricing_config_id;
    
    -- Crear configuraciones hijas basadas en template
    INSERT INTO coordination_configurations (
        pricing_config_id,
        is_enabled,
        rate,
        coordination_type,
        auto_detected,
        industry_rule,
        configuration_source
    ) VALUES (
        v_pricing_config_id,
        COALESCE(v_template_config.coordination_enabled, true),
        COALESCE(v_template_config.coordination_rate, 0.18),
        'standard',
        (p_industry IS NOT NULL),
        p_industry,
        'smart_default'
    );
    
    INSERT INTO cost_per_person_configurations (
        pricing_config_id,
        is_enabled,
        headcount,
        auto_detected,
        headcount_auto_source
    ) VALUES (
        v_pricing_config_id,
        COALESCE(v_template_config.cost_per_person_enabled, false),
        COALESCE(v_template_config.default_headcount, 50),
        (p_industry IS NOT NULL),
        CASE WHEN p_industry IS NOT NULL THEN 'industry_template' ELSE 'default' END
    );
    
    -- Crear registro de defaults del usuario
    INSERT INTO user_configuration_defaults (
        user_id,
        default_pricing_config_id,
        industry_preference,
        auto_apply_branding,
        auto_detect_industry,
        configuration_source
    ) VALUES (
        p_user_id,
        v_pricing_config_id,
        p_industry,
        true,
        true,
        'smart_creation'
    ) RETURNING id INTO v_config_id;
    
    RETURN v_config_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS PARA AUTOMATIZACIÓN
-- =====================================================

-- Trigger para crear defaults automáticamente cuando se crea un usuario
CREATE OR REPLACE FUNCTION auto_create_user_defaults()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo crear si no existe ya
    IF NOT EXISTS (SELECT 1 FROM user_configuration_defaults WHERE user_id = NEW.id) THEN
        PERFORM create_smart_user_defaults(NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_create_user_defaults_trigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_user_defaults();

-- Trigger para actualizar estadísticas de uso
CREATE OR REPLACE FUNCTION update_config_usage_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Actualizar estadísticas del usuario
    UPDATE user_configuration_defaults 
    SET 
        usage_count = usage_count + 1,
        last_applied_at = NOW()
    WHERE user_id = (SELECT user_id FROM rfx_v2 WHERE id = NEW.rfx_id);
    
    -- Actualizar contadores de templates de industria si aplica
    UPDATE industry_configuration_templates
    SET usage_count = usage_count + 1
    WHERE industry_name = (
        SELECT industry_preference 
        FROM user_configuration_defaults ucd
        JOIN rfx_v2 r ON ucd.user_id = r.user_id
        WHERE r.id = NEW.rfx_id
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_config_usage_stats_trigger
    AFTER INSERT ON generated_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_config_usage_stats();

-- =====================================================
-- ÍNDICES ADICIONALES PARA PERFORMANCE
-- =====================================================

-- Índices para las nuevas columnas
CREATE INDEX IF NOT EXISTS idx_rfx_pricing_user_id ON rfx_pricing_configurations(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rfx_pricing_user_default ON rfx_pricing_configurations(user_id, is_user_default) WHERE is_user_default = true;
CREATE INDEX IF NOT EXISTS idx_branding_assets_default ON company_branding_assets(user_id, use_as_default) WHERE use_as_default = true;

-- Índices para búsquedas por industria
CREATE INDEX IF NOT EXISTS idx_branding_assets_industry ON company_branding_assets(industry_detected) WHERE industry_detected IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_coordination_industry ON coordination_configurations(industry_rule) WHERE industry_rule IS NOT NULL;

-- =====================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- =====================================================

COMMENT ON TABLE user_configuration_defaults IS 'Configuraciones por defecto por usuario - unifica branding y pricing usando tablas existentes';
COMMENT ON TABLE industry_configuration_templates IS 'Templates de configuración por industria para automatización inteligente';

COMMENT ON FUNCTION get_user_unified_budget_config(UUID) IS 'Obtiene configuración completa unificada por usuario usando tablas existentes';
COMMENT ON FUNCTION get_rfx_effective_budget_config(UUID) IS 'Obtiene configuración efectiva por RFX con herencia de defaults del usuario';
COMMENT ON FUNCTION create_smart_user_defaults(UUID, VARCHAR) IS 'Crea configuración inteligente por defecto basada en industria detectada';

-- =====================================================
-- MIGRATION LOG
-- =====================================================

-- Crear tabla de log si no existe
CREATE TABLE IF NOT EXISTS migration_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

-- Registrar esta migración
INSERT INTO migration_log (migration_name, version, description, executed_at) VALUES 
('Migration-Enhanced-Configuration', '3.1', 'Extensión inteligente del sistema de configuración existente - mantiene tablas actuales', NOW())
ON CONFLICT (migration_name) DO UPDATE SET 
    version = EXCLUDED.version,
    description = EXCLUDED.description,
    executed_at = EXCLUDED.executed_at;
