"""
Organization Multi-Tenant Middleware

Decoradores para proteger endpoints y validar permisos de organización.
Sigue principios KISS: simple, directo, sin overengineering.
"""

from functools import wraps
from flask import g, jsonify, request
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def require_organization(f):
    """
    Decorator que requiere que el usuario tenga una organización válida.
    Inyecta g.organization_id y g.user_role para uso en el endpoint.
    
    Debe usarse DESPUÉS de @jwt_required (asume que g.user existe).
    
    Ejemplo:
        @app.route('/api/rfx')
        @jwt_required
        @require_organization
        def get_rfx():
            org_id = g.organization_id  # Disponible automáticamente
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar que el usuario esté autenticado
        if not hasattr(g, 'current_user') or not g.current_user:
            logger.warning("❌ require_organization: No current_user in g (jwt_required missing?)")
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = g.current_user.get('id')
        
        # Obtener organization_id y role del usuario
        from backend.core.database import DatabaseClient
        db = DatabaseClient()
        
        try:
            result = db.client.table("users")\
                .select("organization_id, role")\
                .eq("id", user_id)\
                .single()\
                .execute()
            
            if not result.data:
                logger.error(f"❌ User {user_id} not found in database")
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 404
            
            organization_id = result.data.get("organization_id")
            role = result.data.get("role")
            
            if not organization_id:
                logger.error(f"❌ User {user_id} has no organization_id")
                return jsonify({
                    "status": "error",
                    "message": "User has no organization assigned"
                }), 403
            
            # Inyectar en g para uso en el endpoint
            g.organization_id = organization_id
            g.user_role = role
            
            logger.info(f"✅ Organization middleware: user={user_id}, org={organization_id}, role={role}")
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"❌ Error in require_organization: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Failed to validate organization"
            }), 500
    
    return decorated_function


def require_role(allowed_roles: List[str]):
    """
    Decorator que requiere que el usuario tenga uno de los roles especificados.
    Debe usarse DESPUÉS de @require_organization.
    
    Args:
        allowed_roles: Lista de roles permitidos ['owner', 'admin', 'member']
    
    Ejemplo:
        @app.route('/api/organization/members')
        @jwt_required
        @require_organization
        @require_role(['owner', 'admin'])
        def manage_members():
            # Solo owners y admins pueden acceder
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar que require_organization se ejecutó primero
            if not hasattr(g, 'user_role'):
                logger.warning("❌ require_role: g.user_role not set (require_organization missing?)")
                return jsonify({
                    "status": "error",
                    "message": "Organization validation required"
                }), 500
            
            user_role = g.user_role
            
            if user_role not in allowed_roles:
                logger.warning(f"❌ Access denied: user has role '{user_role}', requires one of {allowed_roles}")
                return jsonify({
                    "status": "error",
                    "message": f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
                }), 403
            
            logger.info(f"✅ Role check passed: user has role '{user_role}'")
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def optional_organization(f):
    """
    Decorator que OPCIONALMENTE verifica si el usuario tiene organización.
    Inyecta g.organization_id y g.user_role si existen, pero NO bloquea si no existen.
    
    Útil para endpoints que funcionan tanto para usuarios con organización
    como para usuarios personales (sin organización).
    
    Debe usarse DESPUÉS de @jwt_required (asume que g.user existe).
    
    Ejemplo:
        @app.route('/api/organization/current')
        @jwt_required
        @optional_organization
        def get_current_organization():
            if g.organization_id:
                # Usuario tiene organización
                return org_data
            else:
                # Usuario personal sin organización
                return personal_data
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar que el usuario esté autenticado
        if not hasattr(g, 'current_user') or not g.current_user:
            logger.warning("❌ optional_organization: No current_user in g (jwt_required missing?)")
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        user_id = g.current_user.get('id')
        
        # Obtener organization_id y role del usuario
        from backend.core.database import DatabaseClient
        db = DatabaseClient()
        
        try:
            result = db.client.table("users")\
                .select("organization_id, role")\
                .eq("id", user_id)\
                .single()\
                .execute()
            
            if not result.data:
                logger.error(f"❌ User {user_id} not found in database")
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 404
            
            organization_id = result.data.get("organization_id")
            role = result.data.get("role")
            
            # Inyectar en g (pueden ser None para usuarios personales)
            g.organization_id = organization_id
            g.user_role = role
            
            if organization_id:
                logger.info(f"✅ Optional organization middleware: user={user_id}, org={organization_id}, role={role}")
            else:
                logger.info(f"✅ Optional organization middleware: user={user_id}, personal user (no org)")
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"❌ Error in optional_organization: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Failed to validate organization"
            }), 500
    
    return decorated_function


def get_organization_context() -> Optional[dict]:
    """
    Helper para obtener el contexto de organización desde g.
    
    Returns:
        dict con organization_id y user_role, o None si no está disponible
    
    Ejemplo:
        context = get_organization_context()
        if context:
            org_id = context['organization_id']
            role = context['role']
    """
    if hasattr(g, 'organization_id') and hasattr(g, 'user_role'):
        return {
            'organization_id': g.organization_id,
            'role': g.user_role
        }
    return None
