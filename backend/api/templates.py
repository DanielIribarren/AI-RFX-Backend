"""
🎨 Templates API Endpoints - Lista templates disponibles para presupuestos
"""
from flask import Blueprint, jsonify
import logging

from backend.prompts.template_config import get_all_templates_metadata

logger = logging.getLogger(__name__)

templates_bp = Blueprint("templates_api", __name__, url_prefix="/api/templates")


@templates_bp.route("", methods=["GET"])
def list_templates():
    """
    Lista todos los templates de presupuesto disponibles.
    Retorna metadata para el frontend (nombre, emoji, colores, descripción).
    """
    try:
        templates = get_all_templates_metadata()
        
        return jsonify({
            "status": "success",
            "message": f"{len(templates)} templates disponibles",
            "data": templates
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error listing templates: {e}")
        return jsonify({
            "status": "error",
            "message": "Error al obtener templates",
            "error": str(e)
        }), 500
