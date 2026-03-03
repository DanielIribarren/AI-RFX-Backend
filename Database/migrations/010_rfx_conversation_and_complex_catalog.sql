-- ========================================
-- MIGRATION 010: RFX Conversation Memory + Complex Catalog Products
-- ========================================
-- Objetivos:
-- 1) Memoria y estado conversacional estrictamente por RFX (NO por usuario)
-- 2) Soporte de productos complejos tipo bundle/menu en product_catalog

-- ========================
-- 1) PRODUCT CATALOG: CAMPOS PARA PRODUCTOS COMPLEJOS
-- ========================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'product_catalog'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'product_catalog' AND column_name = 'product_type'
        ) THEN
            EXECUTE 'ALTER TABLE public.product_catalog ADD COLUMN product_type TEXT NOT NULL DEFAULT ''simple''';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'product_catalog' AND column_name = 'bundle_schema'
        ) THEN
            EXECUTE 'ALTER TABLE public.product_catalog ADD COLUMN bundle_schema JSONB DEFAULT ''{}''::jsonb';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'product_catalog' AND column_name = 'constraint_rules'
        ) THEN
            EXECUTE 'ALTER TABLE public.product_catalog ADD COLUMN constraint_rules JSONB DEFAULT ''{}''::jsonb';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'product_catalog' AND column_name = 'semantic_tags'
        ) THEN
            EXECUTE 'ALTER TABLE public.product_catalog ADD COLUMN semantic_tags TEXT[] DEFAULT ARRAY[]::TEXT[]';
        END IF;

        -- Constraint idempotente: tipos permitidos
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'product_catalog_product_type_chk'
        ) THEN
            EXECUTE 'ALTER TABLE public.product_catalog ADD CONSTRAINT product_catalog_product_type_chk CHECK (product_type IN (''simple'', ''complex_bundle'', ''service_bundle''))';
        END IF;

        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_product_catalog_product_type ON public.product_catalog(product_type)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_product_catalog_semantic_tags ON public.product_catalog USING gin (semantic_tags)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_product_catalog_bundle_schema ON public.product_catalog USING gin (bundle_schema)';
    END IF;
END
$$;

COMMENT ON COLUMN public.product_catalog.product_type IS 'simple | complex_bundle | service_bundle';
COMMENT ON COLUMN public.product_catalog.bundle_schema IS 'Plantilla JSON del bundle/menu y opciones por slot/dia';
COMMENT ON COLUMN public.product_catalog.constraint_rules IS 'Reglas de selección para aplicar restricciones (ej: low_carb)';
COMMENT ON COLUMN public.product_catalog.semantic_tags IS 'Tags semánticos para matching inteligente de requerimientos';


-- ========================
-- 2) MEMORIA CONVERSACIONAL POR RFX
-- ========================
DO $$
BEGIN
    -- Permitir cantidades decimales para kg/litros/unidades fraccionadas
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_products' AND column_name = 'quantity'
          AND data_type IN ('integer', 'bigint', 'smallint')
    ) THEN
        EXECUTE 'ALTER TABLE public.rfx_products ALTER COLUMN quantity TYPE NUMERIC(12,3) USING quantity::numeric';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.rfx_conversation_state (
    rfx_id UUID PRIMARY KEY REFERENCES public.rfx_v2(id) ON DELETE CASCADE,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active',
    last_intent TEXT,
    last_user_message TEXT,
    last_assistant_message TEXT,
    requires_clarification BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rfx_conversation_state_status_chk CHECK (status IN ('active', 'clarification', 'ready_for_proposal', 'closed'))
);

CREATE TABLE IF NOT EXISTS public.rfx_conversation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES public.rfx_v2(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    message TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rfx_conversation_events_role_chk CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);

CREATE INDEX IF NOT EXISTS idx_rfx_conversation_events_rfx_created_desc
    ON public.rfx_conversation_events (rfx_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rfx_conversation_state_status
    ON public.rfx_conversation_state (status);

CREATE OR REPLACE FUNCTION public.touch_rfx_conversation_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_touch_rfx_conversation_state_updated_at ON public.rfx_conversation_state;
CREATE TRIGGER trg_touch_rfx_conversation_state_updated_at
BEFORE UPDATE ON public.rfx_conversation_state
FOR EACH ROW
EXECUTE FUNCTION public.touch_rfx_conversation_state_updated_at();

COMMENT ON TABLE public.rfx_conversation_state IS 'Estado conversacional por RFX (memoria scoped por rfx_id)';
COMMENT ON TABLE public.rfx_conversation_events IS 'Eventos de conversación por RFX para trazabilidad';

SELECT 'Migration 010 applied: conversation memory by rfx + complex catalog fields' AS status;
