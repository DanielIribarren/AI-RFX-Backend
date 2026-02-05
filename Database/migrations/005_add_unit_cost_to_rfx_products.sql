-- Migration: Add unit_cost column to rfx_products table
-- Date: 2026-02-05
-- Purpose: Diferenciar entre costo del proveedor (unit_cost) y precio al cliente (estimated_unit_price)

-- Add unit_cost column
ALTER TABLE rfx_products 
ADD COLUMN IF NOT EXISTS unit_cost DECIMAL(10,2);

-- Add comment
COMMENT ON COLUMN rfx_products.unit_cost IS 'Costo unitario del proveedor (lo que le cuesta al negocio)';
COMMENT ON COLUMN rfx_products.estimated_unit_price IS 'Precio unitario al cliente final (precio de venta)';

-- Add index for queries filtering by cost
CREATE INDEX IF NOT EXISTS idx_rfx_products_unit_cost ON rfx_products(unit_cost) WHERE unit_cost IS NOT NULL;

-- Update total_estimated_cost to use unit_cost if available (optional - depends on business logic)
-- Por ahora mantenemos total_estimated_cost basado en estimated_unit_price (precio al cliente)
-- Si necesitas calcular margen de ganancia, puedes agregar una columna calculada:
-- total_margin DECIMAL(12,2) GENERATED ALWAYS AS (quantity * (COALESCE(estimated_unit_price, 0) - COALESCE(unit_cost, 0))) STORED

-- Verification query
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'rfx_products' 
        AND column_name = 'unit_cost'
    ) THEN
        RAISE NOTICE '✅ Migration successful: unit_cost column added to rfx_products';
    ELSE
        RAISE EXCEPTION '❌ Migration failed: unit_cost column not found';
    END IF;
END $$;
