"""
🎨 Branding API Endpoints - Gestión de logos y templates personalizados
Endpoints para upload, consulta y gestión de branding corporativo
"""
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import asyncio
import logging

logger = logging.getLogger(__name__)

branding_bp = Blueprint("branding_api", __name__, url_prefix="/api/branding")


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
        from backend.services.optimized_branding_service import OptimizedBrandingService
        service = OptimizedBrandingService()
        
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
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500


@branding_bp.route("/<company_id>", methods=["GET"])
def get_branding(company_id: str):
    """
    Obtiene configuración de branding con análisis cacheado
    
    Args:
        company_id: UUID de la empresa
    
    Returns:
        JSON con URLs, análisis de logo y template
    """
    try:
        from backend.services.optimized_branding_service import OptimizedBrandingService
        service = OptimizedBrandingService()
        
        branding = service.get_branding_with_analysis(company_id)
        
        if not branding:
            return jsonify({
                "status": "success",
                "message": "No branding configured for this company",
                "company_id": company_id,
                "has_branding": False
            }), 200
        
        return jsonify({
            "status": "success",
            "company_id": company_id,
            "has_branding": True,
            "logo_url": branding.get('logo_url'),
            "template_url": branding.get('template_url'),
            "logo_analysis": branding.get('logo_analysis', {}),
            "template_analysis": branding.get('template_analysis', {}),
            "analysis_status": branding.get('analysis_status'),
            "analysis_error": branding.get('analysis_error'),
            "created_at": branding.get('created_at').isoformat() if branding.get('created_at') else None,
            "updated_at": branding.get('updated_at').isoformat() if branding.get('updated_at') else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting branding for {company_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve branding",
            "error": str(e)
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
        from backend.services.optimized_branding_service import OptimizedBrandingService
        service = OptimizedBrandingService()
        
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
        
        return jsonify({
            "status": "success",
            "analysis_status": analysis_status,
            "progress": progress_message,
            "error": status.get('analysis_error'),
            "started_at": status.get('analysis_started_at').isoformat() if status.get('analysis_started_at') else None,
            "completed_at": status.get('analysis_completed_at').isoformat() if status.get('analysis_completed_at') else None
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
        from backend.services.optimized_branding_service import OptimizedBrandingService
        service = OptimizedBrandingService()
        
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
        from backend.services.optimized_branding_service import OptimizedBrandingService
        service = OptimizedBrandingService()
        
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
            "delete": "DELETE /api/branding/<company_id>"
        }
    }), 200
