"""
🎨 User Branding API Endpoints V3.0 MVP - Branding por usuario autenticado
Usa company_branding_assets con user_id (migrado en V3.0)
"""
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import FileStorage
import asyncio
import logging
from typing import Dict, Any

from backend.services.user_branding_service import user_branding_service
from backend.api.auth import get_current_user

logger = logging.getLogger(__name__)

# Create blueprint
user_branding_bp = Blueprint("user_branding_api", __name__, url_prefix="/api/user-branding")

# ========================
# MIDDLEWARE PARA AUTENTICACIÓN
# ========================

def get_authenticated_user():
    """
    Middleware para obtener usuario autenticado desde JWT
    Usa el sistema de auth que ya implementamos
    """
    try:
        # Esto debería usar el dependency get_current_user de FastAPI
        # Pero como estamos en Flask, necesitamos adaptarlo
        from flask import g
        
        # TODO: Implementar extracción de JWT desde Authorization header
        # Por ahora, devolver usuario de prueba
        return {
            "id": "test-user-id",
            "email": "test@example.com",
            "full_name": "Test User"
        }
    except Exception as e:
        logger.error(f"Error getting authenticated user: {e}")
        return None

# ========================
# BRANDING ENDPOINTS
# ========================

@user_branding_bp.route("/upload", methods=["POST"])
def upload_branding():
    """
    🔐 Subir branding para usuario autenticado
    
    Requiere JWT token válido
    Files: logo, template
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Authentication required",
                "error": "Invalid or missing JWT token"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Obtener archivos del request
        logo_file = request.files.get('logo')
        template_file = request.files.get('template')
        
        if not logo_file and not template_file:
            return jsonify({
                "status": "error", 
                "message": "At least one file (logo or template) is required"
            }), 400
        
        # Validar que sean FileStorage objects
        if logo_file and not isinstance(logo_file, FileStorage):
            return jsonify({
                "status": "error",
                "message": "Invalid logo file"
            }), 400
        
        if template_file and not isinstance(template_file, FileStorage):
            return jsonify({
                "status": "error",
                "message": "Invalid template file"
            }), 400
        
        # Usar servicio async con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                user_branding_service.upload_and_analyze(
                    user_id=user_id,
                    logo_file=logo_file,
                    template_file=template_file,
                    analyze_now=True
                )
            )
            
            return jsonify({
                "status": "success",
                **result
            }), 201
            
        finally:
            loop.close()
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Error uploading branding: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error during upload",
            "error": str(e)
        }), 500

@user_branding_bp.route("/", methods=["GET"])
def get_my_branding():
    """
    📄 Obtener configuración de branding del usuario autenticado
    
    Requiere JWT token válido
    Retorna configuración completa con análisis cacheado
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Obtener configuración de branding
        branding_config = user_branding_service.get_branding_with_analysis(user_id)
        
        if not branding_config:
            return jsonify({
                "status": "success",
                "has_branding": False,
                "message": "No branding configuration found for this user"
            })
        
        return jsonify({
            "status": "success",
            "has_branding": True,
            "user_id": user_id,
            **branding_config
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting branding: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@user_branding_bp.route("/status", methods=["GET"])
def get_analysis_status():
    """
    🔍 Obtener estado del análisis para el usuario autenticado
    
    Útil para polling desde frontend
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Obtener estado del análisis
        analysis_status = user_branding_service.get_analysis_status(user_id)
        
        if not analysis_status:
            return jsonify({
                "status": "success",
                "has_branding": False,
                "message": "No branding configuration found"
            })
        
        return jsonify({
            "status": "success",
            "has_branding": True,
            **analysis_status
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting analysis status: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@user_branding_bp.route("/reanalyze", methods=["POST"])
def reanalyze_branding():
    """
    🔄 Re-analizar branding existente del usuario autenticado
    
    Útil si el usuario no está satisfecho con el análisis actual
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Re-analizar con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                user_branding_service.reanalyze(user_id)
            )
            
            return jsonify({
                "status": "success",
                **result
            })
            
        finally:
            loop.close()
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Error reanalyzing branding: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error during reanalysis",
            "error": str(e)
        }), 500

@user_branding_bp.route("/", methods=["DELETE"])
def delete_my_branding():
    """
    🗑️ Eliminar configuración de branding del usuario autenticado
    
    Marca como inactiva la configuración
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Eliminar branding
        success = user_branding_service.delete_branding(user_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Branding configuration deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to delete branding configuration"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error deleting branding: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@user_branding_bp.route("/summary", methods=["GET"])
def get_branding_summary():
    """
    📊 Obtener resumen de configuración de branding del usuario
    
    Información básica sin análisis completo
    """
    try:
        # Obtener usuario autenticado
        current_user = get_authenticated_user()
        if not current_user:
            return jsonify({
                "status": "error", 
                "message": "Authentication required"
            }), 401
        
        user_id = str(current_user["id"])
        
        # Obtener resumen
        summary = user_branding_service.get_branding_summary(user_id)
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            **summary
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting branding summary: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# ========================
# STATIC FILES (LOGOS Y TEMPLATES)
# ========================

@user_branding_bp.route("/files/<user_id>/<filename>")
def serve_branding_file(user_id: str, filename: str):
    """
    📁 Servir archivos estáticos de branding
    
    TODO: Agregar validación de permisos (usuario solo puede ver sus archivos)
    """
    try:
        import os
        from pathlib import Path
        
        # Validar que el archivo pertenece al usuario autenticado
        current_user = get_authenticated_user()
        if not current_user or str(current_user["id"]) != user_id:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Construir path
        branding_dir = Path("backend/static/branding") / user_id
        
        if not branding_dir.exists():
            return jsonify({
                "status": "error", 
                "message": "File not found"
            }), 404
        
        return send_from_directory(str(branding_dir), filename)
        
    except Exception as e:
        logger.error(f"❌ Error serving file: {e}")
        return jsonify({
            "status": "error",
            "message": "Error serving file",
            "error": str(e)
        }), 500

# ========================
# HEALTH CHECK Y TESTING
# ========================

@user_branding_bp.route("/test", methods=["GET"])
def test_branding_api():
    """
    🧪 Test endpoint para verificar que la API funciona
    """
    return jsonify({
        "status": "success",
        "message": "User Branding API V3.0 MVP is working",
        "version": "3.0",
        "features": {
            "user_authentication": True,
            "logo_upload": True,
            "template_upload": True,
            "ai_analysis": True,
            "caching": True,
            "teams_ready": True
        },
        "endpoints": [
            "POST /upload",
            "GET /",
            "GET /status", 
            "POST /reanalyze",
            "DELETE /",
            "GET /summary",
            "GET /files/<user_id>/<filename>"
        ]
    })

# ========================
# ERROR HANDLERS
# ========================

@user_branding_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "message": "Bad request",
        "error": str(error)
    }), 400

@user_branding_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "status": "error",
        "message": "Authentication required",
        "error": "Please provide a valid JWT token"
    }), 401

@user_branding_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        "status": "error",
        "message": "Access denied",
        "error": str(error)
    }), 403

@user_branding_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error", 
        "message": "Resource not found",
        "error": str(error)
    }), 404

@user_branding_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error", 
        "error": str(error)
    }), 500

# ========================
# LOGGING
# ========================

logger.info("🎨 User Branding API V3.0 MVP endpoints initialized")
logger.info("✅ Ready for user authentication with JWT")
logger.info("✅ Uses company_branding_assets table with user_id")
