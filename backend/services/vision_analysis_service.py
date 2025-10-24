"""
🔍 Vision Analysis Service - Análisis de imágenes con GPT-4o Vision
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
    Servicio para análisis de imágenes con GPT-4o Vision
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
🎯 MISIÓN CRÍTICA: Analiza este presupuesto y extrae ESPECIFICACIONES EXACTAS para replicarlo.

✅ MEJORA #6: ANÁLISIS ESPECÍFICO Y PRECISO (NO GENÉRICO)

OBJETIVO: Extraer colores EXACTOS, medidas PRECISAS y reglas ESPECÍFICAS que permitan replicar este documento fielmente.

🔍 PROCESO DE ANÁLISIS DETALLADO:

1. **COLORES EXACTOS** (extraer hexadecimales precisos):
   - Color primario del branding (bordes, acentos)
   - Color de fondo del header de tabla
   - Color de texto del header de tabla
   - Color de bordes de tabla
   - Colores de texto (primario, secundario)
   - ⚠️ NO uses colores genéricos - extrae los REALES de la imagen

2. **MEDIDAS ESPECÍFICAS** (en mm para PDF):
   - Altura del logo (debe estar entre 80-120px / 15-20mm)
   - Márgenes de página (top, bottom, left, right)
   - Espaciado entre secciones (margin-bottom)
   - Padding de celdas de tabla
   - Tamaños de fuente específicos (no "grande" o "pequeño")

3. **ESTRUCTURA LAYOUT** (orden exacto):
   - Identificar secciones en orden: header, client-info, products-table, totals, footer
   - Especificar qué va en cada sección
   - Proporciones: header 15%, contenido 70%, footer 15%

4. **TIPOGRAFÍA ESPECÍFICA**:
   - Familia de fuente detectada (Arial, Helvetica, etc.)
   - Tamaño base del cuerpo (en px o pt)
   - Tamaño de títulos/headings
   - Tamaño del nombre de empresa
   - Line-height específico

5. **REGLAS DE USO DE COLORES** (para el LLM):
   - Especificar DÓNDE usar cada color
   - Reglas de contraste: "Si fondo es X, texto debe ser Y"
   - Colores permitidos vs prohibidos

✅ FORMATO DE RESPUESTA ESPECÍFICO (JSON sin markdown):

{
  "color_scheme": {
    "primary": "#XXXXXX",  // Color primario EXACTO (bordes, acentos)
    "secondary": "#XXXXXX",  // Color secundario
    "backgrounds": ["#XXXXXX", "#XXXXXX"],  // Lista de fondos usados
    "text": "#XXXXXX",  // Color de texto principal
    "borders": "#XXXXXX"  // Color de bordes
  },
  "color_usage": {
    "header_border": "#XXXXXX",  // Dónde: borde inferior del header
    "header_background": "#XXXXXX",  // Dónde: fondo del header
    "table_header_bg": "#XXXXXX",  // Dónde: fondo del header de tabla
    "table_header_text": "#XXXXXX",  // Dónde: texto del header de tabla
    "table_border": "#XXXXXX",  // Dónde: bordes de celdas
    "text_primary": "#XXXXXX",  // Dónde: texto del cuerpo
    "accent": "#XXXXXX"  // Dónde: elementos destacados
  },
  "contrast_rules": {
    "light_backgrounds": ["#ffffff", "#f0f0f0"],  // Fondos claros detectados
    "dark_backgrounds": ["#0e2541", "#2c5f7c"],  // Fondos oscuros detectados
    "rule": "light_bg_use_dark_text, dark_bg_use_light_text"
  },
  "layout_structure": "header-client-products-totals-footer",  // Orden exacto de secciones
  "html_structure": {
    "order": ["header", "client", "products", "totals", "footer"],
    "section_spacing": "5mm",  // Espacio entre secciones
    "proportions": {
      "header": "15%",
      "content": "70%",
      "footer": "15%"
    }
  },
  "typography": {
    "font_family": "Arial, sans-serif",  // Familia detectada
    "base_size": "11px",  // Tamaño del cuerpo
    "heading_size": "18px",  // Tamaño de títulos
    "company_name_size": "24px",  // Tamaño nombre empresa
    "line_height": "1.5"  // Interlineado
  },
  "table_style": {
    "border_width": "1px",  // Ancho de bordes
    "border_color": "#000000",  // Color de bordes
    "header_background": "#f0f0f0",  // Fondo del header EXACTO
    "header_text_color": "#000000",  // Texto del header EXACTO
    "cell_padding": "10px",  // Padding de celdas
    "has_borders": true,
    "border_collapse": "collapse"
  },
  "table_css": {
    "border": "1px solid #000000",  // CSS completo para border
    "header_bg": "#f0f0f0",
    "header_text": "#000000",
    "row_padding": "10px",
    "cell_align": "left",
    "width": "100%"
  },
  "spacing_rules": {
    "section_margin": "5mm",  // Margen entre secciones
    "header_padding": "5mm 10mm",  // Padding del header
    "table_margin": "5mm 10mm",  // Margen de la tabla
    "cell_padding": "2mm",  // Padding de celdas
    "logo_height": "15mm",  // Altura del logo
    "logo_margin": "0 0 5mm 0"  // Margen del logo
  },
  "quality_checks": {
    "logo_min_height": "80px",  // Mínimo para logo
    "logo_max_height": "120px",  // Máximo para logo
    "min_section_spacing": "3mm",
    "required_sections": ["header", "client_info", "products_table", "totals"],
    "forbidden_elements": ["terms_and_conditions"]
  },
  "style": "professional",  // Estilo general detectado
  "template_version": "specific_analysis_v6.0"
}

🚨 INSTRUCCIONES CRÍTICAS PARA EL ANÁLISIS:

1. **SÉ ESPECÍFICO, NO GENÉRICO:**
   - ❌ MAL: "color azul" → ✅ BIEN: "#2c5f7c"
   - ❌ MAL: "logo grande" → ✅ BIEN: "15mm" o "100px"
   - ❌ MAL: "espaciado normal" → ✅ BIEN: "5mm" o "20px"

2. **EXTRAE COLORES REALES:**
   - Usa herramientas de color picker visual
   - NO inventes colores genéricos
   - Especifica DÓNDE se usa cada color

3. **MIDE PROPORCIONES:**
   - Calcula porcentajes de secciones
   - Mide espacios entre elementos
   - Detecta tamaños de fuente reales

4. **DEFINE REGLAS DE USO:**
   - No solo "qué colores hay"
   - Sino "DÓNDE y CUÁNDO usar cada color"
   - Reglas de contraste claras

5. **INCLUYE TODOS LOS CAMPOS DEL JSON:**
   - No omitas ningún campo del formato
   - Si no detectas algo, usa valores por defecto razonables
   - Completa TODOS los objetos: color_usage, table_css, spacing_rules, etc.

⚠️ CALIDAD OBJETIVO: 
El análisis debe ser TAN ESPECÍFICO que un LLM pueda generar HTML idéntico solo leyendo este JSON.

📋 RESPONDE SOLO EL JSON COMPLETO, sin markdown (```), sin explicaciones adicionales.
"""
            
            client = self._get_client()
            
            response = client.chat.completions.create(
                model="gpt-4o",
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
            
            # Restructurar para compatibilidad con sistema existente
            if "exact_replication_analysis" in analysis:
                # Nueva estructura - mantener análisis exacto y extraer campos compatibles
                exact_analysis = analysis["exact_replication_analysis"]
                
                # Extraer información compatible para el sistema existente
                layout_structure = "header-client-products-totals-footer"
                color_scheme = self._extract_color_scheme_from_exact_analysis(exact_analysis)
                typography = self._extract_typography_from_exact_analysis(exact_analysis)
                table_style = self._extract_table_style_from_exact_analysis(exact_analysis)
                
                # Estructura compatible manteniendo análisis exacto
                analysis.update({
                    "layout_structure": layout_structure,
                    "color_scheme": color_scheme,
                    "typography": typography,
                    "table_style": table_style,
                    "design_style": "exact_replica",
                    "exact_replication_data": exact_analysis  # Preservar análisis completo
                })
            
            # Agregar metadata
            analysis["analyzed_at"] = datetime.now().isoformat()
            analysis["analysis_model"] = "gpt-4o-exact-replica"
            
            logger.info(f"✅ Template analysis completed: layout={analysis.get('layout_structure')}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing template with GPT-4o Vision: {e}")
            logger.warning("⚠️ Falling back to default template analysis")
            return self._fallback_template_analysis()
    
    def _encode_image(self, image_path: str) -> str:
        """Convierte imagen a base64 para enviar a GPT-4o"""
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
    
    def _convert_svg_to_png(self, svg_path: str) -> str:
        """
        Convierte SVG a PNG para análisis
        Usa cairosvg si está disponible
        """
        try:
            import cairosvg
            
            png_path = svg_path.replace('.svg', '_converted.png')
            cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=800)
            
            logger.info(f"✅ SVG converted to PNG: {png_path}")
            return png_path
            
        except ImportError:
            logger.warning("cairosvg not installed. Attempting alternative conversion...")
            # Intentar con Pillow + svglib
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                
                drawing = svg2rlg(svg_path)
                png_path = svg_path.replace('.svg', '_converted.png')
                renderPM.drawToFile(drawing, png_path, fmt='PNG')
                
                logger.info(f"✅ SVG converted to PNG using svglib: {png_path}")
                return png_path
                
            except Exception as e:
                logger.error(f"Failed to convert SVG with alternative method: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error converting SVG to PNG: {e}")
            raise
    
    def _fallback_logo_analysis(self, image_path: str) -> Dict:
        """
        Análisis básico de fallback si falla GPT-4 Vision
        Usa Pillow para extracción simple de colores
        """
        try:
            from PIL import Image
            from collections import Counter
            
            logger.info("Using Pillow for basic color extraction")
            
            # Si es SVG, convertir primero a PNG
            if image_path.lower().endswith('.svg'):
                logger.info(f"Detected SVG file, converting to PNG: {image_path}")
                image_path = self._convert_svg_to_png(image_path)
            
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
    
    def _extract_color_scheme_from_exact_analysis(self, exact_analysis: Dict) -> Dict:
        """
        Extrae esquema de colores desde análisis exacto
        
        Args:
            exact_analysis: Análisis detallado de replicación exacta
            
        Returns:
            Dict con esquema de colores compatible
        """
        try:
            header = exact_analysis.get("header_section", {})
            table = exact_analysis.get("products_table", {})
            
            # Extraer colores de diferentes secciones
            primary_color = "#2c5f7c"  # Default
            secondary_color = "#ffffff"  # Default
            
            # Intentar extraer colores reales del análisis
            if "background_color" in header:
                bg_color = header["background_color"]
                if bg_color and bg_color.startswith("#"):
                    primary_color = bg_color
            
            if "header_background" in table:
                header_bg = table["header_background"]
                if header_bg and header_bg.startswith("#"):
                    secondary_color = header_bg
            
            return {
                "primary": primary_color,
                "secondary": secondary_color,
                "backgrounds": [table.get("header_background", "#f0f0f0")],
                "borders": table.get("border_style", {}).get("color", "#000000"),
                "text": table.get("header_text_color", "#000000")
            }
        except Exception as e:
            logger.warning(f"Error extracting color scheme: {e}")
            return {
                "primary": "#2c5f7c",
                "secondary": "#ffffff", 
                "backgrounds": ["#f0f0f0"],
                "borders": "#000000",
                "text": "#000000"
            }
    
    def _extract_typography_from_exact_analysis(self, exact_analysis: Dict) -> Dict:
        """
        Extrae tipografía desde análisis exacto
        
        Args:
            exact_analysis: Análisis detallado de replicación exacta
            
        Returns:
            Dict con tipografía compatible
        """
        try:
            header = exact_analysis.get("header_section", {})
            overall = exact_analysis.get("overall_layout", {})
            
            return {
                "font_family": overall.get("font_family", "Arial, sans-serif"),
                "company_name_size": self._extract_font_size(header.get("company_name_typography", "24px")),
                "title_size": self._extract_font_size(header.get("title_typography", "18px")),
                "body_size": overall.get("base_font_size", "11px"),
                "table_header_weight": "bold"
            }
        except Exception as e:
            logger.warning(f"Error extracting typography: {e}")
            return {
                "font_family": "Arial, sans-serif",
                "company_name_size": "24px",
                "title_size": "18px", 
                "body_size": "11px",
                "table_header_weight": "bold"
            }
    
    def _extract_table_style_from_exact_analysis(self, exact_analysis: Dict) -> Dict:
        """
        Extrae estilo de tabla desde análisis exacto
        
        Args:
            exact_analysis: Análisis detallado de replicación exacta
            
        Returns:
            Dict con estilo de tabla compatible
        """
        try:
            table = exact_analysis.get("products_table", {})
            
            return {
                "has_borders": True,
                "border_width": self._extract_border_width(table.get("border_style", "1px")),
                "border_color": table.get("border_style", {}).get("color", "#000000"),
                "header_background": table.get("header_background", "#f0f0f0"),
                "alternating_rows": table.get("alternating_rows", False),
                "cell_padding": table.get("cell_padding", "6px")
            }
        except Exception as e:
            logger.warning(f"Error extracting table style: {e}")
            return {
                "has_borders": True,
                "border_width": "1px",
                "border_color": "#000000",
                "header_background": "#f0f0f0",
                "alternating_rows": False,
                "cell_padding": "6px"
            }
    
    def _extract_font_size(self, typography_string: str) -> str:
        """
        Extrae tamaño de fuente de una cadena de tipografía
        
        Args:
            typography_string: String que contiene información de tipografía
            
        Returns:
            Tamaño de fuente en px
        """
        import re
        # Buscar patrón como "24px" o "size: 24px"
        size_match = re.search(r'(\d+)px', typography_string)
        if size_match:
            return f"{size_match.group(1)}px"
        return "12px"  # Default
    
    def _extract_border_width(self, border_string: str) -> str:
        """
        Extrae ancho de borde de una cadena de estilo de borde
        
        Args:
            border_string: String que contiene información de borde
            
        Returns:
            Ancho de borde
        """
        import re
        # Buscar patrón como "1px" o "width: 1px"
        width_match = re.search(r'(\d+)px', str(border_string))
        if width_match:
            return f"{width_match.group(1)}px"
        return "1px"  # Default
