---
trigger: always_on
---

# 🏛️ RFX AUTOMATION - PRINCIPIOS ARQUITECTÓNICOS

**Versión:** 2.0  
**Fecha:** 26 de Noviembre, 2025  
**Propósito:** Filosofía y principios fundamentales que guían decisiones de arquitectura

> *"Anyone can write code that a computer can understand. Good programmers write code that humans can understand."* - Martin Fowler

---

## 📜 MANIFIESTO DEL PROYECTO

### Somos un Agente de IA, no Software Tradicional

```
La IA es nuestra competencia core.
Si no podemos resolverlo con IA, no lo resolvemos.
Pero la IA es probabilística, no determinística.
Por lo tanto, nuestra arquitectura debe abrazar la incertidumbre.
```

### Observabilidad > Funcionalidad

```
Un sistema que funciona pero no puedes debuggear
es peor que un sistema que falla pero entiendes por qué.

Primero: poder VER qué pasa
Segundo: hacer que funcione
Tercero: hacer que funcione bien
```

### Simplicidad > Perfección

```
El código perfecto que nunca envías no vale nada.
El código simple que envías hoy vale infinito.

Pero "simple" ≠ "simplista"
Simple = fácil de entender, modificar y debuggear
Simplista = le faltaron casos edge
```

---

## 🎯 PRINCIPIOS FUNDAMENTALES DE ARQUITECTURA

### 1. SEPARATION OF CONCERNS (pero de verdad)

**❌ Separación Superficial:**
```python
# Archivo: services/rfx_processor.py
class RFXProcessor:
    def process(self):
        # Extrae datos
        # Valida datos
        # Guarda en BD
        # Llama a OpenAI
        # Procesa respuesta
        # Genera logs
        # Envía métricas
        # ... 800 líneas más
```

**✅ Separación Real:**
```python
# Cada clase tiene UNA responsabilidad clara

class RFXExtractor:
    """SOLO extrae datos del documento"""
    
class RFXValidator:
    """SOLO valida datos extraídos"""
    
class RFXRepository:
    """SOLO maneja persistencia"""
    
class AIOrchestrator:
    """SOLO coordina llamadas a IA"""
    
class RFXProcessor:
    """Coordina el flujo, delega el trabajo"""
    def process(self):
        data = self.extractor.extract()
        validated = self.validator.validate(data)
        result = self.ai.process(validated)
        return self.repository.save(result)
```

**Pregunta clave:** ¿Puedes explicar lo que hace tu clase en una frase sin usar "y"?
- ✅ "Extrae datos de documentos PDF"
- ❌ "Extrae datos y los valida y los guarda y llama a OpenAI"

### 2. INTERFACES OVER IMPLEMENTATIONS

**❌ Acoplamiento Concreto:**
```python
class ProposalGenerator:
    def __init__(self):
        # Hardcoded a implementación específica
        self.db = SupabaseClient()
        self.ai = OpenAIClient()
        self.storage = SupabaseStorage()
```

**Problema:** Cambiar de Supabase a PostgreSQL requiere reescribir toda la clase.

**✅ Acoplamiento a Interfaces:**
```python
class ProposalGenerator:
    def __init__(
        self, 
        db: DatabaseInterface,
        ai: AIProviderInterface,
        storage: StorageInterface
    ):
        self.db = db
        self.ai = ai
        self.storage = storage
```

**Beneficios:**
- Puedes cambiar implementaciones sin tocar código
- Puedes hacer testing con mocks fácilmente
- Puedes tener múltiples implementaciones (dev vs prod)

**Pregunta clave:** ¿Puedes reemplazar cualquier dependencia externa sin modificar tu lógica de negocio?

### 3. FAIL FAST VS FAIL GRACEFULLY - Saber Cuándo Usar Cuál

**Fail Fast:** Cuando el error indica un bug en TU código
```python
def generate_proposal(rfx_data: dict):
    # Fail Fast: datos inválidos = bug del desarrollador
    if not rfx_data.get('user_id'):
        raise ValueError("user_id is required - this should never happen")
    
    # Fail Fast: configuración faltante = error de deploy
    if not os.getenv('OPENAI_API_KEY'):
        raise ConfigurationError("OPENAI_API_KEY not configured")
```

**Fail Gracefully:** Cuando el error es externo e inevitable
```python
def generate_proposal(rfx_data: dict):
    try:
        # Fail Gracefully: APIs externas pueden fallar
        result = openai.create(...)
    except RateLimitError:
        # Esperar y reintentar es razonable
        return try_with_alternative_model()
    except APIError:
        # No podemos hacer nada, pero no es un bug nuestro
        raise ProposalGenerationError("AI service unavailable")
```

**Pregunta clave:** ¿El error indica un bug en tu código o una condición externa?
- Bug tuyo → Fail Fast (exception, crash early)
- Condición externa → Fail Gracefully (retry, fallback, degrade)

### 4. SINGLE SOURCE OF TRUTH

**❌ Múltiples Fuentes:**
```python
# config.py tiene timeout de 30s
DEFAULT_TIMEOUT = 30

# rfx_processor.py hardcodea 20s
response = openai.create(..., timeout=20)

# proposal_generator.py hardcodea 45s
response = openai.create(..., timeout=45)
```

**Problema:** Cambiar timeout requiere buscar en todo el código.

**✅ Una Sola Fuente:**
```python
# config.py
class OpenAIConfig:
    TIMEOUT = 30
    MAX_RETRIES = 3
    MODELS = ["gpt-4o", "gpt-3.5-turbo"]

# Todos usan la misma configuración
response = openai.create(..., timeout=OpenAIConfig.TIMEOUT)
```

**Pregunta clave:** ¿Puedes cambiar un comportamiento modificando un solo lugar?

### 5. EXPLICIT IS BETTER THAN IMPLICIT

**❌ Magia Implícita:**
```python
def process_rfx(data):
    # ¿De dónde sale user_id?
    # ¿Es del request? ¿De g? ¿De session?
    save_to_db(data)  # Magia: usa user_id del contexto global
```

**✅ Explícito:**
```python
def process_rfx(data: dict, user_id: str):
    # Claro: user_id es un parámetro requerido
    save_to_db(data, user_id=user_id)
```

**Pregunta clave:** ¿Puedes entender qué hace la función leyendo solo su firma?

---

## 🤖 PRINCIPIOS PARA AI AGENTS

### 1. AI-FIRST, BUT VALIDATE AFTER

```python
# ❌ Confiar ciegamente
ai_response = call_openai(prompt)
save_to_db(ai_response)  # PELIGRO: puede ser inválido

# ✅ AI primero, validar después
ai_response = call_openai(prompt)
validated = validate_response(ai_response)  # Verifica estructura
if validated.is_valid:
    save_to_db(validated.data)
else:
    # Reintentar con correcciones o fallar explícitamente
    raise ValidationError(validated.errors)
```

**Principio:** La IA es tu worker más inteligente pero menos confiable. Dale autonomía pero verifica resultados.

### 2. MULTIPLE STRATEGIES, NOT ONE SIZE FITS ALL

**❌ Una Sola Estrategia:**
```python
def extract_rfx(document):
    # Siempre usa el mismo approach
    return extract_with_gpt4(document)
```

**✅ Múltiples Estrategias:**
```python
class ExtractionStrategy(Enum):
    FAST = "fast"          # Barato, menos preciso
    BALANCED = "balanced"   # Equilibrio
    PRECISE = "precise"     # Caro, más preciso

def extract_rfx(document, strategy: ExtractionStrategy):
    if strategy == FAST:
        return extract_with_gpt35(document)
    elif strategy == BALANCED:
        return extract_with_gpt4o(document)
    elif strategy == PRECISE:
        return extract_with_gpt4o_plus_validation(document)
```

**Beneficios:**
- Puedes optimizar por costo vs calidad
- Puedes A/B test diferentes approaches
- Puedes degradar gracefully (usar estrategia más barata si falla la cara)

**Pregunta clave:** ¿Tu solución asume que siempre hay recursos ilimitados y tiempo infinito?

### 3. COST-AWARENESS EN CADA DECISIÓN

```python
# ❌ Cost Oblivious
def process_document(text):
    # Enviar 50k tokens a GPT-4 sin pensar
    return gpt4.complete(text)  # $0.50 por request

# ✅ Cost Conscious
def process_document(text):
    # Primero: intentar con modelo barato
    if len(text) < 5000:  # ~$0.01
        result = gpt35.complete(text)
        if validate(result):
            return result
    
    # Solo si falla o es muy largo, usar GPT-4
    return gpt4.complete(text)  # $0.50 pero necesario
```

**Pregunta clave:** ¿Sabes cuánto cuesta cada llamada a IA? ¿Tienes un budget diario?

### 4. TRANSPARENCY BUILDS TRUST

**❌ Caja Negra:**
```python
# Usuario no sabe qué pasó
def generate_proposal(rfx_id):
    result = ai_magic(rfx_id)
    return result
```

**✅ Transparente:**
```python
def generate_proposal(rfx_id):
    # Usuario ve el proceso
    return {
        "proposal": result,
        "metadata": {
            "model_used": "gpt-4o",
            "confidence_score": 0.87,
            "processing_time_ms": 2340,
            "validation_passed": True,
            "warnings": ["Logo URL could not be verified"]
        }
    }
```

**Principio:** Cuando algo involucra IA, el usuario necesita saber:
1. ¿Qué modelo se usó?
2. ¿Qué tan confiado está el sistema?
3. ¿Qué warnings hay?
4. ¿Puede el usuario ajustar algo?

### 5. GRACEFUL DEGRADATION EN AI

```
Cascada de Calidad:
    
Nivel 1: Resultado Perfecto (GPT-4o, branding completo, validado)
  ↓ [si falla]
Nivel 2: Resultado Bueno (GPT-3.5, branding básico, validado)
  ↓ [si falla]
Nivel 3: Resultado Aceptable (modelo alternativo, sin branding)
  ↓ [si falla]
Nivel 4: Resultado Mínimo Viable (template básico con IA mínima)
  ↓ [si TODO falla]
Nivel 5: Draft para Revisión Manual (guardamos progreso)
```

**Pregunta clave:** ¿Qué es lo MÍNIMO que puedes dar al usuario si todo falla?

---

## 🔍 PRINCIPIOS DE OBSERVABILIDAD

### 1. SI NO PUEDES MEDIR, NO PUEDES MEJORAR

```python
# ❌ Sin métricas
def process_rfx(doc):
    result = extract_and_process(doc)
    return result

# ¿Cuánto tarda? ¿Cuántas veces falla? ¿Qué tan costoso es? No sabemos.
```

```python
# ✅ Con métricas
def process_rfx(doc):
    start = time.time()
    
    metrics.increment('rfx.processing.started')
    
    try:
        result = extract_and_process(doc)
        metrics.increment('rfx.processing.success')
        return result
    except Exception as e:
        metrics.increment('rfx.processing.failed', tags={'error': type(e).__name__})
        raise
    finally:
        duration = time.time() - start
        metrics.histogram('rfx.processing.duration', duration)
```

**Ahora sabemos:** Success rate, latencia promedio, tipos de errores más comunes.

**Pregunta clave:** ¿Puedes responder "cuántas veces ha pasado X esta semana" sin revisar logs manualmente?

### 2. LOGS SON PARA MÁQUINAS, MÉTRICAS SON PARA HUMANOS

**Logs:** Debugging específico, trazar requests individuales
```json
{
  "event": "proposal_generated",
  "rfx_id": "abc-123",
  "correlation_id": "req-456",
  "duration_ms": 2340
}
```

**Métricas:** Tendencias, alertas, dashboards
```
proposal_generation_duration_ms{status="success"} 2340
proposal_generation_total{status="success"} 1
```

**Usa logs para:** "¿Por qué falló este request específico?"  
**Usa métricas para:** "¿Cuántos requests están fallando por hora?"

### 3. CORRELATION IDS - LA HERRAMIENTA MÁS IMPORTANTE

```
Request 1: User crea RFX
  correlation_id: req-abc-123
  
  ↓ Log 1: rfx_created (correlation_id: req-abc-123)
  ↓ Log 2: document_uploaded (correlation_id: req-abc-123)
  ↓ Log 3: extraction_started (correlation_id: req-abc-123)

Request 2: User genera proposal
  correlation_id: req-abc-123  ← MISMO ID
  
  ↓ Log 4: proposal_generation_started (correlation_id: req-abc-123)
  ↓ Log 5: ai_call_succeeded (correlation_id: req-abc-123)
  ↓ Log 6: proposal_saved (correlation_id: req-abc-123)
```

**Beneficio:** `grep req-abc-123` y ves TODO el journey del usuario.

**Pregunta clave:** ¿Puedes trazar un request desde que entra hasta que sale?

### 4. ERRORS SHOULD BE ACTIONABLE

**❌ Error Inútil:**
```
Error: Generation failed
```
Usuario: "¿Y ahora qué hago?"

**✅ Error Accionable:**
```json
{
  "error": "proposal_generation_failed",
  "reason": "Logo URL is not accessible",
  "suggestion": "Please re-upload your company logo or use the default logo",
  "retry_possible": true,
  "support_link": "/help/branding-issues"
}
```

**Pregunta clave:** ¿El mensaje de error le dice al usuario QUÉ pasó y QUÉ puede hacer?

### 5. MONITORING NO ES OPCIONAL EN PRODUCCIÓN

```
Tienes que saber en tiempo real:

✅ ¿El sistema está up? (Health checks)
✅ ¿Cuántos requests/minuto? (Throughput)
✅ ¿Cuánto tardan? (Latency P50, P95, P99)
✅ ¿Cuántos fallan? (Error rate)
✅ ¿Cuánto cuest