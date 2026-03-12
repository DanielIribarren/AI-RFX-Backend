"""
Download API Endpoints - Versión Final Simplificada
Conversión HTML a PDF con fidelidad visual exacta usando Playwright
"""
from flask import Blueprint, send_file, jsonify, request, make_response
import logging
import os
import io
import tempfile
import re
import hashlib
from datetime import datetime

from backend.core.database import get_database_client
from backend.utils.retry_decorator import retry_on_failure
from backend.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

download_bp = Blueprint("download_api", __name__, url_prefix="/api/download")


@download_bp.route("/html-to-pdf", methods=["POST"])
def convert_html_to_pdf():
    """
    Endpoint principal para conversión HTML a PDF
    Prioridad: Playwright -> HTML con instrucciones
    """
    try:
        # Validar request
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type debe ser application/json"
            }), 400
        
        data = request.get_json()
        html_content = data.get('html_content', '')
        client_name = data.get('client_name', 'Cliente')
        document_id = data.get('document_id', 'documento')
        
        if not html_content or len(html_content.strip()) < 50:
            return jsonify({
                "status": "error",
                "message": "html_content es requerido y debe tener contenido válido"
            }), 400
        
        logger.info(f"Converting HTML to PDF - Client: {client_name}, Size: {len(html_content)} chars")
        
        # MÉTODO 1: Playwright (mejor fidelidad visual)
        try:
            return convert_with_playwright(html_content, client_name, document_id)
        except ImportError:
            logger.warning("Playwright no disponible")
        except Exception as e:
            logger.error(f"Playwright failed: {e}")
        
        # MÉTODO 2: WeasyPrint (buena fidelidad, no requiere browser)
        try:
            return convert_with_weasyprint(html_content, client_name, document_id)
        except ImportError:
            logger.warning("WeasyPrint no disponible")
        except Exception as e:
            logger.error(f"WeasyPrint failed: {e}")
        
        # MÉTODO 3: pdfkit/wkhtmltopdf
        try:
            return convert_with_pdfkit(html_content, client_name, document_id)
        except ImportError:
            logger.warning("pdfkit no disponible")
        except Exception as e:
            logger.error(f"pdfkit failed: {e}")
        
        # MÉTODO 4: HTML con instrucciones precisas (último recurso)
        logger.warning("⚠️ Todos los métodos PDF fallaron, generando HTML con instrucciones")
        return create_html_download_with_instructions(html_content, client_name, document_id)
        
    except Exception as e:
        logger.error(f"Error in PDF conversion: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error interno en conversión",
            "error": str(e)
        }), 500


def sanitize_html_for_chromium_pdf(html_content: str) -> str:
    """
    Elimina CSS que causa crashes en Chromium PDF engine (page.pdf()).
    Mantiene el estilo visual pero quita propiedades problemáticas.
    """
    problematic_css = [
        # Filters y effects (muy problemáticos con page.pdf)
        (r'filter:\s*[^;]+;', ''),
        (r'backdrop-filter:\s*[^;]+;', ''),
        (r'-webkit-backdrop-filter:\s*[^;]+;', ''),
        (r'mix-blend-mode:\s*[^;]+;', ''),
        
        # Masks y clips complejos
        (r'-webkit-mask:\s*[^;]+;', ''),
        (r'-webkit-mask-image:\s*[^;]+;', ''),
        (r'mask:\s*[^;]+;', ''),
        (r'clip-path:\s*polygon[^;]+;', ''),
        
        # Transforms 3D problemáticos
        (r'transform:\s*[^;]*perspective[^;]+;', ''),
        (r'transform:\s*[^;]*rotateX[^;]+;', ''),
        (r'transform:\s*[^;]*rotateY[^;]+;', ''),
        (r'transform:\s*[^;]*rotateZ[^;]+;', ''),
        (r'transform-style:\s*preserve-3d;', ''),
        
        # Will-change (no sirve en PDF)
        (r'will-change:\s*[^;]+;', ''),
        
        # Contenido generado problemático
        (r'content:\s*url\([^)]+\);', ''),
        
        # Animaciones y transiciones (no tienen sentido en PDF)
        (r'animation:\s*[^;]+;', ''),
        (r'animation-[^:]+:\s*[^;]+;', ''),
        (r'transition:\s*[^;]+;', ''),
        (r'transition-[^:]+:\s*[^;]+;', ''),
        
        # image-rendering no estándar
        (r'image-rendering:\s*-webkit-optimize-contrast[^;]*;', 'image-rendering: auto;'),
        
        # -webkit-print-color-adjust con !important en selectores universales
        (r'-webkit-print-color-adjust:\s*exact\s*!important\s*;', '-webkit-print-color-adjust: exact;'),
    ]
    
    sanitized = html_content
    
    for pattern, replacement in problematic_css:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    # Remover bloques universales (*) con -webkit-print-color-adjust (principal causa de crash)
    sanitized = re.sub(
        r'\*\s*(?:,\s*\*::before\s*,\s*\*::after\s*)?\{[^}]*-webkit-print-color-adjust[^}]*\}',
        '',
        sanitized
    )
    
    # Limpiar inline scripts (no sirven en PDF)
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
    
    # Limpiar event handlers inline
    sanitized = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
    
    logger.info("🧹 HTML sanitized for Chromium PDF engine")
    return sanitized


def sanitize_html_for_playwright_stability(html_content: str) -> str:
    """
    Sanitización agresiva para casos donde set_content crashea.
    Reduce features de HTML/CSS que suelen romper el renderer.
    """
    sanitized = html_content

    # Evitar dependencias externas e imports CSS dinámicos
    sanitized = re.sub(r'<link[^>]+rel=["\']?stylesheet["\']?[^>]*>', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'@import\s+url\([^)]+\)\s*;?', '', sanitized, flags=re.IGNORECASE)

    # Remover tags multimedia/embebidos problemáticos para PDF
    sanitized = re.sub(r'<(iframe|embed|object|video|audio|canvas)[^>]*>.*?</\1>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'<(iframe|embed|object|video|audio|canvas)[^>]*/?>', '', sanitized, flags=re.IGNORECASE)

    # SVG complejos pueden tumbar el renderer en algunos hosts
    sanitized = re.sub(r'<svg[^>]*>.*?</svg>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)

    # Reducir payload de data URIs extremadamente largos
    sanitized = re.sub(r'data:[^"\')\s]{5000,}', 'data:,', sanitized, flags=re.IGNORECASE)

    # Quitar scripts inline y handlers
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
    sanitized = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)

    logger.warning("🛟 Applied aggressive HTML stabilization for Playwright")
    return sanitized


def render_html_to_pdf_bytes(page, html_content: str) -> bytes:
    """
    Renderiza HTML y devuelve bytes PDF.
    Usa domcontentloaded para evitar crashes asociados a networkidle.
    """
    page.set_default_timeout(60000)
    page.set_viewport_size({"width": 1200, "height": 1600})

    logger.info("🌐 Loading HTML content into browser...")
    page.set_content(html_content, wait_until='domcontentloaded', timeout=60000)

    # Espera de red no bloqueante: si falla, seguimos.
    try:
        page.wait_for_load_state('networkidle', timeout=5000)
    except Exception:
        logger.info("ℹ️ networkidle not reached, continuing with current render state")

    logger.info("🖼️ Waiting for pending images...")
    try:
        page.evaluate("""
            () => Promise.all(
                Array.from(document.images)
                    .filter(img => !img.complete)
                    .map(img => new Promise(resolve => {
                        img.onload = img.onerror = resolve;
                    }))
            )
        """)
    except Exception as img_error:
        logger.warning(f"⚠️ Image loading check failed (continuing): {img_error}")

    page.wait_for_timeout(700)

    logger.info("✅ Generating PDF...")
    return page.pdf(
        format='A4',
        margin={
            'top': '2cm',
            'right': '2cm',
            'bottom': '2cm',
            'left': '2cm'
        },
        print_background=True,
        prefer_css_page_size=True,
        display_header_footer=False
    )


def persist_html_crash_snapshot(html_content: str, stage: str) -> None:
    """
    Guarda snapshot de HTML para análisis forense cuando Playwright crashea.
    """
    try:
        digest = hashlib.sha256(html_content.encode("utf-8", errors="ignore")).hexdigest()[:12]
        filename = f"/tmp/rfx_pdf_crash_{stage}_{digest}.html"
        with open(filename, "w", encoding="utf-8") as snapshot:
            snapshot.write(html_content)
        logger.warning(f"🧪 Crash snapshot saved: {filename} (len={len(html_content)})")
    except Exception as snapshot_error:
        logger.warning(f"⚠️ Could not persist crash snapshot: {snapshot_error}")


def is_renderer_crash_error(error: Exception) -> bool:
    """Detecta crashes del renderer Chromium en distintos puntos del pipeline."""
    message = str(error).lower()
    crash_tokens = [
        "target crashed",
        "page crashed",
        "renderer",
        "crash"
    ]
    return any(token in message for token in crash_tokens)


@retry_on_failure(max_retries=2, initial_delay=2.0, backoff_factor=2.0)
def convert_with_playwright(html_content: str, client_name: str, document_id: str):
    """
    Conversión usando Playwright - Máxima fidelidad visual
    Soporta imágenes base64 embebidas
    Incluye retry automático para fallos transitorios
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ExternalServiceError("Playwright", "Playwright not installed", original_error=e)
    
    # PASO 1: Limpiar CSS problemático ANTES de optimizar
    sanitized_html = sanitize_html_for_chromium_pdf(html_content)
    
    # PASO 2: Optimizar HTML para PDF
    optimized_html = optimize_html_for_pdf(sanitized_html)
    
    with sync_playwright() as p:
        browser = launch_chromium_for_pdf(p)
        
        try:
            page = browser.new_page()
            try:
                pdf_bytes = render_html_to_pdf_bytes(page, optimized_html)
            except Exception as render_error:
                # Activar safe mode para cualquier crash del renderer (set_content/evaluate/pdf)
                if not is_renderer_crash_error(render_error):
                    raise

                persist_html_crash_snapshot(optimized_html, "optimized")
                logger.warning(f"⚠️ Playwright page crashed with optimized HTML, retrying safe mode: {render_error}")

                # Reintento local sin salir de la función: HTML más conservador
                try:
                    page.close()
                except Exception:
                    pass

                page = browser.new_page()
                safe_html = optimize_html_for_pdf(sanitize_html_for_playwright_stability(sanitized_html))
                try:
                    pdf_bytes = render_html_to_pdf_bytes(page, safe_html)
                except Exception as safe_error:
                    if is_renderer_crash_error(safe_error):
                        persist_html_crash_snapshot(safe_html, "safe")
                    raise

            logger.info(f"✅ PDF generated successfully - Size: {len(pdf_bytes)} bytes")
            return create_pdf_response(pdf_bytes, client_name, document_id)

        except Exception as e:
            logger.error(f"❌ Error during PDF generation: {e}")
            raise
        finally:
            try:
                browser.close()
                logger.info("🔒 Browser closed successfully")
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing browser (non-critical): {close_error}")


def launch_chromium_for_pdf(playwright_instance):
    """
    Lanza Chromium para generación PDF.
    Prioriza headless moderno y usa fallback a old headless para compatibilidad.
    """
    common_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-dev-shm-usage',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
    ]

    launch_configs = [
        {
            "label": "modern-headless",
            "kwargs": {
                "headless": True,
                "args": common_args
            }
        },
        {
            "label": "legacy-headless",
            "kwargs": {
                "headless": True,
                "args": common_args + ['--headless=old']
            }
        }
    ]

    last_error = None
    for config in launch_configs:
        try:
            logger.info(f"🚀 Launching Chromium with {config['label']}")
            return playwright_instance.chromium.launch(**config["kwargs"])
        except Exception as launch_error:
            last_error = launch_error
            logger.warning(f"⚠️ Chromium launch failed ({config['label']}): {launch_error}")

    raise last_error


def convert_with_weasyprint(html_content: str, client_name: str, document_id: str):
    """
    Conversión usando WeasyPrint - Buena fidelidad sin necesidad de browser
    """
    try:
        from weasyprint import HTML as WeasyHTML
    except ImportError as e:
        raise ImportError("WeasyPrint not installed") from e
    
    optimized_html = optimize_html_for_pdf(html_content)
    
    logger.info("📄 Converting HTML to PDF with WeasyPrint...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        WeasyHTML(string=optimized_html).write_pdf(tmp_path)
        
        with open(tmp_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"✅ WeasyPrint PDF generated - Size: {len(pdf_bytes)} bytes")
        return create_pdf_response(pdf_bytes, client_name, document_id)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def convert_with_pdfkit(html_content: str, client_name: str, document_id: str):
    """
    Conversión usando pdfkit (requiere wkhtmltopdf instalado en el sistema)
    """
    try:
        import pdfkit
    except ImportError as e:
        raise ImportError("pdfkit not installed") from e
    
    optimized_html = optimize_html_for_pdf(html_content)
    
    logger.info("📄 Converting HTML to PDF with pdfkit...")
    
    options = {
        'page-size': 'A4',
        'margin-top': '20mm',
        'margin-right': '20mm',
        'margin-bottom': '20mm',
        'margin-left': '20mm',
        'encoding': 'UTF-8',
        'print-media-type': '',
        'no-outline': None,
        'enable-local-file-access': None
    }
    
    try:
        pdf_bytes = pdfkit.from_string(optimized_html, False, options=options)
        logger.info(f"✅ pdfkit PDF generated - Size: {len(pdf_bytes)} bytes")
        return create_pdf_response(pdf_bytes, client_name, document_id)
    except OSError as e:
        if 'wkhtmltopdf' in str(e).lower():
            raise ImportError("wkhtmltopdf not installed on system") from e
        raise


def optimize_html_for_pdf(html_content: str) -> str:
    """
    Optimizar HTML para máxima fidelidad en PDF.

    Hace dos cosas:
    1. Sanitiza propiedades CSS que causan crashes en Chromium page.pdf().
    2. Inyecta un bloque CSS normalizador de layout de tablas que actúa como
       safety net determinístico: independientemente del HTML que genere el LLM,
       garantiza que las tablas tengan bordes completos (incluyendo el borde
       derecho), border-collapse correcto y centrado consistente.

    Por qué esto es necesario:
    - El LLM puede generar `width: calc(100% - 20mm)` con `margin: 5mm 10mm`,
      lo que en el motor PDF de Chromium recorta el área de contenido y hace
      que el borde derecho de la última columna quede fuera del clip de la tabla.
    - Forzar `width: 100%` con `box-sizing: border-box` y dejar que el `@page`
      margin controle el espacio resuelve ambos problemas (borde + centrado).
    - `border-collapse: collapse` es obligatorio; sin él, `border: 1pt solid`
      en celdas individuales produce doble borde o borde faltante en el edge.

    NO usar selectores universales (*) con propiedades -webkit- pesadas
    (causa 'Target crashed' en Chromium).
    """
    pdf_normalization_css = """
    <style type="text/css">
        /* ── PAGE SETUP ─────────────────────────────────────────────────────── */
        @page {
            size: A4;
            margin: 2cm;
        }

        /* ── BODY: reset LLM-generated fixed dimensions + color preservation ───
           The LLM often generates body { width: 216mm; height: 279mm; padding: ... }
           which overflows the @page content area and clips the right side.
           Page geometry is controlled by @page, NOT body width/height.
        ──────────────────────────────────────────────────────────────────────── */
        body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            width: auto !important;
            max-width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* ── TABLE LAYOUT NORMALIZATION (safety net) ─────────────────────────
           FIX: missing right border + centering issues.
           width:100% + box-sizing:border-box ensures the table occupies the
           full content area defined by @page margin, so the rightmost border
           is always rendered inside the printable area.
           Explicit border-collapse prevents double/missing edge borders.
           margin:0 auto centers in the rare case a table has an explicit width.
        ────────────────────────────────────────────────────────────────────── */
        table {
            width: 100% !important;
            box-sizing: border-box !important;
            border-collapse: collapse !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
            table-layout: auto;
        }

        /* Ensure every cell border is visible on all four sides */
        th, td {
            box-sizing: border-box;
        }

        /* ── PAGINATION ──────────────────────────────────────────────────────── */
        thead {
            display: table-header-group;
        }

        tr {
            page-break-inside: avoid;
        }

        table {
            page-break-inside: auto;
        }

        /* ── IMAGES ──────────────────────────────────────────────────────────── */
        img {
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }
    </style>
    """

    # ── SANITIZE: remove CSS that crashes Chromium page.pdf() ────────────────

    # 1. image-rendering: -webkit-optimize-contrast (non-standard, causes crash)
    html_content = re.sub(
        r'image-rendering:\s*-webkit-optimize-contrast[^;]*;',
        'image-rendering: auto;',
        html_content
    )

    # 2. Universal (*) selectors with -webkit-print-color-adjust — main crash cause
    html_content = re.sub(
        r'\*\s*(?:,\s*\*::before\s*,\s*\*::after\s*)?\{[^}]*-webkit-print-color-adjust[^}]*\}',
        '',
        html_content
    )

    # 3. Normalize -webkit-print-color-adjust: exact !important to avoid issues
    html_content = re.sub(
        r'-webkit-print-color-adjust:\s*exact\s*!important\s*;',
        '-webkit-print-color-adjust: exact;',
        html_content
    )

    # 4. Replace calc()-based widths with 100% (unreliable in print media).
    #    Pattern is self-contained: calc(...) — no [^;]* needed outside the parens.
    #    Matches: width: calc(100% - 20mm), width: calc(100% - 2cm), etc.
    html_content = re.sub(
        r'(width\s*:\s*)calc\([^)]*\)',
        r'\1100%',
        html_content,
        flags=re.IGNORECASE
    )

    # 5. Strip fixed dimension body properties that overflow the page content area.
    #    The LLM often generates: body { width: 216mm; height: 279mm; padding: 0 10mm; }
    #    Page geometry is controlled by @page, NOT body width/height/padding.
    #
    #    Strategy: extract the body {} block, sanitize it, put it back.
    #    This is safer than regex-on-whole-file for multiline blocks.
    def _sanitize_body_block(match):
        block = match.group(0)
        # Remove width with absolute units (mm, cm, in, px, pt)
        block = re.sub(r'\bwidth\s*:\s*[\d.]+(?:mm|cm|in|px|pt)\s*;', '', block, flags=re.IGNORECASE)
        # Remove height with absolute units
        block = re.sub(r'\bheight\s*:\s*[\d.]+(?:mm|cm|in|px|pt)\s*;', '', block, flags=re.IGNORECASE)
        # Remove padding with any mm/cm/pt values (e.g. "0 10mm", "5mm 10mm", "10mm")
        block = re.sub(r'\bpadding\s*:[^;]*\d+(?:mm|cm|in|pt)[^;]*;', '', block, flags=re.IGNORECASE)
        return block

    html_content = re.sub(
        r'body\s*\{[^}]*\}',
        _sanitize_body_block,
        html_content,
        flags=re.IGNORECASE
    )

    # 7. Remove explicit mm margins on <table> elements (inline or stylesheet).
    #    Matches: margin: 5mm 10mm, margin-left: 10mm, margin: 0 10mm, etc.
    html_content = re.sub(
        r'(<table[^>]*style\s*=\s*["\'][^"\']*?)margin(?:-(?:left|right|top|bottom))?\s*:\s*[\d.]+(?:mm|cm|in|pt)[^;]*;',
        r'\1margin: 0;',
        html_content,
        flags=re.IGNORECASE
    )

    # ── INJECT normalization CSS (always last, highest specificity via !important)
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', pdf_normalization_css + '\n</head>')
    elif '<head>' in html_content:
        html_content = html_content.replace('<head>', '<head>' + pdf_normalization_css)
    elif '<body>' in html_content:
        html_content = html_content.replace('<body>', f'<head>{pdf_normalization_css}</head><body>')

    logger.info("✅ HTML optimized for PDF: table layout normalized, crash-prone CSS sanitized")
    return html_content


def create_html_download_with_instructions(html_content: str, client_name: str, document_id: str):
    """
    Crear HTML con instrucciones precisas para conversión manual
    """
    optimized_html = optimize_html_for_pdf(html_content)
    
    # Extraer el contenido del body si existe
    body_content = optimized_html
    if '<body>' in optimized_html and '</body>' in optimized_html:
        start = optimized_html.find('<body>') + 6
        end = optimized_html.find('</body>')
        body_content = optimized_html[start:end]
    
    instructions_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta {client_name}</title>
    <style>
        /* Instrucciones (se ocultan al imprimir) */
        .pdf-instructions {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            text-align: center;
            font-family: Arial, sans-serif;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .pdf-instructions h2 {{
            margin: 0 0 20px 0;
            font-size: 24px;
        }}
        
        .instruction-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .instruction-step {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .step-number {{
            background: #fff;
            color: #667eea;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .warning-box {{
            background: #ff6b6b;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-weight: bold;
        }}
        
        .success-box {{
            background: #51cf66;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        
        @media print {{
            .pdf-instructions {{
                display: none !important;
            }}
        }}
        
        /* CSS del documento original */
        @page {{
            margin: 2cm;
            size: A4;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.3;
            color: #000;
            font-size: 11px;
        }}
        
        /* Forzar colores para PDF */
        *, *::before, *::after {{
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        
        .company-name {{
            font-size: 36px;
            font-weight: bold;
            color: #2c5f7c !important;
            margin-bottom: 2px;
            letter-spacing: -1px;
        }}
        
        .company-subtitle {{
            font-size: 14px;
            color: #2c5f7c !important;
            margin-bottom: 5px;
            font-weight: normal;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 25px;
            padding-bottom: 15px;
        }}
        
        .company-section {{
            flex: 1;
        }}
        
        .company-address {{
            font-size: 10px;
            color: #000;
            line-height: 1.2;
        }}
        
        .budget-section {{
            border: 2px solid #000 !important;
            padding: 10px;
            min-width: 180px;
            text-align: center;
        }}
        
        .budget-title {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        
        .budget-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .budget-table td {{
            border: 1px solid #000 !important;
            padding: 4px 6px;
            font-size: 11px;
        }}
        
        .budget-table .label {{
            text-align: left;
            font-weight: normal;
        }}
        
        .budget-table .value {{
            text-align: right;
            font-weight: bold;
        }}
        
        .client-section {{
            margin: 20px 0;
            font-size: 11px;
        }}
        
        .client-name {{
            font-weight: bold;
            margin-bottom: 3px;
        }}
        
        .process-info {{
            font-weight: bold;
            margin-bottom: 15px;
            text-decoration: underline;
        }}
        
        .main-table {{
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000 !important;
            margin: 10px 0;
        }}
        
        .main-table th {{
            background-color: #f0f0f0 !important;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000 !important;
            font-size: 11px;
        }}
        
        .main-table td {{
            padding: 4px 6px;
            border: 1px solid #000 !important;
            font-size: 10px;
            vertical-align: middle;
        }}
        
        .coordination-row {{
            border-top: 2px solid #000 !important;
        }}
        
        .coordination-row td {{
            padding: 6px;
            font-weight: bold;
        }}
        
        .total-row {{
            background-color: #f8f8f8 !important;
            font-weight: bold;
        }}
        
        .total-row td {{
            padding: 6px;
            font-size: 11px;
        }}
        
        .final-total {{
            background-color: #e0e0e0 !important;
            font-weight: bold;
        }}
        
        .final-total td {{
            padding: 8px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="pdf-instructions">
        <h2>🎯 CONVERSIÓN A PDF PERFECTA</h2>
        <p>Cliente: <strong>{client_name}</strong> | ID: {document_id}</p>
        
        <div class="instruction-grid">
            <div class="instruction-step">
                <span class="step-number">1</span>
                <strong>Abrir impresión:</strong><br>
                Ctrl+P (Win) o Cmd+P (Mac)
            </div>
            
            <div class="instruction-step">
                <span class="step-number">2</span>
                <strong>Destino:</strong><br>
                "Guardar como PDF"
            </div>
            
            <div class="instruction-step">
                <span class="step-number">3</span>
                <strong>CRÍTICO:</strong><br>
                Activar "Gráficos de fondo"
            </div>
            
            <div class="instruction-step">
                <span class="step-number">4</span>
                <strong>Márgenes:</strong><br>
                "Predeterminados" o "Mínimos"
            </div>
        </div>
        
        <div class="warning-box">
            ⚠️ SIN "Gráficos de fondo", los colores y bordes NO aparecerán en el PDF
        </div>
        
        <div class="success-box">
            ✅ Con esta configuración, el PDF se verá EXACTAMENTE igual al HTML
        </div>
    </div>
    
    {body_content}
    
    <div style="margin-top: 40px; text-align: center; color: #666; font-size: 10px; border-top: 1px solid #ddd; padding-top: 20px;">
        <p>Propuesta generada automáticamente | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p>Cliente: {client_name} | ID: {document_id}</p>
    </div>
</body>
</html>"""
    
    return create_html_response(instructions_html, client_name, document_id)


def create_pdf_response(pdf_bytes: bytes, client_name: str, document_id: str):
    """Crear respuesta HTTP con PDF usando BytesIO (sin archivo temporal que cause race condition)"""
    safe_name = sanitize_filename(client_name)
    filename = f"propuesta-{safe_name}-{document_id}.pdf"
    
    logger.info(f"PDF generated successfully: {filename} ({len(pdf_bytes)} bytes)")
    
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


def create_html_response(html_content: str, client_name: str, document_id: str):
    """Crear respuesta HTTP con HTML"""
    safe_name = sanitize_filename(client_name)
    filename = f"propuesta-{safe_name}-{document_id}.html"
    html_bytes = html_content.encode('utf-8')

    logger.info(f"HTML with instructions generated: {filename}")

    return send_file(
        io.BytesIO(html_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype='text/html'
    )


def sanitize_filename(filename: str) -> str:
    """Limpiar nombre de archivo para ser safe"""
    # Remover caracteres problemáticos
    safe_name = re.sub(r'[^\w\s-]', '', filename).strip()
    # Reemplazar espacios con guiones
    safe_name = re.sub(r'\s+', '-', safe_name)
    # Limitar longitud
    return safe_name[:50]


# ========================================
# ENDPOINTS PARA DOCUMENTOS EXISTENTES
# ========================================

@download_bp.route("/<document_id>", methods=["GET"])
def download_document(document_id: str):
    """
    Descargar documento existente de la base de datos
    """
    try:
        logger.info(f"Download request for document_id: {document_id}")
        
        # Obtener documento de la base de datos
        db_client = get_database_client()
        document_data = db_client.get_document_by_id(document_id)
        
        if not document_data:
            return jsonify({
                "status": "error",
                "message": "Document not found",
                "document_id": document_id
            }), 404
        
        # Determinar formato de salida
        output_format = request.args.get('format', 'pdf').lower()
        
        if output_format == 'pdf':
            return download_as_pdf(document_data, document_id)
        elif output_format == 'html':
            return download_as_html(document_data, document_id)
        else:
            return jsonify({
                "status": "error",
                "message": f"Unsupported format: {output_format}",
                "supported": ["pdf", "html"]
            }), 400
                
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to download document",
            "error": str(e)
        }), 500


def download_as_pdf(document_data: dict, document_id: str):
    """Generar PDF desde documento de base de datos"""
    try:
        # Extraer contenido HTML
        html_content = get_html_content_from_document(document_data)
        
        if not html_content:
            return jsonify({
                "status": "error",
                "message": "No HTML content found in document"
            }), 400
        
        client_name = document_data.get('client_name', 'Cliente')
        
        # Usar el mismo método que el endpoint principal
        try:
            return convert_with_playwright(html_content, client_name, document_id)
        except Exception:
            return create_html_download_with_instructions(html_content, client_name, document_id)
            
    except Exception as e:
        logger.error(f"Error generating PDF for document {document_id}: {e}")
        raise


def download_as_html(document_data: dict, document_id: str):
    """Descargar como HTML"""
    try:
        html_content = get_html_content_from_document(document_data)
        
        if not html_content:
            return jsonify({
                "status": "error",
                "message": "No HTML content found in document"
            }), 400
        
        client_name = document_data.get('client_name', 'Cliente')
        optimized_html = optimize_html_for_pdf(html_content)
        
        return create_html_response(optimized_html, client_name, document_id)
        
    except Exception as e:
        logger.error(f"Error generating HTML for document {document_id}: {e}")
        raise


def get_html_content_from_document(document_data: dict) -> str:
    """Extraer contenido HTML de documento de base de datos"""
    # Intentar diferentes campos (v2.0 y legacy)
    html_fields = ['content_html', 'contenido_html', 'html_content']
    
    for field in html_fields:
        content = document_data.get(field)
        if content and len(str(content).strip()) > 50:
            return str(content).strip()
    
    logger.warning(f"No valid HTML content found. Available fields: {list(document_data.keys())}")
    return ""


# ========================================
# ENDPOINT DE DIAGNÓSTICO
# ========================================

@download_bp.route("/test-capabilities", methods=["GET"])
def test_capabilities():
    """Verificar capacidades del sistema"""
    capabilities = {
        "playwright": False,
        "system_info": {},
        "errors": []
    }
    
    # Test Playwright
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<h1>Test</h1>")
            pdf = page.pdf(format='A4')
            browser.close()
            
        capabilities["playwright"] = True
        capabilities["system_info"]["pdf_size_test"] = f"{len(pdf)} bytes"
        
    except ImportError:
        capabilities["errors"].append("Playwright not installed: pip install playwright")
    except Exception as e:
        capabilities["errors"].append(f"Playwright error: {str(e)}")
    
    # Recomendación
    if capabilities["playwright"]:
        recommendation = "✅ Sistema listo para conversión PDF con fidelidad exacta"
        install_commands = []
    else:
        recommendation = "⚠️ Instalar Playwright para conversión PDF automática"
        install_commands = [
            "pip install playwright",
            "playwright install chromium"
        ]
    
    return jsonify({
        "status": "success",
        "capabilities": capabilities,
        "recommendation": recommendation,
        "install_commands": install_commands,
        "note": "Sin Playwright, se genera HTML con instrucciones de conversión manual"
    })
