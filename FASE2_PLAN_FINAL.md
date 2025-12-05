# 🎯 Fase 2: Plan Final - Chat Agent Tools

**Fecha:** Diciembre 4, 2025  
**Versión:** 3.0 (Final)

---

## 🔑 PRINCIPIO FUNDAMENTAL

### **Memoria Conversacional = SIEMPRE DISPONIBLE**

```
✅ FIJO: Agente SIEMPRE tiene acceso a memoria conversacional
- RunnableWithMessageHistory está activo
- Historial de mensajes disponible
- Referencias a mensajes previos funcionan

✅ TOOLS: Acceso a datos ACTUALES del request
- Consultar productos actuales
- Modificar datos del request
- Parsear documentos (opcional)
```

**Aclaración Importante:**
- La memoria conversacional NO es una tool
- Es parte del agente (ya implementado en Fase 1)
- Tools son para acceder a datos EXTERNOS (BD, archivos)

---

## 🛠️ TOOLS PARA FASE 2 (Prioridad Corregida)

### **PRIORIDAD 1: Tools de DATOS REQUEST** 🔴 CRÍTICAS

#### **Tool 1: `get_request_data_tool`** 🔴 MÁXIMA PRIORIDAD

**Propósito:** Consultar datos actuales del request (productos, totales, detalles)

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.get_rfx_products(rfx_id)
DatabaseClient.get_rfx_by_id(rfx_id)
```

**Firma:**
```python
@tool
def get_request_data_tool(
    data_type: str,  # "products", "summary", "details"
    request_id: str
) -> Dict[str, Any]:
    """
    Consulta datos actuales del request.
    
    Args:
        data_type: Tipo de datos a consultar
            - "products": Lista de productos actuales
            - "summary": Resumen (total, cantidad productos)
            - "details": Detalles del request (fechas, ubicación, etc.)
        request_id: ID del request (rfx_id)
    
    Returns:
        Datos solicitados del request
        
    Ejemplos de uso:
        Usuario: "¿Cuántos productos tengo?"
        Agente: get_request_data_tool("summary", request_id)
        
        Usuario: "¿Cuál es el total actual?"
        Agente: get_request_data_tool("summary", request_id)
        
        Usuario: "Muéstrame todos los productos"
        Agente: get_request_data_tool("products", request_id)
    """
```

**Implementación:**
```python
# backend/services/tools/get_request_data_tool.py
from langchain.tools import tool
from backend.core.database import get_database_client
from typing import Dict, Any

@tool
def get_request_data_tool(data_type: str, request_id: str) -> Dict[str, Any]:
    """Consulta datos actuales del request (wrapper de DatabaseClient)"""
    
    db = get_database_client()
    
    if data_type == "products":
        # Obtener lista completa de productos
        products = db.get_rfx_products(request_id)
        return {
            "products": products,
            "count": len(products)
        }
    
    elif data_type == "summary":
        # Obtener resumen: total y cantidad
        products = db.get_rfx_products(request_id)
        total = sum(
            p.get('price_unit', 0) * p.get('quantity', 0) 
            for p in products
        )
        return {
            "product_count": len(products),
            "total": total,
            "currency": "MXN"
        }
    
    elif data_type == "details":
        # Obtener detalles del request
        rfx = db.get_rfx_by_id(request_id)
        return {
            "title": rfx.get('title'),
            "event_date": rfx.get('project_start_date'),
            "location": rfx.get('event_location'),
            "city": rfx.get('event_city'),
            "status": rfx.get('status')
        }
    
    else:
        return {"error": f"Invalid data_type: {data_type}"}
```

**Beneficios:**
- ✅ Agente puede responder preguntas sobre estado actual
- ✅ Validar duplicados antes de insertar
- ✅ Verificar totales actuales
- ✅ Consultar detalles del evento

---

#### **Tool 2: `add_products_tool`** 🔴 CRÍTICA

**Propósito:** Insertar productos al request

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.create_rfx_product(rfx_id, product_data)
```

**Firma:**
```python
@tool
def add_products_tool(
    request_id: str,
    products: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Agrega productos al request.
    
    Args:
        request_id: ID del request (rfx_id)
        products: Lista de productos a agregar
            [
                {
                    "name": "Sillas",
                    "quantity": 10,
                    "price_unit": 150.0,
                    "category": "furniture"
                }
            ]
    
    Returns:
        Resultado con IDs de productos creados
    """
```

---

#### **Tool 3: `update_product_tool`** 🔴 CRÍTICA

**Propósito:** Actualizar producto existente

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.update_rfx_product(rfx_id, product_id, updates)
```

**Firma:**
```python
@tool
def update_product_tool(
    request_id: str,
    product_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Actualiza un producto del request.
    
    Args:
        request_id: ID del request (rfx_id)
        product_id: ID del producto
        updates: Campos a actualizar
            {
                "quantity": 20,
                "price_unit": 200.0,
                "name": "Sillas Premium"
            }
    
    Returns:
        Producto actualizado
        
    Ejemplo:
        Usuario: "Cambia la cantidad de sillas a 20"
        Agente: 
          1. get_request_data_tool("products", request_id)
          2. Encuentra producto "Sillas" con id=123
          3. update_product_tool(request_id, "123", {"quantity": 20})
    """
```

---

#### **Tool 4: `delete_product_tool`** 🔴 CRÍTICA

**Propósito:** Eliminar producto del request

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.delete_rfx_product(rfx_id, product_id)
```

**Firma:**
```python
@tool
def delete_product_tool(
    request_id: str,
    product_id: str
) -> Dict[str, Any]:
    """
    Elimina un producto del request.
    
    Args:
        request_id: ID del request (rfx_id)
        product_id: ID del producto
    
    Returns:
        Confirmación de eliminación
        
    Ejemplo:
        Usuario: "Elimina las sillas"
        Agente:
          1. get_request_data_tool("products", request_id)
          2. Encuentra producto "Sillas" con id=123
          3. delete_product_tool(request_id, "123")
    """
```

---

#### **Tool 5: `modify_request_details_tool`** 🔴 CRÍTICA

**Propósito:** Modificar detalles del request (fechas, ubicación, etc.)

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.update_rfx(rfx_id, updates)
```

**Firma:**
```python
@tool
def modify_request_details_tool(
    request_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Modifica detalles del request (no productos).
    
    Args:
        request_id: ID del request (rfx_id)
        updates: Campos a actualizar
            {
                "event_location": "Hotel Marriott",
                "project_start_date": "2025-12-15",
                "event_city": "CDMX"
            }
    
    Returns:
        Request actualizado
        
    Ejemplo:
        Usuario: "Cambia la ubicación a Hotel Marriott"
        Agente: modify_request_details_tool(request_id, {"event_location": "Hotel Marriott"})
    """
```

---

### **PRIORIDAD 2: Tool de PARSING** 🟡 MEDIA

#### **Tool 6: `parse_document_tool`** 🟡 SEGUNDA PRIORIDAD

**Propósito:** Parsear archivos adjuntos bajo demanda

**Wrapper de:**
```python
# backend/services/rfx_processor.py
RFXProcessorService._extract_text_from_document(file_content, file_type, filename)
```

**Firma:**
```python
@tool
def parse_document_tool(
    file_data: str,  # Base64 encoded
    file_type: str,  # "pdf", "excel", "image"
    filename: str
) -> str:
    """
    Parsea un documento adjunto y extrae su contenido como texto.
    
    Args:
        file_data: Contenido del archivo en base64
        file_type: Tipo de archivo (pdf, excel, image)
        filename: Nombre del archivo
    
    Returns:
        Contenido extraído como texto plano
        
    Nota: Esta tool es OPCIONAL en Fase 2
    - Prioridad: Implementar DESPUÉS de las tools de datos
    - Razón: Parsing manual funciona bien en Fase 1
    """
```

**Nota Importante:**
- Esta tool es la ÚLTIMA en prioridad
- Implementar solo después de que las tools de datos funcionen
- El parsing manual de Fase 1 funciona bien por ahora

---

## 📂 ESTRUCTURA DE ARCHIVOS

```
backend/services/tools/
├── __init__.py                        # Exporta todas las tools
├── get_request_data_tool.py          # 🔴 PRIORIDAD 1
├── add_products_tool.py              # 🔴 PRIORIDAD 1
├── update_product_tool.py            # 🔴 PRIORIDAD 1
├── delete_product_tool.py            # 🔴 PRIORIDAD 1
├── modify_request_details_tool.py    # 🔴 PRIORIDAD 1
└── parse_document_tool.py            # 🟡 PRIORIDAD 2 (opcional)
```

**Naming Convention:** `{accion}_{entidad}_tool.py`
- ✅ `get_request_data_tool.py` (no `get_rfx_data_tool.py`)
- ✅ `add_products_tool.py`
- ✅ `modify_request_details_tool.py`

---

## 🚀 PLAN DE IMPLEMENTACIÓN - CHECKLIST INTERACTIVO

---

## ✅ FASE 2A: PRIORIDAD 1 - TOOLS DE DATOS (CRÍTICAS) 🔴

### **Sprint 1: Tool de Consulta** (2-3 días) 🔴

**Objetivo:** Agente puede consultar datos actuales del request

#### **Tareas:**
- [x] 1.1 Crear estructura `backend/services/tools/`
- [x] 1.2 Crear `backend/services/tools/__init__.py`
- [x] 1.3 Implementar `get_request_data_tool.py`
  - [x] 1.3.1 Función base con decorator `@tool`
  - [x] 1.3.2 Implementar `data_type="products"`
  - [x] 1.3.3 Implementar `data_type="summary"`
  - [x] 1.3.4 Implementar `data_type="details"`
- [x] 1.4 Testing unitario de la tool
- [x] 1.5 Integrar tool en `ChatAgent`
  - [x] 1.5.1 Importar tool en `chat_agent.py`
  - [x] 1.5.2 Agregar tool a lista de tools
  - [x] 1.5.3 Configurar AgentExecutor con tools
- [x] 1.6 Actualizar system prompt con instrucciones de tool
- [ ] 1.7 Testing manual: "¿Cuántos productos tengo?"
- [ ] 1.8 Testing manual: "¿Cuál es el total actual?"

**Criterio de éxito:**
```
Usuario: "¿Cuántos productos tengo actualmente?"
Agente: 
  1. Llama get_request_data_tool("summary", request_id)
  2. Responde: "Tienes 10 productos con un total de $5,000 MXN"
```

---

### **Sprint 2: Tools CRUD de Productos** (3-4 días) 

**Objetivo:** Agente puede modificar productos (CRUD completo)

#### **Tareas:**
- [x] 2.1 Implementar `add_products_tool.py`
  - [x] 2.1.1 Función base con decorator `@tool`
  - [x] 2.1.2 Wrapper de `DatabaseClient.create_rfx_product()`
  - [x] 2.1.3 Manejo de múltiples productos
  - [x] 2.1.4 Testing unitario
- [x] 2.2 Implementar `update_product_tool.py`
  - [x] 2.2.1 Función base con decorator `@tool`
  - [x] 2.2.2 Wrapper de `DatabaseClient.update_rfx_product()`
  - [x] 2.2.3 Validación de producto existente
  - [x] 2.2.4 Testing unitario
- [x] 2.3 Implementar `delete_product_tool.py`
  - [x] 2.3.1 Función base con decorator `@tool`
  - [x] 2.3.2 Wrapper de `DatabaseClient.delete_rfx_product()`
  - [x] 2.3.3 Validación de producto existente
  - [x] 2.3.4 Testing unitario
- [x] 2.4 Integrar tools en `ChatAgent`
- [x] 2.5 Actualizar system prompt con instrucciones
  - [ ] 2.3.3 Validación de producto existente
  - [ ] 2.3.4 Testing unitario
- [ ] 2.4 Integrar tools en `ChatAgent`
- [ ] 2.5 Actualizar system prompt con instrucciones
- [ ] 2.6 Testing manual: Insertar productos
- [ ] 2.7 Testing manual: Actualizar cantidad
- [ ] 2.8 Testing manual: Eliminar producto

**Criterio de éxito:**
```
Usuario: "Cambia la cantidad de sillas a 20"
Agente:
  1. get_request_data_tool("products", request_id)
  2. Encuentra producto "Sillas" con id=123
  3. update_product_tool(request_id, "123", {"quantity": 20})
  4. Responde: "✅ Actualizado: Sillas ahora tiene cantidad 20"
```

---

### **Sprint 3: Tool de Modificación de Request** ✅ COMPLETADO

**Objetivo:** Agente puede modificar detalles del request

#### **Tareas:**
- [x] 3.1 Implementar `modify_request_details_tool.py`
  - [x] 3.1.1 Función base con decorator `@tool`
  - [x] 3.1.2 Wrapper de `DatabaseClient.update_rfx()`
  - [x] 3.1.3 Validación de campos permitidos
  - [x] 3.1.4 Testing unitario
- [x] 3.2 Integrar tool en `ChatAgent`
- [x] 3.3 Actualizar system prompt con instrucciones
- [ ] 3.4 Testing manual: Cambiar ubicación
- [ ] 3.5 Testing manual: Cambiar fecha
- [ ] 3.6 Testing manual: Cambiar ciudad

**Criterio de éxito:**
```
Usuario: "Cambia la ubicación a Hotel Marriott"
Agente:
  1. modify_request_details_tool(request_id, {"event_location": "Hotel Marriott"})
  2. Responde: "✅ Ubicación actualizada a Hotel Marriott"
```

---

### **Sprint 4: Validación y Testing Final** (2-3 días) 🔴

**Objetivo:** Validar que todas las tools funcionan correctamente

#### **Tareas:**
- [ ] 4.1 Testing end-to-end completo
  - [ ] 4.1.1 Conversación: Consultar → Insertar → Actualizar
  - [ ] 4.1.2 Conversación: Consultar → Eliminar
  - [ ] 4.1.3 Conversación: Modificar detalles del request
- [ ] 4.2 Testing: Validación de duplicados
- [ ] 4.3 Testing: Conversaciones multi-turno
- [ ] 4.4 Comparar performance con Fase 1
- [ ] 4.5 Documentación completa
  - [ ] 4.5.1 Actualizar `MIGRACION_CHAT_AGENT_A_LANGCHAIN.md`
  - [ ] 4.5.2 Crear guía de uso de tools
  - [ ] 4.5.3 Documentar ejemplos de conversaciones

---

## 🛑 PAUSA AQUÍ - ESPERAR APROBACIÓN PARA FASE 2B

**Estado Fase 2A:** ⏸️ PENDIENTE DE COMPLETAR

Una vez completada la Fase 2A, **DETENER** y esperar aprobación del usuario antes de continuar con Fase 2B.

---

## ⏸️ FASE 2B: PRIORIDAD 2 - TOOL DE PARSING (OPCIONAL) 🟡

### **Sprint 5 (OPCIONAL): Tool de Parsing** (2-3 días) 🟡

**Objetivo:** Agente decide cuándo parsear archivos

#### **Tareas:**
- [ ] 5.1 Implementar `parse_document_tool.py`
  - [ ] 5.1.1 Función base con decorator `@tool`
  - [ ] 5.1.2 Wrapper de `RFXProcessor._extract_text_from_document()`
  - [ ] 5.1.3 Manejo de base64
  - [ ] 5.1.4 Testing unitario
- [ ] 5.2 Integrar tool en `ChatAgent`
- [ ] 5.3 Actualizar system prompt
- [ ] 5.4 Testing: Agente decide cuándo parsear
- [ ] 5.5 Comparar con parsing manual de Fase 1

**Nota:** Solo implementar si hay tiempo y las tools de datos funcionan perfectamente

---

## 📊 RESUMEN DE PRIORIDADES

### **FASE 2A: Tools de Datos (CRÍTICAS)** 🔴

| # | Tool | Propósito | Sprint |
|---|------|-----------|--------|
| 1 | `get_request_data_tool` | Consultar datos actuales | Sprint 1 |
| 2 | `add_products_tool` | Insertar productos | Sprint 2 |
| 3 | `update_product_tool` | Actualizar producto | Sprint 2 |
| 4 | `delete_product_tool` | Eliminar producto | Sprint 2 |
| 5 | `modify_request_details_tool` | Modificar request | Sprint 3 |

**Duración total:** 7-10 días

### **FASE 2B: Tool de Parsing (OPCIONAL)** 🟡

| # | Tool | Propósito | Sprint |
|---|------|-----------|--------|
| 6 | `parse_document_tool` | Parsear archivos | Sprint 5 |

**Duración:** 2-3 días (solo si hay tiempo)

---

## 🎯 CRITERIOS DE ÉXITO FASE 2A

### **Funcionalidad Mínima:**

- ✅ Agente puede consultar datos actuales del request
- ✅ Agente puede responder "¿Cuántos productos tengo?"
- ✅ Agente puede insertar productos
- ✅ Agente puede actualizar productos
- ✅ Agente puede eliminar productos
- ✅ Agente puede modificar detalles del request

### **Conversaciones que Deben Funcionar:**

```
Conversación 1: Consulta
Usuario: "¿Cuántos productos tengo?"
Agente: [Llama get_request_data_tool] "Tienes 10 productos"

Conversación 2: Actualización
Usuario: "Cambia la cantidad de sillas a 20"
Agente: [Consulta productos, actualiza] "✅ Actualizado"

Conversación 3: Eliminación
Usuario: "Elimina las mesas"
Agente: [Consulta productos, elimina] "✅ Eliminado"

Conversación 4: Modificación Request
Usuario: "Cambia la ubicación a Hotel Marriott"
Agente: [Modifica request] "✅ Ubicación actualizada"
```

---

## 🔑 PUNTOS CLAVE (Recordatorio)

### **1. Memoria Conversacional = SIEMPRE ACTIVA**
```
✅ NO es una tool
✅ Ya está implementado en Fase 1
✅ Agente SIEMPRE tiene acceso al historial
```

### **2. Tools = Datos ACTUALES de BD**
```
✅ Consultar productos actuales
✅ Modificar datos del request
✅ NO es para acceder a memoria (ya tiene acceso)
```

### **3. Naming: request (no rfx)**
```
✅ get_request_data_tool
✅ modify_request_details_tool
❌ get_rfx_data_tool
```

### **4. Prioridad: Datos > Parsing**
```
🔴 PRIMERO: Tools de datos (consultar, modificar)
🟡 DESPUÉS: Tool de parsing (opcional)
```

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS

1. **Aprobar este plan final**
2. **Crear estructura de carpetas**
3. **Comenzar Sprint 1: `get_request_data_tool`**

---

**Última actualización:** Diciembre 4, 2025  
**Status:** ✅ PLAN FINAL APROBADO - LISTO PARA IMPLEMENTAR
