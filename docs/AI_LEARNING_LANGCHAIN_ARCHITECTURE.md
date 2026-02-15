# 🧠 AI LEARNING SYSTEM - ARQUITECTURA LANGCHAIN

**Fecha:** 10 de Febrero, 2026  
**Filosofía:** Agentes inteligentes con Tools específicas  
**Framework:** LangChain + OpenAI Function Calling  

---

## 🎯 ANÁLISIS CRÍTICO DEL PROBLEMA

### **¿Por qué LangChain?**

```
PROBLEMA: Aprendizaje complejo con múltiples fuentes de datos
├─ Necesitamos consultar múltiples tablas
├─ Necesitamos tomar decisiones inteligentes
├─ Necesitamos manejar errores y reintentos
└─ Necesitamos razonamiento sobre qué aprender

SOLUCIÓN: LangChain Agents con Tools
├─ Agent decide QUÉ tool usar según contexto
├─ Tools encapsulan lógica de BD
├─ Function Calling para precisión
└─ State management automático
```

### **Riesgos de Aprendizaje Incorrecto:**

```
❌ RIESGO 1: Aprender de RFX incompletos (por eso solo se va a llamar al agente cada vez que el usuario finalice un rfx)
   → Solución: Solo aprender de RFX con status "completed"

❌ RIESGO 2: Sobrescribir preferencias válidas con errores
   → Solución: Confidence scores y validación antes de guardar

❌ RIESGO 3: Aprender de datos corruptos
   → Solución: Validación estricta con Pydantic

❌ RIESGO 4: No detectar cambios reales de precio
   → Solución: Threshold mínimo (>5% diferencia)

❌ RIESGO 5: Recomendar productos obsoletos
   → Solución: Decay temporal (productos viejos pierden peso)
```

---

## 🏗️ ARQUITECTURA COMPLETA

### **Componentes del Sistema:**

```
┌─────────────────────────────────────────────────────────────┐
│                    LANGCHAIN ECOSYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  🤖 LEARNING AGENT (Aprende al finalizar RFX)     │    │
│  │                                                     │    │
│  │  LLM: GPT-4o                                       │    │
│  │  Type: OpenAI Functions Agent                      │    │
│  │  Memory: ConversationBufferMemory                  │    │
│  │                                                     │    │
│  │  Tools disponibles:                                │    │
│  │  ├─ get_rfx_final_data                            │    │
│  │  ├─ get_pricing_configuration                     │    │
│  │  ├─ get_rfx_products                              │    │
│  │  ├─ get_previous_prices                           │    │
│  │  ├─ save_pricing_preference                       │    │
│  │  ├─ save_product_usage                            │    │
│  │  ├─ save_price_correction                         │    │
│  │  ├─ save_co_occurrence                            │    │
│  │  └─ log_learning_event                            │    │
│  │                                                     │    │
│  │  Prompt:                                           │    │
│  │  "Eres un experto en análisis de presupuestos.    │    │
│  │   Analiza el RFX completado y aprende patrones    │    │
│  │   para mejorar futuras recomendaciones."          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  🔍 QUERY AGENT (Consulta al crear RFX)           │    │
│  │                                                     │    │
│  │  LLM: GPT-4o-mini (más rápido, más barato)        │    │
│  │  Type: OpenAI Functions Agent                      │    │
│  │  Memory: None (stateless)                          │    │
│  │                                                     │    │
│  │  Tools disponibles:                                │    │
│  │  ├─ get_pricing_preference                        │    │
│  │  ├─ get_frequent_products                         │    │
│  │  ├─ get_learned_prices                            │    │
│  │  ├─ get_client_history                            │    │
│  │  ├─ get_co_occurrences                            │    │
│  │  └─ calculate_confidence                          │    │
│  │                                                     │    │
│  │  Prompt:                                           │    │
│  │  "Eres un asistente que consulta preferencias     │    │
│  │   aprendidas para pre-configurar RFX."            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    TOOLS LAYER                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📚 READ TOOLS (Solo lectura, sin efectos secundarios)      │
│  ├─ GetRFXFinalDataTool                                     │
│  ├─ GetPricingConfigurationTool                             │
│  ├─ GetRFXProductsTool                                      │
│  ├─ GetPreviousPricesTool                                   │
│  ├─ GetPricingPreferenceTool                                │
│  ├─ GetFrequentProductsTool                                 │
│  ├─ GetLearnedPricesTool                                    │
│  ├─ GetClientHistoryTool                                    │
│  └─ GetCoOccurrencesTool                                    │
│                                                              │
│  ✍️ WRITE TOOLS (Modifican BD, requieren validación)        │
│  ├─ SavePricingPreferenceTool                               │
│  ├─ SaveProductUsageTool                                    │
│  ├─ SavePriceCorrectionTool                                 │
│  ├─ SaveCoOccurrenceTool                                    │
│  └─ LogLearningEventTool                                    │
│                                                              │
│  🧮 COMPUTE TOOLS (Cálculos y análisis)                     │
│  ├─ CalculateConfidenceTool                                 │
│  ├─ DetectPriceChangeTool                                   │
│  └─ AnalyzeProductPatternsTool                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🗄️ BASE DE DATOS (Supabase PostgreSQL)                    │
│  ├─ user_preferences (preferencias aprendidas)              │
│  ├─ learning_events (historial de aprendizaje)              │
│  ├─ price_corrections (correcciones de precios)             │
│  └─ product_co_occurrences (productos relacionados)         │
│                                                              │
│  ❌ ELIMINAR:                                                │
│  └─ product_recommendations (no se usa en MVP)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 DISEÑO DE TOOLS (LangChain)

### **Estructura Base de una Tool:**

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GetPricingPreferenceInput(BaseModel):
    """Input schema para GetPricingPreferenceTool"""
    user_id: str = Field(..., description="UUID del usuario")
    organization_id: str = Field(..., description="UUID de la organización")
    rfx_type: Optional[str] = Field(None, description="Tipo de RFX (catering, corporate_event, etc.)")

class GetPricingPreferenceTool(BaseTool):
    name = "get_pricing_preference"
    description = """
    Obtiene la configuración de pricing preferida por el usuario.
    
    Retorna:
    - coordination_enabled: bool
    - coordination_rate: float (0.0-1.0)
    - taxes_enabled: bool
    - tax_rate: float (0.0-1.0)
    - cost_per_person_enabled: bool
    - confidence: float (0.0-1.0)
    - usage_count: int
    
    Usa esta tool cuando necesites saber qué configuración de pricing
    prefiere el usuario para pre-llenar un nuevo RFX.
    """
    args_schema = GetPricingPreferenceInput
    
    def _run(self, user_id: str, organization_id: str, rfx_type: Optional[str] = None) -> Dict[str, Any]:
        """Ejecuta la consulta a la base de datos"""
        # Implementación real
        pass
    
    async def _arun(self, *args, **kwargs):
        """Versión async (opcional)"""
        raise NotImplementedError("Async not implemented")
```

---

## 📊 TOOLS DETALLADAS

### **READ TOOLS (9 tools):**

#### **1. GetRFXFinalDataTool**
```python
Input:
  - rfx_id: str

Output:
  {
    "rfx_id": "uuid",
    "user_id": "uuid",
    "organization_id": "uuid",
    "rfx_type": "catering",
    "status": "completed",
    "total_amount": 1500.00,
    "created_at": "2026-02-10T22:29:43Z",
    "completed_at": "2026-02-10T23:15:00Z"
  }

Uso: Obtener datos básicos del RFX para contexto
```

#### **2. GetPricingConfigurationTool**
```python
Input:
  - rfx_id: str

Output:
  {
    "coordination_enabled": true,
    "coordination_rate": 0.18,
    "taxes_enabled": true,
    "tax_rate": 0.16,
    "cost_per_person_enabled": false,
    "headcount": 120
  }

Uso: Obtener configuración de pricing final del RFX
```

#### **3. GetRFXProductsTool**
```python
Input:
  - rfx_id: str

Output:
  [
    {
      "product_name": "Tequeños",
      "quantity": 150,
      "unit_price": 3.50,
      "unit_cost": 1.20,
      "total": 525.00
    },
    ...
  ]

Uso: Obtener lista de productos usados en el RFX
```

#### **4. GetPreviousPricesTool**
```python
Input:
  - user_id: str
  - product_names: List[str]

Output:
  {
    "Tequeños": {
      "last_price": 3.00,
      "last_cost": 1.10,
      "last_used": "2026-02-05T10:00:00Z",
      "usage_count": 12
    },
    ...
  }

Uso: Comparar precios actuales con históricos para detectar cambios
```

#### **5. GetPricingPreferenceTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - rfx_type: Optional[str]

Output:
  {
    "coordination_enabled": true,
    "coordination_rate": 0.18,
    "taxes_enabled": true,
    "tax_rate": 0.16,
    "cost_per_person_enabled": false,
    "confidence": 0.92,
    "usage_count": 15,
    "last_used": "2026-02-10T22:29:45Z"
  }

Uso: Consultar preferencia de pricing aprendida
```

#### **6. GetFrequentProductsTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - rfx_type: Optional[str]
  - limit: int = 10

Output:
  [
    {
      "product_name": "Tequeños",
      "frequency": 12,
      "avg_quantity": 150,
      "last_price": 3.50,
      "last_cost": 1.20,
      "confidence": 0.95
    },
    ...
  ]

Uso: Obtener productos que el usuario usa frecuentemente
```

#### **7. GetLearnedPricesTool**
```python
Input:
  - user_id: str
  - product_names: List[str]

Output:
  {
    "Tequeños": {
      "learned_price": 3.50,
      "learned_cost": 1.20,
      "confidence": 0.88,
      "last_updated": "2026-02-10T22:29:45Z",
      "correction_count": 3
    },
    ...
  }

Uso: Obtener precios aprendidos de productos específicos
```

#### **8. GetClientHistoryTool**
```python
Input:
  - user_id: str
  - company_name: str

Output:
  {
    "company_name": "Corporación XYZ",
    "rfx_count": 5,
    "preferred_event_types": ["catering", "corporate_event"],
    "avg_budget": 2500.00,
    "preferred_products": ["Tequeños", "Café", "Torta"],
    "last_rfx_date": "2026-02-10T22:29:45Z"
  }

Uso: Obtener historial de un cliente recurrente
```

#### **9. GetCoOccurrencesTool**
```python
Input:
  - organization_id: str
  - product_name: str
  - min_confidence: float = 0.5

Output:
  [
    {
      "product_a": "Tequeños",
      "product_b": "Café",
      "co_occurrence_count": 8,
      "confidence": 0.85
    },
    ...
  ]

Uso: Obtener productos que frecuentemente van juntos
```

---

### **WRITE TOOLS (5 tools):**

#### **1. SavePricingPreferenceTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - pricing_config: Dict[str, Any]
  - rfx_type: Optional[str]

Validaciones:
  ✓ coordination_rate entre 0.0 y 1.0
  ✓ tax_rate entre 0.0 y 1.0
  ✓ Todos los campos requeridos presentes

Output:
  {
    "success": true,
    "preference_id": "uuid",
    "usage_count": 16
  }

Uso: Guardar configuración de pricing como preferencia
```

#### **2. SaveProductUsageTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - product_name: str
  - quantity: int
  - unit_price: float
  - unit_cost: float
  - rfx_type: Optional[str]

Validaciones:
  ✓ quantity > 0
  ✓ unit_price >= 0
  ✓ unit_cost >= 0
  ✓ product_name no vacío

Output:
  {
    "success": true,
    "frequency": 13,
    "avg_quantity": 145
  }

Uso: Registrar uso de un producto
```

#### **3. SavePriceCorrectionTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - product_name: str
  - original_price: float
  - corrected_price: float
  - rfx_id: str

Validaciones:
  ✓ Diferencia > 5% (evitar ruido)
  ✓ Precios > 0
  ✓ Cambio real (no guardar si es igual)

Output:
  {
    "success": true,
    "correction_id": "uuid",
    "price_difference": 0.50,
    "percentage_change": 16.67
  }

Uso: Registrar corrección de precio
```

#### **4. SaveCoOccurrenceTool**
```python
Input:
  - organization_id: str
  - product_a: str
  - product_b: str

Validaciones:
  ✓ Productos diferentes
  ✓ Nombres no vacíos
  ✓ Orden alfabético automático

Output:
  {
    "success": true,
    "co_occurrence_count": 9,
    "confidence": 0.87
  }

Uso: Registrar que dos productos se usaron juntos
```

#### **5. LogLearningEventTool**
```python
Input:
  - user_id: str
  - organization_id: str
  - event_type: str
  - rfx_id: str
  - context: Dict[str, Any]
  - action_taken: Dict[str, Any]

Output:
  {
    "success": true,
    "event_id": "uuid",
    "timestamp": "2026-02-10T23:15:00Z"
  }

Uso: Registrar evento de aprendizaje en historial
```

---

### **COMPUTE TOOLS (3 tools):**

#### **1. CalculateConfidenceTool**
```python
Input:
  - usage_count: int
  - last_used_days_ago: int
  - total_rfx_count: int

Algorithm:
  base_confidence = min(usage_count / 10, 1.0)  # Max 1.0 con 10+ usos
  decay_factor = max(0.5, 1.0 - (last_used_days_ago / 365))  # Decay anual
  confidence = base_confidence * decay_factor

Output:
  {
    "confidence": 0.85,
    "reason": "Used 12 times, last used 5 days ago"
  }

Uso: Calcular confianza de una preferencia
```

#### **2. DetectPriceChangeTool**
```python
Input:
  - product_name: str
  - current_price: float
  - previous_price: float
  - threshold: float = 0.05  # 5%

Algorithm:
  diff = abs(current_price - previous_price)
  percentage = diff / previous_price
  is_significant = percentage > threshold

Output:
  {
    "changed": true,
    "difference": 0.50,
    "percentage": 16.67,
    "direction": "increase"
  }

Uso: Detectar si un cambio de precio es significativo
```

#### **3. AnalyzeProductPatternsTool**
```python
Input:
  - products: List[str]
  - organization_id: str

Algorithm:
  1. Obtener co-ocurrencias de cada par
  2. Calcular confidence promedio
  3. Identificar productos "hub" (muchas relaciones)

Output:
  {
    "hub_products": ["Tequeños", "Café"],
    "strong_pairs": [
      {"a": "Tequeños", "b": "Café", "confidence": 0.85}
    ],
    "suggestions": ["Agregar Torta (va bien con Café)"]
  }

Uso: Analizar patrones de productos
```

---

## 🤖 LEARNING AGENT - DISEÑO DETALLADO

### **Prompt del Agent:**

```python
LEARNING_AGENT_PROMPT = """
Eres un experto analista de presupuestos y preferencias de usuario.

Tu tarea es analizar un RFX completado y aprender patrones para mejorar 
futuras recomendaciones.

CONTEXTO:
- RFX ID: {rfx_id}
- Usuario: {user_id}
- Organización: {organization_id}

PROCESO DE APRENDIZAJE:

1. OBTENER DATOS DEL RFX:
   - Usa get_rfx_final_data para obtener información básica
   - Verifica que el RFX esté en status "completed"
   - Si no está completado, NO aprendas nada

2. APRENDER CONFIGURACIÓN DE PRICING:
   - Usa get_pricing_configuration para obtener config final
   - Compara con preferencias anteriores (get_pricing_preference)
   - Si es consistente (3+ veces), guarda como preferencia (save_pricing_preference)
   - Calcula confidence con calculate_confidence

3. APRENDER PRODUCTOS:
   - Usa get_rfx_products para obtener lista de productos
   - Para cada producto:
     a) Obtén precio anterior (get_previous_prices)
     b) Detecta cambio significativo (detect_price_change)
     c) Si cambió >5%, guarda corrección (save_price_correction)
     d) Registra uso del producto (save_product_usage)

4. DETECTAR CO-OCURRENCIAS:
   - Para cada par de productos en el RFX:
     a) Guarda co-ocurrencia (save_co_occurrence)
   - Usa analyze_product_patterns para identificar patrones

5. REGISTRAR EVENTO:
   - Usa log_learning_event para registrar todo lo aprendido

REGLAS CRÍTICAS:
❌ NO aprendas de RFX incompletos
❌ NO sobrescribas preferencias sin validar
❌ NO guardes cambios de precio <5%
❌ NO asumas, siempre usa las tools para consultar
✅ SIEMPRE valida datos antes de guardar
✅ SIEMPRE calcula confidence scores
✅ SIEMPRE registra el evento de aprendizaje

Piensa paso a paso y usa las tools disponibles.
"""
```

### **Flujo de Ejecución:**

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# 1. Crear LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 2. Crear tools
tools = [
    GetRFXFinalDataTool(),
    GetPricingConfigurationTool(),
    GetRFXProductsTool(),
    GetPreviousPricesTool(),
    GetPricingPreferenceTool(),
    SavePricingPreferenceTool(),
    SaveProductUsageTool(),
    SavePriceCorrectionTool(),
    SaveCoOccurrenceTool(),
    LogLearningEventTool(),
    CalculateConfidenceTool(),
    DetectPriceChangeTool(),
    AnalyzeProductPatternsTool()
]

# 3. Crear prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", LEARNING_AGENT_PROMPT),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# 4. Crear agent
agent = create_openai_functions_agent(llm, tools, prompt)

# 5. Crear executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=15,  # Límite de iteraciones
    handle_parsing_errors=True
)

# 6. Ejecutar
result = agent_executor.invoke({
    "input": f"Aprende del RFX {rfx_id} que acaba de completarse",
    "rfx_id": rfx_id,
    "user_id": user_id,
    "organization_id": organization_id
})
```

---

## 🔍 QUERY AGENT - DISEÑO DETALLADO

### **Prompt del Agent:**

```python
QUERY_AGENT_PROMPT = """
Eres un asistente inteligente que consulta preferencias aprendidas 
para pre-configurar nuevos RFX.

Tu tarea es obtener la mejor configuración posible basada en el 
historial del usuario.

CONTEXTO:
- Usuario: {user_id}
- Organización: {organization_id}
- Tipo de RFX: {rfx_type}

PROCESO DE CONSULTA:

1. OBTENER PREFERENCIAS DE PRICING:
   - Usa get_pricing_preference
   - Si confidence > 0.7, usa esa configuración
   - Si no hay preferencias, retorna defaults

2. OBTENER PRODUCTOS FRECUENTES:
   - Usa get_frequent_products
   - Filtra por rfx_type si está disponible
   - Ordena por confidence

3. OBTENER PRECIOS APRENDIDOS:
   - Para cada producto frecuente:
     a) Usa get_learned_prices
     b) Verifica que sea reciente (<30 días)

4. CALCULAR CONFIDENCE GENERAL:
   - Usa calculate_confidence para cada elemento
   - Retorna confidence promedio

REGLAS:
✅ SIEMPRE retorna algo (aunque sea defaults)
✅ SIEMPRE incluye confidence scores
✅ SIEMPRE ordena por relevancia
❌ NO inventes datos
❌ NO uses datos muy antiguos (>90 días)

Retorna un objeto JSON con toda la información.
"""
```

### **Output Esperado:**

```json
{
  "pricing": {
    "coordination_enabled": true,
    "coordination_rate": 0.18,
    "taxes_enabled": true,
    "tax_rate": 0.16,
    "cost_per_person_enabled": false,
    "confidence": 0.92,
    "source": "learned"
  },
  "suggested_products": [
    {
      "product_name": "Tequeños",
      "suggested_quantity": 150,
      "learned_price": 3.50,
      "learned_cost": 1.20,
      "confidence": 0.95,
      "frequency": 12
    },
    {
      "product_name": "Pasapalos Variados",
      "suggested_quantity": 200,
      "learned_price": 2.80,
      "learned_cost": 0.90,
      "confidence": 0.88,
      "frequency": 10
    }
  ],
  "co_occurrences": [
    {
      "if_user_adds": "Tequeños",
      "suggest": "Café",
      "confidence": 0.85
    }
  ],
  "overall_confidence": 0.91
}
```

---

## 🗄️ LIMPIEZA DE BASE DE DATOS

### **Tabla a ELIMINAR:**

```sql
-- Esta tabla no se usa en el MVP
DROP TABLE IF EXISTS product_recommendations CASCADE;
```

### **Tablas a MANTENER (4):**

```sql
✅ user_preferences          -- Almacena TODO (pricing, productos, clientes)
✅ learning_events           -- Historial de aprendizaje
✅ price_corrections         -- Correcciones de precios
✅ product_co_occurrences    -- Productos relacionados
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
backend/
├── services/
│   ├── ai_agents/
│   │   ├── __init__.py
│   │   ├── learning_agent.py              ← NUEVO: Agent que aprende
│   │   ├── query_agent.py                 ← NUEVO: Agent que consulta
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── read_tools.py              ← NUEVO: 9 read tools
│   │       ├── write_tools.py             ← NUEVO: 5 write tools
│   │       └── compute_tools.py           ← NUEVO: 3 compute tools
│   │
│   ├── learning_service.py                ← SIMPLIFICAR: Solo helpers
│   └── recommendation_service.py          ← ELIMINAR
│
├── api/
│   └── recommendations.py                 ← ELIMINAR
│
└── models/
    └── learning_models.py                 ← NUEVO: Pydantic schemas
```

---

## 🔄 INTEGRACIÓN CON SERVICIOS EXISTENTES

### **1. rfx_processor.py - Al crear RFX:**

```python
from backend.services.ai_agents.query_agent import query_agent

def process_rfx_case(...):
    # ... código existente ...
    
    # 🤖 Consultar información aprendida
    learned_context = query_agent.get_learned_context(
        user_id=user_id,
        organization_id=org_id,
        rfx_type=rfx_type
    )
    
    # Pasar contexto a pricing_config_service
    pricing_config = pricing_service.create_config_with_learned_data(
        rfx_id=rfx_id,
        learned_context=learned_context
    )
    
    # ... resto del código ...
```

### **2. proposal_generator.py - Al finalizar RFX:**

```python
from backend.services.ai_agents.learning_agent import learning_agent

def generate_proposal(...):
    # ... generar propuesta ...
    
    # Marcar RFX como completado
    db.update_rfx_status(rfx_id, "completed")
    
    # 🤖 Trigger aprendizaje
    learning_result = learning_agent.learn_from_completed_rfx(
        rfx_id=rfx_id,
        user_id=user_id,
        organization_id=org_id
    )
    
    logger.info(f"🧠 Learning completed: {learning_result}")
    
    return proposal
```

---

## 🧪 VALIDACIÓN Y TESTING

### **Tests Críticos:**

```python
# 1. Test: No aprender de RFX incompletos
def test_learning_agent_rejects_incomplete_rfx():
    result = learning_agent.learn_from_completed_rfx(
        rfx_id="incomplete-rfx-id",
        user_id="user-123",
        organization_id="org-456"
    )
    assert result["success"] == False
    assert "not completed" in result["reason"]

# 2. Test: No guardar cambios de precio insignificantes
def test_price_correction_threshold():
    tool = SavePriceCorrectionTool()
    result = tool._run(
        user_id="user-123",
        organization_id="org-456",
        product_name="Tequeños",
        original_price=3.00,
        corrected_price=3.10,  # Solo 3.3% cambio
        rfx_id="rfx-789"
    )
    assert result["success"] == False
    assert "below threshold" in result["reason"]

# 3. Test: Confidence decay temporal
def test_confidence_decay():
    tool = CalculateConfidenceTool()
    
    # Reciente (5 días)
    recent = tool._run(usage_count=10, last_used_days_ago=5, total_rfx_count=15)
    
    # Antiguo (180 días)
    old = tool._run(usage_count=10, last_used_days_ago=180, total_rfx_count=15)
    
    assert recent["confidence"] > old["confidence"]

# 4. Test: Query agent retorna defaults si no hay datos
def test_query_agent_defaults():
    result = query_agent.get_learned_context(
        user_id="new-user",
        organization_id="org-456",
        rfx_type="catering"
    )
    assert result["pricing"]["source"] == "default"
    assert result["overall_confidence"] < 0.5
```

---

## 📊 MÉTRICAS Y MONITOREO

### **Métricas Clave:**

```python
# 1. Tasa de aprendizaje exitoso
learning_success_rate = successful_learnings / total_rfx_completed

# 2. Confidence promedio de recomendaciones
avg_confidence = sum(all_confidences) / len(all_confidences)

# 3. Tasa de aceptación de recomendaciones
acceptance_rate = accepted_recommendations / total_recommendations

# 4. Tiempo de ejecución de agents
avg_learning_time = sum(learning_times) / len(learning_times)
avg_query_time = sum(query_times) / len(query_times)

# 5. Errores de agents
agent_error_rate = agent_errors / total_agent_calls
```

---

## ✅ CRITERIOS DE ÉXITO

```
✅ Learning Agent completa en <10 segundos
✅ Query Agent completa en <3 segundos
✅ Confidence scores > 0.7 para preferencias usadas 5+ veces
✅ 0% de aprendizaje de RFX incompletos
✅ 0% de guardado de cambios de precio <5%
✅ 100% de validación con Pydantic antes de guardar
✅ Logs detallados de cada decisión del agent
✅ Manejo robusto de errores y reintentos
```

---

## 🚀 PRÓXIMOS PASOS

1. ✅ **Aprobar arquitectura** ← ESTAMOS AQUÍ
2. Eliminar tabla `product_recommendations`
3. Crear modelos Pydantic (`learning_models.py`)
4. Implementar 17 tools (read + write + compute)
5. Implementar Learning Agent con LangChain
6. Implementar Query Agent con LangChain
7. Integrar con `rfx_processor.py`
8. Integrar con `proposal_generator.py`
9. Testing exhaustivo
10. Documentación de casos de uso

---

**¿Apruebas esta arquitectura con LangChain?**
