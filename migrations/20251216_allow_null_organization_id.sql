-- Migration: Allow NULL in users.organization_id
-- Date: 2025-12-16
-- Purpose: Permitir que usuarios existan sin organización asignada (plan personal)

-- Paso 1: Eliminar el constraint NOT NULL de organization_id
ALTER TABLE users ALTER COLUMN organization_id DROP NOT NULL;

-- Paso 2: Eliminar el constraint NOT NULL de role (opcional, para usuarios sin org)
ALTER TABLE users ALTER COLUMN role DROP NOT NULL;

-- Verificación: Estos comandos deberían funcionar ahora sin error
-- UPDATE users SET organization_id = NULL, role = NULL WHERE id = 'some-user-id';

-- Notas:
-- - Usuarios con organization_id = NULL tendrán plan personal
-- - Usuarios con organization_id = NULL no tendrán rol (role = NULL)
-- - Esto permite remover usuarios de organizaciones sin eliminarlos de la BD
