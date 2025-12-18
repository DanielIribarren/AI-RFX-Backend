# 🔒 IMPLEMENTACIÓN DE AISLAMIENTO DE DATOS RFX

**Fecha:** 16 de Diciembre, 2025  
**Objetivo:** Implementar aislamiento completo de datos RFX por usuario/organización  
**Estrategia:** Opción B - RFX existentes quedan como personales

---

## ✅ FASES COMPLETADAS

### **FASE 1: Autenticación en Endpoints ✅**

**Archivos Modificados:**
- `backend/api/rfx.py`

**Cambios Realizados:**
```python
# Endpoint /history
@rfx_bp.route("/history", methods=["GET"])
@jwt_required  # ← AGREGADO
def get_rfx_history():
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()
    # ... resto del código

# Endpoint /recent
@rfx_bp.route("/recent", methods=["GET"])
@jwt_required  # ← AGREGADO
def get_recent_rfx():
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()
    # ... resto del código
```

**Resultado:** Endpoints ahora requieren autenticación JWT. ✅

---

### **FASE 2: Filtros de Seguridad en DatabaseClient ✅**

**Archivos Modificados:**
- `backend/core/database.py`

**Cambios Realizados:**

#### **Método `get_rfx_history()` actualizado:**
```python
def get_rfx_history(
    self, 
    user_id: str,
    organization_id: Optional[str] = None,
    limit: int = 50, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    🔒 SEGURIDAD: Implementa aislamiento de datos
    
    Lógica:
    - Si organization_id != NULL → WHERE organization_id = org_id
    - Si organization_id = NULL → WHERE user_id = user_id AND organization_id IS NULL
    """
    query = self.client.table("rfx_v2").select("*, companies(*), requesters(*)")
    
    if organization_id:
        # Usuario organizacional - ver RFX de toda la org
        query = query.eq("organization_id", organization_id)
    else:
        # Usuario personal - ver SOLO sus RFX personales
        query = query.eq("user_id", user_id).is_("organization_id", "null")
    
    response = query.order("received_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    return response.data or []
```

#### **Método `get_latest_rfx()` actualizado:**
```python
def get_latest_rfx(
    self,
    user_id: str,
    organization_id: Optional[str] = None,
    limit: int = 10, 
    offset: int = 0
) -> List[Dict[str, Any]]:
    """🔒 SEGURIDAD: Implementa aislamiento de datos"""
    query = self.client.table("rfx_v2").select("*, companies(*), requesters(*)")
    
    if organization_id:
        query = query.eq("organization_id", organization_id)
    else:
        query = query.eq("user_id", user_id).is_("organization_id", "null")
    
    # ... resto del código
```

**Resultado:** Queries ahora filtran por usuario/organización automáticamente. ✅

---

### **FASE 3: Actualización de Endpoints ✅**

**Archivos Modificados:**
- `backend/api/rfx.py`

**Cambios Realizados:**

#### **Endpoint `/history` actualizado:**
```python
@rfx_bp.route("/history", methods=["GET"])
@jwt_required
def get_rfx_history():
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()
    
    # Llamada con filtros de seguridad
    rfx_records = db_client.get_rfx_history(
        user_id=user_id,
        organization_id=organization_id,
        limit=limit,
        offset=offset
    )
```

#### **Endpoint `/recent` actualizado:**
```python
@rfx_bp.route("/recent", methods=["GET"])
@jwt_required
def get_recent_rfx():
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()
    
    # Llamada con filtros de seguridad
    rfx_records = db_client.get_rfx_history(
        user_id=user_id,
        organization_id=organization_id,
        limit=12,
        offset=0
    )
```

**Resultado:** Endpoints pasan contexto de seguridad a DatabaseClient. ✅

---

## 🚧 FASES PENDIENTES

### **FASE 4: Actualizar Creación de RFX** ⏳

**Objetivo:** Asegurar que al crear un RFX se guarde correctamente `organization_id`.

**Archivos a Modificar:**
- `backend/services/rfx_processor.py` (o donde se guarde el RFX)
- `backend/api/rfx.py` (endpoint `/process`)

**Implementación Requerida:**

```python
# En el endpoint /process
@rfx_bp.route("/process", methods=["POST"])
@jwt_required
def process_rfx():
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()  # Puede ser None
    
    # Pasar organization_id al servicio de procesamiento
    processor = RFXProcessorService()
    result = processor.process(
        files=files,
        user_id=user_id,
        organization_id=organization_id  # ← CRÍTICO
    )
```

**En el servicio de procesamiento:**
```python
# backend/services/rfx_processor.py
def save_rfx_to_database(self, rfx_data: dict, user_id: str, organization_id: Optional[str]):
    """Guardar RFX con aislamiento correcto"""
    rfx_record = {
        "user_id": user_id,  # Siempre presente
        "organization_id": organization_id,  # NULL si usuario personal
        # ... otros campos
    }
    
    response = self.db.client.table("rfx_v2").insert(rfx_record).execute()
    return response.data[0] if response.data else None
```

**Verificación:**
- ✅ Usuario personal crea RFX → `organization_id = NULL`
- ✅ Usuario organizacional crea RFX → `organization_id = org_id`

---

### **FASE 5: Validación de Ownership en GET /{rfx_id}** ⏳

**Objetivo:** Prevenir acceso a RFX de otros usuarios/organizaciones.

**Archivo a Modificar:**
- `backend/api/rfx.py`

**Implementación Requerida:**

```python
@rfx_bp.route("/<rfx_id>", methods=["GET"])
@jwt_required
def get_rfx_by_id(rfx_id: str):
    """
    Get single RFX with ownership validation.
    
    🔒 SEGURIDAD CRÍTICA: Valida que el usuario tenga acceso al RFX
    """
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        
        db_client = get_database_client()
        
        # Obtener RFX
        rfx = db_client.get_rfx_by_id(rfx_id)
        
        if not rfx:
            return jsonify({
                "status": "error",
                "message": "RFX not found"
            }), 404
        
        # 🔒 VALIDACIÓN DE OWNERSHIP
        rfx_org_id = rfx.get("organization_id")
        rfx_user_id = rfx.get("user_id")
        
        # Caso 1: RFX organizacional
        if rfx_org_id:
            if rfx_org_id != organization_id:
                logger.warning(f"🚨 Access denied: User {user_id} tried to access RFX from org {rfx_org_id}")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - RFX belongs to different organization"
                }), 403
        
        # Caso 2: RFX personal
        else:
            # Validar que el RFX pertenece al usuario
            if rfx_user_id != user_id:
                logger.warning(f"🚨 Access denied: User {user_id} tried to access RFX of user {rfx_user_id}")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - RFX belongs to different user"
                }), 403
            
            # Validar que el usuario NO está en una organización
            if organization_id:
                logger.warning(f"🚨 Access denied: User {user_id} in org {organization_id} tried to access personal RFX")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - Personal RFX not accessible while in organization"
                }), 403
        
        # ✅ Acceso permitido
        rfx = db_client.enrich_rfx_with_user_info([rfx])[0]
        
        return jsonify({
            "status": "success",
            "data": rfx
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting RFX: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
```

**Casos de Seguridad Cubiertos:**
1. ✅ Usuario personal NO puede ver RFX de otro usuario personal
2. ✅ Usuario organizacional NO puede ver RFX de otra organización
3. ✅ Usuario organizacional NO puede ver sus RFX personales antiguos
4. ✅ Usuario personal NO puede ver RFX organizacionales

---

### **FASE 6: Testing y Documentación** ⏳

**Crear archivo de tests:**
- `tests/test_rfx_data_isolation.py`

**Tests Requeridos:**

```python
import pytest
from backend.api.rfx import rfx_bp
from backend.core.database import get_database_client

class TestRFXDataIsolation:
    """Tests de seguridad para aislamiento de datos RFX"""
    
    def test_personal_user_cannot_see_org_rfx(self):
        """Usuario personal NO puede ver RFX organizacionales"""
        # 1. Crear RFX en org A
        # 2. Intentar acceder como usuario personal
        # 3. Debe retornar 403
        pass
    
    def test_org_user_cannot_see_other_org_rfx(self):
        """Usuario de Org A NO puede ver RFX de Org B"""
        # 1. Crear RFX en org A
        # 2. Intentar acceder como usuario de org B
        # 3. Debe retornar 403
        pass
    
    def test_org_user_cannot_see_personal_rfx(self):
        """Usuario organizacional NO puede ver sus RFX personales antiguos"""
        # 1. Usuario crea RFX personal
        # 2. Usuario se une a org
        # 3. Intentar acceder a RFX personal antiguo
        # 4. Debe retornar 403
        pass
    
    def test_user_sees_personal_rfx_after_leaving_org(self):
        """Usuario ve sus RFX personales después de salir de org"""
        # 1. Usuario crea RFX personal
        # 2. Usuario se une a org
        # 3. Usuario sale de org
        # 4. Debe ver RFX personales antiguos
        pass
    
    def test_org_members_see_same_rfx(self):
        """Miembros de la misma org ven los mismos RFX"""
        # 1. Usuario A crea RFX en org
        # 2. Usuario B (mismo org) busca historial
        # 3. Debe ver el RFX de usuario A
        pass
    
    def test_personal_user_only_sees_own_rfx(self):
        """Usuario personal solo ve sus propios RFX"""
        # 1. Usuario A crea RFX personal
        # 2. Usuario B (personal) busca historial
        # 3. NO debe ver RFX de usuario A
        pass
```

---

## 📊 MATRIZ DE CASOS DE USO

| Escenario | Usuario | RFX | Resultado Esperado |
|-----------|---------|-----|-------------------|
| 1 | Personal | Propio personal | ✅ Puede ver |
| 2 | Personal | Otro usuario personal | ❌ 403 Forbidden |
| 3 | Personal | Organizacional | ❌ 403 Forbidden |
| 4 | Org A | Propio en Org A | ✅ Puede ver |
| 5 | Org A | Otro miembro Org A | ✅ Puede ver |
| 6 | Org A | Org B | ❌ 403 Forbidden |
| 7 | Org A | Propio personal antiguo | ❌ 403 Forbidden |
| 8 | Ex-Org A (ahora personal) | Propio personal antiguo | ✅ Puede ver |
| 9 | Ex-Org A (ahora personal) | RFX de Org A | ❌ 403 Forbidden |

---

## 🔍 VERIFICACIÓN DE IMPLEMENTACIÓN

### **Checklist de Seguridad:**

- [x] **Autenticación:** Todos los endpoints requieren `@jwt_required`
- [x] **Filtros de DB:** Queries filtran por `user_id` o `organization_id`
- [x] **Contexto de Usuario:** Endpoints obtienen `user_id` y `organization_id` del JWT
- [ ] **Creación de RFX:** Se guarda `organization_id` correctamente
- [ ] **Validación de Ownership:** GET /{rfx_id} valida acceso
- [ ] **Tests de Seguridad:** Tests automatizados implementados
- [ ] **Documentación:** Guía de uso para frontend

---

## 🚀 PRÓXIMOS PASOS

### **Paso 1: Completar FASE 4**
Buscar dónde se guarda el RFX en el procesamiento y asegurar que se pase `organization_id`.

**Archivos a revisar:**
- `backend/services/rfx_processor.py`
- `backend/api/rfx.py` (endpoint `/process`)

### **Paso 2: Implementar FASE 5**
Agregar validación de ownership en GET /{rfx_id}.

### **Paso 3: Testing**
Crear tests automatizados para validar todos los casos de seguridad.

### **Paso 4: Documentación para Frontend**
Crear guía de cómo el frontend debe manejar los diferentes contextos (personal vs organizacional).

---

## 📝 NOTAS IMPORTANTES

### **Decisión: Opción B - RFX Existentes como Personales**

**Ventajas:**
- ✅ Separación clara de datos
- ✅ No mezcla datos históricos
- ✅ Más seguro
- ✅ Comportamiento predecible

**Implicaciones:**
- RFX existentes sin `organization_id` quedan como personales
- Usuarios en organizaciones NO verán estos RFX antiguos
- Al salir de la organización, usuarios recuperan acceso a RFX personales

### **Comportamiento de Transición:**

```
Usuario crea 5 RFX personales (organization_id = NULL)
  ↓
Usuario se une a Organización A
  ↓
Historial muestra: 0 RFX (organización nueva)
RFX personales: OCULTOS (pero NO eliminados)
  ↓
Usuario crea 3 RFX en Org A (organization_id = org_a_id)
  ↓
Historial muestra: 3 RFX (solo de Org A)
  ↓
Usuario sale de Org A
  ↓
Historial muestra: 5 RFX (sus RFX personales originales)
RFX de Org A: OCULTOS (ya no pertenece)
```

---

## 🔒 POLÍTICA DE SEGURIDAD

### **Principios:**
1. **Aislamiento Total:** Datos de diferentes contextos NUNCA se mezclan
2. **Visibilidad Contextual:** Solo ves datos del contexto actual
3. **Preservación de Datos:** Datos nunca se eliminan, solo cambia visibilidad
4. **Colaboración Organizacional:** Miembros de org ven datos compartidos
5. **Privacidad Personal:** RFX personales son privados del usuario

### **Reglas de Acceso:**
- Usuario personal → Ve SOLO sus RFX personales
- Usuario organizacional → Ve TODOS los RFX de la organización
- Cambio de contexto → Cambia visibilidad, NO elimina datos

---

## ✅ ESTADO ACTUAL

**Completado:**
- ✅ FASE 1: Autenticación en endpoints
- ✅ FASE 2: Filtros de seguridad en DatabaseClient
- ✅ FASE 3: Actualización de endpoints de búsqueda

**Pendiente:**
- ⏳ FASE 4: Actualizar creación de RFX
- ⏳ FASE 5: Validación de ownership
- ⏳ FASE 6: Testing y documentación

**Progreso:** 50% completado

---

**Última Actualización:** 16 de Diciembre, 2025  
**Próxima Acción:** Implementar FASE 4 - Actualizar creación de RFX
