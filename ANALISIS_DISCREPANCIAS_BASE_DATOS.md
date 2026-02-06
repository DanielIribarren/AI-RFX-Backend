# 🔍 ANÁLISIS DE DISCREPANCIAS Y REDUNDANCIAS - BASE DE DATOS

**Fecha:** 5 de Febrero, 2026  
**Versión:** 1.0  
**Objetivo:** Identificar discrepancias entre esquema de BD, migraciones y código Python

---

## 📋 RESUMEN EJECUTIVO

### Problemas Críticos Encontrados
1. **Discrepancia de Esquema:** Schema V3.0 vs Migraciones vs Código Python
2. **Configuraciones Duplicadas:** `OpenAIConfig` vs `AIConfig`
3. **Campos Inconsistentes:** `received_at` vs `created_at` en `rfx_v2`
4. **Nomenclatura Mixta:** `product_name` vs `name` en `product_catalog`
5. **Campos Preparados pero No Usados:** `team_id` en múltiples tablas
6. **Sistema de Organizaciones:** Migración parcial implementada

---

## 🔴 PROBLEMA 1: DISCREPANCIA DE ESQUEMA - `rfx_v2` TABLE

### 📍 Ubicación del Problema

**Schema V3.0 (Complete-Schema-V3.0-With-Auth.sql):**
```sql
CREATE TABLE rfx_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id UUID,  -- NULL por ahora
    -- ... otros campos ...
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Código Python (backend/core/database.py):**
```python
# Línea 309: Usa received_at (NO EXISTE en schema V3.0)
response = query.order("received_at", desc=True)

# Línea 349: Usa created_at (CORRECTO)
response = query.order("created_at", desc=True)

# Línea 356-367: Fallback a received_at (campo que NO existe)
# Fallback to received_at if created_at doesn't work
response = query.order("received_at", desc=True)
```

### 🔧 Impacto
- **Severidad:** CRÍTICA ❌
- **Comportamiento:** Queries fallan intermitentemente
- **Causa:** Schema V3.0 NO tiene columna `received_at`, pero código asume que existe

### ✅ Solución Propuesta

**Opción A: Agregar columna `received_at` al schema**
```sql
ALTER TABLE rfx_v2 ADD COLUMN received_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX idx_rfx_v2_received_at ON rfx_v2(received_at DESC);
```

**Opción B: Eliminar referencias a `received_at` del código (RECOMENDADO)**
```python
# Usar SOLO created_at en todas las queries
response = query.order("created_at", desc=True)
```

**Decisión:** Opción B - Usar solo `created_at` (más simple, menos redundancia)

---

## 🔴 PROBLEMA 2: CONFIGURACIONES DUPLICADAS - OpenAI

### 📍 Ubicación del Problema

**Archivo 1: `backend/core/config.py` (Líneas 36-49)**
```python
@dataclass
class OpenAIConfig:
    """OpenAI API configuration - Optimized for GPT-4o with extended context"""
    api_key: str
    model: str = "gpt-4o"  # Default GPT-4o
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout: int = 60
    context_window: int = 128000
```

**Archivo 2: `backend/core/ai_config.py` (Líneas 12-20)**
```python
class AIConfig:
    """Configuración para el agente de IA del chat conversacional."""
    OPENAI_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY", "")
    MODEL: Final[str] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # ❌ Diferente default
    MAX_TOKENS: Final[int] = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))  # ❌ Diferente
    TEMPERATURE: Final[float] = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))  # ❌ Diferente
    TIMEOUT: Final[int] = int(os.getenv("OPENAI_TIMEOUT", "60"))  # ✅ Igual
```

### 🔧 Impacto
- **Severidad:** ALTA ⚠️
- **Comportamiento:** Diferentes servicios usan diferentes configuraciones
- **Causa:** Dos fuentes de verdad para la misma configuración

### ✅ Solución Propuesta

**Consolidar en UNA SOLA clase:**
```python
# backend/core/config.py (ÚNICA FUENTE DE VERDAD)
@dataclass
class OpenAIConfig:
    """Unified OpenAI configuration"""
    api_key: str
    
    # Modelos por caso de uso
    default_model: str = "gpt-4o"
    chat_model: str = "gpt-4o-mini"  # Más económico para chat
    extraction_model: str = "gpt-4o"  # Más preciso para extracción
    
    # Tokens por caso de uso
    default_max_tokens: int = 4096
    chat_max_tokens: int = 2000
    
    # Configuración compartida
    temperature: float = 0.1
    timeout: int = 60
    context_window: int = 128000
```

**Eliminar:** `backend/core/ai_config.py` (mover funciones de costo a `config.py`)

---

## 🟡 PROBLEMA 3: NOMENCLATURA INCONSISTENTE - `product_catalog`

### 📍 Ubicación del Problema

**Schema V3.0 (Complete-Schema-V3.0-With-Auth.sql):**
```sql
CREATE TABLE product_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID,
    name TEXT NOT NULL,  -- ❌ Usa "name"
    category TEXT NOT NULL,
    -- ...
);
```

**Migración 003 (migrations/003_create_product_catalog.sql):**
```sql
CREATE TABLE IF NOT EXISTS product_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),  -- ❌ Usa organization_id
    product_name VARCHAR(255) NOT NULL,  -- ✅ Usa "product_name"
    product_code VARCHAR(100),
    unit_cost DECIMAL(10,2),
    unit_price DECIMAL(10,2),
    -- ...
);
```

**Código Python (backend/services/catalog_import_service.py):**
```python
# Línea 24: Usa product_name
'product_name': 'Nombre descriptivo del producto',

# Línea 196: Usa product_name
'product_name': str(row[mapping['product_name']]).strip(),
```

### 🔧 Impacto
- **Severidad:** ALTA ⚠️
- **Comportamiento:** Schema V3.0 NO coincide con migraciones ni código
- **Causa:** Schema V3.0 desactualizado

### ✅ Solución Propuesta

**Schema V3.0 está DESACTUALIZADO. Usar Migración 003 como fuente de verdad:**

```sql
-- CORRECTO (según migración 003 y código Python):
product_name VARCHAR(255) NOT NULL  -- ✅
product_code VARCHAR(100)           -- ✅
unit_cost DECIMAL(10,2)             -- ✅
unit_price DECIMAL(10,2)            -- ✅
organization_id UUID                -- ✅ (puede ser NULL según migración 004)
user_id UUID                        -- ✅ (agregado en migración 004)
```

**Acción:** Actualizar `Complete-Schema-V3.0-With-Auth.sql` para reflejar migraciones

---

## 🟡 PROBLEMA 4: SISTEMA DE ORGANIZACIONES - MIGRACIÓN PARCIAL

### 📍 Ubicación del Problema

**Schema V3.0 NO tiene tabla `organizations`:**
```sql
-- ❌ NO EXISTE en Complete-Schema-V3.0-With-Auth.sql
CREATE TABLE organizations (...);
```

**Pero el código Python SÍ la usa:**
```python
# backend/core/database.py (Línea 1468)
response = self.client.table("organizations")\
    .select("id, name, slug, plan_tier, max_users, ...")\
    .eq("id", str(organization_id))\
    .execute()

# backend/api/organization.py (31 matches)
# backend/services/credits_service.py (30 matches)
```

**Migraciones indican que SÍ existe:**
```python
# migrations/003_create_product_catalog.sql (Línea 21)
organization_id UUID NOT NULL REFERENCES organizations(id)
```

### 🔧 Impacto
- **Severidad:** CRÍTICA ❌
- **Comportamiento:** Schema V3.0 está desactualizado
- **Causa:** Sistema de organizaciones implementado DESPUÉS de schema V3.0

### ✅ Solución Propuesta

**Crear migración completa de organizaciones:**
```sql
-- migrations/002_create_organizations_system.sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) DEFAULT 'free',
    max_users INTEGER DEFAULT 5,
    max_rfx_per_month INTEGER DEFAULT 50,
    credits_total INTEGER DEFAULT 100,
    credits_used INTEGER DEFAULT 0,
    credits_reset_date TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agregar organization_id a tablas existentes
ALTER TABLE users ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE users ADD COLUMN role VARCHAR(50);
ALTER TABLE rfx_v2 ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE companies ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE suppliers ADD COLUMN organization_id UUID REFERENCES organizations(id);
```

**Acción:** Documentar schema completo con organizaciones

---

## 🟡 PROBLEMA 5: CAMPOS `team_id` PREPARADOS PERO NO USADOS

### 📍 Ubicación del Problema

**Schema V3.0 define `team_id` en múltiples tablas:**
```sql
-- users
default_team_id UUID,  -- NULL por ahora

-- companies
team_id UUID,  -- NULL por ahora, preparado para teams

-- suppliers
team_id UUID,

-- product_catalog
team_id UUID,

-- rfx_v2
team_id UUID,  -- NULL por ahora
```

**Código Python NO usa `team_id`:**
```bash
$ grep -r "team_id" backend/**/*.py
# Resultado: 0 matches (excepto comentarios)
```

### 🔧 Impacto
- **Severidad:** BAJA ℹ️
- **Comportamiento:** Campos muertos en BD
- **Causa:** Preparación para feature futuro

### ✅ Solución Propuesta

**Opción A: Eliminar campos `team_id` (RECOMENDADO para simplicidad)**
```sql
ALTER TABLE users DROP COLUMN default_team_id;
ALTER TABLE companies DROP COLUMN team_id;
ALTER TABLE suppliers DROP COLUMN team_id;
ALTER TABLE product_catalog DROP COLUMN team_id;
ALTER TABLE rfx_v2 DROP COLUMN team_id;
```

**Opción B: Mantener pero documentar claramente**
```sql
COMMENT ON COLUMN users.default_team_id IS 
'PREPARADO PARA FUTURO - No usar hasta implementación de teams';
```

**Decisión:** Opción B (mantener para futuro, pero documentar que NO está implementado)

---

## 🟡 PROBLEMA 6: COLUMNA `unit_cost` AGREGADA DESPUÉS

### 📍 Ubicación del Problema

**Migración 005 (migrations/005_add_unit_cost_to_rfx_products.sql):**
```sql
-- Add unit_cost column
ALTER TABLE rfx_products 
ADD COLUMN IF NOT EXISTS unit_cost DECIMAL(10,2);
```

**Schema V3.0 NO tiene `unit_cost` en `rfx_products`:**
```sql
CREATE TABLE rfx_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    product_catalog_id UUID REFERENCES product_catalog(id),
    product_name TEXT NOT NULL,
    -- ...
    estimated_unit_price DECIMAL(10,2),  -- ✅ Existe
    -- ❌ NO tiene unit_cost
);
```

**Código Python SÍ usa `unit_cost`:**
```python
# backend/core/database.py (Línea 528)
.select("id, rfx_id, product_name, description, quantity, unit, estimated_unit_price, unit_cost, notes, created_at")

# backend/core/database.py (Línea 562)
.update({"unit_cost": unit_cost})
```

### 🔧 Impacto
- **Severidad:** MEDIA ⚠️
- **Comportamiento:** Schema V3.0 desactualizado
- **Causa:** Migración 005 agregó columna DESPUÉS de schema V3.0

### ✅ Solución Propuesta

**Actualizar Schema V3.0:**
```sql
CREATE TABLE rfx_products (
    -- ... campos existentes ...
    estimated_unit_price DECIMAL(10,2),
    unit_cost DECIMAL(10,2),  -- ✅ AGREGAR
    total_estimated_cost DECIMAL(12,2) GENERATED ALWAYS AS (quantity * COALESCE(estimated_unit_price, 0)) STORED,
    -- ...
);

-- Agregar índice
CREATE INDEX IF NOT EXISTS idx_rfx_products_unit_cost 
ON rfx_products(unit_cost) WHERE unit_cost IS NOT NULL;
```

---

## 📊 TABLA RESUMEN DE DISCREPANCIAS

| # | Problema | Severidad | Archivos Afectados | Solución |
|---|----------|-----------|-------------------|----------|
| 1 | `received_at` vs `created_at` | 🔴 CRÍTICA | `database.py` | Eliminar `received_at`, usar solo `created_at` |
| 2 | Configuraciones OpenAI duplicadas | 🟡 ALTA | `config.py`, `ai_config.py` | Consolidar en `config.py` |
| 3 | `name` vs `product_name` en catalog | 🟡 ALTA | Schema V3.0, migraciones | Actualizar schema a `product_name` |
| 4 | Tabla `organizations` faltante | 🔴 CRÍTICA | Schema V3.0 | Documentar schema completo |
| 5 | Campos `team_id` no usados | 🟢 BAJA | Múltiples tablas | Documentar como "preparado para futuro" |
| 6 | `unit_cost` faltante en schema | 🟡 MEDIA | Schema V3.0, `rfx_products` | Agregar columna al schema |

---

## 🎯 RECOMENDACIONES PRIORITARIAS

### Prioridad 1: CRÍTICAS (Hacer AHORA)
1. **Eliminar referencias a `received_at`** en `database.py`
2. **Documentar schema completo** con tabla `organizations`
3. **Crear schema V3.1** que refleje estado REAL de la BD

### Prioridad 2: ALTAS (Hacer en Fase 1)
4. **Consolidar configuraciones OpenAI** en un solo archivo
5. **Actualizar schema** con `product_name` y `unit_cost`

### Prioridad 3: MEDIAS (Hacer en Fase 2)
6. **Documentar campos `team_id`** como preparados para futuro
7. **Crear tests** que validen schema vs código

---

## 📝 PLAN DE ACCIÓN ACTUALIZADO

### Fase 0: Correcciones Urgentes (ANTES de refactorización)
```
1. Eliminar referencias a received_at (2 horas)
   - Archivos: backend/core/database.py
   - Líneas: 309, 356-367
   
2. Crear Schema V3.1 actualizado (4 horas)
   - Incluir tabla organizations
   - Actualizar product_catalog (product_name, organization_id, user_id)
   - Agregar unit_cost a rfx_products
   - Documentar campos team_id como "preparados para futuro"
   
3. Consolidar configuraciones OpenAI (3 horas)
   - Eliminar backend/core/ai_config.py
   - Mover funciones de costo a backend/core/config.py
   - Actualizar imports en 12 archivos
```

### Fase 1: Refactorización (según plan original)
```
Continuar con plan de refactorización DESPUÉS de correcciones urgentes
```

---

## ✅ PRÓXIMOS PASOS

1. **Revisar este análisis con el usuario**
2. **Confirmar prioridades** (¿hacer correcciones urgentes primero?)
3. **Ajustar plan de refactorización** según hallazgos
4. **Proceder con implementación** una vez confirmado

---

**Estado:** ⏸️ ESPERANDO CONFIRMACIÓN DEL USUARIO
