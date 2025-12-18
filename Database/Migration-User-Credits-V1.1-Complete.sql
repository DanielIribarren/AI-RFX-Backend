-- =====================================================
-- MIGRATION: User Credits System - Complete Lifecycle
-- VERSION: 1.1
-- DATE: 17 de Diciembre, 2025
-- DESCRIPTION: Sistema completo de créditos con triggers y reset automático
-- =====================================================

-- ========================
-- 1. TRIGGER: Auto-inicializar créditos para nuevos usuarios
-- ========================

CREATE OR REPLACE FUNCTION auto_initialize_user_credits()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo inicializar si el usuario NO tiene organización
    IF NEW.organization_id IS NULL THEN
        INSERT INTO user_credits (user_id, credits_total, credits_used, plan_tier)
        VALUES (NEW.id, 100, 0, 'free')
        ON CONFLICT (user_id) DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Crear trigger en tabla users
DROP TRIGGER IF EXISTS trigger_auto_initialize_user_credits ON users;
CREATE TRIGGER trigger_auto_initialize_user_credits
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION auto_initialize_user_credits();

COMMENT ON FUNCTION auto_initialize_user_credits() IS 'Inicializa créditos automáticamente cuando se crea un usuario sin organización';

-- ========================
-- 2. FUNCIÓN: Reset mensual de créditos
-- ========================

CREATE OR REPLACE FUNCTION reset_expired_user_credits()
RETURNS TABLE(
    user_id UUID,
    old_credits_used INTEGER,
    new_credits_used INTEGER,
    reset_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    UPDATE user_credits
    SET 
        credits_used = 0,
        credits_reset_date = credits_reset_date + INTERVAL '1 month',
        updated_at = NOW()
    WHERE credits_reset_date <= NOW()
    RETURNING 
        user_credits.user_id,
        user_credits.credits_used as old_credits_used,
        0 as new_credits_used,
        user_credits.credits_reset_date as reset_date;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION reset_expired_user_credits() IS 'Resetea créditos de usuarios cuya fecha de reset ha expirado. Debe ejecutarse diariamente via cron job.';

-- ========================
-- 3. FUNCIÓN: Verificar y resetear créditos de un usuario específico
-- ========================

CREATE OR REPLACE FUNCTION check_and_reset_user_credits(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_reset_date TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Obtener fecha de reset
    SELECT credits_reset_date INTO v_reset_date
    FROM user_credits
    WHERE user_id = p_user_id;
    
    -- Si no existe registro, inicializar
    IF NOT FOUND THEN
        PERFORM initialize_user_credits(p_user_id);
        RETURN TRUE;
    END IF;
    
    -- Si la fecha de reset ya pasó, resetear
    IF v_reset_date <= NOW() THEN
        UPDATE user_credits
        SET 
            credits_used = 0,
            credits_reset_date = credits_reset_date + INTERVAL '1 month',
            updated_at = NOW()
        WHERE user_id = p_user_id;
        
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_and_reset_user_credits(UUID) IS 'Verifica si los créditos de un usuario deben resetearse y lo hace automáticamente';

-- ========================
-- 4. FUNCIÓN: Upgrade de plan de usuario
-- ========================

CREATE OR REPLACE FUNCTION upgrade_user_plan(
    p_user_id UUID,
    p_new_plan_tier VARCHAR(50),
    p_new_credits_total INTEGER
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE user_credits
    SET 
        plan_tier = p_new_plan_tier,
        credits_total = p_new_credits_total,
        credits_used = 0,  -- Reset al hacer upgrade
        credits_reset_date = NOW() + INTERVAL '1 month',
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    IF NOT FOUND THEN
        -- Si no existe, crear con el nuevo plan
        INSERT INTO user_credits (user_id, credits_total, credits_used, plan_tier)
        VALUES (p_user_id, p_new_credits_total, 0, p_new_plan_tier);
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION upgrade_user_plan(UUID, VARCHAR, INTEGER) IS 'Actualiza el plan de un usuario y resetea sus créditos';

-- ========================
-- 5. MIGRAR TODOS LOS USUARIOS EXISTENTES SIN ORGANIZACIÓN
-- ========================

-- Insertar créditos para TODOS los usuarios sin organización que no tienen registro
INSERT INTO user_credits (user_id, credits_total, credits_used, plan_tier, credits_reset_date)
SELECT 
    u.id as user_id,
    100 as credits_total,
    0 as credits_used,
    'free' as plan_tier,
    NOW() + INTERVAL '1 month' as credits_reset_date
FROM users u
LEFT JOIN user_credits uc ON u.id = uc.user_id
WHERE u.organization_id IS NULL
  AND uc.user_id IS NULL  -- Solo usuarios que NO tienen créditos
ON CONFLICT (user_id) DO NOTHING;

-- ========================
-- 6. ÍNDICES ADICIONALES PARA PERFORMANCE
-- ========================

-- Índice para encontrar créditos expirados rápidamente
CREATE INDEX IF NOT EXISTS idx_user_credits_expired 
ON user_credits(credits_reset_date) 
WHERE credits_reset_date <= NOW();

-- Índice para búsquedas por plan
CREATE INDEX IF NOT EXISTS idx_user_credits_plan_tier 
ON user_credits(plan_tier);

-- ========================
-- 7. VIEW: Usuarios con créditos expirados
-- ========================

CREATE OR REPLACE VIEW user_credits_expired AS
SELECT 
    uc.user_id,
    u.email,
    uc.credits_total,
    uc.credits_used,
    uc.plan_tier,
    uc.credits_reset_date,
    NOW() - uc.credits_reset_date as days_expired
FROM user_credits uc
JOIN users u ON uc.user_id = u.id
WHERE uc.credits_reset_date <= NOW();

COMMENT ON VIEW user_credits_expired IS 'Vista de usuarios cuyos créditos han expirado y necesitan reset';

-- ========================
-- 8. COMENTARIOS ADICIONALES
-- ========================

COMMENT ON TRIGGER trigger_auto_initialize_user_credits ON users IS 'Auto-inicializa créditos cuando se crea un usuario sin organización';
COMMENT ON INDEX idx_user_credits_expired IS 'Optimiza búsqueda de créditos expirados para cron job';
COMMENT ON INDEX idx_user_credits_plan_tier IS 'Optimiza búsquedas por tipo de plan';

-- ========================
-- VERIFICACIÓN FINAL
-- ========================

-- Contar usuarios sin organización
SELECT COUNT(*) as usuarios_sin_org
FROM users
WHERE organization_id IS NULL;

-- Contar registros en user_credits
SELECT COUNT(*) as registros_user_credits
FROM user_credits;

-- Verificar que todos los usuarios sin org tienen créditos
SELECT 
    COUNT(*) as usuarios_sin_creditos
FROM users u
LEFT JOIN user_credits uc ON u.id = uc.user_id
WHERE u.organization_id IS NULL
  AND uc.user_id IS NULL;

-- Ver usuarios con créditos expirados
SELECT * FROM user_credits_expired LIMIT 5;

-- ========================
-- INSTRUCCIONES DE CRON JOB
-- ========================

/*
Para ejecutar el reset automático diariamente, configurar un cron job:

1. En Supabase Dashboard → Database → Cron Jobs
2. Crear nuevo job:
   - Name: reset_expired_user_credits
   - Schedule: 0 0 * * * (diario a medianoche)
   - Command: SELECT reset_expired_user_credits();

O ejecutar manualmente cuando sea necesario:
SELECT * FROM reset_expired_user_credits();
*/
