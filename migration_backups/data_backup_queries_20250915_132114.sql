
-- QUERIES PARA BACKUP DE DATOS CRÍTICOS
-- Ejecutar en Supabase SQL Editor antes de migración

-- 1. Contar registros actuales
SELECT 'rfx_v2' as table_name, COUNT(*) as count FROM rfx_v2
UNION ALL
SELECT 'companies' as table_name, COUNT(*) as count FROM companies
UNION ALL  
SELECT 'requesters' as table_name, COUNT(*) as count FROM requesters
UNION ALL
SELECT 'suppliers' as table_name, COUNT(*) as count FROM suppliers;

-- 2. Backup de configuraciones críticas
SELECT json_agg(row_to_json(rfx_v2.*)) as rfx_backup 
FROM rfx_v2 
WHERE created_at > CURRENT_DATE - INTERVAL '30 days';

-- 3. Backup de pricing configs
SELECT json_agg(row_to_json(rpc.*)) as pricing_configs_backup
FROM rfx_pricing_configurations rpc 
WHERE is_active = true;

-- 4. Verificar integridad referencial
SELECT 
  COUNT(*) as total_rfx,
  COUNT(DISTINCT company_id) as unique_companies,
  COUNT(DISTINCT requester_id) as unique_requesters
FROM rfx_v2;
