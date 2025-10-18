"""
🎨 Branding API Endpoints - Gestión de logos y templates personalizados
Endpoints para upload, consulta y gestión de branding corporativo
"""
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

branding_bp = Blueprint("branding_api", __name__, url_prefix="/api/branding")


def format_datetime(dt: Any) -> Optional[str]:
    """Formatea datetime de manera segura, manejando strings y objetos datetime"""
    if not dt:
        return None
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    if isinstance(dt, str):
        # Si ya es string, devolverlo tal como está
        return dt
    return str(dt)


@branding_bp.route("/upload", methods=["POST"])
def upload_branding():
    """
    Sube logo y/o template para una empresa
    Lanza análisis asíncrono con GPT-4 Vision
    
    Form Data:
        company_id: UUID de la empresa (requerido)
        logo: Archivo de logo (opcional)
        template: Archivo de template (opcional)
        analyze_now: Boolean, default true (opcional)
    
    Returns:
        JSON con URLs de archivos y estado de análisis
    """
    try:
        # Validar company_id
        company_id = request.form.get('company_id')
        if not company_id:
            return jsonify({
                "status": "error",
                "message": "company_id is required"
            }), 400
        
        # Obtener archivos
        logo_file = request.files.get('logo')
        template_file = request.files.get('template')
        
        if not logo_file and not template_file:
            return jsonify({
                "status": "error",
                "message": "At least one file (logo or template) is required"
            }), 400
        
        # Opción de análisis
        analyze_now = request.form.get('analyze_now', 'true').lower() == 'true'
        
        # Procesar upload
        from backend.services.optimized_branding_service import OptimizedUserBrandingService
        service = OptimizedUserBrandingService()
        
        # Ejecutar upload asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.upload_and_analyze(
                    company_id=company_id,
                    logo_file=logo_file,
                    template_file=template_file,
                    analyze_now=analyze_now
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "status": "success",
            **result
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error uploading branding: {e}", exc_info=True)
        return jsonify({
            "message": "Internal server error",
            "error": str(e)
        }), 500


@branding_bp.route("/<user_id>", methods=["GET"])
def get_branding(user_id: str):
    """
    Obtiene branding completo con análisis cacheado
    
    Returns:
        JSON con branding data y análisis (logo + template)
    """
    try:
        from backend.services.user_branding_service import user_branding_service
        
        branding = user_branding_service.get_branding_with_analysis(user_id)
        
        if not branding:
            return jsonify({
                "status": "not_found",
                "message": f"No branding found for user: {user_id}"
            }), 404
        
        # Formatear fechas
        for field in ['logo_uploaded_at', 'template_uploaded_at', 'analysis_started_at', 'created_at', 'updated_at']:
            if field in branding and branding[field]:
                branding[field] = format_datetime(branding[field])
        
        return jsonify({
            "status": "success",
            **branding
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting branding for user {user_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@branding_bp.route("/<user_id>/template", methods=["GET"])
def get_html_template(user_id: str):
    """
    🆕 V3.2: Obtiene template HTML generado (si existe)
    
    Args:
        user_id: ID del usuario
        
    Returns:
        JSON con template HTML y placeholders o status not_generated
    """
    try:
        from backend.services.user_branding_service import user_branding_service
        
        branding = user_branding_service.get_branding_with_analysis(user_id)
        
        if not branding:
            return jsonify({
                "status": "no_branding",
                "message": f"No branding found for user: {user_id}",
                "has_template": False
            }), 404
        
        # Verificar si existe template HTML en template_analysis
        template_analysis = branding.get('template_analysis', {})
        html_template = template_analysis.get('html_template')
        placeholders = template_analysis.get('placeholders', [])
        template_version = template_analysis.get('template_version', 'unknown')
        
        if html_template:
            return jsonify({
                "status": "ready",
                "has_template": True,
                "html_template": html_template,
                "placeholders": placeholders,
                "template_version": template_version,
                "analysis_status": branding.get('analysis_status'),
                "message": f"Template ready with {len(placeholders)} placeholders"
            }), 200
        else:
            return jsonify({
                "status": "not_generated",
                "has_template": False,
                "analysis_status": branding.get('analysis_status'),
                "message": "Template analysis completed but no HTML template generated. Re-analyze template to generate HTML."
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting HTML template for user {user_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@branding_bp.route("/analysis-status/<company_id>", methods=["GET"])
def get_analysis_status(company_id: str):
    """
    Obtiene solo el estado del análisis
    Útil para polling desde frontend
    
    Args:
        company_id: UUID de la empresa
    
    Returns:
        JSON con estado del análisis
    """
    try:
        from backend.services.optimized_branding_service import OptimizedUserBrandingService
        service = OptimizedUserBrandingService()
        
        status = service.get_analysis_status(company_id)
        
        if not status:
            return jsonify({
                "status": "not_found",
                "message": "No branding found for this company"
            }), 404
        
        # Calcular progreso estimado
        analysis_status = status.get('analysis_status')
        progress_message = {
            'pending': 'Analysis not started',
            'analyzing': 'Analyzing logo and template with AI...',
            'completed': 'Analysis completed successfully',
            'failed': 'Analysis failed'
        }.get(analysis_status, 'Unknown status')
        
        started_at = status.get('analysis_started_at')
        updated_at = status.get('updated_at')

        return jsonify({
            "status": "success",
            "analysis_status": analysis_status,
            "progress": progress_message,
            "error": status.get('analysis_error'),
            "started_at": format_datetime(started_at),
            "updated_at": format_datetime(updated_at)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analysis status for {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve analysis status",
            "error": str(e)
        }), 500


@branding_bp.route("/reanalyze/<company_id>", methods=["POST"])
def reanalyze_branding(company_id: str):
    """
    Re-analiza branding existente
    Útil si el usuario no está satisfecho con el análisis
    
    Args:
        company_id: UUID de la empresa
    
    Returns:
        JSON con confirmación de re-análisis
    """
    try:
        from backend.services.optimized_branding_service import OptimizedUserBrandingService
        service = OptimizedUserBrandingService()
        
        # Ejecutar re-análisis asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.reanalyze(company_id)
            )
        finally:
            loop.close()
        
        return jsonify({
            "status": "success",
            **result
        }), 200
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Error re-analyzing branding for {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to re-analyze branding",
            "error": str(e)
        }), 500


@branding_bp.route("/<company_id>", methods=["DELETE"])
def delete_branding(company_id: str):
    """
    Desactiva configuración de branding
    No elimina archivos físicos
    
    Args:
        company_id: UUID de la empresa
    
    Returns:
        JSON con confirmación
    """
    try:
        from backend.services.optimized_branding_service import OptimizedUserBrandingService
        service = OptimizedUserBrandingService()
        
        service.delete_branding(company_id)
        
        return jsonify({
            "status": "success",
            "message": "Branding deactivated successfully",
            "company_id": company_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting branding for {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to delete branding",
            "error": str(e)
        }), 500


@branding_bp.route("/files/<user_id>/<file_type>", methods=["GET"])
def serve_branding_file(user_id: str, file_type: str):
    """
    Servir archivos estáticos de branding (logo o template)
    
    Args:
        user_id: UUID del usuario
        file_type: 'logo' o 'template'
    
    Returns:
        Archivo estático o error 404
    """
    try:
        import os
        from pathlib import Path
        
        # Validar tipo de archivo
        if file_type not in ['logo', 'template']:
            return jsonify({
                "status": "error",
                "message": "Invalid file type. Must be 'logo' or 'template'"
            }), 400
        
        # Construir path al directorio de branding del usuario
        # Usar path absoluto desde el directorio del proyecto
        import os
        project_root = Path(os.getcwd())
        branding_dir = project_root / "backend" / "static" / "branding" / user_id
        logger.info(f"🔍 Looking for branding directory: {branding_dir.absolute()}")
        logger.info(f"🔍 Current working directory: {project_root}")
        
        if not branding_dir.exists():
            logger.warning(f"Branding directory not found: {branding_dir.absolute()}")
            return jsonify({
                "status": "error", 
                "message": "User branding directory not found"
            }), 404
        
        # Buscar archivo del tipo solicitado
        # Los archivos pueden tener diferentes extensiones
        possible_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.pdf', '.webp']
        found_file = None
        
        logger.info(f"🔍 Searching for {file_type} files in {branding_dir}")
        for ext in possible_extensions:
            potential_file = branding_dir / f"{file_type}{ext}"
            logger.debug(f"  Checking: {potential_file}")
            if potential_file.exists():
                found_file = potential_file
                logger.info(f"✓ Found file: {found_file}")
                break
        
        if not found_file:
            logger.warning(f"File not found: {file_type} for user {user_id} in {branding_dir}")
            # List available files for debugging
            if branding_dir.exists():
                available_files = list(branding_dir.glob("*"))
                logger.info(f"Available files: {available_files}")
            return jsonify({
                "status": "error",
                "message": f"{file_type.title()} file not found for this user"
            }), 404
        
        logger.info(f"📁 Serving branding file: {found_file}")
        return send_from_directory(str(branding_dir), found_file.name)
        
    except Exception as e:
        logger.error(f"Error serving branding file: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error serving file",
            "error": str(e)
        }), 500


@branding_bp.route("/test", methods=["GET"])
def test_branding_api():
    """
    Endpoint de prueba para verificar que el API está funcionando
    """
    return jsonify({
        "status": "success",
        "message": "Branding API is working",
        "endpoints": {
            "upload": "POST /api/branding/upload",
            "get": "GET /api/branding/<company_id>",
            "status": "GET /api/branding/analysis-status/<company_id>",
            "reanalyze": "POST /api/branding/reanalyze/<company_id>",
            "delete": "DELETE /api/branding/<company_id>",
            "files": "GET /api/branding/files/<user_id>/<file_type>"
        }
    }), 200
