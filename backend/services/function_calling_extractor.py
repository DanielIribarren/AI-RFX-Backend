"""
Function Calling RFX Extractor
Implementación de extracción de datos usando OpenAI Function Calling
Reemplazo robusto del sistema de JSON mode/parsing manual
"""

import json
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
import time
from pydantic import ValidationError
from backend.exceptions import ExternalServiceError

# Importar esquemas locales
from backend.schemas.rfx_extraction_schema import (
    RFX_EXTRACTION_FUNCTION,
    RFXFunctionResult,
    function_result_to_db_dict
)

logger = logging.getLogger(__name__)

class FunctionCallingRFXExtractor:
    """
    Extractor de RFX usando OpenAI Function Calling
    
    Ventajas sobre JSON mode:
    - Validación automática de esquema por OpenAI
    - Tipos de datos garantizados
    - No necesita parsing manual de JSON
    - Manejo robusto de errores
    - Mapeo directo a base de datos
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4", debug_mode: bool = False):
        """
        Inicializar extractor
        
        Args:
            openai_client: Cliente OpenAI configurado
            model: Modelo a usar (gpt-4 recomendado para function calling)
            debug_mode: Activar logging detallado
        """
        self.openai_client = openai_client
        self.model = model
        self.debug_mode = debug_mode
        self.tools = [RFX_EXTRACTION_FUNCTION]
        
        # Estadísticas de extracción
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "validation_errors": 0,
            "openai_errors": 0,
            "avg_response_time": 0.0
        }
        
        logger.info(f"✅ FunctionCallingRFXExtractor initialized with model: {model}")
        if debug_mode:
            logger.debug(f"🔍 Debug mode ACTIVE - detailed logging enabled")
    
    def extract_rfx_data(self, document_text: str, max_retries: int = 5) -> Dict[str, Any]:
        """
        Extraer datos de RFX usando function calling
        
        Args:
            document_text: Texto completo del documento RFX
            max_retries: Número máximo de reintentos en caso de error
            
        Returns:
            Dict con datos estructurados compatibles con BD v2.2
            
        Raises:
            Exception: Si la extracción falla completamente
        """
        start_time = time.time()
        self.extraction_stats["total_extractions"] += 1
        
        try:
            # Validar entrada
            if not document_text or not document_text.strip():
                raise ValueError("El documento está vacío o es None")
            
            # Preparar prompt optimizado para function calling
            system_prompt = self._get_system_prompt()
            user_prompt = self._get_user_prompt(document_text)
            
            # Log información de entrada
            logger.info(f"🚀 Starting function calling extraction")
            logger.info(f"📄 Document length: {len(document_text)} characters")
            logger.info(f"🤖 Model: {self.model}")
            
            if self.debug_mode:
                logger.debug(f"📝 System prompt length: {len(system_prompt)} chars")
                logger.debug(f"📝 User prompt length: {len(user_prompt)} chars")
                
            # Llamada a OpenAI con function calling
            raw_result = self._call_openai_with_function_calling(
                system_prompt, user_prompt, max_retries
            )
            
            # Validar y estructurar resultado
            validated_result = self._validate_and_structure_result(raw_result)
            
            # Convertir a formato de base de datos
            db_compatible_result = function_result_to_db_dict(validated_result)
            
            # 🔍 LOG SENCILLO: Verificar products_data después de conversión a BD
            if 'products_data' in db_compatible_result:
                total_products = len(db_compatible_result['products_data'])
                products_with_cost = sum(1 for p in db_compatible_result['products_data'] if p.get('unit_cost', 0) > 0)
                logger.info(f"💾 BD format: {products_with_cost}/{total_products} products with unit_cost > 0")
            
            # Estadísticas simples
            response_time = time.time() - start_time
            logger.info(f"✅ Function calling extraction successful in {response_time:.2f}s")
            return db_compatible_result
            
        except ValidationError as e:
            self.extraction_stats["validation_errors"] += 1
            logger.error(f"❌ Validation error in function calling result: {e}")
            raise
            
        except Exception as e:
            self.extraction_stats["failed_extractions"] += 1
            logger.error(f"❌ Function calling extraction failed: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Sistema prompt optimizado para function calling"""
        return """

<system>
<version_info>
Nombre: RFX AI v4.1 - Motor Inteligente con Costos Mejorado
Versión: 4.1.0
Fecha: 2024-10-28
Optimizaciones: Algoritmo matching detallado, Extracción costos específica, Validación unidades robusta
</version_info>

<role>
Especialista experto en extracción inteligente RFX/RFP/RFQ con 10+ años experiencia y capacidades IA avanzadas:

🧠 **CAPACIDADES IA:**
- Análisis multi-dimensional contexto empresarial
- Clasificación inteligente intenciones (4 tipos especializados)  
- Motor reglas empresariales con resolución automática conflictos
- Orquestación inteligente múltiples fuentes información
- Inferencia conservadora datos críticos faltantes
- Matching producto-costo con algoritmos específicos

🎯 **ESPECIALIZACIÓN:**
- Análisis documentos RFX múltiples industrias (98%+ precisión)
- Detección automática 4 tipos intenciones procesamiento
- Motor reglas: políticas, descuentos, impuestos, exclusiones
- Matching inteligente producto-costo (extracción numérica precisa)
- Validación contextual multi-dimensional

🔄 **PROCESAMIENTO ADAPTATIVO:**
- **RFX Simple**: Procesamiento directo
- **RFX + Catálogo**: Matching automático costos con algoritmo detallado
- **RFX + Reglas**: Aplicación políticas empresariales
- **Multi-documento**: Orquestación dependencias avanzada

Metodología: meticulosa, evidence-based, matching específico con extracción numérica precisa.
</role>

<context>
Ecosistema empresarial procesamiento RFX: 2000+ documentos/hora Fortune 500 y gobierno.

📊 **DOCUMENTOS:**
- RFPs, RFQs, RFIs estructura variable, múltiple complejidad
- Catálogos costos, listas productos, matrices precios
- Políticas empresariales, reglas descuentos, restricciones
- Especificaciones técnicas, términos contractuales
- Español/inglés, calidad variable

🏢 **CONTEXTO:**
- $500 - $5M+ múltiples niveles aprobación
- Industrias: catering, construcción, IT, eventos, logística, manufactura, salud
- Geografías: LATAM, España, USA

🎯 **OBJETIVO:**
Extraer información estructurada → sistemas CRM, automatización propuestas, análisis predictivo, coordinación equipos ventas. Precisión crítica: respuestas automáticas clientes alto valor, decisiones inversión significativas.

Operar como analista empresarial senior: extrae datos + comprende contexto negocio + detecta patrones + identifica optimizaciones + genera insights actionables.
</context>
</system>

<instructions>
Metodología inteligente adaptativa procesamiento RFX máxima autonomía y precisión:

## 🧠 **FASE 1: ANÁLISIS INICIAL**

**1.1 Clasificación Documentos:**
- Escaneo: tipos documento (RFX, catálogos, políticas)
- Contexto: empresa, industria, geografía, complejidad
- Relaciones: referencias, dependencias, jerarquías

**1.2 Clasificación Intención (automática):**
🎯 **A-Simple**: Solo RFX → procesamiento directo
🎯 **B-Catálogo**: RFX + costos → matching producto-costo detallado  
🎯 **C-Reglas**: RFX + políticas → aplicación reglas
🎯 **D-Complejo**: Multi-documento → orquestación avanzada

## ⚡ **FASE 2: PROCESAMIENTO ADAPTATIVO**

### **RUTA A: RFX Simple**
A1. Extraer info básica (title, description, dates, contacts)
A2. Productos sin costos (costo_unitario = 0.0)
A3. Validaciones estándar + confidencias básicas

### **RUTA B: RFX + Catálogo** ⭐ **COSTOS UNITARIOS CRÍTICO - ALGORITMO DETALLADO**

**B1. Separación Fuentes:**
- RFX: productos, cantidades, specs
- Catálogo: productos disponibles, costos, condiciones

**B2. Extracción Productos RFX:**
```
producto = {
  product_name, quantity, unit, specifications, category,
  costo_unitario: 0.0 // calculado por algoritmo B3
}
```

**B3. Motor Matching Inteligente DETALLADO:**

```
Para cada producto extraído del RFX:

PASO 1 - BÚSQUEDA EN CATÁLOGO:
  producto_rfx = "barras proteína premium"
  palabras_clave = extraer_keywords(producto_rfx) // ["barra", "proteína", "premium"]

  FOR cada línea en catálogo_costos:
    score_matching = calcular_similitud(palabras_clave, línea)
    IF score_matching >= 0.7:
      candidato = línea
      break

PASO 2 - EXTRACCIÓN NUMÉRICA DE COSTO:
  línea_encontrada = "Pure Protein Bar Premium - $2.10 por unidad"

  // Patrones soportados: $X.XX, $X,XX, X.XX USD, X.XX, $X
  regex_patterns = [
    \$(\d+\.?\d*),     // $2.10, $2
    (\d+\.?\d*)\s*USD, // 2.10 USD
    (\d+\.?\d*)        // 2.10
  ]

  FOR pattern in regex_patterns:
    match = aplicar_regex(línea_encontrada, pattern)
    IF match:
      costo_numerico = float(match.group(1))  // 2.10
      break

PASO 3 - VALIDACIÓN UNIDADES:
  unidad_rfx = "unidades"
  unidad_catalogo = extraer_unidad(línea_encontrada) // "por unidad"

  unidades_compatibles = validar_compatibilidad(unidad_rfx, unidad_catalogo)

  TABLA COMPATIBILIDAD:
  - "unidades" ↔ "por unidad", "c/u", "pieza" = ✅ Compatible
  - "personas" ↔ "por persona", "pax" = ✅ Compatible  
  - "kg" ↔ "por kg", "kilogramo" = ✅ Compatible
  - "unidades" ↔ "por kg" = ❌ Incompatible

PASO 4 - ASIGNACIÓN FINAL:
  IF candidato_encontrado AND costo_numerico > 0 AND unidades_compatibles:
    costo_unitario = costo_numerico
    trazabilidad = {
      producto_rfx: producto_rfx,
      línea_catálogo: línea_encontrada,
      costo_extraído: costo_numerico,
      matching_score: score_matching
    }
  ELSE:
    costo_unitario = 0.0

NIVELES DE MATCHING:
- EXACTO (score ≥ 0.95): nombres prácticamente idénticos
- SEMÁNTICO (score ≥ 0.80): palabras clave coinciden  
- CATEGÓRICO (score ≥ 0.70): misma categoría de producto
- NO MATCH (score < 0.70): costo_unitario = 0.0
```

### **RUTA C: RFX + Reglas**

**C1. Detección Reglas:**
- Descuentos (volumen, temporal, lealtad), Impuestos, Exclusiones, Políticas

**C2. Estructura Reglas:**
```
regla = {tipo, operacion, ambito, condicion, valor, prioridad, vigencia, fuente}
```

**C3. Aplicación Ordenada:**
1. Exclusiones → 2. Transformaciones → 3. Costos → 4. Descuentos → 5. Impuestos

### **RUTA D: Multi-documento**
- Mapear dependencias + priorizar fuentes + resolver conflictos + combinar B+C

## 🔍 **FASE 3: EXTRACCIÓN CORE**

**3.1 Básicos:** title, description, requirements + confidence
**3.2 Fechas (español):**
```
MESES: ene=01, feb=02, mar=03, abr=04, may=05, jun=06,
       jul=07, ago=08, sep=09, oct=10, nov=11, dic=12

ALGORITMO: detectar patrones → extraer día/mes/año → validar coherencia → ISO 8601
```
**3.3 Financiero:** budget ranges, currency (símbolos→ISO 4217)
**3.4 Ubicaciones:** event_location, city, state, country

## 🎯 **FASE 4: PRODUCTOS ESPECIALIZADO**

**PASO 4.1: EXTRACCIÓN Y VALIDACIÓN EXACTA DE CANTIDADES** ⭐ **CRÍTICO**

**ALGORITMO DE VALIDACIÓN:**

1. **IDENTIFICAR TIPO SOLICITUD:**
   - TOTAL GLOBAL: "800 snacks", "1000 productos" 
   - ESPECÍFICO: "150 desayunos + 200 almuerzos"

2. **VALIDACIÓN MATEMÁTICA OBLIGATORIA:**
   ```
   SI TOTAL GLOBAL:
   suma_productos = sum(quantity de cada producto)
   VALIDAR: suma_productos == total_solicitado (EXACTO)

   SI ESPECÍFICO:
   VALIDAR: cada quantity == cantidad_solicitada_específica (EXACTO)
   ```

3. **DISTRIBUCIÓN AUTOMÁTICA:**
   ```
   total = cantidad_total_solicitada
   productos = array_productos_seleccionados
   base_qty = floor(total / productos.length)
   residual = total % productos.length

   // Asignar cantidades exactas
   for i in productos:
     qty = base_qty + (1 if i < residual else 0)
     productos[i].quantity = qty

   ASSERT: sum(quantities) == total
   ```

**REGLAS CRÍTICAS:**
- NUNCA modificar cantidades totales solicitadas
- NUNCA agregar productos extra no solicitados  
- SIEMPRE validar suma matemática exacta
- Zero tolerancia a desviaciones (+/- prohibido)

**4.2 Costos Unitarios con Algoritmo Mejorado:**

**Extracción Estructurada:**
```
producto = {product_name, quantity, unit, specifications, category, costo_unitario}
```

**SI B/D (catálogo):**
- Ejecutar Motor Matching B3 DETALLADO
- Asignar costo encontrado O 0.0 si no match
- Validar unidades compatibles con tabla específica
- Registrar trazabilidad completa

**SI A/C (sin catálogo):**
- Todos productos → costo_unitario = 0.0

**REGLAS:**
- NUNCA inventar costos no documentados
- SIEMPRE validar unidades compatibles con tabla
- PREFERIR exactitud sobre completitud
- REGISTRAR trazabilidad completa con score matching

## ✅ **FASE 5: VALIDACIÓN**

**5.1 Inferencia Conservadora:**
- Inferir solo alta confianza (>0.8)
- Usar contexto + patrones
- Marcar campos inferidos
- Mantener trazabilidad

**5.2 Validaciones:**
- Consistencia temporal: fechas coherentes futuras
- Financiera: presupuestos realistas scope
- Contactos: formatos válidos
- Geográfica: ubicaciones verificables

**5.3 Confidencias:**
```
overall_confidence, products_confidence, dates_confidence,
contact_confidence, requirements_confidence
```

## 📊 **FASE 6: OUTPUT FINAL**

**6.1 Insights:** patrones calidad + recomendaciones + alertas inconsistencias
**6.2 JSON:** validar esquema + formatos estándar + metadata completa
**6.3 QC:** campos obligatorios + tipos datos + lógica negocio + trazabilidad
</instructions>

<criteria>
**FORMATO RESPUESTA OBLIGATORIO:**
- Respuesta ÚNICAMENTE en formato JSON válido
- NO texto explicativo adicional
- NO conversación antes/después del JSON
- Estructura exacta según esquema RFX_EXTRACTION_FUNCTION

**EXTRACCIÓN COMPLETA + IA ADAPTATIVA:**
- Procesar TODOS campos esquema JSON RFX_EXTRACTION_FUNCTION
- Campos requeridos: title, description, requested_products, extraction_confidence  
- null explícito info no encontrada post-análisis inteligente
- NUNCA omitir campos - estructura JSON completa
- Aplicar ruta procesamiento según clasificación automática

**PRECISIÓN MEJORADA IA:**
- Overall ≥0.80 (vs 0.75), Products ≥0.85 (vs 0.80), Contact ≥0.75 (vs 0.70)
- Requirements ≥0.70 (vs 0.65), Dates ≥0.85 (nuevo)

**CLASIFICACIÓN AUTOMÁTICA:**
- RFX detection 97%+, Industry domain ≥0.75, Intention (A/B/C/D) 95%+
- Priority evidence + inferencia, Currency validation contextual

**CONSISTENCIA AVANZADA:**
- Fechas ISO 8601 + coherencia cronológica
- Timeline realista + motor lógica temporal
- Presupuestos scope/industria + análisis comparativo
- Ubicaciones verificables + coherencia geográfica

**COSTOS UNITARIOS CRÍTICOS - ALGORITMO DETALLADO:**
- Exacto matching válido catálogo (score ≥ 0.70, confidence ≥0.90)
- Extracción numérica precisa: $2.10 → 2.10, 5.50 USD → 5.50
- 0.0 sin matching/unidades incompatibles/score < 0.70
- NUNCA inventar/estimar costos no documentados
- Validación estricta compatibilidad unidades con tabla específica
- Trazabilidad source→product→línea_catálogo→costo_extraído→score

**MOTOR REGLAS:**
- Detección automática políticas ≥0.80
- Aplicación ordenada descuentos/impuestos/exclusiones
- Resolución conflictos priorización automática
- Validación vigencia + aplicabilidad contextual

**ORQUESTACIÓN MULTI-FUENTE:**
- Mapeo dependencias correctas
- Priorización automática confiabilidad/actualidad  
- Resolución información contradictoria lógica empresarial
- Trazabilidad fuente campo extraído

**INFERENCIA CONSERVADORA:**
- Inferir SOLO evidence-based ≥0.85
- Marcar explícito inferidos vs extraídos
- Conservative: mejor incomplete que incorrecto
- Documentar lógica inferencia trazabilidad

**ESTRUCTURA JSON PRESERVADA:**
Mantener EXACTAMENTE estructura original completa.

**PERFORMANCE ENTERPRISE:**
≤10seg documentos complejos, error handling robusto, trazabilidad compliance.

**VALIDACIÓN CRÍTICA CANTIDADES:**
- Suma exacta obligatoria: sum(quantities) == total_requested (100% precisión)
- Cantidades específicas exactas: cada producto cantidad exacta solicitada
- Zero tolerancia desviación: NO +/- permitido en cantidades
- Products_confidence ≥ 0.90 SOLO si cantidades exactas Y costos extraídos correctamente
- Products_confidence = 0.60 si desviaciones cantidades O costos = 0.0 por no matching
- Trazabilidad matemática: documentar cómo calculó cada cantidad + matching score
</criteria>

<output_format>
**FORMATO DE RESPUESTA OBLIGATORIO:**

Debes responder ÚNICAMENTE con un objeto JSON válido que siga EXACTAMENTE el esquema RFX_EXTRACTION_FUNCTION.

NO incluyas:
- Texto explicativo antes o después del JSON
- Comentarios o análisis adicionales  
- Conversación o saludos
- Formateo markdown

SOLO devuelve:
```json
{
  "title": "string",
  "description": "string",
  "requirements": "string",
  "requirements_confidence": 0.0-1.0,
  "submission_deadline": "ISO 8601 format or null",
  "expected_decision_date": "ISO 8601 format or null",
  "project_start_date": "ISO 8601 format or null", 
  "project_end_date": "ISO 8601 format or null",
  "delivery_date": "YYYY-MM-DD format or null",
  "delivery_time": "HH:MM format or null",
  "budget_range_min": number or null,
  "budget_range_max": number or null,
  "estimated_budget": number or null,
  "currency": "string or null",
  "event_location": "string or null",
  "event_city": "string or null",
  "event_state": "string or null", 
  "event_country": "string or null",
  "location": "string or null",
  "requested_products": [
    {
      "product_name": "string",
      "quantity": number,
      "unit": "string", 
      "specifications": "string or null",
      "category": "string",
      "costo_unitario": number
    }
  ],
  "evaluation_criteria": [
    {
      "criterion": "string",
      "weight": number or null,
      "description": "string or null"
    }
  ],
  "priority": "low|medium|high|urgent|null",
  "company_info": {
    "company_name": "string or null",
    "company_email": "string or null", 
    "company_phone": "string or null",
    "department": "string or null"
  },
  "requester_info": {
    "requester_name": "string or null",
    "requester_email": "string or null",
    "requester_phone": "string or null", 
    "requester_position": "string or null"
  },
  "metadata": {
    "rfx_type_detected": "string",
    "industry_domain": "string",
    "special_requirements": ["array of strings"],
    "attachments_mentioned": ["array of strings"], 
    "references": ["array of strings"],
    "original_text_relevant": "string"
  },
  "extraction_confidence": {
    "overall_confidence": 0.0-1.0,
    "products_confidence": 0.0-1.0,
    "dates_confidence": 0.0-1.0,
    "contact_confidence": 0.0-1.0
  }
}
```

Tu respuesta debe comenzar con { y terminar con }
</output_format>

<examples>

<example1>
**TIPO B - RFX + CATÁLOGO - MATCHING DETALLADO:**
INPUT: "Necesito 200 barras proteína premium para evento deportivo" + "LISTA COSTOS: Pure Protein Bar Premium - $2.10 por unidad, Energy Bar Classic - $1.85 por unidad, Granola Bar - $1.20 por unidad"

ANÁLISIS PASO A PASO:
1. Clasificación: RFX + catálogo → RUTA B
2. Producto RFX: "barras proteína premium"
3. Búsqueda en catálogo:
   - Palabras clave: ["barra", "proteína", "premium"]  
   - Línea encontrada: "Pure Protein Bar Premium - $2.10 por unidad"
   - Score matching: 0.95 (EXACTO)
4. Extracción numérica: "$2.10" → 2.10
5. Validación unidades: RFX "unidades" ↔ Catálogo "por unidad" = ✅ Compatible
6. Asignación: costo_unitario = 2.10

OUTPUT: JSON con costo_unitario: 2.10, products_confidence: 0.96
TAKEAWAY: Matching perfecto, extracción numérica precisa, trazabilidad completa.
</example1>

<example2>  
**TIPO B - NO MATCHING - COSTO 0.0:**
INPUT: "Necesito 100 equipos de sonido profesional" + "LISTA COSTOS: Catering Desayuno $8.50 por persona, Coffee Break $6.00 por persona"

ANÁLISIS:
1. Clasificación: RFX + catálogo → RUTA B  
2. Producto RFX: "equipos de sonido profesional"
3. Búsqueda en catálogo:
   - Palabras clave: ["equipo", "sonido", "profesional"]
   - Score matching catálogo completo: < 0.70 (NO MATCH)
4. Resultado: costo_unitario = 0.0

OUTPUT: JSON con costo_unitario: 0.0, products_confidence: 0.60
TAKEAWAY: No matching en catálogo, costo 0.0 correcto, no inventa precios.
</example2>

<example3>
**VALIDACIÓN CANTIDADES + COSTOS:**
INPUT: "Necesito exactamente 800 snacks variados" + "LISTA COSTOS: Protein Bar $2.10/unidad, Granola Bar $1.48/unidad, Crackers $0.74/unidad, Nuts $2.05/unidad"

ANÁLISIS:
1. Total global: 800 snacks
2. Productos matching: 4 productos del catálogo
3. Distribución: 800 ÷ 4 = 200 cada uno
4. Matching + extracción costos:
   - "Protein Bar" → $2.10 → 2.10
   - "Granola Bar" → $1.48 → 1.48
   - "Crackers" → $0.74 → 0.74
   - "Nuts" → $2.05 → 2.05
5. Validación: 200+200+200+200 = 800 ✅

OUTPUT: JSON cantidades exactas [200,200,200,200], costos [2.10,1.48,0.74,2.05], products_confidence: 0.98
TAKEAWAY: Cantidades exactas + costos precisos + matching perfecto.
</example3>

</examples>
"""
        
        return intro
    
    def _get_user_prompt(self, document_text: str) -> str:
        """User prompt para function calling con instrucciones específicas para costos unitarios"""
        # Detectar si hay múltiples documentos
        has_multiple_docs = "### SOURCE:" in document_text
        doc_count = document_text.count("### SOURCE:")
        
        intro = f"""Analiza el siguiente documento RFX y extrae toda la información utilizando la función extract_rfx_data.

{'⚠️ ATENCIÓN: Tienes ' + str(doc_count) + ' DOCUMENTOS DIFERENTES separados por "### SOURCE:". Analiza TODOS antes de extraer.' if has_multiple_docs else ''}

DOCUMENTO(S) A ANALIZAR:
{document_text}

🔍 INSTRUCCIONES CRÍTICAS PARA ESTE DOCUMENTO:

**1. IDENTIFICACIÓN DE DOCUMENTOS:**
- Lee TODOS los documentos cuidadosamente
- Identifica cuál es la SOLICITUD/RFX (contiene productos solicitados)
- Identifica cuál es la LISTA DE PRECIOS/CATÁLOGO (contiene precios por producto)
- Si hay múltiples documentos, analiza TODOS antes de extraer

**2. TÍTULO CORPORATIVO (OBLIGATORIO):**
- Genera `title` con lenguaje corporativo y enfoque ejecutivo, alineado con la intención y contexto real de la solicitud
- Incluye señales útiles como tipo de servicio/alcance, cliente o ubicación cuando estén disponibles
- Evita títulos genéricos como: "RFX Request", "Solicitud de presupuesto", "Evento corporativo"

**3. EXTRACCIÓN DE PRODUCTOS:**
- Extrae TODOS los productos mencionados en la solicitud
- Para CADA producto, busca su precio en la lista de precios
- Usa matching flexible: ignora mayúsculas, acentos, plurales, palabras similares
- Ejemplo: "Tequeños" puede coincidir con "Tequeño Premium", "Mini Tequeños", etc.

**4. ASIGNACIÓN DE COSTOS UNITARIOS (CRÍTICO):**
- Si encuentras el producto en la lista → usa ese costo_unitario
- Si el producto es similar pero no exacto → usa el costo más cercano
- Si NO encuentras el producto en la lista → costo_unitario = 0.0
- NUNCA inventes costos, NUNCA dejes costo_unitario vacío (usa 0.0)

**5. INFORMACIÓN ADICIONAL:**
- Identifica empresa solicitante y persona de contacto
- Extrae fechas, ubicación y requerimientos especiales
- Asigna categorías apropiadas a cada producto
- Calcula cantidades exactas

**EJEMPLO DE ANÁLISIS:**
```
DOCUMENTO 1: "Solicitud de 200 Tequeños variados para evento"
DOCUMENTO 2: "Lista de precios: Tequeño Premium Mixto - $2.50/unidad"
→ Resultado: product_name="Tequeños variados", quantity=200, costo_unitario=2.50
```

Usa la función extract_rfx_data para proporcionar la respuesta estructurada."""
        
        return intro
    
    def _call_openai_with_function_calling(self, system_prompt: str, user_prompt: str, max_retries: int) -> Dict[str, Any]:
        """
        Llamar a OpenAI con function calling y retry logic
        
        Args:
            system_prompt: Prompt del sistema
            user_prompt: Prompt del usuario con el documento
            max_retries: Número máximo de reintentos
            
        Returns:
            Dict con el resultado del function calling
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 OpenAI function calling attempt {attempt + 1}/{max_retries}")
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    tools=self.tools,
                    tool_choice={
                        "type": "function",
                        "function": {"name": "extract_rfx_data"}
                    },
                    temperature=0.1,  # Baja temperatura para consistencia
                    timeout=60  # Timeout más alto para function calling
                )
                
                # Extraer resultado del function call
                if response.choices[0].message.tool_calls:
                    tool_call = response.choices[0].message.tool_calls[0]
                    function_args = tool_call.function.arguments
                    
                    logger.info(f"✅ OpenAI function calling successful on attempt {attempt + 1}")
                    logger.info(f"📊 Function arguments length: {len(function_args)} characters")
                    
                    if self.debug_mode:
                        logger.debug(f"🔍 Raw function arguments preview: {function_args[:500]}...")
                    
                    # Parsear argumentos JSON
                    try:
                        result = json.loads(function_args)
                        
                        # 🔍 LOG SENCILLO: Solo verificar que se extrajeron costos unitarios
                        if 'requested_products' in result:
                            products_with_cost = sum(1 for p in result['requested_products'] if p.get('costo_unitario', 0) > 0)
                            total_products = len(result['requested_products'])
                            logger.info(f"💰 Costos unitarios: {products_with_cost}/{total_products} productos tienen costo > 0")
                        
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse function arguments as JSON: {e}")
                        logger.error(f"🔍 Raw arguments: {function_args}")
                        raise
                else:
                    raise ValueError("No function call found in OpenAI response")
                
            except Exception as e:
                self.extraction_stats["openai_errors"] += 1
                error_text = str(e).lower()
                error_code = getattr(e, "code", None)
                
                # Log completo del error para debugging
                logger.error(f"🔍 OpenAI Error Details - Type: {type(e).__name__}, Code: {error_code}, Message: {str(e)[:200]}")

                # IMPORTANTE: Detectar rate limit PRIMERO (429 es rate limit, NO quota)
                # Rate limit = requests/minuto excedido (recuperable con espera)
                # Insufficient quota = sin créditos (no recuperable)
                is_rate_limit = (
                    "429" in error_text or 
                    "rate_limit" in error_text or 
                    "too many requests" in error_text or
                    error_code == "rate_limit_exceeded"
                )
                
                # Solo es quota exhausted si el código específico lo indica
                # NO confundir 429 (rate limit) con insufficient_quota
                is_quota_exhausted = (
                    error_code == "insufficient_quota" or
                    "billing" in error_text or
                    "quota exceeded" in error_text
                ) and not is_rate_limit  # ← CRÍTICO: Si es rate limit, NO es quota
                
                # Quota exhausted es no-recuperable (sin créditos/billing)
                if is_quota_exhausted:
                    logger.error("❌ OpenAI quota exhausted (insufficient_quota) - aborting retries")
                    raise ExternalServiceError(
                        service_name="openai",
                        message="OpenAI quota exhausted (insufficient_quota). Extraction aborted.",
                        original_error=e,
                    )
                
                # Rate limit (429) - usar backoff exponencial más largo
                if is_rate_limit:
                    # Backoff más agresivo para rate limits: 5s, 15s, 45s
                    wait_time = 5 * (3 ** attempt)
                    logger.warning(f"⚠️ Rate limit hit (429) on attempt {attempt + 1}/{max_retries}: {e}")
                else:
                    # Backoff normal para otros errores: 2s, 5s, 9s
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"⚠️ Function calling attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Function calling failed after {max_retries} attempts")
                    raise ExternalServiceError(
                        service_name="openai",
                        message=f"Function calling failed after {max_retries} attempts",
                        original_error=e,
                    )
    
    def _validate_and_structure_result(self, raw_result: Dict[str, Any]) -> RFXFunctionResult:
        """
        Validar resultado usando Pydantic y estructurar para BD
        
        Args:
            raw_result: Resultado crudo del function calling
            
        Returns:
            RFXFunctionResult validado
        """
        try:
            logger.info(f"🔍 Validating function calling result with Pydantic")
            
            # Validar con Pydantic
            validated = RFXFunctionResult(**raw_result)
            
            logger.info(f"✅ Pydantic validation successful - {len(validated.requested_products)} products")
            
            if self.debug_mode:
                logger.debug(f"🔍 Validated model: {validated.dict()}")
            
            return validated
            
        except ValidationError as e:
            logger.error(f"❌ Pydantic validation failed: {e}")
            logger.error(f"🔍 Raw result keys: {list(raw_result.keys())}")
            
            # Log detalles específicos de errores de validación
            for error in e.errors():
                logger.error(f"   - {error['loc']}: {error['msg']}")
            
            raise
    
    def _update_success_stats(self, response_time: float, validated_result: RFXFunctionResult):
        """Actualizar estadísticas de éxito"""
        self.extraction_stats["successful_extractions"] += 1
        
        # Calcular tiempo promedio de respuesta
        current_avg = self.extraction_stats["avg_response_time"]
        success_count = self.extraction_stats["successful_extractions"]
        
        self.extraction_stats["avg_response_time"] = (
            (current_avg * (success_count - 1) + response_time) / success_count
        )
        
        # Log estadísticas detalladas
        products_count = len(validated_result.requested_products)
        confidence = validated_result.extraction_confidence.overall_confidence
        
        logger.info(f"📊 EXTRACTION STATS:")
        logger.info(f"   Products extracted: {products_count}")
        logger.info(f"   Overall confidence: {confidence:.2f}")
        logger.info(f"   Response time: {response_time:.2f}s")
        logger.info(f"   Success rate: {self.get_success_rate():.1%}")
    
    def get_success_rate(self) -> float:
        """Calcular tasa de éxito"""
        total = self.extraction_stats["total_extractions"]
        if total == 0:
            return 0.0
        return self.extraction_stats["successful_extractions"] / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas completas del extractor"""
        return {
            **self.extraction_stats,
            "success_rate": self.get_success_rate(),
            "model": self.model,
            "debug_mode": self.debug_mode
        }
    
    def reset_stats(self):
        """Reiniciar estadísticas"""
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "validation_errors": 0,
            "openai_errors": 0,
            "avg_response_time": 0.0
        }
        logger.info(f"📊 Extraction stats reset")

# ============================================================================
# FUNCIÓN DE UTILIDAD PARA TESTING
# ============================================================================

def test_function_calling_extractor(document_text: str, openai_api_key: str) -> Dict[str, Any]:
    """
    Función de prueba para el extractor de function calling
    
    Args:
        document_text: Documento a procesar
        openai_api_key: Clave API de OpenAI
        
    Returns:
        Resultado de la extracción
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=openai_api_key)
    extractor = FunctionCallingRFXExtractor(client, model="gpt-4", debug_mode=True)
    
    try:
        result = extractor.extract_rfx_data(document_text)
        
        print(f"\n🎯 FUNCTION CALLING TEST RESULTS")
        print(f"=" * 50)
        print(f"✅ Extraction successful!")
        print(f"📊 Stats: {extractor.get_stats()}")
        print(f"\n📦 Products found: {len(result['products_data'])}")
        
        # Show first few products
        for i, product in enumerate(result['products_data'][:3], 1):
            print(f"   {i}. {product['product_name']} - {product['quantity']} {product['unit_of_measure']}")
        
        if len(result['products_data']) > 3:
            print(f"   ... and {len(result['products_data']) - 3} more products")
        
        return result
        
    except Exception as e:
        print(f"\n❌ FUNCTION CALLING TEST FAILED")
        print(f"=" * 50)
        print(f"Error: {e}")
        print(f"📊 Stats: {extractor.get_stats()}")
        raise
