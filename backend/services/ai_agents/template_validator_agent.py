"""
✅ Template Validator AI Agent
Responsabilidad: Validar que el HTML generado tenga el contenido correcto del request_data
Enfoque: Simple - Verificar que los datos estén insertados correctamente
"""

import logging
import json
from typing import Dict, Any
from openai import OpenAI

from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class TemplateValidatorAgent:
    """
    Agente simple: Valida que el HTML tenga los datos del request_data
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.client = OpenAI(api_key=self.openai_config.api_key)
    
    async def validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida que HTML generado tenga el contenido del request_data
        
        Args:
            request: {
                "html_generated": "<html>...</html>",
                "html_template": "<html>...</html>",
                "branding_config": {...},
                "request_data": {...}  # Datos que deberían estar en el HTML
            }
        """
        try:
            html_generated = request.get("html_generated", "")
            html_template = request.get("html_template", "")
            branding_config = request.get("branding_config", {})
            request_data = request.get("request_data", {})
            
            if not html_generated:
                return {
                    "is_valid": False,
                    "issues": ["Missing HTML content"],
                    "similarity_score": 0.0,
                    "html_generated": html_generated,
                    "request_data": request_data
                }
            
            # Validación con AI
            result = await self._validate_with_ai(html_generated, html_template, branding_config, request_data)
            
            # Log SOLO el JSON response
            logger.info(f"📋 Validator JSON Response: {json.dumps(result, ensure_ascii=False)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Validator error: {e}")
            return {
                "is_valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "similarity_score": 0.0,
                "html_generated": html_generated,
                "request_data": request_data
            }
    
    
    async def _validate_with_ai(
        self, 
        html_generated: str, 
        html_template: str,
        branding_config: Dict,
        request_data: Dict
    ) -> Dict[str, Any]:
        """Validación con AI - Verifica que el HTML tenga el contenido del request_data"""
        
        # System prompt: Instrucciones de qué hacer con el JSON que recibe
        system_prompt = """Eres un validador de presupuestos HTML profesional.

Tu tarea es analizar el JSON que recibirás y validar que:

1. **CONTENIDO CORRECTO:**
   - El HTML generado contiene TODOS los datos del request_data
   - Nombre del cliente está presente
   - Solicitud/descripción está presente
   - Todos los productos están listados
   - Total y precios son correctos
   - Fecha está presente

2. **ESTRUCTURA DEL TEMPLATE:**
   - Mantiene la MISMA estructura que el template original
   - NO agrega elementos nuevos no solicitados
   - Mantiene el MISMO espaciado y márgenes

3. **BRANDING CONSISTENTE:**
   - Usa los MISMOS colores del branding configurado
   - Mantiene los MISMOS estilos CSS
   - Logo está presente y correcto

**FORMATO DE RESPUESTA:**

Debes responder ÚNICAMENTE con un JSON válido con esta estructura exacta:

{
  "is_valid": true o false,
  "similarity_score": número entre 0.0 y 1.0,
  "issues": ["lista", "de", "problemas"],
  "recommendations": ["lista", "de", "recomendaciones"]
}

NO incluyas explicaciones adicionales.
NO incluyas el HTML en tu respuesta.
NO incluyas el request_data en tu respuesta.
SOLO el JSON de validación."""
        
        # User prompt: JSON directo del proposal generator
        validation_payload = {
            "html_template": html_template[:10000],  # Primeros 10000 chars del template
            "html_generated": html_generated[:10000],  # Primeros 10000 chars del HTML generado
            "branding_config": {
                "primary_color": branding_config.get('primary_color', 'N/A'),
                "table_header_bg": branding_config.get('table_header_bg', 'N/A'),
                "table_header_text": branding_config.get('table_header_text', 'N/A')
            },
            "request_data": request_data
        }
        
        user_prompt = json.dumps(validation_payload, indent=2, ensure_ascii=False)
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Agregar html_generated y request_data al resultado
            return {
                "is_valid": result.get("is_valid", False),
                "issues": result.get("issues", []),
                "similarity_score": result.get("similarity_score", 0.0),
                "recommendations": result.get("recommendations", []),
                "html_generated": html_generated,
                "request_data": request_data
            }
            
        except Exception as e:
            logger.error(f"❌ AI validation failed: {e}")
            return {
                "is_valid": False,
                "issues": [f"AI validation error: {str(e)}"],
                "similarity_score": 0.0,
                "recommendations": [],
                "html_generated": html_generated,
                "request_data": request_data
            }


# Singleton instance
template_validator_agent = TemplateValidatorAgent()
