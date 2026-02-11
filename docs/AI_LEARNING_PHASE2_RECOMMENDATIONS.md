# 🎯 AI Learning System - FASE 2: Recomendaciones

**Fecha:** 10 de Febrero, 2026  
**Estado:** ✅ COMPLETADA  
**Filosofía:** KISS - Recomendaciones simples y efectivas

---

## 📦 **SERVICIO IMPLEMENTADO**

### **`recommendation_service.py`** - 400 líneas

Servicio de recomendaciones inteligentes basado en aprendizaje del usuario.

---

## 🎯 **MÉTODOS PRINCIPALES**

### **1. Recomendaciones de Productos**

#### **`recommend_products_for_rfx(user_id, org_id, rfx_context, limit=5)`**

**Qué hace:**
- Recomienda productos para un nuevo RFX
- Combina productos frecuentes + productos relacionados
- Considera contexto del RFX

**Algoritmo:**
```python
1. Obtener productos frecuentes del usuario (usage_count DESC)
2. Calcular confidence = 0.5 + (usage_count * 0.05), max 0.9
3. Si hay productos existentes en RFX:
   - Buscar productos relacionados (co-occurrence)
   - Agregar con confidence 0.7
4. Ordenar por confidence DESC
5. Retornar top N
```

**Retorna:**
```python
[
    {
        'product_name': 'Tequeños',
        'confidence': 0.85,
        'reason': 'frequently_used',
        'usage_count': 7
    },
    {
        'product_name': 'Empanadas',
        'confidence': 0.7,
        'reason': 'co_occurrence',
        'related_to': 'Tequeños'
    }
]
```

---

#### **`save_recommendation_feedback(user_id, product_name, was_accepted, ...)`**

**Qué hace:**
- Guarda si el usuario aceptó o rechazó una recomendación
- Permite medir efectividad del sistema

**Uso:**
```python
# Usuario acepta recomendación
recommendation_service.save_recommendation_feedback(
    user_id="abc-123",
    organization_id="org-456",
    product_name="Tequeños",
    was_accepted=True,
    confidence_score=0.85,
    reason='frequently_used'
)
```

---

#### **`get_recommendation_stats(org_id, days=30)`**

**Qué hace:**
- Calcula estadísticas de recomendaciones
- Mide tasa de aceptación
- Identifica productos más aceptados

**Retorna:**
```python
{
    'total_recommendations': 150,
    'accepted': 105,
    'rejected': 45,
    'acceptance_rate': 70.0,
    'top_accepted_products': [
        {'product': 'Tequeños', 'count': 25},
        {'product': 'Empanadas', 'count': 18}
    ]
}
```

---

### **2. Recomendaciones de Pricing**

#### **`recommend_pricing_config(user_id, rfx_type=None)`**

**Qué hace:**
- Recomienda configuración de pricing
- Usa preferencia del usuario si existe
- Fallback a defaults por tipo de RFX

**Algoritmo:**
```python
1. Buscar preferencia guardada del usuario
   - Si existe → retornar con confidence 0.9
2. Si no existe, usar default por tipo de RFX:
   - catering → coordination 18%, tax 16%, per_person ON
   - events → coordination 20%, tax 16%, per_person ON
   - supplies → coordination OFF, tax 16%, per_person OFF
3. Retornar con confidence 0.5
```

**Retorna:**
```python
{
    'coordination_enabled': True,
    'coordination_rate': 0.18,
    'taxes_enabled': True,
    'tax_rate': 0.16,
    'cost_per_person_enabled': True,
    'confidence': 0.9,
    'source': 'user_preference'
}
```

---

#### **`recommend_price_for_product(user_id, product_name, quantity, fallback)`**

**Qué hace:**
- Recomienda precio para un producto específico
- Basado en correcciones previas del usuario
- Considera cantidad similar (±20%)

**Algoritmo:**
```python
1. Buscar correcciones previas del producto
   - Filtrar por cantidad similar (±20%)
   - Ordenar por fecha DESC
2. Si encuentra:
   - Contar total de correcciones
   - confidence = 0.6 + (count * 0.1), max 0.95
   - Retornar precio corregido
3. Si no encuentra:
   - Usar fallback_price con confidence 0.3
```

**Retorna:**
```python
{
    'recommended_price': 0.68,
    'confidence': 0.8,
    'source': 'learned_from_corrections',
    'based_on_corrections': 3
}
```

---

### **3. Recomendaciones Completas**

#### **`recommend_for_new_rfx(user_id, org_id, rfx_type, existing_products)`**

**Qué hace:**
- Genera todas las recomendaciones para un nuevo RFX
- Combina pricing + productos en una sola llamada

**Retorna:**
```python
{
    'pricing_config': {
        'coordination_enabled': True,
        'coordination_rate': 0.18,
        'confidence': 0.9
    },
    'recommended_products': [
        {'product_name': 'Tequeños', 'confidence': 0.85},
        {'product_name': 'Empanadas', 'confidence': 0.7}
    ],
    'timestamp': '2026-02-10T21:57:00Z'
}
```

---

## 🔄 **FLUJOS DE USO**

### **Flujo 1: Crear Nuevo RFX con Recomendaciones**

```python
# 1. Usuario inicia creación de RFX
rfx_type = "catering"

# 2. Sistema pide recomendaciones
recommendations = recommendation_service.recommend_for_new_rfx(
    user_id=current_user_id,
    organization_id=current_org_id,
    rfx_type=rfx_type
)

# 3. Frontend muestra:
# - Configuración de pricing pre-llenada
# - Sugerencias de productos frecuentes
# - Productos relacionados si ya agregó algunos

# 4. Usuario acepta/rechaza productos
for product in recommendations['recommended_products']:
    if user_accepts(product):
        recommendation_service.save_recommendation_feedback(
            user_id=current_user_id,
            organization_id=current_org_id,
            product_name=product['product_name'],
            was_accepted=True,
            confidence_score=product['confidence']
        )
```

---

### **Flujo 2: Sugerir Precio al Agregar Producto**

```python
# 1. Usuario agrega producto "Tequeños" (cantidad: 200)
product_name = "Tequeños"
quantity = 200
catalog_price = 0.80

# 2. Sistema busca precio aprendido
price_rec = recommendation_service.recommend_price_for_product(
    user_id=current_user_id,
    product_name=product_name,
    quantity=quantity,
    fallback_price=catalog_price
)

# 3. Si hay recomendación con alta confianza:
if price_rec['confidence'] > 0.7:
    # Mostrar: "Basado en tu historial, sugerimos $0.68"
    suggested_price = price_rec['recommended_price']
else:
    # Usar precio del catálogo
    suggested_price = catalog_price

# 4. Usuario corrige precio
if user_corrects_price:
    learning_service.record_price_correction(
        user_id=current_user_id,
        organization_id=current_org_id,
        product_name=product_name,
        original_price=catalog_price,
        corrected_price=user_price,
        quantity=quantity
    )
```

---

### **Flujo 3: Dashboard de Efectividad**

```python
# Obtener estadísticas de recomendaciones
stats = recommendation_service.get_recommendation_stats(
    organization_id=current_org_id,
    days=30
)

# Mostrar en dashboard:
# - Tasa de aceptación: 70%
# - Total recomendaciones: 150
# - Top productos aceptados
```

---

## 📊 **MÉTRICAS DE CONFIANZA**

### **Cálculo de Confidence Score**

| Fuente | Fórmula | Rango |
|--------|---------|-------|
| Productos frecuentes | `0.5 + (usage_count * 0.05)` | 0.5 - 0.9 |
| Co-ocurrencia | Fijo | 0.7 |
| Precio aprendido | `0.6 + (corrections_count * 0.1)` | 0.6 - 0.95 |
| Pricing preferido | Fijo | 0.9 |
| Default por tipo RFX | Fijo | 0.5 |
| Precio de catálogo | Fijo | 0.3 |

### **Interpretación**

- **> 0.8:** Alta confianza - Mostrar como sugerencia fuerte
- **0.5 - 0.8:** Media confianza - Mostrar como opción
- **< 0.5:** Baja confianza - Usar solo como fallback

---

## 🔗 **INTEGRACIÓN CON LEARNING SERVICE**

El `recommendation_service` usa `learning_service` internamente:

```python
from backend.services.learning_service import learning_service

class RecommendationService:
    def __init__(self):
        self.learning = learning_service  # Reutiliza FASE 1
    
    def recommend_products_for_rfx(...):
        # Usa learning_service.get_frequent_products()
        # Usa learning_service.get_related_products()
```

**Beneficio:** No duplicar código, mantener separación de responsabilidades

---

## ✅ **VENTAJAS DEL DISEÑO**

### **1. KISS - Simple pero Efectivo**
```python
# NO usamos ML complejo
❌ Neural networks
❌ Matrix factorization
❌ Embeddings

# SÍ usamos lógica simple
✅ Contadores de uso
✅ Ordenamiento por frecuencia
✅ Búsqueda de co-ocurrencias
✅ Confidence scores simples
```

### **2. Consistencia con el Proyecto**
```python
# Mismo patrón que otros servicios
- Singleton instance al final
- Logging consistente (✅, ❌, 📭)
- Manejo de errores con try/except
- Returns tipados con Dict[str, Any]
```

### **3. Escalable**
```python
# Fácil agregar nuevos tipos de recomendaciones
def recommend_suppliers(...):
    # Mismo patrón
    
def recommend_templates(...):
    # Mismo patrón
```

---

## 📁 **ARCHIVOS**

```
backend/services/
├── learning_service.py          # FASE 1 (300 líneas)
└── recommendation_service.py    # FASE 2 (400 líneas) ⭐ NUEVO
```

---

## 🚀 **PRÓXIMOS PASOS (FASE 3)**

### **Integración con Servicios Existentes**

**1. Integrar con `pricing_config_service_v2.py`**
```python
# En get_rfx_pricing_configuration()
if not config_found:
    # Usar recomendación
    recommended = recommendation_service.recommend_pricing_config(user_id, rfx_type)
    if recommended:
        return recommended
```

**2. Integrar con `ai_product_selector.py`**
```python
# Antes de seleccionar variante
price_rec = recommendation_service.recommend_price_for_product(
    user_id, product_name, quantity
)
if price_rec['confidence'] > 0.7:
    # Usar precio recomendado
```

**3. Crear Endpoints API**
```python
# backend/api/recommendations.py
@recommendations_bp.route("/products/<rfx_id>")
def get_product_recommendations(rfx_id):
    # Exponer recomendaciones al frontend
```

---

## 📊 **ESTADO ACTUAL**

```
┌─────────────────────────────────────────────────────────┐
│  AI LEARNING SYSTEM - FASE 2 COMPLETADA                │
├─────────────────────────────────────────────────────────┤
│  ✅ FASE 1: learning_service.py (300 líneas)            │
│  ✅ FASE 2: recommendation_service.py (400 líneas)      │
│  ⏳ FASE 3: Integración con servicios existentes        │
│  ⏳ FASE 4: Endpoints API                               │
│  ⏳ FASE 5: Frontend                                    │
└─────────────────────────────────────────────────────────┘
```

**Total código:** 700 líneas  
**Complejidad:** Baja (KISS)  
**Funcionalidad:** Alta (recomendaciones completas)

---

**Fin de FASE 2** ✅
