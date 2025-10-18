"""
🎯 RFX Processor Service - Core business logic for RFX document processing
Extracts logic from rfx_webhook.py and improves it with better practices

REFACTORIZADO: Sistema modular con validaciones Pydantic, templates Jinja2,
modo debug con confidence scores y arquitectura extensible.
"""
import io
import re
import json
import PyPDF2
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
from openai import OpenAI
import zipfile
import mimetypes

# Feature flags for optional functionality
USE_OCR = os.getenv("RFX_USE_OCR", "true").lower() in {"1","true","yes","on"}
USE_ZIP = os.getenv("RFX_USE_ZIP", "true").lower() in {"1","true","yes","on"}

# Pydantic imports for robust validation
from pydantic import BaseModel, Field, validator, ValidationError

# Jinja2 imports for dynamic templates
from jinja2 import Template, Environment, BaseLoader

from backend.models.rfx_models import (
    RFXInput, RFXProcessed, RFXProductRequest, RFXType, RFXStatus,
    CompanyModel, RequesterModel, RFXHistoryEvent,
    # Legacy aliases for backwards compatibility
    ProductoRFX, TipoRFX, EstadoRFX
)
from backend.models.proposal_models import ProposalRequest, ProposalNotes
from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.utils.validators import EmailValidator, DateValidator, TimeValidator
from backend.utils.text_utils import clean_json_string
from backend.core.feature_flags import FeatureFlags
from backend.services.function_calling_extractor import FunctionCallingRFXExtractor

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 🎯 MODELOS PYDANTIC PARA VALIDACIÓN ESTRUCTURADA
# ============================================================================

class ExtractionConfidence(BaseModel):
    """Modelo para tracking de confidence scores en extracciones"""
    field_name: str = Field(..., description="Nombre del campo extraído")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    source: str = Field(..., description="Fuente de la extracción (AI, manual, fallback)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata adicional")

class ProductExtraction(BaseModel):
    """Modelo Pydantic para validación robusta de productos extraídos"""
    nombre: str = Field(..., min_length=1, max_length=200, description="Nombre del producto")
    cantidad: int = Field(..., ge=1, le=10000, description="Cantidad del producto")
    unidad: str = Field(..., min_length=1, max_length=50, description="Unidad de medida")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")
    
    @validator('nombre')
    def validate_nombre(cls, v):
        """Validador para nombre de producto"""
        if v.lower() in ['null', 'none', 'undefined', '']:
            raise ValueError('Nombre de producto no puede ser nulo o vacío')
        return v.strip().title()
    
    @validator('unidad')
    def validate_unidad(cls, v):
        """Validador para unidad de medida"""
        valid_units = ['unidades', 'personas', 'kg', 'litros', 'porciones', 'servicios', 'pax']
        v_clean = v.lower().strip()
        if v_clean not in valid_units:
            # Auto-map common variants
            unit_mapping = {
                'unidad': 'unidades', 'pcs': 'unidades', 'units': 'unidades',
                'persona': 'personas', 'ppl': 'personas', 'people': 'personas',
                'litro': 'litros', 'l': 'litros', 'lts': 'litros',
                'porcion': 'porciones', 'servicio': 'servicios'
            }
            v_clean = unit_mapping.get(v_clean, 'unidades')
        return v_clean

class ChunkExtractionResult(BaseModel):
    """Modelo para resultado de extracción por chunk con confidence tracking"""
    email: Optional[str] = Field(None, description="Email extraído")
    email_empresa: Optional[str] = Field(None, description="Email de la empresa")
    nombre_solicitante: Optional[str] = Field(None, description="Nombre del solicitante")
    nombre_empresa: Optional[str] = Field(None, description="Nombre de la empresa") 
    telefono_solicitante: Optional[str] = Field(None, description="Teléfono del solicitante")
    telefono_empresa: Optional[str] = Field(None, description="Teléfono de la empresa")
    cargo_solicitante: Optional[str] = Field(None, description="Cargo del solicitante")
    tipo_solicitud: Optional[str] = Field(None, description="Tipo de solicitud")
    productos: List[ProductExtraction] = Field(default_factory=list, description="Lista de productos")
    fecha: Optional[str] = Field(None, description="Fecha de entrega")
    hora_entrega: Optional[str] = Field(None, description="Hora de entrega")
    lugar: Optional[str] = Field(None, description="Lugar del evento")
    texto_original_relevante: Optional[str] = Field(None, description="Texto original relevante")
    
    # Campos de confidence y debugging
    confidence_scores: List[ExtractionConfidence] = Field(default_factory=list)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_index: int = Field(default=0, description="Índice del chunk procesado")

class ExtractionDebugInfo(BaseModel):
    """Información de debug para el modo debug"""
    chunk_count: int
    total_characters: int
    processing_time_seconds: float
    ai_calls_made: int
    retries_attempted: int
    confidence_summary: Dict[str, float]
    extraction_quality: str  # 'high', 'medium', 'low', 'fallback'

# ============================================================================
# 🏭 SISTEMA MODULAR DE EXTRACTORES
# ============================================================================

class ExtractionStrategy(Enum):
    """Estrategias de extracción disponibles"""
    CONSERVATIVE = "conservative"  # Alta precisión, baja sensibilidad
    BALANCED = "balanced"         # Balance entre precisión y sensibilidad 
    AGGRESSIVE = "aggressive"     # Alta sensibilidad, menor precisión

class BaseExtractor:
    """Extractor base con funcionalidad común"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.confidence_threshold = 0.7
        
    def calculate_confidence(self, extracted_value: Any, raw_text: str) -> float:
        """Calcula confidence score basado en heurísticas"""
        if not extracted_value:
            return 0.0
        
        # Heurísticas básicas para confidence
        confidence = 0.5  # Base confidence
        
        # Boost si el valor extraído aparece directamente en el texto
        if isinstance(extracted_value, str) and extracted_value.lower() in raw_text.lower():
            confidence += 0.3
            
        # Boost por longitud/format validity 
        if isinstance(extracted_value, str) and len(extracted_value) > 3:
            confidence += 0.1
            
        return min(confidence, 1.0)

class ProductExtractor(BaseExtractor):
    """Extractor especializado para productos con validación robusta"""
    
    def extract_products(self, chunk_data: Dict[str, Any], raw_text: str) -> List[ProductExtraction]:
        """Extrae y valida productos de los datos del chunk"""
        productos_raw = chunk_data.get("productos", [])
        productos_validated = []
        
        if self.debug_mode:
            logger.debug(f"🔍 ProductExtractor: procesando {len(productos_raw)} productos raw")
        
        for i, producto_raw in enumerate(productos_raw):
            try:
                # Intentar crear ProductExtraction con validación Pydantic
                if isinstance(producto_raw, dict):
                    # Extract and clean product data
                    nombre = self._extract_product_name(producto_raw)
                    cantidad = self._extract_product_quantity(producto_raw)
                    unidad = self._extract_product_unit(producto_raw)
                    
                    if nombre:  # Solo proceder si tenemos nombre válido
                        confidence = self.calculate_confidence(nombre, raw_text)
                        
                        producto = ProductExtraction(
                            nombre=nombre,
                            cantidad=cantidad,
                            unidad=unidad,
                            confidence=confidence
                        )
                        productos_validated.append(producto)
                        
                        if self.debug_mode:
                            logger.debug(f"✅ Producto {i+1} validado: {producto.nombre} (confidence: {confidence:.2f})")
                    else:
                        if self.debug_mode:
                            logger.warning(f"⚠️ Producto {i+1} rechazado: nombre inválido")
                            
                elif isinstance(producto_raw, str) and producto_raw.strip():
                    # Handle simple string products
                    confidence = self.calculate_confidence(producto_raw, raw_text)
                    producto = ProductExtraction(
                        nombre=producto_raw.strip(),
                        cantidad=1,
                        unidad="unidades",
                        confidence=confidence
                    )
                    productos_validated.append(producto)
                    
            except ValidationError as e:
                if self.debug_mode:
                    logger.warning(f"⚠️ Validación fallida para producto {i+1}: {e}")
                continue
        
        return productos_validated
    
    def _extract_product_name(self, producto_dict: Dict[str, Any]) -> Optional[str]:
        """Extrae nombre del producto desde múltiples claves posibles"""
        name_keys = ["nombre", "name", "product", "producto", "item"]
        for key in name_keys:
            if key in producto_dict and producto_dict[key]:
                name = str(producto_dict[key]).strip()
                if name and name.lower() not in ["null", "none", "undefined", ""]:
                    return name
        return None
    
    def _extract_product_quantity(self, producto_dict: Dict[str, Any]) -> int:
        """Extrae cantidad del producto con fallback a 1"""
        qty_keys = ["cantidad", "quantity", "qty", "count", "numero"]
        for key in qty_keys:
            if key in producto_dict and producto_dict[key]:
                try:
                    return max(1, int(float(producto_dict[key])))
                except (ValueError, TypeError):
                    continue
        return 1
    
    def _extract_product_unit(self, producto_dict: Dict[str, Any]) -> str:
        """Extrae unidad del producto con fallback a 'unidades'"""
        unit_keys = ["unidad", "unit", "units", "medida"]
        for key in unit_keys:
            if key in producto_dict and producto_dict[key]:
                return str(producto_dict[key]).strip().lower()
        return "unidades"

class SolicitanteExtractor(BaseExtractor):
    """Extractor especializado para información del solicitante"""
    
    def extract_solicitante_info(self, chunk_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Extrae información del solicitante con confidence tracking"""
        client_info = {}
        confidence_scores = []
        
        # Email extraction with confidence
        email = chunk_data.get("email_solicitante") or chunk_data.get("email")
        if email:
            confidence = self.calculate_confidence(email, raw_text)
            # Additional email validation boost
            if "@" in email and "." in email:
                confidence += 0.2
            client_info["email"] = email
            confidence_scores.append(ExtractionConfidence(
                field_name="email", confidence=min(confidence, 1.0), 
                source="AI", metadata={"format_valid": "@" in email}
            ))
        
        # Company email
        email_empresa = chunk_data.get("email_empresa")
        if email_empresa:
            confidence = self.calculate_confidence(email_empresa, raw_text)
            if "@" in email_empresa and "." in email_empresa:
                confidence += 0.2
            client_info["email_empresa"] = email_empresa
            confidence_scores.append(ExtractionConfidence(
                field_name="email_empresa", confidence=min(confidence, 1.0),
                source="AI", metadata={"format_valid": "@" in email_empresa}
            ))
        
        # Solicitante name extraction
        nombre_solicitante = chunk_data.get("nombre_solicitante")
        if nombre_solicitante:
            confidence = self.calculate_confidence(nombre_solicitante, raw_text)
            client_info["nombre_solicitante"] = nombre_solicitante
            confidence_scores.append(ExtractionConfidence(
                field_name="nombre_solicitante", confidence=confidence, source="AI"
            ))
        
        # Company name extraction
        nombre_empresa = chunk_data.get("nombre_empresa")
        if nombre_empresa:
            confidence = self.calculate_confidence(nombre_empresa, raw_text)
            client_info["nombre_empresa"] = nombre_empresa
            confidence_scores.append(ExtractionConfidence(
                field_name="nombre_empresa", confidence=confidence, source="AI"
            ))
        
        # Phone numbers
        for phone_field in ["telefono_solicitante", "telefono_empresa"]:
            phone = chunk_data.get(phone_field)
            if phone:
                confidence = self.calculate_confidence(phone, raw_text)
                client_info[phone_field] = phone
                confidence_scores.append(ExtractionConfidence(
                    field_name=phone_field, confidence=confidence, source="AI"
                ))
        
        # Position/cargo
        cargo = chunk_data.get("cargo_solicitante")
        if cargo:
            confidence = self.calculate_confidence(cargo, raw_text)
            client_info["cargo_solicitante"] = cargo
            confidence_scores.append(ExtractionConfidence(
                field_name="cargo_solicitante", confidence=confidence, source="AI"
            ))
        
        client_info["confidence_scores"] = confidence_scores
        return client_info

class EventExtractor(BaseExtractor):
    """Extractor especializado para información del evento"""
    
    def extract_event_info(self, chunk_data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Extrae información del evento con validación"""
        event_info = {}
        confidence_scores = []
        
        # Date extraction
        fecha = chunk_data.get("fecha")
        if fecha:
            confidence = self.calculate_confidence(fecha, raw_text)
            # Boost confidence for date-like patterns
            if re.match(r'\d{4}-\d{2}-\d{2}', str(fecha)):
                confidence += 0.2
            event_info["fecha"] = fecha
            confidence_scores.append(ExtractionConfidence(
                field_name="fecha", confidence=min(confidence, 1.0), source="AI"
            ))
        
        # Time extraction  
        hora_entrega = chunk_data.get("hora_entrega")
        if hora_entrega:
            confidence = self.calculate_confidence(hora_entrega, raw_text)
            # Boost confidence for time-like patterns
            if re.match(r'\d{1,2}:\d{2}', str(hora_entrega)):
                confidence += 0.2
            event_info["hora_entrega"] = hora_entrega
            confidence_scores.append(ExtractionConfidence(
                field_name="hora_entrega", confidence=min(confidence, 1.0), source="AI"
            ))
        
        # Location extraction
        lugar = chunk_data.get("lugar")
        if lugar:
            confidence = self.calculate_confidence(lugar, raw_text)
            event_info["lugar"] = lugar
            confidence_scores.append(ExtractionConfidence(
                field_name="lugar", confidence=confidence, source="AI"
            ))
        
        # Request type
        tipo_solicitud = chunk_data.get("tipo_solicitud")
        if tipo_solicitud:
            confidence = self.calculate_confidence(tipo_solicitud, raw_text)
            event_info["tipo_solicitud"] = tipo_solicitud
            confidence_scores.append(ExtractionConfidence(
                field_name="tipo_solicitud", confidence=confidence, source="AI"
            ))
        
        event_info["confidence_scores"] = confidence_scores
        return event_info

# ============================================================================
# 🎨 SISTEMA DE TEMPLATES JINJA2 PARA PROMPTS DINÁMICOS
# ============================================================================

class PromptTemplateManager:
    """Manager para templates de prompts usando Jinja2"""
    
    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())
        self._init_templates()
    
    def _init_templates(self):
        """Inicializa templates predefinidos"""
        self.templates = {
            'system_prompt': self._get_system_prompt_template(),
            'extraction_prompt': self._get_extraction_prompt_template(),
            'debug_prompt': self._get_debug_prompt_template()
        }
    
    def _get_system_prompt_template(self) -> str:
        """Template del system prompt con configuración dinámica"""
        return """Eres un especialista experto en análisis de documentos RFX, catering y eventos corporativos. 
Tu trabajo es extraer información EXACTA del texto proporcionado.

CONFIGURACIÓN:
- Estrategia: {{ strategy }}
- Modo Debug: {{ debug_mode }}
- Confidence Threshold: {{ confidence_threshold }}

REGLAS IMPORTANTES:
- Si NO encuentras un dato específico, usa null (no inventes información)
- Extrae solo lo que está explícitamente mencionado en el texto
- Para productos, incluye TODAS las cantidades y unidades mencionadas
- Preserva el texto original relevante para referencia
- Responde ÚNICAMENTE con JSON válido, sin texto adicional

{% if debug_mode %}
MODO DEBUG ACTIVADO:
- Incluye confidence scores para cada campo extraído
- Añade metadata de debugging en el JSON
- Registra heurísticas usadas para extraction decisions
{% endif %}"""

    def _get_extraction_prompt_template(self) -> str:
        """Template del prompt de extracción BALANCEADO para efectividad sin exceder tokens"""
        return """Extrae información del texto en formato JSON:

{
{% for field in required_fields %}
  "{{ field.name }}": "{{ field.description }}",
{% endfor %}
{% if include_products %}
  "productos": [
    {
      "nombre": "nombre exacto del producto/servicio",
      "cantidad": número_entero,
      "unidad": "unidades/personas/kg/litros/etc"
    }
  ],
{% endif %}
  "texto_original_relevante": "fragmento relevante del texto"
}

REGLAS CRÍTICAS:
- Si no encuentras un dato, usa null
- EMPRESA = compañía/organización (ej: Chevron, PDVSA). Si solo hay email "juan@chevron.com" → empresa: "Chevron"  
- SOLICITANTE = persona individual (ej: "Juan Pérez", "Sofia Elena Camejo")
- DIFERENCIA EMAILS: email_empresa (general: info@empresa.com) vs email_solicitante (personal: juan@empresa.com)

EJEMPLOS EMPRESA vs SOLICITANTE:
- "Cristóbal Lopenza, Chevron, Cristobal.Lopenza@chevron.com"
  → nombre_empresa: "Chevron"
  → nombre_solicitante: "Cristóbal Lopenza"  
  → email_solicitante: "Cristobal.Lopenza@chevron.com"

PARA PRODUCTOS: busca comida, bebida, materiales, equipos, servicios
PARA FECHAS: busca "entrega", "evento", "deadline" con fechas DD/MM/YYYY  
PARA HORAS: busca "hora", "entrega", "inicio" con formato HH:MM

TEXTO A ANALIZAR:
{{ chunk_text }}

Responde SOLO JSON:"""

    def _get_debug_prompt_template(self) -> str:
        """Template específico para modo debug con información detallada"""
        return """{{ base_prompt }}

INFORMACIÓN DE DEBUG ADICIONAL:
- Chunk Index: {{ chunk_index }}
- Chunk Size: {{ chunk_size }} caracteres
- Previous Extractions: {{ previous_extractions_count }}
- Context: {{ context_info }}

INSTRUCCIONES DE DEBUG:
1. Incluye confidence scores detallados para cada campo
2. Explica la lógica de extracción en extraction_notes
3. Identifica posibles ambigüedades en ambiguity_flags
4. Registra palabras clave encontradas en keywords_found

FORMATO JSON EXTENDIDO:
{
  ... campos normales ...,
  "debug_info": {
    "confidence_details": {
      "field_name": {"score": 0.85, "reasoning": "explicación"}
    },
    "extraction_notes": "notas detalladas del proceso",
    "ambiguity_flags": ["lista de ambigüedades detectadas"],
    "keywords_found": ["palabras clave que influyeron en la extracción"],
    "processing_time_estimate": "estimación del tiempo de procesamiento"
  }
}"""

    def render_prompt(self, template_name: str, **kwargs) -> str:
        """Renderiza un template con los parámetros dados"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' no encontrado")
        
        template = self.jinja_env.from_string(self.templates[template_name])
        return template.render(**kwargs)
    
    def get_system_prompt(self, strategy: ExtractionStrategy = ExtractionStrategy.BALANCED, 
                         debug_mode: bool = False, confidence_threshold: float = 0.7) -> str:
        """Genera system prompt dinámico"""
        return self.render_prompt('system_prompt', 
                                strategy=strategy.value,
                                debug_mode=debug_mode,
                                confidence_threshold=confidence_threshold)
    
    def get_extraction_prompt(self, chunk_text: str, strategy: ExtractionStrategy = ExtractionStrategy.BALANCED,
                            debug_mode: bool = False, chunk_index: int = 0, **kwargs) -> str:
        """Genera prompt de extracción dinámico"""
        
        # Definir campos requeridos con descripciones mejoradas para mejor diferenciación
        required_fields = [
            {"name": "nombre_empresa", "description": "EMPRESA: nombre de la compañía/organización (ej: Chevron, Microsoft, PDVSA). Si solo tienes un email como juan@chevron.com, extrae 'Chevron' del dominio", "format": None},
            {"name": "email_empresa", "description": "EMPRESA: email corporativo general de la empresa (ej: info@chevron.com, contacto@empresa.com). NO el email personal del solicitante", "format": None},
            {"name": "nombre_solicitante", "description": "PERSONA: nombre y apellido de la persona individual que hace la solicitud (ej: 'Sofia Elena Camejo Copello', 'Juan Pérez')", "format": None},
            {"name": "email_solicitante", "description": "PERSONA: email personal/de trabajo de la persona específica que solicita (ej: 'sofia.camejo@chevron.com', 'juan.perez@empresa.com')", "format": None},
            {"name": "telefono_solicitante", "description": "PERSONA: número telefónico personal de la persona que solicita", "format": None},
            {"name": "telefono_empresa", "description": "EMPRESA: número telefónico principal/general de la empresa", "format": None},
            {"name": "cargo_solicitante", "description": "PERSONA: puesto/cargo que ocupa la persona en la empresa (ej: 'Gerente', 'Asistente', 'Coordinador')", "format": None},
            {"name": "tipo_solicitud", "description": "tipo de solicitud de catering/evento", "format": None},
            {"name": "fecha", "description": "fecha de entrega del evento", "format": "YYYY-MM-DD"},
            {"name": "hora_entrega", "description": "hora de entrega del evento", "format": "HH:MM"},
            {"name": "lugar", "description": "dirección completa o ubicación donde se realizará el evento", "format": None},
            {"name": "currency", "description": "MONEDA: código de moneda ISO 4217 de 3 letras mencionada en el documento. INSTRUCCIONES ESPECÍFICAS: 1) Buscar símbolos monetarios: $ (verificar contexto para USD/MXN/CAD), €, £, ¥, CHF, etc. 2) Buscar menciones explícitas: 'dólares americanos'=USD, 'euros'=EUR, 'pesos mexicanos'=MXN, 'libras'=GBP, 'yenes'=JPY, 'francos suizos'=CHF. 3) Buscar códigos ISO: USD, EUR, MXN, CAD, GBP, JPY, CHF, AUD, BRL, COP, PEN, etc. 4) Analizar contexto geográfico: Venezuela/Colombia→USD, México→MXN, Europa→EUR, Reino Unido→GBP. 5) Si hay precios con $ sin contexto adicional→USD. 6) Si NO hay ninguna mención de moneda→USD (predeterminado). EJEMPLOS: '$100 USD'→USD, '€50'→EUR, '100 pesos'→MXN, '$1000 canadienses'→CAD, 'precio en libras £200'→GBP", "format": "3-letter ISO code"},
            # 🆕 MVP: Campo requirements para instrucciones específicas del cliente
            {"name": "requirements", "description": "REQUIREMENTS: Instrucciones, preferencias o requisitos específicos mencionados por el cliente (ej: 'empleados con +5 años experiencia', 'solo opciones vegetarianas', 'presupuesto máximo $1000', 'sin frutos secos por alergias'). Solo extraer si hay instrucciones claras y específicas, NO descripciones generales", "format": None},
            {"name": "requirements_confidence", "description": "CONFIDENCE: Nivel de confianza 0.0-1.0 sobre la extracción de requirements. 1.0 = muy específicos y claros, 0.5 = algo ambiguos, 0.0 = no hay requirements específicos", "format": "decimal 0.0-1.0"}
        ]
        
        # Categorías de productos
        product_categories = [
            "sandwiches", "bocadillos", "ensaladas", "bebidas", "café", "agua", 
            "postres", "menús", "comidas", "tequeños", "empanadas", "canapés"
        ]
        
        # Ejemplos de productos
        product_examples = [
            {"input": "Catering para 60 personas", "nombre": "Catering", "cantidad": 60, "unidad": "personas"},
            {"input": "30 sandwiches", "nombre": "Sandwiches", "cantidad": 30, "unidad": "unidades"},
            {"input": "Café para todos", "nombre": "Café", "cantidad": 1, "unidad": "servicio"}
        ]
        
        if debug_mode:
            # Usar template de debug
            base_prompt = self.render_prompt('extraction_prompt',
                                           required_fields=required_fields,
                                           include_products=True,
                                           product_categories=product_categories,
                                           product_examples=product_examples,
                                           strategy=strategy.value,
                                           debug_mode=debug_mode,
                                           chunk_text=chunk_text)
            
            return self.render_prompt('debug_prompt',
                                    base_prompt=base_prompt,
                                    chunk_index=chunk_index,
                                    chunk_size=len(chunk_text),
                                    previous_extractions_count=kwargs.get('previous_extractions_count', 0),
                                    context_info=kwargs.get('context_info', 'N/A'))
        else:
            # Usar template normal
            return self.render_prompt('extraction_prompt',
                                    required_fields=required_fields,
                                    include_products=True,
                                    product_categories=product_categories,
                                    product_examples=product_examples,
                                    strategy=strategy.value,
                                    debug_mode=debug_mode,
                                    chunk_text=chunk_text)

# ============================================================================
# 🔧 EXTRACTOR MODULAR MEJORADO
# ============================================================================

class ModularRFXExtractor:
    """Extractor modular que coordina todos los extractores especializados"""
    
    def __init__(self, strategy: ExtractionStrategy = ExtractionStrategy.BALANCED, debug_mode: bool = False):
        self.strategy = strategy
        self.debug_mode = debug_mode or FeatureFlags.eval_debug_enabled()
        
        # Inicializar extractores especializados
        self.product_extractor = ProductExtractor(debug_mode=self.debug_mode)
        self.solicitante_extractor = SolicitanteExtractor(debug_mode=self.debug_mode)
        self.event_extractor = EventExtractor(debug_mode=self.debug_mode)
        
        # Inicializar template manager
        self.template_manager = PromptTemplateManager()
        
        # Estadísticas de debugging
        self.extraction_stats = {
            'chunks_processed': 0,
            'ai_calls_made': 0,
            'retries_attempted': 0,
            'total_processing_time': 0.0
        }
        
        if self.debug_mode:
            logger.info(f"🔧 ModularRFXExtractor inicializado - Estrategia: {strategy.value}, Debug: {debug_mode}")
    
    def extract_from_chunk(self, chunk_text: str, chunk_index: int = 0, 
                          openai_client: OpenAI = None, openai_config: Any = None) -> ChunkExtractionResult:
        """
        Extrae información de un chunk usando el sistema modular mejorado
        
        Args:
            chunk_text: Texto del chunk a procesar
            chunk_index: Índice del chunk para tracking
            openai_client: Cliente OpenAI configurado
            openai_config: Configuración de OpenAI
            
        Returns:
            ChunkExtractionResult: Resultado validado con confidence scores
        """
        start_time = time.time()
        
        try:
            if self.debug_mode:
                logger.debug(f"🔍 Procesando chunk {chunk_index} ({len(chunk_text)} chars) con estrategia {self.strategy.value}")
            
            # Generar prompts dinámicos usando templates
            system_prompt = self.template_manager.get_system_prompt(
                strategy=self.strategy,
                debug_mode=self.debug_mode,
                confidence_threshold=0.7
            )
            
            extraction_prompt = self.template_manager.get_extraction_prompt(
                chunk_text=chunk_text,
                strategy=self.strategy,
                debug_mode=self.debug_mode,
                chunk_index=chunk_index,
                previous_extractions_count=self.extraction_stats['chunks_processed']
            )
            
            # Llamada a OpenAI con retry logic
            raw_result = self._call_openai_with_retry(
                openai_client=openai_client,
                openai_config=openai_config,
                system_prompt=system_prompt,
                user_prompt=extraction_prompt
            )
            
            # Procesar resultado con extractores especializados
            chunk_result = self._process_extraction_result(raw_result, chunk_text, chunk_index)
            
            # Actualizar estadísticas
            processing_time = time.time() - start_time
            self.extraction_stats['chunks_processed'] += 1
            self.extraction_stats['total_processing_time'] += processing_time
            
            if self.debug_mode:
                logger.debug(f"✅ Chunk {chunk_index} procesado en {processing_time:.3f}s - Productos: {len(chunk_result.productos)}")
            
            return chunk_result
            
        except Exception as e:
            logger.error(f"❌ Error procesando chunk {chunk_index}: {e}")
            # Retornar resultado vacío en caso de error
            return ChunkExtractionResult(
                chunk_index=chunk_index,
                extraction_metadata={
                    'error': str(e),
                    'processing_time': time.time() - start_time,
                    'fallback_used': True
                }
            )
    
    def _call_openai_with_retry(self, openai_client: OpenAI, openai_config: Any,
                               system_prompt: str, user_prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """Llama a OpenAI con retry logic y parsing robusto"""
        
        # 🔍 Debug: Log token estimates before sending
        system_tokens = len(system_prompt.split()) * 1.3  # Rough estimate
        user_tokens = len(user_prompt.split()) * 1.3
        total_estimated = system_tokens + user_tokens
        logger.info(f"📊 Token estimates - System: ~{int(system_tokens)}, User: ~{int(user_tokens)}, Total: ~{int(total_estimated)}")
        
        if total_estimated > 120000:  # 🚀 GPT-4o: 128k context - 4k response - 4k safety margin
            logger.warning(f"⚠️ Token estimate ({int(total_estimated)}) exceeds safe limit (120000). May fail.")
        
        for attempt in range(max_retries):
            try:
                self.extraction_stats['ai_calls_made'] += 1
                
                if self.debug_mode:
                    logger.debug(f"🤖 Llamada OpenAI intento {attempt + 1}/{max_retries}")
                
                response = openai_client.chat.completions.create(
                    model=openai_config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=openai_config.temperature,
                    max_tokens=openai_config.max_tokens,
                    response_format={"type": "json_object"},  # 🆕 JSON MODE: Sistema modular
                    timeout=30
                )
                
                output = response.choices[0].message.content.strip()
                
                # Parsear JSON con manejo robusto
                return self._parse_json_response(output)
                
            except Exception as e:
                self.extraction_stats['retries_attempted'] += 1
                
                # 🔍 Enhanced error logging
                error_type = type(e).__name__
                error_msg = str(e)
                
                # Special handling for token limit errors
                if "maximum context length" in error_msg or "context_length_exceeded" in error_msg:
                    logger.error(f"❌ TOKEN LIMIT EXCEEDED - {error_msg}")
                    logger.error(f"📊 Estimated tokens: {int(total_estimated)}, prompt lengths: system={len(system_prompt)}, user={len(user_prompt)}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    if self.debug_mode:
                        logger.warning(f"⚠️ Intento {attempt + 1} falló: {error_type}: {error_msg}, reintentando en {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Todos los intentos OpenAI fallaron: {error_type}: {error_msg}")
                    raise
    
    def _parse_json_response(self, output: str) -> Dict[str, Any]:
        """Parsea respuesta JSON con manejo robusto de errores"""
        # Extraer JSON del output
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = output[json_start:json_end]
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Intentar limpiar JSON
                json_str = clean_json_string(json_str)
                return json.loads(json_str)
        else:
            raise ValueError("No se encontró estructura JSON válida en la respuesta")
    
    def _process_extraction_result(self, raw_result: Dict[str, Any], chunk_text: str, 
                                 chunk_index: int) -> ChunkExtractionResult:
        """Procesa resultado raw usando extractores especializados"""
        
        # Extraer productos con validación Pydantic
        productos = self.product_extractor.extract_products(raw_result, chunk_text)
        
        # Extraer información del cliente
        client_info = self.solicitante_extractor.extract_solicitante_info(raw_result, chunk_text)
        
        # Extraer información del evento
        event_info = self.event_extractor.extract_event_info(raw_result, chunk_text)
        
        # Combinar confidence scores
        all_confidence_scores = []
        all_confidence_scores.extend(client_info.get('confidence_scores', []))
        all_confidence_scores.extend(event_info.get('confidence_scores', []))
        for producto in productos:
            all_confidence_scores.append(ExtractionConfidence(
                field_name=f"producto_{producto.nombre}",
                confidence=producto.confidence,
                source="ProductExtractor"
            ))
        
        # Construir resultado final
        result = ChunkExtractionResult(
            # Información del solicitante y empresa
            email=client_info.get('email'),
            email_empresa=client_info.get('email_empresa'),
            nombre_solicitante=client_info.get('nombre_solicitante'),
            nombre_empresa=client_info.get('nombre_empresa'),
            telefono_solicitante=client_info.get('telefono_solicitante'),
            telefono_empresa=client_info.get('telefono_empresa'),
            cargo_solicitante=client_info.get('cargo_solicitante'),
            
            # Información del evento
            fecha=event_info.get('fecha'),
            hora_entrega=event_info.get('hora_entrega'),
            lugar=event_info.get('lugar'),
            tipo_solicitud=event_info.get('tipo_solicitud'),
            
            # Productos validados
            productos=productos,
            
            # Texto original
            texto_original_relevante=raw_result.get('texto_original_relevante'),
            
            # Metadata de debugging
            confidence_scores=all_confidence_scores,
            chunk_index=chunk_index,
            extraction_metadata={
                'strategy': self.strategy.value,
                'debug_mode': self.debug_mode,
                'productos_count': len(productos),
                'client_fields_found': len([k for k, v in client_info.items() if v and k != 'confidence_scores']),
                'event_fields_found': len([k for k, v in event_info.items() if v and k != 'confidence_scores']),
                'raw_result_keys': list(raw_result.keys()) if self.debug_mode else None
            }
        )
        
        return result
    
    def get_extraction_summary(self) -> ExtractionDebugInfo:
        """Retorna resumen de extracción para debugging"""
        
        # Calcular confidence promedio
        avg_confidence = 0.0
        if self.extraction_stats['chunks_processed'] > 0:
            avg_confidence = 0.8  # Placeholder, calcular de confidence_scores reales
        
        # Determinar calidad de extracción
        quality = "high"
        if avg_confidence < 0.5:
            quality = "low"
        elif avg_confidence < 0.7:
            quality = "medium"
        
        return ExtractionDebugInfo(
            chunk_count=self.extraction_stats['chunks_processed'],
            total_characters=0,  # Se calculará en el uso
            processing_time_seconds=self.extraction_stats['total_processing_time'],
            ai_calls_made=self.extraction_stats['ai_calls_made'],
            retries_attempted=self.extraction_stats['retries_attempted'],
            confidence_summary={'average': avg_confidence},
            extraction_quality=quality
        )


class RFXProcessorService:
    """Service for processing RFX documents from PDF to structured data"""
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = OpenAI(api_key=self.openai_config.api_key)
        self.db_client = get_database_client()
        
        # Validation helpers (legacy - mantenemos para compatibilidad)
        self.email_validator = EmailValidator()
        self.date_validator = DateValidator()
        self.time_validator = TimeValidator()
        
        # 🆕 NUEVO SISTEMA MODULAR
        # Inicializar extractor modular con configuración dinámica
        debug_mode = FeatureFlags.eval_debug_enabled()
        extraction_strategy = self._get_extraction_strategy()
        
        self.modular_extractor = ModularRFXExtractor(
            strategy=extraction_strategy,
            debug_mode=debug_mode
        )
        
        # 🚀 FUNCTION CALLING EXTRACTOR (Fase 2B)
        # Inicializar solo si está habilitado por feature flag
        self.function_calling_extractor = None
        if FeatureFlags.function_calling_enabled():
            try:
                self.function_calling_extractor = FunctionCallingRFXExtractor(
                    openai_client=self.openai_client,
                    model=self.openai_config.model,
                    debug_mode=debug_mode
                )
                logger.info("🚀 Function Calling Extractor initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Function Calling Extractor initialization failed: {e}")
                logger.info("📋 Falling back to JSON mode extraction")
        
        # Estadísticas de procesamiento para debugging
        self.processing_stats = {
            'total_documents_processed': 0,
            'chunks_processed': 0,
            'average_confidence': 0.0,
            'fallback_usage_count': 0
        }
        
        logger.info(f"🚀 RFXProcessorService inicializado - Estrategia: {extraction_strategy.value}, Debug: {debug_mode}")
    
    def _get_extraction_strategy(self) -> ExtractionStrategy:
        """Determina estrategia de extracción basada en configuración"""
        # Puedes añadir feature flags para controlar la estrategia
        if FeatureFlags.eval_debug_enabled():
            return ExtractionStrategy.AGGRESSIVE  # Más sensible en modo debug
        else:
            return ExtractionStrategy.BALANCED    # Balance por defecto
    
    def process_rfx_document(self, rfx_input: RFXInput, pdf_content: bytes) -> RFXProcessed:
        """
        Main processing pipeline: PDF → Text → AI Analysis → Structured Data
        """
        try:
            logger.info(f"🚀 Starting RFX processing for: {rfx_input.id}")
            
            # Step 1: Extract text from document
            extracted_text = self._extract_text_from_document(pdf_content)
            logger.info(f"📄 Text extracted: {len(extracted_text)} characters")
            
            # Store extracted text in RFXInput for later use
            rfx_input.extracted_content = extracted_text
            
            # Step 2: Process with AI
            raw_data = self._process_with_ai(extracted_text)
            logger.info(f"🤖 AI processing completed")
            
            # Step 3: Validate and clean data (enhanced with modular data)
            validated_data = self._validate_and_clean_data(raw_data, rfx_input.id)
            logger.info(f"✅ Data validated successfully")
            
            # Log modular processing statistics if available
            if self.modular_extractor.debug_mode and 'modular_debug_info' in raw_data:
                debug_info = raw_data['modular_debug_info']
                logger.info(f"📊 Modular processing stats: Strategy={debug_info['extraction_strategy']}, Time={debug_info['total_processing_time']:.3f}s")
                
                # Update service-level statistics
                self.processing_stats['total_documents_processed'] += 1
                if debug_info['extraction_summary']['extraction_quality'] == 'fallback':
                    self.processing_stats['fallback_usage_count'] += 1
            
            # Step 3.5: Intelligent RFX evaluation (if enabled)
            evaluation_metadata = self._evaluate_rfx_intelligently(validated_data, rfx_input.id)
            
            # Step 4: Create structured RFX object
            rfx_processed = self._create_rfx_processed(validated_data, rfx_input, evaluation_metadata)
            
            # Step 5: Save to database
            self._save_rfx_to_database(rfx_processed)
            
            # Step 6: RFX processing completed - Proposal generation will be handled separately by user request
            
            logger.info(f"✅ RFX processing completed successfully: {rfx_input.id}")
            return rfx_processed
            
        except Exception as e:
            logger.error(f"❌ RFX processing failed for {rfx_input.id}: {e}")
            raise
    
    def _extract_text_from_document(self, pdf_content: bytes) -> str:
        """Extract text content from PDF bytes or other file types"""
        try:
            logger.info(f"📄 Starting document text extraction, file size: {len(pdf_content)} bytes")
            
            # Try to detect file type from content
            if pdf_content.startswith(b'%PDF'):
                logger.info("📄 Detected PDF file")
                # This is a PDF file
                pdf_file = io.BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text_pages = []
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text_pages.append(page_text)
                    logger.debug(f"📄 Page {i+1} extracted {len(page_text)} characters")
                
                full_text = "\n".join(text_pages)
                
                if not full_text.strip() or len(re.sub(r"\s+", "", full_text)) < 50:
                    # Attempt OCR for scanned PDFs
                    ocr_text = self._extract_text_with_ocr(pdf_content, kind="pdf")
                    if ocr_text.strip():
                        logger.info("🧠 Fallback OCR applied: PDF had no embedded text")
                        return ocr_text
                    logger.error("❌ No text extracted from PDF (even after OCR)")
                    raise ValueError("No text could be extracted from PDF")
                
                logger.info(f"✅ PDF extraction successful: {len(full_text)} total characters")
                logger.debug(f"📄 PDF text preview: {full_text[:500]}...")
                return full_text
                
            elif pdf_content.startswith(b'PK'):
                logger.info("📄 Detected DOCX file (ZIP-based)")
                # This looks like a DOCX file (ZIP format)
                try:
                    from docx import Document
                    
                    # Create a document from the bytes
                    doc_file = io.BytesIO(pdf_content)
                    doc = Document(doc_file)
                    
                    # Extract text from all paragraphs
                    paragraphs = []
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            paragraphs.append(paragraph.text.strip())
                    
                    # Extract text from tables
                    table_texts = []
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                if cell.text.strip():
                                    table_texts.append(cell.text.strip())
                    
                    # Combine all text
                    all_text = "\n".join(paragraphs + table_texts)
                    
                    if not all_text.strip():
                        logger.error("❌ No text extracted from DOCX")
                        raise ValueError("No text could be extracted from DOCX")
                    
                    logger.info(f"✅ DOCX extraction successful: {len(all_text)} total characters")
                    logger.info(f"📊 Extracted {len(paragraphs)} paragraphs and {len(table_texts)} table cells")
                    logger.debug(f"📄 DOCX text preview: {all_text[:500]}...")
                    
                    return all_text
                    
                except ImportError:
                    logger.error("❌ python-docx not installed, falling back to text decode")
                    # Fallback to text decoding
                except Exception as e:
                    logger.error(f"❌ DOCX extraction failed: {e}, falling back to text decode")
            
            # Try to decode as text file
            logger.info("📄 Attempting text file decoding")
            try:
                text_content = pdf_content.decode('utf-8')
                if not text_content.strip():
                    raise ValueError("Text file is empty")
                logger.info(f"✅ UTF-8 text extraction successful: {len(text_content)} characters")
                logger.debug(f"📄 Text preview: {text_content[:500]}...")
                return text_content
            except UnicodeDecodeError:
                logger.warning("⚠️ UTF-8 decode failed, trying other encodings")
                # Try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        text_content = pdf_content.decode(encoding)
                        if text_content.strip():
                            logger.info(f"✅ Text extraction successful with {encoding}: {len(text_content)} characters")
                            logger.debug(f"📄 Text preview: {text_content[:500]}...")
                            return text_content
                    except UnicodeDecodeError:
                        continue
                        
                logger.error("❌ All text decoding attempts failed")
                raise ValueError("Unable to decode file content")
            
        except Exception as e:
            logger.error(f"❌ Text extraction failed: {e}")
            # 🔍 Debug: Log more details about the failure
            logger.error(f"📄 File size: {len(pdf_content)} bytes")
            logger.error(f"📄 File starts with: {pdf_content[:50]}")
            logger.error(f"📄 Error type: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to extract text from file: {e}")
    
    def _process_with_ai(self, text: str) -> Dict[str, Any]:
        """🚀 REFACTORIZADO: Process COMPLETE text with single AI call - NO CHUNKING"""
        try:
            start_time = time.time()
            word_count = len(text.split())
            estimated_tokens = int(word_count * 1.2)  # Conservative estimate
            
            logger.info(f"🚀 Starting COMPLETE AI processing for text of {len(text)} characters (~{estimated_tokens} tokens)")
            
            # 🔍 DEBUG: Log text preview and key indicators
            logger.info(f"📄 TEXT_PREVIEW: {text[:500]}...")
            
            # Quick analysis for completeness validation
            text_lower = text.lower()
            keywords_found = []
            if "fecha" in text_lower: keywords_found.append("fecha")
            if "hora" in text_lower: keywords_found.append("hora") 
            if "entrega" in text_lower: keywords_found.append("entrega")
            if "productos" in text_lower or "servicios" in text_lower: keywords_found.append("productos")
            
            logger.info(f"🗓️ KEYWORDS_FOUND: {keywords_found}" if keywords_found else "⚠️ NO_KEYWORDS_FOUND")
            
            # Validate text size for model limits (GPT-4o: 128K tokens)
            if estimated_tokens > 120000:
                logger.warning(f"⚠️ Text might exceed model limits: {estimated_tokens} tokens")
                # Fallback to chunking only if absolutely necessary
                return self._process_with_ai_chunked_fallback(text)
            
            # 🎯 ESTRATEGIA DE EXTRACCIÓN CON FALLBACKS
            extracted_data = None
            
            # 1️⃣ PRIMERA OPCIÓN: Function Calling (más robusto)
            if self.function_calling_extractor and FeatureFlags.function_calling_enabled():
                try:
                    logger.info(f"🚀 Attempting Function Calling extraction...")
                    db_result = self.function_calling_extractor.extract_rfx_data(text)
                    
                    # Convertir resultado de function calling a formato legacy
                    extracted_data = self._convert_function_calling_to_legacy_format(db_result)
                    logger.info(f"✅ Function Calling extraction successful")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Function Calling extraction failed: {e}")
                    if not FeatureFlags.json_mode_fallback_enabled():
                        raise  # Si no hay fallback habilitado, propagar error
            
            # 2️⃣ SEGUNDA OPCIÓN: JSON Mode (sistema actual)
            if not extracted_data and FeatureFlags.json_mode_fallback_enabled():
                try:
                    logger.info(f"🔄 Falling back to JSON Mode extraction...")
                    extracted_data = self._extract_complete_with_ai(text)
                    logger.info(f"✅ JSON Mode extraction successful")
                    
                except Exception as e:
                    logger.warning(f"⚠️ JSON Mode extraction failed: {e}")
            
            # 3️⃣ TERCERA OPCIÓN: Legacy fallback
            if not extracted_data:
                logger.warning(f"🔄 Falling back to legacy extraction...")
                extracted_data = self._process_with_ai_chunked_fallback(text)
            
            # 🔍 Validate completeness automatically (for metrics only)
            completeness_result = self._validate_product_completeness(extracted_data, text)
            
            # Calculate processing metrics
            processing_time = time.time() - start_time
            self.processing_stats['total_documents_processed'] += 1
            
            # Enhanced logging
            products_found = len(extracted_data.get('productos', []))
            logger.info(f"✅ COMPLETE AI processing completed in {processing_time:.3f}s")
            logger.info(f"📊 Products found: {products_found}")
            logger.info(f"💰 Cost optimization: Single call vs multiple chunks")
            
            if extracted_data.get("productos"):
                product_names = [p['nombre'] for p in extracted_data['productos']]
                logger.info(f"📦 Product names: {product_names}")
            else:
                logger.error(f"❌ NO PRODUCTS found!")
                
            # Add completeness validation results
            extracted_data['completeness_validation'] = completeness_result
            extracted_data['processing_metrics'] = {
                'processing_time': processing_time,
                'estimated_tokens': estimated_tokens,
                'single_call': True,
                'cost_optimized': True
            }
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ COMPLETE AI processing failed: {e}")
            self.processing_stats['fallback_usage_count'] += 1
            
            # Fallback to chunking only as last resort
            logger.warning(f"🔄 Fallback to chunked processing due to error")
            
            # Return minimal structure instead of None to prevent downstream errors
            return {
                "productos": [],
                "email": "",
                "fecha_entrega": "",
                "hora_entrega": "",
                "lugar": "",
                "nombre_solicitante": "",
                "currency": "USD",
                "processing_error": True,
                "error_message": str(e)
            }
    
    def _extract_complete_with_ai(self, text: str) -> Dict[str, Any]:
        """🎯 NUEVA FUNCIÓN: Extrae datos con una sola llamada a IA - SIN CHUNKING"""
        try:
            # 🎨 SYSTEM PROMPT PROFESIONAL (del sistema legacy optimizado)
            system_prompt = """<rfx_analysis_system>
  <identity>
    <role>Especialista experto en análisis inteligente de documentos RFX con capacidades avanzadas de evaluación automática</role>
    <version>4.0</version>
    <capabilities>
      <capability priority="critical">Evaluación automática de calidad con 95%+ precisión</capability>
      <capability priority="critical">Detección automática de dominio multi-industria</capability>
      <capability priority="high">Extracción de datos estructurados con validación contextual</capability>
      <capability priority="high">Generación de insights específicos por industria</capability>
      <capability priority="medium">Análisis de consistencia con reasoning avanzado</capability>
      <capability priority="medium">Manejo robusto de errores y casos edge</capability>
    </capabilities>
    <specializations>
      <domain confidence_threshold="0.7">catering</domain>
      <domain confidence_threshold="0.7">construccion</domain>
      <domain confidence_threshold="0.7">it_services</domain>
      <domain confidence_threshold="0.7">eventos</domain>
      <domain confidence_threshold="0.7">logistica</domain>
      <domain confidence_threshold="0.7">marketing</domain>
      <domain confidence_threshold="0.5">otro</domain>
    </specializations>
  </identity>

  <core_principles>
    <principle name="precision_absoluta">
      <rule>Solo extraigo información explícitamente presente en el texto</rule>
      <fallback>Uso null cuando no hay información clara</fallback>
      <validation>Nunca inventar o asumir información no presente</validation>
    </principle>
    <principle name="validacion_contextual">
      <rule>Cada dato debe tener coherencia interna y externa</rule>
      <cross_validation>Verificar consistencia entre campos relacionados</cross_validation>
      <error_detection>Identificar y reportar inconsistencias</error_detection>
    </principle>
    <principle name="diferenciacion_critica">
      <rule>Distinguir claramente entre información empresarial vs personal</rule>
      <separation_logic>Aplicar lógica específica para cada tipo de información</separation_logic>
      <validation>Verificar correcta categorización de datos</validation>
    </principle>
    <principle name="completitud_total">
      <rule>ENCONTRAR Y EXTRAER **TODOS** los productos/servicios mencionados sin excepción</rule>
      <pattern_recognition>Si ves listas numeradas (1., 2., 3...) o con viñetas (-, •), extrae TODOS los ítems</pattern_recognition>
      <validation>NO te detengas en los primeros productos encontrados</validation>
      <completeness_check>Incluye comida, bebidas, equipos, servicios, personal, extras</completeness_check>
      <verification>Verifica completitud antes de responder - si hay 15 productos, debes encontrar los 15</verification>
    </principle>
  </core_principles>

  <output_requirements>
    <format>JSON estructurado válido únicamente - SIN markdown fences</format>
    <json_mode>Responder ÚNICAMENTE con objeto JSON válido, sin ```json ni texto adicional</json_mode>
    <null_handling>Campos null cuando no hay información explícita</null_handling>
    <evidence_based>Incluir fragmento de texto original como evidencia</evidence_based>
    <confidence_required>Score de confianza obligatorio para cada extracción</confidence_required>
    <error_transparency>Reportar problemas y limitaciones encontradas</error_transparency>
  </output_requirements>

  <data_extraction_rules>
    <information_hierarchy>
      <level_1 priority="critical">
        <field>nombre_empresa</field>
        <field>productos_servicios</field>
        <field>moneda</field>
        <field>fecha_requerida</field>
        <field>ubicacion_servicio</field>
      </level_1>
      <level_2 priority="high">
        <field>nombre_solicitante</field>
        <field>email_solicitante</field>
        <field>telefono_solicitante</field>
        <field>tipo_solicitud</field>
      </level_2>
      <level_3 priority="medium">
        <field>requisitos_especiales</field>
        <field>especificaciones</field>
        <field>presupuesto</field>
      </level_3>
    </information_hierarchy>

    <validation_protocols>
      <email_validation>
        <pattern>RFC 5322 compliant</pattern>
        <business_logic>Distinguir emails corporativos vs personales</business_logic>
        <domain_extraction>Extraer empresa del dominio si aplicable</domain_extraction>
      </email_validation>
      <date_validation>
        <formats>ISO 8601, DD/MM/YYYY, DD-MM-YYYY, natural language</formats>
        <future_check>Validar que fechas sean futuras</future_check>
        <reasonability>Verificar lead time apropiado por industria</reasonability>
      </date_validation>
      <quantity_validation>
        <numeric_extraction>Identificar números y unidades</numeric_extraction>
        <context_validation>Verificar coherencia con tipo de producto</context_validation>
        <range_checking>Aplicar rangos razonables por dominio</range_checking>
      </quantity_validation>
    </validation_protocols>
  </data_extraction_rules>
</rfx_analysis_system>"""
        
            # 🎯 USER PROMPT con el documento a analizar
            user_prompt = f"""Analiza cuidadosamente este texto de un documento de catering/evento y extrae la siguiente información en formato JSON:

        {{
        "nombre_empresa": "EMPRESA: nombre de la compañía/organización (ej: Chevron, Microsoft). Si solo hay email como juan@chevron.com, extrae 'Chevron' del dominio (null si no se encuentra)",
        "email_empresa": "EMPRESA: email corporativo general de la empresa. NO el email personal del solicitante (null si no se encuentra)",
        "nombre_solicitante": "PERSONA: nombre y apellido de la persona individual que hace la solicitud (null si no se encuentra)",
        "email_solicitante": "PERSONA: email personal/de trabajo de la persona específica que solicita (null si no se encuentra)",
        "telefono_solicitante": "PERSONA: número telefónico personal de la persona que solicita (null si no se encuentra)",
        "telefono_empresa": "EMPRESA: número telefónico principal/general de la empresa (null si no se encuentra)",
        "cargo_solicitante": "PERSONA: puesto/cargo que ocupa la persona en la empresa (null si no se encuentra)",
        "tipo_solicitud": "tipo de solicitud de catering/evento (null si no se encuentra)",
        "productos": [
            {{
            "nombre": "nombre exacto del producto/servicio",
            "cantidad": número_entero,
            "unidad": "unidades/personas/kg/litros/etc"
            }}
        ],
        "fecha": "fecha de entrega en formato YYYY-MM-DD (null si no se encuentra)",
        "hora_entrega": "hora de entrega en formato HH:MM (null si no se encuentra)",
        "lugar": "dirección completa o ubicación del evento (null si no se encuentra)",
        "currency": "MONEDA: código de moneda ISO 4217 de 3 letras mencionada en el documento (ej: USD, EUR, MXN, CAD). Buscar símbolos como $, €, £, CAD$, USD$, menciones de 'dólares', 'euros', 'pesos', etc. Si no se encuentra específicamente, usar 'USD' como predeterminado",
        "requirements": "INSTRUCCIONES ESPECÍFICAS, preferencias o restricciones mencionadas por el cliente. NO incluir descripción general del servicio (null si no se encuentra)",
        "texto_original_relevante": "fragmento del texto donde encontraste la información principal",
        "confidence_score": número_decimal_entre_0_y_1_indicando_confianza_en_extracción
        }}

        ═══════════════════════════════════════════════════════════════════════════════════
🎯 INSTRUCCIONES CRÍTICAS PARA COMPLETITUD DE PRODUCTOS
        ═══════════════════════════════════════════════════════════════════════════════════

**REGLAS ABSOLUTAS PARA PRODUCTOS:**
✅ BUSCA Y EXTRAE **TODOS** LOS PRODUCTOS/SERVICIOS MENCIONADOS SIN EXCEPCIÓN
✅ Si ves secciones con emojis (🥗, 🍽️, 🍰, ☕, 🥂), extrae TODO lo que aparece bajo cada sección
✅ Si ves listas numeradas o con viñetas, extrae TODOS los ítems de la lista completa
✅ Incluye TODAS las entradas, platos principales, postres, bebidas, servicios, extras
✅ NO te detengas en los primeros productos - busca por TODO el documento
✅ Cada línea con comida/bebida/servicio = un producto en la lista

**EJEMPLOS DE PRODUCTOS A BUSCAR:**
- Comida: tequeños, empanadas, canapés, brochetas, ceviche, pollo, res, lasaña
- Bebidas: jugos, agua, café, té, refrescos 
- Servicios: meseros, montaje, coordinación, transporte
- Extras: mantelería, copas, vajilla, decoración

        REGLAS CRÍTICAS PARA EMPRESA vs SOLICITANTE:
        - EMPRESA = compañía/organización que solicita el servicio
        - SOLICITANTE = persona individual dentro de la empresa
        - Si ves "sofia.elena@chevron.com" → nombre_empresa="Chevron", email_solicitante="sofia.elena@chevron.com"

        INSTRUCCIONES ESPECÍFICAS PARA PRODUCTOS:
        - Busca CUALQUIER tipo de comida, bebida o servicio de catering
        - Incluye cantidades: números seguidos de "personas", "pax", "unidades", "kg", "litros"
        - Si solo encuentras "para X personas" sin productos específicos, usa "Catering para X personas"
        - SIEMPRE incluye al menos un producto si el texto menciona comida o catering

        CONFIDENCE SCORE (0.0 - 1.0):
        - 0.9-1.0: Información muy clara y explícita
        - 0.7-0.8: Información clara con interpretación mínima
        - 0.5-0.6: Información implícita o requiere interpretación
        - 0.3-0.4: Información ambigua o parcial
        - 0.0-0.2: Información muy incierta o extrapolada

        TEXTO A ANALIZAR:
{text}

Responde SOLO con el JSON solicitado - asegúrate de haber encontrado TODOS los productos mencionados:"""

            # 🚀 Llamada única a OpenAI con JSON MODE (elimina markdown fences)
            logger.info(f"🤖 Sending to OpenAI: System prompt ({len(system_prompt)} chars), User prompt ({len(user_prompt)} chars)")
            logger.info(f"🔧 Using JSON mode to prevent markdown fences")
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_config.model,  # GPT-4o
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.openai_config.temperature,
                max_tokens=self.openai_config.max_tokens,
                response_format={"type": "json_object"},  # 🆕 JSON MODE: Elimina ```json fences
                timeout=45  # Increased timeout for single call
            )
            
            output = response.choices[0].message.content.strip()
            logger.info(f"🤖 OpenAI raw response length: {len(output)} characters")
            
            # Log first 500 chars of response for debugging
            response_preview = output[:500].replace('\n', ' ')
            logger.info(f"📝 OpenAI response preview: {response_preview}...")
            
            # Check if response is empty
            if not output:
                logger.error(f"❌ OpenAI returned empty response!")
                return self._get_empty_extraction_result()
            
            # Parse JSON response with robust handling (backup for JSON mode)
            try:
                # JSON mode should return clean JSON, but apply robust cleaning as backup
                json_str = self._robust_json_clean(output)
                logger.info(f"🧹 Cleaned JSON string length: {len(json_str)} characters")
                
                if not json_str.strip():
                    logger.error(f"❌ Cleaned JSON string is empty!")
                    logger.error(f"🔍 Original output: {output[:1000]}")
                    return self._get_empty_extraction_result()
                
                result = json.loads(json_str)
                logger.info(f"✅ JSON parsing successful with JSON mode")
                logger.info(f"📦 Products found: {len(result.get('productos', []))}")
                
                # Log key extracted fields for debugging
                logger.info(f"🏢 Company: {result.get('nombre_empresa', 'Not found')}")
                logger.info(f"👤 Requester: {result.get('nombre_solicitante', 'Not found')}")
                logger.info(f"📧 Email: {result.get('email_solicitante', 'Not found')}")
                logger.info(f"📍 Location: {result.get('lugar', 'Not found')}")
                logger.info(f"📅 Date: {result.get('fecha', 'Not found')}")
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed even with JSON mode and robust cleaning: {e}")
                logger.error(f"🔍 Raw output (first 1000 chars): {output[:1000]}")
                logger.error(f"🔍 Cleaned JSON (first 1000 chars): {json_str[:1000]}")
            return self._get_empty_extraction_result()
            
        except Exception as e:
            logger.error(f"❌ Complete AI extraction failed: {e}")
            # Return empty result for fallback
            return self._get_empty_extraction_result()
    
    def _robust_json_clean(self, raw_output: str) -> str:
        """🔧 Limpieza robusta de JSON que maneja markdown fences correctamente"""
        if not raw_output:
            return ""
        
        # Paso 1: Quitar markdown fences de cualquier tipo
        text = raw_output.strip()
        
        # Remover fences comunes: ```json, ```JSON, ```Json, etc.
        import re
        text = re.sub(r'^```(?:json|JSON|Json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
        
        # Paso 2: Buscar el JSON válido más largo
        # Encuentra el primer { y el último } balanceado
        first_brace = text.find('{')
        if first_brace == -1:
            return text  # No JSON encontrado, devolver como está
        
        # Contar llaves para encontrar el cierre balanceado
        brace_count = 0
        last_brace = -1
        
        for i in range(first_brace, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_brace = i
                    break
        
        if last_brace == -1:
            # No se encontró cierre balanceado, usar hasta el final
            json_str = text[first_brace:]
        else:
            json_str = text[first_brace:last_brace + 1]
        
        # Paso 3: Limpiar caracteres problemáticos comunes
        json_str = json_str.strip()
        
        # Remover texto antes del primer { si hay
        if json_str.startswith('JSON:') or json_str.startswith('json:'):
            json_str = json_str[5:].strip()
        
        logger.debug(f"🧹 JSON cleaning: {len(raw_output)} chars → {len(json_str)} chars")
        return json_str
    
    def _convert_function_calling_to_legacy_format(self, db_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 Convierte resultado de function calling a formato legacy esperado por el sistema
        
        Args:
            db_result: Resultado estructurado de function calling con formato BD v2.2
            
        Returns:
            Dict en formato legacy compatible con el resto del sistema
        """
        try:
            rfx_data = db_result.get('rfx_data', {})
            products_data = db_result.get('products_data', [])
            company_data = db_result.get('company_data', {})
            requester_data = db_result.get('requester_data', {})
            
            # Mapear a formato legacy
            legacy_result = {
                # Información básica
                "titulo": rfx_data.get('title', ''),
                "descripcion": rfx_data.get('description', ''),
                "requirements": rfx_data.get('requirements', ''),
                
                # Fechas
                "fecha": rfx_data.get('delivery_date', ''),
                "fecha_entrega": rfx_data.get('delivery_date', ''),
                "hora_entrega": rfx_data.get('delivery_time', ''),
                
                # Ubicación
                "lugar": rfx_data.get('event_location', ''),
                "ciudad": rfx_data.get('event_city', ''),
                "pais": rfx_data.get('event_country', 'Mexico'),
                
                # Moneda y presupuesto
                "currency": rfx_data.get('currency', 'USD'),
                "presupuesto_min": rfx_data.get('budget_range_min'),
                "presupuesto_max": rfx_data.get('budget_range_max'),
                
                # Información de empresa
                "nombre_empresa": company_data.get('company_name', ''),
                "email_empresa": company_data.get('company_email', ''),
                "telefono_empresa": company_data.get('phone', ''),
                "direccion_empresa": company_data.get('address', ''),
                
                # Información de solicitante
                "nombre_solicitante": requester_data.get('name', ''),
                "email_solicitante": requester_data.get('email', ''),
                "telefono_solicitante": requester_data.get('phone', ''),
                "cargo_solicitante": requester_data.get('position', ''),
                "departamento_solicitante": requester_data.get('department', ''),
                
                # Productos (conversión crítica)
            "productos": [],
                
                # Metadatos
                "extraction_method": "function_calling",
                "confidence_scores": rfx_data.get('metadata_json', {}).get('extraction_confidence', {}),
                "texto_original_relevante": rfx_data.get('metadata_json', {}).get('additional_metadata', {}).get('original_text_sample', '')
            }
            
            # Convertir productos a formato legacy
            for i, product in enumerate(products_data, 1):
                legacy_product = {
                    "nombre": product.get('product_name', ''),
                    "descripcion": product.get('description', ''),
                    "categoria": product.get('category', 'otro'),
                    "cantidad": product.get('quantity', 1),
                    "unidad": product.get('unit_of_measure', 'unidades'),
                    "especificaciones": product.get('specifications', ''),
                    "es_obligatorio": product.get('is_mandatory', True),
                    "orden_prioridad": product.get('priority_order', i),
                    "notas": product.get('notes', '')
                }
                legacy_result["productos"].append(legacy_product)
            
            logger.info(f"🔄 Function calling result converted to legacy format")
            logger.info(f"📦 Products converted: {len(legacy_result['productos'])}")
            logger.info(f"🏢 Company: {legacy_result['nombre_empresa']}")
            logger.info(f"👤 Requester: {legacy_result['nombre_solicitante']}")
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"❌ Error converting function calling result to legacy format: {e}")
            raise
    
    def _is_input_incomplete(self, extracted_data: Dict[str, Any], original_text: str, completeness_result: Dict[str, Any]) -> bool:
        """🚨 NUEVA FUNCIÓN: Determina si el input es incompleto y requiere más información del usuario"""
        
        logger.info(f"🔍 DEBUGGING COMPLETENESS CHECK:")
        logger.info(f"📊 Extracted data keys: {list(extracted_data.keys()) if extracted_data else 'None'}")
        
        if not extracted_data:
            logger.warning(f"❌ INCOMPLETE: No data extracted")
            return True
        
        productos = extracted_data.get('productos', [])
        logger.info(f"📦 Products to validate: {len(productos)}")
        
        # 1. NO PRODUCTS FOUND
        if not productos:
            logger.warning(f"❌ INCOMPLETE: No products found")
            return True
        
        # 2. GENERIC/VAGUE PRODUCTS - STRICTER VALIDATION
        generic_terms = ['material', 'producto', 'servicio', 'item', 'artículo', 'elemento', 'pop']
        vague_products = []
        
        for i, producto in enumerate(productos):
            nombre = producto.get('nombre', '').lower()
            descripcion = producto.get('descripcion', '').lower()
            cantidad = producto.get('cantidad', 0)
            
            logger.info(f"📦 Product {i+1}: '{nombre}' - Qty: {cantidad} - Desc: '{descripcion[:50]}...'")
            
            # Check if product name is too generic
            is_generic = any(term in nombre for term in generic_terms)
            
            # Check if missing critical information
            has_no_quantity = not cantidad or cantidad == 0
            has_no_description = not descripcion or len(descripcion.strip()) < 10
            
            # More strict: Consider vague if generic OR lacks details
            is_vague = is_generic or has_no_quantity or has_no_description
            
            if is_vague:
                vague_products.append(nombre)
                logger.warning(f"❌ VAGUE PRODUCT: '{nombre}' - Generic: {is_generic}, No quantity: {has_no_quantity}, No description: {has_no_description}")
        
        # If ANY product is vague, consider incomplete
        if vague_products:
            logger.warning(f"❌ INCOMPLETE: {len(vague_products)}/{len(productos)} products are vague: {vague_products}")
            return True
        
        # 3. MISSING ESSENTIAL INFORMATION
        essential_fields = ['nombre_solicitante', 'fecha_entrega']
        missing_fields = []
        
        for field in essential_fields:
            value = extracted_data.get(field, '')
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"❌ INCOMPLETE: Missing essential fields: {missing_fields}")
            return True
        
        # 4. COMPLETENESS RATIO TOO LOW - More strict
        completeness_ratio = completeness_result.get('completeness_ratio', 0)
        if completeness_ratio < 0.7:  # Increased from 30% to 70%
            logger.warning(f"❌ INCOMPLETE: Completeness ratio too low: {completeness_ratio:.2f}")
            return True
        
        # 5. TEXT TOO SHORT (likely incomplete description)
        if len(original_text.strip()) < 200:  # Increased from 100 to 200 characters
            logger.warning(f"❌ INCOMPLETE: Input text too short: {len(original_text)} characters")
            return True
        
        logger.info(f"✅ INPUT COMPLETE: All validation checks passed")
        return False

    def _validate_product_completeness(self, extracted_data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """🔍 NUEVA FUNCIÓN: Valida que se extrajeron todos los productos usando heurísticas"""
        try:
            productos_found = len(extracted_data.get('productos', []))
            
            # Simple heuristics to estimate expected products
            text_lower = original_text.lower()
            
            # Count potential food/service indicators
            food_indicators = ['tequeños', 'empanadas', 'canapés', 'brochetas', 'ceviche', 'pollo', 'res', 'lasaña', 'tortas', 'cheesecake', 'frutas']
            service_indicators = ['meseros', 'montaje', 'agua', 'jugos', 'café', 'té', 'refrescos']
            
            estimated_products = 0
            for indicator in food_indicators + service_indicators:
                if indicator in text_lower:
                    estimated_products += 1
            
            completeness_ratio = productos_found / max(estimated_products, 1) if estimated_products > 0 else 1.0
            
            validation_result = {
                'products_found': productos_found,
                'estimated_products': estimated_products,
                'completeness_ratio': min(completeness_ratio, 1.0),
                'validation_status': 'complete' if completeness_ratio >= 0.8 else 'partial'
            }
            
            logger.info(f"🔍 Completeness validation: Found {productos_found}, Estimated {estimated_products}, Ratio {completeness_ratio:.2f}")
            
            return validation_result
            
        except Exception as e:
            logger.warning(f"⚠️ Completeness validation failed: {e}")
            return {'validation_status': 'unknown', 'products_found': 0}
    
    def _process_with_ai_chunked_fallback(self, text: str) -> Dict[str, Any]:
        """🔄 FALLBACK: Sistema de chunking solo cuando es absolutamente necesario"""
        logger.warning(f"🔄 Using chunked fallback processing")
        
        try:
            # Very simple fallback - try to extract at least basic info
            logger.warning(f"⚠️ Implementing simple fallback extraction")
            return self._process_with_ai_legacy(text)
            
        except Exception as e:
            logger.error(f"❌ Even fallback processing failed: {e}")
            return self._get_empty_extraction_result()
    
    def _process_with_ai_legacy(self, text: str) -> Dict[str, Any]:
        """🔧 SIMPLIFIED FALLBACK: No chunking, basic extraction only"""
        logger.warning(f"⚠️ Using SIMPLIFIED LEGACY fallback - no chunking")
        
        try:
            # Very basic extraction with JSON mode compatible prompt
            system_prompt = """Eres un extractor de datos básico. Responde ÚNICAMENTE en formato JSON válido sin markdown fences."""
            
            user_prompt = f"""Extrae información básica de este texto de catering en formato JSON:

Estructura requerida:
{{
    "nombre_empresa": "nombre de la empresa si se encuentra",
    "nombre_solicitante": "nombre de la persona que solicita",
    "email": "email encontrado", 
    "productos": [
        {{"nombre": "producto", "cantidad": 1, "unidad": "unidades"}}
    ],
    "fecha": "fecha si se encuentra",
    "lugar": "ubicación si se encuentra",
    "currency": "USD"
}}

TEXTO: {text[:5000]}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use simpler model for fallback
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},  # 🆕 JSON MODE: Fallback legacy
                timeout=30
            )
            
            output = response.choices[0].message.content.strip()
            json_str = self._robust_json_clean(output)
            result = json.loads(json_str)
            
            # Map to expected format
            return {
                "email": result.get("email", ""),
                "nombre_solicitante": result.get("nombre_solicitante", ""),
                "nombre_empresa": result.get("nombre_empresa", ""), 
                "productos": result.get("productos", []),
                "fecha": result.get("fecha", ""),
                "lugar": result.get("lugar", ""),
                "currency": "USD",
                "texto_original_relevante": text[:500] if text else "",
                "processing_error": "Used simplified fallback"
            }
            
        except Exception as e:
            logger.error(f"❌ Legacy fallback failed: {e}")
            return {
                "email": "",
                "nombre_solicitante": "",
                "productos": [],
                "fecha": "",
                "lugar": "",
                "currency": "USD",
                "texto_original_relevante": text[:500] if text else "",
                "processing_error": f"Legacy fallback failed: {str(e)}"
            }
    
    def _safe_get_requirements(self, validated_data: Dict[str, Any]) -> tuple:
        """Safely get requirements with fallback"""
        try:
            requirements = validated_data.get("requirements")
            confidence = validated_data.get("requirements_confidence", 0.0)
            
            # Si no hay requirements, usar valores seguros
            if not requirements or requirements in ["null", "None", ""]:
                return None, 0.0
                
            return requirements, float(confidence) if confidence else 0.0
        except Exception as e:
            logger.warning(f"⚠️ Requirements extraction failed: {e}")
            return None, 0.0
    
    def _validate_basic_requirements(self, requirements: str, confidence: float) -> Dict[str, Any]:
        """Validación mínima para MVP de requirements"""
        if not requirements:
            return {
                'validated_requirements': None,
                'adjusted_confidence': 0.0,
                'validation_issues': [],
                'needs_review': False
            }
        
        issues = []
        adjusted_confidence = confidence
        cleaned_requirements = requirements.strip()
        
        # Validación 1: Longitud apropiada
        if len(cleaned_requirements) < 5:
            issues.append("requirements_too_short")
            adjusted_confidence *= 0.3
            logger.warning(f"⚠️ Requirements muy cortos: '{cleaned_requirements}'")
        
        if len(cleaned_requirements) > 1500:
            issues.append("requirements_too_long")
            adjusted_confidence *= 0.5
            cleaned_requirements = cleaned_requirements[:1500] + "..."
            logger.warning(f"⚠️ Requirements truncados por longitud")
        
        # Validación 2: Detectar si son demasiado genéricos
        generic_phrases = [
            "necesitamos catering", "queremos evento", "solicito servicio",
            "buen servicio", "servicio de calidad", "excelente atención"
        ]
        
        requirements_lower = cleaned_requirements.lower()
        has_generic = any(phrase in requirements_lower for phrase in generic_phrases)
        
        # Detectar si hay requirements específicos
        specific_indicators = [
            "preferimos", "debe", "sin", "con experiencia", "mínimo", "máximo",
            "años", "alergia", "vegetariano", "vegano", "halal", "kosher",
            "presupuesto", "horario", "personal", "certificación"
        ]
        
        has_specific = any(indicator in requirements_lower for indicator in specific_indicators)
        
        if has_generic and not has_specific:
            adjusted_confidence *= 0.4
            issues.append("seems_too_generic")
            logger.warning(f"⚠️ Requirements parecen demasiado genéricos: {confidence:.2f} → {adjusted_confidence:.2f}")
        
        # Validación 3: Detectar si contiene información de empresa/contacto (error de extracción)
        contact_indicators = ["@", "tel:", "email:", "teléfono", "contacto:"]
        if any(indicator in requirements_lower for indicator in contact_indicators):
            adjusted_confidence *= 0.3
            issues.append("contains_contact_info")
            logger.warning(f"⚠️ Requirements contienen información de contacto")
        
        # Validación 4: Score demasiado bajo necesita revisión
        needs_review = adjusted_confidence < 0.4
        
        if needs_review:
            logger.warning(f"⚠️ Requirements necesitan revisión - Confidence: {adjusted_confidence:.2f}")
        
        return {
            'validated_requirements': cleaned_requirements,
            'adjusted_confidence': round(adjusted_confidence, 3),
            'validation_issues': issues,
            'needs_review': needs_review,
            'original_confidence': confidence
        }
    
    def _log_requirements_extraction(self, rfx_id: str, validation_result: Dict) -> None:
        """Log detallado para analizar y mejorar requirements extraction"""
        log_data = {
            'rfx_id': rfx_id,
            'timestamp': datetime.now(),
            'requirements_extracted': validation_result.get('validated_requirements'),
            'confidence_score': validation_result.get('adjusted_confidence', 0.0),
            'original_confidence': validation_result.get('original_confidence', 0.0),
            'validation_issues': validation_result.get('validation_issues', []),
            'needs_review': validation_result.get('needs_review', False),
            'requirements_length': len(validation_result.get('validated_requirements', '') or '')
        }
        
        # Log básico para monitoring
        logger.info(f"📋 Requirements extracted for {rfx_id}: "
                   f"Length={log_data['requirements_length']}, "
                   f"Confidence={log_data['confidence_score']:.3f}, "
                   f"Issues={len(log_data['validation_issues'])}")
        
        # Log detallado en debug
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"📊 Requirements log data: {log_data}")
        
        # TODO: En el futuro, guardar en tabla de logs para análisis
        # self.requirements_logs.insert(log_data)
    
    def _validate_and_normalize_currency(self, currency: str) -> str | None:
        """🆕 Valida y normaliza códigos de moneda ISO 4217"""
        if not currency or currency.lower() in ["null", "none", "", "undefined"]:
            logger.info(f"📝 No currency provided - left as null for user completion")
            return None
        
        # Lista de monedas válidas más comunes en el contexto de negocio
        valid_currencies = {
            # Monedas principales
            "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
            # Monedas latinoamericanas
            "MXN", "BRL", "ARS", "COP", "PEN", "CLP", "UYU", "BOB", "VES",
            # Monedas asiáticas
            "CNY", "HKD", "SGD", "KRW", "INR", "THB", "MYR", "IDR",
            # Otras monedas relevantes
            "NOK", "SEK", "DKK", "PLN", "CZK", "HUF", "RUB", "ZAR"
        }
        
        # Normalizar entrada
        currency_clean = currency.strip().upper()
        
        # Validación directa
        if currency_clean in valid_currencies:
            logger.debug(f"💰 Currency validated: {currency_clean}")
            return currency_clean
        
        # Mapeo de aliases comunes
        currency_aliases = {
            # Símbolos a códigos
            "$": "USD",  # Predeterminado para $
            "€": "EUR",
            "£": "GBP", 
            "¥": "JPY",
            "₽": "RUB",
            "₹": "INR",
            
            # Variaciones textuales
            "DOLLAR": "USD",
            "DOLARES": "USD", 
            "DÓLARES": "USD",
            "DOLLARS": "USD",
            "EURO": "EUR",
            "EUROS": "EUR",
            "POUND": "GBP",
            "POUNDS": "GBP",
            "LIBRA": "GBP",
            "LIBRAS": "GBP",
            "YEN": "JPY",
            "PESO": "MXN",  # Predeterminado para peso sin contexto
            "PESOS": "MXN",
            "REAL": "BRL",
            "REALES": "BRL",
            "R$": "BRL",
            
            # Códigos con sufijos
            "USD$": "USD",
            "CAD$": "CAD",
            "AUD$": "AUD",
            "MXN$": "MXN",
            
            # Variaciones regionales
            "DÓLAR": "USD",
            "DÓLARES AMERICANOS": "USD",
            "DÓLARES ESTADOUNIDENSES": "USD",
            "PESOS MEXICANOS": "MXN",
            "PESOS COLOMBIANOS": "COP",
            "SOLES": "PEN",
            "BOLIVARES": "VES"
        }
        
        # Buscar en aliases
        if currency_clean in currency_aliases:
            mapped_currency = currency_aliases[currency_clean]
            logger.debug(f"💰 Currency mapped: {currency} → {mapped_currency}")
            return mapped_currency
        
        # Intentar extraer código de una cadena más larga
        for valid_code in valid_currencies:
            if valid_code in currency_clean:
                logger.debug(f"💰 Currency extracted from text: {currency} → {valid_code}")
                return valid_code
        
        # Si no se puede validar, preservar para revisión manual
        logger.warning(f"⚠️ Unrecognized currency '{currency}' - preserved for manual review")
        return currency
    
    def _validate_and_clean_data(self, raw_data: Dict[str, Any], rfx_id: str) -> Dict[str, Any]:
        """Validate and clean extracted data with fallbacks for invalid values"""
        # 🔍 DEBUG: Log validation process
        logger.info(f"🔍 Starting validation for RFX: {rfx_id}")
        logger.debug(f"📦 Raw data to validate: {raw_data}")
        
        # 🛡️ SAFETY CHECK: Handle None raw_data - Create minimal structure
        if raw_data is None:
            logger.warning(f"⚠️ raw_data is None for RFX: {rfx_id} - Creating minimal structure")
            raw_data = {
                "productos": [],
                "email": None,
                "fecha_entrega": None,
                "hora_entrega": None,
                "lugar": None,
                "nombre_solicitante": None,
                "currency": None
            }
        
        cleaned_data = raw_data.copy()
        validation_status = {
            "email_valid": False,
            "fecha_valid": False,
            "hora_valid": False,
            "has_original_data": True
        }
        
        # Validate and clean email - PRESERVE original even if invalid
        email = raw_data.get("email", "") or ""
        email = email.strip() if email else ""
        if email:
            if self.email_validator.validate(email):
                cleaned_data["email"] = email
                validation_status["email_valid"] = True
                logger.info(f"✅ Email validated successfully: {email}")
            else:
                # Keep original email but mark as invalid
                cleaned_data["email"] = email
                validation_status["email_valid"] = False
                logger.warning(f"⚠️ Email format invalid but preserved: {email}")
        else:
            # Leave as null - user will complete in interface
            cleaned_data["email"] = None
            validation_status["email_valid"] = False
            validation_status["has_original_data"] = False
            logger.info(f"📝 No email found - left as null for user completion")
        
                # Validate and clean date - NORMALIZE before validation 
        fecha = raw_data.get("fecha", "") or ""
        fecha = fecha.strip() if fecha else ""
        # Clean AI null responses
        if fecha in ["null", "None", "", "undefined"]:
            fecha = ""
        
        if fecha:
            # Normalize date format to YYYY-MM-DD for Pydantic
            fecha_normalized = self._normalize_date_format(fecha)
            if self.date_validator.validate(fecha_normalized):
                cleaned_data["fecha"] = fecha_normalized
                validation_status["fecha_valid"] = True
                logger.info(f"✅ Date validated and normalized: {fecha} → {fecha_normalized}")
            else:
                # Try with normalized format anyway for Pydantic
                cleaned_data["fecha"] = fecha_normalized
                validation_status["fecha_valid"] = False
                logger.warning(f"⚠️ Date format may be invalid but normalized: {fecha} → {fecha_normalized}")
        else:
            # Leave as null - user will complete in interface
            cleaned_data["fecha"] = None
            validation_status["fecha_valid"] = False
            logger.info(f"📝 No date found - left as null for user completion")
        
        # Validate and clean time - NORMALIZE format for Pydantic
        hora = raw_data.get("hora_entrega", "") or ""
        hora = hora.strip() if hora else ""
        # Clean AI null responses
        if hora in ["null", "None", "", "undefined"]:
            hora = ""
            
        if hora:
            # Normalize common time formats
            hora_normalized = self._normalize_time_format(hora)
            if self.time_validator.validate(hora_normalized):
                cleaned_data["hora_entrega"] = hora_normalized
                validation_status["hora_valid"] = True
                logger.info(f"✅ Time validated successfully: {hora} → {hora_normalized}")
            else:
                # Try with normalized format anyway for Pydantic
                cleaned_data["hora_entrega"] = hora_normalized
                validation_status["hora_valid"] = False
                logger.warning(f"⚠️ Time format may be invalid but preserved: {hora} → {hora_normalized}")
        else:
            # Leave as null - user will complete in interface
            cleaned_data["hora_entrega"] = None
            validation_status["hora_valid"] = False
            logger.info(f"📝 No time found - left as null for user completion")
        
        # Clean and validate client name - MORE PERMISSIVE
        nombre_solicitante = raw_data.get("nombre_solicitante", "") or ""
        nombre_solicitante = nombre_solicitante.strip() if nombre_solicitante else ""
        if nombre_solicitante and nombre_solicitante.lower() not in ["null", "none", ""]:
            cleaned_data["nombre_solicitante"] = nombre_solicitante.title()
            logger.info(f"✅ Solicitante name processed: {nombre_solicitante}")
        else:
            # Leave as null - user will complete in interface
            cleaned_data["nombre_solicitante"] = None
            validation_status["has_original_data"] = False
            logger.info(f"📝 No client name found - left as null for user completion")
        
        # Clean place - MORE PERMISSIVE
        lugar = raw_data.get("lugar", "") or ""
        lugar = lugar.strip() if lugar else ""
        if lugar and lugar.lower() not in ["null", "none", ""]:
            cleaned_data["lugar"] = lugar
            logger.info(f"✅ Location preserved: {lugar}")
        else:
            # Leave as null - user will complete in interface
            cleaned_data["lugar"] = None
            logger.info(f"📝 No location found - left as null for user completion")
        
        # 🆕 Currency validation and normalization
        currency = raw_data.get("currency", "") or ""
        currency = currency.strip().upper() if currency else ""
        cleaned_data["currency"] = self._validate_and_normalize_currency(currency)
        logger.info(f"💰 Currency processed: '{raw_data.get('currency', '')}' → '{cleaned_data['currency']}'")
        
        # Validate products - VERY PERMISSIVE (Allow empty products for informational RFXs)
        productos = raw_data.get("productos", [])
        logger.info(f"🔍 Validating {len(productos)} products from AI extraction")
        logger.debug(f"📦 Raw products data: {productos}")
        
        if not productos:
            logger.warning(f"⚠️ No products array found in AI response - treating as informational RFX")
            logger.debug(f"📦 Full raw_data keys: {list(raw_data.keys())}")
            # Don't raise error - some RFXs might be informational without products
            cleaned_data["productos"] = []
            validation_status["has_products"] = False
            validation_status["product_count"] = 0
            # 🔧 FIX: Initialize cleaned_productos to prevent UnboundLocalError
            cleaned_productos = []
            logger.info(f"📄 Processing as informational RFX without products")
        else:
            # Clean and validate each product - VERY PERMISSIVE
            cleaned_productos = []
            for i, producto in enumerate(productos):
                logger.debug(f"🔍 Processing product {i+1}: {producto}")
                
                # Handle different formats of product data
                if isinstance(producto, dict):
                    nombre = None
                    cantidad = 1
                    unidad = "unidades"
                    
                    # Try to extract name from various possible keys
                    for name_key in ["nombre", "name", "product", "producto", "item"]:
                        if producto.get(name_key):
                            nombre = str(producto[name_key]).strip()
                            break
                    
                    # Try to extract quantity
                    for qty_key in ["cantidad", "quantity", "qty", "count", "numero"]:
                        if producto.get(qty_key):
                            try:
                                cantidad = max(1, int(float(producto[qty_key])))
                                break
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ Invalid quantity for product {i+1}: {producto.get(qty_key)}")
                                continue
                    
                    # Try to extract unit
                    for unit_key in ["unidad", "unit", "units", "medida"]:
                        if producto.get(unit_key):
                            unidad = str(producto[unit_key]).strip().lower()
                            break
                    
                    # Accept product if it has any meaningful name
                    if nombre and len(nombre.strip()) > 0 and nombre.lower() not in ["null", "none", "", "undefined"]:
                        cleaned_producto = {
                            "nombre": nombre.title(),
                            "cantidad": cantidad,
                            "unidad": unidad or "unidades"
                        }
                        cleaned_productos.append(cleaned_producto)
                        logger.info(f"✅ Product {i+1} accepted: {cleaned_producto}")
                    else:
                        logger.warning(f"⚠️ Product {i+1} rejected - invalid name: {nombre}")
                        
                elif isinstance(producto, str):
                    # Handle product as simple string
                    nombre = producto.strip()
                    if nombre and len(nombre) > 0 and nombre.lower() not in ["null", "none", "", "undefined"]:
                        cleaned_producto = {
                            "nombre": nombre.title(),
                            "cantidad": 1,
                            "unidad": "unidades"
                        }
                        cleaned_productos.append(cleaned_producto)
                        logger.info(f"✅ Product {i+1} accepted as string: {cleaned_producto}")
                    else:
                        logger.warning(f"⚠️ Product {i+1} rejected - invalid string: {nombre}")
                else:
                    logger.warning(f"⚠️ Product {i+1} skipped - unrecognized format: {type(producto)}")
            
            logger.info(f"📊 Product validation completed: {len(cleaned_productos)} valid products from {len(productos)} raw products")
            
            if not cleaned_productos:
                logger.error(f"❌ No valid products could be processed from AI extraction")
                logger.error(f"🔍 Original products data: {productos}")
                # Create a fallback product to avoid complete failure
                logger.warning(f"⚠️ Creating fallback product to prevent complete failure")
                cleaned_productos = [{
                    "nombre": "Producto No Especificado",
                    "cantidad": 1,
                    "unidad": "unidades"
                }]
                logger.info(f"✅ Fallback product created: {cleaned_productos[0]}")
            
            cleaned_data["productos"] = cleaned_productos
        
        # ✨ PRESERVE: Datos de empresa sin validación (son opcionales)
        empresa_fields = ["nombre_empresa", "email_empresa", "telefono_empresa", "telefono_solicitante", "cargo_solicitante"]
        for field in empresa_fields:
            if field in raw_data and raw_data[field]:
                cleaned_data[field] = str(raw_data[field]).strip()
                logger.info(f"✅ Empresa field preserved: {field} = {cleaned_data[field]}")
            else:
                cleaned_data[field] = ""
                logger.debug(f"📝 Empresa field empty: {field}")
        
        # 🆕 MVP: Validate and clean requirements
        requirements = raw_data.get("requirements", "")
        requirements_confidence = raw_data.get("requirements_confidence", 0.0)
        
        if requirements and requirements.strip():
            # Aplicar validación básica
            validation_result = self._validate_basic_requirements(
                requirements.strip(), 
                float(requirements_confidence) if requirements_confidence else 0.0
            )
            
            # Guardar resultados validados
            cleaned_data["requirements"] = validation_result['validated_requirements']
            cleaned_data["requirements_confidence"] = validation_result['adjusted_confidence']
            
            # Actualizar validation status
            validation_status["requirements_valid"] = not validation_result['needs_review']
            validation_status["requirements_issues"] = validation_result['validation_issues']
            
            # Log extraction para mejora continua
            self._log_requirements_extraction(rfx_id, validation_result)
            
            logger.info(f"✅ Requirements processed: confidence={validation_result['adjusted_confidence']:.3f}, "
                       f"issues={len(validation_result['validation_issues'])}")
        else:
            # No hay requirements extraídos
            cleaned_data["requirements"] = None
            cleaned_data["requirements_confidence"] = 0.0
            validation_status["requirements_valid"] = True  # Válido que no haya requirements
            validation_status["requirements_issues"] = []
            logger.debug(f"📝 No requirements extracted for RFX: {rfx_id}")
        
        # Add validation metadata
        cleaned_data["validation_metadata"] = validation_status
        
        # 🔍 DEBUG: Log final validation result
        logger.info(f"✅ Validation completed for {len(cleaned_productos)} products")
        logger.info(f"📊 Validation status: {validation_status}")
        logger.debug(f"📦 Final cleaned data: {cleaned_data}")
        
        return cleaned_data
    
    def _create_rfx_processed(self, validated_data: Dict[str, Any], rfx_input: RFXInput, evaluation_metadata: Optional[Dict[str, Any]] = None) -> RFXProcessed:
        """Create RFXProcessed object from validated data and evaluation results"""
        try:
            # 🔍 DEBUG: Log object creation
            logger.info(f"🔨 Creating RFXProcessed object for: {rfx_input.id}")
            
            # Convert productos to ProductoRFX objects (map Spanish to English fields)
            productos = [
                ProductoRFX(
                    product_name=p["nombre"],
                    quantity=p["cantidad"],
                    unit=p["unidad"]
                )
                for p in validated_data["productos"]
            ]
            
            # Prepare enhanced metadata including empresa data
            metadata = {
                "original_rfx_id": rfx_input.id,  # Preserve original string ID for frontend
                "texto_original_length": len(rfx_input.extracted_content or ""),
                "productos_count": len(productos),
                "processing_version": "2.1",  # Upgraded version with intelligent evaluation
                "validation_status": validated_data.get("validation_metadata", {}),
                "texto_original_relevante": validated_data.get("texto_original_relevante", ""),
                "ai_extraction_quality": "high" if validated_data.get("validation_metadata", {}).get("has_original_data", False) else "fallback",
                # ✨ AÑADIR: Datos de empresa en metadatos para acceso del frontend
                "nombre_empresa": validated_data.get("nombre_empresa", ""),
                "email_empresa": validated_data.get("email_empresa", ""),
                "telefono_empresa": validated_data.get("telefono_empresa", ""),
                "telefono_solicitante": validated_data.get("telefono_solicitante", ""),
                "cargo_solicitante": validated_data.get("cargo_solicitante", ""),
                # ✨ MONEDA: Currency extraída por AI
                "validated_currency": validated_data.get("currency", "USD")
            }
            
            # Integrate intelligent evaluation metadata if available
            if evaluation_metadata:
                metadata["intelligent_evaluation"] = evaluation_metadata
                
                # Log evaluation integration
                if evaluation_metadata.get('evaluation_enabled'):
                    if 'evaluation_error' in evaluation_metadata:
                        logger.warning(f"⚠️ Evaluation error included in metadata for {rfx_input.id}")
                    else:
                        score = evaluation_metadata.get('execution_summary', {}).get('consolidated_score')
                        quality = evaluation_metadata.get('execution_summary', {}).get('overall_quality')
                        domain = evaluation_metadata.get('domain_detection', {}).get('primary_domain')
                        logger.info(f"📊 Evaluation metadata integrated - Score: {score}, Quality: {quality}, Domain: {domain}")
                else:
                    logger.debug(f"🔧 Evaluation disabled - metadata reflects feature flag status")
            else:
                logger.debug(f"ℹ️ No evaluation metadata provided for {rfx_input.id}")
            
            # 🔍 DEBUG: Log metadata
            logger.debug(f"📊 Metadata prepared: {metadata}")
            
            # Generate UUID for database, but keep original ID in metadata
            from uuid import uuid4
            rfx_uuid = uuid4()
            
            rfx_processed = RFXProcessed(
                id=rfx_uuid,
                rfx_type=rfx_input.rfx_type,
                title=f"RFX Request - {validated_data.get('nombre_solicitante', 'Unknown')} - {rfx_input.rfx_type.value if hasattr(rfx_input.rfx_type, 'value') else str(rfx_input.rfx_type)}",
                location=validated_data["lugar"],
                delivery_date=validated_data["fecha"],
                delivery_time=validated_data["hora_entrega"],
                status=RFXStatus.IN_PROGRESS,
                original_pdf_text=rfx_input.extracted_content,
                requested_products=[p.dict() for p in productos] if productos else [],
                metadata_json=metadata,
                received_at=datetime.now(),
                
                # Legacy/extracted fields for compatibility
                email=validated_data["email"],
                requester_name=validated_data["nombre_solicitante"],
                company_name=validated_data.get("nombre_empresa", ""),
                products=productos,  # productos is already a list of RFXProductRequest objects
                
                # 🆕 MVP: Requirements específicos del cliente (SAFE)
                requirements=self._safe_get_requirements(validated_data)[0],
                requirements_confidence=self._safe_get_requirements(validated_data)[1]
            )
            
            # 🔍 DEBUG: Log successful creation
            logger.info(f"✅ RFXProcessed object created successfully")
            empresa_info = metadata or {}
            empresa_nombre = empresa_info.get("nombre_empresa", "No especificada")
            original_id = empresa_info.get("original_rfx_id", str(rfx_processed.id))
            logger.info(f"📦 RFX Object: Original ID={original_id}, UUID={rfx_processed.id}, Solicitante={rfx_processed.requester_name}, Empresa={empresa_nombre}, Productos={len(rfx_processed.products)}")
            
            # Log empresa details if available
            if empresa_info.get("nombre_empresa"):
                logger.info(f"🏢 Empresa: {empresa_info.get('nombre_empresa')} | Email: {empresa_info.get('email_empresa', 'N/A')} | Tel: {empresa_info.get('telefono_empresa', 'N/A')}")
            
            # Log solicitante details if available  
            if empresa_info.get("telefono_solicitante") or empresa_info.get("cargo_solicitante"):
                logger.info(f"👤 Solicitante: {rfx_processed.requester_name} | Tel: {empresa_info.get('telefono_solicitante', 'N/A')} | Cargo: {empresa_info.get('cargo_solicitante', 'N/A')}")
            
            # 🆕 MVP: Log requirements info if available
            if rfx_processed.requirements:
                req_preview = rfx_processed.requirements[:100] + "..." if len(rfx_processed.requirements) > 100 else rfx_processed.requirements
                logger.info(f"📋 Requirements: '{req_preview}' | Confidence: {rfx_processed.requirements_confidence:.3f}")
            else:
                logger.debug(f"📝 No requirements extracted for RFX")
                
            return rfx_processed
            
        except Exception as e:
            logger.error(f"❌ Failed to create RFXProcessed object: {e}")
            raise
    
    def _save_rfx_to_database(self, rfx_processed: RFXProcessed, user_id: str = None) -> None:
        """Save processed RFX to database V2.0 with normalized structure"""
        try:
            if user_id:
                logger.info(f"💾 Saving RFX with user_id: {user_id}")
            else:
                logger.warning(f"⚠️ Saving RFX without user_id - will be NULL in database")
            # Extract company and requester information from metadata
            metadata = rfx_processed.metadata_json or {}
            
            # 1. Create or find company
            # Clean email to meet database constraints (no spaces allowed)
            email_empresa = metadata.get("email_empresa", "")
            if email_empresa:
                email_empresa = email_empresa.replace(" ", "").strip()
                if not email_empresa or "@" not in email_empresa:
                    email_empresa = None
            else:
                email_empresa = None
                
            company_data = {
                "name": metadata.get("nombre_empresa", "Unknown Company"),
                "email": email_empresa,
                "phone": metadata.get("telefono_empresa")
            }
            company_record = self.db_client.insert_company(company_data)
            
            # 2. Create or find requester
            # Clean requester email to meet database constraints
            requester_email = rfx_processed.email or ""
            if requester_email:
                requester_email = requester_email.replace(" ", "").strip()
                if not requester_email or "@" not in requester_email:
                    requester_email = None
            else:
                requester_email = None
                
            requester_data = {
                "company_id": company_record.get("id"),
                "name": rfx_processed.requester_name or "Unknown Requester",
                "email": requester_email,
                "phone": metadata.get("telefono_solicitante"),
                "position": metadata.get("cargo_solicitante")
            }
            requester_record = self.db_client.insert_requester(requester_data)
            
            # 3. Prepare RFX data for database (V2.0 schema)
            rfx_data = {
                "id": str(rfx_processed.id),
                "company_id": company_record.get("id"),
                "requester_id": requester_record.get("id"),
                "rfx_type": rfx_processed.rfx_type.value if hasattr(rfx_processed.rfx_type, 'value') else str(rfx_processed.rfx_type),
                "title": f"RFX Request - {rfx_processed.rfx_type}",
                "location": rfx_processed.location,
                "delivery_date": rfx_processed.delivery_date.isoformat() if rfx_processed.delivery_date else None,
                "delivery_time": rfx_processed.delivery_time.isoformat() if rfx_processed.delivery_time else None,
                "status": rfx_processed.status.value if hasattr(rfx_processed.status, 'value') else str(rfx_processed.status),
                "original_pdf_text": rfx_processed.original_pdf_text,
                "requested_products": rfx_processed.requested_products or [],
                "received_at": rfx_processed.received_at.isoformat() if rfx_processed.received_at else None,
                "metadata_json": rfx_processed.metadata_json,
                "currency": rfx_processed.metadata_json.get('validated_currency', 'USD') if rfx_processed.metadata_json else 'USD',
                
                # 🆕 MVP: Requirements específicos del cliente
                "requirements": rfx_processed.requirements,
                "requirements_confidence": rfx_processed.requirements_confidence
            }
            
            # 🆕 CRITICAL: Add user_id if provided
            if user_id:
                rfx_data["user_id"] = user_id
                logger.info(f"✅ Added user_id to rfx_data: {user_id}")
            else:
                logger.warning(f"⚠️ No user_id provided - rfx_data will not have user_id field")
            
            # 4. Insert RFX data
            rfx_record = self.db_client.insert_rfx(rfx_data)
            
            # 5. Insert structured products if available
            if rfx_processed.products:
                structured_products = []
                for product in rfx_processed.products:
                    product_data = {
                        "product_name": product.product_name if hasattr(product, 'product_name') else product.nombre,
                        "quantity": product.quantity if hasattr(product, 'quantity') else product.cantidad,
                        "unit": product.unit if hasattr(product, 'unit') else product.unidad,
                        "estimated_unit_price": getattr(product, 'estimated_unit_price', None),
                        "notes": f"Extracted from RFX processing"
                    }
                    structured_products.append(product_data)
                
                self.db_client.insert_rfx_products(rfx_record["id"], structured_products)
                logger.info(f"✅ {len(structured_products)} structured products saved")
            
            # 6. Create history event
            history_event = {
                "rfx_id": str(rfx_processed.id),
                "event_type": "rfx_processed",
                "description": f"RFX processed successfully with {len(rfx_processed.products or [])} products",
                "new_values": {
                    "company_name": company_data["name"],
                    "requester_name": requester_data["name"],
                    "processing_version": metadata.get("processing_version", "2.0"),
                    "original_rfx_id": metadata.get("original_rfx_id"),
                    "product_count": len(rfx_processed.products or [])
                },
                "performed_by": "system_ai"
            }
            self.db_client.insert_rfx_history(history_event)
            
            logger.info(f"✅ RFX saved to database V2.0: {rfx_processed.id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save RFX to database: {e}")
            raise
    
    # REMOVED: _generate_proposal_automatically
    # La generación de propuestas ahora se maneja por separado cuando el usuario lo solicite
    # mediante el endpoint /api/proposals/generate después de revisar datos y establecer costos
    
    def _map_rfx_data_for_proposal(self, rfx_data_raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔧 Mapea estructura BD V2.0 (inglés, normalizada) → ProposalGenerationService (español, plana)
        
        Args:
            rfx_data_raw: Datos del RFX desde BD V2.0 con companies, requesters, etc.
            
        Returns:
            Dict con estructura esperada por ProposalGenerationService
        """
        try:
            # Extraer datos de BD V2.0
            company_data = rfx_data_raw.get("companies", {}) or {}
            requester_data = rfx_data_raw.get("requesters", {}) or {}
            requested_products = rfx_data_raw.get("requested_products", [])
            metadata = rfx_data_raw.get("metadata_json", {}) or {}
            
            # Mapear productos con fallback a metadata si es necesario
            productos_mapped = []
            if requested_products:
                # Usar productos estructurados de BD
                for producto in requested_products:
                    productos_mapped.append({
                        "nombre": producto.get("product_name", producto.get("nombre", "Producto")),
                        "cantidad": producto.get("quantity", producto.get("cantidad", 1)),
                        "unidad": producto.get("unit", producto.get("unidad", "unidades"))
                    })
            else:
                # Fallback a metadata si no hay productos estructurados
                metadata_productos = metadata.get("productos", [])
                for producto in metadata_productos:
                    if isinstance(producto, dict):
                        productos_mapped.append({
                            "nombre": producto.get("nombre", "Producto"),
                            "cantidad": producto.get("cantidad", 1),
                            "unidad": producto.get("unidad", "unidades")
                        })
            
            # Si aún no hay productos, crear uno por defecto
            if not productos_mapped:
                productos_mapped = [{
                    "nombre": "Servicio de Catering",
                    "cantidad": 1,
                    "unidad": "servicio"
                }]
            
            # Estructura mapeada esperada por ProposalGenerationService
            mapped_data = {
                # ✅ Mapear información del cliente (combinando empresa + solicitante)
                "clientes": {
                    "nombre": requester_data.get("name", metadata.get("nombre_solicitante", "Cliente")),
                    "email": requester_data.get("email", metadata.get("email", "")),
                    "empresa": company_data.get("name", metadata.get("nombre_empresa", "")),
                    "telefono": requester_data.get("phone", metadata.get("telefono_solicitante", "")),
                    "cargo": requester_data.get("position", metadata.get("cargo_solicitante", "")),
                    # Información adicional de empresa
                    "email_empresa": company_data.get("email", metadata.get("email_empresa", "")),
                    "telefono_empresa": company_data.get("phone", metadata.get("telefono_empresa", ""))
                },
                
                # ✅ Mapear productos
                "productos": productos_mapped,
                
                # ✅ Mapear información del evento
                "lugar": rfx_data_raw.get("location", metadata.get("lugar", "Por definir")),
                "fecha_entrega": rfx_data_raw.get("delivery_date", metadata.get("fecha", "")),
                "hora_entrega": rfx_data_raw.get("delivery_time", metadata.get("hora_entrega", "")),
                "tipo": rfx_data_raw.get("rfx_type", metadata.get("tipo_solicitud", "catering")),
                
                # ✅ Información adicional
                "id": str(rfx_data_raw.get("id", "")),
                "title": rfx_data_raw.get("title", ""),
                "received_at": rfx_data_raw.get("received_at", ""),
                "texto_original_relevante": metadata.get("texto_original_relevante", "")
            }
            
            logger.debug(f"🔧 Datos mapeados para propuesta: Cliente={mapped_data['clientes']['nombre']}, "
                        f"Empresa={mapped_data['clientes']['empresa']}, Productos={len(mapped_data['productos'])}")
            
            return mapped_data
            
        except Exception as e:
            logger.error(f"❌ Error mapeando datos para propuesta: {e}")
            # Fallback con estructura mínima
            return {
                "clientes": {"nombre": "Cliente", "email": ""},
                "productos": [{"nombre": "Servicio de Catering", "cantidad": 1, "unidad": "servicio"}],
                "lugar": "Por definir",
                "fecha_entrega": "",
                "hora_entrega": "",
                "tipo": "catering"
            }
    
    # REMOVED: _log_proposal_generation_event and _log_proposal_generation_error
    # Estas funciones ya no se necesitan porque la generación de propuestas es manual

    def _call_openai_with_retry(self, max_retries: int = 3, **kwargs) -> Any:
        """Call OpenAI API with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 OpenAI API call attempt {attempt + 1}/{max_retries}")
                response = self.openai_client.chat.completions.create(**kwargs)
                logger.info(f"✅ OpenAI API call successful on attempt {attempt + 1}")
                return response
            except Exception as e:
                wait_time = (2 ** attempt) + 1  # Exponential backoff: 2s, 3s, 5s
                logger.warning(f"⚠️ OpenAI API call failed on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ OpenAI API call failed after {max_retries} attempts")
                    raise

    def _evaluate_rfx_intelligently(self, validated_data: Dict[str, Any], rfx_id: str) -> Dict[str, Any]:
        """
        Ejecuta evaluación inteligente del RFX usando el orquestador.
        
        Args:
            validated_data: Datos del RFX ya validados y limpios
            rfx_id: ID único del RFX para logging
            
        Returns:
            Dict con metadata de evaluación para incluir en RFXProcessed
        """
        # Verificar si la evaluación está habilitada
        if not FeatureFlags.evals_enabled():
            logger.debug(f"🔧 Evaluación inteligente deshabilitada por feature flag para RFX: {rfx_id}")
            return {
                'evaluation_enabled': False,
                'reason': 'Feature flag disabled'
            }
        
        try:
            # Import lazy para evitar circular imports y mejorar startup time
            from backend.services.evaluation_orchestrator import evaluate_rfx_intelligently
            
            logger.info(f"🔍 Iniciando evaluación inteligente para RFX: {rfx_id}")
            start_time = datetime.now()
            
            # Ejecutar evaluación completa
            eval_result = evaluate_rfx_intelligently(validated_data)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log resultados principales
            domain = eval_result['domain_detection']['primary_domain']
            confidence = eval_result['domain_detection']['confidence']
            score = eval_result['consolidated_score']
            quality = eval_result['execution_summary']['overall_quality']
            
            logger.info(f"✅ Evaluación completada para {rfx_id} - Dominio: {domain} ({confidence:.3f}), Score: {score:.3f} ({quality}), Tiempo: {execution_time:.3f}s")
            
            # Extraer recomendaciones críticas y de alta prioridad
            critical_recommendations = [
                {
                    'title': rec['title'],
                    'description': rec['description'],
                    'priority': rec['priority'],
                    'category': rec['category'],
                    'type': rec['type']
                }
                for rec in eval_result['recommendations'] 
                if rec.get('priority') in ['critical', 'high']
            ]
            
            # Log recomendaciones críticas
            if critical_recommendations:
                logger.warning(f"⚠️ RFX {rfx_id} tiene {len(critical_recommendations)} recomendaciones críticas/alta prioridad")
                for rec in critical_recommendations[:2]:  # Log solo las primeras 2
                    logger.warning(f"   - [{rec['priority'].upper()}] {rec['title']}")
            
            # Estructura optimizada de metadata (solo datos esenciales)
            evaluation_metadata = {
                'evaluation_enabled': True,
                'execution_summary': {
                    'consolidated_score': score,
                    'overall_quality': quality,
                    'execution_time_seconds': round(execution_time, 3),
                    'evaluators_executed': eval_result['execution_summary']['evaluators_executed'],
                    'timestamp': datetime.now().isoformat()
                },
                'domain_detection': {
                    'primary_domain': domain,
                    'confidence': confidence,
                    'secondary_domains': eval_result['domain_detection'].get('secondary_domains', [])
                },
                'evaluation_scores': {
                    'generic_score': eval_result['generic_evaluation']['score'],
                    'domain_specific_score': eval_result['domain_specific_evaluation']['score'],
                    'generic_evaluators_count': eval_result['generic_evaluation']['count'],
                    'domain_specific_evaluators_count': eval_result['domain_specific_evaluation']['count']
                },
                'critical_recommendations': critical_recommendations,
                'recommendations_summary': {
                    'total_count': len(eval_result['recommendations']),
                    'critical_count': len([r for r in eval_result['recommendations'] if r.get('priority') == 'critical']),
                    'high_priority_count': len([r for r in eval_result['recommendations'] if r.get('priority') == 'high']),
                    'by_category': {
                        cat: len([r for r in eval_result['recommendations'] if r.get('category') == cat])
                        for cat in set(r.get('category', 'other') for r in eval_result['recommendations'])
                    }
                }
            }
            
            # Log opcional de debugging si está habilitado
            if FeatureFlags.eval_debug_enabled():
                logger.debug(f"🔍 Evaluación detallada para {rfx_id}: {evaluation_metadata}")
            
            return evaluation_metadata
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando evaluación inteligente para {rfx_id}: {str(e)}")
            
            # NO fallar el procesamiento principal - solo log el error
            # Retornar metadata de error para debugging
            return {
                'evaluation_enabled': True,
                'evaluation_error': {
                    'error_message': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat(),
                    'rfx_id': rfx_id
                },
                'execution_summary': {
                    'consolidated_score': None,
                    'overall_quality': 'evaluation_failed',
                    'execution_time_seconds': 0.0,
                    'evaluators_executed': 0
                }
            }

    def _get_empty_extraction_result(self) -> Dict[str, Any]:
        """Return empty result structure for failed extractions"""
        return {
            "email": "",
            "nombre_solicitante": "",
            "productos": [],
            "hora_entrega": "",
            "fecha": "",
            "lugar": "",
            "currency": "USD",
            "texto_original_relevante": "",
            # 🆕 MVP: Requirements fields for compatibility
            "requirements": None,
            "requirements_confidence": 0.0,
            "confidence_score": 0.0  # Legacy compatibility
        }
    
    # ============================================================================
    # 🔍 MÉTODOS DE DEBUGGING Y ESTADÍSTICAS
    # ============================================================================
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """🆕 Retorna estadísticas de procesamiento para monitoring y debugging"""
        base_stats = self.processing_stats.copy()
        
        # Añadir estadísticas del extractor modular
        if hasattr(self, 'modular_extractor'):
            extraction_summary = self.modular_extractor.get_extraction_summary()
            base_stats.update({
                'modular_extractor_stats': extraction_summary.dict(),
                'modular_extraction_quality': extraction_summary.extraction_quality,
                'modular_chunks_processed': extraction_summary.chunk_count,
                'modular_ai_calls': extraction_summary.ai_calls_made,
                'modular_retries': extraction_summary.retries_attempted
            })
        
        # Calcular ratios y métricas derivadas
        if base_stats['total_documents_processed'] > 0:
            base_stats['fallback_usage_ratio'] = base_stats['fallback_usage_count'] / base_stats['total_documents_processed']
            base_stats['average_chunks_per_document'] = base_stats['chunks_processed'] / base_stats['total_documents_processed']
        else:
            base_stats['fallback_usage_ratio'] = 0.0
            base_stats['average_chunks_per_document'] = 0.0
        
        return base_stats
    
    def reset_processing_statistics(self) -> None:
        """🆕 Resetea estadísticas de procesamiento"""
        self.processing_stats = {
            'total_documents_processed': 0,
            'chunks_processed': 0,
            'average_confidence': 0.0,
            'fallback_usage_count': 0
        }
        
        if hasattr(self, 'modular_extractor'):
            # Resetear estadísticas del extractor modular
            self.modular_extractor.extraction_stats = {
                'chunks_processed': 0,
                'ai_calls_made': 0,
                'retries_attempted': 0,
                'total_processing_time': 0.0
            }
        
        logger.info("📊 Processing statistics reset")
    
    def get_debug_mode_status(self) -> Dict[str, Any]:
        """🆕 Retorna estado del modo debug y configuración actual"""
        return {
            'debug_mode_enabled': getattr(self.modular_extractor, 'debug_mode', False),
            'extraction_strategy': getattr(self.modular_extractor, 'strategy', ExtractionStrategy.BALANCED).value,
            'feature_flags': {
                'evals_enabled': FeatureFlags.evals_enabled(),
                'eval_debug_enabled': FeatureFlags.eval_debug_enabled(),
                'meta_prompting_enabled': FeatureFlags.meta_prompting_enabled() if hasattr(FeatureFlags, 'meta_prompting_enabled') else False,
                'vertical_agent_enabled': FeatureFlags.vertical_agent_enabled() if hasattr(FeatureFlags, 'vertical_agent_enabled') else False
            },
            'processing_version': '2.1_modular',
            'available_extractors': ['ProductExtractor', 'ClientExtractor', 'EventExtractor'],
            'template_manager_initialized': hasattr(self.modular_extractor, 'template_manager')
        }

    # NEW: Multi-file processing
    def process_rfx_case(self, rfx_input: RFXInput, blobs: List[Dict[str, Any]], user_id: str = None) -> RFXProcessed:
        """Multi-file processing pipeline with OCR and spreadsheet support"""
        logger.info(f"📦 process_rfx_case start: {rfx_input.id} with {len(blobs)} file(s)")
        if user_id:
            logger.info(f"✅ user_id provided for RFX: {user_id}")
        else:
            logger.warning(f"⚠️ No user_id provided for RFX: {rfx_input.id}")
        
        # 🔍 DEBUG: Detailed file logging
        for i, b in enumerate(blobs):
            fname = b.get("filename", f"file_{i}")
            content_size = len(b.get("content", b.get("bytes", b"")))
            logger.info(f"🔍 INPUT FILE {i+1}: '{fname}' ({content_size} bytes)")
        
        # 1) Expand ZIPs
        expanded: List[Dict[str, Any]] = []
        for i, b in enumerate(blobs):
            fname = (b.get("filename") or f"file_{i}").lower()
            content = b.get("content") or b.get("bytes")
            if not content: 
                logger.warning(f"⚠️ EMPTY FILE {i+1}: '{fname}' - skipping")
                continue
            if USE_ZIP and (fname.endswith(".zip") or (content[:2] == b"PK" and not fname.endswith(".docx") and not fname.endswith(".xlsx"))):
                try:
                    with zipfile.ZipFile(io.BytesIO(content)) as zf:
                        for name in zf.namelist():
                            if name.endswith("/"): continue
                            expanded.append({"filename": name, "content": zf.read(name)})
                    logger.info(f"🗜️ ZIP expanded: {fname} → {len(expanded)} internal files")
                except Exception as e:
                    logger.warning(f"⚠️ ZIP expand failed {fname}: {e}")
            else:
                expanded.append({"filename": fname, "content": content})

        text_parts: List[str] = []
        canonical_items: List[Dict[str, Any]] = []
        
        # 2) Per-file routing with DETAILED DEBUG LOGGING
        for file_index, b in enumerate(expanded):
            fname = b["filename"].lower()
            content: bytes = b["content"]
            kind = self._detect_content_type(content, fname)
            logger.info(f"🔎 PROCESSING FILE {file_index+1}: '{fname}' kind={kind} size={len(content)} bytes")
            
            try:
                if kind in ("pdf", "docx", "text"):
                    logger.info(f"📄 Extracting text from {kind.upper()}: {fname}")
                    txt = self._extract_text_from_document(content)
                    logger.info(f"📄 TEXT EXTRACTED from {fname}: {len(txt)} characters")
                    
                    # Fallback OCR if PDF nearly empty
                    if kind == "pdf" and (not txt.strip() or len(re.sub(r"\s+", "", txt)) < 50):
                        logger.info(f"🧠 PDF text too short ({len(txt)} chars), trying OCR for: {fname}")
                        ocr_txt = self._extract_text_with_ocr(content, kind="pdf", filename=fname)
                        if ocr_txt.strip():
                            logger.info(f"🧠 OCR SUCCESS: {fname} → {len(ocr_txt)} characters")
                            txt = ocr_txt
                        else:
                            logger.warning(f"🧠 OCR FAILED for: {fname}")
                    
                    if txt.strip():
                        text_parts.append(f"\n\n### SOURCE: {fname}\n{txt}")
                        logger.info(f"✅ ADDED TO AI CONTEXT: {fname} ({len(txt)} chars)")
                        # Show preview of text to verify content
                        preview = txt[:300].replace('\n', ' ')
                        logger.info(f"📝 CONTENT PREVIEW: {fname} → {preview}...")
                    else:
                        logger.error(f"❌ NO TEXT EXTRACTED from {fname} - file will be ignored!")
                        
                elif kind in ("xlsx", "csv"):
                    logger.info(f"📊 Parsing spreadsheet: {fname}")
                    parsed = self._parse_spreadsheet_items(fname, content)
                    items_count = len(parsed.get('items', []))
                    text_length = len(parsed.get('text', ''))
                    logger.info(f"📊 SPREADSHEET PARSED: {fname} → {items_count} items, {text_length} chars of text")
                    
                    if parsed["items"]: 
                        canonical_items.extend(parsed["items"])
                        logger.info(f"📋 PRODUCTS FOUND in {fname}: {items_count} items")
                        # Log first 3 items for verification
                        for i, item in enumerate(parsed['items'][:3]):
                            logger.info(f"📋 PRODUCT {i+1}: {item}")
                    else:
                        logger.warning(f"⚠️ NO PRODUCTS found in spreadsheet: {fname}")
                    
                    # Always add text for AI metadata extraction
                    if parsed["text"]:  
                        text_parts.append(f"\n\n### SOURCE: {fname}\n{parsed['text']}")
                        preview = parsed['text'][:300].replace('\n', ' ')
                        logger.info(f"📄 SPREADSHEET TEXT ADDED: {fname} → {preview}...")
                    else:
                        # Create summary for AI if we have items but no text
                        if parsed["items"]:
                            summary = f"EXCEL: {len(parsed['items'])} productos encontrados:\n"
                            for item in parsed["items"][:5]:  # First 5 products
                                summary += f"- {item['nombre']}: {item['cantidad']} {item['unidad']}\n"
                            text_parts.append(f"\n\n### SOURCE: {fname}\n{summary}")
                            logger.info(f"📄 SUMMARY CREATED for {fname}: {len(summary)} chars")
                        
                elif kind == "image":
                    logger.info(f"🖼️ Applying OCR to image: {fname}")
                    ocr_txt = self._extract_text_with_ocr(content, kind="image", filename=fname)
                    if ocr_txt.strip():
                        text_parts.append(f"\n\n### SOURCE: {fname} (OCR)\n{ocr_txt}")
                        logger.info(f"✅ IMAGE OCR SUCCESS: {fname} → {len(ocr_txt)} chars")
                        preview = ocr_txt[:300].replace('\n', ' ')
                        logger.info(f"📝 OCR PREVIEW: {fname} → {preview}...")
                    else:
                        logger.error(f"❌ IMAGE OCR FAILED: {fname}")
                else:
                    logger.error(f"❌ UNSUPPORTED FILE TYPE: {fname} (kind={kind})")
                    
            except Exception as e:
                logger.error(f"❌ PROCESSING ERROR for {fname}: {e}")
                import traceback
                logger.error(f"❌ FULL ERROR TRACE: {traceback.format_exc()}")

        combined_text = "\n\n".join(tp for tp in text_parts if tp.strip()) or ""
        
        # 🔍 CRITICAL DEBUG: Show what's being sent to AI
        logger.info(f"📊 FINAL PROCESSING SUMMARY:")
        logger.info(f"📊   - Files processed: {len(expanded)}")
        logger.info(f"📊   - Text parts created: {len(text_parts)}")
        logger.info(f"📊   - Canonical items found: {len(canonical_items)}")
        logger.info(f"📊   - Combined text length: {len(combined_text)} characters")
        
        if combined_text.strip():
            # Show preview of combined text
            preview = combined_text[:500].replace('\n', ' ')
            logger.info(f"📝 COMBINED TEXT PREVIEW (first 500 chars): {preview}...")
            
            # Show text structure
            sources = [part.split('\n')[0] for part in combined_text.split("### SOURCE:") if part.strip()]
            logger.info(f"📄 TEXT SOURCES DETECTED: {sources}")
        else:
            logger.warning(f"⚠️ NO COMBINED TEXT - only canonical items: {len(canonical_items)}")
        
        if not combined_text.strip() and not canonical_items:
            logger.error(f"❌ FATAL: No content extracted from ANY file!")
            raise ValueError("No se pudo extraer texto ni ítems de los archivos proporcionados")

        # 3) AI pipeline
        rfx_input.extracted_content = combined_text
        logger.info(f"🤖 SENDING TO AI: {len(combined_text)} characters of combined text")
        raw_data = self._process_with_ai(combined_text)
        
        # 🛡️ SAFETY CHECK: Handle None raw_data before accessing
        if raw_data is None:
            logger.warning(f"⚠️ raw_data is None, creating minimal structure")
            raw_data = {
                "productos": [],
                "email": None,
                "fecha_entrega": None,
                "hora_entrega": None,
                "lugar": None,
                "nombre_solicitante": None,
                "currency": None
            }
        
        # Log AI results
        ai_products_count = len(raw_data.get("productos", []))
        logger.info(f"🤖 AI EXTRACTION RESULTS: {ai_products_count} products found")
        
        if canonical_items:
            logger.info(f"📊 OVERRIDING AI products with canonical spreadsheet products: {len(canonical_items)} items (AI found {ai_products_count})")
            raw_data["productos"] = canonical_items  # Spreadsheet is canonical
        else:
            logger.info(f"📊 USING AI extracted products: {ai_products_count} items")

        validated_data = self._validate_and_clean_data(raw_data, rfx_input.id)
        
        evaluation_metadata = self._evaluate_rfx_intelligently(validated_data, rfx_input.id)
        rfx_processed = self._create_rfx_processed(validated_data, rfx_input, evaluation_metadata)
        self._save_rfx_to_database(rfx_processed, user_id=user_id)
        logger.info(f"✅ process_rfx_case done: {rfx_input.id}")
        return rfx_processed

    def _detect_content_type(self, content: bytes, filename: str) -> str:
        """Detect file content type from bytes and filename with improved detection"""
        fn = (filename or "").lower()
        
        # Robust PDF detection
        if content.startswith(b"%PDF") or fn.endswith(".pdf"):
            return "pdf"
        
        # DOCX detection (ZIP with specific structure)
        if content[:2] == b"PK":
            if fn.endswith(".docx"):
                return "docx"
            elif fn.endswith(".xlsx"):
                return "xlsx" 
            elif not fn.endswith((".docx", ".xlsx")) and not fn.endswith(".zip"):
                # This could be a DOCX without proper extension
                try:
                    import zipfile
                    with zipfile.ZipFile(io.BytesIO(content)) as zf:
                        # Check for DOCX structure
                        if any("word/" in name for name in zf.namelist()):
                            logger.info(f"🔍 Detected DOCX structure in file without .docx extension: {filename}")
                            return "docx"
                        # Check for XLSX structure
                        elif any("xl/" in name for name in zf.namelist()):
                            logger.info(f"🔍 Detected XLSX structure in file without .xlsx extension: {filename}")
                            return "xlsx"
                except:
                    pass
        
        # Excel and CSV files
        if fn.endswith(".xlsx") or fn.endswith(".xls"):
            return "xlsx"
        if fn.endswith(".csv"):
            return "csv"
        
        # Image files
        image_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"]
        if any(fn.endswith(ext) for ext in image_extensions):
            return "image"
        
        # Image magic bytes detection
        if (content.startswith(b"\x89PNG") or 
            content.startswith(b"\xFF\xD8") or  # JPEG
            content.startswith(b"GIF87a") or content.startswith(b"GIF89a") or
            content.startswith(b"RIFF") and b"WEBP" in content[:12]):
            return "image"
        
        # Text files
        if any(fn.endswith(ext) for ext in [".txt", ".md", ".text", ".rtf"]):
            return "text"
        
        # Legacy Word documents
        if fn.endswith(".doc") or content.startswith(b"\xD0\xCF\x11\xE0"):
            return "doc"
        
        # ZIP files
        if fn.endswith(".zip"):
            return "zip"
        
        # Try to detect by content if text-like
        try:
            content.decode('utf-8')
            # If we can decode as UTF-8, probably text
            if len(content) < 50000:  # Small files likely to be text
                return "text"
        except UnicodeDecodeError:
            pass
        
        # Fallback to MIME type guessing
        guessed, _ = mimetypes.guess_type(fn)
        if guessed:
            if "image" in guessed:
                return "image"
            elif "text" in guessed:
                return "text"
            elif "pdf" in guessed:
                return "pdf"
        
        # Final fallback
        logger.warning(f"⚠️ Could not detect content type for {filename}, treating as text")
        return "text"

    def _extract_text_with_ocr(self, file_bytes: bytes, kind: str = "image", filename: Optional[str] = None) -> str:
        """Optional OCR via pytesseract; for PDF, uses pdf2image if available."""
        if not USE_OCR:
            return ""
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception as e:
            logger.warning(f"⚠️ OCR unavailable (install pytesseract & pillow): {e}")
            return ""

        if kind == "image":
            try:
                img = Image.open(io.BytesIO(file_bytes))
                return pytesseract.image_to_string(img) or ""
            except Exception as e:
                logger.warning(f"⚠️ OCR image failed: {filename} → {e}")
                return ""

        if kind == "pdf":
            try:
                try:
                    from pdf2image import convert_from_bytes  # type: ignore
                except Exception as e:
                    logger.warning(f"⚠️ pdf2image unavailable for PDF OCR: {e}")
                    return ""
                pages = convert_from_bytes(file_bytes, dpi=200, fmt="png")
                out = []
                for img in pages[:10]:  # safety limit
                    out.append(pytesseract.image_to_string(img) or "")
                return "\n".join(out)
            except Exception as e:
                logger.warning(f"⚠️ OCR PDF failed: {filename} → {e}")
                return ""
        return ""

    def _normalize_date_format(self, date_str: str) -> str:
        """Normalize date formats to YYYY-MM-DD for Pydantic validation"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        date_str = date_str.strip()
        logger.info(f"🔍 PARSING DATE: '{date_str}'")
        
        # Handle ISO 8601 formats (e.g., "2025-09-06T00:00:00Z", "2025-09-06T00:00:00")
        iso_match = re.match(r'^(\d{4}-\d{1,2}-\d{1,2})T.*$', date_str)
        if iso_match:
            iso_date = iso_match.group(1)
            logger.info(f"📅 EXTRACTED ISO DATE: '{iso_date}' from '{date_str}'")
            try:
                parts = iso_date.split('-')
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                    normalized = f"{year:04d}-{month:02d}-{day:02d}"
                    logger.info(f"✅ ISO DATE NORMALIZED: '{date_str}' → '{normalized}'")
                    return normalized
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse ISO date '{iso_date}': {e}")
        
        # Handle natural language dates in Spanish
        date_natural = self._parse_natural_language_date(date_str)
        if date_natural:
            logger.info(f"✅ NATURAL LANGUAGE DATE: '{date_str}' → '{date_natural}'")
            return date_natural
        
        # Handle DD/MM/YYYY format
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
            try:
                parts = date_str.split('/')
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                    normalized = f"{year:04d}-{month:02d}-{day:02d}"
                    logger.info(f"✅ DD/MM/YYYY NORMALIZED: '{date_str}' → '{normalized}'")
                    return normalized
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse DD/MM/YYYY date '{date_str}': {e}")
        
        # Handle DD-MM-YYYY format
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', date_str):
            try:
                parts = date_str.split('-')
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                    normalized = f"{year:04d}-{month:02d}-{day:02d}"
                    logger.info(f"✅ DD-MM-YYYY NORMALIZED: '{date_str}' → '{normalized}'")
                    return normalized
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse DD-MM-YYYY date '{date_str}': {e}")
        
        # Handle YYYY/MM/DD format
        if re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', date_str):
            try:
                parts = date_str.split('/')
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                    normalized = f"{year:04d}-{month:02d}-{day:02d}"
                    logger.info(f"✅ YYYY/MM/DD NORMALIZED: '{date_str}' → '{normalized}'")
                    return normalized
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse YYYY/MM/DD date '{date_str}': {e}")
        
        # If already in YYYY-MM-DD format, validate and return
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
            try:
                parts = date_str.split('-')
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                    normalized = f"{year:04d}-{month:02d}-{day:02d}"
                    logger.info(f"✅ YYYY-MM-DD VALIDATED: '{date_str}' → '{normalized}'")
                    return normalized
            except Exception as e:
                logger.warning(f"⚠️ Failed to validate YYYY-MM-DD date '{date_str}': {e}")
        
        # Handle relative dates like "mañana", "today", etc.
        date_str_lower = date_str.lower()
        if date_str_lower in ["hoy", "today"]:
            normalized = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"✅ RELATIVE DATE: '{date_str}' → '{normalized}' (today)")
            return normalized
        elif date_str_lower in ["mañana", "tomorrow"]:
            from datetime import timedelta
            normalized = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            logger.info(f"✅ RELATIVE DATE: '{date_str}' → '{normalized}' (tomorrow)")
            return normalized
        
        # Fallback to current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        logger.error(f"❌ COULD NOT PARSE DATE: '{date_str}' - Using current date: {current_date}")
        return current_date

    def _parse_natural_language_date(self, date_str: str) -> str:
        """Parse natural language dates in Spanish like 'octubre 6', '6 de octubre', etc."""
        date_str_lower = date_str.lower().strip()
        
        # Spanish month mapping
        spanish_months = {
            'enero': 1, 'ene': 1,
            'febrero': 2, 'feb': 2,
            'marzo': 3, 'mar': 3,
            'abril': 4, 'abr': 4,
            'mayo': 5, 'may': 5,
            'junio': 6, 'jun': 6,
            'julio': 7, 'jul': 7,
            'agosto': 8, 'ago': 8,
            'septiembre': 9, 'sep': 9, 'sept': 9,
            'octubre': 10, 'oct': 10,
            'noviembre': 11, 'nov': 11,
            'diciembre': 12, 'dic': 12
        }
        
        # English month mapping
        english_months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        # Combine both mappings
        month_mapping = {**spanish_months, **english_months}
        
        current_year = datetime.now().year
        
        # Pattern: "octubre 6", "6 octubre", "octubre 6, 2025", "6 de octubre"
        for month_name, month_num in month_mapping.items():
            if month_name in date_str_lower:
                # Look for day numbers near the month
                words = date_str_lower.replace(',', ' ').replace('de', ' ').split()
                day = None
                year = current_year
                
                # Find day number
                for word in words:
                    if word.isdigit():
                        num = int(word)
                        if 1 <= num <= 31:  # Could be a day
                            day = num
                        elif num > 1900:  # Could be a year
                            year = num
                
                if day:
                    try:
                        # Validate the date
                        import calendar
                        if day <= calendar.monthrange(year, month_num)[1]:
                            result = f"{year:04d}-{month_num:02d}-{day:02d}"
                            logger.info(f"🗓️ PARSED NATURAL DATE: '{date_str}' → month='{month_name}'({month_num}), day={day}, year={year} → '{result}'")
                            return result
                        else:
                            logger.warning(f"⚠️ Invalid day {day} for month {month_num} year {year}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error validating natural date: {e}")
                break
        
        return None

    def _normalize_time_format(self, time_str: str) -> str:
        """Normalize time formats for Pydantic validation"""
        if not time_str:
            return "12:00"
        
        time_str = time_str.strip().lower()
        
        # Handle AM/PM formats
        if 'a.m' in time_str or 'am' in time_str:
            # Extract hour and minute
            time_part = time_str.replace('a.m', '').replace('am', '').strip()
            if ':' in time_part:
                try:
                    hour, minute = time_part.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    # Convert to 24h format
                    if hour == 12:
                        hour = 0  # 12 AM = 00:00
                    return f"{hour:02d}:{minute:02d}"
                except:
                    pass
        elif 'p.m' in time_str or 'pm' in time_str:
            # Extract hour and minute
            time_part = time_str.replace('p.m', '').replace('pm', '').strip()
            if ':' in time_part:
                try:
                    hour, minute = time_part.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    # Convert to 24h format
                    if hour != 12:
                        hour += 12
                    return f"{hour:02d}:{minute:02d}"
                except:
                    pass
        
        # If already in HH:MM format, validate and return
        if ':' in time_str:
            try:
                parts = time_str.split(':')
                if len(parts) == 2:
                    hour, minute = int(parts[0]), int(parts[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return f"{hour:02d}:{minute:02d}"
            except:
                pass
        
        # Fallback
        return "12:00"

    def _parse_spreadsheet_items(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Lee XLSX/CSV y devuelve {'items': [...], 'text': 'csv-like'} con mapeo:
        nombre <- Item, cantidad <- Quantity, unidad <- UOM, notes <- Item # (+Description)."""
        try:
            import pandas as pd  # type: ignore
            from io import BytesIO
        except Exception as e:
            logger.warning(f"⚠️ pandas no disponible, saltando parseo de {filename}: {e}")
            return {"items": [], "text": ""}
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(BytesIO(content))
            else:
                df = pd.read_excel(BytesIO(content))
            if df is None or df.empty:
                logger.warning(f"⚠️ Hoja vacía en {filename}")
                return {"items": [], "text": ""}

            # Normalizar cabeceras
            def _norm(s: str) -> str:
                return str(s).strip().lower()
            cols = {_norm(c): c for c in df.columns}
            def pick(cands: List[str]) -> Optional[str]:
                for c in cands:
                    k = _norm(c)
                    if k in cols: return cols[k]
                    k2 = k.replace(" ", "")
                    if k2 in cols: return cols[k2]
                return None

            itemnum_col = pick(["item #","item#","item no","item nro","item number","numero de item","número de item","id","code","codigo","código"])
            name_col    = pick(["item","producto","product","nombre"])  # ← nombre <- Item
            desc_col    = pick(["description","descripcion","descripción","detalle","item description"])
            qty_col     = pick(["quantity","qty","cantidad","cant","q"])
            unit_col    = pick(["uom","unidad","unidad_medida","unit","units","unidad de medida"])

            logger.info(f"📑 [{filename}] Cols detectadas -> Item#:{itemnum_col} Item:{name_col} Desc:{desc_col} Qty:{qty_col} UOM:{unit_col}")

            def to_int(val) -> int:
                try:
                    if val is None: return 1
                    if isinstance(val, (int, float)): return max(1, int(round(float(val))))
                    s = str(val).strip()
                    if s == "" or s.lower() in {"nan","none","null"}: return 1
                    s = s.replace(" ", "")
                    if "," in s and "." in s:
                        # 1,000.50 -> 1000.50
                        s = s.replace(",", "")
                    else:
                        # 1.000,50 or 25 -> 1 000.50 or 25.0
                        s = s.replace(",", ".")
                    return max(1, int(round(float(s))))
                except Exception:
                    return 1

            def norm_uom(u: Optional[str]) -> str:
                if not u: return "unidades"
                s = str(u).strip().lower().replace(".", "").replace(",", "")
                aliases = {
                    "und":"unidades","un":"unidades","unidad":"unidades","unid":"unidades",
                    "pcs":"unidades","pc":"unidades","pz":"unidades","pza":"unidades",
                    "ea":"unidades","each":"unidades","units":"unidades","unit":"unidades",
                    "set":"set","sets":"set","kg":"kg","kilogram":"kg","kilogramos":"kg",
                    "g":"g","gr":"g","l":"l","lt":"l","liter":"l","litro":"l","litros":"l",
                    "m":"m","mt":"m","caja":"caja","box":"caja","pack":"pack"
                }
                return aliases.get(s, s or "unidades")

            items: List[Dict[str, Any]] = []
            for _, row in df.iterrows():
                nombre = (str(row.get(name_col, "")).strip() if name_col else "")
                if not nombre or nombre.lower() in {"nan","none","null",""}:
                    continue
                cantidad = to_int(row.get(qty_col)) if qty_col else 1
                unidad = norm_uom(str(row.get(unit_col)) if unit_col else None)
                prod: Dict[str, Any] = {"nombre": nombre, "cantidad": cantidad, "unidad": unidad}
                # notes: Item # + Description (si existe y no hay campo dedicated)
                notes_parts = []
                if itemnum_col:
                    v = str(row.get(itemnum_col, "")).strip()
                    if v and v.lower() not in {"nan","none","null",""}:
                        notes_parts.append(f"item_number:{v}")
                if desc_col:
                    d = str(row.get(desc_col, "")).strip()
                    if d and d.lower() not in {"nan","none","null",""}:
                        notes_parts.append(f"desc:{d}")
                if notes_parts:
                    prod["notes"] = " | ".join(notes_parts)
                items.append(prod)

            lines = ["ITEMS_FROM_SPREADSHEET (CANONICAL):", "nombre,cantidad,unidad"]
            for it in items:
                lines.append(f"{it['nombre']},{it['cantidad']},{it['unidad']}")
            logger.info(f"📊 [{filename}] Ítems parseados: {len(items)}")
            return {"items": items, "text": "\n".join(lines)}
        except Exception as e:
            logger.warning(f"⚠️ Falló parseo de hoja {filename}: {e}")
            return {"items": [], "text": ""}
