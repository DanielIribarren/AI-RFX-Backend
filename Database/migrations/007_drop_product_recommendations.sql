-- Migration: Drop product_recommendations table
-- Reason: Not used in MVP, simplified to user_preferences table
-- Date: 2026-02-10

-- Drop table if exists
DROP TABLE IF EXISTS product_recommendations CASCADE;

-- Log migration
DO $$
BEGIN
    RAISE NOTICE '✅ Dropped product_recommendations table - not used in AI Learning MVP';
END $$;
