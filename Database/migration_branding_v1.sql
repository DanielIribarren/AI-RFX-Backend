-- ========================
-- MIGRACIÓN: Sistema de Branding Personalizado
-- Versión: 1.0
-- Fecha: 2024-10-01
-- Descripción: Agrega soporte para logos y templates personalizados con análisis cacheado
--
-- ENFOQUE DE ANÁLISIS:
-- 1. LOGO: Se usa DIRECTAMENTE en el HTML (NO se recrea con IA)
--    - Solo extracción básica de colores con Pillow para referencia
--    - El archivo de logo se inserta tal cual en el documento
--
-- 2. TEMPLATE: Análisis SOLO de formato visual con GPT-4 Vision
--    - Analiza: colores, espaciados, distribución, orden de secciones
--    - NO analiza: contenido textual, datos específicos, información del negocio
--    - Enfoque: estructura visual y estilo, no contenido
--
-- 3. CACHE: Análisis se hace UNA VEZ y se guarda en JSONB
--    - Generación de presupuestos usa análisis cacheado (rápido, sin costos repetidos)
-- ========================

BEGIN;

-- ========================
-- TABLA: company_branding_assets
-- ========================

CREATE TABLE IF NOT EXISTS company_branding_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Logo
    logo_filename TEXT,
    logo_path TEXT,
    logo_url TEXT,  -- URL relativa: /static/branding/{company_id}/logo.png
    logo_uploaded_at TIMESTAMPTZ,
    
    -- Análisis de logo (CACHEADO en JSONB)
    -- IMPORTANTE: El logo se usa DIRECTAMENTE en el HTML, NO se recrea
    -- Solo se extraen colores básicos con Pillow para referencia
    logo_analysis JSONB DEFAULT '{}',
    -- Estructura esperada (análisis MÍNIMO):
    -- {
    --   "dominant_colors": ["#2c5f7c", "#ffffff", "#f0f0f0"],
    --   "primary_color": "#2c5f7c",
    --   "secondary_color": "#ffffff",
    --   "has_transparency": true,
    --   "recommended_position": "top-left",
    --   "optimal_dimensions": {"width": 200, "height": 80},
    --   "analyzed_at": "2024-10-01T16:00:00Z",
    --   "analysis_model": "fallback-pillow"
    -- }
    -- NOTA: El logo NO se analiza con IA, solo extracción de colores
    
    -- Template (ejemplo de formato)
    template_filename TEXT,
    template_path TEXT,
    template_url TEXT,  -- URL relativa: /static/branding/{company_id}/template.pdf
    template_uploaded_at TIMESTAMPTZ,
    
    -- Análisis de template (CACHEADO en JSONB)
    -- IMPORTANTE: Analiza SOLO formato visual, NO contenido textual ni datos
    -- Enfoque: colores, espaciados, distribución, orden de secciones
    template_analysis JSONB DEFAULT '{}',
    -- Estructura esperada (SOLO FORMATO VISUAL):
    -- {
    --   "layout_structure": "header-client-products-totals-footer",
    --   "sections": [
    --     {"name": "header", "has_logo_space": true, "logo_position": "top-left", "visual_elements": ["company_name", "document_title", "date_box"]},
    --     {"name": "client_info", "position": "after_header", "layout": "single_column"},
    --     {"name": "products_table", "columns_count": 4, "has_header_row": true},
    --     {"name": "totals", "position": "bottom_right", "layout": "aligned_right"}
    --   ],
    --   "color_scheme": {
    --     "primary": "#2c5f7c",
    --     "secondary": "#ffffff",
    --     "backgrounds": ["#f0f0f0"],
    --     "borders": "#000000",
    --     "text": "#000000"
    --   },
    --   "table_style": {
    --     "has_borders": true,
    --     "border_width": "1px",
    --     "border_color": "#000000",
    --     "header_background": "#f0f0f0",
    --     "alternating_rows": false,
    --     "cell_padding": "6px"
    --   },
    --   "typography": {
    --     "font_family": "Arial, sans-serif",
    --     "company_name_size": "24px",
    --     "title_size": "18px",
    --     "body_size": "11px",
    --     "table_header_weight": "bold"
    --   },
    --   "spacing": {
    --     "section_margins": "20px",
    --     "table_spacing": "10px",
    --     "line_height": "1.5"
    --   },
    --   "design_style": "professional",
    --   "analyzed_at": "2024-10-01T16:00:00Z",
    --   "analysis_model": "gpt-4-vision-preview"
    -- }
    -- NOTA: NO incluye nombres de empresas, productos, precios ni datos específicos
    -- SOLO: Formato, colores, espacios, distribución, orden visual
    
    -- Estado del análisis
    analysis_status TEXT DEFAULT 'pending' CHECK (analysis_status IN ('pending', 'analyzing', 'completed', 'failed')),
    analysis_error TEXT,
    analysis_started_at TIMESTAMPTZ,
    
    -- Configuración activa
    is_active BOOLEAN DEFAULT true,
    
    -- Metadatos
    created_by TEXT,
    updated_by TEXT,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint: Una configuración por empresa
    CONSTRAINT unique_company_branding UNIQUE(company_id)
);

-- ========================
-- ÍNDICES
-- ========================

CREATE INDEX idx_company_branding_company_id ON company_branding_assets(company_id);
CREATE INDEX idx_company_branding_status ON company_branding_assets(analysis_status);
CREATE INDEX idx_company_branding_active ON company_branding_assets(company_id, is_active) WHERE is_active = true;

-- Índices GIN para búsquedas en JSONB (opcional, para queries avanzadas)
CREATE INDEX idx_company_branding_logo_analysis ON company_branding_assets USING GIN (logo_analysis);
CREATE INDEX idx_company_branding_template_analysis ON company_branding_assets USING GIN (template_analysis);

-- ========================
-- TRIGGER PARA updated_at
-- ========================

CREATE TRIGGER update_company_branding_updated_at 
    BEFORE UPDATE ON company_branding_assets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ========================
-- COMENTARIOS DE DOCUMENTACIÓN
-- ========================

COMMENT ON TABLE company_branding_assets IS 'Almacena configuración de branding personalizado por empresa con análisis cacheado. Logo se usa directamente, template se analiza solo formato visual.';

COMMENT ON COLUMN company_branding_assets.logo_analysis IS 'Extracción básica de colores del logo con Pillow (NO usa IA). El logo se inserta directamente en HTML sin recreación.';
COMMENT ON COLUMN company_branding_assets.template_analysis IS 'Análisis de formato visual del template con GPT-4 Vision - SOLO colores, espaciados, distribución, orden. NO analiza contenido textual.';
COMMENT ON COLUMN company_branding_assets.analysis_status IS 'Estado del análisis: pending (inicial), analyzing (en proceso), completed (listo), failed (error)';

-- ========================
-- FUNCIONES AUXILIARES
-- ========================

-- Función para obtener branding con análisis
CREATE OR REPLACE FUNCTION get_company_branding(company_uuid UUID)
RETURNS TABLE (
    id UUID,
    company_id UUID,
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
        cba.company_id,
        cba.logo_url,
        cba.template_url,
        cba.logo_analysis,
        cba.template_analysis,
        cba.analysis_status,
        cba.is_active,
        cba.created_at,
        cba.updated_at
    FROM company_branding_assets cba
    WHERE cba.company_id = company_uuid 
    AND cba.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_company_branding(UUID) IS 'Obtiene configuración de branding activa para una empresa';

-- Función para verificar si empresa tiene branding configurado
CREATE OR REPLACE FUNCTION has_branding_configured(company_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM company_branding_assets 
        WHERE company_id = company_uuid 
        AND is_active = true
        AND analysis_status = 'completed'
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION has_branding_configured(UUID) IS 'Verifica si una empresa tiene branding completamente configurado y analizado';

-- ========================
-- DATOS DE EJEMPLO (OPCIONAL - COMENTADO)
-- ========================

-- Descomentar para insertar datos de prueba
/*
INSERT INTO company_branding_assets (
    company_id,
    logo_url,
    template_url,
    logo_analysis,
    template_analysis,
    analysis_status,
    is_active
) VALUES (
    (SELECT id FROM companies LIMIT 1),  -- Primera empresa
    '/static/branding/example-company/logo.png',
    '/static/branding/example-company/template.pdf',
    '{"primary_color": "#2c5f7c", "secondary_color": "#ffffff", "dominant_colors": ["#2c5f7c", "#ffffff"], "recommended_position": "top-left", "optimal_dimensions": {"width": 200, "height": 80}}'::jsonb,
    '{"layout_structure": "header-client-products-totals", "color_scheme": {"primary": "#2c5f7c", "backgrounds": ["#f0f0f0"]}, "table_style": {"has_borders": true, "border_width": "1px"}}'::jsonb,
    'completed',
    true
);
*/

COMMIT;

-- ========================
-- VERIFICACIÓN
-- ========================

SELECT 'Branding migration completed successfully!' as status;

-- Verificar que la tabla existe
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'company_branding_assets'
ORDER BY ordinal_position;

-- Verificar índices
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'company_branding_assets';
