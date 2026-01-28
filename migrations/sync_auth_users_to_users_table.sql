-- ============================================================================
-- MIGRACIÓN: Sincronizar usuarios de auth.users a tabla users
-- ============================================================================
-- Propósito: Copiar usuarios que existen en auth.users pero NO en tabla users
-- Fecha: 2026-01-27
-- ============================================================================

-- 1. Insertar usuarios faltantes desde auth.users
INSERT INTO users (
    id,
    email,
    full_name,
    username,
    avatar_url,
    status,
    organization_id,
    role,
    created_at,
    updated_at
)
SELECT 
    au.id,
    au.email,
    -- Extraer nombre de raw_user_meta_data o usar email
    COALESCE(
        au.raw_user_meta_data->>'full_name',
        au.raw_user_meta_data->>'name',
        SPLIT_PART(au.email, '@', 1)
    ) as full_name,
    -- Username desde metadata o email
    COALESCE(
        au.raw_user_meta_data->>'username',
        SPLIT_PART(au.email, '@', 1)
    ) as username,
    -- Avatar desde metadata
    au.raw_user_meta_data->>'avatar_url' as avatar_url,
    -- Status basado en email_confirmed_at
    CASE 
        WHEN au.email_confirmed_at IS NOT NULL THEN 'active'
        ELSE 'pending_verification'
    END as status,
    -- Organization_id: buscar org por defecto o NULL
    (SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1) as organization_id,
    -- Role por defecto
    'admin' as role,
    au.created_at,
    NOW() as updated_at
FROM auth.users au
WHERE NOT EXISTS (
    -- Solo insertar si NO existe en tabla users
    SELECT 1 FROM users u WHERE u.id = au.id
)
AND au.deleted_at IS NULL  -- Excluir usuarios eliminados
ON CONFLICT (id) DO NOTHING;  -- Por seguridad

-- 2. Verificar usuarios específicos de los logs
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    -- Usuario 1: 186ea35f-3cf8-480f-a7d3-0af178c09498
    SELECT COUNT(*) INTO user_count 
    FROM users 
    WHERE id = '186ea35f-3cf8-480f-a7d3-0af178c09498';
    
    IF user_count > 0 THEN
        RAISE NOTICE '✅ Usuario 186ea35f-3cf8-480f-a7d3-0af178c09498 existe en tabla users';
    ELSE
        RAISE WARNING '❌ Usuario 186ea35f-3cf8-480f-a7d3-0af178c09498 NO existe en tabla users';
    END IF;
    
    -- Usuario 2: c17f0d49-501c-40e4-8a63-c02c4f09ed90
    SELECT COUNT(*) INTO user_count 
    FROM users 
    WHERE id = 'c17f0d49-501c-40e4-8a63-c02c4f09ed90';
    
    IF user_count > 0 THEN
        RAISE NOTICE '✅ Usuario c17f0d49-501c-40e4-8a63-c02c4f09ed90 existe en tabla users';
    ELSE
        RAISE WARNING '❌ Usuario c17f0d49-501c-40e4-8a63-c02c4f09ed90 NO existe en tabla users';
    END IF;
END $$;

-- 3. Actualizar status de usuarios con email confirmado
UPDATE users u
SET status = 'active'
FROM auth.users au
WHERE u.id = au.id
AND au.email_confirmed_at IS NOT NULL
AND u.status = 'pending_verification';

-- 4. Reporte final
SELECT 
    'RESUMEN DE SINCRONIZACIÓN' as tipo,
    COUNT(*) as total_usuarios_tabla_users
FROM users
UNION ALL
SELECT 
    'Usuarios activos' as tipo,
    COUNT(*) as total
FROM users
WHERE status = 'active'
UNION ALL
SELECT 
    'Usuarios pendientes' as tipo,
    COUNT(*) as total
FROM users
WHERE status = 'pending_verification'
UNION ALL
SELECT 
    'Usuarios con organización' as tipo,
    COUNT(*) as total
FROM users
WHERE organization_id IS NOT NULL;

-- 5. Mostrar usuarios sincronizados recientemente
SELECT 
    id,
    email,
    full_name,
    status,
    organization_id,
    created_at
FROM users
WHERE updated_at >= NOW() - INTERVAL '5 minutes'
ORDER BY updated_at DESC;
