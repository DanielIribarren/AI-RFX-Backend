-- ========================
-- MIGRATION: Organizations Data Migration
-- Fecha: 11 de Diciembre, 2025
-- Propósito: Migrar datos existentes al sistema de organizaciones
-- ========================

-- IMPORTANTE: Ejecutar DESPUÉS de Migration-Organizations-V1.0.sql
-- Este script migra datos existentes sin pérdida de información

BEGIN;

-- ========================
-- PASO 1: CREAR ORGANIZACIÓN POR DEFECTO
-- ========================

-- Insertar organización por defecto para usuarios existentes
INSERT INTO organizations (
    id,
    name,
    slug,
    plan_tier,
    credits_total,
    credits_used,
    credits_reset_date,
    is_active,
    trial_ends_at,
    created_at
)
VALUES (
    gen_random_uuid(),
    'Default Organization',
    'default-org',
    'free',
    100,  -- Plan free: 100 créditos
    0,
    NOW() + INTERVAL '30 days',
    true,
    NOW() + INTERVAL '14 days',
    NOW()
)
ON CONFLICT (slug) DO NOTHING
RETURNING id;

-- Guardar ID de la organización por defecto
DO $$
DECLARE
    default_org_id UUID;
BEGIN
    SELECT id INTO default_org_id FROM organizations WHERE slug = 'default-org';
    
    IF default_org_id IS NULL THEN
        RAISE EXCEPTION 'Default organization not found';
    END IF;
    
    RAISE NOTICE '✅ Default organization created: %', default_org_id;
END $$;

-- ========================
-- PASO 2: ASIGNAR USUARIOS A ORGANIZACIÓN
-- ========================

-- Asignar todos los usuarios existentes a la organización por defecto
UPDATE users
SET 
    organization_id = (SELECT id FROM organizations WHERE slug = 'default-org'),
    role = CASE 
        WHEN email LIKE '%admin%' THEN 'owner'  -- Usuarios con "admin" en email son owners
        ELSE 'owner'  -- Por defecto, todos son owners (pueden crear su propia org después)
    END
WHERE organization_id IS NULL;

-- Verificar asignación
DO $$
DECLARE
    users_updated INTEGER;
    users_without_org INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_updated FROM users WHERE organization_id IS NOT NULL;
    SELECT COUNT(*) INTO users_without_org FROM users WHERE organization_id IS NULL;
    
    RAISE NOTICE '✅ Users assigned to organization: %', users_updated;
    
    IF users_without_org > 0 THEN
        RAISE WARNING '⚠️ Users without organization: %', users_without_org;
    END IF;
END $$;

-- ========================
-- PASO 3: ASIGNAR RFX A ORGANIZACIONES
-- ========================

-- Asignar RFX a la organización del usuario que lo creó
UPDATE rfx_v2
SET organization_id = (
    SELECT organization_id 
    FROM users 
    WHERE users.id = rfx_v2.user_id
)
WHERE organization_id IS NULL
AND user_id IS NOT NULL;

-- Verificar asignación
DO $$
DECLARE
    rfx_updated INTEGER;
    rfx_without_org INTEGER;
    rfx_without_user INTEGER;
BEGIN
    SELECT COUNT(*) INTO rfx_updated FROM rfx_v2 WHERE organization_id IS NOT NULL;
    SELECT COUNT(*) INTO rfx_without_org FROM rfx_v2 WHERE organization_id IS NULL AND user_id IS NOT NULL;
    SELECT COUNT(*) INTO rfx_without_user FROM rfx_v2 WHERE user_id IS NULL;
    
    RAISE NOTICE '✅ RFX assigned to organizations: %', rfx_updated;
    
    IF rfx_without_org > 0 THEN
        RAISE WARNING '⚠️ RFX without organization (but with user): %', rfx_without_org;
    END IF;
    
    IF rfx_without_user > 0 THEN
        RAISE WARNING '⚠️ RFX without user_id (orphaned): %', rfx_without_user;
        RAISE NOTICE 'ℹ️ Orphaned RFX will be assigned to default organization';
        
        -- Asignar RFX huérfanos a organización por defecto
        UPDATE rfx_v2
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'default-org')
        WHERE organization_id IS NULL;
    END IF;
END $$;

-- ========================
-- PASO 4: ASIGNAR COMPANIES A ORGANIZACIONES
-- ========================

-- Asignar companies a la organización del usuario que las creó
UPDATE companies
SET organization_id = (
    SELECT organization_id 
    FROM users 
    WHERE users.id = companies.user_id
)
WHERE organization_id IS NULL
AND user_id IS NOT NULL;

-- Verificar asignación
DO $$
DECLARE
    companies_updated INTEGER;
    companies_without_org INTEGER;
BEGIN
    SELECT COUNT(*) INTO companies_updated FROM companies WHERE organization_id IS NOT NULL;
    SELECT COUNT(*) INTO companies_without_org FROM companies WHERE organization_id IS NULL;
    
    RAISE NOTICE '✅ Companies assigned to organizations: %', companies_updated;
    
    IF companies_without_org > 0 THEN
        RAISE WARNING '⚠️ Companies without organization: %', companies_without_org;
        
        -- Asignar companies huérfanas a organización por defecto
        UPDATE companies
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'default-org')
        WHERE organization_id IS NULL;
    END IF;
END $$;

-- ========================
-- PASO 5: ASIGNAR SUPPLIERS A ORGANIZACIONES
-- ========================

-- Asignar suppliers a la organización del usuario que los creó
UPDATE suppliers
SET organization_id = (
    SELECT organization_id 
    FROM users 
    WHERE users.id = suppliers.user_id
)
WHERE organization_id IS NULL
AND user_id IS NOT NULL;

-- Verificar asignación
DO $$
DECLARE
    suppliers_updated INTEGER;
    suppliers_without_org INTEGER;
BEGIN
    SELECT COUNT(*) INTO suppliers_updated FROM suppliers WHERE organization_id IS NOT NULL;
    SELECT COUNT(*) INTO suppliers_without_org FROM suppliers WHERE organization_id IS NULL;
    
    RAISE NOTICE '✅ Suppliers assigned to organizations: %', suppliers_updated;
    
    IF suppliers_without_org > 0 THEN
        RAISE WARNING '⚠️ Suppliers without organization: %', suppliers_without_org;
        
        -- Asignar suppliers huérfanos a organización por defecto
        UPDATE suppliers
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'default-org')
        WHERE organization_id IS NULL;
    END IF;
END $$;

-- ========================
-- PASO 6: INICIALIZAR ESTADO DE PROCESAMIENTO
-- ========================

-- Crear registros de estado de procesamiento para RFX existentes
INSERT INTO rfx_processing_status (rfx_id, free_regenerations_used, total_regenerations, created_at)
SELECT 
    id,
    0,  -- Asumir 0 regeneraciones usadas
    0,  -- Asumir 0 regeneraciones totales
    created_at
FROM rfx_v2
WHERE id NOT IN (SELECT rfx_id FROM rfx_processing_status)
ON CONFLICT (rfx_id) DO NOTHING;

-- Verificar inicialización
DO $$
DECLARE
    status_created INTEGER;
BEGIN
    SELECT COUNT(*) INTO status_created FROM rfx_processing_status;
    RAISE NOTICE '✅ Processing status initialized for % RFX', status_created;
END $$;

-- ========================
-- PASO 7: CREAR TRANSACCIÓN INICIAL DE CRÉDITOS
-- ========================

-- Registrar créditos iniciales para la organización por defecto
INSERT INTO credit_transactions (
    organization_id,
    amount,
    type,
    description,
    metadata,
    created_at
)
SELECT 
    id,
    100,  -- Créditos iniciales del plan free
    'monthly_reset',
    'Initial credits allocation for migrated organization',
    jsonb_build_object(
        'migration', true,
        'plan_tier', 'free',
        'migration_date', NOW()
    ),
    NOW()
FROM organizations
WHERE slug = 'default-org'
ON CONFLICT DO NOTHING;

RAISE NOTICE '✅ Initial credit transaction created';

-- ========================
-- PASO 8: VERIFICACIÓN FINAL
-- ========================

DO $$
DECLARE
    total_users INTEGER;
    users_with_org INTEGER;
    total_rfx INTEGER;
    rfx_with_org INTEGER;
    total_companies INTEGER;
    companies_with_org INTEGER;
    total_suppliers INTEGER;
    suppliers_with_org INTEGER;
BEGIN
    -- Verificar usuarios
    SELECT COUNT(*) INTO total_users FROM users;
    SELECT COUNT(*) INTO users_with_org FROM users WHERE organization_id IS NOT NULL;
    
    -- Verificar RFX
    SELECT COUNT(*) INTO total_rfx FROM rfx_v2;
    SELECT COUNT(*) INTO rfx_with_org FROM rfx_v2 WHERE organization_id IS NOT NULL;
    
    -- Verificar companies
    SELECT COUNT(*) INTO total_companies FROM companies;
    SELECT COUNT(*) INTO companies_with_org FROM companies WHERE organization_id IS NOT NULL;
    
    -- Verificar suppliers
    SELECT COUNT(*) INTO total_suppliers FROM suppliers;
    SELECT COUNT(*) INTO suppliers_with_org FROM suppliers WHERE organization_id IS NOT NULL;
    
    -- Reportar resultados
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION SUMMARY';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Users: %/% assigned to organizations', users_with_org, total_users;
    RAISE NOTICE 'RFX: %/% assigned to organizations', rfx_with_org, total_rfx;
    RAISE NOTICE 'Companies: %/% assigned to organizations', companies_with_org, total_companies;
    RAISE NOTICE 'Suppliers: %/% assigned to organizations', suppliers_with_org, total_suppliers;
    RAISE NOTICE '========================================';
    
    -- Verificar que todos los datos críticos tienen organización
    IF users_with_org < total_users THEN
        RAISE WARNING '⚠️ Some users are not assigned to an organization';
    END IF;
    
    IF rfx_with_org < total_rfx THEN
        RAISE WARNING '⚠️ Some RFX are not assigned to an organization';
    END IF;
    
    -- Éxito si al menos el 95% de los datos están migrados
    IF users_with_org::FLOAT / NULLIF(total_users, 0) >= 0.95 AND
       rfx_with_org::FLOAT / NULLIF(total_rfx, 0) >= 0.95 THEN
        RAISE NOTICE '✅ Data migration completed successfully';
    ELSE
        RAISE WARNING '⚠️ Data migration completed with warnings - review logs';
    END IF;
END $$;

COMMIT;

-- ========================
-- PASO 9: RECOMENDACIONES POST-MIGRACIÓN
-- ========================

-- Ejecutar estas queries para verificar el estado:
/*
-- Ver organizaciones creadas
SELECT id, name, slug, plan_tier, credits_total, credits_used 
FROM organizations;

-- Ver usuarios por organización
SELECT 
    o.name as organization,
    u.email,
    u.role,
    u.created_at
FROM users u
JOIN organizations o ON u.organization_id = o.id
ORDER BY o.name, u.role DESC, u.created_at;

-- Ver RFX por organización
SELECT 
    o.name as organization,
    COUNT(r.id) as rfx_count
FROM organizations o
LEFT JOIN rfx_v2 r ON r.organization_id = o.id
GROUP BY o.id, o.name
ORDER BY rfx_count DESC;

-- Ver créditos disponibles
SELECT 
    name,
    plan_tier,
    credits_total,
    credits_used,
    (credits_total - credits_used) as credits_available,
    ROUND((credits_total - credits_used)::NUMERIC / NULLIF(credits_total, 0) * 100, 2) as percentage_available
FROM organizations
ORDER BY name;
*/

-- ========================
-- ROLLBACK (Solo si es necesario)
-- ========================

/*
BEGIN;

-- Eliminar transacciones de créditos
DELETE FROM credit_transactions WHERE description LIKE '%migrated%';

-- Eliminar estado de procesamiento
DELETE FROM rfx_processing_status;

-- Limpiar organization_id de tablas
UPDATE users SET organization_id = NULL, role = NULL;
UPDATE rfx_v2 SET organization_id = NULL;
UPDATE companies SET organization_id = NULL;
UPDATE suppliers SET organization_id = NULL;

-- Eliminar organización por defecto
DELETE FROM organizations WHERE slug = 'default-org';

COMMIT;
*/
