# 🔄 Refactorización Tools - HTTP Endpoints en lugar de Database Direct

**Fecha:** 4 de Diciembre, 2025  
**Filosofía:** Las tools NO tienen lógica de negocio, solo llaman a endpoints HTTP existentes

---

## 🎯 Problema Original

Las tools tenían **lógica de negocio duplicada**:
- ❌ Acceso directo a `DatabaseClient`
- ❌ Validación de datos en las tools
- ❌ Mapeo de campos
- ❌ Lógica de inserción/actualización

**Resultado:** Código duplicado, difícil de mantener, tools "inteligentes" en lugar de simples wrappers.

---

## ✅ Solución Implementada

### Principio KISS

```
Tools = HTTP Client Simple
├─ Llaman a endpoints existentes
├─ Retornan JSON raw sin modificación
└─ El agente lee, razona y decide
```

### Flujo Correcto

```
Usuario: "Agrega 10 sillas"
    ↓
Agente: Decide usar add_products_tool
    ↓
Tool: POST http://localhost:5001/api/rfx/{rfx_id}/products
    ↓
Endpoint: Valida, inserta en BD, retorna JSON
    ↓
Tool: Retorna JSON raw al agente
    ↓
Agente: Lee JSON, razona, responde al usuario
    ↓
Respuesta: "✅ Agregué 10 sillas..."
```

---

## 📝 Tools Refactorizadas

### 1. `get_request_data_tool`

**ANTES:**
```python
db = get_database_client()
products = db.get_rfx_products(request_id)
return {"products": products, "count": len(products)}
```

**DESPUÉS:**
```python
url = f"{base_url}/api/rfx/{request_id}/products"
response = requests.get(url)
return response.json()  # JSON raw del endpoint
```

**Endpoints usados:**
- `GET /api/rfx/<rfx_id>/products` - Para data_type="products"
- `GET /api/rfx/<rfx_id>` - Para data_type="details"

---

### 2. `add_products_tool`

**ANTES:**
```python
db = get_database_client()
for product in products:
    # Validación
    if not product.get('name'): continue
    # Mapeo de campos
    product_data = {"nombre": product.get('name'), ...}
    # Inserción
    product_id = db.create_rfx_product(request_id, product_data)
```

**DESPUÉS:**
```python
url = f"{base_url}/api/rfx/{request_id}/products"
payload = {"products": products}
response = requests.post(url, json=payload)
return response.json()  # JSON raw del endpoint
```

**Endpoint usado:**
- `POST /api/rfx/<rfx_id>/products`

---

### 3. `update_product_tool`

**ANTES:**
```python
db = get_database_client()
# Mapeo de campos
field_mapping = {"name": "nombre", "quantity": "cantidad", ...}
db_updates = {field_mapping.get(k, k): v for k, v in updates.items()}
success = db.update_rfx_product(request_id, product_id, db_updates)
```

**DESPUÉS:**
```python
url = f"{base_url}/api/rfx/{request_id}/products/{product_id}"
response = requests.put(url, json=updates)
return response.json()  # JSON raw del endpoint
```

**Endpoint usado:**
- `PUT /api/rfx/<rfx_id>/products/<product_id>`

---

### 4. `delete_product_tool`

**ANTES:**
```python
db = get_database_client()
# Verificar existencia
products = db.get_rfx_products(request_id)
product = next((p for p in products if p.get('id') == product_id), None)
if not product: return error
# Eliminar
db.delete_rfx_product(request_id, product_id)
```

**DESPUÉS:**
```python
url = f"{base_url}/api/rfx/{request_id}/products/{product_id}"
response = requests.delete(url)
return response.json()  # JSON raw del endpoint
```

**Endpoint usado:**
- `DELETE /api/rfx/<rfx_id>/products/<product_id>`

---

### 5. `modify_request_details_tool`

**ANTES:**
```python
db = get_database_client()
# Verificar existencia
rfx = db.get_rfx_by_id(request_id)
if not rfx: return error
# Mapeo de campos
field_mapping = {"event_date": "project_start_date", ...}
update_data = {field_mapping.get(k, k): v for k, v in updates.items()}
db.update_rfx(request_id, update_data)
```

**DESPUÉS:**
```python
url = f"{base_url}/api/rfx/{request_id}/data"
response = requests.put(url, json=updates)
return response.json()  # JSON raw del endpoint
```

**Endpoint usado:**
- `PUT /api/rfx/<rfx_id>/data`

---

## 📊 Comparación

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Dependencias** | `DatabaseClient` | `requests` + `os` |
| **Líneas de código** | ~150 líneas | ~30 líneas |
| **Lógica de negocio** | En tools | En endpoints |
| **Validación** | Duplicada | Solo en endpoints |
| **Mapeo de campos** | En tools | En endpoints |
| **Mantenibilidad** | Baja (código duplicado) | Alta (un solo lugar) |
| **Testing** | Difícil (mock DB) | Fácil (mock HTTP) |

---

## 🔧 Configuración

### Variable de Entorno

```bash
# .env
BASE_URL=http://localhost:5001
```

Las tools usan esta variable para construir las URLs:
```python
base_url = os.getenv('BASE_URL', 'http://localhost:5001')
url = f"{base_url}/api/rfx/{request_id}/products"
```

---

## 🧪 Testing

### Ejemplo: Agregar Producto

```python
# Tool call
result = add_products_tool(
    request_id="uuid-123",
    products=[
        {"name": "Sillas", "quantity": 10, "price_unit": 150.0}
    ]
)

# Resultado (JSON raw del endpoint)
{
    "status": "success",
    "message": "1 producto(s) agregado(s) exitosamente",
    "products": [
        {
            "id": "uuid-producto",
            "nombre": "Sillas",
            "cantidad": 10,
            "precio": 150.0
        }
    ]
}
```

### Ejemplo: Consultar Productos

```python
# Tool call
result = get_request_data_tool(
    data_type="products",
    request_id="uuid-123"
)

# Resultado (JSON raw del endpoint)
{
    "status": "success",
    "products": [
        {"id": "uuid-1", "nombre": "Sillas", "cantidad": 10, "precio": 150.0},
        {"id": "uuid-2", "nombre": "Mesas", "cantidad": 5, "precio": 300.0}
    ],
    "currency": "MXN",
    "total": 3000.0
}
```

---

## ✅ Beneficios

### 1. **Separación de Responsabilidades**
- Tools = HTTP clients simples
- Endpoints = Lógica de negocio
- Agente = Razonamiento e inteligencia

### 2. **Sin Código Duplicado**
- Validación: Solo en endpoints
- Mapeo de campos: Solo en endpoints
- Lógica de BD: Solo en endpoints

### 3. **Fácil de Mantener**
- Cambiar validación: Solo modificar endpoint
- Agregar campo: Solo modificar endpoint
- Tools no necesitan cambios

### 4. **Fácil de Testear**
- Mock HTTP requests (simple)
- No necesitas mock de DatabaseClient
- Tests unitarios más simples

### 5. **Escalabilidad**
- Tools pueden llamar a microservicios externos
- No están acopladas a la base de datos
- Fácil migrar a arquitectura distribuida

---

## 🚀 Próximos Pasos

### Fase 1: Testing ✅
- [ ] Probar `get_request_data_tool` con diferentes data_types
- [ ] Probar `add_products_tool` con múltiples productos
- [ ] Probar `update_product_tool` con diferentes campos
- [ ] Probar `delete_product_tool`
- [ ] Probar `modify_request_details_tool`

### Fase 2: Optimizaciones
- [ ] Agregar retry logic para requests HTTP
- [ ] Implementar timeout configurables
- [ ] Agregar caching de respuestas (opcional)

### Fase 3: Monitoreo
- [ ] Logging de latencia de HTTP requests
- [ ] Métricas de success rate por tool
- [ ] Alertas si endpoints fallan

---

## 📚 Endpoints Disponibles

### Productos

| Método | Endpoint | Tool que lo usa |
|--------|----------|-----------------|
| GET | `/api/rfx/<rfx_id>/products` | `get_request_data_tool` |
| POST | `/api/rfx/<rfx_id>/products` | `add_products_tool` |
| PUT | `/api/rfx/<rfx_id>/products/<product_id>` | `update_product_tool` |
| DELETE | `/api/rfx/<rfx_id>/products/<product_id>` | `delete_product_tool` |

### RFX Details

| Método | Endpoint | Tool que lo usa |
|--------|----------|-----------------|
| GET | `/api/rfx/<rfx_id>` | `get_request_data_tool` |
| PUT | `/api/rfx/<rfx_id>/data` | `modify_request_details_tool` |

---

## 🎯 Filosofía AI-First

```
El agente es INTELIGENTE:
├─ Lee JSON raw de los endpoints
├─ Razona con los datos
├─ Decide qué hacer
└─ Responde conversacionalmente

Las tools son SIMPLES:
├─ Llaman a HTTP endpoints
├─ Retornan JSON raw
└─ Sin lógica de negocio

Los endpoints son ROBUSTOS:
├─ Validan datos
├─ Aplican lógica de negocio
├─ Manejan errores
└─ Retornan JSON estructurado
```

---

**Estado:** ✅ IMPLEMENTADO - Todas las tools refactorizadas

**Archivos modificados:**
- ✅ `backend/services/tools/get_request_data_tool.py`
- ✅ `backend/services/tools/add_products_tool.py`
- ✅ `backend/services/tools/update_product_tool.py`
- ✅ `backend/services/tools/delete_product_tool.py`
- ✅ `backend/services/tools/modify_request_details_tool.py`
