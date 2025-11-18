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
import asyncio
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
        Optimiza HTML para conversión PDF profesional multipágina
        Enfoque: Paginación inteligente, espaciado profesional, layout optimizado
        """
        try:
            logger.info("🎨 PDF Optimizer Agent - Starting optimization")
            
            html_content = request.get("html_content", "")
            validation_results = request.get("validation_results", {})
            page_config = request.get("page_config", {})
            quality_req = request.get("quality_requirements", {})
            branding_config = request.get("branding_config", {})
            
            if not html_content:
                return {
                    "status": "error",
                    "error": "html_content is required",
                    "html_optimized": None
                }
            
            # Optimización completa con AI para paginación multipágina
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
        
        # System prompt SIMPLIFICADO para respuestas más rápidas
        system_prompt = """Eres un experto en optimización de HTML para conversión PDF multipágina.

## OBJETIVO:
Optimizar HTML para PDF profesional con paginación inteligente. Mantener TODO el contenido intacto.

## OPTIMIZACIONES CRÍTICAS:

### 1. PAGINACIÓN MULTIPÁGINA:
- Si >12 productos: agregar `page-break-after: auto;` cada 12 filas
- Header de tabla: `display: table-header-group;` (repetir en cada página)
- Filas: `page-break-inside: avoid;` (no partir filas entre páginas)

### 2. CSS OBLIGATORIO:
```css
@page { size: letter; margin: 15mm; }
body { -webkit-print-color-adjust: exact; }
table { page-break-inside: auto; max-width: 190mm; margin: 0 auto; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
img { max-width: 100%; page-break-inside: avoid; }
```

### 3. PRESERVAR:
- Placeholder {{LOGO_PLACEHOLDER}} sin modificar
- Todos los productos y precios
- Colores del branding
- Contenido completo

## RESPUESTA JSON:
{
  "html_optimized": "HTML completo optimizado",
  "table_width": "190mm",
  "estimated_pages": 2,
  "adjustments_made": ["Lista de ajustes"],
  "warnings": [],
  "quality_score": 1.0
}

⚠️ NO truncar HTML. Retornar contenido completo."""
        
        # User prompt: HTML COMPLETO sin truncar (calidad > costo)
        optimization_payload = {
            "html_content": html_content,  # HTML COMPLETO - NO truncar
            "validation_results": {
                "is_valid": validation_results.get("is_valid", False),
                "issues_count": len(validation_results.get("issues", [])),
                "similarity_score": validation_results.get("similarity_score", 0.0)
            },
            "branding_config": {
                "primary_color": branding_config.get('primary_color', '#000000'),
                "secondary_color": branding_config.get('secondary_color', '#ffffff')
            },
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
        
        logger.info(f"📤 Sending HTML COMPLETO to AI - Size: {len(html_content)} chars (NO truncado)")
        logger.info(f"🤖 Model: {self.openai_config.model}, Temperature: 0.2")
        
        try:
            import time
            start_time = time.time()
            
            logger.info("⏳ Calling OpenAI API...")
            
            # Ejecutar llamada síncrona en thread separado para no bloquear
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Baja temperatura para optimización precisa y consistente
                # SIN max_tokens - dejar que el modelo genere HTML completo (calidad > costo)
                response_format={"type": "json_object"}
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ OpenAI API responded in {elapsed:.2f}s")
            
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
