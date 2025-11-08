"""
🎨 PDF Optimizer AI Agent
Responsabilidad: Optimizar HTML para conversión PDF profesional
Enfoque: Analizar críticamente y tomar decisiones inteligentes sobre:
- Paginación (page-breaks)
- Anchos de tabla
- Espaciado profesional
- Centrado de contenido
- Estructura header/content/footer
"""

import logging
from typing import Dict, Any
from openai import OpenAI

from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class PDFOptimizerAgent:
    """
    Agente especializado en optimizar HTML para conversión PDF profesional
    Este es el agente MÁS INTELIGENTE - toma decisiones críticas sobre layout
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.client = OpenAI(api_key=self.openai_config.api_key)
    
    async def optimize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimiza HTML para conversión PDF profesional
        
        Args:
            request: {
                "html_content": "<html>...</html>",
                "validation_results": {  
                    "is_valid": True/False,
                    "issues": ["issue1", "issue2"],
                    "similarity_score": 0.95,
                    "retries_performed": 2
                },
                "branding_config": {  
                    "primary_color": "#0e2541",
                    "table_header_bg": "#f0f0f0",
                    ...
                },
                "page_config": {
                    "size": "letter",  # letter, a4
                    "orientation": "portrait"
                },
                "quality_requirements": {
                    "professional_spacing": True,
                    "table_centering": True,
                    "min_margin": "15mm",
                    "max_table_width": "190mm"
                }
            }
        
        Returns:
            {
                "status": "success" | "error",
                "html_optimized": "<html>...optimizado...</html>",
                "analysis": {
                    "table_width": "190mm",
                    "estimated_pages": 2,
                    "adjustments_made": [...],
                    "warnings": [...]
                }
            }
        """
        try:
            logger.info("🎨 PDF Optimizer Agent - Starting optimization")
            
            html_content = request.get("html_content", "")
            validation_results = request.get("validation_results", {})
            branding_config = request.get("branding_config", {})
            page_config = request.get("page_config", {})
            quality_req = request.get("quality_requirements", {})
            
            if not html_content:
                return {
                    "status": "error",
                    "error": "html_content is required",
                    "html_optimized": None
                }
            
            # Análisis y optimización con AI
            optimization_result = await self._optimize_with_ai(
                html_content, 
                validation_results,
                branding_config,
                page_config, 
                quality_req
            )
            
            logger.info(f"✅ PDF optimization complete - {len(optimization_result.get('adjustments_made', []))} adjustments")
            
            return {
                "status": "success",
                "html_optimized": optimization_result.get("html_optimized"),
                "analysis": {
                    "table_width": optimization_result.get("table_width"),
                    "estimated_pages": optimization_result.get("estimated_pages"),
                    "adjustments_made": optimization_result.get("adjustments_made", []),
                    "warnings": optimization_result.get("warnings", [])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in PDF Optimizer Agent: {e}")
            return {
                "status": "error",
                "error": str(e),
                "html_optimized": html_content  # Fallback: devolver HTML sin optimizar
            }
    
    async def _optimize_with_ai(
        self, 
        html_content: str, 
        validation_results: Dict,
        branding_config: Dict,
        page_config: Dict,
        quality_req: Dict
    ) -> Dict[str, Any]:
        """Optimización inteligente con AI"""
        
        page_size = page_config.get("size", "letter")
        max_width = "216mm" if page_size == "letter" else "210mm"  # Letter vs A4
        
        # System prompt: Instrucciones de qué hacer con el JSON que recibe
        system_prompt = """Eres un experto en optimización de HTML para conversión PDF profesional.

Tu tarea es analizar el JSON que recibirás y optimizar el HTML para que se vea PERFECTO al convertirse en PDF.

**OPTIMIZACIONES CRÍTICAS:**

1. **LOGOS EN BASE64:**
   - NUNCA modifiques las imágenes con src="data:image/..."
   - Asegura que tengan: max-width: 100%, height: auto
   - Agrega: page-break-inside: avoid
   - Mantén el CSS: image-rendering: -webkit-optimize-contrast

2. **ESTRUCTURA Y ESPACIADO:**
   - Centrar tabla horizontalmente
   - Espaciado profesional: 30px entre secciones
   - Header: máximo 15% de altura
   - Content: mínimo 70%
   - Footer: máximo 15%

3. **PAGINACIÓN:**
   - Si >15 productos: agregar page-break cada 15 filas
   - Header de tabla debe repetirse en cada página
   - NUNCA cortar una fila entre páginas

4. **ANCHOS Y MÁRGENES:**
   - Tabla máxima: 190mm (letter) o 180mm (A4)
   - Márgenes mínimos: 15mm
   - Si tabla muy ancha: ajustar proporcionalmente

5. **COMPATIBILIDAD PDF:**
   - Agregar: -webkit-print-color-adjust: exact
   - Agregar: print-color-adjust: exact
   - Usar unidades absolutas (mm, pt)
   - NO usar position: fixed

6. **COLORES Y BRANDING:**
   - MANTENER colores exactos del branding
   - NO modificar estilos del template
   - Asegurar que colores se impriman correctamente

**FORMATO DE RESPUESTA:**

Debes responder ÚNICAMENTE con un JSON válido:

{
  "html_optimized": "HTML completo optimizado con todos los ajustes",
  "table_width": "190mm",
  "estimated_pages": 2,
  "adjustments_made": ["ajuste1", "ajuste2", ...],
  "warnings": ["warning1", "warning2", ...],
  "quality_score": 0.95
}

NO incluyas explicaciones adicionales.
SOLO el JSON de optimización."""
        
        # User prompt: JSON directo del validator
        optimization_payload = {
            "html_content": html_content,
            "validation_results": validation_results,
            "branding_config": branding_config,
            "page_config": {
                "size": page_size,
                "max_width": max_width,
                "orientation": page_config.get('orientation', 'portrait')
            },
            "quality_requirements": {
                "min_margin": quality_req.get('min_margin', '15mm'),
                "max_table_width": quality_req.get('max_table_width', '190mm'),
                "professional_spacing": quality_req.get('professional_spacing', True),
                "table_centering": quality_req.get('table_centering', True)
            }
        }
        
        import json
        user_prompt = json.dumps(optimization_payload, indent=2, ensure_ascii=False)
        
        # Nota: Truncar HTML si es muy largo para evitar exceder límites de tokens
        if len(user_prompt) > 50000:
            # Truncar HTML pero mantener estructura
            html_preview = html_content[:10000] + "\n...[HTML truncado]...\n" + html_content[-5000:]
            optimization_payload["html_content"] = html_preview
            user_prompt = json.dumps(optimization_payload, indent=2, ensure_ascii=False)
        
        logger.info(f"📤 Sending to AI - Payload size: {len(user_prompt)} chars")
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ PDF optimization complete - Adjustments: {len(result.get('adjustments_made', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AI optimization failed: {e}")
            # Fallback: devolver HTML sin optimizar
            return {
                "html_optimized": html_content,
                "table_width": "unknown",
                "estimated_pages": 1,
                "adjustments_made": [],
                "warnings": [f"Optimization failed: {str(e)}"],
                "quality_score": 0.5
            }


# Singleton instance
pdf_optimizer_agent = PDFOptimizerAgent()
