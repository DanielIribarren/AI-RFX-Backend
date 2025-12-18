"""
🔐 Flask JWT Middleware - Autenticación para Flask (no FastAPI)
Middleware para validar JWT tokens en endpoints Flask
"""
from functools import wraps
from flask import request, jsonify, g
import logging
from typing import Optional, Dict, Any

from backend.services.auth_service_fixed import decode_token_fixed as decode_token
from backend.repositories.user_repository import user_repository

logger = logging.getLogger(__name__)

def jwt_required(f):
    """
    Decorator para endpoints que requieren autenticación JWT
    
    Usage:
        @app.route("/protected")
        @jwt_required
        def protected_endpoint():
            current_user = g.current_user  # Usuario autenticado disponible
            return {"user_id": current_user["id"]}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        current_user = None
        
        # Extraer token del header Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                # Format: "Bearer <token>"
                parts = auth_header.split()
                if parts[0].lower() == 'bearer' and len(parts) == 2:
                    token = parts[1]
                    logger.debug(f"🔑 JWT token received (length: {len(token)})")
                else:
                    logger.warning(f"❌ JWT Auth: Invalid header format - parts: {len(parts)}")
                    return jsonify({
                        "status": "error",
                        "message": "Invalid Authorization header format. Use 'Bearer <token>'"
                    }), 401
            except Exception as e:
                logger.warning(f"❌ JWT Auth: Header parsing error - {e}")
                return jsonify({
                    "status": "error",
                    "message": "Invalid Authorization header"
                }), 401
        
        if not token:
            logger.warning(f"❌ JWT Auth: No token provided - endpoint: {request.endpoint}")
            return jsonify({
                "status": "error",
                "message": "Authentication required",
                "error": "Missing Authorization header"
            }), 401
        
        try:
            # Decodificar token
            payload = decode_token(token)
            if not payload:
                return jsonify({
                    "status": "error",
                    "message": "Invalid or expired token"
                }), 401
            
            # Obtener user_id del payload
            user_id = payload.get("sub")
            if not user_id:
                return jsonify({
                    "status": "error", 
                    "message": "Invalid token payload"
                }), 401
            
            # Obtener usuario de la base de datos
            from uuid import UUID
            user = user_repository.get_by_id(UUID(user_id))
            
            if not user:
                logger.warning(f"❌ JWT Auth: User not found - user_id: {user_id}")
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 401
            
            user_status = user.get('status', 'unknown')
            if user_status not in ['active', 'pending_verification']:
                logger.warning(f"❌ JWT Auth: User inactive - user_id: {user_id}, status: {user_status}")
                return jsonify({
                    "status": "error",
                    "message": "User account is inactive"
                }), 401
            
            # Guardar usuario en Flask g object
            g.current_user = user
            
            logger.debug(f"✅ Authenticated user: {user['email']} (ID: {user['id']}, status: {user_status})")
            
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Invalid user ID format"
            }), 401
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return jsonify({
                "status": "error",
                "message": "Authentication failed",
                "error": str(e)
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Obtener usuario actual desde Flask g object
    
    Returns:
        Dict con datos del usuario o None si no autenticado
    """
    return getattr(g, 'current_user', None)

def get_current_user_id() -> Optional[str]:
    """
    Obtener ID del usuario actual
    
    Returns:
        String UUID del usuario o None si no autenticado
    """
    user = get_current_user()
    return str(user['id']) if user else None

def get_current_user_organization_id() -> Optional[str]:
    """
    Obtener organization_id del usuario actual
    
    Returns:
        String UUID de la organización o None si no autenticado/sin org
    """
    user = get_current_user()
    if not user:
        return None
    
    org_id = user.get('organization_id')
    return str(org_id) if org_id else None

def optional_jwt(f):
    """
    Decorator para endpoints donde JWT es opcional
    Si hay token válido, carga el usuario. Si no hay token, continúa sin error.
    
    Usage:
        @app.route("/public-or-private")
        @optional_jwt 
        def mixed_endpoint():
            current_user = g.current_user  # Puede ser None
            if current_user:
                return {"message": f"Hello {current_user['full_name']}"}
            else:
                return {"message": "Hello anonymous user"}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Intentar extraer token (sin fallar si no existe)
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                parts = auth_header.split()
                if parts[0].lower() == 'bearer' and len(parts) == 2:
                    token = parts[1]
            except Exception:
                pass  # Ignorar errores de parsing
        
        if token:
            try:
                # Intentar decodificar token
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        from uuid import UUID
                        user = user_repository.get_by_id(UUID(user_id))
                        if user and user['status'] in ['active', 'pending_verification']:
                            g.current_user = user
                            logger.debug(f"✅ Optional auth - user: {user['email']}")
            except Exception as e:
                logger.debug(f"Optional auth failed: {e}")
                pass  # Continuar sin autenticación
        
        # Si no se pudo autenticar, g.current_user será None
        if not hasattr(g, 'current_user'):
            g.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator para endpoints que requieren permisos de admin
    TODO: Implementar sistema de roles cuando sea necesario
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Por ahora, todos los usuarios autenticados son "admin"
        # En el futuro, agregar validación de roles
        return jwt_required(f)(*args, **kwargs)
    
    return decorated

# ========================
# UTILITY FUNCTIONS
# ========================

def validate_user_ownership(resource_user_id: str) -> bool:
    """
    Validar que el usuario actual es dueño del recurso
    
    Args:
        resource_user_id: user_id del recurso a validar
        
    Returns:
        True si el usuario actual es dueño del recurso
    """
    current_user = get_current_user()
    if not current_user:
        return False
    
    return str(current_user['id']) == str(resource_user_id)

def require_ownership(resource_user_id: str):
    """
    Validar ownership y devolver error 403 si no es dueño
    
    Args:
        resource_user_id: user_id del recurso
        
    Raises:
        Flask abort(403) si no es dueño
    """
    if not validate_user_ownership(resource_user_id):
        from flask import abort
        abort(403, description="Access denied: You don't own this resource")

logger.info("🔐 Flask JWT Middleware initialized")
