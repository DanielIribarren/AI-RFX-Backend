# 📊 Análisis de Fase 1 y Diseño de Fase 2 - Chat Agent LangChain

**Fecha:** Diciembre 4, 2025  
**Status Fase 1:** ✅ COMPLETADA  
**Status Fase 2:** 📝 EN DISEÑO

---

## 🔍 ANÁLISIS CRÍTICO DE FASE 1

### ✅ **Éxitos de Fase 1**

#### **1. Memoria Conversacional Funcional**
- ✅ `RunnableWithMessageHistory` implementado correctamente
- ✅ Historial persistente en PostgreSQL (`rfx_chat_history`)
- ✅ Referencias a mensajes previos funcionan
- ✅ Contexto por RFX (session_id = rfx_id)

#### **2. Arquitectura Limpia**
- ✅ No se modificó `rfx_processor.py` (reutilización total)
- ✅ Logging conversacional implementado (`ChatLogger`)
- ✅ Parsing de archivos funcional (reutiliza `RFXProcessor`)

#### **3. Estabilidad**
- ✅ Backend inicia correctamente
- ✅ Sin errores de dependencias (después de fixes)
- ✅ Conversaciones simples funcionan

---

### ❌ **ERRORES CRÍTICOS IDENTIFICADOS EN FASE 1**

#### **ERROR 1: Pérdida de Contexto de Archivos Adjuntos** 🔴

**Problema:**
```
Usuario: [Adjunta PDF con productos] "Inserta estos productos"
Agente: "Detecté ambigüedad, ¿confirmas insertar?"
Usuario: "Sí, inserta los productos"
Agente: ❌ "No tengo información de qué productos insertar"
```

**Causa Raíz:**
- El archivo se parsea en `_extract_files_content()` ANTES de llamar al agente
- El contenido extraído se pasa como STRING en el prompt
- LangChain NO guarda el contenido del archivo en el historial
- En el siguiente mensaje, el agente NO tiene acceso al contenido del archivo

**Por qué pasa:**
```python
# backend/services/chat_agent.py - Línea ~140
files_content = self._extract_files_content(files, chat_log)

# El contenido se pasa al prompt como string
formatted_input = self._format_input(message, context)
# Pero NO se guarda en el historial de LangChain
```

**Impacto:** 🔴 CRÍTICO
- Conversaciones multi-turno con archivos NO funcionan
- Usuario debe re-adjuntar archivo en cada mensaje

---

#### **ERROR 2: Sin Acceso a Datos Actuales del RFX** 🔴

**Problema:**
```
Usuario: "¿Cuáles son los productos actuales del RFX?"
Agente: ❌ "No tengo información de productos actuales"
```

**Causa Raíz:**
- El agente recibe `context` con productos en el prompt
- Pero solo cuando va a INSERTAR productos
- No tiene una Tool para CONSULTAR datos del RFX bajo demanda

**Por qué pasa:**
```python
# backend/api/rfx_chat.py - Línea ~70
context = {
    "current_products": products,  # Solo se pasa al inicio
    "current_total": total
}
```

**Impacto:** 🔴 CRÍTICO
- Agente no puede responder preguntas sobre estado actual
- No puede verificar duplicados antes de insertar
- No puede hacer correcciones inteligentes

---

#### **ERROR 3: Operaciones CRUD Incompletas** 🟡

**Problema:**
- ✅ Agente puede INSERTAR productos
- ❌ Agente NO puede ELIMINAR productos
- ❌ Agente NO puede ACTUALIZAR productos existentes
- ❌ Agente NO puede modificar otros datos del RFX (fechas, ubicación, etc.)

**Causa Raíz:**
- El `ChatResponse` solo soporta `changes` con `action: "add"`
- No hay acciones para `update`, `delete`, `modify_rfx_data`

**Impacto:** 🟡 MEDIO
- Usuario debe usar UI para eliminar/actualizar
- Agente no puede corregir errores que él mismo cometió

---

#### **ERROR 4: Sin Validación de Duplicados** 🟡

**Problema:**
```
Usuario: "Agrega 10 sillas"
Agente: ✅ Inserta 10 sillas
Usuario: "Agrega 10 sillas" (olvida que ya las agregó)
Agente: ✅ Inserta 10 sillas MÁS (ahora hay 20)
```

**Causa Raíz:**
- Agente no consulta productos actuales antes de insertar
- No tiene Tool para verificar duplicados

**Impacto:** 🟡 MEDIO
- Datos duplicados en RFX
- Usuario debe limpiar manualmente

---

### 📊 **Resumen de Problemas**

| # | Problema | Severidad | Causa | Solución (Fase 2) |
|---|----------|-----------|-------|-------------------|
| 1 | Pérdida de contexto de archivos | 🔴 CRÍTICO | Parsing manual, no Tool | Tool: `get_file_content` |
| 2 | Sin acceso a datos RFX | 🔴 CRÍTICO | Context estático | Tool: `get_rfx_data` |
| 3 | CRUD incompleto | 🟡 MEDIO | Solo `add` action | Tools: `update_product`, `delete_product`, `modify_rfx` |
| 4 | Sin validación duplicados | 🟡 MEDIO | No consulta antes | Tool: `get_rfx_data` + lógica |

---

## 🎯 DISEÑO DE FASE 2: TOOLS INTELIGENTES

### **Filosofía de Diseño**

```
PRINCIPIO 1: Tools = Acceso a Información + Acciones
- Tools de LECTURA: Consultar datos (RFX, archivos, catálogo)
- Tools de ESCRITURA: Modificar datos (CRUD completo)

PRINCIPIO 2: Agente Decide Cuándo Usar Tools
- NO parsing manual antes del agente
- Agente decide si necesita leer archivo
- Agente decide si necesita consultar RFX

PRINCIPIO 3: Stateless Tools, Stateful Agent
- Tools no guardan estado
- Agente usa memoria conversacional para contexto
- Tools reciben solo parámetros necesarios
```

---

## 🛠️ TOOLS DEFINIDAS PARA FASE 2

### **Categoría 1: Tools de LECTURA (Información)**

#### **Tool 1: `get_file_content`** 🔴 CRÍTICA

**Propósito:** Acceder a contenido de archivos adjuntos en mensajes previos

**Firma:**
```python
@tool
def get_file_content(
    message_index: int,
    file_index: int = 0
) -> str:
    """
    Obtiene el contenido de un archivo adjunto en un mensaje previo.
    
    Args:
        message_index: Índice del mensaje en el historial (0 = más reciente)
        file_index: Índice del archivo si hay múltiples (default: 0)
    
    Returns:
        Contenido extraído del archivo como texto
        
    Ejemplo:
        Usuario (mensaje -2): [Adjunta productos.pdf]
        Usuario (mensaje -1): "Inserta esos productos"
        Agente: get_file_content(message_index=2, file_index=0)
    """
```

**Implementación:**
```python
# backend/services/langchain_tools/file_tools.py
from langchain.tools import tool
from backend.services.rfx_processor import RFXProcessorService

@tool
def get_file_content(message_index: int, file_index: int = 0) -> str:
    """Obtiene contenido de archivo en mensaje previo"""
    # 1. Obtener historial de mensajes (desde g.rfx_id o context)
    # 2. Buscar mensaje en índice especificado
    # 3. Extraer archivo en file_index
    # 4. Parsear con RFXProcessor._extract_text_from_document()
    # 5. Retornar contenido
    pass
```

**Soluciona:** ERROR 1 (Pérdida de contexto de archivos)

---

#### **Tool 2: `get_rfx_data`** 🔴 CRÍTICA

**Propósito:** Consultar datos actuales del RFX (productos, totales, detalles)

**Firma:**
```python
@tool
def get_rfx_data(
    data_type: str,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Consulta datos actuales del RFX.
    
    Args:
        data_type: Tipo de datos a consultar
            - "products": Lista de productos actuales
            - "summary": Resumen (total, cantidad productos)
            - "details": Detalles del RFX (fechas, ubicación, etc.)
            - "all": Todos los datos
        filters: Filtros opcionales (ej: {"category": "furniture"})
    
    Returns:
        Diccionario con los datos solicitados
        
    Ejemplo:
        get_rfx_data("products") → Lista de productos
        get_rfx_data("summary") → {"total": 5000, "product_count": 10}
    """
```

**Implementación:**
```python
# backend/services/langchain_tools/rfx_tools.py
from langchain.tools import tool
from backend.core.database import get_database_client

@tool
def get_rfx_data(data_type: str, filters: Optional[Dict] = None) -> Dict:
    """Consulta datos actuales del RFX"""
    db = get_database_client()
    rfx_id = get_current_rfx_id()  # Desde context o g
    
    if data_type == "products":
        products = db.get_rfx_products(rfx_id)
        if filters:
            # Filtrar productos por criterios
            products = apply_filters(products, filters)
        return {"products": products}
    
    elif data_type == "summary":
        products = db.get_rfx_products(rfx_id)
        total = sum(p['price_unit'] * p['quantity'] for p in products)
        return {
            "product_count": len(products),
            "total": total,
            "currency": "MXN"
        }
    
    elif data_type == "details":
        rfx = db.get_rfx_by_id(rfx_id)
        return {
            "title": rfx['title'],
            "event_date": rfx['project_start_date'],
            "location": rfx['event_location'],
            "status": rfx['status']
        }
    
    elif data_type == "all":
        # Retornar todo
        pass
```

**Soluciona:** ERROR 2 (Sin acceso a datos RFX) + ERROR 4 (Validación duplicados)

---

#### **Tool 3: `search_catalog`** 🟢 OPCIONAL (Futuro)

**Propósito:** Buscar productos en catálogo de la empresa

**Firma:**
```python
@tool
def search_catalog(
    query: str,
    category: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Busca productos en el catálogo de la empresa.
    
    Args:
        query: Término de búsqueda (ej: "sillas", "mesas redondas")
        category: Categoría opcional para filtrar
        max_results: Máximo número de resultados
    
    Returns:
        Lista de productos del catálogo con precios sugeridos
    """
```

**Nota:** Requiere tabla `catalog` en BD (no existe aún)

---

### **Categoría 2: Tools de ESCRITURA (Acciones)**

#### **Tool 4: `add_products`** ✅ YA EXISTE (mejorar)

**Propósito:** Insertar nuevos productos al RFX

**Firma ACTUAL:**
```python
# Actualmente se hace via ChatResponse.changes
changes = [
    {
        "action": "add",
        "entity": "product",
        "data": {
            "name": "Sillas",
            "quantity": 10,
            "price_unit": 150.0
        }
    }
]
```

**Firma MEJORADA (Tool):**
```python
@tool
def add_products(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agrega productos al RFX.
    
    Args:
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
        Resultado de la operación con IDs de productos creados
    """
```

**Beneficio:** Validación y ejecución inmediata (no esperar a frontend)

---

#### **Tool 5: `update_product`** 🔴 CRÍTICA (Nueva)

**Propósito:** Actualizar producto existente

**Firma:**
```python
@tool
def update_product(
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    updates: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Actualiza un producto existente del RFX.
    
    Args:
        product_id: ID del producto (si se conoce)
        product_name: Nombre del producto (si no se conoce ID)
        updates: Campos a actualizar
            {
                "quantity": 20,  # Cambiar cantidad
                "price_unit": 200.0,  # Cambiar precio
                "name": "Sillas Premium"  # Cambiar nombre
            }
    
    Returns:
        Producto actualizado
        
    Ejemplo:
        Usuario: "Cambia la cantidad de sillas a 20"
        Agente: update_product(product_name="Sillas", updates={"quantity": 20})
    """
```

**Implementación:**
```python
@tool
def update_product(product_id: str = None, product_name: str = None, updates: Dict = {}) -> Dict:
    """Actualiza producto existente"""
    db = get_database_client()
    rfx_id = get_current_rfx_id()
    
    # 1. Buscar producto por ID o nombre
    if product_id:
        product = db.get_product_by_id(product_id)
    elif product_name:
        products = db.get_rfx_products(rfx_id)
        product = next((p for p in products if p['name'].lower() == product_name.lower()), None)
    
    if not product:
        return {"error": "Producto no encontrado"}
    
    # 2. Actualizar producto
    db.update_rfx_product(rfx_id, product['id'], updates)
    
    # 3. Retornar producto actualizado
    return db.get_product_by_id(product['id'])
```

**Soluciona:** ERROR 3 (CRUD incompleto - UPDATE)

---

#### **Tool 6: `delete_product`** 🔴 CRÍTICA (Nueva)

**Propósito:** Eliminar producto del RFX

**Firma:**
```python
@tool
def delete_product(
    product_id: Optional[str] = None,
    product_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Elimina un producto del RFX.
    
    Args:
        product_id: ID del producto (si se conoce)
        product_name: Nombre del producto (si no se conoce ID)
    
    Returns:
        Confirmación de eliminación
        
    Ejemplo:
        Usuario: "Elimina las sillas"
        Agente: delete_product(product_name="Sillas")
    """
```

**Soluciona:** ERROR 3 (CRUD incompleto - DELETE)

---

#### **Tool 7: `modify_rfx_details`** 🟡 MEDIA (Nueva)

**Propósito:** Modificar detalles del RFX (fechas, ubicación, etc.)

**Firma:**
```python
@tool
def modify_rfx_details(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modifica detalles del RFX (no productos).
    
    Args:
        updates: Campos a actualizar
            {
                "event_location": "Hotel Marriott",
                "project_start_date": "2025-12-15",
                "event_city": "CDMX"
            }
    
    Returns:
        RFX actualizado
        
    Ejemplo:
        Usuario: "Cambia la ubicación a Hotel Marriott"
        Agente: modify_rfx_details({"event_location": "Hotel Marriott"})
    """
```

**Soluciona:** ERROR 3 (CRUD incompleto - Modificar RFX)

---

## 📋 RESUMEN DE TOOLS FASE 2

### **Prioridad CRÍTICA (Implementar primero)** 🔴

| Tool | Propósito | Soluciona Error |
|------|-----------|-----------------|
| `get_file_content` | Acceder a archivos previos | ERROR 1 |
| `get_rfx_data` | Consultar datos actuales | ERROR 2, ERROR 4 |
| `update_product` | Actualizar productos | ERROR 3 |
| `delete_product` | Eliminar productos | ERROR 3 |

### **Prioridad MEDIA (Implementar después)** 🟡

| Tool | Propósito |
|------|-----------|
| `modify_rfx_details` | Modificar detalles RFX |
| `add_products` (mejorar) | Validación mejorada |

### **Prioridad BAJA (Futuro)** 🟢

| Tool | Propósito |
|------|-----------|
| `search_catalog` | Buscar en catálogo |
| `calculate_totals` | Cálculos complejos |

---

## 🏗️ ARQUITECTURA FASE 2

### **Estructura de Archivos**

```
backend/services/langchain_tools/
├── __init__.py
├── file_tools.py          # get_file_content
├── rfx_tools.py           # get_rfx_data, modify_rfx_details
├── product_tools.py       # add_products, update_product, delete_product
└── catalog_tools.py       # search_catalog (futuro)
```

### **Integración con ChatAgent**

```python
# backend/services/chat_agent.py

from langchain.agents import create_openai_functions_agent, AgentExecutor
from backend.services.langchain_tools import (
    get_file_content,
    get_rfx_data,
    add_products,
    update_product,
    delete_product,
    modify_rfx_details
)

class ChatAgent:
    def __init__(self):
        self.llm = ChatOpenAI(...)
        
        # Definir tools
        self.tools = [
            get_file_content,
            get_rfx_data,
            add_products,
            update_product,
            delete_product,
            modify_rfx_details
        ]
        
        # Crear agente con tools
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Crear executor con memoria
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )
```

---

## 🎯 PLAN DE IMPLEMENTACIÓN FASE 2

### **Sprint 1: Tools Críticas de LECTURA** (3-4 días)

- [ ] Crear estructura `backend/services/langchain_tools/`
- [ ] Implementar `get_file_content`
- [ ] Implementar `get_rfx_data`
- [ ] Testing unitario de cada tool
- [ ] Testing integración con agente

### **Sprint 2: Tools Críticas de ESCRITURA** (3-4 días)

- [ ] Implementar `update_product`
- [ ] Implementar `delete_product`
- [ ] Mejorar `add_products` (convertir a tool)
- [ ] Testing CRUD completo

### **Sprint 3: Integración y Validación** (2-3 días)

- [ ] Integrar tools en `ChatAgent`
- [ ] Actualizar system prompt con instrucciones de tools
- [ ] Testing end-to-end
- [ ] Comparar con Fase 1

### **Sprint 4: Tools Opcionales** (2-3 días)

- [ ] Implementar `modify_rfx_details`
- [ ] Mejorar logging de decisiones de tools
- [ ] Documentación completa

---

## 📊 MÉTRICAS DE ÉXITO FASE 2

### **Funcionalidad**

- ✅ Conversaciones multi-turno con archivos funcionan
- ✅ Agente puede responder preguntas sobre datos actuales
- ✅ CRUD completo de productos funciona
- ✅ Validación de duplicados funciona

### **Performance**

- ⏱️ Latencia < 3 segundos por mensaje (con tools)
- 💰 Costo por conversación < $0.10 USD
- 🎯 Accuracy > 90% en decisiones de tools

### **Experiencia de Usuario**

- 😊 Usuario no necesita re-adjuntar archivos
- 😊 Usuario puede hacer correcciones conversacionales
- 😊 Agente detecta y previene duplicados

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS

1. **Revisar y aprobar este diseño**
2. **Crear issues/tasks en proyecto**
3. **Comenzar Sprint 1: Tools de LECTURA**

---

**Última actualización:** Diciembre 4, 2025  
**Autor:** AI Assistant  
**Status:** 📝 PROPUESTA PARA REVISIÓN
