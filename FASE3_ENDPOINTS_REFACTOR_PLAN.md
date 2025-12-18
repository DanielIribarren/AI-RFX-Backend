# 📋 FASE 3 - Plan de Refactorización de Endpoints Multi-Tenant

**Fecha:** 5 de Diciembre, 2025  
**Objetivo:** Actualizar endpoints y tools existentes para usar multi-tenancy  
**Principio:** KISS - Cambios mínimos, máximo impacto

---

## 🎯 Objetivos de la Fase 3

1. ✅ Agregar `@require_organization` a endpoints críticos
2. ✅ Filtrar queries por `organization_id`
3. ✅ Validar límites antes de crear recursos
4. ✅ Actualizar tools del chat agent
5. ✅ Mantener backward compatibility donde sea posible

---

## 📊 Inventario de Endpoints a Actualizar

### 🔴 CRÍTICOS (Prioridad 1)

#### 1. `/api/rfx/*` - RFX Management
**Archivo:** `backend/api/rfx.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `POST /api/rfx/process` | POST | ✅ Ya tiene `@jwt_required`, agregar `@require_organization` + validar límite |
| `GET /api/rfx/history` | GET | Agregar `@require_organization` + filtrar por org |
| `GET /api/rfx/{rfx_id}` | GET | Agregar `@require_organization` + validar ownership |
| `GET /api/rfx/latest` | GET | Agregar `@require_organization` + filtrar por org |
| `PUT /api/rfx/{rfx_id}` | PUT | Agregar `@require_organization` + validar ownership |
| `DELETE /api/rfx/{rfx_id}` | DELETE | Agregar `@require_organization` + validar ownership |

**Impacto:** ALTO - Estos son los endpoints más usados

#### 2. `/api/rfx-secure/*` - Secure RFX Endpoints
**Archivo:** `backend/api/rfx_secure_patch.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `GET /api/rfx-secure/history` | GET | Agregar `@require_organization` + filtrar por org |
| `GET /api/rfx-secure/{rfx_id}` | GET | Agregar `@require_organization` + validar ownership |

**Impacto:** ALTO - Versión segura de los endpoints

---

### 🟡 IMPORTANTES (Prioridad 2)

#### 3. `/api/branding/*` - Branding Management
**Archivo:** `backend/api/branding.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `POST /api/branding/upload` | POST | Agregar `@require_organization` |
| `GET /api/branding/{user_id}` | GET | Validar que user pertenece a org |
| `GET /api/branding/files/{user_id}/{file_type}` | GET | Validar ownership |

**Impacto:** MEDIO - Branding debe ser por organización

#### 4. `/api/user-branding/*` - User Branding
**Archivo:** `backend/api/user_branding.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `POST /api/user-branding/upload` | POST | Ya tiene `@jwt_required`, agregar `@require_organization` |
| `GET /api/user-branding/analysis` | GET | Agregar `@require_organization` |

**Impacto:** MEDIO

---

### 🟢 OPCIONALES (Prioridad 3)

#### 5. `/api/proposals/*` - Proposal Generation
**Archivo:** `backend/api/proposals.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `POST /api/proposals/generate/{rfx_id}` | POST | Agregar `@require_organization` + validar RFX ownership |

**Impacto:** BAJO - Solo validar que RFX pertenece a org

#### 6. `/api/pricing/*` - Pricing Configuration
**Archivo:** `backend/api/pricing.py`

| Endpoint | Método | Cambio Requerido |
|----------|--------|------------------|
| `GET /api/pricing/config/{rfx_id}` | GET | Agregar `@require_organization` + validar RFX ownership |
| `PUT /api/pricing/config/{rfx_id}` | PUT | Agregar `@require_organization` + validar RFX ownership |

**Impacto:** BAJO

---

## 🛠️ Tools del Chat Agent a Actualizar

**Ubicación:** `backend/services/tools/`

### Tools que Acceden a RFX

1. **`add_products_tool.py`** ✅
   - Validar que `request_id` pertenece a la organización del usuario
   - Agregar parámetro `organization_id` al contexto

2. **`update_product_tool.py`** ✅
   - Validar ownership del producto
   - Verificar que RFX pertenece a org

3. **`delete_product_tool.py`** ✅
   - Validar ownership del producto
   - Verificar que RFX pertenece a org

4. **`get_request_data_tool.py`** ✅
   - Filtrar por organización
   - Solo retornar RFX de la org del usuario

5. **`modify_request_details_tool.py`** ✅
   - Validar ownership del RFX
   - Verificar que pertenece a org

---

## 📝 Estrategia de Implementación

### Paso 1: Actualizar Endpoints RFX (CRÍTICO)

**Orden de implementación:**

1. **`POST /api/rfx/process`** - Crear RFX
   ```python
   @rfx_bp.route("/process", methods=["POST"])
   @jwt_required
   @require_organization  # ← AGREGAR
   def process_rfx():
       # Validar límite ANTES de procesar
       limit_check = db.check_organization_limit(
           g.organization_id, 
           'rfx_monthly'
       )
       
       if not limit_check['can_proceed']:
           from backend.core.plans import format_limit_error
           return jsonify(
               format_limit_error(
                   limit_check['plan_tier'], 
                   'rfx'
               )
           ), 403
       
       # Inyectar organization_id en rfx_data
       rfx_data['organization_id'] = g.organization_id
       
       # Procesar normalmente
       ...
   ```

2. **`GET /api/rfx/history`** - Listar RFX
   ```python
   @rfx_bp.route("/history", methods=["GET"])
   @jwt_required
   @require_organization  # ← AGREGAR
   def get_rfx_history():
       # Filtrar por organización
       rfx_records = db.client.table("rfx_v2")\
           .select("*")\
           .eq("organization_id", g.organization_id)\  # ← AGREGAR
           .order("created_at", desc=True)\
           .limit(limit)\
           .offset(offset)\
           .execute()
       
       return jsonify(rfx_records.data)
   ```

3. **`GET /api/rfx/{rfx_id}`** - Obtener RFX individual
   ```python
   @rfx_bp.route("/<rfx_id>", methods=["GET"])
   @jwt_required
   @require_organization  # ← AGREGAR
   def get_rfx_by_id(rfx_id):
       # Obtener RFX
       rfx = db.get_rfx_by_id(rfx_id)
       
       # Validar ownership
       if rfx.get('organization_id') != g.organization_id:
           return jsonify({
               "status": "error",
               "message": "RFX not found or access denied"
           }), 404
       
       return jsonify(rfx)
   ```

### Paso 2: Actualizar Tools del Chat Agent

**Patrón común para todas las tools:**

```python
# ANTES
@tool
def add_products_tool(request_id: str, products: List[Dict]) -> Dict:
    db = get_database_client()
    # Insertar productos sin validar organización
    inserted = db.insert_rfx_products(request_id, products)
    ...

# DESPUÉS
@tool
def add_products_tool(
    request_id: str, 
    products: List[Dict],
    organization_id: str = None  # ← AGREGAR (opcional para backward compat)
) -> Dict:
    db = get_database_client()
    
    # Validar que RFX pertenece a la organización
    if organization_id:
        rfx = db.get_rfx_by_id(request_id)
        if rfx.get('organization_id') != organization_id:
            return {
                "status": "error",
                "message": "Access denied: RFX does not belong to your organization"
            }
    
    # Insertar productos
    inserted = db.insert_rfx_products(request_id, products)
    ...
```

### Paso 3: Actualizar Chat Agent para Pasar organization_id

**Archivo:** `backend/api/rfx_chat.py` o donde se invoque el chat agent

```python
# Obtener organization_id del contexto
organization_id = g.organization_id

# Pasar como contexto a las tools
agent_context = {
    "organization_id": organization_id,
    "user_role": g.user_role
}

# Las tools pueden acceder al contexto
response = agent.invoke({
    "input": user_message,
    "context": agent_context
})
```

---

## ✅ Checklist de Implementación

### Endpoints RFX
- [ ] `POST /api/rfx/process` - Agregar middleware + validar límite
- [ ] `GET /api/rfx/history` - Agregar middleware + filtrar por org
- [ ] `GET /api/rfx/{rfx_id}` - Agregar middleware + validar ownership
- [ ] `GET /api/rfx/latest` - Agregar middleware + filtrar por org
- [ ] `PUT /api/rfx/{rfx_id}` - Agregar middleware + validar ownership
- [ ] `DELETE /api/rfx/{rfx_id}` - Agregar middleware + validar ownership

### Endpoints Secure
- [ ] `GET /api/rfx-secure/history` - Agregar middleware + filtrar
- [ ] `GET /api/rfx-secure/{rfx_id}` - Agregar middleware + validar

### Endpoints Branding
- [ ] `POST /api/branding/upload` - Agregar middleware
- [ ] `GET /api/branding/{user_id}` - Validar ownership
- [ ] `POST /api/user-branding/upload` - Agregar middleware

### Tools del Chat
- [ ] `add_products_tool.py` - Agregar validación de org
- [ ] `update_product_tool.py` - Agregar validación de org
- [ ] `delete_product_tool.py` - Agregar validación de org
- [ ] `get_request_data_tool.py` - Filtrar por org
- [ ] `modify_request_details_tool.py` - Validar ownership

### Testing
- [ ] Test: Crear RFX con límite alcanzado (debe fallar)
- [ ] Test: Listar RFX solo muestra de mi org
- [ ] Test: Acceder a RFX de otra org (debe fallar 404)
- [ ] Test: Tools validan ownership correctamente

---

## 🚨 Consideraciones Importantes

### 1. Backward Compatibility

**Problema:** Algunos endpoints pueden ser llamados por código legacy sin JWT.

**Solución:** Mantener endpoints legacy SIN middleware, crear versiones nuevas:

```python
# Legacy (mantener temporalmente)
@rfx_bp.route("/history", methods=["GET"])
def get_rfx_history_legacy():
    # Sin autenticación (INSECURE)
    ...

# Nueva versión segura
@rfx_bp.route("/history/secure", methods=["GET"])
@jwt_required
@require_organization
def get_rfx_history_secure():
    # Con multi-tenancy
    ...
```

### 2. Performance

**Problema:** Agregar filtros de organización puede afectar performance.

**Solución:** Los índices ya están creados en Fase 1:
- `idx_rfx_organization` en `rfx_v2(organization_id)`
- `idx_rfx_org_created` en `rfx_v2(organization_id, created_at DESC)`

### 3. Error Messages

**Problema:** No revelar información de otras organizaciones.

**Solución:** Siempre retornar 404 en lugar de 403:

```python
# ❌ MAL - Revela que el RFX existe
if rfx.organization_id != g.organization_id:
    return jsonify({"error": "Access denied"}), 403

# ✅ BIEN - No revela nada
if rfx.organization_id != g.organization_id:
    return jsonify({"error": "RFX not found"}), 404
```

---

## 📊 Estimación de Tiempo

| Tarea | Tiempo Estimado |
|-------|-----------------|
| Actualizar endpoints RFX (6 endpoints) | 2 horas |
| Actualizar endpoints secure (2 endpoints) | 30 min |
| Actualizar endpoints branding (3 endpoints) | 1 hora |
| Actualizar tools del chat (5 tools) | 1.5 horas |
| Testing manual | 1 hora |
| Documentación | 30 min |
| **TOTAL** | **6.5 horas** |

---

## 🎯 Próximos Pasos Inmediatos

1. **Comenzar con `/api/rfx/process`** (crear RFX)
   - Es el más crítico
   - Necesita validación de límites
   - Afecta monetización directamente

2. **Continuar con `/api/rfx/history`** (listar RFX)
   - Segundo más usado
   - Fácil de implementar (solo filtro)

3. **Luego `/api/rfx/{rfx_id}`** (obtener individual)
   - Necesita validación de ownership
   - Patrón se repite en otros endpoints

---

**¿Listo para comenzar con la implementación?** 🚀

Sugiero empezar por el endpoint más crítico: `POST /api/rfx/process`
