"""
🚀 Flask Application Factory - New improved backend application
Uses the new architecture with proper separation of concerns
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_mail import Mail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import new architecture components
from backend.core.config import config, get_server_config
from backend.core.database import get_database_client
from backend.api.rfx import rfx_bp
from backend.api.proposals import proposals_bp
from backend.api.download import download_bp
from backend.api.pricing import pricing_bp
from backend.api.branding import branding_bp  # 🆕 Branding API
from backend.api.catalog_sync import catalog_bp  # 🛒 Product Catalog API (SYNC)

# 🔐 V3.0 Authentication & Security Blueprints
from backend.api.auth_flask import auth_bp  # ✅ Flask JWT Auth
from backend.api.rfx_secure_patch import rfx_secure_bp  # ✅ Secure RFX endpoints  
from backend.api.user_branding import user_branding_bp  # ✅ User branding
from backend.api.rfx_chat import rfx_chat_bp  # ✅ RFX Chat conversacional
from backend.api.organization import organization_bp  # ✅ Multi-tenant organizations
from backend.api.credits import credits_bp  # ✅ Credits management
from backend.api.contact import contact_bp  # ✅ Contact request emails
from backend.api.health import health_bp  # ✅ Health checks and monitoring
from backend.api.recommendations import recommendations_bp  # 🧠 AI Learning System recommendations
from backend.api.subscription import subscription_bp  # ✅ Plan requests & approval

from backend.models.rfx_models import RFXResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.is_development else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """
    🏗️ Application Factory - Creates Flask app with proper configuration
    Allows different configurations for development, testing, production
    """
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.secret_key
    app.config['MAX_CONTENT_LENGTH'] = config.file_upload.max_file_size
    
    # Configure Flask-Mail for email notifications
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budyai.com')
    
    # Initialize Flask-Mail
    mail = Mail(app)
    
    # Configure CORS - Temporary fix for production
    server_config = get_server_config()
    CORS(app, 
         origins=["*"],  # Temporary: Allow all origins
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # ✅ Added PATCH for independent pricing updates
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
         supports_credentials=True,
         expose_headers=["Content-Disposition", "Content-Type"]
    )
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Register health check
    _register_health_checks(app)
    
    # Log startup info
    logger.info(f"🚀 Application created successfully in {config.environment.value} mode")
    logger.info(f"🔌 CORS enabled for origins: {server_config.cors_origins}")
    
    return app


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints"""
    
    # 🔐 V3.0 SECURITY: Authentication endpoints (PRIORITY)
    app.register_blueprint(auth_bp)  # ✅ /api/auth/* - Login, signup, etc.
    app.register_blueprint(rfx_secure_bp)  # ✅ /api/rfx-secure/* - Secure RFX endpoints
    app.register_blueprint(user_branding_bp)  # ✅ /api/user-branding/* - User branding
    app.register_blueprint(rfx_chat_bp)  # ✅ /api/rfx/<id>/chat - Chat conversacional
    app.register_blueprint(organization_bp)  # ✅ /api/organization/* - Multi-tenant organizations
    app.register_blueprint(credits_bp)  # ✅ /api/credits/* - Credits management
    app.register_blueprint(contact_bp)  # ✅ /api/contact-request - Email notifications
    app.register_blueprint(health_bp)  # ✅ /api/health/* - Health checks and monitoring
    app.register_blueprint(recommendations_bp)  # 🧠 /api/recommendations/* - AI Learning System
    app.register_blueprint(subscription_bp)  # ✅ /api/subscription/* - Plan requests & approval
    
    # Original API endpoints (keeping for compatibility)
    app.register_blueprint(rfx_bp)  # ⚠️ INSECURE - use rfx_secure_bp instead
    app.register_blueprint(proposals_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(branding_bp)  # ⚠️ OLD - use user_branding_bp instead
    app.register_blueprint(catalog_bp)  # 🛒 Product Catalog Management
    
    # Legacy compatibility routes
    _register_legacy_routes(app)
    
    logger.info("✅ All blueprints registered successfully")
    logger.info("🔐 V3.0 Authentication endpoints available:")
    logger.info("   POST /api/auth/login")
    logger.info("   POST /api/auth/signup") 
    logger.info("   GET  /api/auth/me")
    logger.info("🔒 V3.0 Secure endpoints available:")
    logger.info("   GET  /api/rfx-secure/my-rfx")
    logger.info("   POST /api/rfx-secure/create")
    logger.info("   POST /api/user-branding/upload")


def _register_legacy_routes(app: Flask) -> None:
    """Register legacy routes for backward compatibility"""
    
    @app.route('/webhook/rfx', methods=['POST'])
    def legacy_webhook():
        """Legacy webhook endpoint - redirects to new API"""
        logger.info("📡 Legacy webhook endpoint called - redirecting to new API")
        from backend.api.rfx import process_rfx
        return process_rfx()
    
    @app.route('/api/rfx-history', methods=['GET'])
    def legacy_rfx_history():
        """Legacy RFX history endpoint - redirects to new API"""
        logger.info("📚 Legacy history endpoint called - redirecting to new API")
        from backend.api.rfx import get_rfx_history
        return get_rfx_history()
    
    @app.route('/api/download/<document_id>', methods=['GET'])
    def legacy_download_pdf(document_id: str):
        """Legacy PDF download endpoint - maintains existing functionality"""
        try:
            db_client = get_database_client()
            document = db_client.get_document_by_id(document_id)
            
            if not document:
                return jsonify({"error": "Document not found"}), 404
            
            # Return the content (for now as text, can be enhanced to return actual PDF)
            return jsonify({
                "content": document["contenido_markdown"],
                "filename": f"propuesta-{document_id}.txt"
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Error downloading document {document_id}: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"⚠️ Bad request: {error}")
        response = RFXResponse(
            status="error",
            message="Bad request",
            error=str(error.description) if hasattr(error, 'description') else "Invalid request format"
        )
        return jsonify(response.dict()), 400
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"⚠️ Not found: {error}")
        return jsonify({
            "status": "error",
            "message": "Resource not found",
            "error": "The requested resource does not exist"
        }), 404
    
    @app.errorhandler(413)
    def file_too_large(error):
        logger.warning(f"⚠️ File too large: {error}")
        max_size_mb = config.file_upload.max_file_size // (1024 * 1024)
        return jsonify({
            "status": "error",
            "message": f"File too large. Maximum size allowed: {max_size_mb}MB",
            "error": "File size exceeds limit"
        }), 413
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        logger.warning(f"⚠️ Validation error: {error}")
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "error": str(error.description) if hasattr(error, 'description') else "Data validation error"
        }), 422
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"❌ Internal server error: {error}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": "An unexpected error occurred" if config.is_production else str(error)
        }), 500


def _register_health_checks(app: Flask) -> None:
    """Register health check endpoints"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Basic health check endpoint"""
        return jsonify({
            "status": "healthy",
            "message": "AI-RFX Backend is running",
            "environment": config.environment.value,
            "version": "2.0"
        }), 200
    
    @app.route('/health/detailed', methods=['GET'])
    def detailed_health_check():
        """Detailed health check including dependencies"""
        health_status = {
            "status": "healthy",
            "message": "AI-RFX Backend detailed health check",
            "environment": config.environment.value,
            "version": "2.0",
            "checks": {}
        }
        
        # Check database connection
        try:
            db_client = get_database_client()
            db_healthy = db_client.health_check()
            health_status["checks"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "message": "Database connection OK" if db_healthy else "Database connection failed"
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}"
            }
        
        # Check OpenAI configuration
        try:
            openai_config = config.openai
            openai_config.validate()
            health_status["checks"]["openai"] = {
                "status": "healthy",
                "message": "OpenAI configuration valid"
            }
        except Exception as e:
            health_status["checks"]["openai"] = {
                "status": "unhealthy",
                "message": f"OpenAI configuration error: {str(e)}"
            }
        
        # Overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_status["checks"].values()
        )
        
        if not all_healthy:
            health_status["status"] = "degraded"
            health_status["message"] = "Some health checks failed"
        
        status_code = 200 if all_healthy else 503
        return jsonify(health_status), status_code


# Create application instance
app = create_app()


if __name__ == "__main__":
    """
    🚀 Development server entry point
    For production, use wsgi.py with a proper WSGI server
    """
    server_config = get_server_config()
    
    logger.info(f"🚀 Starting AI-RFX Backend on {server_config.host}:{server_config.port}")
    logger.info(f"🔧 Environment: {config.environment.value}")
    logger.info(f"🔍 Debug mode: {server_config.debug}")
    
    app.run(
        host=server_config.host,
        port=server_config.port,
        debug=server_config.debug,
        use_reloader=config.is_development
    )
