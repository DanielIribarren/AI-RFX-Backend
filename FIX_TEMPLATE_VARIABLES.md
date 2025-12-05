# 🔧 Fix: Template Variables en Docstrings de Tools

**Fecha:** 4 de Diciembre, 2025  
**Error:** `KeyError: "Input to ChatPromptTemplate is missing variables {'name', 'quantity'}"`

---

## 🔴 Problema

LangChain detectaba `{name}` y `{quantity}` en los docstrings de las tools como **variables del template** en lugar de ejemplos de JSON.

### Error Completo:
```
KeyError: "Input to ChatPromptTemplate is missing variables {'name', 'quantity'}.
Expected: ['agent_scratchpad', 'history', 'input', 'name', 'quantity']
Received: ['input', 'history', 'intermediate_steps', 'agent_scratchpad']"
```

### Causa Raíz:

Cuando usas `create_openai_functions_agent`, LangChain:
1. Lee los docstrings de todas las tools
2. Los incluye en el prompt del agente
3. **Parsea el texto buscando variables con formato `{variable}`**
4. Intenta inyectar esas variables en el template

**Problema:** Los ejemplos JSON en los docstrings tenían llaves simples `{...}` que LangChain interpretaba como variables del template.

---

## ✅ Solución

**Escapar las llaves en los docstrings** usando doble llave `{{...}}` para que LangChain las trate como texto literal.

### Archivos Modificados:

#### 1. `backend/services/tools/add_products_tool.py`

**ANTES:**
```python
"""
Ejemplo:
[
    {
        "name": "Sillas",
        "quantity": 10,
        "price_unit": 150.0
    }
]
"""
```

**DESPUÉS:**
```python
"""
Ejemplo:
[
    {{
        "name": "Sillas",
        "quantity": 10,
        "price_unit": 150.0
    }}
]
"""
```

#### 2. `backend/services/tools/update_product_tool.py`

**ANTES:**
```python
"""
Ejemplo:
{
    "quantity": 20,
    "price_unit": 200.0
}
"""
```

**DESPUÉS:**
```python
"""
Ejemplo:
{{
    "quantity": 20,
    "price_unit": 200.0
}}
"""
```

#### 3. `backend/services/tools/get_request_data_tool.py`

**ANTES:**
```python
"""
Para "products":
{
    "products": [
        {
            "id": "uuid",
            "name": "Sillas",
            "quantity": 10
        }
    ]
}
"""
```

**DESPUÉS:**
```python
"""
Para "products":
{{
    "products": [
        {{
            "id": "uuid",
            "name": "Sillas",
            "quantity": 10
        }}
    ]
}}
"""
```

---

## 📝 Regla General

**Cuando escribas docstrings para LangChain tools:**

✅ **Usa doble llave `{{...}}` para ejemplos JSON**
```python
"""
Ejemplo:
{{
    "field": "value"
}}
"""
```

❌ **NO uses llave simple `{...}` en docstrings**
```python
"""
Ejemplo:
{
    "field": "value"  # ← LangChain lo interpreta como variable
}
"""
```

---

## 🧪 Testing

Después del fix, el agente debería inicializar correctamente:

```bash
# Logs esperados:
2025-12-04 17:54:34,139 - backend.services.chat_agent - INFO - 🦜 ChatAgent initialized with LangChain + 5 tools

# Sin errores de KeyError
```

---

## 🔍 Por Qué Pasó Esto

LangChain usa `ChatPromptTemplate` que:
1. Parsea strings buscando variables con formato `{variable}`
2. Espera que esas variables sean pasadas al invocar el template
3. Los docstrings de las tools se incluyen en el prompt del agente
4. Por lo tanto, cualquier `{...}` en los docstrings se interpreta como variable

**Solución:** Escapar con doble llave `{{...}}` para que se trate como texto literal.

---

## ✅ Estado

**IMPLEMENTADO** - Todas las tools actualizadas con doble llave en ejemplos JSON.

**Archivos afectados:**
- ✅ `add_products_tool.py`
- ✅ `update_product_tool.py`
- ✅ `get_request_data_tool.py`
- ⚠️ Verificar `delete_product_tool.py` y `modify_request_details_tool.py` si tienen ejemplos JSON

---

## 📚 Referencias

- [LangChain ChatPromptTemplate](https://python.langchain.com/docs/modules/model_io/prompts/prompt_templates/)
- [Python String Formatting - Escaping Braces](https://docs.python.org/3/library/string.html#format-string-syntax)
