"""
🔒 RFX Ownership Validation Utilities

Funciones helper para validar que un usuario tiene acceso a un RFX específico.
Implementa la lógica de aislamiento de datos entre usuarios personales y organizaciones.
"""

from typing import Tuple, Optional
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def validate_rfx_ownership(
    rfx: dict,
    user_id: str,
    organization_id: Optional[str]
) -> Tuple[bool, Optional[tuple]]:
    """
    Valida que un usuario tenga acceso a un RFX específico.
    
    Lógica de validación:
    - RFX organizacional: usuario debe pertenecer a la misma organización
    - RFX personal: usuario debe ser el dueño Y no estar en una organización
    
    Args:
        rfx: Diccionario con datos del RFX (debe incluir organization_id y user_id)
        user_id: ID del usuario que intenta acceder
        organization_id: ID de la organización del usuario (None si es personal)
    
    Returns:
        Tuple[bool, Optional[tuple]]: 
            - (True, None) si el acceso está permitido
            - (False, (response, status_code)) si el acceso está denegado
    
    Examples:
        >>> rfx = {"organization_id": "org-123", "user_id": "user-456"}
        >>> validate_rfx_ownership(rfx, "user-456", "org-123")
        (True, None)
        
        >>> validate_rfx_ownership(rfx, "user-789", "org-123")
        (True, None)  # Otro usuario de la misma org puede acceder
        
        >>> validate_rfx_ownership(rfx, "user-456", None)
        (False, (response, 403))  # Usuario personal no puede acceder a RFX org
    """
    if not rfx:
        logger.error("❌ RFX not found")
        return False, (jsonify({
            "status": "error",
            "message": "RFX not found"
        }), 404)
    
    rfx_org_id = rfx.get("organization_id")
    rfx_user_id = rfx.get("user_id")
    
    # Caso 1: RFX organizacional
    if rfx_org_id:
        if rfx_org_id != organization_id:
            logger.warning(
                f"🚨 Access denied: User {user_id} (org: {organization_id}) "
                f"tried to access RFX from org {rfx_org_id}"
            )
            return False, (jsonify({
                "status": "error",
                "message": "Access denied - RFX belongs to different organization"
            }), 403)
        
        # Usuario pertenece a la organización correcta
        logger.info(f"✅ Organization access granted: user {user_id} → org {rfx_org_id}")
        return True, None
    
    # Caso 2: RFX personal
    else:
        # Validar que el usuario sea el dueño
        if rfx_user_id != user_id:
            logger.warning(
                f"🚨 Access denied: User {user_id} tried to access "
                f"personal RFX of user {rfx_user_id}"
            )
            return False, (jsonify({
                "status": "error",
                "message": "Access denied - RFX belongs to different user"
            }), 403)
        
        # Validar que el usuario NO esté en una organización
        if organization_id:
            logger.warning(
                f"🚨 Access denied: User {user_id} in org {organization_id} "
                f"tried to access personal RFX"
            )
            return False, (jsonify({
                "status": "error",
                "message": "Access denied - Personal RFX not accessible while in organization"
            }), 403)
        
        # Usuario personal accediendo a su propio RFX
        logger.info(f"✅ Personal access granted: user {user_id} → personal RFX")
        return True, None


def get_and_validate_rfx_ownership(
    db_client,
    rfx_id: str,
    user_id: str,
    organization_id: Optional[str]
) -> Tuple[Optional[dict], Optional[tuple]]:
    """
    Obtiene un RFX y valida ownership en un solo paso.
    
    Combina get_rfx_by_id() con validate_rfx_ownership() para simplificar código.
    
    Args:
        db_client: Cliente de base de datos
        rfx_id: ID del RFX a obtener
        user_id: ID del usuario que intenta acceder
        organization_id: ID de la organización del usuario (None si es personal)
    
    Returns:
        Tuple[Optional[dict], Optional[tuple]]:
            - (rfx_data, None) si el acceso está permitido
            - (None, (response, status_code)) si hay error o acceso denegado
    
    Example:
        >>> rfx, error = get_and_validate_rfx_ownership(db, rfx_id, user_id, org_id)
        >>> if error:
        >>>     return error  # Retornar directamente el error
        >>> # Continuar con rfx...
    """
    # Obtener RFX
    rfx = db_client.get_rfx_by_id(rfx_id)
    
    if not rfx:
        logger.error(f"❌ RFX not found: {rfx_id}")
        return None, (jsonify({
            "status": "error",
            "message": "RFX not found"
        }), 404)
    
    # Validar ownership
    is_valid, error_response = validate_rfx_ownership(rfx, user_id, organization_id)
    
    if not is_valid:
        return None, error_response
    
    logger.info(f"✅ RFX {rfx_id} retrieved and ownership validated")
    return rfx, None
