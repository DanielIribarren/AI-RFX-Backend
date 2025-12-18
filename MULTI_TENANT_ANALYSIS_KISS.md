# 🔍 Análisis Multi-Tenant KISS - Sistema RFX

**Fecha:** 5 de Diciembre, 2025  
**Objetivo:** Analizar estructura actual y diseñar solución multi-tenant más simple posible  
**Filosofía:** KISS - Keep It Simple, Stupid

---

## 📊 ANÁLISIS DE ESTRUCTURA ACTUAL

### ✅ Lo Que YA EXISTE (No Reinventar)

#### 1. **Sistema de Autenticación Completo**

```sql
-- Tabla: users (LÍNEA 74-105)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    full_name TEXT NOT NULL,
    company_name TEXT,  -- ⚠️ Nombre de SU empresa
    phone TEXT,
    status user_status DEFAULT 'pending_verification',
    last_login_at TIMESTAMPTZ,
    
    -- ✅ YA PREPARADO PARA TEAMS
    default_team_id UUID,  -- NULL por ahora
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**✅ Ya tenemos:**
- Sistema JWT funcionando (`backend/utils/auth_middleware.py`)
- Decorators: `@jwt_required`, `@optional_jwt`
- Funciones: `get_current_user()`, `get_current_user_id()`
- Validación de ownership: `validate_user_ownership()`

#### 2. **Aislamiento de Datos POR user_id**

```sql
-- TODAS estas tablas YA tienen user_id:
companies (user_id)           -- Línea 146
suppliers (user_id)           -- Línea 196
product_catalog (user_id)     -- Línea 219
rfx_v2 (user_id)             -- Línea 251
company_branding_assets (user_id)  -- Línea 554
```

**✅ Índices de performance YA CREADOS:**
```sql
CREATE INDEX idx_rfx_user ON rfx_v2(user_id);              -- Línea 622
CREATE INDEX idx_companies_user ON companies(user_id);      -- Línea 624
CREATE INDEX idx_suppliers_user ON suppliers(user_id);      -- Línea 626
CREATE INDEX idx_products_user ON product_catalog(user_id); -- Línea 628
```

#### 3. **Campo team_id YA PREPARADO**

```sql
-- Todas las tablas críticas tienen:
team_id UUID,  -- NULL por ahora, preparado para teams

-- Con índices condicionales:
CREATE INDEX idx_rfx_team ON rfx_v2(team_id) WHERE team_id IS NOT NULL;
```

**💡 Insight KISS:** El schema YA está preparado para multi-tenancy. Solo necesitamos:
1. Activar el campo `team_id` 
2. Crear tabla de organizaciones
3. Migrar datos existentes

---

## 🎯 DECISIÓN ARQUITECTÓNICA KISS

### Opción A: Shared Database + Row-Level Security (RLS)
```
✅ VENTAJAS:
- Schema YA tiene user_id en todas las tablas
- Índices YA están creados
- Middleware de auth YA funciona
- Supabase tiene RLS nativo
- Migración más simple

❌ DESVENTAJAS:
- Requiere cuidado en queries
- Todos los tenants en misma DB
```

### Opción B: Database Per Tenant
```
❌ DESVENTAJAS:
- Requiere reescribir lógica de conexión
- Mayor complejidad operativa
- Mayor costo de infraestructura
- Migración compleja

✅ VENTAJAS:
- Aislamiento total
- Más fácil de escalar (después)
```

### 🏆 DECISIÓN: **Opción A (Shared DB + RLS)**

**Razones KISS:**
1. **80% del trabajo ya está hecho** - Solo necesitamos agregar capa de organización
2. **No romper lo que funciona** - Sistema de auth actual es sólido
3. **Migración incremental** - Podemos hacerlo paso a paso
4. **Suficiente para 100-500 clientes** - Escalar después si es necesario

---

## 📐 MODELO DE DATOS KISS - MÍNIMO VIABLE

### 🆕 Nueva Tabla: `organizations` (SIMPLE)

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificación básica
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- sabra-corp
    
    -- Plan (SIMPLE - solo 3 planes)
    plan_tier VARCHAR(20) DEFAULT 'free' CHECK (plan_tier IN ('free', 'pro', 'enterprise')),
    
    -- Límites del plan (SIMPLE - solo lo esencial)
    max_users INTEGER DEFAULT 2,
    max_rfx_per_month INTEGER DEFAULT 10,
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice simple
CREATE INDEX idx_organizations_slug ON organizations(slug);
```

**💡 Decisión KISS:** 
- ❌ NO crear tabla `subscription_plans` separada (overkill para MVP)
- ✅ Solo 3 planes hardcodeados: free, pro, enterprise
- ✅ Límites en la misma tabla (más simple)

### 🔄 Modificar Tabla: `users` (MÍNIMO)

```sql
-- Solo agregar 2 campos:
ALTER TABLE users ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member'));

-- Índice simple
CREATE INDEX idx_users_organization ON users(organization_id);
```

**💡 Decisión KISS:**
- ✅ Solo 3 roles: owner, admin, member
- ❌ NO crear tabla `roles` separada
- ❌ NO crear tabla `permissions` (overkill)

### 🔄 Modificar Tabla: `rfx_v2` (MÍNIMO)

```sql
-- Solo agregar 1 campo:
ALTER TABLE rfx_v2 ADD COLUMN organization_id UUID REFERENCES organizations(id);

-- Índice crítico
CREATE INDEX idx_rfx_organization ON rfx_v2(organization_id);
```

**💡 Decisión KISS:**
- ✅ Mantener `user_id` (quién creó el RFX)
- ✅ Agregar `organization_id` (a qué organización pertenece)
- ✅ Ambos campos coexisten (trazabilidad)

---

## 🔧 CAMBIOS EN BACKEND - MÍNIMO VIABLE

### 1. **Middleware Simple** (NO crear servicio complejo)

```python
# backend/utils/organization_middleware.py

from functools import wraps
from flask import g, jsonify

def require_organization(f):
    """Inyecta organization_id en el contexto"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Usuario ya está en g.current_user (del jwt_required)
        user = g.current_user
        
        if not user.get('organization_id'):
            return jsonify({
                "error": "User not associated with organization"
            }), 403
        
        # Inyectar en contexto
        g.organization_id = user['organization_id']
        g.user_role = user.get('role', 'member')
        
        return f(*args, **kwargs)
    
    return decorated
```

**💡 Decisión KISS:**
- ✅ Solo un decorator simple
- ❌ NO crear `OrganizationService` complejo
- ✅ Reutilizar middleware de auth existente

### 2. **Modificar DatabaseClient** (MÍNIMO)

```python
# backend/core/database.py

class DatabaseClient:
    
    # ✅ Agregar método simple para filtrar por org
    def filter_by_organization(self, table: str, org_id: str):
        """Helper para filtrar por organización"""
        return self.client.table(table).select("*").eq("organization_id", org_id)
    
    # ✅ Modificar métodos existentes (ejemplo)
    def get_rfx_by_id(self, rfx_id: str, organization_id: str = None):
        query = self.client.table("rfx_v2").select("*").eq("id", rfx_id)
        
        # Si se pasa organization_id, filtrar
        if organization_id:
            query = query.eq("organization_id", organization_id)
        
        return query.single().execute()
```

**💡 Decisión KISS:**
- ✅ Agregar `organization_id` como parámetro opcional
- ✅ Mantener compatibilidad con código existente
- ❌ NO reescribir todos los métodos de golpe

### 3. **Uso en Endpoints** (SIMPLE)

```python
# backend/api/rfx.py

@rfx_bp.route("/", methods=["POST"])
@jwt_required
@require_organization  # ← Solo agregar este decorator
def create_rfx():
    # g.organization_id ya está disponible
    rfx_data = request.get_json()
    rfx_data['organization_id'] = g.organization_id
    rfx_data['user_id'] = g.current_user['id']
    
    # Resto del código igual...
```

**💡 Decisión KISS:**
- ✅ Solo agregar decorator `@require_organization`
- ✅ Inyectar `organization_id` en los datos
- ✅ Código existente sigue funcionando

---

## 🚀 PLAN DE MIGRACIÓN INCREMENTAL

### Fase 1: Preparación (1 día)
```sql
-- 1. Crear tabla organizations
-- 2. Agregar columnas organization_id a users y rfx_v2
-- 3. Crear índices
```

### Fase 2: Migración de Datos (1 día)
```sql
-- 1. Crear organización por cada usuario existente
INSERT INTO organizations (name, slug, plan_tier)
SELECT 
    COALESCE(company_name, full_name || '''s Organization'),
    LOWER(REGEXP_REPLACE(email, '@.*', '', 'g')),
    'free'
FROM users;

-- 2. Asignar usuarios a sus organizaciones
UPDATE users u
SET organization_id = o.id,
    role = 'owner'
FROM organizations o
WHERE o.slug = LOWER(REGEXP_REPLACE(u.email, '@.*', '', 'g'));

-- 3. Asignar RFX a organizaciones
UPDATE rfx_v2 r
SET organization_id = u.organization_id
FROM users u
WHERE r.user_id = u.id;
```

### Fase 3: Backend (2 días)
```
1. Crear organization_middleware.py
2. Modificar DatabaseClient (agregar métodos helper)
3. Actualizar endpoints críticos (rfx, branding)
4. Testing
```

### Fase 4: Validación (1 día)
```
1. Probar aislamiento de datos
2. Verificar que usuarios solo ven sus RFX
3. Testing de roles (owner vs member)
```

---

## 📊 COMPARACIÓN: ANTES vs DESPUÉS

### ANTES (Single-Tenant)
```
Usuario A → RFX de Usuario A (filtrado por user_id)
Usuario B → RFX de Usuario B (filtrado por user_id)
```

### DESPUÉS (Multi-Tenant KISS)
```
Organización 1:
  ├─ Usuario A (owner) → Todos los RFX de Org 1
  └─ Usuario B (member) → Todos los RFX de Org 1

Organización 2:
  └─ Usuario C (owner) → Todos los RFX de Org 2
```

**Cambio clave:** Filtrar por `organization_id` en lugar de solo `user_id`

---

## 🎯 LÍMITES Y VALIDACIÓN KISS

### Validación Simple en Endpoints

```python
def check_organization_limits(org_id: str, action: str):
    """Validar límites del plan (SIMPLE)"""
    
    # Obtener organización
    org = db.client.table("organizations").select("*").eq("id", org_id).single().execute()
    
    if action == "create_rfx":
        # Contar RFX del mes actual
        count = db.client.table("rfx_v2")\
            .select("id", count="exact")\
            .eq("organization_id", org_id)\
            .gte("created_at", "2025-12-01")\
            .execute()
        
        if count.count >= org.data['max_rfx_per_month']:
            raise Exception(f"Monthly limit reached ({org.data['max_rfx_per_month']} RFX)")
    
    elif action == "invite_user":
        # Contar usuarios
        count = db.client.table("users")\
            .select("id", count="exact")\
            .eq("organization_id", org_id)\
            .execute()
        
        if count.count >= org.data['max_users']:
            raise Exception(f"User limit reached ({org.data['max_users']} users)")
```

**💡 Decisión KISS:**
- ✅ Validación simple antes de crear recursos
- ❌ NO crear sistema complejo de quotas
- ✅ Solo validar lo esencial: RFX/mes y usuarios

---

## 💰 PLANES HARDCODEADOS (NO DB)

```python
# backend/core/plans.py

PLANS = {
    'free': {
        'name': 'Free',
        'max_users': 2,
        'max_rfx_per_month': 10,
        'features': ['ai_chat', 'basic_branding']
    },
    'pro': {
        'name': 'Professional',
        'max_users': 10,
        'max_rfx_per_month': 100,
        'features': ['ai_chat', 'custom_branding', 'analytics']
    },
    'enterprise': {
        'name': 'Enterprise',
        'max_users': 999,
        'max_rfx_per_month': 999,
        'features': ['ai_chat', 'custom_branding', 'analytics', 'api_access', 'priority_support']
    }
}

def get_plan_limits(plan_tier: str):
    return PLANS.get(plan_tier, PLANS['free'])
```

**💡 Decisión KISS:**
- ✅ Planes hardcodeados en código
- ❌ NO crear tabla `subscription_plans` (overkill)
- ✅ Más fácil de modificar y deployar

---

## 🔒 ROW-LEVEL SECURITY (RLS) - OPCIONAL

```sql
-- Solo si usamos Supabase RLS (opcional para MVP)
ALTER TABLE rfx_v2 ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only see their organization's RFX"
  ON rfx_v2
  FOR SELECT
  USING (organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  ));
```

**💡 Decisión KISS:**
- ⚠️ RLS es OPCIONAL para MVP
- ✅ Podemos confiar en filtros de backend primero
- ✅ Agregar RLS después si es necesario

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Base de Datos
- [ ] Crear tabla `organizations` (simple)
- [ ] Agregar `organization_id` a `users`
- [ ] Agregar `organization_id` a `rfx_v2`
- [ ] Crear índices necesarios
- [ ] Migrar datos existentes

### Backend
- [ ] Crear `organization_middleware.py` (simple)
- [ ] Agregar helpers a `DatabaseClient`
- [ ] Actualizar endpoints de RFX
- [ ] Actualizar endpoints de branding
- [ ] Agregar validación de límites

### Testing
- [ ] Probar aislamiento de datos
- [ ] Verificar límites de plan
- [ ] Testing de roles (owner/member)
- [ ] Verificar migración de datos

---

## 🎯 PRÓXIMOS PASOS INMEDIATOS

1. **Revisar y aprobar este análisis** ✋
2. **Crear script de migración SQL**
3. **Implementar middleware simple**
4. **Actualizar endpoints críticos**
5. **Testing completo**

---

## 💡 PRINCIPIOS KISS APLICADOS

✅ **Reutilizar lo que existe** - 80% del trabajo ya está hecho  
✅ **No sobre-ingenierizar** - Solo 3 planes, no tabla separada  
✅ **Migración incremental** - Paso a paso, sin romper nada  
✅ **Código simple** - Middleware de 20 líneas, no servicio complejo  
✅ **Validación simple** - Solo contar y comparar, sin sistema de quotas  
✅ **Hardcodear cuando tiene sentido** - Planes en código, no en DB  

---

**Última actualización:** 5 de Diciembre, 2025  
**Status:** ✅ ANÁLISIS COMPLETO - LISTO PARA REVISIÓN
