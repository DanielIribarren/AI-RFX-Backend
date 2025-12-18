# ✅ FASE 2 COMPLETADA - Backend Multi-Tenant Core

**Fecha:** 5 de Diciembre, 2025  
**Duración:** ~45 minutos  
**Status:** ✅ COMPLETADO EXITOSAMENTE

---

## 📊 Resumen de Cambios

### ✅ Archivos Creados

1. **`backend/utils/organization_middleware.py`** ✅
   - Decorador `@require_organization`
   - Decorador `@require_role(['owner', 'admin'])`
   - Helper `get_organization_context()`

2. **`backend/core/plans.py`** ✅
   - 3 planes hardcodeados (free, pro, enterprise)
   - Helpers: `get_plan()`, `validate_limit()`, `can_add_user()`, `can_create_rfx()`
   - Función `format_limit_error()` para mensajes amigables

3. **`backend/api/organization.py`** ✅
   - Endpoint `GET /api/organization/current`
   - Endpoint `GET /api/organization/members`
   - Endpoint `GET /api/organization/plans`
   - Endpoint `GET /api/organization/upgrade-info`

### ✅ Archivos Modificados

1. **`backend/core/database.py`** ✅
   - Método `filter_by_organization(query, org_id)`
   - Método `get_organization(org_id)`
   - Método `check_organization_limit(org_id, limit_type)`
   - Método `get_organization_members(org_id)`

2. **`backend/app.py`** ✅
   - Import de `organization_bp`
   - Registro del blueprint

---

## 🎯 Middleware de Organización

### Uso Básico

```python
from backend.utils.organization_middleware import require_organization, require_role

@app.route('/api/rfx')
@jwt_required  # Primero autenticación
@require_organization  # Luego organización
def get_rfx():
    org_id = g.organization_id  # Disponible automáticamente
    role = g.user_role  # Disponible automáticamente
    
    # Filtrar RFX por organización
    rfx = db.client.table("rfx_v2")\
        .select("*")\
        .eq("organization_id", org_id)\
        .execute()
    
    return jsonify(rfx.data)
```

### Restricción por Rol

```python
@app.route('/api/organization/members', methods=['POST'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])  # Solo owners y admins
def add_member():
    # Solo owners y admins pueden agregar miembros
    ...
```

---

## 📋 Planes Hardcodeados

### Configuración de Planes

| Plan | Users | RFX/mes | Precio | Features |
|------|-------|---------|--------|----------|
| **Free** | 2 | 10 | $0 | Básico, email support |
| **Pro** | 10 | 100 | $99 | Branding, analytics, API |
| **Enterprise** | ∞ | ∞ | $499 | White-label, SLA, 24/7 |

### Uso en Código

```python
from backend.core.plans import get_plan, can_create_rfx

# Obtener plan
plan = get_plan('free')
print(plan.max_users)  # 2
print(plan.max_rfx_per_month)  # 10

# Validar límites
if can_create_rfx('free', rfx_this_month=9):
    # Puede crear
    create_rfx()
else:
    # Límite alcanzado
    return error_response("Monthly limit reached")
```

---

## 🔍 Database Helpers

### 1. Filtrar por Organización

```python
from backend.core.database import get_database_client

db = get_database_client()

# Forma 1: Helper directo
query = db.client.table("rfx_v2").select("*")
query = db.filter_by_organization(query, organization_id)
rfx = query.execute()

# Forma 2: Manual (equivalente)
rfx = db.client.table("rfx_v2")\
    .select("*")\
    .eq("organization_id", organization_id)\
    .execute()
```

### 2. Verificar Límites

```python
# Verificar límite de usuarios
result = db.check_organization_limit(org_id, 'users')

if result['can_proceed']:
    # Puede agregar usuario
    add_user()
else:
    # Límite alcanzado
    return jsonify({
        "error": f"User limit reached: {result['current_count']}/{result['limit']}"
    }), 403
```

### 3. Obtener Miembros

```python
members = db.get_organization_members(org_id)

for member in members:
    print(f"{member['email']} - {member['role']}")
```

---

## 🌐 API Endpoints

### 1. GET /api/organization/current

Obtener información de la organización actual.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "name": "Sabra Corporation",
    "slug": "sabra-corp",
    "plan": {
      "tier": "free",
      "name": "Free Plan",
      "max_users": 2,
      "max_rfx_per_month": 10
    },
    "usage": {
      "users": {
        "current": 1,
        "limit": 2,
        "can_add_more": true
      },
      "rfx_this_month": {
        "current": 5,
        "limit": 10,
        "can_create_more": true
      }
    }
  }
}
```

### 2. GET /api/organization/members

Listar miembros de la organización.

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "owner",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### 3. GET /api/organization/plans

Ver todos los planes disponibles.

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "tier": "free",
      "name": "Free Plan",
      "max_users": 2,
      "max_rfx_per_month": 10,
      "price_monthly_usd": 0.0,
      "features": ["Up to 2 users", "10 RFX per month", ...]
    },
    ...
  ]
}
```

### 4. GET /api/organization/upgrade-info

Ver información de upgrade disponible.

**Response:**
```json
{
  "status": "success",
  "data": {
    "current_plan": {...},
    "upgrade_available": true,
    "next_plan": {...},
    "benefits": [
      "Increase users from 2 to 10",
      "Increase RFX from 10 to 100/month",
      "Custom branding",
      "Advanced analytics"
    ]
  }
}
```

---

## 🧪 Testing Manual

### Test 1: Middleware Básico

```bash
# 1. Login para obtener token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# 2. Usar token para obtener organización
curl -X GET http://localhost:5001/api/organization/current \
  -H "Authorization: Bearer <token>"
```

### Test 2: Verificar Límites

```python
# Script de prueba
from backend.core.database import get_database_client
from backend.core.plans import can_create_rfx

db = get_database_client()

# Obtener organización
org = db.get_organization("uuid-de-org")
print(f"Plan: {org['plan_tier']}")

# Verificar límite
result = db.check_organization_limit(org['id'], 'rfx_monthly')
print(f"RFX este mes: {result['current_count']}/{result['limit']}")
```

### Test 3: Roles

```bash
# Como owner (debería funcionar)
curl -X GET http://localhost:5001/api/organization/members \
  -H "Authorization: Bearer <owner_token>"

# Como member (debería funcionar - solo lectura)
curl -X GET http://localhost:5001/api/organization/members \
  -H "Authorization: Bearer <member_token>"
```

---

## 🎯 Próximos Pasos (Fase 3)

### Actualizar Endpoints Existentes

1. **`/api/rfx/*`** - Agregar filtros de organización
   - `@require_organization` en todos los endpoints
   - Filtrar queries por `organization_id`
   - Validar límites antes de crear RFX

2. **`/api/branding/*`** - Aislamiento por organización
   - Branding por organización, no por usuario
   - Validar ownership

3. **`/api/proposals/*`** - Verificar permisos
   - Solo generar propuestas de RFX de la organización

---

## 📝 Notas de Implementación

### Orden de Decoradores (IMPORTANTE)

```python
# ✅ CORRECTO
@app.route('/endpoint')
@jwt_required  # 1. Primero autenticación
@require_organization  # 2. Luego organización
@require_role(['owner'])  # 3. Finalmente rol
def endpoint():
    ...

# ❌ INCORRECTO
@app.route('/endpoint')
@require_organization  # Error: g.user no existe todavía
@jwt_required
def endpoint():
    ...
```

### Variables en `g` (Flask)

Después de `@require_organization`:
- `g.user` - Usuario autenticado (del JWT)
- `g.organization_id` - UUID de la organización
- `g.user_role` - Rol del usuario ('owner', 'admin', 'member')

### Manejo de Errores

```python
# El middleware retorna automáticamente:
# - 401 si no hay autenticación
# - 403 si no tiene organización
# - 403 si no tiene el rol requerido
# - 404 si la organización no existe
```

---

## 🔒 Seguridad

### Validaciones Implementadas

✅ **JWT requerido** - Todos los endpoints protegidos  
✅ **Organization_id validado** - Existe en BD  
✅ **Role verificado** - Permisos correctos  
✅ **Límites respetados** - No puede exceder plan  

### Aislamiento de Datos

```python
# ✅ CORRECTO - Filtra por organización
rfx = db.client.table("rfx_v2")\
    .select("*")\
    .eq("organization_id", g.organization_id)\
    .execute()

# ❌ INCORRECTO - No filtra, puede ver otras orgs
rfx = db.client.table("rfx_v2")\
    .select("*")\
    .execute()
```

---

## 📊 Estructura de Archivos

```
backend/
├── api/
│   └── organization.py          # ✅ NUEVO - Endpoints de org
├── core/
│   ├── database.py              # ✅ MODIFICADO - Helpers
│   └── plans.py                 # ✅ NUEVO - Planes hardcoded
├── utils/
│   └── organization_middleware.py  # ✅ NUEVO - Decoradores
└── app.py                       # ✅ MODIFICADO - Blueprint
```

---

## ✅ Checklist de Completitud

- [x] Middleware de organización creado
- [x] Decoradores `@require_organization` y `@require_role`
- [x] Planes hardcodeados (free, pro, enterprise)
- [x] Helpers en DatabaseClient
- [x] API endpoints de organización
- [x] Blueprint registrado en app.py
- [x] Documentación completa

---

**Última actualización:** 5 de Diciembre, 2025  
**Status:** ✅ FASE 2 COMPLETADA - LISTO PARA FASE 3  
**Tiempo Total:** ~45 minutos  
**Archivos Creados:** 3  
**Archivos Modificados:** 2
