"""
🔍 Vision Analysis Service - Análisis de imágenes con GPT-4 Vision
Analiza logos y templates una sola vez, cachea resultados en BD
"""
import base64
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VisionAnalysisService:
    """
    Servicio para análisis de imágenes con GPT-4 Vision
    Análisis se hace UNA VEZ y se cachea en base de datos
    """
    
    def __init__(self):
        from backend.core.config import get_openai_config
        self.config = get_openai_config()
        self.client = None
    
    def _get_client(self):
        """Lazy initialization de OpenAI client"""
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("OpenAI module not installed. Run: pip install openai")
        return self.client
    
    async def analyze_logo(self, image_path: str) -> Dict:
        """
        Análisis MÍNIMO del logo - Solo extracción de colores
        El logo se usa DIRECTAMENTE en el HTML, NO se recrea
        
        Args:
            image_path: Ruta al archivo de imagen del logo
            
        Returns:
            Dict con análisis básico (solo colores para referencia)
        """
        logger.info(f"🔍 Extracting colors from logo: {image_path}")
        
        # IMPORTANTE: Solo extraemos colores básicos con Pillow
        # NO usamos GPT-4 Vision porque el logo se usa tal cual
        return self._fallback_logo_analysis(image_path)
    
    async def analyze_template(self, template_path: str) -> Dict:
        """
        Analiza template de presupuesto con GPT-4 Vision
        Retorna análisis completo para cachear en BD
        
        Args:
            template_path: Ruta al archivo del template (PDF o imagen)
            
        Returns:
            Dict con análisis detallado del template
        """
        logger.info(f"🔍 Analyzing template: {template_path}")
        
        try:
            # Si es PDF, convertir primera página a imagen
            if template_path.lower().endswith('.pdf'):
                image_path = await self._convert_pdf_to_image(template_path)
            else:
                image_path = template_path
            
            image_data = self._encode_image(image_path)
            
            prompt = """
Analiza ÚNICAMENTE el FORMATO VISUAL de este documento de presupuesto.

IMPORTANTE: NO analices contenido textual ni datos específicos. Solo analiza:
- Formato y estructura visual
- Colores utilizados
- Espaciados y márgenes
- Distribución de elementos
- Orden de las secciones

Responde SOLO con el siguiente JSON (sin texto adicional, sin markdown):

{
  "layout_structure": "header-client-products-totals-footer",
  "sections": [
    {
      "name": "header",
      "has_logo_space": true,
      "logo_position": "top-left",
      "visual_elements": ["company_name", "document_title", "date_box"]
    },
    {
      "name": "client_info",
      "position": "after_header",
      "layout": "single_column"
    },
    {
      "name": "products_table",
      "columns_count": 4,
      "has_header_row": true
    },
    {
      "name": "totals",
      "position": "bottom_right",
      "layout": "aligned_right"
    }
  ],
  "color_scheme": {
    "primary": "#2c5f7c",
    "secondary": "#ffffff",
    "backgrounds": ["#f0f0f0"],
    "borders": "#000000",
    "text": "#000000"
  },
  "table_style": {
    "has_borders": true,
    "border_width": "1px",
    "border_color": "#000000",
    "header_background": "#f0f0f0",
    "alternating_rows": false,
    "cell_padding": "6px"
  },
  "typography": {
    "font_family": "Arial, sans-serif",
    "company_name_size": "24px",
    "title_size": "18px",
    "body_size": "11px",
    "table_header_weight": "bold"
  },
  "spacing": {
    "section_margins": "20px",
    "table_spacing": "10px",
    "line_height": "1.5"
  },
  "design_style": "professional"
}

Instrucciones CRÍTICAS - SOLO FORMATO VISUAL:
1. Identifica la ESTRUCTURA de secciones (orden visual, no contenido)
2. Extrae COLORES en formato hexadecimal exacto
3. Mide ESPACIADOS: márgenes, padding, separación entre secciones
4. Describe DISTRIBUCIÓN: alineación, posición de elementos
5. Analiza TIPOGRAFÍA: fuentes y tamaños (en px)
6. Estilo de TABLA: bordes, fondos, padding

NO INCLUYAS: Nombres de empresas, productos, precios, ni ningún dato específico.
SOLO: Formato, colores, espacios, distribución, orden visual.

Responde SOLO el JSON, sin ```json ni explicaciones.
"""
            
            client = self._get_client()
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Parsear JSON
            analysis_text = self._clean_json_response(analysis_text)
            analysis = json.loads(analysis_text)
            
            # Agregar metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_model"] = "gpt-4-vision-preview"
            
            logger.info(f"✅ Template analysis completed: layout={analysis.get('layout_structure')}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing template with GPT-4 Vision: {e}")
            logger.warning("⚠️ Falling back to default template analysis")
            return self._fallback_template_analysis()
    
    def _encode_image(self, image_path: str) -> str:
        """Convierte imagen a base64 para enviar a GPT-4 Vision"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise
    
    async def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """
        Convierte primera página de PDF a imagen
        Requiere: pdf2image y poppler
        """
        try:
            from pdf2image import convert_from_path
            
            logger.info(f"Converting PDF to image: {pdf_path}")
            
            # Convertir solo primera página
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
            
            # Guardar primera página como imagen temporal
            image_path = pdf_path.replace('.pdf', '_page1.png')
            images[0].save(image_path, 'PNG')
            
            logger.info(f"PDF converted to image: {image_path}")
            return image_path
            
        except ImportError:
            logger.error("pdf2image not installed. Install with: pip install pdf2image")
            logger.error("Also requires poppler: brew install poppler (Mac) or apt-get install poppler-utils (Linux)")
            raise
        except Exception as e:
            logger.error(f"Error converting PDF to image: {e}")
            raise
    
    def _clean_json_response(self, text: str) -> str:
        """Limpia respuesta de IA para extraer JSON puro"""
        # Remover markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1)
        if text.startswith("```"):
            text = text.replace("```", "", 1)
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()
    
    def _fallback_logo_analysis(self, image_path: str) -> Dict:
        """
        Análisis básico de fallback si falla GPT-4 Vision
        Usa Pillow para extracción simple de colores
        """
        try:
            from PIL import Image
            from collections import Counter
            
            logger.info("Using Pillow for basic color extraction")
            
            img = Image.open(image_path).convert('RGB')
            img_resized = img.resize((50, 50))  # Reducir para rapidez
            pixels = list(img_resized.getdata())
            
            # Obtener 3 colores más comunes
            most_common = Counter(pixels).most_common(3)
            colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in most_common]
            
            return {
                "dominant_colors": colors,
                "primary_color": colors[0] if colors else "#2c5f7c",
                "secondary_color": colors[1] if len(colors) > 1 else "#ffffff",
                "has_transparency": img.mode == 'RGBA',
                "recommended_position": "top-left",
                "optimal_dimensions": {"width": 200, "height": 80},
                "logo_type": "unknown",
                "color_palette_description": "Análisis básico con Pillow",
                "design_notes": "Fallback analysis - GPT-4 Vision not available",
                "analyzed_at": datetime.now().isoformat(),
                "analysis_model": "fallback-pillow"
            }
        except Exception as e:
            logger.error(f"Error in fallback analysis: {e}")
            # Retornar valores por defecto
            return {
                "primary_color": "#2c5f7c",
                "secondary_color": "#ffffff",
                "dominant_colors": ["#2c5f7c", "#ffffff"],
                "has_transparency": False,
                "recommended_position": "top-left",
                "optimal_dimensions": {"width": 200, "height": 80},
                "analyzed_at": datetime.now().isoformat(),
                "analysis_model": "default"
            }
    
    def _fallback_template_analysis(self) -> Dict:
        """Análisis de fallback para template"""
        return {
            "layout_structure": "header-client-products-totals",
            "sections": [
                {
                    "name": "header",
                    "has_logo": True,
                    "logo_position": "top-left",
                    "elements": ["company_name", "document_title"]
                },
                {
                    "name": "client_info",
                    "fields": ["client_name", "company", "location"]
                },
                {
                    "name": "products_table",
                    "columns": ["description", "quantity", "unit_price", "total"]
                },
                {
                    "name": "totals",
                    "includes": ["subtotal", "total"]
                }
            ],
            "color_scheme": {
                "primary": "#2c5f7c",
                "secondary": "#ffffff",
                "backgrounds": ["#f0f0f0"],
                "borders": "#000000",
                "text": "#000000"
            },
            "table_style": {
                "has_borders": True,
                "border_width": "1px",
                "border_color": "#000000",
                "header_background": "#f0f0f0",
                "alternating_rows": False
            },
            "typography": {
                "font_family": "Arial, sans-serif",
                "company_name_size": "24px",
                "title_size": "18px",
                "body_size": "11px"
            },
            "design_style": "professional",
            "analyzed_at": datetime.now().isoformat(),
            "analysis_model": "default"
        }
