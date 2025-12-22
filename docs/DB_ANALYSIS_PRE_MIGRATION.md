# 🔍 ANÁLISIS DE BASE DE DATOS PRE-MIGRACIÓN
## Sistema de Créditos y Planes - Fase 1

**Fecha:** 9 de Diciembre, 2025  
**Analista:** AI Assistant  
**Propósito:** Análisis completo antes de migraciones para sistema de créditos

---

## 📊 ESTADO ACTUAL DE LA BASE DE DATOS

### Tablas Principales Identificadas

#### 1. `users` (17 columnas)
```sql
✅ id (UUID, PK)
✅ email (TEXT, NOT NULL)
✅ full_name (TEXT, NOT NULL)
✅ organization_id (UUID, NOT NULL, FK → organizations.id)
✅ role (VARCHAR, DEFAULT 'member')
✅ created_at, updated_at (TIMESTAMPTZ)

❌ NO TIENE: personal_plan_tier, credits_total, credits_used, credits_reset_date
```

**Observaciones:**
- Ya tiene `organization_id` (multi-tenant implementado ✅)
- Ya tiene `role` (owner/admin/member implementado ✅)
- Necesita columnas de créditos personales

#### 2. `organizations` (10 columnas)
```sql
✅ id (UUID, PK)
✅ name (VARCHAR)
✅ slug (VARCHAR, UNIQUE)
✅ plan_tier (VARCHAR, DEFAULT 'free') ← YA EXISTE
✅ max_users (INTEGER, DEFAULT 2) ← YA EXISTE
✅ max_rfx_per_month (INTEGER, DEFAULT 10) ← YA EXISTE
✅ is_active (BOOLEAN)
✅ trial_ends_at (TIMESTAMPTZ)
✅ created_at, updated_at (TIMESTAMPTZ)

❌ NO TIENE: credits_total, credits_used, credits_reset_date
```

**Observaciones:**
- Estructura multi-tenant ya implementada ✅
- Ya tiene `plan_tier` con constraint CHECK (free/pro/enterprise)
- Solo necesita columnas de créditos

#### 3. `rfx_v2` (38 columnas)
```sql
✅ id (UUID, PK)
✅ user_id (UUID, FK → users.id)
✅ organization_id (UUID, NOT NULL, FK → organizations.id)
✅ company_id, requester_id
✅ rfx_type, title, description, status
✅ ... (muchos campos de negocio)

❌ NO TIENE: has_extracted_data, has_generated_proposal, regeneration_count
```

**Observaciones:**
- Tabla principal de negocio con 98 registros
- Ya tiene `user_id` y `organization_id` ✅
- **NO debe agregar columnas de procesamiento aquí (anti-patrón)**
- Necesita tabla separada `rfx_processing_status`

#### 4. Tablas NO Existentes
```
❌ credit_transactions - NO EXISTE
❌ rfx_processing_status - NO EXISTE
```

---

## 🎯 DATOS ACTUALES - SABRA CORPORATION

```sql
ID: 5237af2a-7b75-479a-925f-540fb4f2c2e8
Nombre: Sabra Corporation
Slug: sabra-corp-official
Plan: PRO
Max Users: 50
Max RFX/mes: 500
Activo: TRUE
Trial hasta: 2026-12-05
```

**Usuarios en Sabra Corp:** 5 usuarios
- 1 owner (iriyidan@gmail.com)
- 4 admins

**RFX en sistema:** 98 registros

---

## ⚠️ RIESGOS IDENTIFICADOS

### Riesgo ALTO
1. **Tabla `rfx_v2` tiene 98 registros**
   - Cualquier error en migración afecta datos de producción
   - Necesita backup antes de cualquier cambio
   - NO agregar columnas directamente (usar tabla separada)

2. **Foreign Keys activas**
   - `rfx_v2.organization_id` → `organizations.id`
   - `rfx_v2.user_id` → `users.id`
   - Cualquier cambio debe respetar integridad referencial

### Riesgo MEDIO
3. **Usuarios activos en sistema**
   - 5 usuarios en Sabra Corp
   - Agregar columnas con DEFAULT NULL puede causar issues
   - Necesita inicialización de valores

### Riesgo BAJO
4. **Plan tier ya existe**
   - `organizations.plan_tier` ya tiene constraint CHECK
   - Necesita verificar compatibilidad con nuevo enum (free/starter/pro/enterprise)

---

## ✅ ESTRATEGIA DE MIGRACIÓN SEGURA

### Fase 1A: Agregar Columnas a `users`
```sql
-- SAFE: Agregar columnas con DEFAULT
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    personal_plan_tier VARCHAR(20) DEFAULT 'free';
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_total INTEGER DEFAULT 100;
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_used INTEGER DEFAULT 0;
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_reset_date TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 month';
```

**Impacto:** BAJO - Solo agrega columnas, no modifica existentes  
**Rollback:** DROP COLUMN si es necesario

### Fase 1B: Agregar Columnas a `organizations`
```sql
-- SAFE: Agregar columnas con DEFAULT
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_total INTEGER DEFAULT 500;
    
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_used INTEGER DEFAULT 0;
    
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_reset_date TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 month';
```

**Impacto:** BAJO - Solo agrega columnas  
**Rollback:** DROP COLUMN si es necesario

### Fase 1C: Crear Tabla `credit_transactions`
```sql
-- SAFE: Nueva tabla, no afecta existentes
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    amount INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSONB,
    
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CHECK (amount != 0),
    CHECK (user_id IS NOT NULL OR organization_id IS NOT NULL)
);
```

**Impacto:** NINGUNO - Tabla nueva, sin datos  
**Rollback:** DROP TABLE si es necesario

### Fase 1D: Crear Tabla `rfx_processing_status` (NORMALIZADA)
```sql
-- SAFE: Nueva tabla, no modifica rfx_v2
CREATE TABLE IF NOT EXISTS rfx_processing_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL UNIQUE REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Estados de extracción
    has_extracted_data BOOLEAN DEFAULT FALSE,
    extraction_completed_at TIMESTAMPTZ,
    extraction_credits_consumed INTEGER DEFAULT 0,
    
    -- Estados de generación
    has_generated_proposal BOOLEAN DEFAULT FALSE,
    generation_completed_at TIMESTAMPTZ,
    generation_credits_consumed INTEGER DEFAULT 0,
    
    -- Regeneraciones
    regeneration_count INTEGER DEFAULT 0,
    last_regeneration_at TIMESTAMPTZ,
    free_regenerations_used INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CHECK (regeneration_count >= 0),
    CHECK (extraction_credits_consumed >= 0),
    CHECK (generation_credits_consumed >= 0)
);
```

**Impacto:** NINGUNO - Tabla nueva, sin datos  
**Rollback:** DROP TABLE si es necesario

### Fase 1E: Inicializar Sabra Corp
```sql
-- SAFE: Solo UPDATE, no DELETE ni ALTER
UPDATE organizations
SET 
    credits_total = 1500,  -- Plan PRO
    credits_used = 0,
    credits_reset_date = NOW() + INTERVAL '1 month'
WHERE id = '5237af2a-7b75-479a-925f-540fb4f2c2e8';
```

**Impacto:** BAJO - Solo actualiza 1 registro  
**Rollback:** Restaurar valores anteriores (NULL)

### Fase 1F: Inicializar Estados de RFX Existentes
```sql
-- SAFE: INSERT, no modifica rfx_v2
INSERT INTO rfx_processing_status (rfx_id, has_extracted_data, has_generated_proposal)
SELECT 
    id,
    FALSE,  -- Asumir que no están procesados
    FALSE
FROM rfx_v2
ON CONFLICT (rfx_id) DO NOTHING;
```

**Impacto:** BAJO - Solo inserta registros nuevos  
**Rollback:** DELETE FROM rfx_processing_status

---

## 🔒 PLAN DE BACKUP

### Antes de Migración
```sql
-- Backup de tablas críticas
CREATE TABLE users_backup_20251209 AS SELECT * FROM users;
CREATE TABLE organizations_backup_20251209 AS SELECT * FROM organizations;
CREATE TABLE rfx_v2_backup_20251209 AS SELECT * FROM rfx_v2;
```

### Verificación Post-Migración
```sql
-- Verificar que no se perdieron datos
SELECT COUNT(*) FROM users;  -- Debe ser igual a antes
SELECT COUNT(*) FROM organizations;  -- Debe ser igual a antes
SELECT COUNT(*) FROM rfx_v2;  -- Debe ser 98

-- Verificar nuevas columnas
SELECT personal_plan_tier, credits_total FROM users LIMIT 1;
SELECT credits_total, credits_used FROM organizations WHERE slug = 'sabra-corp-official';
SELECT COUNT(*) FROM credit_transactions;  -- Debe ser 0
SELECT COUNT(*) FROM rfx_processing_status;  -- Debe ser 98
```

---

## ✅ ORDEN DE EJECUCIÓN RECOMENDADO

1. ✅ **Backup de tablas críticas**
2. ✅ **Fase 1A:** Agregar columnas a `users`
3. ✅ **Fase 1B:** Agregar columnas a `organizations`
4. ✅ **Fase 1C:** Crear tabla `credit_transactions`
5. ✅ **Fase 1D:** Crear tabla `rfx_processing_status`
6. ✅ **Fase 1E:** Crear índices
7. ✅ **Fase 1F:** Crear trigger para `updated_at`
8. ✅ **Fase 1G:** Inicializar Sabra Corp
9. ✅ **Fase 1H:** Inicializar estados de RFX existentes
10. ✅ **Verificación:** Queries de validación

---

## 🎯 CRITERIOS DE ÉXITO

- [ ] Todas las migraciones ejecutadas sin errores
- [ ] Conteo de registros igual a antes
- [ ] Sabra Corp tiene `credits_total = 1500`
- [ ] 98 registros en `rfx_processing_status`
- [ ] Foreign keys intactas
- [ ] Índices creados correctamente
- [ ] Trigger funcionando

---

## 🚨 PLAN DE ROLLBACK

Si algo sale mal:

```sql
-- 1. Eliminar tablas nuevas
DROP TABLE IF EXISTS credit_transactions CASCADE;
DROP TABLE IF EXISTS rfx_processing_status CASCADE;

-- 2. Eliminar columnas agregadas
ALTER TABLE users DROP COLUMN IF EXISTS personal_plan_tier;
ALTER TABLE users DROP COLUMN IF EXISTS credits_total;
ALTER TABLE users DROP COLUMN IF EXISTS credits_used;
ALTER TABLE users DROP COLUMN IF EXISTS credits_reset_date;

ALTER TABLE organizations DROP COLUMN IF EXISTS credits_total;
ALTER TABLE organizations DROP COLUMN IF EXISTS credits_used;
ALTER TABLE organizations DROP COLUMN IF EXISTS credits_reset_date;

-- 3. Restaurar desde backup si es necesario
-- (solo si hubo corrupción de datos)
```

---

**Estado:** ✅ ANÁLISIS COMPLETO - LISTO PARA MIGRACIÓN  
**Próximo Paso:** Ejecutar migraciones en orden con MCP Server  
**Tiempo Estimado:** 5-10 minutos
