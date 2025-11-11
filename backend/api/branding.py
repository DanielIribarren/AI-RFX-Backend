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
    Sube logo y/o template para un usuario
    Lanza análisis asíncrono con GPT-4 Vision (UN SOLO PASO)
    
    Form Data:
        user_id: UUID del usuario (requerido)
        logo: Archivo de logo (opcional)
        template: Archivo de template (opcional)
        analyze_now: Boolean, default true (opcional)
    
    Returns:
        JSON con URLs de archivos y estado de análisis
    """
    try:
        # Validar user_id (acepta también company_id para compatibilidad)
        user_id = request.form.get('user_id') or request.form.get('company_id')
        if not user_id:
            return jsonify({
                "status": "error",
                "message": "user_id or company_id is required"
            }), 400
        
        logger.info(f"📤 Upload request for user: {user_id}")
        
        # Obtener archivos
        logo_file = request.files.get('logo')
        template_file = request.files.get('template')
        
        logger.info(f"📁 Files received - Logo: {bool(logo_file)}, Template: {bool(template_file)}")
        
        if not logo_file and not template_file:
            logger.warning(f"❌ No files provided. Form keys: {list(request.form.keys())}, File keys: {list(request.files.keys())}")
            return jsonify({
                "status": "error",
                "message": "At least one file (logo or template) is required"
            }), 400
        
        # Opción de análisis
        analyze_now = request.form.get('analyze_now', 'true').lower() == 'true'
        
        # Procesar upload con servicio refactorizado
        from backend.services.user_branding_service import UserBrandingService
        service = UserBrandingService()
        
        # Ejecutar upload asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.upload_and_analyze(
                    user_id=user_id,
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
    🆕 V3.2: Obtiene template HTML generado con logo en base64
    
    Args:
        user_id: ID del usuario
        
    Returns:
        JSON con template HTML completo (con logo en base64)
    """
    try:
        from backend.core.database import get_database_client
        
        db = get_database_client()
        
        # Obtener branding del usuario directamente desde BD
        result = db.client.table("company_branding_assets")\
            .select("html_template, analysis_status, template_analysis, updated_at")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()
        
        if not result.data:
            return jsonify({
                "status": "no_branding",
                "message": f"No branding found for user: {user_id}",
                "has_template": False
            }), 404
        
        branding = result.data[0]
        
        # Obtener HTML template del campo correcto
        html_template = branding.get('html_template')
        analysis_status = branding.get('analysis_status')
        
        if html_template:
            logger.info(f"✅ HTML template retrieved for user: {user_id} - Length: {len(html_template)} chars")
            
            return jsonify({
                "status": "ready",
                "has_template": True,
                "html_template": html_template,
                "analysis_status": analysis_status,
                "generated_at": branding.get('updated_at'),
                "message": "Template ready with logo in base64"
            }), 200
        else:
            return jsonify({
                "status": "not_generated",
                "has_template": False,
                "analysis_status": analysis_status,
                "message": "No HTML template generated yet. Please upload a template first."
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting HTML template for user {user_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@branding_bp.route("/analysis-status/<user_id>", methods=["GET"])
def get_analysis_status(user_id: str):
    """
    Obtiene solo el estado del análisis
    Útil para polling desde frontend
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        JSON con estado del análisis
    """
    try:
        from backend.services.user_branding_service import UserBrandingService
        service = UserBrandingService()
        
        status = service.get_analysis_status(user_id)
        
        if not status:
            return jsonify({
                "status": "not_found",
                "message": "No branding found for this user"
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
        logger.error(f"Error getting analysis status for {user_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve analysis status",
            "error": str(e)
        }), 500


# NOTA: Endpoint reanalyze eliminado - funcionalidad no necesaria en flujo simplificado


@branding_bp.route("/<user_id>", methods=["DELETE"])
def delete_branding(user_id: str):
    """
    Desactiva configuración de branding
    No elimina archivos físicos
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        JSON con confirmación
    """
    try:
        from backend.services.user_branding_service import UserBrandingService
        service = UserBrandingService()
        
        service.delete_branding(user_id)
        
        return jsonify({
            "status": "success",
            "message": "Branding deactivated successfully",
            "user_id": user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting branding for {user_id}: {e}")
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
        # Usar path absoluto desde el directorio del proyecto usando __file__
        import os
        from pathlib import Path
        
        # Get the project root by going up from this file's location
        # backend/api/branding.py -> backend/ -> project_root/
        current_file_dir = Path(__file__).parent  # backend/api/
        backend_dir = current_file_dir.parent     # backend/
        project_root = backend_dir.parent         # project_root/
        
        branding_dir = project_root / "backend" / "static" / "branding" / user_id
        logger.info(f"🔍 Project root: {project_root.absolute()}")
        logger.info(f"🔍 Looking for branding directory: {branding_dir.absolute()}")
        logger.info(f"🔍 Current file location: {__file__}")
        
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


@branding_bp.route("/default/logo", methods=["GET"])
def serve_default_logo():
    """
    Servir logo por defecto de Sabra Corporation
    Usado cuando el usuario no tiene branding configurado
    
    Returns:
        Archivo PNG del logo de Sabra
    """
    try:
        import os
        from pathlib import Path
        
        # Get the project root by going up from this file's location
        # backend/api/branding.py -> backend/ -> project_root/
        current_file_dir = Path(__file__).parent  # backend/api/
        backend_dir = current_file_dir.parent     # backend/
        project_root = backend_dir.parent         # project_root/
        
        # Path al logo por defecto
        default_dir = project_root / "backend" / "static" / "default"
        logo_file = default_dir / "sabra_logo.png"
        
        logger.info(f"🔍 Project root: {project_root.absolute()}")
        logger.info(f"📁 Serving default logo: {logo_file}")
        logger.info(f"🔍 Current file location: {__file__}")
        
        if not logo_file.exists():
            logger.error(f"Default logo not found: {logo_file}")
            return jsonify({
                "status": "error",
                "message": "Default logo not found"
            }), 404
        
        return send_from_directory(str(default_dir), "sabra_logo.png")
        
    except Exception as e:
        logger.error(f"Error serving default logo: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error serving default logo",
            "error": str(e)
        }), 500


@branding_bp.route("/<user_id>/update", methods=["PUT"])
def update_branding(user_id: str):
    """
    🔄 Actualizar branding existente
    Solo actualiza archivos y re-análisis si se proporcionan
    
    Form Data:
        logo: Archivo de logo (opcional)
        template: Archivo de template (opcional)
        reanalyze: Boolean, default false (opcional)
    
    Returns:
        JSON con URLs actualizadas y estado de análisis
    """
    try:
        logger.info(f"🔄 Updating branding for user: {user_id}")
        
        # Verificar que existe branding para este usuario
        from backend.services.user_branding_service import UserBrandingService
        service = UserBrandingService()
        
        # Obtener archivos
        logo_file = request.files.get('logo')
        template_file = request.files.get('template')
        
        if not logo_file and not template_file:
            return jsonify({
                "status": "error",
                "message": "At least one file (logo or template) is required for update"
            }), 400
        
        # Opción de re-análisis
        reanalyze = request.form.get('reanalyze', 'false').lower() == 'true'
        
        # Ejecutar update asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.update_branding(
                    user_id=user_id,
                    logo_file=logo_file,
                    template_file=template_file,
                    reanalyze=reanalyze
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
        }), 404
        
    except Exception as e:
        logger.error(f"Error updating branding: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500


@branding_bp.route("/create", methods=["POST"])
def create_branding():
    """
    🆕 Crear nuevo branding para usuario sin branding existente
    
    Form Data:
        user_id: UUID del usuario (requerido)
        logo: Archivo de logo (opcional)
        template: Archivo de template (opcional)
        analyze_now: Boolean, default true (opcional)
    
    Returns:
        JSON con URLs de archivos y estado de análisis
    """
    try:
        # Validar user_id
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({
                "status": "error",
                "message": "user_id is required"
            }), 400
        
        logger.info(f"🆕 Creating new branding for user: {user_id}")
        
        # Verificar que NO existe branding para este usuario
        from backend.services.user_branding_service import UserBrandingService
        service = UserBrandingService()
        
        # Verificar existencia
        existing = service.get_branding(user_id)
        if existing and existing.get('user_id'):
            return jsonify({
                "status": "error",
                "message": "Branding already exists for this user. Use PUT /api/branding/<user_id>/update instead"
            }), 409
        
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
        
        # Ejecutar create asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.upload_and_analyze(
                    user_id=user_id,
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
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating branding: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500


@branding_bp.route("/test", methods=["GET"])
def test_branding_api():
    """
    Endpoint de prueba para verificar que el API está funcionando
    """
    return jsonify({
        "status": "success",
        "message": "Branding API is working - Refactored (UN SOLO PASO)",
        "endpoints": {
            "create": "POST /api/branding/create (user_id) - Crear nuevo branding",
            "update": "PUT /api/branding/<user_id>/update - Actualizar branding existente",
            "upload": "POST /api/branding/upload (user_id o company_id) - Upload genérico",
            "get": "GET /api/branding/<user_id>",
            "status": "GET /api/branding/analysis-status/<user_id>",
            "html": "GET /api/branding/<user_id>/html",
            "delete": "DELETE /api/branding/<user_id>",
            "files": "GET /api/branding/files/<user_id>/<file_type>",
            "default_logo": "GET /api/branding/default/logo"
        },
        "note": "Sistema usa Supabase client para guardar (como productos)"
    }), 200
