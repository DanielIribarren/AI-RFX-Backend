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
    
    async def analyze_template(self, template_path: str, user_id: str) -> Dict:
        """
        🎯 UN SOLO PASO: GPT-4 Vision lee template y genera HTML idéntico
        
        Args:
            template_path: Ruta al archivo del template (PDF o imagen)
            user_id: ID del usuario para guardar en BD
            
        Returns:
            Dict con metadata del análisis
        """
        logger.info(f"🎨 Generating HTML from template for user {user_id}: {template_path}")
        
        try:
            # Si es PDF, convertir primera página a imagen
            if template_path.lower().endswith('.pdf'):
                image_path = await self._convert_pdf_to_image(template_path)
            else:
                image_path = template_path
            
            image_data = self._encode_image(image_path)

            # Obtener logo del usuario en base64
            logo_base64 = await self._get_user_logo_base64(user_id)
            
            prompt = f"""
🎯 TAREA: Observa esta imagen de template de presupuesto y genera HTML IDÉNTICO

📋 INSTRUCCIONES:

1. **OBSERVA LA IMAGEN CUIDADOSAMENTE:**
   - Identifica colores exactos (formato hex #RRGGBB)
   - Mide proporciones de secciones
   - Detecta tamaños de fuente, espaciados, bordes
   - Observa estructura: ¿dónde está el logo original?

2. **ELEMENTOS A IDENTIFICAR:**
   - Header: Color de fondo, altura, posición del logo
   - Información del cliente: Formato (cajas, texto, etc.)
   - Tabla de productos: Columnas, colores, bordes, padding
   - Totales: Estilo, posición, formato
   - Comentarios: Si existe, su estilo

3. **LOGO DEL USUARIO (BASE64):**
   - DEBES reemplazar cualquier logo que veas en el template con esta variable: {{{{LOGO_BASE64}}}}
   - Usa exactamente: <img src="{{{{LOGO_BASE64}}}}" alt="Logo">
   - Mantén el tamaño y posición similares al logo original
   - NO uses URLs, solo la variable {{{{LOGO_BASE64}}}}

4. **GENERA HTML COMPLETO CON:**
   - <!DOCTYPE html>, <head>, <style>, <body>
   - Colores EXACTOS que identificaste
   - Espaciado y proporciones correctas
   - Variables dinámicas:
     {{{{CLIENT_NAME}}}}, {{{{REQUEST_DESCRIPTION}}}}, {{{{PRODUCT_ROWS}}}}, {{{{TOTAL_AMOUNT}}}}, {{{{CURRENT_DATE}}}}
   - Logo con variable {{{{LOGO_BASE64}}}} en la posición correcta

5. **REQUISITOS:**
   - Diseño para impresión (letter: 216mm x 279mm)
   - CSS inline o en <style>
   - print-color-adjust: exact
   - page-break-inside: avoid

⚠️ IMPORTANTE: Responde SOLO con HTML completo, sin explicaciones ni markdown
"""
            
            # Obtener cliente OpenAI
            client = self._get_client()
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
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
                max_tokens=4000,
                temperature=0.1
            )
            
            html_template = response.choices[0].message.content.strip()
            
            logger.info(f"📝 GPT-4 Response received - Length: {len(html_template)} characters")
            print(f"🔥 DEBUG: GPT-4 Response received - Length: {len(html_template)} characters")
            
            # Limpiar markdown si existe
            if html_template.startswith("```html"):
                html_template = html_template.replace("```html", "", 1)
                logger.info("🧹 Removed ```html wrapper")
                print("🔥 DEBUG: Removed ```html wrapper")
            if html_template.startswith("```"):
                html_template = html_template.replace("```", "", 1)
                logger.info("🧹 Removed ``` wrapper")
                print("🔥 DEBUG: Removed ``` wrapper")
            if html_template.endswith("```"):
                html_template = html_template.rsplit("```", 1)[0]
                logger.info("🧹 Removed trailing ```")
                print("🔥 DEBUG: Removed trailing ```")
            
            html_template = html_template.strip()
            
            # Reemplazar variable LOGO_BASE64 con el logo real
            html_template = html_template.replace("{{LOGO_BASE64}}", logo_base64)
            html_template = html_template.replace("{{{{LOGO_BASE64}}}}", logo_base64)  # Por si AI usa doble llave
            
            logger.info(f"✅ HTML cleaned - Final length: {len(html_template)} characters")
            logger.info(f"✅ Logo base64 injected - Logo size: {len(logo_base64)} chars")
            logger.info(f"✅ HTML starts with: {html_template[:200]}")
            print(f"🔥 DEBUG: HTML cleaned - Length: {len(html_template)}")
            print(f"🔥 DEBUG: Logo base64 size: {len(logo_base64)} chars")
            print(f"🔥 DEBUG: HTML starts with: {html_template[:200]}")
            print("🔥 DEBUG: FULL HTML BELOW:")
            print(html_template)
            print("🔥 DEBUG: END HTML")
            
            # Crear análisis simple con metadata
            analysis = {
                "template_analyzed": True,
                "html_generated": True,
                "analyzed_at": datetime.now().isoformat(),
                "analysis_model": "gpt-4o-vision-direct"
            }
            
            logger.info(f"💾 About to save to database - user_id: {user_id}")
            print(f"🔥 DEBUG: About to save HTML to database for user: {user_id}")
            
            # Guardar HTML en BD
            await self._save_to_database(user_id, analysis, html_template)
            
            logger.info(f"✅ HTML template generated and saved for user: {user_id}")
            print(f"🔥 DEBUG: HTML template generated and saved for user: {user_id}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing template: {e}")
            # Guardar error en BD
            await self._save_error_to_database(user_id, str(e))
            raise
    
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
        text = text.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1)
        if text.startswith("```"):
            text = text.replace("```", "", 1)
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()
    
    async def _get_user_logo_base64(self, user_id: str) -> str:
        """Obtiene el logo del usuario en formato base64"""
        try:
            from pathlib import Path
            
            # Buscar logo en directorio del usuario
            logo_dir = Path("backend/static/branding") / user_id
            
            # Buscar archivo de logo (cualquier extensión)
            logo_extensions = ['.png', '.jpg', '.jpeg', '.svg']
            logo_path = None
            
            for ext in logo_extensions:
                potential_path = logo_dir / f"logo{ext}"
                if potential_path.exists():
                    logo_path = potential_path
                    break
            
            if not logo_path:
                logger.warning(f"⚠️ No logo found for user: {user_id}")
                return ""  # Retornar vacío si no hay logo
            
            # Convertir SVG a PNG si es necesario
            if logo_path.suffix.lower() == '.svg':
                logo_path = Path(self._convert_svg_to_png(str(logo_path)))
            
            # Leer y convertir a base64
            with open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Detectar tipo MIME
            mime_type = "image/png"
            if logo_path.suffix.lower() in ['.jpg', '.jpeg']:
                mime_type = "image/jpeg"
            
            # Retornar data URI completa
            data_uri = f"data:{mime_type};base64,{logo_base64}"
            logger.info(f"✅ Logo converted to base64 - Size: {len(logo_base64)} chars")
            
            return data_uri
                
        except Exception as e:
            logger.error(f"❌ Error getting user logo base64: {e}")
            return ""  # Retornar vacío en caso de error
    
    async def _save_to_database(self, user_id: str, analysis: Dict, html_template: str):
        """Guarda análisis y HTML template en BD usando Supabase client"""
        try:
            from backend.core.database import get_database_client
            
            db = get_database_client()
            
            # Usar Supabase client directamente (como guardas productos)
            update_data = {
                "template_analysis": analysis,
                "html_template": html_template,
                "analysis_status": "completed",
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"💾 Saving to DB - user_id: {user_id}")
            logger.info(f"💾 HTML length: {len(html_template)} chars")
            
            result = db.client.table("company_branding_assets")\
                .update(update_data)\
                .eq("user_id", user_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Analysis and HTML saved successfully for user: {user_id}")
                logger.info(f"✅ Updated fields: {list(update_data.keys())}")
            else:
                logger.warning(f"⚠️ No rows updated for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to database: {e}", exc_info=True)
            raise
    
    async def _save_error_to_database(self, user_id: str, error: str):
        """Guarda error de análisis en BD usando Supabase client"""
        try:
            from backend.core.database import get_database_client
            
            db = get_database_client()
            
            # Usar Supabase client directamente
            error_data = {
                "analysis_status": "failed",
                "analysis_error": error,
                "updated_at": datetime.now().isoformat()
            }
            
            db.client.table("company_branding_assets")\
                .update(error_data)\
                .eq("user_id", user_id)\
                .execute()
            
            logger.info(f"💾 Error saved to database for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving error to database: {e}")
    
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
    
