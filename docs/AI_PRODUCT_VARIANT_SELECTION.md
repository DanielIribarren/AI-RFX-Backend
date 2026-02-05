# 🤖 SISTEMA DE SELECCIÓN INTELIGENTE DE VARIANTES DE PRODUCTOS

**Versión:** 1.0  
**Fecha:** 3 de Febrero, 2026  
**Autor:** Sistema AI-First

---

## 🎯 PROBLEMA RESUELTO

### Escenario Original:

```
RFX dice: "Tequeños" (100 unidades)

Catálogo tiene:
- "Tequeños Salados" ($3.05 costo / $4.43 precio)
- "Tequeños de Queso" ($3.50 costo / $5.00 precio)
- "Tequeños Dulces" ($4.00 costo / $6.00 precio)

❓ ¿Cuál elegir?
```

**Antes:** Sistema retornaba el primero que encontraba (orden de BD)  
**Ahora:** AI analiza contexto y elige el más apropiado

---

## 🏗️ ARQUITECTURA

### Flujo Completo:

```
1. Usuario sube RFX: "Tequeños para evento corporativo"
   ↓
2. AI extrae: "Tequeños" (100 unidades)
   ↓
3. CatalogSearchServiceSync.search_product_variants()
   ├─ Exact match: ❌ No encuentra "Tequeños" exacto
   ├─ Fuzzy match: ✅ Encuentra 3 variantes
   │   - "Tequeños Salados" (confidence: 1.0)
   │   - "Tequeños de Queso" (confidence: 1.0)
   │   - "Tequeños Dulces" (confidence: 1.0)
   └─ Semantic search: (skip, ya hay matches)
   ↓
4. AIProductSelector.select_best_variant()
   ├─ Analiza contexto: "evento corporativo"
   ├─ Evalúa opciones según:
   │   - Similitud con lo solicitado
   │   - Contexto del evento
   │   - Relación calidad-precio
   │   - Confidence scores
   └─ Selecciona: "Tequeños Salados" 
       Razón: "Opción más común y económica para eventos corporativos"
   ↓
5. Enriquecimiento con precios del catálogo
   ↓
6. Guardado en BD con metadata de selección
```

---

## 📦 COMPONENTES

### 1. CatalogSearchServiceSync (Búsqueda Múltiple)

**Archivo:** `backend/services/catalog_search_service_sync.py`

**Método nuevo:** `search_product_variants()`

```python
def search_product_variants(
    query: str, 
    organization_id: str = None,
    user_id: str = None,
    max_variants: int = 5
) -> List[Dict[str, Any]]:
    """
    Busca múltiples variantes de un producto
    
    Returns:
        Lista de productos ordenados por confidence (mayor a menor)
    """
```

**Estrategia:**
1. **Exact match** → Si encuentra exacto, lo incluye
2. **Fuzzy match múltiple** → Busca hasta 10 productos, filtra por score >= 0.5
3. **Semantic search múltiple** → Busca hasta 5 productos, filtra por similarity >= 0.65
4. **Deduplicación** → Elimina duplicados por ID
5. **Ordenamiento** → Por confidence descendente
6. **Limitación** → Retorna top N (default 5)

---

### 2. AIProductSelector (Selección Inteligente)

**Archivo:** `backend/services/ai_product_selector.py`

**Método principal:** `select_best_variant()`

```python
def select_best_variant(
    query: str,
    variants: List[Dict[str, Any]],
    rfx_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Selecciona la mejor variante usando AI
    
    Estrategia en cascada:
    1. Si solo 1 variante → retornar directamente
    2. Si todas tienen mismo precio → retornar primera
    3. Usar AI (gpt-4o-mini) para seleccionar
    4. Fallback: precio promedio de todas las variantes
    """
```

**Prompt AI:**
```
Eres un experto en catering y eventos. El cliente solicitó "Tequeños".

Encontramos estas variantes:
1. Tequeños Salados - Costo: $3.05, Precio: $4.43 (confidence: 1.0)
2. Tequeños de Queso - Costo: $3.50, Precio: $5.00 (confidence: 1.0)
3. Tequeños Dulces - Costo: $4.00, Precio: $6.00 (confidence: 1.0)

Contexto del RFX:
- Tipo de evento: catering
- Descripción: Evento corporativo para 120 personas
- Ubicación: Ciudad de México

Selecciona la MÁS APROPIADA según:
1. Similitud con lo solicitado
2. Contexto del evento
3. Relación calidad-precio
4. Confidence score

Responde SOLO con el número (1, 2, 3) seguido de razón (máximo 20 palabras).
Formato: "Número: Razón"
```

**Respuesta AI:**
```
1: Opción más común y económica para eventos corporativos
```

---

### 3. RFXProcessorService (Integración)

**Archivo:** `backend/services/rfx_processor.py`

**Método actualizado:** `_enrich_products_with_catalog()`

```python
def _enrich_products_with_catalog(
    products: List[Dict[str, Any]], 
    organization_id: str,
    rfx_context: Dict[str, Any] = None  # ← NUEVO
) -> List[Dict[str, Any]]:
    """
    Enriquece productos con precios del catálogo
    
    MEJORADO con selección inteligente de variantes
    """
```

**Cambios:**
1. Llama a `search_product_variants()` en lugar de `search_product()`
2. Si hay múltiples variantes, usa `AIProductSelector`
3. Pasa contexto del RFX para selección inteligente
4. Agrega metadata de selección al producto

---

## �� METADATA DE SELECCIÓN

Cada producto enriquecido ahora incluye:

```python
{
    'nombre': 'Tequeños',
    'cantidad': 100,
    'unidad': 'unidades',
    'costo_unitario': 3.05,      # Del catálogo
    'precio_unitario': 4.43,     # Del catálogo
    
    # Metadata estándar
    'catalog_match': True,
    'catalog_product_name': 'Tequeños Salados',
    'catalog_match_type': 'fuzzy',
    'catalog_confidence': 1.0,
    'pricing_source': 'catalog',
    
    # Metadata de selección AI (NUEVO)
    'selection_method': 'ai_intelligent',  # o 'single_variant', 'same_price', 'average_pricing'
    'ai_reasoning': 'Opción más común y económica para eventos corporativos',
    'variants_count': 3
}
```

---

## 🔄 MÉTODOS DE SELECCIÓN

### 1. **single_variant**
- Solo se encontró 1 variante
- No requiere AI
- Retorna directamente

### 2. **same_price**
- Múltiples variantes con precios idénticos
- No requiere AI (no hay diferencia económica)
- Retorna la primera

### 3. **ai_intelligent** ⭐
- Múltiples variantes con precios diferentes
- AI analiza contexto y selecciona
- Incluye razonamiento en metadata

### 4. **average_pricing** (Fallback)
- AI falló o no disponible
- Calcula precio promedio de todas las variantes
- Usa nombre de la variante con mayor confidence

---

## 📝 LOGS DETALLADOS

### Ejemplo de logs durante procesamiento:

```
🔍 Searching variants: 'Tequeños' (org: abc-123)
✅ FUZZY match: Tequeños Salados (score: 1.00)
✅ FUZZY match: Tequeños de Queso (score: 1.00)
✅ FUZZY match: Tequeños Dulces (score: 1.00)
✅ Found 3 variants for 'Tequeños'
   1. Tequeños Salados (confidence: 1.00)
   2. Tequeños de Queso (confidence: 1.00)
   3. Tequeños Dulces (confidence: 1.00)

🤖 Found 3 variants for 'Tequeños', using AI to select best match
🤖 AI response: 1: Opción más común y económica para eventos corporativos

✅ AI-selected match: 'Tequeños' → 'Tequeños Salados' (3 variants, confidence=1.00) [cost=$3.05, price=$4.43] Reason: Opción más común y económica para eventos corporativos

🛒 CATALOG ENRICHMENT SUMMARY: 1/1 matches (100.0%), 0 misses
🤖 AI intelligent selections: 1/1 matches
```

---

## 🎯 CASOS DE USO

### Caso 1: Una sola variante
```
RFX: "Empanadas de Carne"
Catálogo: "Empanadas de Carne" (única)

Resultado: Selección directa (single_variant)
```

### Caso 2: Múltiples variantes, mismo precio
```
RFX: "Agua"
Catálogo:
- "Agua Natural" ($1.00 / $1.50)
- "Agua Mineral" ($1.00 / $1.50)

Resultado: Primera variante (same_price)
```

### Caso 3: Múltiples variantes, precios diferentes
```
RFX: "Tequeños para evento corporativo"
Catálogo:
- "Tequeños Salados" ($3.05 / $4.43)
- "Tequeños de Queso" ($3.50 / $5.00)
- "Tequeños Dulces" ($4.00 / $6.00)

Resultado: AI selecciona "Tequeños Salados" (ai_intelligent)
Razón: "Opción más común y económica para eventos corporativos"
```

### Caso 4: AI falla
```
RFX: "Pastelitos"
Catálogo:
- "Pastelitos de Guayaba" ($2.50 / $3.50)
- "Pastelitos de Carne" ($3.00 / $4.00)

AI: Error de API o respuesta inválida

Resultado: Precio promedio (average_pricing)
- Costo: $2.75 (promedio)
- Precio: $3.75 (promedio)
```

---

## ⚙️ CONFIGURACIÓN

### Parámetros ajustables:

**CatalogSearchServiceSync:**
```python
max_variants = 5  # Máximo de variantes a retornar
fuzzy_threshold = 0.5  # Threshold mínimo para fuzzy match
semantic_threshold = 0.65  # Threshold mínimo para semantic search
```

**AIProductSelector:**
```python
model = "gpt-4o-mini"  # Modelo de OpenAI
temperature = 0.3  # Creatividad (0.0 = determinístico)
max_tokens = 100  # Límite de respuesta
max_retries = 2  # Reintentos si falla
```

---

## 💰 COSTOS

### Por producto con múltiples variantes:

```
Búsqueda de variantes:
- Exact match: 0 tokens, <10ms
- Fuzzy match: 0 tokens, ~50ms
- Semantic search: ~50 tokens, ~150ms (solo si necesario)

Selección AI:
- Prompt: ~200 tokens
- Respuesta: ~20 tokens
- Total: ~220 tokens (~$0.0001 con gpt-4o-mini)

TOTAL: ~270 tokens, ~$0.0001 por producto con variantes
```

**Optimización:** Solo se usa AI cuando hay múltiples variantes con precios diferentes.

---

## 🚀 BENEFICIOS

✅ **Precisión:** Selección contextual vs aleatoria  
✅ **Transparencia:** Metadata completa de selección  
✅ **Trazabilidad:** Logs detallados del proceso  
✅ **Eficiencia:** Solo usa AI cuando es necesario  
✅ **Fallback robusto:** Precio promedio si AI falla  
✅ **Escalable:** Funciona con N variantes  

---

## 📈 PRÓXIMAS MEJORAS

1. **Cache de selecciones AI:** Guardar selecciones previas para productos similares
2. **Aprendizaje:** Analizar selecciones históricas para mejorar prompts
3. **Feedback loop:** Permitir al usuario corregir selecciones
4. **Reglas de negocio:** Agregar reglas específicas por tipo de evento
5. **A/B Testing:** Comparar AI vs precio promedio vs primera variante

---

## 🔧 TESTING

### Comando de prueba:

```python
from backend.services.catalog_search_service_sync import CatalogSearchServiceSync
from backend.services.ai_product_selector import AIProductSelector
from backend.core.ai_config import get_openai_client

# Buscar variantes
variants = catalog_search.search_product_variants(
    "Tequeños",
    organization_id="abc-123",
    max_variants=5
)

# Seleccionar mejor variante
selector = AIProductSelector(get_openai_client())
selected = selector.select_best_variant(
    query="Tequeños",
    variants=variants,
    rfx_context={
        'rfx_type': 'catering',
        'description': 'Evento corporativo',
        'location': 'CDMX'
    }
)

print(f"Selected: {selected['product_name']}")
print(f"Reason: {selected.get('ai_reasoning')}")
```

---

**Estado:** ✅ IMPLEMENTADO Y FUNCIONANDO  
**Versión:** 1.0  
**Última actualización:** 3 de Febrero, 2026
