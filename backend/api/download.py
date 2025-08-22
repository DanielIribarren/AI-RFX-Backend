"""
📥 Download API Endpoints - Versión Simplificada para Descarga Directa de HTML a PDF
Maneja la conversión de HTML del frontend directamente a PDF con múltiples métodos de fallback
"""
from flask import Blueprint, send_file, jsonify, request
from werkzeug.exceptions import NotFound
import logging
import os
import tempfile
from io import BytesIO
import markdown
from typing import Optional

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

download_bp = Blueprint("download_api", __name__, url_prefix="/api/download")


@download_bp.route("/<document_id>", methods=["GET"])
def download_document(document_id: str):
    """
    📄 Descargar documento generado como PDF
    """
    try:
        logger.info(f"📥 Download request for document_id: {document_id}")
        logger.info(f"🔍 Request args: {dict(request.args)}")
        
        # Get document from database
        db_client = get_database_client()
        logger.info(f"🔗 Database client obtained successfully")
        
        document_data = db_client.get_document_by_id(document_id)
        logger.info(f"📄 Document query result: {document_data is not None}")
        
        if not document_data:
            logger.warning(f"❌ Document {document_id} not found in database")
            return jsonify({
                "status": "error",
                "message": "Document not found",
                "error": f"No document found with ID: {document_id}"
            }), 404
        
        # Validate document_data is a dictionary
        if not isinstance(document_data, dict):
            logger.error(f"❌ Document data is not a dictionary: {type(document_data)}")
            return jsonify({
                "status": "error",
                "message": "Invalid document data format",
                "error": f"Expected dict, got {type(document_data)}"
            }), 500
        
        # DEBUG: Log document structure to understand what keys are available
        logger.info(f"🔍 Document {document_id} keys: {list(document_data.keys())}")
        logger.info(f"📊 Document data type: {type(document_data)}")
        
        # Check all possible content fields
        content_found = False
        for field in ['content_html', 'content_markdown', 'contenido_html', 'contenido_markdown']:
            if field in document_data and document_data[field]:
                content_length = len(str(document_data[field]))
                logger.info(f"✅ Found {field}: {content_length} characters")
                content_found = True
            else:
                logger.debug(f"❌ Missing or empty {field}")
        
        if not content_found:
            logger.error(f"❌ No content found in document {document_id}")
            # Still proceed but log the issue
            logger.info(f"📄 Document data preview: {str(document_data)[:200]}...")
        
        # Determine output format (default to PDF)
        output_format = request.args.get('format', 'pdf').lower()
        
        if output_format == 'pdf':
            return _download_as_pdf(document_data, document_id)
        elif output_format == 'html':
            return _download_as_html(document_data, document_id)
        elif output_format == 'markdown':
            return _download_as_markdown(document_data, document_id)
        else:
            return jsonify({
                "status": "error",
                "message": f"Unsupported format: {output_format}",
                "error": "Supported formats: pdf, html, markdown"
            }), 400
                
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"❌ Error downloading document {document_id}: {e}")
        logger.error(f"🔍 Full traceback: {error_traceback}")
        
        # Determine specific error type
        if "get_document_by_id" in str(e):
            return jsonify({
                "status": "error",
                "message": "Database error retrieving document",
                "error": str(e)
            }), 500
        elif "database" in str(e).lower():
            return jsonify({
                "status": "error",
                "message": "Database connection failed",
                "error": str(e)
            }), 500
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to download document",
                "error": str(e)
            }), 500


@download_bp.route("/test-pdf-capabilities", methods=["GET"])
def test_pdf_capabilities():
    """
    🧪 Test endpoint para verificar qué librerías de PDF están disponibles
    """
    capabilities = {
        "weasyprint": False,
        "puppeteer": False,
        "reportlab": False,
        "beautifulsoup4": False,
        "errors": []
    }
    
    # Test WeasyPrint
    try:
        import weasyprint
        from weasyprint import HTML, CSS
        capabilities["weasyprint"] = True
        logger.info("✅ WeasyPrint is available")
    except ImportError as e:
        capabilities["errors"].append(f"WeasyPrint import error: {e}")
        logger.warning(f"❌ WeasyPrint not available: {e}")
    except OSError as e:
        # Handle libpango and other system library errors
        capabilities["errors"].append(f"WeasyPrint system dependencies missing: {e}")
        logger.warning(f"❌ WeasyPrint system dependencies missing: {e}")
    except Exception as e:
        capabilities["errors"].append(f"WeasyPrint unexpected error: {e}")
        logger.warning(f"❌ WeasyPrint unexpected error: {e}")
    
    # Test Puppeteer
    try:
        from pyppeteer import launch
        capabilities["puppeteer"] = True
        logger.info("✅ Puppeteer is available")
    except ImportError as e:
        capabilities["errors"].append(f"Puppeteer not available: {e}")
        logger.warning(f"❌ Puppeteer not available: {e}")
    
    # Test ReportLab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
        capabilities["reportlab"] = True
        logger.info("✅ ReportLab is available")
    except ImportError as e:
        capabilities["errors"].append(f"ReportLab not available: {e}")
        logger.warning(f"❌ ReportLab not available: {e}")
    
    # Test BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        capabilities["beautifulsoup4"] = True
        logger.info("✅ BeautifulSoup4 is available")
    except ImportError as e:
        capabilities["errors"].append(f"BeautifulSoup4 not available: {e}")
        logger.warning(f"❌ BeautifulSoup4 not available: {e}")
    
    # Recomendación
    if capabilities["weasyprint"]:
        recommendation = "WeasyPrint (recomendado)"
    elif capabilities["puppeteer"]:
        recommendation = "Puppeteer (buena calidad)"
    elif capabilities["reportlab"]:
        recommendation = "ReportLab (básico pero confiable)"
    else:
        recommendation = "Ninguno disponible - instalar dependencias"
    
    return jsonify({
        "status": "success",
        "capabilities": capabilities,
        "recommendation": recommendation,
        "install_command": "pip install weasyprint pyppeteer reportlab beautifulsoup4"
    })


@download_bp.route("/html-to-pdf", methods=["POST"])
def convert_html_to_pdf():
    """
    🎯 ENDPOINT PRINCIPAL: Convertir HTML del frontend directamente a PDF
    
    Este es el endpoint principal que usa el frontend renovado.
    Recibe el HTML exacto que se muestra en el preview y lo convierte a PDF.
    
    Métodos de fallback en orden de prioridad:
    1. WeasyPrint (mejor calidad HTML/CSS)
    2. Puppeteer (excelente renderizado)
    3. ReportLab (fallback confiable)
    4. HTML estilizado (último recurso)
    """
    try:
        # ✅ Validar request JSON
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type debe ser application/json",
                "error": "Tipo de contenido inválido"
            }), 400
        
        data = request.get_json()
        html_content = data.get('html_content')
        document_id = data.get('document_id', 'propuesta')
        client_name = data.get('client_name', 'cliente')
        structured_data = data.get('structured_data')
        
        # ✅ Validar que hay contenido HTML
        if not html_content:
            return jsonify({
                "status": "error",
                "message": "Se requiere contenido HTML",
                "error": "Parámetro html_content faltante"
            }), 400
        
        logger.info(f"🎯 Convirtiendo HTML a PDF para cliente: {client_name}")
        logger.info(f"📝 Longitud del contenido HTML: {len(html_content)} caracteres")
        logger.info(f"📊 Datos estructurados disponibles: {bool(structured_data)}")
        
        # ✅ Registrar errores para debugging
        conversion_errors = []
        
        # 🥇 MÉTODO 1: WeasyPrint (mejor soporte HTML/CSS)
        try:
            logger.info("🔄 Intentando conversión con WeasyPrint...")
            return _convert_with_weasyprint(html_content, document_id, client_name)
        except ImportError as e:
            error_msg = f"WeasyPrint no disponible: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("WeasyPrint Import", error_msg))
        except Exception as e:
            error_msg = f"WeasyPrint falló: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("WeasyPrint Runtime", error_msg))
        
        # 🥈 MÉTODO 2: Puppeteer (excelente renderizado)
        try:
            logger.info("🔄 Intentando conversión con Puppeteer...")
            return _convert_with_puppeteer(html_content, document_id, client_name)
        except ImportError as e:
            error_msg = f"Puppeteer no disponible: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("Puppeteer Import", error_msg))
        except Exception as e:
            error_msg = f"Puppeteer falló: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("Puppeteer Runtime", error_msg))
        
        # 🥉 MÉTODO 3: ReportLab (fallback confiable)
        try:
            logger.info("🔄 Intentando conversión con ReportLab...")
            return _convert_with_reportlab(html_content, document_id, client_name, structured_data)
        except ImportError as e:
            error_msg = f"ReportLab no disponible: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("ReportLab Import", error_msg))
        except Exception as e:
            error_msg = f"ReportLab falló: {e}"
            logger.warning(f"⚠️ {error_msg}")
            conversion_errors.append(("ReportLab Runtime", error_msg))
        
        # 🆘 MÉTODO 4: HTML estilizado (último recurso)
        logger.warning("🔄 Todos los métodos PDF fallaron, devolviendo HTML estilizado...")
        try:
            return _create_styled_html_download(html_content, document_id, client_name)
        except Exception as e:
            error_msg = f"HTML fallback falló: {e}"
            logger.error(f"❌ {error_msg}")
            conversion_errors.append(("HTML Fallback", error_msg))
        
        # ❌ Si todo falla, devolver error detallado
        error_summary = "\n".join([f"{method}: {error}" for method, error in conversion_errors])
        logger.error(f"❌ Todos los métodos de conversión fallaron para {client_name}:\n{error_summary}")
        
        return jsonify({
            "status": "error",
            "message": "Todos los métodos de conversión a PDF fallaron",
            "error": "Generación de PDF no disponible",
            "details": dict(conversion_errors),
            "suggestion": "Instale dependencias PDF: pip install weasyprint pyppeteer reportlab beautifulsoup4"
        }), 500
            
    except Exception as e:
        logger.error(f"❌ Error inesperado en convert_html_to_pdf: {e}")
        logger.error(f"❌ Tipo de excepción: {type(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error inesperado en conversión a PDF",
            "error": str(e),
            "type": str(type(e))
        }), 500


def _download_as_pdf(document_data: dict, document_id: str):
    """Generate and download PDF from document content with optimized fallback order"""
    try:
        # FIXED: Try WeasyPrint first (better HTML support when libpango works)
        try:
            import weasyprint
            # Quick test to see if WeasyPrint can import properly
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            logger.info("🔄 Trying WeasyPrint first (best HTML support)")
            return _download_as_pdf_weasyprint_direct(document_data, document_id)
        except ImportError as weasy_import:
            logger.warning(f"WeasyPrint not available: {weasy_import}")
        except Exception as weasy_error:
            logger.error(f"WeasyPrint failed: {weasy_error}")
            if "libpango" in str(weasy_error) or "WeasyPrint could not import" in str(weasy_error):
                logger.info("🔄 libpango issue detected, trying ReportLab (stable fallback)")
                return _download_as_pdf_reportlab(document_data, document_id)
        
        # Try Puppeteer as secondary option (good quality but threading issues)
        try:
            logger.info("🔄 Trying Puppeteer as secondary option")
            return _download_as_pdf_puppeteer(document_data, document_id)
        except ImportError:
            logger.warning("Puppeteer not available, trying ReportLab")
        except Exception as puppeteer_error:
            logger.error(f"Puppeteer failed: {puppeteer_error}")
            logger.info("🔄 Puppeteer failed, trying ReportLab fallback")
        
        # Try ReportLab as reliable fallback
        try:
            logger.info("🔄 Trying ReportLab as final fallback")
            return _download_as_pdf_reportlab(document_data, document_id)
        except ImportError:
            logger.warning("ReportLab not available, falling back to HTML download")
        except Exception as reportlab_error:
            logger.error(f"ReportLab failed: {reportlab_error}")
            
        # Last resort: HTML download with professional styling
        logger.warning("🔄 All PDF methods failed, falling back to styled HTML download")
        return _download_as_styled_html_fallback(document_data, document_id)
            
    except Exception as e:
        logger.error(f"❌ PDF generation completely failed: {e}")
        raise


def _download_as_pdf_weasyprint_direct(document_data: dict, document_id: str):
    """Direct WeasyPrint PDF generation (optimized version)"""
    try:
        import weasyprint
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        # FIXED: Use helper to get content with V2.0 and legacy support
        html_content, markdown_content = _get_document_contents(document_data)
        
        # If no professional HTML exists, fall back to markdown conversion
        if not html_content and markdown_content:
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
            # Create styled HTML using fallback function
            styled_html = _create_styled_html(html_content, document_data)
        elif html_content:
            # Use the professional HTML directly (this is what we want!)
            styled_html = html_content
        else:
            styled_html = _create_styled_html("No content available", document_data)
        
        # Generate PDF
        font_config = FontConfiguration()
        pdf_buffer = BytesIO()
        
        # Use the HTML with Sabra Corporation design-specific CSS styles
        pdf_css = CSS(string="""
            @page {
                margin: 2cm;
                size: A4;
            }
            
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.3;
                color: #000;
                font-size: 11px;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 25px;
                padding-bottom: 15px;
            }
            
            .company-section {
                flex: 1;
            }
            
            .company-name {
                font-size: 36px;
                font-weight: bold;
                color: #2c5f7c;
                margin-bottom: 2px;
                letter-spacing: -1px;
            }
            
            .company-subtitle {
                font-size: 14px;
                color: #2c5f7c;
                margin-bottom: 5px;
                font-weight: normal;
            }
            
            .company-address {
                font-size: 10px;
                color: #000;
                line-height: 1.2;
            }
            
            .budget-section {
                border: 2px solid #000;
                padding: 10px;
                min-width: 180px;
                text-align: center;
            }
            
            .main-table {
                width: 100%;
                border-collapse: collapse;
                border: 2px solid #000;
                margin: 10px 0;
            }
            
            .main-table th {
                background-color: #f0f0f0;
                font-weight: bold;
                padding: 8px 6px;
                text-align: center;
                border: 1px solid #000;
                font-size: 11px;
            }
            
            .main-table td {
                padding: 4px 6px;
                border: 1px solid #000;
                font-size: 10px;
                vertical-align: middle;
            }
            
            .no-print { display: none; }
        """)
        
        HTML(string=styled_html).write_pdf(
            pdf_buffer,
            stylesheets=[pdf_css],
            font_config=font_config
        )
        
        pdf_buffer.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_buffer.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"✅ WeasyPrint PDF generated successfully: {document_id}")
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
                
    except Exception as e:
        logger.error(f"❌ WeasyPrint direct PDF generation failed: {e}")
        raise






def _download_as_pdf_puppeteer(document_data: dict, document_id: str):
    """Generate PDF using Puppeteer (primary method)"""
    try:
        import asyncio
        from pyppeteer import launch
        
        # FIXED: Use helper to get content with V2.0 and legacy support
        html_content, markdown_content = _get_document_contents(document_data)
        
        # If no professional HTML exists, fall back to markdown conversion
        if not html_content and markdown_content:
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
            # Create styled HTML using fallback function
            styled_html = _create_styled_html(html_content, document_data)
        elif html_content:
            # Use the professional HTML directly (this is what we want!)
            styled_html = html_content
        else:
            styled_html = _create_styled_html("No content available", document_data)
        
        # Generate PDF with Puppeteer
        async def generate_pdf():
            browser = await launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            
            try:
                page = await browser.newPage()
                await page.setContent(styled_html, waitUntil='networkidle0')
                
                # Set viewport for consistent rendering
                await page.setViewport({'width': 1920, 'height': 1080})
                
                # Generate PDF with A4 format
                pdf_buffer = await page.pdf({
                    'format': 'A4',
                    'margin': {
                        'top': '2cm',
                        'right': '2cm',
                        'bottom': '2cm',
                        'left': '2cm'
                    },
                    'printBackground': True,
                    'preferCSSPageSize': True
                })
                
                return pdf_buffer
            
            finally:
                await browser.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            pdf_bytes = loop.run_until_complete(generate_pdf())
        finally:
            loop.close()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"Puppeteer PDF generation failed: {e}")
        raise


def _get_document_contents(document_data: dict) -> tuple[str, str]:
    """
    Get HTML and markdown content from document data, handling both V2.0 and legacy field names.
    
    Returns:
        tuple[str, str]: (html_content, markdown_content)
    """
    if not isinstance(document_data, dict):
        logger.error(f"❌ _get_document_contents received non-dict: {type(document_data)}")
        return "", ""
    
    logger.info(f"🔍 _get_document_contents processing document with keys: {list(document_data.keys())}")
    
    # V2.0 field names (from Supabase generated_documents table)
    html_content = document_data.get("content_html", "")
    markdown_content = document_data.get("content_markdown", "")
    
    # Legacy field names (Spanish) - fallback
    if not html_content:
        html_content = document_data.get("contenido_html", "")
        if html_content:
            logger.info("📄 Using legacy contenido_html field")
    else:
        logger.info("📄 Using V2.0 content_html field")
        
    if not markdown_content:
        markdown_content = document_data.get("contenido_markdown", "")
        if markdown_content:
            logger.info("📄 Using legacy contenido_markdown field")
    else:
        logger.info("📄 Using V2.0 content_markdown field")
    
    # Convert to strings and clean
    html_content = str(html_content or "").strip()
    markdown_content = str(markdown_content or "").strip()
    
    logger.info(f"📄 Final content lengths: html={len(html_content)}, markdown={len(markdown_content)}")
    
    if not html_content and not markdown_content:
        logger.error(f"❌ No content found in any field. Document preview: {str(document_data)[:300]}...")
    
    return html_content, markdown_content


def _extract_text_from_html_for_reportlab(html_content: str) -> str:
    """Extract clean text from HTML for ReportLab PDF generation"""
    try:
        from bs4 import BeautifulSoup
        
        # Parse HTML and extract text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text with some structure preservation
        text_content = []
        
        # Process headers
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            text_content.append(f"\n# {header.get_text().strip()}\n")
        
        # Process tables
        for table in soup.find_all('table'):
            text_content.append("\n[TABLA DE PRESUPUESTO]\n")
            for row in table.find_all('tr'):
                row_text = []
                for cell in row.find_all(['td', 'th']):
                    cell_text = cell.get_text().strip()
                    if cell_text:
                        row_text.append(cell_text)
                if row_text:
                    text_content.append(" | ".join(row_text))
        
        # Process paragraphs and other content
        for para in soup.find_all(['p', 'div', 'span']):
            para_text = para.get_text().strip()
            if para_text and para_text not in [item.strip() for item in text_content]:
                text_content.append(para_text)
        
        # Join and clean
        final_text = "\n".join(text_content)
        
        # If BeautifulSoup extraction failed, use simple HTML tag removal
        if not final_text.strip():
            import re
            final_text = re.sub(r'<[^>]+>', '', html_content)
            final_text = re.sub(r'\s+', ' ', final_text).strip()
        
        return final_text
        
    except ImportError:
        # Fallback: Simple HTML tag removal
        logger.warning("⚠️ BeautifulSoup not available, using simple HTML parsing")
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logger.error(f"❌ Error extracting text from HTML: {e}")
        # Last resort: return HTML as-is
        return html_content


def _download_as_pdf_reportlab(document_data: dict, document_id: str):
    """Fallback PDF generation using ReportLab"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               topMargin=1*inch, bottomMargin=1*inch,
                               leftMargin=1*inch, rightMargin=1*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        
        # Build content
        story = []
        
        # Add title
        title = f"Propuesta Comercial - {document_data.get('id', 'Documento')}"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))
        
        # Add document info
        if document_data.get('fecha_creacion'):
            story.append(Paragraph(f"<b>Fecha:</b> {document_data['fecha_creacion']}", styles['Normal']))
            story.append(Spacer(1, 10))
        
        if document_data.get('costo_total'):
            story.append(Paragraph(f"<b>Costo Total:</b> ${document_data['costo_total']:,.2f}", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # FIXED: Use helper to get content with V2.0 and legacy support
        html_content, markdown_content = _get_document_contents(document_data)
        
        # Convert content to display format
        if html_content:
            # Use HTML content (professional content from AI)
            content = _extract_text_from_html_for_reportlab(html_content)
            logger.info(f"📄 Using HTML content for ReportLab: {len(content)} characters")
        elif markdown_content:
            # Fallback to markdown
            content = markdown_content
            logger.info(f"📄 Using Markdown content for ReportLab: {len(content)} characters")
        else:
            content = "No content available"
            logger.warning("⚠️ No content found for ReportLab PDF generation")
        
        # Simple content to paragraphs conversion
        for line in content.split('\n'):
            if line.strip():
                if line.startswith('#'):
                    # Header
                    header_text = line.replace('#', '').strip()
                    story.append(Paragraph(f"<b>{header_text}</b>", styles['Heading2']))
                else:
                    # Regular paragraph
                    story.append(Paragraph(line, styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(buffer.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except ImportError:
        logger.warning("ReportLab not available, falling back to text download")
        return _download_as_text(document_data, document_id)


def _download_as_html(document_data: dict, document_id: str):
    """Download as HTML file"""
    try:
        # FIXED: Use helper to get content with V2.0 and legacy support
        html_content, markdown_content = _get_document_contents(document_data)
        
        if not html_content and markdown_content:
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        styled_html = _create_styled_html(html_content, document_data)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as tmp_file:
            tmp_file.write(styled_html)
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.html",
                mimetype='text/html'
            )
        finally:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"Error generating HTML: {e}")
        return _download_as_text(document_data, document_id)


def _download_as_markdown(document_data: dict, document_id: str):
    """Download as Markdown file"""
    try:
        # FIXED: Use helper to get content with V2.0 and legacy support
        html_content, markdown_content = _get_document_contents(document_data)
        content = markdown_content or "No content available"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.md",
                mimetype='text/markdown'
            )
        finally:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"Error generating Markdown: {e}")
        return _download_as_text(document_data, document_id)


def _download_as_text(document_data: dict, document_id: str):
    """Fallback: download as plain text"""
    try:
        content = document_data.get("contenido_markdown", "No content available")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            tmp_file.write(f"PROPUESTA COMERCIAL - {document_id}\n")
            tmp_file.write("=" * 50 + "\n\n")
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.txt",
                mimetype='text/plain'
            )
        finally:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"Error generating text file: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to generate any document format",
            "error": str(e)
        }), 500


def _create_styled_html(content: str, document_data: dict) -> str:
    """Create styled HTML document matching the sabra corporation design"""
    from datetime import datetime
    
    fecha_actual = datetime.now().strftime("%d/%m/%y")
    numero_presupuesto = f"EV-{datetime.now().strftime('%d%m%y')}{document_data.get('id', 'Unknown')[-3:]}"
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Propuesta Comercial - {document_data.get('id', 'Documento')}</title>
        <style>
            {_get_html_styles()}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-section">
                <div class="company-name">sabra</div>
                <div class="company-subtitle">corporation</div>
                <div class="company-address">
                    Av. Principal, Mini Centro<br>
                    Principal Local 16, Lechería,<br>
                    Anzoátegui, 6016
                </div>
            </div>
            
            <div class="budget-section">
                <div class="budget-title">PRESUPUESTO</div>
                <table class="budget-table">
                    <tr>
                        <td class="label">Fecha</td>
                        <td class="value">{fecha_actual}</td>
                    </tr>
                    <tr>
                        <td class="label">Duración</td>
                        <td class="value">20 días</td>
                    </tr>
                    <tr>
                        <td class="label">#</td>
                        <td class="value">{numero_presupuesto}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="content">
            {content}
        </div>
    </body>
    </html>
    """


def _get_html_styles() -> str:
    """Get CSS styles for HTML documents - Updated to match sabra corporation design"""
    return """
        @page {
            margin: 2cm;
            size: A4;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.3;
            color: #000;
            font-size: 11px;
            background-color: white;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 25px;
            padding-bottom: 15px;
        }
        
        .company-section {
            flex: 1;
        }
        
        .company-name {
            font-size: 36px;
            font-weight: bold;
            color: #2c5f7c;
            margin-bottom: 2px;
            letter-spacing: -1px;
        }
        
        .company-subtitle {
            font-size: 14px;
            color: #2c5f7c;
            margin-bottom: 5px;
            font-weight: normal;
        }
        
        .company-address {
            font-size: 10px;
            color: #000;
            line-height: 1.2;
        }
        
        .budget-section {
            border: 2px solid #000;
            padding: 10px;
            min-width: 180px;
            text-align: center;
        }
        
        .budget-title {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
        }
        
        .budget-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .budget-table td {
            border: 1px solid #000;
            padding: 4px 6px;
            font-size: 11px;
        }
        
        .budget-table .label {
            text-align: left;
            font-weight: normal;
        }
        
        .budget-table .value {
            text-align: right;
            font-weight: bold;
        }
        
        .client-section {
            margin: 20px 0;
            font-size: 11px;
        }
        
        .client-name {
            font-weight: bold;
            margin-bottom: 3px;
        }
        
        .process-info {
            font-weight: bold;
            margin-bottom: 15px;
            text-decoration: underline;
        }
        
        .main-table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000;
            margin: 10px 0;
        }
        
        .main-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000;
            font-size: 11px;
        }
        
        .main-table td {
            padding: 4px 6px;
            border: 1px solid #000;
            font-size: 10px;
            vertical-align: middle;
        }
        
        .content {
            margin: 20px 0;
            padding: 0;
        }
        
        .content table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000;
            margin: 10px 0;
        }
        
        .content th {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000;
            font-size: 11px;
        }
        
        .content td {
            padding: 4px 6px;
            border: 1px solid #000;
            font-size: 10px;
            vertical-align: middle;
        }
        
        .category-header {
            background-color: #d3d3d3;
            font-weight: bold;
            text-align: center;
        }
        
        .category-header td {
            padding: 6px;
            font-size: 11px;
        }
        
        .coordination-row {
            border-top: 2px solid #000;
        }
        
        .coordination-row td {
            padding: 6px;
            font-weight: bold;
        }
        
        .total-row {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        
        .total-row td {
            padding: 6px;
            font-size: 11px;
        }
        
        .final-total {
            background-color: #e0e0e0;
            font-weight: bold;
        }
        
        .final-total td {
            padding: 8px;
            font-size: 12px;
        }
        
        h1, h2, h3 { 
            color: #2c3e50; 
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h1 {
            font-size: 2em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        
        h2 {
            font-size: 1.5em;
            color: #374151;
        }
        
        h3 {
            font-size: 1.2em;
            color: #4b5563;
        }
        
        p {
            margin: 0.8em 0;
        }
        
        strong {
            color: #1f2937;
        }
        
        ul, ol {
            padding-left: 1.5em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 2em 0;
        }
        
        @media print {
            body { 
                margin: 0;
                padding: 15px;
                font-size: 11pt;
            }
        }
    """


def _download_as_styled_html_fallback(document_data: dict, document_id: str):
    """Generate a beautifully styled HTML document as PDF fallback"""
    try:
        # Get HTML content (professional version)
        html_content = document_data.get("contenido_html", "")
        
        if not html_content:
            # If no HTML, convert markdown to basic HTML
            markdown_content = document_data.get("contenido_markdown", "")
            if markdown_content:
                html_content = f"<div class='markdown-content'><pre>{markdown_content}</pre></div>"
            else:
                html_content = "<p>No hay contenido disponible</p>"
        
        # Create complete styled HTML document
        styled_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta Comercial - {document_id}</title>
    <style>
        {_get_professional_html_styles()}
    </style>
</head>
<body>
    <div class="document-header">
        <div class="header-notice">
            <h4>📄 Propuesta Comercial</h4>
            <p>Documento ID: {document_id}</p>
            <p><em>Para convertir a PDF: Ctrl+P → Guardar como PDF</em></p>
        </div>
    </div>
    
    <div class="document-content">
        {html_content}
    </div>
    
    <div class="document-footer">
        <hr>
        <p><small>Documento generado automáticamente por AI-RFX System</small></p>
        <p><small>Fecha de generación: {document_data.get('fecha_creacion', 'N/A')}</small></p>
    </div>
</body>
</html>"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_file:
            tmp_file.write(styled_document)
            tmp_file_path = tmp_file.name
        
        try:
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta_{document_id}.html",
                mimetype='text/html'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
                
    except Exception as e:
        logger.error(f"Error generating styled HTML fallback: {e}")
        # Final fallback - plain text
        return _download_as_text(document_data, document_id)


def _get_professional_html_styles() -> str:
    """Professional CSS styles for HTML fallback document - Updated sabra corporation design"""
    return """
        @page {
            margin: 2cm;
            size: A4;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.3;
            color: #000;
            font-size: 11px;
            background-color: white;
        }
        
        .document-header {
            margin-bottom: 20px;
            padding-bottom: 10px;
        }
        
        .header-notice {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .header-notice h4 {
            margin: 0 0 10px 0;
            color: #1e40af;
            font-size: 1.2em;
        }
        
        .header-notice p {
            margin: 5px 0;
            color: #64748b;
            font-size: 0.9em;
        }
        
        .document-content {
            margin: 20px 0;
            padding: 0;
        }
        
        /* Sabra Corporation Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 25px;
            padding-bottom: 15px;
        }
        
        .company-section {
            flex: 1;
        }
        
        .company-name {
            font-size: 36px;
            font-weight: bold;
            color: #2c5f7c;
            margin-bottom: 2px;
            letter-spacing: -1px;
        }
        
        .company-subtitle {
            font-size: 14px;
            color: #2c5f7c;
            margin-bottom: 5px;
            font-weight: normal;
        }
        
        .company-address {
            font-size: 10px;
            color: #000;
            line-height: 1.2;
        }
        
        .budget-section {
            border: 2px solid #000;
            padding: 10px;
            min-width: 180px;
            text-align: center;
        }
        
        .budget-title {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
        }
        
        .budget-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .budget-table td {
            border: 1px solid #000;
            padding: 4px 6px;
            font-size: 11px;
        }
        
        .budget-table .label {
            text-align: left;
            font-weight: normal;
        }
        
        .budget-table .value {
            text-align: right;
            font-weight: bold;
        }
        
        /* Professional table styles for proposal */
        .main-table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000;
            margin: 10px 0;
            font-size: 11px;
        }
        
        .main-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000;
            font-size: 11px;
        }
        
        .main-table td {
            padding: 4px 6px;
            border: 1px solid #000;
            font-size: 10px;
            vertical-align: middle;
        }
        
        /* Client info */
        .client-section {
            margin: 20px 0;
            font-size: 11px;
        }
        
        .client-name {
            font-weight: bold;
            margin-bottom: 3px;
        }
        
        .process-info {
            font-weight: bold;
            margin-bottom: 15px;
            text-decoration: underline;
        }
        
        /* Category rows */
        .category-header {
            background-color: #d3d3d3;
            font-weight: bold;
            text-align: center;
        }
        
        .category-header td {
            padding: 6px;
            font-size: 11px;
        }
        
        .coordination-row {
            border-top: 2px solid #000;
        }
        
        .coordination-row td {
            padding: 6px;
            font-weight: bold;
        }
        
        /* Total section */
        .total-row {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        
        .total-row td {
            padding: 6px;
            font-size: 11px;
        }
        
        .final-total {
            background-color: #e0e0e0;
            font-weight: bold;
        }
        
        .final-total td {
            padding: 8px;
            font-size: 12px;
        }
        
        .document-footer {
            margin-top: 50px;
            padding-top: 20px;
            text-align: center;
            color: #64748b;
            font-size: 0.85em;
        }
        
        /* Print styles */
        @media print {
            .document-header .header-notice {
                display: none;
            }
            
            body {
                margin: 0;
                padding: 15px;
                font-size: 11pt;
            }
        }
        
        /* Generic content styling */
        h1, h2, h3 {
            color: #1e293b;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h1 {
            font-size: 2em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        
        h2 {
            font-size: 1.5em;
            color: #374151;
        }
        
        h3 {
            font-size: 1.2em;
            color: #4b5563;
        }
        
        p {
            margin: 0.8em 0;
        }
        
        strong {
            color: #1f2937;
        }
        
        ul, ol {
            padding-left: 1.5em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 2em 0;
        }
    """


def _convert_html_to_pdf_puppeteer(html_content: str, document_id: str, client_name: str):
    """Convert HTML to PDF using Puppeteer (primary method for professional HTML)"""
    try:
        import asyncio
        from pyppeteer import launch
        
        logger.info(f"🎯 Starting Puppeteer PDF conversion for {client_name}")
        
        async def generate_pdf():
            browser = await launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            
            try:
                page = await browser.newPage()
                await page.setContent(html_content, waitUntil='networkidle0')
                
                # Set viewport for consistent rendering
                await page.setViewport({'width': 1920, 'height': 1080})
                
                # Generate PDF with A4 format
                pdf_buffer = await page.pdf({
                    'format': 'A4',
                    'margin': {
                        'top': '2cm',
                        'right': '2cm',
                        'bottom': '2cm',
                        'left': '2cm'
                    },
                    'printBackground': True,
                    'preferCSSPageSize': True
                })
                
                return pdf_buffer
            
            finally:
                await browser.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            pdf_bytes = loop.run_until_complete(generate_pdf())
        finally:
            loop.close()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"✅ Puppeteer PDF generated successfully for {client_name}")
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"Puppeteer PDF conversion failed: {e}")
        raise


def _convert_html_to_pdf_reportlab_simple(html_content: str, document_id: str, client_name: str):
    """Convert HTML to simple PDF using ReportLab (ultimate fallback)"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        import re
        from html import unescape
        
        logger.info(f"🎯 Starting ReportLab simple PDF conversion for {client_name}")
        
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               topMargin=1*inch, bottomMargin=1*inch,
                               leftMargin=1*inch, rightMargin=1*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.Color(44/255, 95/255, 124/255),  # #2c5f7c
            alignment=0
        )
        
        # Build content
        story = []
        
        # Add Sabra Corporation header
        story.append(Paragraph("<b>sabra</b>", company_style))
        story.append(Paragraph("corporation", styles['Normal']))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Av. Principal, Mini Centro<br/>Principal Local 16, Lechería,<br/>Anzoátegui, 6016", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Add title
        story.append(Paragraph(f"PRESUPUESTO - {client_name}", title_style))
        story.append(Spacer(1, 20))
        
        # Extract and display content from HTML
        try:
            # Clean HTML and extract text content
            clean_content = re.sub(r'<[^>]+>', ' ', html_content)
            clean_content = unescape(clean_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # Extract client name
            client_match = re.search(r'Para:\s*([A-Z][A-Z\s&]+)', clean_content)
            if client_match:
                story.append(Paragraph(f"<b>Para:</b> {client_match.group(1).strip()}", styles['Normal']))
                story.append(Spacer(1, 10))
            
            # Extract productos/items from table structure
            # Look for patterns like "Product Quantity Price Total"
            product_pattern = r'(\w+(?:\s+\w+)*)\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)'
            matches = re.findall(product_pattern, clean_content)
            
            if matches:
                story.append(Paragraph("<b>Productos y Servicios:</b>", styles['Heading2']))
                story.append(Spacer(1, 10))
                
                # Create table data
                table_data = [['Descripción', 'Cantidad', 'Precio', 'Total']]
                
                for match in matches:
                    product_name, quantity, price, total = match
                    table_data.append([product_name, quantity, price, total])
                
                # Create table
                table = Table(table_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 20))
            
            # Extract total
            total_match = re.search(r'Total\s+([\d,\.]+)', clean_content)
            if total_match:
                story.append(Paragraph(f"<b>TOTAL: {total_match.group(1)}</b>", styles['Heading2']))
                story.append(Spacer(1, 20))
            
            # Add footer
            story.append(Spacer(1, 30))
            story.append(Paragraph("Documento generado automáticamente por AI-RFX System", styles['Normal']))
        
        except Exception as extract_error:
            logger.warning(f"Could not extract detailed info from HTML: {extract_error}")
            # Fallback: just add basic info
            story.append(Paragraph(f"Propuesta comercial para: {client_name}", styles['Normal']))
            story.append(Spacer(1, 10))
            story.append(Paragraph("Propuesta generada automáticamente", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(buffer.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"✅ ReportLab simple PDF generated successfully for {client_name}")
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"ReportLab simple PDF conversion failed: {e}")
        logger.error(f"Exception details:", exc_info=True)
        raise


def _convert_html_to_pdf_weasyprint(html_content: str, document_id: str, client_name: str):
    """Convert HTML to PDF using WeasyPrint (fallback method)"""
    try:
        import weasyprint
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        logger.info(f"🎯 Starting WeasyPrint PDF conversion for {client_name}")
        
        # Generate PDF
        font_config = FontConfiguration()
        pdf_buffer = BytesIO()
        
        # Use the HTML with Sabra Corporation design-specific CSS styles
        pdf_css = CSS(string="""
            @page {
                margin: 2cm;
                size: A4;
            }
            
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.3;
                color: #000;
                font-size: 11px;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 25px;
                padding-bottom: 15px;
            }
            
            .company-section {
                flex: 1;
            }
            
            .company-name {
                font-size: 36px;
                font-weight: bold;
                color: #2c5f7c;
                margin-bottom: 2px;
                letter-spacing: -1px;
            }
            
            .company-subtitle {
                font-size: 14px;
                color: #2c5f7c;
                margin-bottom: 5px;
                font-weight: normal;
            }
            
            .company-address {
                font-size: 10px;
                color: #000;
                line-height: 1.2;
            }
            
            .budget-section {
                border: 2px solid #000;
                padding: 10px;
                min-width: 180px;
                text-align: center;
            }
            
            .budget-title {
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 8px;
            }
            
            .budget-table {
                width: 100%;
                border-collapse: collapse;
            }
            
            .budget-table td {
                border: 1px solid #000;
                padding: 4px 6px;
                font-size: 11px;
            }
            
            .budget-table .label {
                text-align: left;
                font-weight: normal;
            }
            
            .budget-table .value {
                text-align: right;
                font-weight: bold;
            }
            
            .client-section {
                margin: 20px 0;
                font-size: 11px;
            }
            
            .client-name {
                font-weight: bold;
                margin-bottom: 3px;
            }
            
            .process-info {
                font-weight: bold;
                margin-bottom: 15px;
                text-decoration: underline;
            }
            
            .main-table {
                width: 100%;
                border-collapse: collapse;
                border: 2px solid #000;
                margin: 10px 0;
            }
            
            .main-table th {
                background-color: #f0f0f0;
                font-weight: bold;
                padding: 8px 6px;
                text-align: center;
                border: 1px solid #000;
                font-size: 11px;
            }
            
            .main-table td {
                padding: 4px 6px;
                border: 1px solid #000;
                font-size: 10px;
                vertical-align: middle;
            }
            
            .category-header {
                background-color: #d3d3d3;
                font-weight: bold;
                text-align: center;
            }
            
            .category-header td {
                padding: 6px;
                font-size: 11px;
            }
            
            .coordination-row {
                border-top: 2px solid #000;
            }
            
            .coordination-row td {
                padding: 6px;
                font-weight: bold;
            }
            
            .total-row {
                background-color: #f8f8f8;
                font-weight: bold;
            }
            
            .total-row td {
                padding: 6px;
                font-size: 11px;
            }
            
            .final-total {
                background-color: #e0e0e0;
                font-weight: bold;
            }
            
            .final-total td {
                padding: 8px;
                font-size: 12px;
            }
            
            .no-print { display: none; }
        """)
        
        HTML(string=html_content).write_pdf(
            pdf_buffer,
            stylesheets=[pdf_css],
            font_config=font_config
        )
        
        pdf_buffer.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_buffer.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"✅ WeasyPrint PDF generated successfully for {client_name}")
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
                mimetype='application/pdf'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
    
    except Exception as e:
        logger.error(f"WeasyPrint PDF conversion failed: {e}")
        raise


def _create_styled_html_fallback(html_content: str, document_id: str, client_name: str):
    """Create styled HTML download as final fallback when PDF generation fails"""
    try:
        from datetime import datetime
        
        # Extract the Sabra Corporation CSS styles that we defined earlier
        sabra_styles = """
        @page {
            margin: 2cm;
            size: A4;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.3;
            color: #000;
            font-size: 11px;
            background-color: white;
        }
        
        .fallback-notice {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .fallback-notice h4 {
            margin: 0 0 10px 0;
            color: #856404;
            font-size: 1.1em;
        }
        
        .fallback-notice p {
            margin: 5px 0;
            color: #856404;
            font-size: 0.9em;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 25px;
            padding-bottom: 15px;
        }
        
        .company-section {
            flex: 1;
        }
        
        .company-name {
            font-size: 36px;
            font-weight: bold;
            color: #2c5f7c;
            margin-bottom: 2px;
            letter-spacing: -1px;
        }
        
        .company-subtitle {
            font-size: 14px;
            color: #2c5f7c;
            margin-bottom: 5px;
            font-weight: normal;
        }
        
        .company-address {
            font-size: 10px;
            color: #000;
            line-height: 1.2;
        }
        
        .budget-section {
            border: 2px solid #000;
            padding: 10px;
            min-width: 180px;
            text-align: center;
        }
        
        .budget-title {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
        }
        
        .budget-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .budget-table td {
            border: 1px solid #000;
            padding: 4px 6px;
            font-size: 11px;
        }
        
        .budget-table .label {
            text-align: left;
            font-weight: normal;
        }
        
        .budget-table .value {
            text-align: right;
            font-weight: bold;
        }
        
        .client-section {
            margin: 20px 0;
            font-size: 11px;
        }
        
        .client-name {
            font-weight: bold;
            margin-bottom: 3px;
        }
        
        .process-info {
            font-weight: bold;
            margin-bottom: 15px;
            text-decoration: underline;
        }
        
        .main-table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000;
            margin: 10px 0;
        }
        
        .main-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000;
            font-size: 11px;
        }
        
        .main-table td {
            padding: 4px 6px;
            border: 1px solid #000;
            font-size: 10px;
            vertical-align: middle;
        }
        
        .category-header {
            background-color: #d3d3d3;
            font-weight: bold;
            text-align: center;
        }
        
        .category-header td {
            padding: 6px;
            font-size: 11px;
        }
        
        .coordination-row {
            border-top: 2px solid #000;
        }
        
        .coordination-row td {
            padding: 6px;
            font-weight: bold;
        }
        
        .total-row {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        
        .total-row td {
            padding: 6px;
            font-size: 11px;
        }
        
        .final-total {
            background-color: #e0e0e0;
            font-weight: bold;
        }
        
        .final-total td {
            padding: 8px;
            font-size: 12px;
        }
        
        @media print {
            .fallback-notice { display: none; }
            body { margin: 0; padding: 15px; font-size: 11pt; }
        }
        """
        
        # Create complete styled HTML document
        styled_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta Comercial - {client_name}</title>
    <style>
        {sabra_styles}
    </style>
</head>
<body>
    <div class="fallback-notice">
        <h4>📄 Propuesta Comercial - {client_name}</h4>
        <p>ID: {document_id}</p>
        <p><strong>Nota:</strong> Para convertir a PDF: Ctrl+P → Guardar como PDF</p>
        <p><strong>Alternativa:</strong> Abrir en navegador y usar "Imprimir" → "Guardar como PDF"</p>
    </div>
    
    {html_content}
    
    <div style="margin-top: 50px; padding-top: 20px; text-align: center; color: #64748b; font-size: 0.85em; border-top: 1px solid #e2e8f0;">
        <p><small>Documento generado automáticamente por AI-RFX System</small></p>
        <p><small>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small></p>
        <p><small>Cliente: {client_name}</small></p>
    </div>
</body>
</html>"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_file:
            tmp_file.write(styled_document)
            tmp_file_path = tmp_file.name
        
        try:
            logger.info(f"📄 Generated professional styled HTML fallback for {client_name}")
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.html",
                mimetype='text/html'
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
                
    except Exception as e:
        logger.error(f"HTML fallback creation failed: {e}")
        logger.error(f"Exception details:", exc_info=True)
        raise


# ================================
# 🛠️ NUEVOS MÉTODOS DE CONVERSIÓN OPTIMIZADOS
# ================================

def _convert_with_weasyprint(html_content: str, document_id: str, client_name: str):
    """🥇 Método 1: WeasyPrint - Mejor soporte HTML/CSS"""
    import weasyprint
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    
    logger.info(f"🎯 Iniciando conversión WeasyPrint para {client_name}")
    
    # Configuración de fuentes
    font_config = FontConfiguration()
    pdf_buffer = BytesIO()
    
    # CSS específico para PDF (mantiene diseño Sabra Corporation)
    pdf_css = CSS(string="""
        @page {
            margin: 2cm;
            size: A4;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.3;
            color: #000;
            font-size: 11px;
        }
        
        .company-name {
            font-size: 36px;
            font-weight: bold;
            color: #2c5f7c;
            margin-bottom: 2px;
            letter-spacing: -1px;
        }
        
        .company-subtitle {
            font-size: 14px;
            color: #2c5f7c;
            margin-bottom: 5px;
            font-weight: normal;
        }
        
        .main-table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid #000;
            margin: 10px 0;
        }
        
        .main-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #000;
            font-size: 11px;
        }
        
        .main-table td {
            padding: 4px 6px;
            border: 1px solid #000;
            font-size: 10px;
            vertical-align: middle;
        }
        
        .no-print { display: none; }
    """)
    
    # Generar PDF
    HTML(string=html_content).write_pdf(
        pdf_buffer,
        stylesheets=[pdf_css],
        font_config=font_config
    )
    
    pdf_buffer.seek(0)
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_buffer.getvalue())
        tmp_file_path = tmp_file.name
    
    try:
        logger.info(f"✅ PDF WeasyPrint generado exitosamente para {client_name}")
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
            mimetype='application/pdf'
        )
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


def _convert_with_puppeteer(html_content: str, document_id: str, client_name: str):
    """🥈 Método 2: Puppeteer - Excelente renderizado"""
    import asyncio
    from pyppeteer import launch
    
    logger.info(f"🎯 Iniciando conversión Puppeteer para {client_name}")
    
    async def generate_pdf():
        browser = await launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        )
        
        try:
            page = await browser.newPage()
            await page.setContent(html_content, waitUntil='networkidle0')
            await page.setViewport({'width': 1920, 'height': 1080})
            
            # Generar PDF con formato A4
            pdf_buffer = await page.pdf({
                'format': 'A4',
                'margin': {
                    'top': '2cm',
                    'right': '2cm',
                    'bottom': '2cm',
                    'left': '2cm'
                },
                'printBackground': True,
                'preferCSSPageSize': True
            })
            
            return pdf_buffer
        
        finally:
            await browser.close()
    
    # Ejecutar función async
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        pdf_bytes = loop.run_until_complete(generate_pdf())
    finally:
        loop.close()
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        logger.info(f"✅ PDF Puppeteer generado exitosamente para {client_name}")
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
            mimetype='application/pdf'
        )
    finally:
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


def _convert_with_reportlab(html_content: str, document_id: str, client_name: str, structured_data: dict = None):
    """🥉 Método 3: ReportLab - Fallback confiable"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    import re
    from html import unescape
    
    logger.info(f"🎯 Iniciando conversión ReportLab para {client_name}")
    
    buffer = BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           topMargin=1*inch, bottomMargin=1*inch,
                           leftMargin=1*inch, rightMargin=1*inch)
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.Color(44/255, 95/255, 124/255),  # #2c5f7c (Sabra)
        alignment=1
    )
    
    # Construir contenido
    story = []
    
    # Header Sabra Corporation
    story.append(Paragraph("<b>sabra corporation</b>", title_style))
    story.append(Paragraph("Av. Principal, Mini Centro<br/>Principal Local 16, Lechería, Anzoátegui, 6016", styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Título
    story.append(Paragraph(f"PRESUPUESTO - {client_name.upper()}", title_style))
    story.append(Spacer(1, 20))
    
    # Procesar contenido HTML
    try:
        # Extraer texto limpio del HTML
        clean_content = re.sub(r'<[^>]+>', ' ', html_content)
        clean_content = unescape(clean_content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        # Información del cliente desde datos estructurados
        if structured_data and structured_data.get('client_info'):
            client_info = structured_data['client_info']
            if client_info.get('name'):
                story.append(Paragraph(f"<b>Para:</b> {client_info['name']}", styles['Normal']))
            if client_info.get('company'):
                story.append(Paragraph(f"<b>Empresa:</b> {client_info['company']}", styles['Normal']))
            if client_info.get('delivery_date'):
                story.append(Paragraph(f"<b>Fecha:</b> {client_info['delivery_date']}", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Costos desde datos estructurados
        if structured_data and structured_data.get('costs'):
            costs = structured_data['costs']
            if costs.get('products'):
                story.append(Paragraph("<b>Productos y Servicios:</b>", styles['Heading2']))
                
                # Crear tabla de productos
                table_data = [['Descripción', 'Cantidad', 'Precio Unit.', 'Total']]
                
                for product in costs['products']:
                    name = product.get('nombre', 'Producto')
                    quantity = str(product.get('cantidad', 1))
                    price = f"€{product.get('precio', 0):.2f}"
                    total = f"€{product.get('precio', 0) * product.get('cantidad', 1):.2f}"
                    table_data.append([name, quantity, price, total])
                
                # Crear tabla
                table = Table(table_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 20))
            
            # Total
            if costs.get('total'):
                story.append(Paragraph(f"<b>TOTAL: €{costs['total']:,.2f}</b>", styles['Heading2']))
                story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Documento generado para: {client_name}", styles['Normal']))
        story.append(Paragraph("AI-RFX System - Sabra Corporation", styles['Normal']))
    
    except Exception as extract_error:
        logger.warning(f"No se pudo extraer info detallada del HTML: {extract_error}")
        # Fallback básico
        story.append(Paragraph(f"Propuesta comercial para: {client_name}", styles['Normal']))
    
    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(buffer.getvalue())
        tmp_file_path = tmp_file.name
    
    try:
        logger.info(f"✅ PDF ReportLab generado exitosamente para {client_name}")
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.pdf",
            mimetype='application/pdf'
        )
    finally:
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


def _create_styled_html_download(html_content: str, document_id: str, client_name: str):
    """🆘 Método 4: HTML estilizado - Último recurso"""
    from datetime import datetime
    
    logger.info(f"🎯 Creando descarga HTML estilizada para {client_name}")
    
    # CSS profesional para el HTML
    professional_css = """
        @page { margin: 2cm; size: A4; }
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            line-height: 1.3; color: #000;
            font-size: 11px; background-color: white;
        }
        .notice {
            background: #fff3cd; border: 1px solid #ffeaa7;
            border-radius: 8px; padding: 15px; margin-bottom: 20px;
            text-align: center; color: #856404;
        }
        .company-name {
            font-size: 36px; font-weight: bold;
            color: #2c5f7c; margin-bottom: 2px;
            letter-spacing: -1px;
        }
        .main-table {
            width: 100%; border-collapse: collapse;
            border: 2px solid #000; margin: 10px 0;
        }
        .main-table th {
            background-color: #f0f0f0; font-weight: bold;
            padding: 8px 6px; text-align: center;
            border: 1px solid #000; font-size: 11px;
        }
        .main-table td {
            padding: 4px 6px; border: 1px solid #000;
            font-size: 10px; vertical-align: middle;
        }
        @media print { .notice { display: none; } }
    """
    
    # Crear documento HTML completo
    styled_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta Comercial - {client_name}</title>
    <style>{professional_css}</style>
</head>
<body>
    <div class="notice">
        <h4>📄 Propuesta Comercial - {client_name}</h4>
        <p><strong>Para convertir a PDF:</strong> Ctrl+P → Guardar como PDF</p>
        <p><strong>Configuración recomendada:</strong> A4, márgenes normales</p>
    </div>
    
    {html_content}
    
    <div style="margin-top: 50px; text-align: center; color: #64748b; font-size: 0.85em; border-top: 1px solid #e2e8f0; padding-top: 20px;">
        <p>Documento generado por AI-RFX System - Sabra Corporation</p>
        <p>Cliente: {client_name} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
</body>
</html>"""
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_file:
        tmp_file.write(styled_document)
        tmp_file_path = tmp_file.name
    
    try:
        logger.info(f"✅ HTML estilizado generado exitosamente para {client_name}")
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"propuesta-{client_name.replace(' ', '-').lower()}.html",
            mimetype='text/html'
        )
    finally:
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


def _get_pdf_styles() -> str:
    """Get CSS styles for PDF generation"""
    return """
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'DejaVu Sans', sans-serif;
            line-height: 1.6;
            color: #333;
        }
        .header {
            background: #667eea;
            color: white;
            padding: 20px;
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 24pt;
        }
        h1, h2, h3 { color: #2c3e50; }
        h2 { border-bottom: 2px solid #3498db; padding-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
    """ 