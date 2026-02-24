# Plan de Implementación: Optimización DB para RFX (Performance + Consistencia)

**Última actualización:** 2026-02-20 — Análisis real ejecutado contra DB de producción (`mjwnmzdgxcxubanubvms`)

## 1) Contexto
El backend de RFX presenta latencia creciente y resultados inconsistentes en endpoints de historial, latest y presupuesto, especialmente cuando aumenta el volumen de RFX y productos por solicitud.

Este plan describe:
- Problema actual y causas raíz.
- Hallazgos críticos técnicos **verificados contra datos reales de producción**.
- Implementación paso a paso para corregir performance y consistencia.
- Validaciones, métricas de éxito y estrategia de rollback.

## 2) Problema
### 2.1 Síntomas observados
- Endpoints de historial/listados se vuelven lentos al crecer la data.
- Variabilidad en tiempos de respuesta para consultas similares.
- Riesgo de inconsistencias en configuración de pricing bajo concurrencia.
- Exceso de roundtrips a Supabase para armar respuestas del frontend.

### 2.2 Impacto
- Mala experiencia de usuario (pantallas lentas en dashboard/historial).
- Mayor consumo de cuota DB y mayor costo operativo por consulta redundante.
- Riesgo de estados intermedios en pricing (datos parciales) cuando fallan operaciones intermedias.

## 3) Análisis Crítico (Causa Raíz)
## 3.1 Patrones ineficientes detectados
1. `N+1 queries` en listados de RFX:
   - Por cada RFX se consulta `rfx_products` para contar productos.
   - Resultado: 1 consulta base + N consultas adicionales.

2. Overfetching (`SELECT *`) en rutas calientes:
   - Se retornan columnas no usadas por el endpoint.
   - Resultado: mayor transferencia/red, más CPU de serialización.

3. Actualización de pricing en pasos secuenciales sin transacción única:
   - Se actualizan tabla principal y tablas hijas por separado.
   - Resultado: posibilidad de inconsistencia parcial bajo fallo/interrupción.

4. Índices incompletos para filtros reales de negocio:
   - Filtros frecuentes: `(organization_id, created_at)`, `(user_id, created_at)` y últimas propuestas por `rfx_id`.
   - Resultado: scans más costosos de lo necesario.

## 3.2 Riesgos de arquitectura
- “Paralelizar consultas” desde backend no corrige N+1; sólo distribuye costo y aumenta presión de conexiones.
- Debe priorizarse consolidación en DB (queries batch/RPC), no fan-out desde Python.

## 4) Problemas Encontrados
1. Consulta N+1 en endpoints de historial/latest/load-more para conteo de productos.
2. Falta de función batch para producto por RFX.
3. Falta de ruta atómica para upsert de pricing (principal + hijas).
4. Potencial carrera en creación de configuración activa de pricing.
5. Paginación con `total_items` no representa total real del dataset en algunos endpoints.
6. Índices no alineados al patrón de acceso principal.

## 5) Objetivos Técnicos
1. Reducir latencia P95 en endpoints de historial/latest/load-more al menos 40%.
2. Reducir roundtrips por request en endpoints de listado (eliminar N+1).
3. Garantizar consistencia de pricing con operación atómica.
4. Mejorar estabilidad bajo concurrencia (sin duplicados por `pricing_config_id`).

## 6) Solución Propuesta
### 6.1 Cambios en DB (base del plan)
Se implementa migración:
- `database/migrations/009_rfx_performance_and_pricing_consistency.sql`

Incluye:
1. Índices compuestos/condicionales para filtros reales.
2. Índices únicos en tablas hijas de pricing por `pricing_config_id`.
3. Función batch `get_rfx_product_counts(uuid[])`.
4. Función atómica `upsert_rfx_pricing_configuration_atomic(...)`.

### 6.2 Cambios en backend (aprovechar DB)
1. Reemplazar llamadas N+1 de conteo por llamada batch RPC.
2. Reemplazar flujo secuencial de pricing por RPC atómico.
3. Reducir `SELECT *` a proyecciones mínimas en endpoints críticos.
4. Ajustar paginación para devolver `total_count` real o adoptar cursor pagination.

## 7) Plan Paso a Paso
## Fase 0: Preparación
1. Respaldar esquema actual y funciones críticas.
2. Identificar ventana de despliegue con bajo tráfico.
3. Activar logging de latencia por endpoint si no existe.

Criterio de salida:
- Backup realizado y checklist de despliegue aprobado.

## Fase 1: Migración de DB
1. Ejecutar migración `009_rfx_performance_and_pricing_consistency.sql`.
2. Confirmar creación de índices:
   - `idx_rfx_v2_org_created_desc`
   - `idx_rfx_v2_user_personal_created_desc` o `idx_rfx_v2_user_created_desc`
   - índice para `generated_documents (rfx_id, document_type, created_at/generated_at desc)`
   - `idx_rfx_products_rfx_id`
3. Confirmar índices únicos en hijas de pricing:
   - `uq_coordination_config_pricing_id`
   - `uq_cost_per_person_config_pricing_id`
   - `uq_tax_config_pricing_id`
4. Confirmar funciones nuevas:
   - `get_rfx_product_counts`
   - `upsert_rfx_pricing_configuration_atomic`

Criterio de salida:
- Migración aplicada sin errores y objetos presentes.

## Fase 2: Refactor de consultas backend (performance)
1. Historial/latest/load-more:
   - Obtener IDs de RFX de la página.
   - Llamar una sola vez `get_rfx_product_counts`.
   - Mapear `product_count` en memoria sin consultas por item.
2. Mantener prefetch de última propuesta por lote (`get_latest_proposals_for_rfx_ids`).
3. Reducir payload de consultas en DB client:
   - Reemplazar `select("*")` por campos requeridos por endpoint.

Criterio de salida:
- No quedan llamadas `get_rfx_products(record["id"])` dentro de loops de listados.

## Fase 3: Refactor de pricing (consistencia)
1. En `pricing_config_service_v2`, reemplazar secuencia de upserts por llamada única a:
   - `upsert_rfx_pricing_configuration_atomic(...)`
2. Conservar lógica de negocio de defaults/normalización en backend.
3. Dejar que DB garantice atomicidad y unicidad por configuración.

Criterio de salida:
- Una sola operación RPC para actualización de pricing por request.

## Fase 4: Validación funcional y de performance
1. Validación funcional:
   - Historial, latest, load-more devuelven mismos datos funcionales.
   - Pricing se guarda igual en escenarios enabled/disabled.
2. Validación técnica:
   - Comparar latencia P50/P95 pre vs post.
   - Verificar reducción de roundtrips por request.
3. Prueba de concurrencia:
   - 10-20 requests concurrentes de update pricing sobre mismo RFX.
   - Verificar que no haya filas duplicadas en tablas hijas.

Criterio de salida:
- Objetivos de latencia y consistencia cumplidos.

## Fase 5: Hardening y observabilidad
1. Dashboard mínimo de métricas por endpoint (`history`, `latest`, `load-more`, `pricing`).
2. Alertas por latencia P95 y errores 5xx.
3. Registro de resultados de query plan para consultas críticas (cuando aplique).

## 8) Validaciones SQL Recomendadas
```sql
-- Ver funciones
select proname
from pg_proc
where proname in ('get_rfx_product_counts', 'upsert_rfx_pricing_configuration_atomic');

-- Ver índices críticos
select indexname, indexdef
from pg_indexes
where schemaname='public'
  and indexname in (
    'idx_rfx_v2_org_created_desc',
    'idx_rfx_v2_user_personal_created_desc',
    'idx_rfx_v2_user_created_desc',
    'idx_generated_documents_rfx_type_created_desc',
    'idx_generated_documents_rfx_type_generated_desc',
    'idx_rfx_products_rfx_id',
    'uq_coordination_config_pricing_id',
    'uq_cost_per_person_config_pricing_id',
    'uq_tax_config_pricing_id'
  );
```

## 9) Riesgos y Mitigación
1. Riesgo: datos existentes duplicados en tablas hijas de pricing impiden índice único.
   - Mitigación: script de deduplicación previo por `pricing_config_id` (mantener más reciente).

2. Riesgo: drift de esquema entre ambientes.
   - Mitigación: migración defensiva con checks de existencia (ya implementado).

3. Riesgo: cambios funcionales no deseados en listados.
   - Mitigación: pruebas snapshot de payload antes/después y feature flag temporal.

## 10) Rollback
1. Revertir backend a versión anterior.
2. Mantener funciones nuevas (son aditivas y seguras).
3. Si un índice impacta negativamente, remover índice específico con `DROP INDEX CONCURRENTLY` en ventana de mantenimiento.

## 11) Criterios de Éxito Final
- Reducción medible de latencia en endpoints de listados de RFX.
- Eliminación de N+1 en rutas principales.
- Sin inconsistencias de pricing bajo concurrencia.
- Menor variabilidad de tiempos y menor costo de consulta.

## 12) Próximos pasos sugeridos
1. Ejecutar migración 009 en staging y capturar baseline comparativo.
2. Aplicar refactor backend por fases (listados -> pricing).
3. Promover a producción con monitoreo reforzado 24-48h.
