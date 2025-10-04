-- ========================
-- MIGRACIÓN MVP: Sistema de Usuarios + Branding por Usuario
-- Versión: 3.0 MVP
-- Fecha: 2024-10-04
-- Descripción: Implementación MÍNIMA para hoy - usuarios individuales con branding
-- PREPARADO PARA ESCALAR: Teams se puede agregar después sin romper nada
-- ========================

BEGIN;

-- ========================
-- PASO 1: TIPOS ENUM BÁSICOS
-- ========================

CREATE TYPE user_status AS ENUM (
    'active',
    'inactive',
    'pending_verification'
);

SELECT '✓ Step 1: ENUMs created' as status;

-- ========================
-- PASO 2: TABLA USERS (Minimalista)
-- ========================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Información básica
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,  -- bcrypt/argon2
    
    -- Perfil
    full_name TEXT NOT NULL,
    company_name TEXT,  -- Nombre de su empresa/negocio
    phone TEXT,
    
    -- Estado
    status user_status DEFAULT 'pending_verification',
    email_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMPTZ,
    
    -- Seguridad
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- PREPARADO PARA TEAMS (nullable por ahora, se llena después)
    default_team_id UUID,  -- NULL por ahora, se usará cuando agregues teams
    
    -- Constraints
    CONSTRAINT email_lowercase CHECK (email = LOWER(email)),
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Índices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_email_verified ON users(email_verified);

COMMENT ON TABLE users IS 'Usuarios del sistema. default_team_id preparado para migración futura a teams.';

SELECT '✓ Step 2: Users table created' as status;

-- ========================
-- PASO 3: TABLA PASSWORD_RESETS (Para recuperación)
-- ========================

CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 hour'),
    used_at TIMESTAMPTZ,
    
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_password_resets_token ON password_resets(token) WHERE used_at IS NULL;
CREATE INDEX idx_password_resets_user ON password_resets(user_id);

SELECT '✓ Step 3: Password resets table created' as status;

-- ========================
-- PASO 4: TABLA EMAIL_VERIFICATIONS
-- ========================

CREATE TABLE email_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    verified_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_verifications_token ON email_verifications(token) WHERE verified_at IS NULL;
CREATE INDEX idx_email_verifications_user ON email_verifications(user_id);

SELECT '✓ Step 4: Email verifications table created' as status;

-- ========================
-- PASO 5: MODIFICAR TABLAS EXISTENTES (User ownership)
-- ========================

-- Agregar user_id a rfx_v2 (quien creó el RFX en tu sistema)
ALTER TABLE rfx_v2
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN team_id UUID;  -- NULL por ahora, se usará después

-- Agregar user_id a companies (cada usuario tiene sus propios clientes)
ALTER TABLE companies
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN team_id UUID;  -- NULL por ahora

-- Agregar user_id a suppliers
ALTER TABLE suppliers
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN team_id UUID;  -- NULL por ahora

-- Agregar user_id a product_catalog
ALTER TABLE product_catalog
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN team_id UUID;  -- NULL por ahora

-- Índices para ownership
CREATE INDEX idx_rfx_user ON rfx_v2(user_id);
CREATE INDEX idx_companies_user ON companies(user_id);
CREATE INDEX idx_suppliers_user ON suppliers(user_id);
CREATE INDEX idx_products_user ON product_catalog(user_id);

-- Índices para team_id (preparados para el futuro)
CREATE INDEX idx_rfx_team ON rfx_v2(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_companies_team ON companies(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_suppliers_team ON suppliers(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_products_team ON product_catalog(team_id) WHERE team_id IS NOT NULL;

COMMENT ON COLUMN rfx_v2.user_id IS 'Usuario que creó este RFX en el sistema';
COMMENT ON COLUMN rfx_v2.team_id IS 'Preparado para migración a teams - NULL por ahora';

SELECT '✓ Step 5: Existing tables updated with user ownership' as status;

-- ========================
-- PASO 6: ACTUALIZAR BRANDING (company_id → user_id)
-- ========================

-- Modificar company_branding_assets
ALTER TABLE company_branding_assets
    DROP CONSTRAINT IF EXISTS company_branding_assets_company_id_fkey,
    DROP CONSTRAINT IF EXISTS unique_company_branding;

-- Renombrar columna
ALTER TABLE company_branding_assets 
    RENAME COLUMN company_id TO user_id;

-- Agregar column para teams (preparado)
ALTER TABLE company_branding_assets
    ADD COLUMN team_id UUID;  -- NULL por ahora

-- Nueva foreign key
ALTER TABLE company_branding_assets
    ADD CONSTRAINT company_branding_assets_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Constraint: una configuración por usuario
ALTER TABLE company_branding_assets
    ADD CONSTRAINT unique_user_branding UNIQUE(user_id);

-- Actualizar índices
DROP INDEX IF EXISTS idx_company_branding_company_id;
DROP INDEX IF EXISTS idx_company_branding_active;

CREATE INDEX idx_user_branding_user_id ON company_branding_assets(user_id);
CREATE INDEX idx_user_branding_active ON company_branding_assets(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_team_branding_team_id ON company_branding_assets(team_id) WHERE team_id IS NOT NULL;

-- Actualizar comentarios
COMMENT ON TABLE company_branding_assets IS 'Branding por USUARIO. team_id preparado para migración futura.';
COMMENT ON COLUMN company_branding_assets.user_id IS 'Usuario dueño de esta configuración de branding';
COMMENT ON COLUMN company_branding_assets.team_id IS 'Preparado para teams - NULL por ahora';

-- Actualizar función de branding
DROP FUNCTION IF EXISTS get_company_branding(UUID);
DROP FUNCTION IF EXISTS get_team_branding(UUID);

CREATE OR REPLACE FUNCTION get_user_branding(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    logo_url TEXT,
    template_url TEXT,
    logo_analysis JSONB,
    template_analysis JSONB,
    analysis_status TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cba.id,
        cba.user_id,
        cba.logo_url,
        cba.template_url,
        cba.logo_analysis,
        cba.template_analysis,
        cba.analysis_status,
        cba.is_active,
        cba.created_at,
        cba.updated_at
    FROM company_branding_assets cba
    WHERE cba.user_id = user_uuid 
    AND cba.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS has_branding_configured(UUID);

CREATE OR REPLACE FUNCTION has_branding_configured(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM company_branding_assets 
        WHERE user_id = user_uuid 
        AND is_active = true
        AND analysis_status = 'completed'
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_branding(UUID) IS 'Obtiene branding del usuario';
COMMENT ON FUNCTION has_branding_configured(UUID) IS 'Verifica si usuario tiene branding configurado';

SELECT '✓ Step 6: Branding migrated to user ownership' as status;

-- ========================
-- PASO 7: TRIGGERS
-- ========================

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT '✓ Step 7: Triggers created' as status;

-- ========================
-- PASO 8: FUNCIONES AUXILIARES
-- ========================

-- Generar token seguro
CREATE OR REPLACE FUNCTION generate_secure_token()
RETURNS TEXT AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Verificar email
CREATE OR REPLACE FUNCTION verify_user_email(verification_token TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- Obtener verificación
    SELECT user_id, expires_at INTO v_user_id, v_expires_at
    FROM email_verifications
    WHERE token = verification_token
    AND verified_at IS NULL;
    
    -- Validar
    IF v_user_id IS NULL THEN
        RETURN false;
    END IF;
    
    IF v_expires_at < NOW() THEN
        RETURN false;
    END IF;
    
    -- Marcar como verificado
    UPDATE email_verifications
    SET verified_at = NOW()
    WHERE token = verification_token;
    
    -- Actualizar usuario
    UPDATE users
    SET email_verified = true,
        email_verified_at = NOW(),
        status = 'active'
    WHERE id = v_user_id;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Limpiar tokens expirados (ejecutar periódicamente)
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS TABLE (
    password_resets_cleaned INTEGER,
    email_verifications_cleaned INTEGER
) AS $$
DECLARE
    pr_count INTEGER;
    ev_count INTEGER;
BEGIN
    DELETE FROM password_resets WHERE expires_at < NOW() AND used_at IS NULL;
    GET DIAGNOSTICS pr_count = ROW_COUNT;
    
    DELETE FROM email_verifications WHERE expires_at < NOW() AND verified_at IS NULL;
    GET DIAGNOSTICS ev_count = ROW_COUNT;
    
    RETURN QUERY SELECT pr_count, ev_count;
END;
$$ LANGUAGE plpgsql;

-- Obtener datos completos del usuario
CREATE OR REPLACE FUNCTION get_user_profile(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    email TEXT,
    full_name TEXT,
    company_name TEXT,
    phone TEXT,
    status TEXT,
    email_verified BOOLEAN,
    last_login_at TIMESTAMPTZ,
    has_branding BOOLEAN,
    rfx_count BIGINT,
    companies_count BIGINT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.email,
        u.full_name,
        u.company_name,
        u.phone,
        u.status::TEXT,
        u.email_verified,
        u.last_login_at,
        has_branding_configured(u.id) as has_branding,
        COUNT(DISTINCT r.id) as rfx_count,
        COUNT(DISTINCT c.id) as companies_count,
        u.created_at
    FROM users u
    LEFT JOIN rfx_v2 r ON u.id = r.user_id
    LEFT JOIN companies c ON u.id = c.user_id
    WHERE u.id = user_uuid
    GROUP BY u.id;
END;
$$ LANGUAGE plpgsql;

SELECT '✓ Step 8: Helper functions created' as status;

-- ========================
-- PASO 9: VISTAS ÚTILES
-- ========================

CREATE VIEW users_summary AS
SELECT 
    u.id,
    u.email,
    u.full_name,
    u.company_name,
    u.status,
    u.email_verified,
    u.last_login_at,
    COUNT(DISTINCT r.id) as rfx_count,
    COUNT(DISTINCT c.id) as companies_count,
    COUNT(DISTINCT s.id) as suppliers_count,
    EXISTS(SELECT 1 FROM company_branding_assets WHERE user_id = u.id AND is_active = true) as has_branding,
    u.created_at
FROM users u
LEFT JOIN rfx_v2 r ON u.id = r.user_id
LEFT JOIN companies c ON u.id = c.user_id
LEFT JOIN suppliers s ON u.id = s.user_id
GROUP BY u.id;

SELECT '✓ Step 9: Views created' as status;

-- ========================
-- PASO 10: DATOS DE EJEMPLO (OPCIONAL - Comentado)
-- ========================

-- Descomentar para crear usuario de prueba
/*
-- Crear usuario de prueba (password: "Test123456")
INSERT INTO users (email, password_hash, full_name, company_name, status, email_verified)
VALUES (
    'test@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYXqK3bZvPK',  -- bcrypt hash
    'Usuario de Prueba',
    'Mi Empresa Test',
    'active',
    true
);

-- Crear verificación de email
INSERT INTO email_verifications (user_id, token)
VALUES (
    (SELECT id FROM users WHERE email = 'test@example.com'),
    generate_secure_token()
);
*/

SELECT '✓ Step 10: Test data ready (commented)' as status;

COMMIT;

-- ========================
-- VERIFICACIÓN FINAL
-- ========================

SELECT '✅ MVP MIGRATION COMPLETE!' as status;

-- Verificar estructura
SELECT 'Users table:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;

SELECT 'Branding table updated:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'company_branding_assets' 
ORDER BY ordinal_position;

-- Verificar funciones
SELECT 'Functions available:' as info;
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND (routine_name LIKE '%user%' OR routine_name LIKE '%branding%')
ORDER BY routine_name;

-- Estadísticas
SELECT 
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM password_resets) as password_resets_count,
    (SELECT COUNT(*) FROM email_verifications) as email_verifications_count;

SELECT '🚀 READY FOR PRODUCTION - Teams can be added later without breaking changes!' as final_message;
