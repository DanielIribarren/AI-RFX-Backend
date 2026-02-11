-- ========================
-- Migration 008: Create plan_requests table
-- Date: 2026-02-11
-- Purpose: Sistema de solicitud y aprobación manual de planes (MVP)
--
-- Flujo:
--   1. Usuario solicita plan → INSERT con status='pending'
--   2. Admin revisa en /api/subscription/admin/pending
--   3. Admin aprueba/rechaza → UPDATE status + actualiza plan en organization/user_credits
--
-- IMPORTANTE: Los planes NUNCA se activan automáticamente.
--             Solo se activan cuando el admin cambia status a 'approved'.
-- ========================

BEGIN;

-- Tabla de solicitudes de plan
CREATE TABLE IF NOT EXISTS plan_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Quién solicita
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Para qué contexto (NULL = usuario personal)
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Qué plan tiene y cuál quiere
    current_tier TEXT NOT NULL DEFAULT 'free',
    requested_tier TEXT NOT NULL,

    -- Estado de la solicitud
    -- 'pending'  → esperando revisión del admin
    -- 'approved' → admin aprobó, plan activado
    -- 'rejected' → admin rechazó
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),

    -- Notas
    user_notes TEXT,         -- Comentario del usuario al hacer la solicitud
    admin_notes TEXT,        -- Comentario del admin al revisar

    -- Trazabilidad
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE plan_requests IS 'Solicitudes de cambio de plan. Requieren aprobación manual del admin.';
COMMENT ON COLUMN plan_requests.status IS 'pending=esperando revisión, approved=aprobado y activo, rejected=rechazado';
COMMENT ON COLUMN plan_requests.organization_id IS 'NULL si es una solicitud de usuario personal';

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_plan_requests_user_id ON plan_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_plan_requests_org_id ON plan_requests(organization_id) WHERE organization_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_plan_requests_status ON plan_requests(status);
CREATE INDEX IF NOT EXISTS idx_plan_requests_pending ON plan_requests(created_at) WHERE status = 'pending';

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_plan_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER plan_requests_updated_at
    BEFORE UPDATE ON plan_requests
    FOR EACH ROW EXECUTE FUNCTION update_plan_requests_updated_at();

-- ========================
-- Asegurarse que organizations tiene todas las columnas necesarias
-- (por si el schema base no las tiene)
-- ========================

-- Agregar credits_reset_date si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'organizations'
        AND column_name = 'credits_reset_date'
    ) THEN
        ALTER TABLE organizations ADD COLUMN credits_reset_date TIMESTAMPTZ;
        COMMENT ON COLUMN organizations.credits_reset_date IS 'Fecha en que se reinician los créditos mensuales';
    END IF;
END $$;

-- Agregar credits_total si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'organizations'
        AND column_name = 'credits_total'
    ) THEN
        ALTER TABLE organizations ADD COLUMN credits_total INTEGER DEFAULT 100;
    END IF;
END $$;

-- Agregar credits_used si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'organizations'
        AND column_name = 'credits_used'
    ) THEN
        ALTER TABLE organizations ADD COLUMN credits_used INTEGER DEFAULT 0;
    END IF;
END $$;

-- ========================
-- Tabla user_credits (para usuarios personales sin organización)
-- ========================

CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    plan_tier TEXT NOT NULL DEFAULT 'free',
    credits_total INTEGER NOT NULL DEFAULT 100,
    credits_used INTEGER NOT NULL DEFAULT 0,
    credits_reset_date TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_credits IS 'Créditos para usuarios personales (sin organización). Plan free por defecto.';

CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_reset_date ON user_credits(credits_reset_date);

-- Trigger updated_at para user_credits
CREATE TRIGGER user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================
-- Función RPC: initialize_user_credits
-- Crea créditos para usuario personal si no existen
-- ========================

CREATE OR REPLACE FUNCTION initialize_user_credits(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO user_credits (user_id, plan_tier, credits_total, credits_used, credits_reset_date)
    VALUES (p_user_id, 'free', 100, 0, NOW() + INTERVAL '30 days')
    ON CONFLICT (user_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION initialize_user_credits IS 'Inicializa créditos para usuario personal con plan free. Idempotente.';

COMMIT;

SELECT 'Migration 008: plan_requests table created successfully' as status;
