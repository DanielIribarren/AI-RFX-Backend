"""
✅ Template Validator + Auto-Fix AI Agent
Responsabilidad: Validar HTML Y corregir automáticamente cualquier problema encontrado
Enfoque: Validar → Si falla → Corregir → Retornar HTML corregido
Elimina la necesidad de retries externos - el agente se auto-corrige
"""

import logging
import asyncio
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
        Valida HTML Y corrige automáticamente si encuentra problemas
        
        Args:
            request: {
                "html_generated": "<html>...</html>",
                "html_template": "<html>...</html>",
                "branding_config": {...},
                "request_data": {...}  # Datos que deberían estar en el HTML
            }
        
        Returns:
            {
                "is_valid": True (siempre True después de auto-corrección),
                "html_corrected": "<html>...corregido...</html>",
                "corrections_made": ["Lista de correcciones aplicadas"],
                "similarity_score": 0.95
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
                    "html_corrected": html_generated,
                    "corrections_made": ["HTML vacío - no se puede corregir"],
                    "similarity_score": 0.0
                }
            
            # Validación + Auto-corrección con AI
            result = await self._validate_and_fix_with_ai(
                html_generated, 
                html_template, 
                branding_config, 
                request_data
            )
            
            # Log de resultados
            corrections = result.get("corrections_made", [])
            if corrections:
                logger.info(f"🔧 Auto-corrections applied: {len(corrections)} fixes")
                for correction in corrections[:3]:  # Log primeras 3
                    logger.info(f"  ✓ {correction}")
            else:
                logger.info(f"✅ Validation PASSED - No corrections needed")
            
            logger.info(f"📊 Final Score: {result.get('similarity_score', 0.0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Validator error: {e}")
            return {
                "is_valid": False,
                "html_corrected": html_generated,
                "corrections_made": [f"Error en validación: {str(e)}"],
                "similarity_score": 0.0
            }
    
    
    async def _validate_and_fix_with_ai(
        self, 
        html_generated: str, 
        html_template: str,
        branding_config: Dict,
        request_data: Dict
    ) -> Dict[str, Any]:
        """Validación + Auto-corrección con AI - Valida Y corrige automáticamente"""
        
        # System prompt: Validador ESTRICTO que CORRIGE automáticamente
        system_prompt = """Eres un validador Y corrector experto de documentos HTML profesionales.

## OBJETIVO PRINCIPAL:
1. Validar el HTML generado con CRITERIOS ESTRICTOS
2. Si encuentras problemas → CORREGIRLOS AUTOMÁTICAMENTE
3. Retornar HTML corregido + lista de correcciones aplicadas

## CRITERIOS DE VALIDACIÓN (ESTRICTOS):

### ✅ CONTENIDO OBLIGATORIO:
- Nombre del cliente (visible y correcto)
- Descripción de la solicitud completa
- TODOS los productos de request_data (sin omitir ninguno)
- Precios correctos para cada producto
- Subtotal, coordinación (si aplica), impuestos (si aplica), total
- Fechas: actual y validez (30 días después)
- Logo o placeholder {{LOGO_PLACEHOLDER}}

### ✅ ESTRUCTURA PROFESIONAL:
- HTML bien formado (tags cerrados)
- Tabla con columnas: Producto, Cantidad, Unidad, Precio Unit., Total
- Header con logo/empresa
- Footer con información de contacto
- Estilos CSS inline para PDF

### ✅ BRANDING CONSISTENTE:
- Colores del branding aplicados correctamente
- Contraste legible (texto oscuro en fondos claros, viceversa)
- Espaciado profesional entre secciones

## PROCESO DE AUTO-CORRECCIÓN:

Si encuentras problemas, DEBES corregirlos:

1. **Contenido faltante** → Agregar del request_data
2. **Productos omitidos** → Insertar en la tabla
3. **Precios incorrectos** → Corregir con valores de request_data
4. **Totales mal calculados** → Recalcular correctamente
5. **HTML mal formado** → Cerrar tags, corregir estructura
6. **Contraste pobre** → Ajustar colores para legibilidad
7. **Espaciado malo** → Agregar márgenes profesionales

## FORMATO DE RESPUESTA (JSON):

{
  "is_valid": true,  // Siempre true después de correcciones
  "html_corrected": "HTML COMPLETO corregido con TODAS las correcciones aplicadas",
  "corrections_made": [
    "Descripción específica de cada corrección aplicada",
    "Ej: Agregado producto 'X' que faltaba en la tabla",
    "Ej: Corregido total de $1500 a $1690.94",
    ...
  ],
  "similarity_score": float (0.0 a 1.0),  // Qué tan similar quedó al template original
  "quality_score": float (0.0 a 1.0)  // Calidad final del documento
}

## REGLAS CRÍTICAS:

1. **SIEMPRE retornar HTML corregido** - Nunca devolver HTML con errores
2. **corrections_made vacío []** solo si el HTML original estaba perfecto
3. **html_corrected debe ser COMPLETO** - No truncar, incluir TODO
4. **Preservar contenido original** - Solo corregir problemas, no reescribir todo
5. **Aplicar TODAS las correcciones necesarias** - No dejar problemas sin resolver
6. **is_valid: true** después de correcciones (false solo si imposible corregir)

⚠️ IMPORTANTE: Sé ESTRICTO en validación pero EFECTIVO en corrección. El HTML final debe ser perfecto."""
        
        # User prompt: Datos estructurados para validación (SIN truncar HTML)
        validation_payload = {
            "html_template": html_template,  # HTML COMPLETO - calidad > costo
            "html_generated": html_generated,  # HTML COMPLETO - no truncar
            "branding_config": {
                "primary_color": branding_config.get('primary_color', 'N/A'),
                "table_header_bg": branding_config.get('table_header_bg', 'N/A'),
                "table_header_text": branding_config.get('table_header_text', 'N/A')
            },
            "request_data": {
                "client_name": request_data.get('client_name', 'N/A'),
                "solicitud": request_data.get('solicitud', 'N/A'),
                "products_count": len(request_data.get('products', [])),
                "total": request_data.get('pricing', {}).get('total_formatted', '$0.00'),
                "current_date": request_data.get('current_date', 'N/A')
            }
        }
        
        user_prompt = json.dumps(validation_payload, indent=2, ensure_ascii=False)
        
        try:
            # Ejecutar llamada síncrona en thread separado para no bloquear
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Baja para validación consistente
                # SIN max_tokens - dejar que el modelo use lo necesario (calidad > costo)
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Retornar HTML corregido + metadata
            return {
                "is_valid": result.get("is_valid", True),  # True después de correcciones
                "html_corrected": result.get("html_corrected", html_generated),
                "corrections_made": result.get("corrections_made", []),
                "similarity_score": result.get("similarity_score", 0.0),
                "quality_score": result.get("quality_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ AI validation+fix failed: {e}")
            # Fallback: retornar HTML original sin correcciones
            return {
                "is_valid": False,
                "html_corrected": html_generated,
                "corrections_made": [f"Error en auto-corrección: {str(e)}"],
                "similarity_score": 0.0,
                "quality_score": 0.0
            }


# Singleton instance
template_validator_agent = TemplateValidatorAgent()
