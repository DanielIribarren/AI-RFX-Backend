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
    
    def extract_rfx_data(self, document_text: str, max_retries: int = 2) -> Dict[str, Any]:
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
            
            # Estadísticas de éxito
            response_time = time.time() - start_time
            self._update_success_stats(response_time, validated_result)
            
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
        return """<system>

<role>
Eres un especialista experto en extracción de datos RFX/RFP/RFQ con más de 10 años de experiencia en análisis de documentos empresariales. Tu expertise incluye:
- Análisis avanzado de documentos RFX de múltiples industrias (catering, construcción, IT, eventos, logística, marketing)
- Extracción de datos estructurados con precisión del 95%+
- Clasificación automática de tipos RFX y dominios industriales
- Diferenciación crítica entre información empresarial vs. personal
- Detección de criterios de evaluación y prioridades de proyecto
- Validación contextual y manejo robusto de información faltante
Tu enfoque es meticuloso, basado en evidencia y orientado a la precisión absoluta.
</role>

<context>
Trabajas en un sistema automatizado de procesamiento RFX que maneja 1000+ documentos por hora para empresas Fortune 500. Los documentos incluyen:
- RFPs (Request for Proposal), RFQs (Request for Quote), RFIs (Request for Information)
- Solicitudes de catering corporativo, construcción, IT services, eventos, logística
- Documentos en PDF, Word, Excel con calidad y estructura variable
- Información en español, inglés y formatos mixtos
- Rangos de presupuesto desde $500 hasta $500,000+
Tu objetivo es extraer información estructurada completa que alimentará sistemas CRM, automatización de propuestas y coordinación de equipos de ventas. La precisión es crítica porque los datos generan respuestas automáticas a clientes empresariales.
</context>

<instructions>
Sigue esta metodología paso a paso para extraer TODOS los campos del esquema JSON:

**PASO 1: ANÁLISIS Y CLASIFICACIÓN DEL DOCUMENTO**
- Identifica el TIPO DE RFX: RFP, RFQ, RFI, catering, evento, u otro
- Detecta el DOMINIO INDUSTRIAL: catering, construcción, eventos, IT services, logística, marketing, corporativo, bodas, conferencias, u otro
- Determina la PRIORIDAD si se menciona: low, medium, high, urgent
- Lee completamente identificando estructura y secciones clave

**PASO 2: EXTRACCIÓN DE INFORMACIÓN BÁSICA**
- **TITLE**: Título del proyecto o solicitud (crear uno descriptivo si no existe)
- **DESCRIPTION**: Descripción detallada del proyecto o evento
- **REQUIREMENTS**: Requerimientos técnicos, funcionales y restricciones específicas del cliente (NO descripciones generales)
- **REQUIREMENTS_CONFIDENCE**: Score 0.0-1.0 sobre la extracción de requirements

**PASO 3: PROCESAMIENTO ROBUSTO DE FECHAS EN ESPAÑOL**

⚠️ **MAPEO CRÍTICO DE MESES EN ESPAÑOL**:
```
enero = 01      febrero = 02    marzo = 03      abril = 04
mayo = 05       junio = 06      julio = 07      agosto = 08  
septiembre = 09 octubre = 10    noviembre = 11  diciembre = 12
```

**REGLAS DE PARSING UNIVERSALES**:
1. **Identificar mes**: Buscar cualquier nombre de mes en español
2. **Extraer día**: Número entre 1-31 cerca del mes  
3. **Determinar año**: Si no se especifica, usar 2025
4. **Formatear**: Siempre YYYY-MM-DD

**CAMPOS DE FECHA A EXTRAER**:
- **SUBMISSION_DEADLINE**: Fecha límite propuestas (ISO 8601: YYYY-MM-DDTHH:MM:SS)
- **EXPECTED_DECISION_DATE**: Fecha decisión (ISO 8601)
- **PROJECT_START_DATE**: Fecha inicio proyecto (ISO 8601)
- **PROJECT_END_DATE**: Fecha fin proyecto (ISO 8601)
- **DELIVERY_DATE**: Fecha entrega evento/servicio (YYYY-MM-DD)
- **DELIVERY_TIME**: Hora entrega (HH:MM)

📋 **EJEMPLOS SISTEMÁTICOS**:
  - "enero 15" → "2025-01-15"
  - "febrero 28" → "2025-02-28"
  - "marzo 10" → "2025-03-10"
  - "abril 5" → "2025-04-05"
  - "mayo 20" → "2025-05-20"
  - "junio 12" → "2025-06-12"
  - "julio 8" → "2025-07-08"
  - "agosto 25" → "2025-08-25"
  - "septiembre 3" → "2025-09-03"
  - "octubre 6" → "2025-10-06"
  - "noviembre 18" → "2025-11-18"
  - "diciembre 31" → "2025-12-31"

**VARIACIONES COMUNES**:
  - "15 de marzo" → "2025-03-15"
  - "el 10 de julio" → "2025-07-10"
  - "para agosto 5" → "2025-08-05"
  - "entrega septiembre 20" → "2025-09-20"

**PASO 4: EXTRACCIÓN DE PRESUPUESTO Y MONEDA**
- **BUDGET_RANGE_MIN**: Presupuesto mínimo mencionado
- **BUDGET_RANGE_MAX**: Presupuesto máximo mencionado
- **ESTIMATED_BUDGET**: Presupuesto estimado total
- **CURRENCY**: Código ISO 4217 (USD, EUR, GBP, MXN, CAD, etc.)
  - Símbolos: $ → USD, € → EUR, £ → GBP, CAD$ → CAD
  - Texto: "dólares" → USD, "euros" → EUR, "pesos" → MXN
  - DEFAULT: USD si no se especifica

**PASO 5: UBICACIONES DETALLADAS**
- **EVENT_LOCATION**: Ubicación completa del evento (dirección, venue, etc.)
- **EVENT_CITY**: Ciudad donde se realizará el evento
- **EVENT_STATE**: Estado, provincia o región del evento
- **EVENT_COUNTRY**: País del evento
- **LOCATION**: Ubicación general del proyecto (puede ser diferente del evento)

**PASO 6: PRODUCTOS Y SERVICIOS ESTRUCTURADOS**
- **REQUESTED_PRODUCTS**: Array completo con:
  - product_name: Nombre exacto del producto/servicio
  - quantity: Cantidad numérica
  - unit: unidades, personas, pax, kg, litros, horas, días, etc.
  - specifications: Especificaciones adicionales
  - category: comida, bebida, servicio, equipo, personal, decoración, transporte, otro

**PASO 7: CRITERIOS DE EVALUACIÓN**
- **EVALUATION_CRITERIA**: Array de criterios mencionados:
  - criterion: Nombre del criterio (precio, experiencia, calidad, etc.)
  - weight: Peso/porcentaje si se menciona
  - description: Descripción detallada del criterio

**PASO 8: INFORMACIÓN DE CONTACTO SEPARADA**
- **COMPANY_INFO**:
  - company_name: Nombre de la empresa/organización
  - company_email: Email corporativo general
  - company_phone: Teléfono principal de la empresa
  - department: Departamento que solicita
- **REQUESTER_INFO**:
  - requester_name: Nombre completo de la persona solicitante
  - requester_email: Email personal/profesional del solicitante
  - requester_phone: Teléfono directo del solicitante
  - requester_position: Cargo/puesto del solicitante

**PASO 9: METADATA Y ELEMENTOS ADICIONALES**
- **RFX_TYPE_DETECTED**: Tipo detectado basado en contenido
- **INDUSTRY_DOMAIN**: Dominio industrial detectado
- **SPECIAL_REQUIREMENTS**: Array de requerimientos especiales (halal, kosher, vegano, alergias, etc.)
- **ATTACHMENTS_MENTIONED**: Array de archivos adjuntos mencionados
- **REFERENCES**: Array de referencias a otros documentos o proyectos
- **ORIGINAL_TEXT_RELEVANT**: Fragmento más relevante del texto original

**PASO 10: CONFIDENCE SCORING COMPLETO**
- **OVERALL_CONFIDENCE**: Confianza general (0.0-1.0)
- **PRODUCTS_CONFIDENCE**: Confianza en productos extraídos
- **DATES_CONFIDENCE**: Confianza en fechas extraídas
- **CONTACT_CONFIDENCE**: Confianza en información de contacto
</instructions>

<criteria>
**EXTRACCIÓN COMPLETA OBLIGATORIA:**
- Procesar TODOS los campos del esquema JSON RFX_EXTRACTION_FUNCTION
- Campos requeridos: title, description, requested_products, extraction_confidence
- Usar null explícitamente para información no encontrada
- NUNCA omitir campos del esquema

**PRECISIÓN Y CALIDAD:**
- Overall confidence ≥ 0.75 para documentos procesables
- Products confidence ≥ 0.80 para especificaciones críticas
- Contact confidence ≥ 0.70 para información de contacto
- Requirements confidence ≥ 0.65 para requerimientos técnicos

**CLASIFICACIÓN CORRECTA:**
- RFX type detection con 95%+ precisión
- Industry domain con confidence ≥ 0.7
- Priority level basado en evidencia textual explícita
- Currency detection con validación contextual

**CONSISTENCIA TEMPORAL Y CONTEXTUAL:**
- Todas las fechas en formatos ISO 8601 correctos
- Fechas futuras y timeline realista
- Presupuestos alineados con scope y industria
- Ubicaciones verificables y completas
</criteria>

<examples>

**EJEMPLO 1 - RFQ CATERING CORPORATIVO COMPLETO:**
INPUT: "RFQ-2024-CAT-001: PDVSA requiere servicio de catering para Asamblea General de Accionistas el 15 de marzo 2024, 9:00 AM - 6:00 PM en Hotel Eurobuilding Caracas, Venezuela.
Productos requeridos: 200 desayunos ejecutivos, 300 almuerzos, 150 coffee breaks (mañana y tarde), servicio de meseros.
Presupuesto máximo: $25,000 USD. Criterios evaluación: 40% precio, 35% experiencia previa eventos corporativos, 25% calidad servicio.
Fecha límite propuestas: 1 marzo 2024. Decisión: 8 marzo 2024.
Contacto: María Rodríguez, Gerente Eventos Corporativos, maria.rodriguez@pdvsa.com, +58-212-708-1234.
Email corporativo: licitaciones@pdvsa.com. Adjuntar: certificaciones sanitarias, referencias clientes similares.
Requerimientos especiales: menú sin gluten disponible, personal bilingüe español/inglés."

OUTPUT:
{
"title": "RFQ-2024-CAT-001: Servicio de catering Asamblea General PDVSA",
"description": "Servicio de catering completo para Asamblea General de Accionistas de PDVSA el 15 de marzo 2024 en Hotel Eurobuilding Caracas",
"requirements": "Menú sin gluten disponible, personal bilingüe español/inglés, certificaciones sanitarias requeridas",
"requirements_confidence": 0.95,
"submission_deadline": "2024-03-01T23:59:59",
"expected_decision_date": "2024-03-08T17:00:00",
"project_start_date": "2024-03-15T09:00:00",
"project_end_date": "2024-03-15T18:00:00",
"delivery_date": "2024-03-15",
"delivery_time": "09:00",
"budget_range_max": 25000,
"estimated_budget": 25000,
"currency": "USD",
"event_location": "Hotel Eurobuilding Caracas, Venezuela",
"event_city": "Caracas",
"event_country": "Venezuela",
"requested_products": [
{
"product_name": "desayunos ejecutivos",
"quantity": 200,
"unit": "unidades",
"category": "comida"
},
{
"product_name": "almuerzos",
"quantity": 300,
"unit": "unidades",
"category": "comida"
},
{
"product_name": "coffee breaks",
"quantity": 150,
"unit": "servicios",
"specifications": "mañana y tarde",
"category": "servicio"
},
{
"product_name": "servicio de meseros",
"quantity": 1,
"unit": "servicios",
"category": "personal"
}
],
"evaluation_criteria": [
{
"criterion": "precio",
"weight": 40,
"description": "Criterio principal de evaluación"
},
{
"criterion": "experiencia previa eventos corporativos",
"weight": 35,
"description": "Experiencia en eventos corporativos similares"
},
{
"criterion": "calidad servicio",
"weight": 25,
"description": "Calidad del servicio ofrecido"
}
],
"priority": "high",
"company_info": {
"company_name": "PDVSA",
"company_email": "licitaciones@pdvsa.com",
"department": "Eventos Corporativos"
},
"requester_info": {
"requester_name": "María Rodríguez",
"requester_email": "maria.rodriguez@pdvsa.com",
"requester_phone": "+58-212-708-1234",
"requester_position": "Gerente Eventos Corporativos"
},
"metadata": {
"rfx_type_detected": "RFQ",
"industry_domain": "catering",
"special_requirements": ["menú sin gluten", "personal bilingüe español/inglés"],
"attachments_mentioned": ["certificaciones sanitarias", "referencias clientes similares"],
"original_text_relevant": "RFQ-2024-CAT-001: PDVSA requiere servicio de catering para Asamblea General..."
},
"extraction_confidence": {
"overall_confidence": 0.96,
"products_confidence": 0.94,
"dates_confidence": 0.98,
"contact_confidence": 0.97
}
}

javascript
Copy code

</examples>

</system>

"""
    
    def _get_user_prompt(self, document_text: str) -> str:
        """User prompt con el documento a analizar"""
        return f"""Analiza el siguiente documento RFX y extrae toda la información utilizando la función extract_rfx_data.

DOCUMENTO A ANALIZAR:
{document_text}

Instrucciones específicas para este documento:
- Busca TODOS los productos mencionados (comida, bebida, servicios, equipos)
- Identifica claramente la empresa solicitante y la persona de contacto
- Extrae fechas, ubicación y requerimientos especiales
- Asigna categorías apropiadas a cada producto
- Calcula cantidades exactas basándote en el número de personas y especificaciones

Usa la función extract_rfx_data para proporcionar la respuesta estructurada."""
    
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
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse function arguments as JSON: {e}")
                        logger.error(f"🔍 Raw arguments: {function_args}")
                        raise
                else:
                    raise ValueError("No function call found in OpenAI response")
                
            except Exception as e:
                self.extraction_stats["openai_errors"] += 1
                wait_time = (2 ** attempt) + 1  # Exponential backoff
                logger.warning(f"⚠️ Function calling attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Function calling failed after {max_retries} attempts")
                    raise
    
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
            
            logger.info(f"✅ Pydantic validation successful")
            logger.info(f"📦 Products validated: {len(validated.requested_products)}")
            logger.info(f"🏢 Company: {validated.company_info.company_name or 'Not found'}")
            logger.info(f"👤 Requester: {validated.requester_info.name or 'Not found'}")
            logger.info(f"📊 Overall confidence: {validated.extraction_confidence.overall_confidence:.2f}")
            
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
