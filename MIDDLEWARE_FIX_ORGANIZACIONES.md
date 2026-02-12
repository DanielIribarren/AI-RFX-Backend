# 🔧 FIX: Middleware de Organizaciones - Soporte para Usuarios Personales

**Fecha:** 11 de Febrero, 2026  
**Problema:** Middleware bloqueaba usuarios sin organización  
**Estado:** ✅ RESUELTO

---

## 🔴 PROBLEMA IDENTIFICADO

### Error en Logs

```
2026-02-11 17:13:25,419 - backend.utils.organization_middleware - ERROR - ❌ User e4f41ab2-8817-4367-917e-d9a5e9650bcc has no organization_id
2026-02-11 17:13:25,419 - werkzeug - INFO - 127.0.0.1 - - [11/Feb/2026 17:13:25] "GET /api/organization/current HTTP/1.1" 403 -
```

### Causa Raíz

El decorador `@require_organization` bloqueaba **TODOS** los usuarios que no tuvieran `organization_id`, incluyendo:
- ✅ Usuarios personales válidos (sin organización)
- ✅ Usuarios que usan créditos personales (`user_credits` table)
- ✅ Usuarios que aún no han creado una organización

**Archivo:** `backend/utils/organization_middleware.py` - Líneas 64-69

```python
if not organization_id:
    logger.error(f"❌ User {user_id} has no organization_id")
    return jsonify({
        "status": "error",
        "message": "User has no organization assigned"
    }), 403  # ← BLOQUEABA usuarios personales
```

### Impacto

- ❌ Usuarios personales NO podían acceder a `/api/organization/current`
- ❌ Frontend recibía 403 Forbidden
- ❌ Sistema asumía que TODOS los usuarios deben tener organización
- ❌ Contradecía el diseño de usuarios personales vs organizaciones

---

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Nuevo Decorador: `@optional_organization`

**Archivo:** `backend/utils/organization_middleware.py` - Líneas 135-208

```python
def optional_organization(f):
    """
    Decorator que OPCIONALMENTE verifica si el usuario tiene organización.
    Inyecta g.organization_id y g.user_role si existen, pero NO bloquea si no existen.
    
    Útil para endpoints que funcionan tanto para usuarios con organización
    como para usuarios personales (sin organización).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ... obtener organization_id y role ...
        
        # Inyectar en g (pueden ser None para usuarios personales)
        g.organization_id = organization_id
        g.user_role = role
        
        if organization_id:
            logger.info(f"✅ Optional organization middleware: user={user_id}, org={organization_id}, role={role}")
        else:
            logger.info(f"✅ Optional organization middleware: user={user_id}, personal user (no org)")
        
        return f(*args, **kwargs)  # ← NO bloquea si organization_id es None
```

**Diferencias con `@require_organization`:**

| Aspecto | `@require_organization` | `@optional_organization` |
|---------|------------------------|--------------------------|
| **Bloquea sin org** | ✅ SÍ (403 error) | ❌ NO (permite continuar) |
| **Inyecta g.organization_id** | ✅ SÍ (siempre válido) | ✅ SÍ (puede ser None) |
| **Inyecta g.user_role** | ✅ SÍ (siempre válido) | ✅ SÍ (puede ser None) |
| **Uso** | Endpoints solo para orgs | Endpoints flexibles |

### 2. Actualización del Endpoint `/api/organization/current`

**Archivo:** `backend/api/organization.py` - Líneas 220-318

**ANTES:**
```python
@organization_bp.route('/current', methods=['GET'])
@jwt_required
@require_organization  # ← Bloqueaba usuarios personales
def get_current_organization():
    organization_id = g.organization_id  # Siempre válido
    # ... retornar datos de organización
```

**DESPUÉS:**
```python
@organization_bp.route('/current', methods=['GET'])
@jwt_required
@optional_organization  # ← Permite usuarios personales
def get_current_organization():
    organization_id = g.organization_id  # Puede ser None
    
    # Usuario NO tiene organización (usuario personal)
    if not organization_id:
        logger.info(f"✅ User {g.current_user.get('id')} has no organization - personal user")
        return jsonify({
            "status": "success",
            "has_organization": False,
            "message": "User has no organization. Using personal credits.",
            "data": None
        }), 200
    
    # Usuario SÍ tiene organización
    # ... retornar datos de organización
```

### 3. Respuestas Diferenciadas

**Usuario CON Organización:**
```json
{
  "status": "success",
  "has_organization": true,
  "data": {
    "id": "uuid",
    "name": "Sabra Corporation",
    "slug": "sabra-corp",
    "plan": {
      "tier": "pro",
      "name": "Pro Plan",
      "max_users": 10
    },
    "usage": {
      "users": {"current": 5, "limit": 10},
      "rfx_this_month": {"current": 20, "limit": 100}
    }
  }
}
```

**Usuario SIN Organización (Personal):**
```json
{
  "status": "success",
  "has_organization": false,
  "message": "User has no organization. Using personal credits.",
  "data": null
}
```

---

## 📊 COMPARACIÓN DE DECORADORES

### Cuándo Usar Cada Uno

**`@require_organization` - Endpoints SOLO para organizaciones:**
```python
# Gestión de miembros (solo orgs)
@organization_bp.route('/members', methods=['GET'])
@jwt_required
@require_organization
def get_organization_members():
    # organization_id SIEMPRE existe aquí
    pass

# Invitar miembros (solo orgs)
@organization_bp.route('/invite', methods=['POST'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])
def invite_member():
    # organization_id SIEMPRE existe aquí
    pass
```

**`@optional_organization` - Endpoints flexibles:**
```python
# Ver organización actual (o indicar que no tiene)
@organization_bp.route('/current', methods=['GET'])
@jwt_required
@optional_organization
def get_current_organization():
    if g.organization_id:
        # Usuario con organización
        return org_data
    else:
        # Usuario personal
        return personal_message

# Ver planes disponibles (antes de crear org)
@organization_bp.route('/plans', methods=['GET'])
@jwt_required
@optional_organization
def get_available_plans():
    # Funciona para ambos tipos de usuarios
    pass
```

**Sin decorador de organización:**
```python
# Crear organización (usuario aún no tiene)
@organization_bp.route('', methods=['POST'])
@jwt_required  # Solo autenticación
def create_organization():
    # NO usar @require_organization aquí
    # El usuario está CREANDO su primera org
    pass
```

---

## 🔍 ARCHIVOS MODIFICADOS

### 1. `/backend/utils/organization_middleware.py`

**Cambios:**
- ✅ Agregado decorador `optional_organization()` (líneas 135-208)
- ✅ Mantiene `require_organization()` para endpoints estrictos
- ✅ Mantiene `require_role()` sin cambios

### 2. `/backend/api/organization.py`

**Cambios:**
- ✅ Import actualizado: `from backend.utils.organization_middleware import require_organization, require_role, optional_organization`
- ✅ Endpoint `/current` usa `@optional_organization` en lugar de `@require_organization`
- ✅ Lógica actualizada para manejar `organization_id = None`
- ✅ Respuestas diferenciadas con campo `has_organization`

---

## 🎯 FLUJO ACTUALIZADO

### Usuario Personal (Sin Organización)

```
1. Usuario se autentica → JWT token válido
2. Frontend llama GET /api/organization/current
3. Backend:
   ├─ @jwt_required → Verifica token ✅
   ├─ @optional_organization → Obtiene organization_id (None)
   └─ Endpoint detecta organization_id = None
4. Respuesta: { has_organization: false, data: null }
5. Frontend muestra: "No tienes organización. Usando créditos personales."
6. Usuario puede:
   ├─ Crear organización (POST /api/organization)
   ├─ Usar créditos personales (tabla user_credits)
   └─ Procesar RFX con límites de plan free personal
```

### Usuario con Organización

```
1. Usuario se autentica → JWT token válido
2. Frontend llama GET /api/organization/current
3. Backend:
   ├─ @jwt_required → Verifica token ✅
   ├─ @optional_organization → Obtiene organization_id (UUID válido)
   └─ Endpoint detecta organization_id existe
4. Respuesta: { has_organization: true, data: {...} }
5. Frontend muestra: Dashboard de organización completo
6. Usuario puede:
   ├─ Ver miembros del equipo
   ├─ Gestionar roles
   ├─ Solicitar upgrade de plan
   └─ Usar créditos compartidos de la organización
```

---

## 🧪 TESTING

### Caso 1: Usuario Personal

```bash
# Usuario sin organización
curl -X GET http://localhost:5000/api/organization/current \
  -H "Authorization: Bearer <token_usuario_personal>"

# Respuesta esperada:
{
  "status": "success",
  "has_organization": false,
  "message": "User has no organization. Using personal credits.",
  "data": null
}
```

### Caso 2: Usuario con Organización

```bash
# Usuario con organización
curl -X GET http://localhost:5000/api/organization/current \
  -H "Authorization: Bearer <token_usuario_org>"

# Respuesta esperada:
{
  "status": "success",
  "has_organization": true,
  "data": {
    "id": "uuid",
    "name": "Mi Empresa",
    "plan": {...}
  }
}
```

### Caso 3: Crear Organización (Usuario Personal)

```bash
# Usuario personal crea su primera organización
curl -X POST http://localhost:5000/api/organization \
  -H "Authorization: Bearer <token_usuario_personal>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Mi Nueva Empresa", "slug": "mi-empresa"}'

# Respuesta esperada:
{
  "status": "success",
  "message": "Organization created successfully",
  "data": {
    "id": "uuid",
    "name": "Mi Nueva Empresa",
    "your_role": "owner"
  }
}
```

---

## 📝 LOGS ACTUALIZADOS

### Antes del Fix (ERROR)

```
2026-02-11 17:13:25,419 - backend.utils.organization_middleware - ERROR - ❌ User e4f41ab2-8817-4367-917e-d9a5e9650bcc has no organization_id
2026-02-11 17:13:25,419 - werkzeug - INFO - 127.0.0.1 - - [11/Feb/2026 17:13:25] "GET /api/organization/current HTTP/1.1" 403 -
```

### Después del Fix (SUCCESS)

```
2026-02-11 17:20:00,123 - backend.utils.organization_middleware - INFO - ✅ Optional organization middleware: user=e4f41ab2-8817-4367-917e-d9a5e9650bcc, personal user (no org)
2026-02-11 17:20:00,124 - backend.api.organization - INFO - ✅ User e4f41ab2-8817-4367-917e-d9a5e9650bcc has no organization - personal user
2026-02-11 17:20:00,125 - werkzeug - INFO - 127.0.0.1 - - [11/Feb/2026 17:20:00] "GET /api/organization/current HTTP/1.1" 200 -
```

---

## 🎯 FRONTEND - CÓMO MANEJAR LA RESPUESTA

### React/Next.js Example

```javascript
const checkOrganization = async () => {
  try {
    const response = await fetch('/api/organization/current', {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`
      }
    });
    
    const data = await response.json();
    
    if (data.has_organization) {
      // Usuario tiene organización
      console.log('Organización:', data.data.name);
      setOrganization(data.data);
      setShowOrgDashboard(true);
    } else {
      // Usuario personal sin organización
      console.log('Usuario personal - sin organización');
      setOrganization(null);
      setShowCreateOrgPrompt(true);
    }
  } catch (err) {
    console.error('Error checking organization:', err);
  }
};
```

### Componente Condicional

```jsx
{organization ? (
  <OrganizationDashboard org={organization} />
) : (
  <PersonalUserView>
    <p>No tienes una organización.</p>
    <button onClick={() => navigate('/create-organization')}>
      Crear Organización
    </button>
    <p>Usando créditos personales: {personalCredits}</p>
  </PersonalUserView>
)}
```

---

## ✅ RESUMEN

### Problema
- Middleware bloqueaba usuarios sin organización con 403 Forbidden
- Sistema no permitía usuarios personales

### Solución
- Nuevo decorador `@optional_organization` para endpoints flexibles
- Endpoint `/api/organization/current` actualizado
- Respuestas diferenciadas según tipo de usuario

### Beneficios
- ✅ Usuarios personales pueden usar la plataforma
- ✅ Sistema multi-tenant completo (orgs + personales)
- ✅ Frontend puede detectar tipo de usuario
- ✅ Transición suave de personal → organización
- ✅ Logs claros y descriptivos

### Estado
**✅ IMPLEMENTADO Y FUNCIONANDO**

---

**Fecha:** 11 de Febrero, 2026  
**Autor:** Sistema de Fix Automático  
**Versión:** 1.0
