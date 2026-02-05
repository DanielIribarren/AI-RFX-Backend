-- ============================================
-- MIGRATION: Allow NULL organization_id in product_catalog
-- Version: 4.0
-- Date: 2026-02-02
-- Description: Permitir catálogos individuales (user_id) cuando no hay organización
-- ============================================

-- 1. Permitir NULL en organization_id
ALTER TABLE product_catalog 
ALTER COLUMN organization_id DROP NOT NULL;

-- 2. Agregar user_id como fallback
ALTER TABLE product_catalog 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- 3. Constraint: Debe tener organization_id O user_id (no ambos NULL)
ALTER TABLE product_catalog
ADD CONSTRAINT catalog_owner_check CHECK (
    organization_id IS NOT NULL OR user_id IS NOT NULL
);

-- 4. Índice compuesto para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_product_catalog_owner 
ON product_catalog(organization_id, user_id, is_active);

-- 5. Índice para búsqueda por user_id individual
CREATE INDEX IF NOT EXISTS idx_product_catalog_user 
ON product_catalog(user_id) 
WHERE organization_id IS NULL;

-- ============================================
-- COMENTARIOS
-- ============================================

COMMENT ON COLUMN product_catalog.organization_id IS 
'ID de organización (NULL si es catálogo individual por user_id)';

COMMENT ON COLUMN product_catalog.user_id IS 
'ID de usuario (usado solo si organization_id es NULL)';

COMMENT ON CONSTRAINT catalog_owner_check ON product_catalog IS 
'Garantiza que cada producto pertenece a una organización O a un usuario individual';

-- ============================================
-- VERIFICACIÓN
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 004 completed: product_catalog now supports individual catalogs';
END $$;
