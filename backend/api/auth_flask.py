"""
🔐 Authentication API Endpoints - Flask Implementation
Sistema completo de autenticación con JWT para Flask
"""
from flask import Blueprint, request, jsonify, g
import asyncio
import logging
from typing import Dict, Any

from backend.services.auth_service_fixed import auth_service_fixed as auth_service
from backend.repositories.user_repository import user_repository
from backend.utils.auth_middleware import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")

# ========================
# VALIDATION HELPERS
# ========================

def validate_signup_data(data: Dict) -> Dict[str, Any]:
    """Validar datos de registro"""
    errors = []
    
    # Campos requeridos
    required_fields = ['email', 'password', 'full_name']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is required")
    
    if errors:
        return {"is_valid": False, "errors": errors}
    
    # Validar con servicio de auth
    validation = auth_service.validate_user_data(
        data['email'], 
        data['password'], 
        data['full_name']
    )
    
    return validation

def validate_login_data(data: Dict) -> Dict[str, Any]:
    """Validar datos de login"""
    errors = []
    
    if not data.get('email'):
        errors.append("email is required")
    if not data.get('password'):
        errors.append("password is required")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }

# ========================
# BACKGROUND TASKS (SIMULATED)
# ========================

def send_verification_email_sync(user_email: str, token: str):
    """
    Simular envío de email de verificación
    TODO: Integrar con servicio de email real
    """
    logger.info(f"📧 Would send verification email to {user_email}")
    logger.info(f"Verification link: https://rfxsystem.com/verify?token={token}")

def send_password_reset_email_sync(user_email: str, token: str):
    """
    Simular envío de email de reset
    TODO: Integrar con servicio de email real
    """
    logger.info(f"📧 Would send password reset email to {user_email}")
    logger.info(f"Reset link: https://rfxsystem.com/reset-password?token={token}")

# ========================
# AUTH ENDPOINTS
# ========================

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    🔐 Registrar nuevo usuario
    
    Body: {
        "email": "user@example.com",
        "password": "SecurePass123",
        "full_name": "Juan Pérez",
        "company_name": "Mi Empresa" (opcional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON body required"
            }), 400
        
        # Validar datos
        validation = validate_signup_data(data)
        if not validation['is_valid']:
            return jsonify({
                "status": "error",
                "message": "Validation failed",
                "errors": validation['errors']
            }), 400
        
        # Verificar si usuario ya existe
        existing_user = user_repository.get_by_email(data['email'])
        if existing_user:
            return jsonify({
                "status": "error",
                "message": "Email already registered"
            }), 400
        
        # Crear usuario con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(
                user_repository.create_user(
                    email=data['email'],
                    password=data['password'],
                    full_name=data['full_name'],
                    company_name=data.get('company_name')
                )
            )
            
            if not user:
                return jsonify({
                    "status": "error",
                    "message": "Failed to create user"
                }), 500
            
            # Generar token de verificación
            from uuid import UUID
            verification_token = loop.run_until_complete(
                user_repository.create_verification_token(UUID(user['id']))
            )
            
            if verification_token:
                # Enviar email (simulado)
                send_verification_email_sync(user['email'], verification_token)
            
        finally:
            loop.close()
        
        # Crear JWT token
        token_data = {"sub": str(user['id'])}
        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(str(user['id']))
        
        logger.info(f"✅ User registered successfully: {user['email']}")
        
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": auth_service.token_expire_minutes * 60,
            "user": {
                "id": str(user['id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "company_name": user.get('company_name'),
                "status": user['status'],
                "email_verified": user['email_verified']
            }
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error during signup: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error during registration",
            "error": str(e)
        }), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    🔐 Iniciar sesión
    
    Body: {
        "email": "user@example.com",
        "password": "SecurePass123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON body required"
            }), 400
        
        # Validar datos
        validation = validate_login_data(data)
        if not validation['is_valid']:
            return jsonify({
                "status": "error",
                "message": "Validation failed",
                "errors": validation['errors']
            }), 400
        
        # Obtener usuario por email
        user = user_repository.get_by_email(data['email'])
        if not user:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Verificar contraseña
        if not auth_service.verify_password(data['password'], user['password_hash']):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Verificar que la cuenta no esté suspendida
        if user['status'] == 'inactive':
            return jsonify({
                "status": "error",
                "message": "Account inactive"
            }), 401
        
        # Actualizar last login
        from uuid import UUID
        user_repository.update_last_login(UUID(user['id']))
        
        # Verificar si tiene branding configurado
        has_branding = user_repository.has_branding_configured(UUID(user['id']))
        
        # Crear JWT token
        token_data = {"sub": str(user['id'])}
        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(str(user['id']))
        
        logger.info(f"✅ User logged in successfully: {user['email']}")
        
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": auth_service.token_expire_minutes * 60,
            "user": {
                "id": str(user['id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "company_name": user.get('company_name'),
                "status": user['status'],
                "email_verified": user['email_verified'],
                "has_branding": has_branding
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error during login: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error during login",
            "error": str(e)
        }), 500

@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_me():
    """
    🔐 Obtener información del usuario actual
    
    Headers: Authorization: Bearer <token>
    """
    try:
        current_user = get_current_user()
        
        # Verificar si tiene branding configurado
        from uuid import UUID
        has_branding = user_repository.has_branding_configured(UUID(current_user['id']))
        
        return jsonify({
            "status": "success",
            "user": {
                "id": str(current_user['id']),
                "email": current_user['email'],
                "full_name": current_user['full_name'],
                "company_name": current_user.get('company_name'),
                "phone": current_user.get('phone'),
                "status": current_user['status'],
                "email_verified": current_user['email_verified'],
                "has_branding": has_branding,
                "last_login_at": current_user['last_login_at'].isoformat() if current_user.get('last_login_at') else None,
                "created_at": current_user['created_at'].isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting user info: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    🔐 Renovar access token usando refresh token
    
    Body: {
        "refresh_token": "eyJ0eXAiOiJKV1Q..."
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('refresh_token'):
            return jsonify({
                "status": "error",
                "message": "refresh_token is required"
            }), 400
        
        new_access_token = auth_service.refresh_access_token(data['refresh_token'])
        
        if not new_access_token:
            return jsonify({
                "status": "error",
                "message": "Invalid refresh token"
            }), 401
        
        # Obtener user ID del refresh token para respuesta
        payload = auth_service.decode_token(data['refresh_token'])
        user_id = payload.get("sub") if payload else None
        
        return jsonify({
            "status": "success",
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": auth_service.token_expire_minutes * 60,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error refreshing token: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# ========================
# EMAIL VERIFICATION
# ========================

@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """
    📧 Verificar email usando token enviado por email
    
    Body: {
        "token": "verification_token"
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('token'):
            return jsonify({
                "status": "error",
                "message": "token is required"
            }), 400
        
        # Usar asyncio para verificación
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(
                user_repository.verify_email(data['token'])
            )
        finally:
            loop.close()
        
        if not success:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired verification token"
            }), 400
        
        return jsonify({
            "status": "success",
            "message": "Email verified successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error verifying email: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@auth_bp.route("/resend-verification", methods=["POST"])
@jwt_required
def resend_verification_email():
    """
    📧 Reenviar email de verificación
    
    Headers: Authorization: Bearer <token>
    """
    try:
        current_user = get_current_user()
        
        if current_user['email_verified']:
            return jsonify({
                "status": "error",
                "message": "Email already verified"
            }), 400
        
        # Generar nuevo token con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from uuid import UUID
            verification_token = loop.run_until_complete(
                user_repository.create_verification_token(UUID(current_user['id']))
            )
        finally:
            loop.close()
        
        if verification_token:
            send_verification_email_sync(current_user['email'], verification_token)
        
        return jsonify({
            "status": "success",
            "message": "Verification email sent"
        })
        
    except Exception as e:
        logger.error(f"❌ Error resending verification: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# ========================
# PASSWORD RESET
# ========================

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    🔑 Solicitar reset de contraseña
    
    Body: {
        "email": "user@example.com"
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({
                "status": "error",
                "message": "email is required"
            }), 400
        
        # Generar token de reset con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            reset_token = loop.run_until_complete(
                user_repository.create_password_reset_token(data['email'])
            )
        finally:
            loop.close()
        
        if reset_token:
            send_password_reset_email_sync(data['email'], reset_token)
        
        # Siempre retornar éxito para evitar enumeración de usuarios
        return jsonify({
            "status": "success",
            "message": "If the email exists, a reset link has been sent"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in forgot password: {e}")
        # No revelar errores internos
        return jsonify({
            "status": "success",
            "message": "If the email exists, a reset link has been sent"
        })

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    🔑 Confirmar reset de contraseña con token
    
    Body: {
        "token": "reset_token",
        "new_password": "NewSecurePass123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON body required"
            }), 400
        
        if not data.get('token') or not data.get('new_password'):
            return jsonify({
                "status": "error",
                "message": "token and new_password are required"
            }), 400
        
        # Validar nueva contraseña
        password_validation = auth_service.validate_password_strength(data['new_password'])
        if not password_validation['is_valid']:
            return jsonify({
                "status": "error",
                "message": "Password requirements not met",
                "errors": password_validation['errors']
            }), 400
        
        # Resetear contraseña con asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(
                user_repository.reset_password_with_token(
                    data['token'], 
                    data['new_password']
                )
            )
        finally:
            loop.close()
        
        if not success:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired reset token"
            }), 400
        
        return jsonify({
            "status": "success",
            "message": "Password reset successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error resetting password: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# ========================
# HEALTH CHECK
# ========================

@auth_bp.route("/health", methods=["GET"])
def health_check():
    """
    🧪 Health check endpoint
    """
    return jsonify({
        "status": "healthy",
        "service": "authentication_flask",
        "version": "3.0",
        "framework": "Flask"
    })

# ========================
# ERROR HANDLERS
# ========================

@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "message": "Bad request",
        "error": str(error)
    }), 400

@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "status": "error",
        "message": "Authentication required",
        "error": "Please provide a valid JWT token"
    }), 401

@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error", 
        "error": str(error)
    }), 500

# ========================
# LOGGING
# ========================

logger.info("🔐 Flask Authentication API endpoints initialized")
logger.info("✅ All endpoints use Flask (no FastAPI hybrid)")
