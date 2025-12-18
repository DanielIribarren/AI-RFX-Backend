-- Script de debugging para verificar estado de créditos de usuario
-- Reemplaza '<user-email>' con el email del usuario que tiene el problema

-- 1. Verificar usuario en tabla users
SELECT 
    id,
    email,
    organization_id,
    created_at
FROM users
WHERE email = '<user-email>';

-- 2. Verificar si tiene créditos personales
SELECT 
    id,
    user_id,
    credits_total,
    credits_used,
    plan_tier,
    credits_reset_date,
    created_at
FROM user_credits
WHERE user_id = (SELECT id FROM users WHERE email = '<user-email>');

-- 3. Verificar si tiene organización
SELECT 
    o.id,
    o.name,
    o.credits_total,
    o.credits_used,
    o.plan_tier,
    o.credits_reset_date
FROM organizations o
JOIN users u ON u.organization_id = o.id
WHERE u.email = '<user-email>';

-- 4. Si no tiene créditos personales, inicializarlos manualmente
-- Descomenta la siguiente línea y ejecuta:
-- SELECT initialize_user_credits((SELECT id FROM users WHERE email = '<user-email>'));

-- 5. Verificar que se crearon correctamente
SELECT 
    uc.credits_total,
    uc.credits_used,
    uc.plan_tier,
    u.email
FROM user_credits uc
JOIN users u ON uc.user_id = u.id
WHERE u.email = '<user-email>';
