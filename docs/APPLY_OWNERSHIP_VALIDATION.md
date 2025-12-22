# 🔒 APLICACIÓN MASIVA DE VALIDACIÓN DE OWNERSHIP

**Fecha:** 16 de Diciembre, 2025  
**Propósito:** Aplicar validación de ownership a TODOS los endpoints de RFX

---

## 📋 ENDPOINTS A CORREGIR

### **Patrón de Corrección Estándar:**

```python
from backend.utils.rfx_ownership import get_and_validate_rfx_ownership

@rfx_bp.route("/<rfx_id>/...", methods=["..."])
@jwt_required  # ← Agregar si no existe
def endpoint_name(rfx_id: str):
    """Docstring"""
    try:
        # 🔒 PASO 1: Obtener usuario autenticado
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        
        from ..core.database import get_database_client
        from ..utils.rfx_ownership import get_and_validate_rfx_ownership
        
        db_client = get_database_client()
        
        # 🔒 PASO 2: Validar ownership
        rfx, error = get_and_validate_rfx_ownership(
            db_client, rfx_id, user_id, organization_id
        )
        if error:
            return error
        
        # PASO 3: Continuar con lógica normal...
```

---

## ✅ ENDPOINTS CORREGIDOS

1. ✅ `GET /api/rfx/<rfx_id>` - **CORREGIDO**
2. ✅ `POST /api/rfx/<rfx_id>/chat` - **CORREGIDO**
3. ✅ `POST /api/proposals/generate` - **CORREGIDO**

---

## ⏳ ENDPOINTS PENDIENTES (10 restantes)

### **backend/api/rfx.py:**

4. `POST /api/rfx/<rfx_id>/finalize` (línea 490)
5. `GET /api/rfx/<rfx_id>/products` (línea 674)
6. `PUT /api/rfx/<rfx_id>/currency` (línea 788)
7. `PUT /api/rfx/<rfx_id>/data` (línea 927)
8. `PUT /api/rfx/<rfx_id>/products/costs` (línea 1160)
9. `POST /api/rfx/<rfx_id>/products` (línea 1343)
10. `DELETE /api/rfx/<rfx_id>/products/<product_id>` (línea 1482)
11. `PUT /api/rfx/<rfx_id>/products/<product_id>` (línea 1585)
12. `PATCH /api/rfx/<rfx_id>/title` (línea 1821) - Ya tiene @jwt_required
13. Revisar otros archivos (download.py, pricing.py, etc.)

---

## 🎯 ESTRATEGIA DE IMPLEMENTACIÓN

Dado el gran número de endpoints, voy a:

1. **Crear un decorador reutilizable** que combine @jwt_required + validación de ownership
2. **Aplicar el decorador** a todos los endpoints de forma masiva
3. **Verificar** que todos funcionen correctamente

---

## 🔧 DECORADOR REUTILIZABLE

```python
# backend/utils/rfx_decorators.py

from functools import wraps
from flask import jsonify
from backend.auth.jwt_utils import jwt_required, get_current_user_id, get_current_user_organization_id
from backend.utils.rfx_ownership import get_and_validate_rfx_ownership
from backend.core.database import get_database_client

def require_rfx_ownership(f):
    """
    Decorador que combina @jwt_required con validación de ownership de RFX.
    
    El endpoint debe tener un parámetro 'rfx_id' en la ruta.
    
    Usage:
        @rfx_bp.route("/<rfx_id>/data", methods=["PUT"])
        @require_rfx_ownership
        def update_rfx_data(rfx_id: str, rfx: dict):  # ← rfx se inyecta automáticamente
            # rfx ya está validado y disponible
            pass
    """
    @wraps(f)
    @jwt_required
    def decorated_function(*args, **kwargs):
        # Extraer rfx_id de kwargs
        rfx_id = kwargs.get('rfx_id')
        if not rfx_id:
            return jsonify({
                "status": "error",
                "message": "rfx_id is required"
            }), 400
        
        # Obtener usuario autenticado
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        
        # Validar ownership
        db_client = get_database_client()
        rfx, error = get_and_validate_rfx_ownership(
            db_client, rfx_id, user_id, organization_id
        )
        
        if error:
            return error
        
        # Inyectar rfx validado en kwargs
        kwargs['rfx'] = rfx
        kwargs['user_id'] = user_id
        kwargs['organization_id'] = organization_id
        
        return f(*args, **kwargs)
    
    return decorated_function
```

---

## 📝 EJEMPLO DE USO

### **Antes:**
```python
@rfx_bp.route("/<rfx_id>/data", methods=["PUT"])
def update_rfx_data(rfx_id: str):
    try:
        # Sin autenticación
        # Sin validación de ownership
        db_client = get_database_client()
        rfx = db_client.get_rfx_by_id(rfx_id)
        # ... actualizar datos
```

### **Después:**
```python
@rfx_bp.route("/<rfx_id>/data", methods=["PUT"])
@require_rfx_ownership
def update_rfx_data(rfx_id: str, rfx: dict, user_id: str, organization_id: str):
    # rfx ya está validado y disponible
    # user_id y organization_id inyectados automáticamente
    try:
        db_client = get_database_client()
        # ... actualizar datos (rfx ya validado)
```

---

## ✅ BENEFICIOS DEL DECORADOR

1. **DRY:** No repetir código de validación en cada endpoint
2. **Consistencia:** Todos los endpoints usan la misma lógica
3. **Mantenibilidad:** Cambios en una sola ubicación
4. **Legibilidad:** Código más limpio y claro
5. **Seguridad:** Imposible olvidar la validación

---

## 🚀 PLAN DE ACCIÓN

1. ✅ Crear `backend/utils/rfx_decorators.py` con decorador
2. ⏳ Aplicar decorador a los 10 endpoints pendientes
3. ⏳ Verificar funcionamiento con tests
4. ⏳ Documentar cambios

---

**Estado:** Listo para implementar decorador y aplicar masivamente.
