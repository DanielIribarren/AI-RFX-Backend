"""
🤖 AI Extractor - Extracción de datos estructurados con OpenAI Function Calling
Usa GPT-4o para extraer y validar datos de documentos RFX
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

from backend.core.config import get_openai_config
from backend.schemas.rfx_extraction_schema import RFX_EXTRACTION_FUNCTION
from backend.prompts.rfx_extraction import RFXExtractionPrompt
from backend.utils.retry_decorator import retry_on_failure

logger = logging.getLogger(__name__)


class AIExtractor:
    """
    Extractor de datos estructurados usando OpenAI Function Calling.
    
    Principio AI-FIRST: El LLM hace TODO el trabajo inteligente:
    - Extracción de datos
    - Validación de formatos (emails, fechas, teléfonos)
    - Normalización de unidades
    - Detección de dominio
    - Categorización de productos
    
    El código solo orquesta y maneja errores.
    """
    
    def __init__(self, model: str = "gpt-4o", debug_mode: bool = False):
        """
        Args:
            model: Modelo de OpenAI a usar (default: gpt-4o)
            debug_mode: Habilitar logs detallados
        """
        config = get_openai_config()
        self.client = OpenAI(api_key=config.api_key)
        self.model = model
        self.debug_mode = debug_mode
        self.timeout = config.timeout
        
        logger.info(f"🤖 AIExtractor initialized with model: {model}")
    
    @retry_on_failure(max_retries=2, initial_delay=2.0)
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrae datos estructurados del texto usando Function Calling.
        
        Args:
            text: Texto del documento a analizar
            
        Returns:
            Dict con datos extraídos en formato de base de datos
            
        Raises:
            Exception: Si la extracción falla después de reintentos
        """
        if not text or len(text.strip()) < 10:
            logger.warning("⚠️ Text too short for extraction")
            return self._get_empty_result()
        
        logger.info(f"🤖 Starting AI extraction ({len(text)} chars)")
        
        try:
            # Detectar si hay múltiples documentos
            has_multiple_docs = "### SOURCE:" in text
            
            # Construir mensajes
            messages = RFXExtractionPrompt.build_messages(text, has_multiple_docs)
            
            if self.debug_mode:
                logger.debug(f"📤 Sending to OpenAI:\n{json.dumps(messages, indent=2)}")
            
            # Llamada a OpenAI con Function Calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[RFX_EXTRACTION_FUNCTION],
                tool_choice={
                    "type": "function",
                    "function": {"name": "extract_rfx_data"}
                },
                temperature=0.1,  # Baja temperatura para consistencia
                timeout=self.timeout
            )
            
            # Extraer resultado del function call
            tool_call = response.choices[0].message.tool_calls[0]
            extracted_data = json.loads(tool_call.function.arguments)
            
            if self.debug_mode:
                logger.debug(f"📥 Received from OpenAI:\n{json.dumps(extracted_data, indent=2)}")
            
            # Validar resultado
            self._validate_extraction(extracted_data)
            
            # Log resumen
            product_count = len(extracted_data.get('requested_products', []))
            confidence = extracted_data.get('extraction_confidence', 0.0)
            logger.info(f"✅ Extraction complete: {product_count} products, confidence: {confidence:.2f}")
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise Exception(f"Invalid JSON response from AI: {e}")
            
        except Exception as e:
            logger.error(f"❌ AI extraction error: {e}")
            raise
    
    def extract_with_retry_on_error(self, text: str, previous_error: str) -> Dict[str, Any]:
        """
        Reintenta extracción con contexto del error anterior.
        
        Args:
            text: Texto del documento
            previous_error: Descripción del error anterior
            
        Returns:
            Dict con datos extraídos
        """
        logger.info(f"🔄 Retrying extraction with error context")
        
        try:
            # Construir mensajes con contexto de error
            messages = RFXExtractionPrompt.build_retry_messages(text, previous_error)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[RFX_EXTRACTION_FUNCTION],
                tool_choice={
                    "type": "function",
                    "function": {"name": "extract_rfx_data"}
                },
                temperature=0.1,
                timeout=self.timeout
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            extracted_data = json.loads(tool_call.function.arguments)
            
            self._validate_extraction(extracted_data)
            
            logger.info(f"✅ Retry successful")
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Retry failed: {e}")
            raise
    
    def _validate_extraction(self, data: Dict[str, Any]) -> None:
        """
        Valida que la extracción tenga los campos mínimos requeridos.
        
        Args:
            data: Datos extraídos
            
        Raises:
            ValueError: Si faltan campos críticos
        """
        required_fields = ['title', 'description', 'requested_products']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validar que haya al menos un producto
        products = data.get('requested_products', [])
        if not products:
            logger.warning("⚠️ No products extracted")
        
        # Validar estructura de productos
        for i, product in enumerate(products):
            if not isinstance(product, dict):
                raise ValueError(f"Product {i} is not a dict")
            
            if 'product_name' not in product:
                raise ValueError(f"Product {i} missing product_name")
            
            if 'quantity' not in product:
                raise ValueError(f"Product {i} missing quantity")
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """
        Retorna un resultado vacío válido.
        
        Returns:
            Dict con estructura mínima
        """
        return {
            'title': 'Sin título',
            'description': 'No se pudo extraer información del documento',
            'rfx_type': 'rfq',
            'requested_products': [],
            'extraction_confidence': 0.0,
            'requester_info': {},
            'delivery_info': {},
            'special_requirements': []
        }


# Singleton para reutilización
ai_extractor = AIExtractor(
    model=get_openai_config().model,
    debug_mode=False  # Cambiar a True para debugging
)
