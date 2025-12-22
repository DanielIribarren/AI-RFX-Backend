# 🤖 Refactorización Chat Agent - Arquitectura Simplificada

**Fecha:** 4 de Diciembre, 2025  
**Inspiración:** Arquitectura TypeScript/NestJS (ejemplo proporcionado)

---

## 🎯 Problema Original

### 1. **El agente NO decidía cuándo usar tools**
```python
# ❌ ANTES: Construcción dinámica de prompts
prompt = f"""
# SOLICITUD DEL USUARIO
{message}

# CONTEXTO ACTUAL DEL RFX
## Productos Actuales:
{products_text}

Por favor responde en formato JSON con la estructura especificada.
"""
```

**Problemas:**
- El prompt pedía JSON pero las tools esperaban respuestas conversacionales
- Instrucciones contradictorias: "usa tools" vs "responde en JSON"
- El agente estaba confundido sobre su rol

### 2. **Respuestas hardcodeadas y no inteligentes**
```json
{
  "message": "Hola, actualmente no hay productos en el RFX...",
  "confidence": 0.95,
  "changes": [],
  "requires_confirmation": false
}
```

**Problema:** El agente NO consultaba `get_request_data_tool`, solo respondía con texto genérico.

### 3. **Múltiples prompts construidos dinámicamente**
- `CHAT_SYSTEM_PROMPT` (339 líneas)
- `_get_tools_instructions()` (instrucciones adicionales)
- `_format_input()` (contexto dinámico con productos)
- Reglas adicionales hardcodeadas

**Resultado:** Prompt gigante, confuso y contradictorio.

---

## ✅ Solución Implementada

### Arquitectura Simplificada (Estilo TypeScript/NestJS)

```
┌─────────────────────────────────────────┐
│  ChatAgent (Simplified)                 │
├─────────────────────────────────────────┤
│                                         │
│  1. Un solo system prompt inteligente   │
│  2. El agente decide cuándo usar tools  │
│  3. Streaming de respuestas             │
│  4. Sin construcción dinámica           │
│                                         │
└─────────────────────────────────────────┘
         │
         ├─► get_request_data_tool (consulta)
         ├─► add_products_tool (agregar)
         ├─► update_product_tool (modificar)
         ├─► delete_product_tool (eliminar)
         └─► modify_request_details_tool (detalles)
```

---

## 📝 Cambios Implementados

### 1. **System Prompt Unificado y Simple**

**Archivo:** `backend/prompts/chat_system_prompt.py`

**ANTES (339 líneas):**
- 20+ casos de uso detallados
- Instrucciones de formato JSON
- Reglas de decisión complejas
- Ejemplos de respuestas JSON

**DESPUÉS (161 líneas):**
```python
CHAT_SYSTEM_PROMPT = """Eres un asistente experto en gestión de RFX.

# TU ROL
Ayudas a usuarios a gestionar RFX mediante lenguaje natural conversacional.

**IMPORTANTE:** Tienes acceso a TOOLS. Úsalas cuando necesites información o realizar cambios.

# FILOSOFÍA DE TRABAJO
- **Consulta primero:** Si necesitas información, USA get_request_data_tool
- **Actúa después:** Usa las tools CRUD para hacer cambios
- **Sé conversacional:** Responde de forma natural, NO en JSON
- **Explica lo que haces:** Confirma cambios realizados

# REGLAS CRÍTICAS
## 1. Precios
- Si el usuario NO menciona precio, usa **0.00**
- NO inventes precios

## 2. Consultas vs Modificaciones
**CONSULTAS:** Usa get_request_data_tool, NO modifiques nada
**MODIFICACIONES:** Usa tools CRUD (add/update/delete)

# EJEMPLOS
Usuario: "Hola"
TÚ: [Usar get_request_data_tool("summary")]
TÚ: "¡Hola! 👋 Veo que aún no tienes productos. ¿Quieres agregar algunos?"
"""
```

**Beneficios:**
✅ Simple y directo  
✅ Confía en la inteligencia del agente  
✅ Ejemplos conversacionales, NO JSON  
✅ Instrucciones claras sobre cuándo usar tools  

### 2. **ChatAgent Simplificado**

**Archivo:** `backend/services/chat_agent.py`

#### **A. Prompt Simple (Sin Construcción Dinámica)**

**ANTES:**
```python
self.prompt = ChatPromptTemplate.from_messages([
    ("system", CHAT_SYSTEM_PROMPT),
    ("system", "⚠️ REGLA CRÍTICA: Si no se menciona precio, USA 0.00..."),
    ("system", self._get_tools_instructions()),  # ❌ Construcción dinámica
    ("system", """🎯 FLUJO DE TRABAJO:..."""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])
```

**DESPUÉS:**
```python
self.prompt = ChatPromptTemplate.from_messages([
    ("system", CHAT_SYSTEM_PROMPT),  # ✅ Solo system prompt
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])
```

#### **B. Streaming Execution (Estilo TypeScript)**

**ANTES:**
```python
# Ejecutar agent con ainvoke (sin streaming)
agent_result = await agent_with_history.ainvoke(
    {"input": self._format_input(message, context)},  # ❌ Construcción dinámica
    config={"configurable": {"session_id": rfx_id}}
)

agent_output = agent_result.get("output", "")
```

**DESPUÉS:**
```python
# ✅ Streaming (estilo TypeScript)
response_message = None
intermediate_steps = []

agent_input = {
    "input": f"{message}\n\n[CONTEXT: request_id={rfx_id}]"
}

async for step in agent_with_history.astream(
    agent_input,
    config={"configurable": {"session_id": rfx_id}}
):
    if "output" in step:
        response_message = step["output"]
        logger.info(f"🤖 Agent response: {response_message}")
    
    if "intermediate_steps" in step:
        intermediate_steps = step["intermediate_steps"]
```

**Beneficios:**
✅ Streaming para mejor UX  
✅ Captura respuesta final + tools usadas  
✅ Similar a ejemplo TypeScript proporcionado  

#### **C. Eliminada Construcción Dinámica de Contexto**

**ELIMINADO:**
```python
def _format_input(self, message: str, context: Dict[str, Any]) -> str:
    """❌ Construcción dinámica de prompt con productos"""
    products_text = ""
    for product in context.get("current_products", []):
        products_text += f"{product.get('nombre')}..."
    
    prompt = f"""
    # SOLICITUD DEL USUARIO
    {message}
    
    # CONTEXTO ACTUAL DEL RFX
    ## Productos Actuales:
    {products_text}
    
    Por favor responde en formato JSON...  # ❌ Contradictorio
    """
    return prompt
```

**RAZÓN:** El agente debe consultar `get_request_data_tool` cuando necesite información, NO recibir todo el contexto en el prompt.

#### **D. Nueva Función: Extraer Cambios de Tools**

**AGREGADO:**
```python
def _extract_changes_from_steps(self, intermediate_steps: List) -> List[Dict[str, Any]]:
    """
    Extrae cambios estructurados de las tools ejecutadas.
    
    Solo extrae de tools CRUD (no de get_request_data_tool)
    """
    changes = []
    
    for action, observation in intermediate_steps:
        tool_name = action.tool
        
        if tool_name in ["add_products_tool", "update_product_tool", 
                         "delete_product_tool", "modify_request_details_tool"]:
            tool_result = json.loads(observation) if isinstance(observation, str) else observation
            
            if tool_result.get("status") == "success":
                changes.append({
                    "type": tool_name.replace("_tool", ""),
                    "field": tool_input.get("product_id") or tool_input.get("request_id"),
                    "old_value": None,
                    "new_value": tool_input.get("updates") or tool_input.get("products"),
                    "confidence": 1.0
                })
    
    return changes
```

---

## 🔄 Flujo de Ejecución

### Ejemplo: Usuario dice "Hola"

**ANTES (Hardcoded):**
```
1. Usuario: "Hola"
2. ChatAgent: Construye prompt con contexto completo
3. LLM: Responde con JSON hardcodeado
4. Response: "Hola, actualmente no hay productos en el RFX..."
```

**DESPUÉS (Inteligente):**
```
1. Usuario: "Hola"
2. ChatAgent: Pasa mensaje simple al agente
3. Agente: "Necesito saber si hay productos"
4. Agente: Ejecuta get_request_data_tool("summary", request_id)
5. Tool: Retorna {"product_count": 0, "total": 0}
6. Agente: Razona con el resultado
7. Agente: Responde conversacionalmente
8. Response: "¡Hola! 👋 Veo que aún no tienes productos en este RFX. ¿Quieres que te ayude a agregar algunos?"
```

### Ejemplo: Usuario dice "Agrega 10 sillas"

**ANTES:**
```
1. Usuario: "Agrega 10 sillas"
2. ChatAgent: Construye prompt con productos actuales
3. LLM: Responde con JSON
4. Backend: Parsea JSON y ejecuta cambios
```

**DESPUÉS:**
```
1. Usuario: "Agrega 10 sillas"
2. Agente: "Necesito agregar producto"
3. Agente: Ejecuta add_products_tool(request_id, [{name: "Sillas", quantity: 10, price_unit: 0}])
4. Tool: Retorna {"status": "success", "product_id": "uuid"}
5. Agente: Responde conversacionalmente
6. Response: "✅ Agregué 10 sillas. Como no mencionaste el precio, lo dejé en $0. ¿Quieres que actualice el precio?"
```

---

## 📊 Comparación

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **System Prompt** | 339 líneas, complejo | 161 líneas, simple |
| **Construcción Dinámica** | Sí (contexto + productos) | No (solo mensaje) |
| **Formato Respuesta** | JSON hardcodeado | Conversacional |
| **Uso de Tools** | Confuso, contradictorio | Claro, el agente decide |
| **Streaming** | No (ainvoke) | Sí (astream) |
| **Inteligencia** | Limitada (respuestas genéricas) | Alta (consulta tools) |
| **Líneas de Código** | ~445 líneas | ~329 líneas |

---

## 🧪 Testing

### Casos de Prueba

#### 1. **Consulta Simple**
```
Input: "Hola"
Esperado: 
- Agente usa get_request_data_tool("summary")
- Responde conversacionalmente según resultado
- NO responde con JSON
```

#### 2. **Agregar Producto Sin Precio**
```
Input: "Agrega 20 servilletas"
Esperado:
- Agente usa add_products_tool con price_unit=0
- Responde confirmando y mencionando que precio es $0
- Pregunta si quiere actualizar precio
```

#### 3. **Consulta de Productos**
```
Input: "¿Qué productos tengo?"
Esperado:
- Agente usa get_request_data_tool("products")
- Lista productos de forma conversacional
- NO usa tools CRUD (solo consulta)
```

#### 4. **Modificar Producto**
```
Input: "Cambia las sillas a 15"
Esperado:
- Agente usa get_request_data_tool("products") para obtener product_id
- Agente usa update_product_tool(product_id, {quantity: 15})
- Responde confirmando cambio con antes → después
```

---

## 🚀 Próximos Pasos

### Fase 1: Testing ✅
- [ ] Probar consulta simple ("Hola")
- [ ] Probar agregar producto sin precio
- [ ] Probar modificar producto
- [ ] Probar eliminar producto
- [ ] Verificar que NO responde en JSON

### Fase 2: Optimizaciones
- [ ] Agregar retry logic para tools que fallen
- [ ] Implementar confirmaciones para acciones destructivas
- [ ] Mejorar detección de productos duplicados

### Fase 3: Métricas
- [ ] Tracking de tools usadas por request
- [ ] Latencia de streaming vs ainvoke
- [ ] Tasa de éxito de tools

---

## 📚 Referencias

### Ejemplo TypeScript/NestJS (Proporcionado)
```typescript
public async processMessage(threadId: string, message: string) {
    const config = { configurable: { thread_id: threadId } };
    
    const stream = await this.techSupportAgent.stream(
        { messages: [{ role: 'user', content: message }] },
        config,
    );
    
    let responseMessage = null;
    for await (const step of stream) {
        for (const update of Object.values(step)) {
            if (update && typeof update === 'object' && 'messages' in update) {
                const messages = (update as { messages: any[] }).messages;
                for (const message of messages) {
                    if (message.type === 'ai' && message.content && !responseMessage) {
                        responseMessage = message.content;
                    }
                }
            }
        }
    }
    
    return { response: responseMessage };
}
```

**Adaptación Python:**
```python
async for step in agent_with_history.astream(
    agent_input,
    config={"configurable": {"session_id": rfx_id}}
):
    if "output" in step:
        response_message = step["output"]
    
    if "intermediate_steps" in step:
        intermediate_steps = step["intermediate_steps"]
```

---

## ✅ Conclusión

### Problemas Resueltos

1. ✅ **El agente ahora decide cuándo usar tools** (no está hardcodeado)
2. ✅ **Respuestas inteligentes** (consulta datos reales, no genéricos)
3. ✅ **Un solo prompt simple** (eliminada construcción dinámica)
4. ✅ **Streaming** (mejor UX, similar a TypeScript)
5. ✅ **Conversacional** (NO responde en JSON)

### Filosofía AI-First

```
El agente es INTELIGENTE:
- Decide cuándo consultar datos
- Decide cuándo modificar
- Razona con resultados de tools
- Responde conversacionalmente

El backend solo EJECUTA:
- Provee tools
- Captura respuestas
- Retorna ChatResponse
```

---

**Estado:** ✅ IMPLEMENTADO Y LISTO PARA TESTING
