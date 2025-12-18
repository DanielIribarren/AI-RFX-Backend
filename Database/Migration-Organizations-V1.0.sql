-- ========================
-- MIGRATION: Organizations Multi-Tenant System V1.0
-- Fecha: 11 de Diciembre, 2025
-- Propósito: Implementar sistema de organizaciones multi-tenant
-- ========================

-- IMPORTANTE: Este script debe ejecutarse en orden
-- Asegúrate de tener backup antes de ejecutar

BEGIN;

-- ========================
-- PASO 1: CREAR TABLA ORGANIZATIONS
-- ========================

CREATE TABLE IF NOT EXISTS organizations (
    -- Identificador
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Información básica
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    
    -- Plan y créditos
    plan_tier TEXT DEFAULT 'free' CHECK (plan_tier IN ('free', 'starter', 'pro', 'enterprise')),
    credits_total INTEGER DEFAULT 100 CHECK (credits_total >= 0),
    credits_used INTEGER DEFAULT 0 CHECK (credits_used >= 0),
    credits_reset_date TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_slug CHECK (slug ~ '^[a-z0-9-]+$'),
    CONSTRAINT credits_not_negative CHECK (credits_used <= credits_total)
);

COMMENT ON TABLE organizations IS 'Organizaciones multi-tenant con sistema de créditos';
COMMENT ON COLUMN organizations.slug IS 'Identificador único legible (URL-friendly)';
COMMENT ON COLUMN organizations.plan_tier IS 'Tier del plan: free, starter, pro, enterprise';
COMMENT ON COLUMN organizations.credits_total IS 'Créditos totales del plan mensual';
COMMENT ON COLUMN organizations.credits_used IS 'Créditos consumidos en el período actual';
COMMENT ON COLUMN organizations.trial_ends_at IS 'Fecha de fin del trial (14 días por defecto)';

-- Índices
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_plan_tier ON organizations(plan_tier);
CREATE INDEX IF NOT EXISTS idx_organizations_is_active ON organizations(is_active);

-- ========================
-- PASO 2: ACTUALIZAR TABLA USERS
-- ========================

-- Agregar columnas de organización y rol
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member'));

COMMENT ON COLUMN users.organization_id IS 'Organización a la que pertenece el usuario';
COMMENT ON COLUMN users.role IS 'Rol del usuario en la organización: owner, admin, member';

-- Índices
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ========================
-- PASO 3: ACTUALIZAR TABLAS PRINCIPALES
-- ========================

-- RFX V2
ALTER TABLE rfx_v2 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

COMMENT ON COLUMN rfx_v2.organization_id IS 'Organización dueña del RFX (multi-tenant)';

CREATE INDEX IF NOT EXISTS idx_rfx_organization_id ON rfx_v2(organization_id);

-- Companies
ALTER TABLE companies 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

COMMENT ON COLUMN companies.organization_id IS 'Organización dueña de la empresa cliente';

CREATE INDEX IF NOT EXISTS idx_companies_organization_id ON companies(organization_id);

-- Suppliers
ALTER TABLE suppliers 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

COMMENT ON COLUMN suppliers.organization_id IS 'Organización dueña del proveedor';

CREATE INDEX IF NOT EXISTS idx_suppliers_organization_id ON suppliers(organization_id);

-- ========================
-- PASO 4: TABLA DE TRANSACCIONES DE CRÉDITOS
-- ========================

CREATE TABLE IF NOT EXISTS credit_transactions (
    -- Identificador
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relaciones
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    
    -- Transacción
    amount INTEGER NOT NULL,  -- Negativo para consumo, positivo para recarga
    type TEXT NOT NULL CHECK (type IN ('extraction', 'generation', 'complete', 'chat_message', 'regeneration', 'monthly_reset', 'manual_adjustment', 'refund')),
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE credit_transactions IS 'Historial de transacciones de créditos';
COMMENT ON COLUMN credit_transactions.amount IS 'Cantidad de créditos (negativo = consumo, positivo = recarga)';
COMMENT ON COLUMN credit_transactions.type IS 'Tipo de operación que generó la transacción';
COMMENT ON COLUMN credit_transactions.metadata IS 'Información adicional en formato JSON';

-- Índices
CREATE INDEX IF NOT EXISTS idx_credit_transactions_org ON credit_transactions(organization_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_rfx ON credit_transactions(rfx_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at DESC);

-- ========================
-- PASO 5: TABLA DE ESTADO DE PROCESAMIENTO
-- ========================

CREATE TABLE IF NOT EXISTS rfx_processing_status (
    -- Identificador
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL UNIQUE REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Regeneraciones
    free_regenerations_used INTEGER DEFAULT 0 CHECK (free_regenerations_used >= 0),
    total_regenerations INTEGER DEFAULT 0 CHECK (total_regenerations >= 0),
    
    -- Estado
    last_generation_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT regenerations_valid CHECK (total_regenerations >= free_regenerations_used)
);

COMMENT ON TABLE rfx_processing_status IS 'Estado de procesamiento y regeneraciones de RFX';
COMMENT ON COLUMN rfx_processing_status.free_regenerations_used IS 'Regeneraciones gratuitas consumidas';
COMMENT ON COLUMN rfx_processing_status.total_regenerations IS 'Total de regeneraciones realizadas';

-- Índices
CREATE INDEX IF NOT EXISTS idx_rfx_processing_status_rfx ON rfx_processing_status(rfx_id);

-- ========================
-- PASO 6: FUNCIÓN PARA INCREMENTAR REGENERACIONES
-- ========================

CREATE OR REPLACE FUNCTION increment_free_regenerations(rfx_id_param UUID)
RETURNS void AS $$
BEGIN
    -- Insertar o actualizar contador de regeneraciones
    INSERT INTO rfx_processing_status (rfx_id, free_regenerations_used, total_regenerations, last_generation_at)
    VALUES (rfx_id_param, 1, 1, NOW())
    ON CONFLICT (rfx_id) DO UPDATE
    SET 
        free_regenerations_used = rfx_processing_status.free_regenerations_used + 1,
        total_regenerations = rfx_processing_status.total_regenerations + 1,
        last_generation_at = NOW(),
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_free_regenerations IS 'Incrementar contador de regeneraciones gratuitas para un RFX';

-- ========================
-- PASO 7: TRIGGERS PARA UPDATED_AT
-- ========================

-- Función genérica para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para organizations
DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para rfx_processing_status
DROP TRIGGER IF EXISTS update_rfx_processing_status_updated_at ON rfx_processing_status;
CREATE TRIGGER update_rfx_processing_status_updated_at
    BEFORE UPDATE ON rfx_processing_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================
-- PASO 8: POLÍTICAS RLS (Row Level Security) - PREPARADO PARA FUTURO
-- ========================

-- Habilitar RLS en tablas principales (comentado por ahora)
-- ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE rfx_processing_status ENABLE ROW LEVEL SECURITY;

-- Políticas de ejemplo (implementar cuando sea necesario)
-- CREATE POLICY org_isolation_policy ON rfx_v2
--     USING (organization_id = current_setting('app.current_organization_id')::uuid);

COMMENT ON TABLE organizations IS 'RLS preparado pero no habilitado - implementar en Fase 2';

-- ========================
-- VERIFICACIÓN FINAL
-- ========================

-- Verificar que las tablas existen
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'organizations') = 1,
        'Table organizations not created';
    ASSERT (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'credit_transactions') = 1,
        'Table credit_transactions not created';
    ASSERT (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rfx_processing_status') = 1,
        'Table rfx_processing_status not created';
    
    -- Verificar columnas en users
    ASSERT (SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'organization_id') = 1,
        'Column users.organization_id not created';
    ASSERT (SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'role') = 1,
        'Column users.role not created';
    
    RAISE NOTICE '✅ Migration V1.0 completed successfully';
END $$;

COMMIT;

-- ========================
-- ROLLBACK SCRIPT (Guardar para emergencias)
-- ========================

-- Para revertir esta migración, ejecutar:
/*
BEGIN;

-- Eliminar tablas nuevas
DROP TABLE IF EXISTS rfx_processing_status CASCADE;
DROP TABLE IF EXISTS credit_transactions CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Eliminar columnas agregadas
ALTER TABLE users DROP COLUMN IF EXISTS organization_id;
ALTER TABLE users DROP COLUMN IF EXISTS role;
ALTER TABLE rfx_v2 DROP COLUMN IF EXISTS organization_id;
ALTER TABLE companies DROP COLUMN IF EXISTS organization_id;
ALTER TABLE suppliers DROP COLUMN IF EXISTS organization_id;

-- Eliminar función
DROP FUNCTION IF EXISTS increment_free_regenerations(UUID);
DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
*/
