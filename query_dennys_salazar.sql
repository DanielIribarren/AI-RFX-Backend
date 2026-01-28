-- ========================
-- QUERY: Verificar información de Dennys Salazar y Sabra Corporation
-- ========================

-- 1. Buscar usuario Dennys Salazar
SELECT 
    id,
    email,
    full_name,
    username,
    organization_id,
    role,
    created_at
FROM users
WHERE 
    LOWER(email) LIKE '%dennys%' OR
    LOWER(full_name) LIKE '%dennys%' OR
    LOWER(username) LIKE '%dennys%' OR
    LOWER(email) LIKE '%salazar%' OR
    LOWER(full_name) LIKE '%salazar%';

-- 2. Buscar organización Sabra Corporation
SELECT 
    id,
    name,
    slug,
    plan_tier,
    credits_total,
    credits_used,
    is_active,
    created_at
FROM organizations
WHERE 
    LOWER(name) LIKE '%sabra%' OR
    LOWER(slug) LIKE '%sabra%';

-- 3. Ver todas las organizaciones disponibles
SELECT 
    id,
    name,
    slug,
    plan_tier,
    credits_total,
    credits_used,
    (credits_total - credits_used) as credits_available,
    is_active
FROM organizations
ORDER BY created_at;

-- 4. Ver todos los usuarios y sus organizaciones
SELECT 
    u.id,
    u.email,
    u.full_name,
    u.role,
    o.name as organization_name,
    o.slug as organization_slug
FROM users u
LEFT JOIN organizations o ON u.organization_id = o.id
ORDER BY o.name, u.email;
