-- ========================
-- MIGRACIÓN: Agregar columna html_template a company_branding_assets
-- Fecha: 2025-11-05
-- Propósito: Soportar sistema de 3 agentes AI para generación de propuestas
-- ========================

-- IMPORTANTE: Esta migración es SEGURA y NO afecta datos existentes
-- Solo agrega una nueva columna opcional

BEGIN;

-- ========================
-- VERIFICAR SI LA COLUMNA YA EXISTE
-- ========================

DO $$
BEGIN
    -- Verificar si la columna ya existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'company_branding_assets' 
        AND column_name = 'html_template'
    ) THEN
        -- Agregar columna html_template
        ALTER TABLE company_branding_assets
        ADD COLUMN html_template TEXT;
        
        RAISE NOTICE '✅ Columna html_template agregada exitosamente';
    ELSE
        RAISE NOTICE '⚠️ Columna html_template ya existe - no se requiere acción';
    END IF;
END $$;

-- ========================
-- COMENTARIO DE DOCUMENTACIÓN
-- ========================

COMMENT ON COLUMN company_branding_assets.html_template IS 
'Template HTML generado automáticamente basado en análisis de branding. 
Usado por el sistema de 3 agentes AI (ProposalGenerator, TemplateValidator, PDFOptimizer) 
para generar propuestas consistentes con el branding del usuario.
Contiene variables {{VAR}} que son reemplazadas con datos del RFX.';

-- ========================
-- VERIFICACIÓN POST-MIGRACIÓN
-- ========================

-- Mostrar estructura actualizada de la tabla
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'company_branding_assets'
AND column_name IN ('logo_analysis', 'template_analysis', 'html_template')
ORDER BY ordinal_position;

COMMIT;

-- ========================
-- ROLLBACK (Si es necesario)
-- ========================

-- Para revertir esta migración, ejecutar:
-- ALTER TABLE company_branding_assets DROP COLUMN IF EXISTS html_template;
