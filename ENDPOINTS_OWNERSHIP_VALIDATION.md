# 🔒 ENDPOINTS QUE REQUIEREN VALIDACIÓN DE OWNERSHIP

**Fecha:** 16 de Diciembre, 2025  
**Propósito:** Lista completa de endpoints que necesitan validación de ownership de RFX

---

## ✅ ENDPOINTS YA CORREGIDOS

### **1. RFX Chat (`backend/api/rfx_chat.py`)**
- ✅ `POST /api/rfx/<rfx_id>/chat` - Enviar mensaje al chat
- ✅ Validación de ownership implementada
- ✅ Créditos contextuales (org vs personal)

### **2. Proposals (`backend/api/proposals.py`)**
- ✅ `POST /api/proposals/generate` - Generar propuesta
- ✅ Validación de ownership implementada
- ✅ Créditos contextuales (org vs personal)

---

## ⏳ ENDPOINTS PENDIENTES DE CORRECCIÓN

### **Archivo: `backend/api/rfx.py`**

#### **Endpoints Críticos (Acceso Individual a RFX):**

1. **`GET /api/rfx/<rfx_id>`** - Obtener RFX por ID
   - **Prioridad:** CRÍTICA
   - **Acción:** Validar ownership antes de retornar datos
   - **Línea:** ~528

2. **`POST /api/rfx/<rfx_id>/finalize`** - Finalizar RFX
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de cambiar estado
   - **Línea:** ~490

3. **`GET /api/rfx/<rfx_id>/products`** - Obtener productos del RFX
   - **Prioridad:** CRÍTICA
   - **Acción:** Validar ownership antes de retornar productos
   - **Línea:** ~665

4. **`PUT /api/rfx/<rfx_id>/currency`** - Actualizar moneda del RFX
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de actualizar
   - **Línea:** ~779

5. **`PUT /api/rfx/<rfx_id>/data`** - Actualizar datos del RFX
   - **Prioridad:** CRÍTICA
   - **Acción:** Validar ownership antes de actualizar
   - **Línea:** ~918

6. **`PUT /api/rfx/<rfx_id>/products/costs`** - Actualizar costos de productos
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de actualizar
   - **Línea:** ~1151

7. **`POST /api/rfx/<rfx_id>/products`** - Crear producto en RFX
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de crear
   - **Línea:** ~1334

8. **`DELETE /api/rfx/<rfx_id>/products/<product_id>`** - Eliminar producto
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de eliminar
   - **Línea:** ~1473

9. **`PUT /api/rfx/<rfx_id>/products/<product_id>`** - Actualizar producto
   - **Prioridad:** ALTA
   - **Acción:** Validar ownership antes de actualizar
   - **Línea:** ~1576

10. **`PATCH /api/rfx/<rfx_id>/title`** - Actualizar título del RFX
    - **Prioridad:** MEDIA
    - **Acción:** Validar ownership antes de actualizar
    - **Línea:** ~1812
    - **Nota:** Ya tiene `@jwt_required`

---

### **Archivo: `backend/api/pricing.py`**

11. **Endpoints de pricing relacionados con RFX**
    - **Acción:** Revisar si hay endpoints que reciban `rfx_id`
    - **Prioridad:** MEDIA

---

### **Archivo: `backend/api/download.py`**

12. **Endpoints de descarga de documentos/propuestas**
    - **Acción:** Revisar si hay endpoints que descarguen datos de RFX
    - **Prioridad:** ALTA

---

### **Archivo: `backend/api/branding.py` / `backend/api/user_branding.py`**

13. **Endpoints de branding relacionados con RFX**
    - **Acción:** Revisar si hay endpoints que usen RFX para branding
    - **Prioridad:** BAJA (branding es por usuario, no por RFX)

---

## 🛠️ ESTRATEGIA DE IMPLEMENTACIÓN

### **Paso 1: Usar Helper Function**
Importar y usar la función helper creada:

```python
from backend.utils.rfx_ownership import get_and_validate_rfx_ownership

@rfx_bp.route("/<rfx_id>", methods=["GET"])
@jwt_required
def get_rfx_by_id(rfx_id: str):
    user_id = get_current_user_id()
    organization_id = get_current_user_organization_id()
    
    from ..core.database import get_database_client
    db = get_database_client()
    
    # Validar ownership en una línea
    rfx, error = get_and_validate_rfx_ownership(db, rfx_id, user_id, organization_id)
    if error:
        return error
    
    # Continuar con lógica normal...
```

### **Paso 2: Orden de Prioridad**
1. **CRÍTICOS:** Endpoints de lectura/escritura de datos sensibles
2. **ALTOS:** Endpoints de modificación de datos
3. **MEDIOS:** Endpoints de operaciones secundarias
4. **BAJOS:** Endpoints que no exponen datos sensibles

### **Paso 3: Testing**
Después de cada corrección, verificar:
- ✅ Usuario personal puede acceder a sus RFX
- ✅ Usuario personal NO puede acceder a RFX de otros
- ✅ Usuario organizacional puede acceder a RFX de su org
- ✅ Usuario organizacional NO puede acceder a RFX de otras orgs
- ✅ Usuario organizacional NO puede acceder a RFX personales

---

## 📊 PROGRESO

**Total Endpoints:** ~15  
**Corregidos:** 2 (13%)  
**Pendientes:** 13 (87%)  

---

## 🚨 ENDPOINTS MÁS CRÍTICOS (PRIORIDAD INMEDIATA)

1. ✅ `POST /api/rfx/<rfx_id>/chat` - **CORREGIDO**
2. ✅ `POST /api/proposals/generate` - **CORREGIDO**
3. ⏳ `GET /api/rfx/<rfx_id>` - **PENDIENTE**
4. ⏳ `PUT /api/rfx/<rfx_id>/data` - **PENDIENTE**
5. ⏳ `GET /api/rfx/<rfx_id>/products` - **PENDIENTE**

---

**Próxima Acción:** Corregir los 3 endpoints más críticos restantes.
