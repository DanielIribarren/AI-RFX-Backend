-- ============================================
-- MIGRATION: Product Catalog System
-- Version: 3.0
-- Date: 2026-01-29
-- Description: Sistema de catálogo de productos con búsqueda híbrida
-- ============================================

-- ============================================
-- 1. HABILITAR EXTENSIÓN pg_trgm (Fuzzy Search)
-- ============================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON EXTENSION pg_trgm IS 'Fuzzy text search using trigram matching';

-- ============================================
-- 2. TABLA PRINCIPAL: product_catalog
-- ============================================
CREATE TABLE IF NOT EXISTS product_catalog (
    -- Identificadores
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Información del producto
    product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100),  -- SKU, código interno (opcional)
    
    -- Pricing (flexible - al menos uno requerido)
    unit_cost DECIMAL(10,2),     -- Costo unitario (lo que pagamos)
    unit_price DECIMAL(10,2),    -- Precio unitario (lo que cobramos)
    
    -- Metadata
    unit VARCHAR(50) DEFAULT 'unit',  -- Unidad de medida
    is_active BOOLEAN DEFAULT true,   -- Soft delete
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints de validación
    CONSTRAINT at_least_one_price CHECK (
        unit_cost IS NOT NULL OR unit_price IS NOT NULL
    ),
    CONSTRAINT positive_values CHECK (
        (unit_cost IS NULL OR unit_cost > 0) AND
        (unit_price IS NULL OR unit_price > 0)
    )
);

-- ============================================
-- 3. ÍNDICES PARA PERFORMANCE
-- ============================================

-- Índice principal: búsqueda por organización y estado
CREATE INDEX idx_product_catalog_org_active 
ON product_catalog(organization_id, is_active);

-- Índice para búsqueda por nombre
CREATE INDEX idx_product_catalog_name 
ON product_catalog(product_name);

-- Índice para búsqueda por código (solo si existe)
CREATE INDEX idx_product_catalog_code 
ON product_catalog(product_code) 
WHERE product_code IS NOT NULL;

-- Índice GIN para fuzzy search (CRÍTICO para performance)
CREATE INDEX idx_product_catalog_name_trgm 
ON product_catalog 
USING gin (product_name gin_trgm_ops);

-- ============================================
-- 4. TRIGGER PARA updated_at
-- ============================================

-- Reutilizar función existente si ya existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'update_updated_at_column'
    ) THEN
        CREATE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $func$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;
    END IF;
END $$;

-- Crear trigger
CREATE TRIGGER trigger_update_product_catalog_timestamp
BEFORE UPDATE ON product_catalog
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. COMENTARIOS PARA DOCUMENTACIÓN
-- ============================================

COMMENT ON TABLE product_catalog IS 
'Catálogo de productos por organización. Soporta búsqueda híbrida: exact match, fuzzy match (pg_trgm), y semantic search (embeddings en Redis).';

COMMENT ON COLUMN product_catalog.product_name IS 
'Nombre del producto. Indexado para búsqueda exact y fuzzy.';

COMMENT ON COLUMN product_catalog.product_code IS 
'Código SKU o identificador interno del producto (opcional).';

COMMENT ON COLUMN product_catalog.unit_cost IS 
'Costo unitario del producto (lo que pagamos al proveedor). Opcional pero al menos uno de cost/price debe existir.';

COMMENT ON COLUMN product_catalog.unit_price IS 
'Precio unitario de venta (lo que cobramos al cliente). Opcional pero al menos uno de cost/price debe existir.';

COMMENT ON COLUMN product_catalog.unit IS 
'Unidad de medida (kg, unit, liter, etc.). Default: "unit".';

COMMENT ON COLUMN product_catalog.is_active IS 
'Soft delete flag. false = producto eliminado lógicamente.';

-- ============================================
-- 6. VERIFICACIÓN DE INSTALACIÓN
-- ============================================

-- Verificar que pg_trgm está habilitado
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) THEN
        RAISE EXCEPTION 'pg_trgm extension not installed. Run: CREATE EXTENSION pg_trgm;';
    END IF;
    
    RAISE NOTICE '✅ pg_trgm extension is installed';
END $$;

-- Verificar que la tabla fue creada
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'product_catalog'
    ) THEN
        RAISE NOTICE '✅ product_catalog table created successfully';
    END IF;
END $$;

-- Verificar índices
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename = 'product_catalog';
    
    RAISE NOTICE '✅ Created % indexes on product_catalog', index_count;
END $$;

-- ============================================
-- 7. DATOS DE PRUEBA (OPCIONAL - COMENTADO)
-- ============================================

-- Descomentar para insertar datos de prueba
/*
INSERT INTO product_catalog (
    organization_id,
    product_name,
    product_code,
    unit_cost,
    unit_price,
    unit
) VALUES
    (
        (SELECT id FROM organizations LIMIT 1),
        'Tequeños salados',
        'TEQ-001',
        0.45,
        0.68,
        'unit'
    ),
    (
        (SELECT id FROM organizations LIMIT 1),
        'Empanadas de carne',
        'EMP-001',
        0.50,
        0.75,
        'unit'
    ),
    (
        (SELECT id FROM organizations LIMIT 1),
        'Canapés variados',
        'CAN-001',
        0.60,
        0.85,
        'unit'
    );

RAISE NOTICE '✅ Inserted test data';
*/

-- ============================================
-- FIN DE MIGRATION
-- ============================================
