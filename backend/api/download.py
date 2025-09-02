"""
Download API Endpoints - Versión Final Simplificada
Conversión HTML a PDF con fidelidad visual exacta usando Playwright
"""
from flask import Blueprint, send_file, jsonify, request
import logging
import os
import tempfile
import re
from datetime import datetime

from backend.core.database import get_database_client

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
        
        # MÉTODO 2: HTML con instrucciones precisas
        logger.info("Fallback: generando HTML con instrucciones")
        return create_html_download_with_instructions(html_content, client_name, document_id)
        
    except Exception as e:
        logger.error(f"Error in PDF conversion: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error interno en conversión",
            "error": str(e)
        }), 500


def convert_with_playwright(html_content: str, client_name: str, document_id: str):
    """
    Conversión usando Playwright - Máxima fidelidad visual
    """
    from playwright.sync_api import sync_playwright
    
    # Optimizar HTML para PDF
    optimized_html = optimize_html_for_pdf(html_content)
    
    with sync_playwright() as p:
        # Lanzar navegador
        browser = p.chromium.launch(headless=True)
        
        try:
            page = browser.new_page()
            
            # Configurar viewport para renderizado consistente
            page.set_viewport_size({"width": 1200, "height": 1600})
            
            # Cargar HTML y esperar renderizado completo
            page.set_content(optimized_html, wait_until='networkidle')
            
            # Esperar un momento adicional para asegurar renderizado
            page.wait_for_timeout(1000)
            
            # Generar PDF con configuración optimizada
            pdf_bytes = page.pdf(
                format='A4',
                margin={
                    'top': '2cm',
                    'right': '2cm',
                    'bottom': '2cm',
                    'left': '2cm'
                },
                print_background=True,  # CRÍTICO para colores
                prefer_css_page_size=True,
                display_header_footer=False
            )
            
            return create_pdf_response(pdf_bytes, client_name, document_id)
            
        finally:
            browser.close()


def optimize_html_for_pdf(html_content: str) -> str:
    """
    Optimizar HTML para máxima fidelidad en PDF
    """
    # CSS para forzar colores y estilos en PDF
    pdf_optimization_css = """
    <style type="text/css">
        /* FORZAR COLORES EN PDF */
        *, *::before, *::after {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        
        /* ASEGURAR COLORES SABRA CORPORATION */
        .company-name {
            color: #2c5f7c !important;
            font-weight: bold !important;
        }
        
        .company-subtitle {
            color: #2c5f7c !important;
        }
        
        /* FORZAR FONDOS DE TABLA */
        .main-table th {
            background-color: #f0f0f0 !important;
        }
        
        .total-row {
            background-color: #f8f8f8 !important;
        }
        
        .final-total {
            background-color: #e0e0e0 !important;
        }
        
        .coordination-row td {
            border-top: 2px solid #000 !important;
        }
        
        /* ASEGURAR BORDES */
        .budget-section {
            border: 2px solid #000 !important;
        }
        
        .budget-table td {
            border: 1px solid #000 !important;
        }
        
        .main-table {
            border: 2px solid #000 !important;
        }
        
        .main-table th,
        .main-table td {
            border: 1px solid #000 !important;
        }
        
        /* EVITAR CORTES DE PÁGINA EN ELEMENTOS CRÍTICOS */
        .header {
            page-break-inside: avoid !important;
        }
        
        .main-table thead {
            page-break-inside: avoid !important;
        }
        
        /* ASEGURAR TIPOGRAFÍA */
        body {
            font-family: Arial, sans-serif !important;
        }
    </style>
    """
    
    # Insertar CSS optimizado
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', pdf_optimization_css + '\n</head>')
    elif '<head>' in html_content:
        html_content = html_content.replace('<head>', '<head>' + pdf_optimization_css)
    elif '<body>' in html_content:
        # Si no hay head, crearlo
        html_content = html_content.replace('<body>', f'<head>{pdf_optimization_css}</head><body>')
    
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
            ⚠️ SIN "Gráficos de fondo", los colores azules de Sabra Corporation y bordes NO aparecerán
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
    """Crear respuesta HTTP con PDF"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        safe_name = sanitize_filename(client_name)
        filename = f"propuesta-{safe_name}-{document_id}.pdf"
        
        logger.info(f"PDF generated successfully: {filename} ({len(pdf_bytes)} bytes)")
        
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    finally:
        # Cleanup en background
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


def create_html_response(html_content: str, client_name: str, document_id: str):
    """Crear respuesta HTTP con HTML"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        tmp_file_path = tmp_file.name
    
    try:
        safe_name = sanitize_filename(client_name)
        filename = f"propuesta-{safe_name}-{document_id}.html"
        
        logger.info(f"HTML with instructions generated: {filename}")
        
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/html'
        )
    finally:
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


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
