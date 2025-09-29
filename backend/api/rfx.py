"""
🔄 RFX API Legacy Compatibility Layer
Redirects legacy RFX endpoints to modern Projects/Proposals APIs
Maintains backward compatibility for frontend during migration
"""
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

# Create blueprint for legacy compatibility
rfx_bp = Blueprint("rfx_api", __name__, url_prefix="/api/rfx")


@rfx_bp.route("/process", methods=["POST"])
def process_rfx():
    """
    🔄 REDIRECT: Legacy RFX endpoint → Modern Projects API
    This endpoint redirects to /api/projects/ for new SaaS workflow
    Maintains backward compatibility for frontend
    """
    logger.info("🔄 Legacy /api/rfx/process called - redirecting to /api/projects/")
    
    # Import projects function to avoid circular imports
    from backend.api.projects import create_project
    
    # Call the modern projects endpoint directly
    return create_project()


@rfx_bp.route("/recent", methods=["GET"])
def get_recent_rfx():
    """
    🔄 REDIRECT: Legacy recent RFX → Modern Projects recent
    """
    logger.info("🔄 Legacy /api/rfx/recent called - redirecting to /api/projects/recent")
    
    from backend.api.projects import get_recent_projects
    return get_recent_projects()


@rfx_bp.route("/health", methods=["GET"])
def rfx_health():
    """Health check for legacy RFX endpoints"""
    return jsonify({
        "status": "ok",
        "message": "RFX Legacy Compatibility Layer is running",
        "redirect_info": "All RFX endpoints redirect to modern Projects/Proposals APIs"
    }), 200
