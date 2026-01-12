# 🔧 Fix: Corrección de Mapeos de Campos en Updates

**Fecha:** 12 de Enero, 2026  
**Problema:** Updates de productos y otros campos fallaban por mapeos incorrectos  
**Estado:** ✅ CORREGIDO

---

## 🐛 Problemas Identificados

### 1. **Error en update_rfx_product**
```
❌ Exception in update_rfx_product: cannot access local variable 'get_database_client' 
   where it is not associated with a value
```

**Causa:** Importación duplicada de `get_database_client` en línea 1684  
**Ubicación:** `backend/api/rfx.py:1684-1685`

### 2. **Campo inexistente en mapeo de productos**
```
❌ Campo "total_estimated_cost" no existe en tabla rfx_products
```

**Causa:** Mapeo incluía campo `subtotal → total_estimated_cost` que no existe en la BD  
**Ubicación:** `backend/api/rfx.py:1748`

---

## ✅ Soluciones Implementadas

### Fix 1: Eliminar Importaciones Duplicadas en 3 Endpoints

**Archivo:** `backend/api/rfx.py`

**Problema:** Múltiples endpoints tenían `db_client` creado con `get_and_validate_rfx_ownership`, pero luego reimportaban `get_database_client`, causando `UnboundLocalError`.

#### **1.1 Endpoint: `update_rfx_product` (líneas 1678-1684)**

**ANTES:**
```python
if not field_name:
    return jsonify({
        "status": "error",
        "message": "field name is required"
    }), 400

from ..core.database import get_database_client  # ❌ DUPLICADO
db_client = get_database_client()                # ❌ CONFLICTO

# Verificar que el RFX existe
```

**DESPUÉS:**
```python
if not field_name:
    return jsonify({
        "status": "error",
        "message": "field name is required"
    }), 400

# Verificar que el RFX existe
# (usa db_client ya creado en línea 1657)
```

#### **1.2 Endpoint: `update_rfx_data` (líneas 1003-1007)**

**ANTES:**
```python
if not field_name:
    logger.error(f"❌ DEBUG: Missing field name in request")
    return jsonify({
        "status": "error",
        "message": "field name is required",
        "error": "Missing field name"
    }), 400

from ..core.database import get_database_client  # ❌ DUPLICADO
db_client = get_database_client()                # ❌ CONFLICTO

logger.info(f"🔄 DEBUG: Database client obtained...")
```

**DESPUÉS:**
```python
if not field_name:
    logger.error(f"❌ DEBUG: Missing field name in request")
    return jsonify({
        "status": "error",
        "message": "field name is required",
        "error": "Missing field name"
    }), 400

logger.info(f"🔄 DEBUG: Database client obtained...")
# (usa db_client ya creado en línea 971)
```

#### **1.3 Endpoint: `update_product_costs` (líneas 1238-1239)**

**ANTES:**
```python
if not product_costs or not isinstance(product_costs, list):
    return jsonify({
        "status": "error",
        "message": "product_costs array is required",
        "error": "Invalid product costs data"
    }), 400

from ..core.database import get_database_client  # ❌ DUPLICADO
db_client = get_database_client()                # ❌ CONFLICTO

# Verificar que el RFX existe
```

**DESPUÉS:**
```python
if not product_costs or not isinstance(product_costs, list):
    return jsonify({
        "status": "error",
        "message": "product_costs array is required",
        "error": "Invalid product costs data"
    }), 400

# Verificar que el RFX existe
# (usa db_client ya creado en línea 1214)
```

### Fix 2: Corregir Mapeo de Campos de Productos

**Archivo:** `backend/api/rfx.py`

**ANTES (líneas 1743-1761):**
```python
product_field_mapping = {
    "nombre": "product_name",
    "cantidad": "quantity",
    "unidad": "unit",
    "precio_unitario": "estimated_unit_price",
    "costo_unitario": "unit_cost",
    "subtotal": "total_estimated_cost",  # ❌ NO EXISTE
    "descripcion": "description",
    "notas": "notes",
    
    # Inglés
    "product_name": "product_name",
    "quantity": "quantity", 
    "unit": "unit",
    "estimated_unit_price": "estimated_unit_price",
    "unit_cost": "unit_cost",
    "total_estimated_cost": "total_estimated_cost",  # ❌ NO EXISTE
    "description": "description",
    "notes": "notes"
}
```

**DESPUÉS (líneas 1740-1761):**
```python
# SOLO columnas que existen en rfx_products: 
# created_at, description, estimated_unit_price, id, notes, 
# product_name, quantity, rfx_id, unit, unit_cost

product_field_mapping = {
    "nombre": "product_name",
    "cantidad": "quantity",
    "unidad": "unit",
    "precio_unitario": "estimated_unit_price",
    "costo_unitario": "unit_cost",
    "descripcion": "description",
    "notas": "notes",
    
    # Inglés
    "product_name": "product_name",
    "quantity": "quantity", 
    "unit": "unit",
    "estimated_unit_price": "estimated_unit_price",
    "unit_cost": "unit_cost",
    "description": "description",
    "notes": "notes"
}
```

### Fix 3: Corregir Validación de Tipos

**Archivo:** `backend/api/rfx.py`

**ANTES (línea 1776):**
```python
elif db_field in ["estimated_unit_price", "total_estimated_cost", "unit_cost"]:
    # ❌ Incluye campo que no existe
```

**DESPUÉS (línea 1776):**
```python
elif db_field in ["estimated_unit_price", "unit_cost"]:
    # ✅ Solo campos que existen
```

---

## 📊 Estructura Real de Tablas Verificadas

### rfx_products (10 columnas)
```
✅ created_at
✅ description
✅ estimated_unit_price
✅ id
✅ notes
✅ product_name
✅ quantity
✅ rfx_id
✅ unit
✅ unit_cost
```

### requesters (10 columnas)
```
✅ company_id
✅ created_at
✅ department
✅ email
✅ id
✅ name
✅ notes
✅ phone
✅ position
✅ updated_at
```

### companies (12 columnas)
```
✅ address
✅ created_at
✅ email
✅ id
✅ industry
✅ name
✅ notes
✅ organization_id
✅ phone
✅ team_id
✅ updated_at
✅ user_id
```

### users (21 columnas)
```
✅ company_name
✅ created_at
✅ credits_reset_date
✅ credits_total
✅ credits_used
✅ default_team_id
✅ email
✅ email_verified
✅ email_verified_at
✅ failed_login_attempts
✅ full_name
✅ id
✅ last_login_at
✅ locked_until
✅ organization_id
✅ password_hash
✅ personal_plan_tier
✅ phone
✅ role
✅ status
✅ updated_at
```

### organizations (13 columnas)
```
✅ created_at
✅ credits_reset_date
✅ credits_total
✅ credits_used
✅ id
✅ is_active
✅ max_rfx_per_month
✅ max_users
✅ name
✅ plan_tier
✅ slug
✅ trial_ends_at
✅ updated_at
```

---

## ✅ Mapeos Verificados como Correctos

### Productos (`backend/api/rfx.py:1743-1761`)
```python
✅ "nombre" → "product_name"
✅ "cantidad" → "quantity"
✅ "unidad" → "unit"
✅ "precio_unitario" → "estimated_unit_price"
✅ "costo_unitario" → "unit_cost"
✅ "descripcion" → "description"
✅ "notas" → "notes"
```

### Requesters (`backend/api/rfx.py:1074-1079`)
```python
✅ "solicitante" → "name"
✅ "email" → "email"
✅ "telefonoSolicitante" → "phone"
✅ "cargoSolicitante" → "position"
```

### Companies (`backend/api/rfx.py:1118-1122`)
```python
✅ "nombreEmpresa" → "name"
✅ "emailEmpresa" → "email"
✅ "telefonoEmpresa" → "phone"
```

### RFX V2 (`backend/api/rfx.py:1152-1156`)
```python
✅ "fechaEntrega" → "delivery_date"
✅ "lugarEntrega" → "location"
✅ "requirements" → "requirements"
```

---

## 🧪 Testing

### Endpoints Afectados y Corregidos:

1. **PUT `/api/rfx/{rfx_id}/products/{product_id}`**
   - ✅ Importación duplicada eliminada
   - ✅ Mapeo de campos corregido
   - ✅ Validación de tipos corregida

2. **PATCH `/api/rfx/{rfx_id}/field`**
   - ✅ Mapeos verificados contra estructura real
   - ✅ Todos los campos coinciden con BD

### Campos Actualizables por Tabla:

**rfx_products:**
- ✅ product_name
- ✅ quantity
- ✅ unit
- ✅ estimated_unit_price
- ✅ unit_cost
- ✅ description
- ✅ notes

**requesters:**
- ✅ name
- ✅ email
- ✅ phone
- ✅ position

**companies:**
- ✅ name
- ✅ email
- ✅ phone

**rfx_v2:**
- ✅ delivery_date
- ✅ location
- ✅ requirements

---

## 📝 Archivos Modificados

1. **`backend/api/rfx.py`**
   - Línea 1684-1685: Eliminada importación duplicada
   - Línea 1740-1761: Corregido mapeo de productos
   - Línea 1776: Corregida validación de tipos

---

## 🚀 Resultado

**Estado:** ✅ Todos los updates funcionando correctamente

**Verificado:**
- ✅ Update de productos (precio, costo, cantidad, etc.)
- ✅ Update de requesters (nombre, email, teléfono, cargo)
- ✅ Update de companies (nombre, email, teléfono)
- ✅ Update de RFX (fecha entrega, lugar, requirements)

**Prueba:**
```bash
# Update de costo unitario de producto
curl -X PUT http://localhost:5001/api/rfx/{rfx_id}/products/{product_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"field": "costo_unitario", "value": 150.00}'

# Respuesta esperada:
{
  "status": "success",
  "message": "Product field 'costo_unitario' updated successfully with profit recalculation",
  "data": {
    "rfx_id": "...",
    "product_id": "...",
    "field": "costo_unitario",
    "value": 150.00,
    "profit_metrics": {
      "unit_profit": 50.00,
      "unit_margin": 33.33,
      "total_profit": 500.00
    }
  }
}
```

---

## 📚 Lecciones Aprendidas

1. **Siempre verificar estructura real de BD antes de optimizar**
   - No asumir nombres de columnas
   - Consultar directamente la BD para confirmar

2. **Evitar importaciones duplicadas**
   - Revisar scope de variables
   - Usar instancias ya creadas

3. **Mantener mapeos sincronizados con BD**
   - Documentar estructura de tablas
   - Validar contra esquema real

4. **Testing exhaustivo después de optimizaciones**
   - No solo SELECT, también UPDATE/INSERT/DELETE
   - Verificar todos los endpoints afectados

---

**Documentación:** Este archivo  
**Implementación:** `backend/api/rfx.py`  
**Fecha de corrección:** 12/01/2026
