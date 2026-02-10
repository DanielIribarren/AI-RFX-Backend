-- ============================================
-- AI LEARNING SYSTEM - MIGRACIONES V1.0
-- Fecha: 2026-02-06
-- Filosofía: KISS - Mínimo viable para aprendizaje
-- ============================================

BEGIN;

-- ============================================
-- 1. USER PREFERENCES (Configuraciones aprendidas)
-- ============================================
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Tipo de preferencia
    preference_type VARCHAR(50) NOT NULL, -- 'pricing', 'product', 'config'
    preference_key VARCHAR(100) NOT NULL, -- 'coordination_rate', 'default_products', etc.
    preference_value JSONB NOT NULL, -- Valor flexible
    
    -- Métricas de confianza
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, preference_type, preference_key),
    
    -- Índices
    INDEX idx_user_pref_type (user_id, preference_type),
    INDEX idx_org_pref_type (organization_id, preference_type),
    INDEX idx_last_used (last_used_at DESC)
);

COMMENT ON TABLE user_preferences IS 'Preferencias aprendidas por usuario (pricing, productos, configuraciones)';
COMMENT ON COLUMN user_preferences.preference_type IS 'Tipo: pricing, product, config, branding';
COMMENT ON COLUMN user_preferences.preference_value IS 'Valor JSONB flexible según tipo';
COMMENT ON COLUMN user_preferences.usage_count IS 'Cuántas veces se ha usado esta preferencia';

-- ============================================
-- 2. LEARNING EVENTS (Historial de aprendizaje)
-- ============================================
CREATE TABLE learning_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Tipo de evento
    event_type VARCHAR(50) NOT NULL, -- 'price_correction', 'product_selection', 'config_change'
    
    -- Contexto del evento
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    context JSONB NOT NULL, -- Contexto completo del evento
    
    -- Acción y resultado
    action_taken JSONB NOT NULL, -- Qué hizo el usuario
    outcome VARCHAR(50), -- 'accepted', 'rejected', 'modified'
    
    -- Metadata
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id VARCHAR(255),
    
    -- Índices
    INDEX idx_user_event_type (user_id, event_type),
    INDEX idx_org_timestamp (organization_id, timestamp DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_rfx_events (rfx_id)
);

COMMENT ON TABLE learning_events IS 'Historial de eventos de aprendizaje (correcciones, selecciones, cambios)';
COMMENT ON COLUMN learning_events.event_type IS 'Tipo: price_correction, product_selection, config_change, etc.';
COMMENT ON COLUMN learning_events.context IS 'Contexto completo: qué estaba haciendo el usuario';
COMMENT ON COLUMN learning_events.action_taken IS 'Acción específica: qué cambió el usuario';

-- ============================================
-- 3. PRICE CORRECTIONS (Correcciones de precios)
-- ============================================
CREATE TABLE price_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Producto
    product_name VARCHAR(255) NOT NULL,
    product_id UUID REFERENCES product_catalog(id) ON DELETE SET NULL,
    
    -- Corrección
    original_price NUMERIC(10,2) NOT NULL,
    corrected_price NUMERIC(10,2) NOT NULL,
    price_difference NUMERIC(10,2) GENERATED ALWAYS AS (corrected_price - original_price) STORED,
    
    -- Contexto
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    quantity INTEGER,
    context JSONB, -- Contexto adicional (tipo evento, fecha, etc.)
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índices
    INDEX idx_user_product (user_id, product_name),
    INDEX idx_org_product (organization_id, product_name),
    INDEX idx_created (created_at DESC)
);

COMMENT ON TABLE price_corrections IS 'Historial de correcciones de precios por usuario';
COMMENT ON COLUMN price_corrections.price_difference IS 'Diferencia calculada automáticamente';

-- ============================================
-- 4. PRODUCT RECOMMENDATIONS (Recomendaciones)
-- ============================================
CREATE TABLE product_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Recomendación
    product_name VARCHAR(255) NOT NULL,
    product_id UUID REFERENCES product_catalog(id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Contexto de recomendación
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    recommendation_reason VARCHAR(100), -- 'frequently_used', 'similar_rfx', 'co_occurrence'
    context JSONB,
    
    -- Resultado
    was_accepted BOOLEAN,
    accepted_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índices
    INDEX idx_user_accepted (user_id, was_accepted),
    INDEX idx_org_confidence (organization_id, confidence_score DESC),
    INDEX idx_created (created_at DESC)
);

COMMENT ON TABLE product_recommendations IS 'Recomendaciones de productos generadas por el sistema';
COMMENT ON COLUMN product_recommendations.confidence_score IS 'Confianza de la recomendación (0.0-1.0)';
COMMENT ON COLUMN product_recommendations.was_accepted IS 'Si el usuario aceptó la recomendación';

-- ============================================
-- 5. PRODUCT CO_OCCURRENCES (Productos que van juntos)
-- ============================================
CREATE TABLE product_co_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Par de productos
    product_a VARCHAR(255) NOT NULL,
    product_b VARCHAR(255) NOT NULL,
    
    -- Métricas
    co_occurrence_count INTEGER DEFAULT 1,
    confidence FLOAT DEFAULT 0.5,
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(organization_id, product_a, product_b),
    CHECK (product_a < product_b), -- Evitar duplicados (A,B) y (B,A)
    
    -- Índices
    INDEX idx_org_product_a (organization_id, product_a),
    INDEX idx_org_confidence (organization_id, confidence DESC)
);

COMMENT ON TABLE product_co_occurrences IS 'Productos que frecuentemente se usan juntos';
COMMENT ON COLUMN product_co_occurrences.co_occurrence_count IS 'Cuántas veces se han usado juntos';

-- ============================================
-- TRIGGERS PARA UPDATED_AT
-- ============================================
CREATE OR REPLACE FUNCTION update_learning_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_learning_updated_at();

-- ============================================
-- FUNCIÓN HELPER: Incrementar uso de preferencia
-- ============================================
CREATE OR REPLACE FUNCTION increment_preference_usage(
    p_user_id UUID,
    p_preference_type VARCHAR,
    p_preference_key VARCHAR
)
RETURNS VOID AS $$
BEGIN
    UPDATE user_preferences
    SET 
        usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE 
        user_id = p_user_id
        AND preference_type = p_preference_type
        AND preference_key = p_preference_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_preference_usage IS 'Incrementa contador de uso de una preferencia';

-- ============================================
-- FUNCIÓN HELPER: Registrar co-ocurrencia
-- ============================================
CREATE OR REPLACE FUNCTION register_product_co_occurrence(
    p_organization_id UUID,
    p_product_a VARCHAR,
    p_product_b VARCHAR
)
RETURNS VOID AS $$
DECLARE
    v_prod_a VARCHAR;
    v_prod_b VARCHAR;
BEGIN
    -- Ordenar alfabéticamente para evitar duplicados
    IF p_product_a < p_product_b THEN
        v_prod_a := p_product_a;
        v_prod_b := p_product_b;
    ELSE
        v_prod_a := p_product_b;
        v_prod_b := p_product_a;
    END IF;
    
    -- Upsert
    INSERT INTO product_co_occurrences (
        organization_id, product_a, product_b, co_occurrence_count, last_seen_at
    )
    VALUES (
        p_organization_id, v_prod_a, v_prod_b, 1, NOW()
    )
    ON CONFLICT (organization_id, product_a, product_b)
    DO UPDATE SET
        co_occurrence_count = product_co_occurrences.co_occurrence_count + 1,
        last_seen_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION register_product_co_occurrence IS 'Registra que dos productos se usaron juntos';

COMMIT;

-- ============================================
-- VERIFICACIÓN
-- ============================================
-- Verificar que las tablas se crearon correctamente
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'user_preferences',
                'learning_events',
                'price_corrections',
                'product_recommendations',
                'product_co_occurrences'
            )) = 5, 'Error: No se crearon todas las tablas del Learning System';
    
    RAISE NOTICE '✅ Learning System tables created successfully';
END $$;
