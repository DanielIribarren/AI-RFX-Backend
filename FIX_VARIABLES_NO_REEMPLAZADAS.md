# 🔴 FIX: Variables NO Reemplazadas en HTML Generado

## Problema Identificado

**Fecha:** 2025-11-05  
**Gravedad:** ❌ CRÍTICO  

### Síntomas

El HTML generado por el Proposal Generator Agent contiene variables sin reemplazar:

```html
Cliente: {{CLIENT_NAME}}
Solicitud: {{SOLICITUD}}
{{PRODUCT_ROWS}}
TOTAL: {{TOTAL_AMOUNT}}
Fecha: {{CURRENT_DATE}}
Vigencia: {{VALIDITY_DATE}}
```

Además, el logo no se muestra (solo aparece el texto "[Logo]").

### Análisis de Logs

```
✅ HTML generated - Length: 6283 chars
❌ Validation complete - Issues: 2
🔄 Regenerating with 2 corrections
❌ Validation complete - Issues: 1
🔄 Regenerating with 1 corrections
❌ Validation complete - Issues: 1
⚠️ Validation still failing after 2 retries - proceeding with warnings
```

**Conclusión:** El Proposal Generator Agent NO está reemplazando las variables `{{VAR}}` como debería.

---

## Causa Raíz

### 1. Prompt Confuso

El prompt original usaba formato confuso con múltiples llaves:

```python
# ANTES (Confuso)
vars_text = "\n".join([f"- {{{{{key}}}}}: {value}" for key, value in variables.items()])

# Generaba:
- {{CLIENT_NAME}}: Empresa XYZ
- {{SOLICITUD}}: Descripción
```

El modelo se confundía con tantas llaves y no entendía claramente qué debía hacer.

### 2. Instrucciones No Explícitas

El prompt decía "REEMPLAZA SOLO las variables {{{{VAR}}}}" pero no daba ejemplos claros de CÓMO hacer el reemplazo.

### 3. System Message Genérico

El system message era demasiado genérico y no enfatizaba suficientemente la tarea de reemplazo.

---

## Solución Implementada

### 1. Prompt Mejorado con Ejemplos Claros

**Archivo:** `backend/services/ai_agents/proposal_generator_agent.py`

```python
# NUEVO FORMATO - Mucho más claro
vars_examples = []
for key, value in variables.items():
    vars_examples.append(f"   ENCUENTRA: {{{{{key}}}}}\n   REEMPLAZA CON: {value}")

vars_text = "\n\n".join(vars_examples)
```

**Genera:**
```
ENCUENTRA: {{CLIENT_NAME}}
REEMPLAZA CON: Empresa XYZ

ENCUENTRA: {{SOLICITUD}}
REEMPLAZA CON: Descripción del RFX
```

### 2. Instrucciones Paso a Paso

```markdown
## INSTRUCCIONES PASO A PASO:

1. Lee el template HTML completo de arriba
2. Busca CADA ocurrencia de texto entre llaves dobles (ejemplo: {{CLIENT_NAME}})
3. Reemplaza ese texto CON EL VALOR correspondiente de la lista de arriba
4. NO cambies NADA más: ni colores, ni estilos, ni estructura
5. Copia TODO el resto del HTML exactamente como está
```

### 3. Ejemplo Concreto de Reemplazo

```markdown
## EJEMPLO DE REEMPLAZO:

Si ves en el template:
   <div>Cliente: {{CLIENT_NAME}}</div>

Y el valor es:
   REEMPLAZA CON: Empresa XYZ

Debes generar:
   <div>Cliente: Empresa XYZ</div>
```

### 4. System Message Más Explícito

```python
"Eres un sistema automático de REEMPLAZO DE VARIABLES en HTML. Tu ÚNICA tarea es:
1. Buscar texto entre llaves dobles: {{VARIABLE}}
2. Reemplazar ese texto con el valor real que se te proporciona
3. Copiar TODO lo demás EXACTAMENTE como está
NO cambies colores, NO cambies estilos, NO agregues nada nuevo. SOLO reemplaza las variables."
```

### 5. Logs Detallados para Debugging

```python
# Log detallado de variables
logger.info(f"📋 Variables preparadas para reemplazo:")
for key, value in variables.items():
    logger.info(f"   - {{{{{key}}}}}: {value[:50]}")
```

---

## Archivos Modificados

**1. `/backend/services/ai_agents/proposal_generator_agent.py`**

- **Líneas 144-198:** Método `_build_prompt()` completamente reescrito
- **Líneas 99-126:** Método `_prepare_variables()` con logs detallados
- **Líneas 215-217:** System message mejorado

---

## Testing Recomendado

### Test 1: Verificar Variables en Logs

```bash
# Buscar en logs:
grep "Variables preparadas para reemplazo" logs.txt
```

**Esperado:**
```
📋 Variables preparadas para reemplazo:
   - {{CLIENT_NAME}}: Empresa XYZ
   - {{SOLICITUD}}: RFX para servicios
   - {{TOTAL_AMOUNT}}: $1,500.00
```

### Test 2: Generar Propuesta y Verificar HTML

```bash
# Generar propuesta vía API
POST /api/proposals/generate
{
  "rfx_id": "5a275a11-8bc9-4329-a7c8-a219ffbead1a"
}
```

**Esperado en HTML:**
```html
<div>Cliente: Empresa XYZ</div>
<div>Solicitud: RFX para servicios</div>
<div>TOTAL: $1,500.00</div>
```

**NO debe aparecer:**
```html
<div>Cliente: {{CLIENT_NAME}}</div>  ❌
<div>Solicitud: {{SOLICITUD}}</div>   ❌
```

### Test 3: Verificar Logo

El logo debe mostrarse como imagen, no como texto "[Logo]".

```html
<!-- Correcto ✅ -->
<img src="/api/branding/files/186ea35f-3cf8-480f-a7d3-0af178c09498/logo" alt="Logo">

<!-- Incorrecto ❌ -->
[Logo]
```

---

## Próximos Pasos

1. **Reiniciar servidor backend** para cargar cambios
2. **Generar nueva propuesta** y verificar que las variables se reemplazan
3. **Revisar logs** para confirmar que las variables se preparan correctamente
4. **Si el problema persiste:**
   - Verificar que el template en `company_branding_assets` tenga las variables correctamente
   - Aumentar `max_tokens` si el HTML es muy largo
   - Verificar conectividad con OpenAI

---

## Mejoras Futuras

1. **Validación Pre-Generación:**
   - Verificar que todas las variables del template existan en el diccionario
   - Alertar si hay variables sin valor

2. **Post-Procesamiento:**
   - Validar que NO queden variables sin reemplazar en el HTML final
   - Rechazar automáticamente si encuentra `{{VAR}}`

3. **Fallback Automático:**
   - Si el Generator falla 3 veces, usar reemplazo Python directo
   - `html.replace("{{VAR}}", value)`

---

## Estado

✅ **IMPLEMENTADO** - Esperando testing  
📅 **Fecha:** 2025-11-05  
👤 **Por:** Sistema AI Agents  

---

## Filosofía AI-First

Este fix mantiene el enfoque AI-first pero con instrucciones **MUCHO MÁS CLARAS** para el modelo:

- ✅ **Ejemplos concretos** de cómo hacer el reemplazo
- ✅ **Formato simplificado** sin confusión de llaves
- ✅ **Instrucciones paso a paso** fáciles de seguir
- ✅ **System message enfocado** en una sola tarea

El modelo es lo suficientemente inteligente, solo necesitaba **instrucciones más claras**.
