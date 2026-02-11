# 🧠 AI LEARNING SYSTEM - MVP REDESIGN

**Fecha:** 10 de Febrero, 2026  
**Filosofía:** KISS - Simple, Funcional, Efectivo  
**Objetivo:** Sistema de aprendizaje que realmente funcione en producción

---

## 📋 ANÁLISIS DEL SISTEMA ACTUAL

### ✅ **Lo que TENEMOS (Base de Datos):**

```sql
1. user_preferences          ← Preferencias aprendidas (pricing, productos, etc.)
2. learning_events           ← Historial de eventos de aprendizaje
3. price_corrections         ← Correcciones de precios
4. product_recommendations   ← Recomendaciones generadas
5. product_co_occurrences    ← Productos que van juntos
```

### ✅ **Lo que TENEMOS (Servicios):**

```python
1. learning_service.py       ← Guarda/lee preferencias
2. recommendation_service.py ← Genera recomendaciones
3. pricing_config_service_v2 ← Integración parcial con pricing
```

### ❌ **Lo que NO FUNCIONA:**

```
1. NO se guarda información cuando RFX se completa
2. NO hay agente que analice RFX exitosos
3. NO se aprende de productos usados
4. NO se aprende de precios finales
5. NO se detectan patrones de cliente
```

---

## 🎯 REDISEÑO MVP - ENFOQUE SIMPLE

### **Principio Central:**

```
UN AGENTE aprende cuando RFX se COMPLETA exitosamente
UN AGENTE consulta información aprendida cuando RFX se CREA
```

---

## 🔄 FLUJO COMPLETO DEL SISTEMA

### **FASE 1: CREACIÓN DE RFX (Consulta Aprendizaje)**

```
┌─────────────────────────────────────────────────────────────┐
│  👤 USUARIO CREA RFX                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  📄 RFX PROCESSOR (rfx_processor.py)                        │
│  - Extrae información del documento                         │
│  - Identifica: user_id, org_id, tipo_evento                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  🤖 AGENTE CONSULTOR (learning_query_agent.py) ← NUEVO     │
│                                                              │
│  Consulta información aprendida:                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. PRICING PREFERIDO                                 │  │
│  │    - ¿Qué % de coordinación usa normalmente?        │  │
│  │    - ¿Qué % de impuestos aplica?                    │  │
│  │    - ¿Usa costo por persona?                        │  │
│  │                                                       │  │
│  │ 2. PRODUCTOS FRECUENTES                              │  │
│  │    - ¿Qué productos usa en eventos tipo "catering"? │  │
│  │    - ¿Qué cantidades típicas?                       │  │
│  │                                                       │  │
│  │ 3. PRECIOS APRENDIDOS                                │  │
│  │    - ¿Cuál es el precio actual de "Tequeños"?       │  │
│  │    - ¿Ha cambiado recientemente?                    │  │
│  │                                                       │  │
│  │ 4. CLIENTES RECURRENTES                              │  │
│  │    - ¿Este cliente ya ha hecho pedidos antes?       │  │
│  │    - ¿Qué productos prefiere?                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Retorna: {                                                 │
│    "pricing_config": {...},                                 │
│    "suggested_products": [...],                             │
│    "learned_prices": {...},                                 │
│    "client_history": {...}                                  │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ SISTEMA APLICA INFORMACIÓN APRENDIDA                   │
│  - Pre-llena configuración de pricing                      │
│  - Sugiere productos frecuentes                            │
│  - Aplica precios aprendidos                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  👤 USUARIO TRABAJA EN RFX                                  │
│  - Modifica productos                                       │
│  - Ajusta precios                                           │
│  - Cambia configuración                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### **FASE 2: FINALIZACIÓN DE RFX (Aprendizaje)**

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ USUARIO FINALIZA RFX (Genera Propuesta)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  🤖 AGENTE DE APRENDIZAJE (learning_agent.py) ← NUEVO      │
│                                                              │
│  Se activa automáticamente cuando:                          │
│  - RFX cambia a estado "completed"                          │
│  - Se genera propuesta exitosamente                         │
│                                                              │
│  Analiza y aprende de:                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. CONFIGURACIÓN DE PRICING FINAL                    │  │
│  │    Query:                                             │  │
│  │    SELECT coordination_rate, tax_rate,               │  │
│  │           cost_per_person_enabled                    │  │
│  │    FROM rfx_pricing_configurations                   │  │
│  │    WHERE rfx_id = ? AND is_active = true             │  │
│  │                                                       │  │
│  │    Aprende:                                           │  │
│  │    - "Usuario prefiere coordinación 18%"             │  │
│  │    - "Usuario NO usa costo por persona"              │  │
│  │    - Guarda en user_preferences                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 2. PRODUCTOS UTILIZADOS                               │  │
│  │    Query:                                             │  │
│  │    SELECT product_name, quantity, unit_price,        │  │
│  │           unit_cost                                   │  │
│  │    FROM rfx_products                                  │  │
│  │    WHERE rfx_id = ?                                   │  │
│  │                                                       │  │
│  │    Aprende:                                           │  │
│  │    - "Tequeños se usa frecuentemente"                │  │
│  │    - "Precio actual: $3.50/unidad"                   │  │
│  │    - "Costo actual: $1.20/unidad"                    │  │
│  │    - Guarda en user_preferences (productos)          │  │
│  │    - Guarda en price_corrections (si cambió)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 3. CO-OCURRENCIAS DE PRODUCTOS                        │  │
│  │    Detecta:                                           │  │
│  │    - "Tequeños" + "Pasapalos" van juntos             │  │
│  │    - "Café" + "Torta" van juntos                     │  │
│  │                                                       │  │
│  │    Guarda en product_co_occurrences                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 4. INFORMACIÓN DEL CLIENTE                            │  │
│  │    Query:                                             │  │
│  │    SELECT company_name, contact_email                │  │
│  │    FROM companies WHERE id = ?                       │  │
│  │                                                       │  │
│  │    Aprende:                                           │  │
│  │    - "Corporación XYZ es cliente recurrente"         │  │
│  │    - "Prefiere eventos tipo 'catering'"              │  │
│  │    - Guarda en user_preferences (clientes)           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 5. MÁRGENES DE GANANCIA                               │  │
│  │    Calcula:                                           │  │
│  │    margen = (precio_final - costo_total) / precio   │  │
│  │                                                       │  │
│  │    Aprende:                                           │  │
│  │    - "Usuario prefiere margen 25%"                   │  │
│  │    - "Antes era 20%, ahora 25%"                      │  │
│  │    - Guarda en user_preferences (margins)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Registra evento en learning_events:                        │
│  {                                                           │
│    "event_type": "rfx_completed",                           │
│    "context": {                                              │
│      "rfx_id": "...",                                        │
│      "rfx_type": "catering",                                 │
│      "total_products": 8,                                    │
│      "total_amount": 1500.00                                 │
│    },                                                        │
│    "action_taken": {                                         │
│      "pricing_learned": true,                                │
│      "products_learned": 8,                                  │
│      "co_occurrences_detected": 12                           │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ ESTRUCTURA DE DATOS APRENDIDOS

### **1. Preferencias de Pricing**

```json
// Tabla: user_preferences
{
  "user_id": "186ea35f-...",
  "organization_id": "5237af2a-...",
  "preference_type": "pricing",
  "preference_key": "default_config",
  "preference_value": {
    "coordination_enabled": true,
    "coordination_rate": 0.18,
    "taxes_enabled": true,
    "tax_rate": 0.16,
    "cost_per_person_enabled": false,
    "margin_preference": 0.25  // ← NUEVO: Margen preferido
  },
  "usage_count": 15,  // Usado en 15 RFX
  "last_used_at": "2026-02-10T22:29:45Z"
}
```

### **2. Productos Frecuentes**

```json
// Tabla: user_preferences
{
  "user_id": "186ea35f-...",
  "organization_id": "5237af2a-...",
  "preference_type": "product",
  "preference_key": "frequent_products",
  "preference_value": {
    "products": [
      {
        "name": "Tequeños",
        "frequency": 12,  // Usado en 12 RFX
        "avg_quantity": 150,
        "last_price": 3.50,
        "last_cost": 1.20,
        "price_updated_at": "2026-02-10T22:29:45Z"
      },
      {
        "name": "Pasapalos Variados",
        "frequency": 10,
        "avg_quantity": 200,
        "last_price": 2.80,
        "last_cost": 0.90,
        "price_updated_at": "2026-02-08T15:30:00Z"
      }
    ]
  },
  "usage_count": 12,
  "last_used_at": "2026-02-10T22:29:45Z"
}
```

### **3. Clientes Recurrentes**

```json
// Tabla: user_preferences
{
  "user_id": "186ea35f-...",
  "organization_id": "5237af2a-...",
  "preference_type": "client",
  "preference_key": "recurrent_clients",
  "preference_value": {
    "clients": [
      {
        "company_name": "Corporación XYZ",
        "company_id": "abc-123",
        "rfx_count": 5,
        "preferred_event_types": ["catering", "corporate_event"],
        "avg_budget": 2500.00,
        "preferred_products": ["Tequeños", "Café", "Torta"],
        "last_rfx_date": "2026-02-10T22:29:45Z"
      }
    ]
  },
  "usage_count": 5,
  "last_used_at": "2026-02-10T22:29:45Z"
}
```

### **4. Co-ocurrencias de Productos**

```json
// Tabla: product_co_occurrences
{
  "organization_id": "5237af2a-...",
  "product_a": "Café",
  "product_b": "Torta",
  "co_occurrence_count": 8,  // Usados juntos 8 veces
  "confidence": 0.85,  // 85% de confianza
  "first_seen_at": "2026-01-15T10:00:00Z",
  "last_seen_at": "2026-02-10T22:29:45Z"
}
```

### **5. Historial de Correcciones de Precio**

```json
// Tabla: price_corrections
{
  "user_id": "186ea35f-...",
  "organization_id": "5237af2a-...",
  "product_name": "Tequeños",
  "original_price": 3.00,
  "corrected_price": 3.50,
  "price_difference": 0.50,  // +$0.50
  "rfx_id": "795b284d-...",
  "quantity": 150,
  "context": {
    "reason": "price_increase",
    "event_type": "catering",
    "date": "2026-02-10"
  },
  "created_at": "2026-02-10T22:29:45Z"
}
```

---

## 🛠️ IMPLEMENTACIÓN MVP

### **Tablas a MANTENER (5 tablas):**

```
✅ user_preferences          ← Almacena TODO (pricing, productos, clientes, márgenes)
✅ learning_events           ← Historial de aprendizaje
✅ price_corrections         ← Correcciones de precios
✅ product_co_occurrences    ← Productos que van juntos
❌ product_recommendations   ← ELIMINAR (no se usa en MVP)
```

### **Servicios a CREAR/MODIFICAR:**

```python
1. learning_agent.py              ← NUEVO: Aprende cuando RFX se completa
2. learning_query_agent.py        ← NUEVO: Consulta info aprendida
3. learning_service.py            ← MODIFICAR: Simplificar métodos
4. recommendation_service.py      ← ELIMINAR: No se usa en MVP
5. rfx_processor.py               ← MODIFICAR: Integrar learning_query_agent
6. proposal_generator.py          ← MODIFICAR: Trigger learning_agent al finalizar
```

---

## 📊 DIAGRAMA DE FLUJO DETALLADO

### **MOMENTO 1: Usuario Crea RFX**

```
┌──────────────────────────────────────────────────────────────┐
│ POST /api/rfx/process                                        │
│ - user_id: "186ea35f-..."                                    │
│ - organization_id: "5237af2a-..."                            │
│ - file: documento.pdf                                        │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ rfx_processor.process_rfx_case()                             │
│ 1. Extrae información del PDF                                │
│ 2. Identifica tipo de evento: "catering"                     │
│ 3. Crea RFX en base de datos                                 │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 🤖 learning_query_agent.get_learned_context()               │
│                                                               │
│ Consulta 1: Pricing preferido                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT preference_value                                 │ │
│ │ FROM user_preferences                                   │ │
│ │ WHERE user_id = '186ea35f-...'                          │ │
│ │   AND preference_type = 'pricing'                       │ │
│ │ ORDER BY usage_count DESC LIMIT 1                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Resultado: coordination_rate = 0.18, taxes = 0.16           │
│                                                               │
│ Consulta 2: Productos frecuentes para "catering"             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT preference_value                                 │ │
│ │ FROM user_preferences                                   │ │
│ │ WHERE user_id = '186ea35f-...'                          │ │
│ │   AND preference_type = 'product'                       │ │
│ │   AND preference_value->>'event_type' = 'catering'      │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Resultado: ["Tequeños", "Pasapalos", "Café"]                │
│                                                               │
│ Consulta 3: Precios actuales                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT product_name, corrected_price                    │ │
│ │ FROM price_corrections                                  │ │
│ │ WHERE user_id = '186ea35f-...'                          │ │
│ │   AND product_name IN ('Tequeños', 'Pasapalos')        │ │
│ │ ORDER BY created_at DESC                                │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Resultado: Tequeños = $3.50, Pasapalos = $2.80              │
│                                                               │
│ Retorna contexto aprendido:                                  │
│ {                                                             │
│   "pricing": {                                                │
│     "coordination_rate": 0.18,                                │
│     "tax_rate": 0.16,                                         │
│     "cost_per_person_enabled": false                          │
│   },                                                          │
│   "suggested_products": [                                     │
│     {"name": "Tequeños", "price": 3.50, "cost": 1.20},       │
│     {"name": "Pasapalos", "price": 2.80, "cost": 0.90}       │
│   ],                                                          │
│   "confidence": 0.92                                          │
│ }                                                             │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ pricing_config_service_v2._create_default_configuration()    │
│ - Usa pricing aprendido para pre-llenar                      │
│ - Guarda configuración en BD                                 │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ ✅ RFX Creado con información aprendida                      │
│ - Pricing pre-configurado                                    │
│ - Productos sugeridos disponibles                            │
└──────────────────────────────────────────────────────────────┘
```

---

### **MOMENTO 2: Usuario Finaliza RFX**

```
┌──────────────────────────────────────────────────────────────┐
│ POST /api/proposals/generate                                 │
│ - rfx_id: "795b284d-..."                                     │
│ - user_id: "186ea35f-..."                                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ proposal_generator.generate_proposal()                       │
│ 1. Genera HTML de propuesta                                  │
│ 2. Convierte a PDF                                            │
│ 3. Guarda en base de datos                                   │
│ 4. Marca RFX como "completed"                                │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 🤖 learning_agent.learn_from_completed_rfx()                │
│                                                               │
│ Paso 1: Obtener datos del RFX                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT r.*, pc.*, cpp.*, coord.*, tax.*                 │ │
│ │ FROM rfx_v2 r                                            │ │
│ │ LEFT JOIN rfx_pricing_configurations pc                 │ │
│ │   ON r.id = pc.rfx_id AND pc.is_active = true           │ │
│ │ LEFT JOIN cost_per_person_configurations cpp            │ │
│ │   ON pc.id = cpp.pricing_config_id                      │ │
│ │ LEFT JOIN coordination_configurations coord             │ │
│ │   ON pc.id = coord.pricing_config_id                    │ │
│ │ LEFT JOIN tax_configurations tax                        │ │
│ │   ON pc.id = tax.pricing_config_id                      │ │
│ │ WHERE r.id = '795b284d-...'                              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Paso 2: Aprender configuración de pricing                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ INSERT INTO user_preferences (...)                      │ │
│ │ VALUES (                                                 │ │
│ │   user_id = '186ea35f-...',                             │ │
│ │   preference_type = 'pricing',                          │ │
│ │   preference_value = {                                  │ │
│ │     "coordination_enabled": true,                       │ │
│ │     "coordination_rate": 0.18,                          │ │
│ │     "cost_per_person_enabled": false                    │ │
│ │   }                                                      │ │
│ │ )                                                        │ │
│ │ ON CONFLICT (user_id, preference_type, preference_key)  │ │
│ │ DO UPDATE SET usage_count = usage_count + 1             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Paso 3: Obtener productos del RFX                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SELECT product_name, quantity, unit_price, unit_cost    │ │
│ │ FROM rfx_products                                        │ │
│ │ WHERE rfx_id = '795b284d-...'                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Resultado: 8 productos                                       │
│                                                               │
│ Paso 4: Aprender productos frecuentes                        │
│ Para cada producto:                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ - Obtener preferencia actual de productos               │ │
│ │ - Incrementar frecuencia del producto                   │ │
│ │ - Actualizar precio/costo si cambió                     │ │
│ │ - Guardar en user_preferences                           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Paso 5: Detectar cambios de precio                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Si precio actual != precio anterior:                    │ │
│ │   INSERT INTO price_corrections (...)                   │ │
│ │   VALUES (                                               │ │
│ │     product_name = 'Tequeños',                          │ │
│ │     original_price = 3.00,                              │ │
│ │     corrected_price = 3.50,                             │ │
│ │     price_difference = 0.50                             │ │
│ │   )                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Paso 6: Detectar co-ocurrencias                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Para cada par de productos (A, B):                      │ │
│ │   CALL register_product_co_occurrence(                  │ │
│ │     org_id, 'Tequeños', 'Pasapalos'                     │ │
│ │   )                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ Paso 7: Registrar evento de aprendizaje                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ INSERT INTO learning_events (...)                       │ │
│ │ VALUES (                                                 │ │
│ │   event_type = 'rfx_completed',                         │ │
│ │   context = {                                            │ │
│ │     "rfx_type": "catering",                             │ │
│ │     "total_products": 8,                                │ │
│ │     "total_amount": 1500.00                             │ │
│ │   },                                                     │ │
│ │   action_taken = {                                       │ │
│ │     "pricing_learned": true,                            │ │
│ │     "products_learned": 8,                              │ │
│ │     "price_corrections": 2,                             │ │
│ │     "co_occurrences": 12                                │ │
│ │   }                                                      │ │
│ │ )                                                        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ✅ Aprendizaje completado                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 CASOS DE USO REALES

### **Caso 1: Empresa de Catering - Aprendizaje de Precios**

```
Situación Inicial:
- Precio helado: $1.00/unidad
- Usuario crea 5 RFX con helado a $1.00

Cambio de Precio:
- Proveedor sube precio
- Usuario crea RFX #6 con helado a $3.00
- Sistema detecta cambio y guarda en price_corrections

Próximo RFX:
- Usuario crea RFX #7
- Sistema sugiere helado a $3.00 (precio aprendido)
- Usuario acepta → Sistema incrementa confianza
```

### **Caso 2: Empresa de Catering - Margen de Ganancia**

```
Situación Inicial:
- Usuario aplica margen 20% en primeros 10 RFX

Cambio de Estrategia:
- Usuario decide aumentar margen a 25%
- Modifica pricing en próximos 5 RFX

Sistema Aprende:
- Detecta patrón: últimos 5 RFX usan 25%
- Actualiza preferencia de margen
- Próximo RFX pre-llena con 25%
```

### **Caso 3: Productos Recurrentes**

```
Cliente: Corporación XYZ
Historial:
- RFX #1: Tequeños, Pasapalos, Café
- RFX #2: Tequeños, Pasapalos, Torta
- RFX #3: Tequeños, Café, Torta

Sistema Aprende:
- "Tequeños" aparece en 100% de RFX (confianza 1.0)
- "Tequeños" + "Café" van juntos (confianza 0.67)
- Cantidad promedio Tequeños: 150 unidades

Próximo RFX para Corporación XYZ:
- Sistema sugiere: Tequeños (150 unidades)
- Si usuario agrega Tequeños → sugiere Café
```

---

## 📝 RESUMEN DE CAMBIOS NECESARIOS

### **Base de Datos:**

```sql
-- ELIMINAR tabla no usada
DROP TABLE product_recommendations;

-- MANTENER tablas útiles
✅ user_preferences
✅ learning_events
✅ price_corrections
✅ product_co_occurrences
```

### **Servicios a CREAR:**

```python
1. backend/services/ai_agents/learning_agent.py
   - learn_from_completed_rfx(rfx_id, user_id, org_id)
   - _learn_pricing_config(rfx_id)
   - _learn_products(rfx_id)
   - _detect_price_changes(rfx_id)
   - _detect_co_occurrences(rfx_id)

2. backend/services/ai_agents/learning_query_agent.py
   - get_learned_context(user_id, org_id, rfx_type)
   - get_pricing_preference(user_id)
   - get_frequent_products(user_id, rfx_type)
   - get_learned_prices(user_id, product_names)
   - get_client_history(user_id, company_name)
```

### **Servicios a MODIFICAR:**

```python
1. backend/services/rfx_processor.py
   - Integrar learning_query_agent al crear RFX
   - Pasar contexto aprendido a pricing_config_service

2. backend/services/proposal_generator.py
   - Trigger learning_agent después de generar propuesta
   - Marcar RFX como "completed"

3. backend/services/learning_service.py
   - Simplificar métodos
   - Eliminar código no usado
```

### **Servicios a ELIMINAR:**

```python
❌ backend/services/recommendation_service.py
❌ backend/api/recommendations.py
```

---

## ✅ PRÓXIMOS PASOS

1. **Revisar y aprobar diseño** ← ESTAMOS AQUÍ
2. **Eliminar tabla product_recommendations**
3. **Crear learning_agent.py**
4. **Crear learning_query_agent.py**
5. **Modificar rfx_processor.py**
6. **Modificar proposal_generator.py**
7. **Simplificar learning_service.py**
8. **Eliminar recommendation_service.py**
9. **Probar flujo completo**
10. **Documentar casos de uso**

---

## 🎯 CRITERIOS DE ÉXITO

```
✅ Usuario crea RFX → Sistema pre-llena con info aprendida
✅ Usuario modifica precio → Sistema detecta y guarda cambio
✅ Usuario finaliza RFX → Sistema aprende automáticamente
✅ Próximo RFX → Sistema aplica aprendizaje anterior
✅ Todo funciona sin intervención manual
✅ Código simple y mantenible (< 500 líneas por agente)
```
