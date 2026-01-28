# 🔧 FIX: Configuraciones de Pricing en Generación de Presupuestos

**Fecha:** 27 de Enero, 2026  
**Problema:** Configuraciones de coordinación, logística, impuestos y costo por persona no se respetaban consistentemente en todos los agentes  
**Solución:** Documentación clara y lógica condicional en TODOS los agentes

---

## 📋 RESUMEN EJECUTIVO

### ✅ **Verificación Completada - 4 Puntos**

#### **1. ¿El Prompt Tiene Claro las Configuraciones?**
✅ **SÍ** - El prompt principal ya tenía instrucciones claras sobre pricing condicional:

**Archivo:** `backend/services/prompts/proposal_prompts.py`
```python
5. **PRICING CONDICIONAL:**
   - Coordinación: {'MOSTRAR' if show_coordination else 'NO MOSTRAR (omitir completamente)'}
   - Impuestos: {'MOSTRAR' if show_tax else 'NO MOSTRAR (omitir completamente)'}
   - Costo por persona: {'MOSTRAR' if show_cost_per_person else 'NO MOSTRAR (omitir completamente)'}
```

#### **2. ¿Se Proporciona como Contexto?**
✅ **SÍ** - El servicio principal ya formateaba y pasaba los flags correctamente:

**Archivo:** `backend/services/proposal_generator.py`
```python
def _format_pricing_data(self, pricing_calculation, currency, rfx_id):
    # ✅ LÓGICA INTELIGENTE: Solo mostrar si está ACTIVO Y tiene valor > 0
    show_coordination = coordination_enabled and coordination > 0
    show_tax = taxes_enabled and tax > 0
    show_cost_per_person = cost_per_person_enabled and cost_per_person > 0
    
    return {
        'show_coordination': show_coordination,
        'show_tax': show_tax,
        'show_cost_per_person': show_cost_per_person,
        # ... valores formateados
    }
```

#### **3. ¿Los Agentes Respetan las Configuraciones?**
⚠️ **PROBLEMA IDENTIFICADO Y CORREGIDO**

**Antes:** Los agentes AI no validaban los flags `show_coordination`, `show_tax`, `show_cost_per_person`

**Después:** Todos los agentes ahora tienen documentación clara y lógica condicional

#### **4. ¿Se Llama al Endpoint de Configuración?**
✅ **SÍ** - El endpoint ya se llamaba correctamente:

```python
pricing_calculation = unified_budget_service.calculate_with_unified_config(
    proposal_request.rfx_id, subtotal
)
```

---

## 🔧 CAMBIOS IMPLEMENTADOS

### **1. Agente Generador (proposal_generator_agent.py)**

**Cambio:** Agregada lógica condicional para respetar flags de pricing

**Antes:**
```python
html = html.replace("{{COORDINATION}}", pricing.get('coordination_formatted', '$0.00'))
html = html.replace("{{TAX}}", pricing.get('tax_formatted', '$0.00'))
```

**Después:**
```python
# ✅ PRICING CONDICIONAL: Usar flags para mostrar/ocultar filas
show_coordination = pricing.get('show_coordination', False)
show_tax = pricing.get('show_tax', False)
show_cost_per_person = pricing.get('show_cost_per_person', False)

# Reemplazos condicionales (solo si están activos)
if show_coordination:
    html = html.replace("{{COORDINATION}}", pricing.get('coordination_formatted', '$0.00'))
    logger.info(f"✅ Coordination enabled: {pricing.get('coordination_formatted')}")
else:
    html = html.replace("{{COORDINATION}}", "")
    logger.info("⚠️ Coordination disabled - omitting from template")

if show_tax:
    html = html.replace("{{TAX}}", pricing.get('tax_formatted', '$0.00'))
    logger.info(f"✅ Tax enabled: {pricing.get('tax_formatted')}")
else:
    html = html.replace("{{TAX}}", "")
    logger.info("⚠️ Tax disabled - omitting from template")

if show_cost_per_person:
    html = html.replace("{{COST_PER_PERSON}}", pricing.get('cost_per_person_formatted', '$0.00'))
    logger.info(f"✅ Cost per person enabled: {pricing.get('cost_per_person_formatted')}")
else:
    html = html.replace("{{COST_PER_PERSON}}", "")
    logger.info("⚠️ Cost per person disabled - omitting from template")
```

**Beneficio:** El agente ahora respeta las configuraciones activas y omite las desactivadas

---

### **2. Agente Validador (template_validator_agent.py)**

**Cambio:** Agregada documentación completa sobre pricing condicional en el system prompt

**Agregado:**
```python
### 🚨 CONFIGURACIONES DE PRICING CONDICIONAL (CRÍTICO):
**REGLA FUNDAMENTAL:** Solo mostrar filas de pricing si están ACTIVAS en la configuración.

El request_data.pricing contiene flags que indican qué mostrar:
- **show_coordination**: Si True → Mostrar fila "Coordinación y Logística"
- **show_tax**: Si True → Mostrar fila "Impuestos"  
- **show_cost_per_person**: Si True → Mostrar fila "Costo por persona"

**VALIDACIÓN OBLIGATORIA:**
1. Si show_coordination = False → NO debe existir fila de coordinación en el HTML
2. Si show_tax = False → NO debe existir fila de impuestos en el HTML
3. Si show_cost_per_person = False → NO debe existir fila de costo por persona en el HTML

**CORRECCIÓN AUTOMÁTICA:**
- Si encuentras una fila de coordinación pero show_coordination = False → ELIMINAR la fila
- Si encuentras una fila de impuestos pero show_tax = False → ELIMINAR la fila
- Si encuentras una fila de costo por persona pero show_cost_per_person = False → ELIMINAR la fila

**⚠️ NUNCA AGREGUES FILAS DE PRICING QUE NO ESTÉN ACTIVAS**
```

**Beneficio:** El agente validador ahora corrige automáticamente cualquier inconsistencia con las configuraciones

---

### **3. Agente Optimizador PDF (pdf_optimizer_agent.py)**

**Cambio:** Agregada documentación clara sobre NO modificar filas de pricing

**Agregado:**
```python
### 4. 🚨 CONFIGURACIONES DE PRICING CONDICIONAL (CRÍTICO - NO MODIFICAR):
**REGLA FUNDAMENTAL:** NO agregar ni eliminar filas de pricing. Solo optimizar las que YA existen.

El HTML que recibes ya tiene las filas de pricing correctas según la configuración:
- Si hay fila de "Coordinación y Logística" → Está activa, NO eliminar
- Si NO hay fila de coordinación → NO está activa, NO agregar
- Si hay fila de "Impuestos" → Está activa, NO eliminar
- Si NO hay fila de impuestos → NO está activa, NO agregar

**TU RESPONSABILIDAD:**
- Solo optimizar el CSS y paginación de las filas existentes
- NO agregar filas de pricing que no existen
- NO eliminar filas de pricing que existen
- NO modificar valores de pricing
- NO inventar configuraciones
```

**Beneficio:** El agente optimizador ahora preserva las configuraciones correctas sin modificarlas

---

## 🎯 FLUJO COMPLETO DE CONFIGURACIONES

```
┌─────────────────────────────────────────────────────────────────┐
│                  FLUJO DE PRICING CONFIGURATION                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. USUARIO CONFIGURA PRICING                                   │
│     ├─ Coordinación: ON (18%)                                   │
│     ├─ Impuestos: OFF                                           │
│     └─ Costo por persona: OFF                                   │
│                                                                  │
│  2. ENDPOINT CALCULA PRICING                                    │
│     unified_budget_service.calculate_with_unified_config()      │
│     ├─ coordination_enabled: True                               │
│     ├─ coordination_amount: $150.00                             │
│     ├─ taxes_enabled: False                                     │
│     └─ cost_per_person_enabled: False                           │
│                                                                  │
│  3. SERVICIO FORMATEA CON FLAGS                                 │
│     _format_pricing_data()                                      │
│     ├─ show_coordination: True (enabled=True, amount>0)         │
│     ├─ show_tax: False (enabled=False)                          │
│     └─ show_cost_per_person: False (enabled=False)              │
│                                                                  │
│  4. AGENTE GENERADOR APLICA FLAGS                               │
│     proposal_generator_agent.generate()                         │
│     ├─ Reemplaza {{COORDINATION}} con "$150.00"                 │
│     ├─ Reemplaza {{TAX}} con "" (vacío)                         │
│     └─ Reemplaza {{COST_PER_PERSON}} con "" (vacío)             │
│                                                                  │
│  5. AGENTE VALIDADOR VERIFICA                                   │
│     template_validator_agent.validate()                         │
│     ├─ Verifica que NO exista fila de impuestos                 │
│     ├─ Verifica que NO exista fila de costo por persona         │
│     └─ Si encuentra filas incorrectas → ELIMINA                 │
│                                                                  │
│  6. AGENTE OPTIMIZADOR PRESERVA                                 │
│     pdf_optimizer_agent.optimize()                              │
│     ├─ Optimiza CSS de filas existentes                         │
│     ├─ NO agrega filas de pricing                               │
│     └─ NO elimina filas de pricing                              │
│                                                                  │
│  7. RESULTADO FINAL                                             │
│     ✅ HTML con SOLO coordinación (activa)                      │
│     ✅ SIN impuestos (desactivados)                             │
│     ✅ SIN costo por persona (desactivado)                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 ARCHIVOS MODIFICADOS

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `backend/services/ai_agents/proposal_generator_agent.py` | Lógica condicional para flags | 145-178 |
| `backend/services/ai_agents/template_validator_agent.py` | Documentación pricing condicional | 159-192 |
| `backend/services/ai_agents/pdf_optimizer_agent.py` | Documentación NO modificar pricing | 133-159 |

---

## ✅ VALIDACIÓN

### **Escenario 1: Coordinación Activa, Impuestos Desactivados**

**Configuración:**
- `coordination_enabled: True`
- `taxes_enabled: False`

**Resultado Esperado:**
```html
<tr><td>Subtotal</td><td>$1,000.00</td></tr>
<tr><td>Coordinación y Logística</td><td>$180.00</td></tr>
<tr><td>TOTAL</td><td>$1,180.00</td></tr>
<!-- NO debe existir fila de impuestos -->
```

**Logs Esperados:**
```
✅ Coordination enabled: $180.00
⚠️ Tax disabled - omitting from template
```

---

### **Escenario 2: Todo Desactivado**

**Configuración:**
- `coordination_enabled: False`
- `taxes_enabled: False`
- `cost_per_person_enabled: False`

**Resultado Esperado:**
```html
<tr><td>Subtotal</td><td>$1,000.00</td></tr>
<tr><td>TOTAL</td><td>$1,000.00</td></tr>
<!-- NO debe existir ninguna fila adicional -->
```

**Logs Esperados:**
```
⚠️ Coordination disabled - omitting from template
⚠️ Tax disabled - omitting from template
⚠️ Cost per person disabled - omitting from template
```

---

### **Escenario 3: Todo Activado**

**Configuración:**
- `coordination_enabled: True`
- `taxes_enabled: True`
- `cost_per_person_enabled: True`

**Resultado Esperado:**
```html
<tr><td>Subtotal</td><td>$1,000.00</td></tr>
<tr><td>Coordinación y Logística</td><td>$180.00</td></tr>
<tr><td>Impuestos</td><td>$160.00</td></tr>
<tr><td>TOTAL</td><td>$1,340.00</td></tr>
<tr><td>Costo por persona</td><td>$13.40</td></tr>
```

**Logs Esperados:**
```
✅ Coordination enabled: $180.00
✅ Tax enabled: $160.00
✅ Cost per person enabled: $13.40
```

---

## 🎯 BENEFICIOS

1. ✅ **Consistencia Total:** Todos los agentes respetan las mismas configuraciones
2. ✅ **Logs Claros:** Se registra qué configuraciones están activas/desactivadas
3. ✅ **Validación Automática:** El agente validador corrige inconsistencias
4. ✅ **Preservación:** El agente optimizador no modifica configuraciones
5. ✅ **Mantenibilidad:** Documentación clara en cada agente

---

## 🚀 PRÓXIMOS PASOS

1. **Testing:** Probar los 3 escenarios de validación
2. **Monitoreo:** Revisar logs para verificar que los flags se respetan
3. **Ajustes:** Si se detectan inconsistencias, ajustar la lógica condicional

---

**Estado:** ✅ IMPLEMENTADO Y DOCUMENTADO
**Requiere:** Testing en ambiente de desarrollo
