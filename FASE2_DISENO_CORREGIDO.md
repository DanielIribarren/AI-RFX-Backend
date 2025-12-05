# 🎯 Fase 2: Diseño Corregido - Chat Agent Tools

**Fecha:** Diciembre 4, 2025  
**Versión:** 2.0 (Corregida)

---

## 🔍 CONTEXTO: Lo que Realmente Dijimos en la Migración

### **Fase 1 (COMPLETADA)** ✅
```
"Parsing MANUAL antes del agente"
- ChatAgent usa RFXProcessorService para parsear archivos
- El contenido se pasa como STRING en el prompt
- NO hay tools todavía
```

### **Fase 2 (AHORA)** 🚧
```
"Migrar parsing a LangChain Tools"
- Tools son WRAPPERS de funciones existentes
- RFXProcessorService NO cambia
- ChatAgent decide CUÁNDO parsear (no manual)
```

### **Fase 3 (FUTURO)** 🔮
```
"RFXProcessor también usa LangChain"
- Compartir tools entre ChatAgent y RFXProcessor
- Unificar arquitectura
```

---

## ❌ ERROR EN EL ANÁLISIS ANTERIOR

### **Lo que dije mal:**

> "ERROR 1: Pérdida de Contexto de Archivos"
> "Solución: Tool `get_file_content` para acceder a archivos previos"

**Esto NO tiene sentido porque:**
1. Los archivos se parsean y el contenido va al prompt
2. LangChain SÍ guarda el contenido en el historial (está en el mensaje del usuario)
3. El problema NO es "pérdida de contexto", es que el parsing es MANUAL

### **El Problema Real:**

```python
# FASE 1 (Actual):
files_content = self._extract_files_content(files, chat_log)  # Manual
message = f"{message}\n\n### ARCHIVOS ADJUNTOS:\n{files_content}"
# ↓
# El agente recibe el contenido como STRING en el prompt
# ✅ Esto SÍ se guarda en historial
# ❌ Pero el agente NO decide cuándo parsear
```

**Lo que queremos en Fase 2:**
```python
# FASE 2 (Con Tools):
# El agente decide SI necesita parsear el archivo
# Tool: parse_document_tool(file_bytes, file_type)
# El agente llama a la tool SOLO si necesita el contenido
```

---

## ✅ DISEÑO CORREGIDO: Tools para Chat Agent

### **Principio Fundamental:**

```
Tools = Wrappers de funciones existentes
- NO duplicar código
- NO modificar RFXProcessorService
- Tools llaman a métodos existentes
```

---

## 🛠️ TOOLS REALES PARA FASE 2

### **Categoría 1: Tools de PARSING (Wrappers de RFXProcessor)**

#### **Tool 1: `parse_document_tool`** 🔴 CRÍTICA

**Propósito:** Parsear archivos adjuntos (PDF, Excel, Imágenes)

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
        
    Ejemplo:
        Usuario adjunta "productos.pdf"
        Agente decide: "Necesito ver el contenido"
        Agente llama: parse_document_tool(file_data, "pdf", "productos.pdf")
    """
```

**Implementación:**
```python
# backend/services/tools/parse_document_tool.py
from langchain.tools import tool
from backend.services.rfx_processor import RFXProcessorService
import base64

@tool
def parse_document_tool(file_data: str, file_type: str, filename: str) -> str:
    """Parsea documento adjunto (wrapper de RFXProcessor)"""
    
    # 1. Decodificar base64
    file_bytes = base64.b64decode(file_data)
    
    # 2. REUTILIZAR método existente
    processor = RFXProcessorService()
    content = processor._extract_text_from_document(
        file_content=file_bytes,
        file_type=file_type,
        filename=filename
    )
    
    return content
```

**Beneficio:**
- Agente decide CUÁNDO parsear (no siempre)
- Reutiliza código existente 100%
- No duplica lógica de parsing

---

### **Categoría 2: Tools de DATOS RFX**

#### **Tool 2: `get_rfx_data_tool`** 🔴 CRÍTICA

**Propósito:** Consultar datos actuales del RFX

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.get_rfx_products(rfx_id)
DatabaseClient.get_rfx_by_id(rfx_id)
```

**Firma:**
```python
@tool
def get_rfx_data_tool(
    data_type: str,  # "products", "summary", "details"
    rfx_id: str
) -> Dict[str, Any]:
    """
    Consulta datos actuales del RFX.
    
    Args:
        data_type: Tipo de datos ("products", "summary", "details")
        rfx_id: ID del RFX
    
    Returns:
        Datos solicitados
        
    Ejemplo:
        Usuario: "¿Cuántos productos tengo?"
        Agente: get_rfx_data_tool("summary", rfx_id)
    """
```

**Implementación:**
```python
# backend/services/tools/get_rfx_data_tool.py
from langchain.tools import tool
from backend.core.database import get_database_client

@tool
def get_rfx_data_tool(data_type: str, rfx_id: str) -> dict:
    """Consulta datos del RFX (wrapper de DatabaseClient)"""
    
    db = get_database_client()
    
    if data_type == "products":
        products = db.get_rfx_products(rfx_id)
        return {"products": products, "count": len(products)}
    
    elif data_type == "summary":
        products = db.get_rfx_products(rfx_id)
        total = sum(p.get('price_unit', 0) * p.get('quantity', 0) for p in products)
        return {
            "product_count": len(products),
            "total": total,
            "currency": "MXN"
        }
    
    elif data_type == "details":
        rfx = db.get_rfx_by_id(rfx_id)
        return {
            "title": rfx.get('title'),
            "event_date": rfx.get('project_start_date'),
            "location": rfx.get('event_location'),
            "status": rfx.get('status')
        }
```

---

#### **Tool 3: `add_products_tool`** 🔴 CRÍTICA

**Propósito:** Insertar productos al RFX

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.create_rfx_product(rfx_id, product_data)
```

**Firma:**
```python
@tool
def add_products_tool(
    rfx_id: str,
    products: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Agrega productos al RFX.
    
    Args:
        rfx_id: ID del RFX
        products: Lista de productos a agregar
    
    Returns:
        Resultado con IDs de productos creados
    """
```

---

#### **Tool 4: `update_product_tool`** 🔴 CRÍTICA

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
    rfx_id: str,
    product_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Actualiza un producto del RFX.
    
    Args:
        rfx_id: ID del RFX
        product_id: ID del producto
        updates: Campos a actualizar
    
    Returns:
        Producto actualizado
    """
```

---

#### **Tool 5: `delete_product_tool`** 🔴 CRÍTICA

**Propósito:** Eliminar producto

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.delete_rfx_product(rfx_id, product_id)
```

**Firma:**
```python
@tool
def delete_product_tool(
    rfx_id: str,
    product_id: str
) -> Dict[str, Any]:
    """
    Elimina un producto del RFX.
    
    Args:
        rfx_id: ID del RFX
        product_id: ID del producto
    
    Returns:
        Confirmación de eliminación
    """
```

---

#### **Tool 6: `modify_rfx_details_tool`** 🟡 MEDIA

**Propósito:** Modificar detalles del RFX (fechas, ubicación, etc.)

**Wrapper de:**
```python
# backend/core/database.py
DatabaseClient.update_rfx(rfx_id, updates)
```

---

## 📂 ESTRUCTURA DE ARCHIVOS (Mejores Prácticas)

```
backend/services/tools/
├── __init__.py                    # Exporta todas las tools
├── parse_document_tool.py         # Parsing de archivos
├── get_rfx_data_tool.py          # Consultar datos RFX
├── add_products_tool.py          # Insertar productos
├── update_product_tool.py        # Actualizar producto
├── delete_product_tool.py        # Eliminar producto
└── modify_rfx_details_tool.py    # Modificar RFX
```

**Naming Convention:** `{accion}_{entidad}_tool.py`
- ✅ `get_rfx_data_tool.py`
- ✅ `parse_document_tool.py`
- ✅ `add_products_tool.py`

---

## 🎯 RESUMEN DE TOOLS (Corregido)

### **Tools CRÍTICAS (Fase 2)** 🔴

| Tool | Wrapper de | Propósito |
|------|------------|-----------|
| `parse_document_tool` | `RFXProcessor._extract_text_from_document()` | Parsear archivos |
| `get_rfx_data_tool` | `DatabaseClient.get_rfx_products()` | Consultar datos |
| `add_products_tool` | `DatabaseClient.create_rfx_product()` | Insertar productos |
| `update_product_tool` | `DatabaseClient.update_rfx_product()` | Actualizar producto |
| `delete_product_tool` | `DatabaseClient.delete_rfx_product()` | Eliminar producto |

### **Tools OPCIONALES** 🟡

| Tool | Wrapper de | Propósito |
|------|------------|-----------|
| `modify_rfx_details_tool` | `DatabaseClient.update_rfx()` | Modificar RFX |

---

## 🔄 COMPARACIÓN: Fase 1 vs Fase 2

### **Fase 1 (Actual):**
```python
# Parsing MANUAL
files_content = self._extract_files_content(files, chat_log)
message = f"{message}\n\n### ARCHIVOS:\n{files_content}"

# El agente recibe TODO el contenido siempre
# ❌ No decide cuándo parsear
# ❌ Parsea TODOS los archivos siempre
```

### **Fase 2 (Con Tools):**
```python
# Agente decide SI parsear
tools = [parse_document_tool, get_rfx_data_tool, ...]

# El agente recibe metadata de archivos
# ✅ Decide si necesita parsear
# ✅ Llama a parse_document_tool solo si necesita
# ✅ Puede parsear solo algunos archivos
```

---

## 🚀 PLAN DE IMPLEMENTACIÓN (Corregido)

### **Sprint 1: Tool de Parsing** (2-3 días)

- [ ] Crear estructura `backend/services/tools/`
- [ ] Implementar `parse_document_tool.py`
- [ ] Testing: Agente decide cuándo parsear
- [ ] Comparar con Fase 1 (manual parsing)

### **Sprint 2: Tools de Datos RFX** (2-3 días)

- [ ] Implementar `get_rfx_data_tool.py`
- [ ] Testing: Consultar productos actuales
- [ ] Testing: Validación de duplicados

### **Sprint 3: Tools CRUD** (3-4 días)

- [ ] Implementar `add_products_tool.py`
- [ ] Implementar `update_product_tool.py`
- [ ] Implementar `delete_product_tool.py`
- [ ] Testing: CRUD completo

### **Sprint 4: Integración** (2-3 días)

- [ ] Integrar todas las tools en ChatAgent
- [ ] Actualizar system prompt
- [ ] Testing end-to-end
- [ ] Documentación

---

## 📊 SOBRE RFXProcessor (Fase 3 - Futuro)

### **¿Qué tools necesita RFXProcessor?**

Solo **2 tools** (las de parsing):
1. `parse_document_tool` - Parsear PDFs, Excel, Imágenes
2. ~~`extract_structured_data_tool`~~ - Ya lo hace con prompts

**Pero NO es prioridad ahora:**
- RFXProcessor funciona bien como está
- Fase 3 es para DESPUÉS de que Chat Agent funcione perfectamente
- Compartir tools es optimización, no necesidad

---

## ✅ PRINCIPIOS CORREGIDOS

### **1. Tools = Wrappers (NO duplicar código)**
```python
# ✅ CORRECTO
@tool
def parse_document_tool(...):
    processor = RFXProcessorService()
    return processor._extract_text_from_document(...)

# ❌ INCORRECTO
@tool
def parse_document_tool(...):
    # Reimplementar parsing desde cero
    # Duplicar lógica de PyPDF2, openpyxl, etc.
```

### **2. Agente Decide (NO parsing manual)**
```python
# ✅ FASE 2
# Agente recibe metadata de archivos
# Agente decide si llama a parse_document_tool

# ❌ FASE 1
# Parsear TODOS los archivos siempre
# Pasar contenido completo al prompt
```

### **3. Una Tool por Archivo**
```
✅ backend/services/tools/parse_document_tool.py
✅ backend/services/tools/get_rfx_data_tool.py
✅ backend/services/tools/add_products_tool.py
```

---

## 🎯 PRÓXIMOS PASOS INMEDIATOS

1. **Aprobar este diseño corregido**
2. **Crear estructura de carpetas**
3. **Comenzar con `parse_document_tool.py`**

---

**Última actualización:** Diciembre 4, 2025  
**Status:** 📝 DISEÑO CORREGIDO - LISTO PARA IMPLEMENTAR
