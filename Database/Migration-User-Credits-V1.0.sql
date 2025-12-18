-- =====================================================
-- MIGRATION: User Credits for Personal Plans
-- VERSION: 1.0
-- DATE: 17 de Diciembre, 2025
-- DESCRIPTION: Tabla para rastrear créditos de usuarios personales (sin organización)
-- =====================================================

-- ========================
-- 1. CREAR TABLA user_credits
-- ========================

CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Créditos
    credits_total INTEGER NOT NULL DEFAULT 100,  -- Total de créditos del plan
    credits_used INTEGER NOT NULL DEFAULT 0,     -- Créditos consumidos
    
    -- Plan
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, starter, pro, enterprise
    
    -- Reset mensual
    credits_reset_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '1 month'),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_credits UNIQUE (user_id),
    CONSTRAINT check_credits_positive CHECK (credits_total >= 0),
    CONSTRAINT check_credits_used_positive CHECK (credits_used >= 0),
    CONSTRAINT check_credits_used_lte_total CHECK (credits_used <= credits_total)
);

-- ========================
-- 2. ÍNDICES
-- ========================

CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_reset_date ON user_credits(credits_reset_date);

-- ========================
-- 3. RLS (Row Level Security)
-- ========================

ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- Policy: Los usuarios solo pueden ver sus propios créditos
CREATE POLICY user_credits_select_own 
ON user_credits FOR SELECT 
USING (auth.uid() = user_id);

-- Policy: Los usuarios pueden actualizar sus propios créditos (para consumo)
CREATE POLICY user_credits_update_own 
ON user_credits FOR UPDATE 
USING (auth.uid() = user_id);

-- ========================
-- 4. TRIGGER PARA updated_at
-- ========================

CREATE TRIGGER update_user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================
-- 5. FUNCIÓN PARA INICIALIZAR CRÉDITOS DE USUARIO
-- ========================

CREATE OR REPLACE FUNCTION initialize_user_credits(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO user_credits (user_id, credits_total, credits_used, plan_tier)
    VALUES (p_user_id, 100, 0, 'free')
    ON CONFLICT (user_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================
-- 6. MIGRAR USUARIOS EXISTENTES SIN ORGANIZACIÓN
-- ========================

-- Crear registros de créditos para usuarios que NO tienen organización
INSERT INTO user_credits (user_id, credits_total, credits_used, plan_tier)
SELECT 
    id as user_id,
    100 as credits_total,
    0 as credits_used,
    'free' as plan_tier
FROM users
WHERE organization_id IS NULL
ON CONFLICT (user_id) DO NOTHING;

-- ========================
-- 7. COMENTARIOS
-- ========================

COMMENT ON TABLE user_credits IS 'Créditos para usuarios personales (sin organización)';
COMMENT ON COLUMN user_credits.user_id IS 'ID del usuario (FK a auth.users)';
COMMENT ON COLUMN user_credits.credits_total IS 'Total de créditos disponibles en el plan';
COMMENT ON COLUMN user_credits.credits_used IS 'Créditos consumidos en el período actual';
COMMENT ON COLUMN user_credits.plan_tier IS 'Tier del plan: free, starter, pro, enterprise';
COMMENT ON COLUMN user_credits.credits_reset_date IS 'Fecha del próximo reset mensual de créditos';

-- ========================
-- VERIFICACIÓN
-- ========================

-- Verificar que la tabla se creó correctamente
SELECT 
    COUNT(*) as total_users_with_credits,
    SUM(credits_total) as total_credits_allocated,
    SUM(credits_used) as total_credits_used
FROM user_credits;

-- Verificar usuarios sin organización que tienen créditos
SELECT 
    u.id,
    u.email,
    uc.credits_total,
    uc.credits_used,
    uc.plan_tier
FROM users u
LEFT JOIN user_credits uc ON u.id = uc.user_id
WHERE u.organization_id IS NULL
LIMIT 10;
