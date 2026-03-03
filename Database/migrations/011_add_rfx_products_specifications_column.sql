-- ========================================
-- MIGRATION 011: Add rfx_products.specifications (compat)
-- ========================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'rfx_products'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_products' AND column_name = 'specifications'
    ) THEN
        EXECUTE 'ALTER TABLE public.rfx_products ADD COLUMN specifications JSONB DEFAULT ''{}''::jsonb';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rfx_products_specifications_gin ON public.rfx_products USING gin (specifications)';
    END IF;
END
$$;

SELECT 'Migration 011 applied' AS status;
