-- ========================================
-- MIGRATION 009: RFX Performance + Pricing Consistency
-- ========================================
-- Objetivos:
-- 1) Mejorar performance de consultas RFX (historial/listados)
-- 2) Eliminar N+1 para conteo de productos con función batch
-- 3) Garantizar upsert atómico y consistente de pricing
--
-- Notas:
-- - Se usan checks de existencia para tolerar drift entre esquemas.
-- - No se eliminan estructuras existentes.

-- ========================
-- 1) ÍNDICES PARA RUTAS CALIENTES DE RFX
-- ========================
DO $$
BEGIN
    -- rfx_v2: organización + fecha (historial organizacional)
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'organization_id'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'created_at'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rfx_v2_org_created_desc ON public.rfx_v2 (organization_id, created_at DESC)';
    END IF;

    -- rfx_v2: usuario + fecha para contexto personal
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'user_id'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'created_at'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'organization_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rfx_v2_user_personal_created_desc ON public.rfx_v2 (user_id, created_at DESC) WHERE organization_id IS NULL';
        ELSE
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rfx_v2_user_created_desc ON public.rfx_v2 (user_id, created_at DESC)';
        END IF;
    END IF;

    -- generated_documents: búsqueda rápida de última propuesta por RFX
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'generated_documents' AND column_name = 'rfx_id'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'generated_documents' AND column_name = 'document_type'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'generated_documents' AND column_name = 'created_at'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_generated_documents_rfx_type_created_desc ON public.generated_documents (rfx_id, document_type, created_at DESC)';
        ELSIF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'generated_documents' AND column_name = 'generated_at'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_generated_documents_rfx_type_generated_desc ON public.generated_documents (rfx_id, document_type, generated_at DESC)';
        END IF;
    END IF;

    -- rfx_products: join principal por rfx_id
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_products' AND column_name = 'rfx_id'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rfx_products_rfx_id ON public.rfx_products (rfx_id)';
    END IF;
END
$$;


-- ========================
-- 2) CONSISTENCIA DE PRICING (UPSERT CONFLICT-FREE)
-- ========================
-- Asegurar una sola fila hija por pricing_config_id para permitir ON CONFLICT
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='coordination_configurations') THEN
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS uq_coordination_config_pricing_id ON public.coordination_configurations (pricing_config_id)';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='cost_per_person_configurations') THEN
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS uq_cost_per_person_config_pricing_id ON public.cost_per_person_configurations (pricing_config_id)';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tax_configurations') THEN
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS uq_tax_config_pricing_id ON public.tax_configurations (pricing_config_id)';
    END IF;
END
$$;


-- ========================
-- 3) FUNCIÓN BATCH: CONTEO DE PRODUCTOS POR RFX
-- ========================
CREATE OR REPLACE FUNCTION public.get_rfx_product_counts(p_rfx_ids UUID[])
RETURNS TABLE (
    rfx_id UUID,
    product_count BIGINT
) AS $$
    SELECT
        rp.rfx_id,
        COUNT(*)::BIGINT AS product_count
    FROM public.rfx_products rp
    WHERE rp.rfx_id = ANY(p_rfx_ids)
    GROUP BY rp.rfx_id;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION public.get_rfx_product_counts(UUID[]) IS
'Conteo batch de productos por lista de rfx_id para eliminar N+1 en historial/listados.';


-- ========================
-- 4) FUNCIÓN ATÓMICA: UPSERT DE PRICING POR RFX
-- ========================
CREATE OR REPLACE FUNCTION public.upsert_rfx_pricing_configuration_atomic(
    p_rfx_id UUID,
    p_coordination_enabled BOOLEAN,
    p_coordination_rate NUMERIC,
    p_coordination_type TEXT,
    p_cost_per_person_enabled BOOLEAN,
    p_headcount INTEGER,
    p_display_in_proposal BOOLEAN,
    p_taxes_enabled BOOLEAN,
    p_tax_rate NUMERIC,
    p_tax_name TEXT,
    p_updated_by TEXT DEFAULT 'user'
)
RETURNS UUID AS $$
DECLARE
    v_pricing_config_id UUID;
    v_coord_type TEXT;
BEGIN
    v_coord_type := LOWER(COALESCE(p_coordination_type, 'standard'));
    IF v_coord_type NOT IN ('basic', 'standard', 'premium', 'custom') THEN
        v_coord_type := 'standard';
    END IF;

    -- Buscar configuración activa existente (lock para consistencia)
    SELECT rpc.id
    INTO v_pricing_config_id
    FROM public.rfx_pricing_configurations rpc
    WHERE rpc.rfx_id = p_rfx_id
      AND rpc.is_active = TRUE
    ORDER BY rpc.updated_at DESC NULLS LAST, rpc.created_at DESC NULLS LAST
    LIMIT 1
    FOR UPDATE;

    -- Crear si no existe (con manejo de carrera)
    IF v_pricing_config_id IS NULL THEN
        BEGIN
            INSERT INTO public.rfx_pricing_configurations (
                rfx_id,
                configuration_name,
                is_active,
                status,
                created_by,
                updated_by
            )
            VALUES (
                p_rfx_id,
                'Default Configuration',
                TRUE,
                'active',
                COALESCE(p_updated_by, 'user'),
                COALESCE(p_updated_by, 'user')
            )
            RETURNING id INTO v_pricing_config_id;
        EXCEPTION
            WHEN unique_violation OR exclusion_violation THEN
                SELECT rpc.id
                INTO v_pricing_config_id
                FROM public.rfx_pricing_configurations rpc
                WHERE rpc.rfx_id = p_rfx_id
                  AND rpc.is_active = TRUE
                ORDER BY rpc.updated_at DESC NULLS LAST, rpc.created_at DESC NULLS LAST
                LIMIT 1;
        END;
    END IF;

    -- Upsert coordinación
    INSERT INTO public.coordination_configurations (
        pricing_config_id,
        is_enabled,
        rate,
        coordination_type,
        description,
        updated_at
    )
    VALUES (
        v_pricing_config_id,
        COALESCE(p_coordination_enabled, FALSE),
        COALESCE(p_coordination_rate, 0.18),
        v_coord_type::coordination_type,
        'Coordinación y logística',
        NOW()
    )
    ON CONFLICT (pricing_config_id)
    DO UPDATE SET
        is_enabled = EXCLUDED.is_enabled,
        rate = EXCLUDED.rate,
        coordination_type = EXCLUDED.coordination_type,
        updated_at = NOW();

    -- Upsert costo por persona
    INSERT INTO public.cost_per_person_configurations (
        pricing_config_id,
        is_enabled,
        headcount,
        display_in_proposal,
        calculation_base,
        description,
        updated_at
    )
    VALUES (
        v_pricing_config_id,
        COALESCE(p_cost_per_person_enabled, FALSE),
        GREATEST(COALESCE(p_headcount, 120), 1),
        COALESCE(p_display_in_proposal, TRUE),
        'final_total',
        'Cálculo de costo individual',
        NOW()
    )
    ON CONFLICT (pricing_config_id)
    DO UPDATE SET
        is_enabled = EXCLUDED.is_enabled,
        headcount = GREATEST(EXCLUDED.headcount, 1),
        display_in_proposal = EXCLUDED.display_in_proposal,
        calculation_base = EXCLUDED.calculation_base,
        updated_at = NOW();

    -- Upsert impuestos
    INSERT INTO public.tax_configurations (
        pricing_config_id,
        is_enabled,
        tax_name,
        tax_rate,
        updated_at
    )
    VALUES (
        v_pricing_config_id,
        COALESCE(p_taxes_enabled, FALSE),
        COALESCE(NULLIF(TRIM(p_tax_name), ''), 'IVA'),
        COALESCE(p_tax_rate, 0.16),
        NOW()
    )
    ON CONFLICT (pricing_config_id)
    DO UPDATE SET
        is_enabled = EXCLUDED.is_enabled,
        tax_name = EXCLUDED.tax_name,
        tax_rate = EXCLUDED.tax_rate,
        updated_at = NOW();

    -- Touch configuración principal
    UPDATE public.rfx_pricing_configurations
    SET
        updated_by = COALESCE(p_updated_by, 'user'),
        updated_at = NOW()
    WHERE id = v_pricing_config_id;

    RETURN v_pricing_config_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.upsert_rfx_pricing_configuration_atomic(
    UUID, BOOLEAN, NUMERIC, TEXT, BOOLEAN, INTEGER, BOOLEAN, BOOLEAN, NUMERIC, TEXT, TEXT
) IS 'Upsert atómico de configuración de pricing por RFX (principal + tablas hijas).';


SELECT 'Migration 009: performance + pricing consistency applied successfully' AS status;
