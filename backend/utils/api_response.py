"""
📦 API Response Utilities - Formato estandarizado para todas las respuestas

Proporciona funciones helper para crear respuestas consistentes en toda la API:
- Respuestas de éxito con datos
- Respuestas de error con detalles
- Códigos HTTP estandarizados
- Formato JSON consistente

Usage:
    from backend.utils.api_response import success_response, error_response
    
    # Success
    return success_response(data={"user": user_data}, message="User created")
    
    # Error
    return error_response(message="User not found", status_code=404)
"""
from typing import Any, Optional, Dict, List, Union
from flask import jsonify, Response
import logging

logger = logging.getLogger(__name__)


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de éxito estandarizada.
    
    Args:
        data: Datos a retornar (dict, list, o cualquier tipo serializable)
        message: Mensaje descriptivo del éxito
        status_code: Código HTTP (default: 200)
        meta: Metadata adicional (paginación, totales, etc.)
    
    Returns:
        tuple: (Response JSON, status_code)
    
    Formato de respuesta:
        {
            "status": "success",
            "message": "Operation completed successfully",
            "data": {...},
            "meta": {...}  # opcional
        }
    
    Example:
        return success_response(
            data={"user_id": "123", "name": "John"},
            message="User retrieved successfully",
            meta={"timestamp": "2026-02-05T12:00:00Z"}
        )
    """
    response = {
        "status": "success",
        "message": message,
        "data": data
    }
    
    if meta:
        response["meta"] = meta
    
    return jsonify(response), status_code


def error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Union[Dict, List, str]] = None,
    suggestions: Optional[List[str]] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de error estandarizada.
    
    Args:
        message: Mensaje de error principal
        status_code: Código HTTP (400, 404, 500, etc.)
        error_code: Código de error específico (ej: "USER_NOT_FOUND")
        details: Detalles adicionales del error
        suggestions: Lista de sugerencias para resolver el error
    
    Returns:
        tuple: (Response JSON, status_code)
    
    Formato de respuesta:
        {
            "status": "error",
            "message": "User not found",
            "error_code": "USER_NOT_FOUND",
            "details": {...},  # opcional
            "suggestions": [...]  # opcional
        }
    
    Example:
        return error_response(
            message="User not found",
            status_code=404,
            error_code="USER_NOT_FOUND",
            details={"user_id": "123"},
            suggestions=["Check if the user ID is correct", "Verify user exists"]
        )
    """
    response = {
        "status": "error",
        "message": message
    }
    
    if error_code:
        response["error_code"] = error_code
    
    if details:
        response["details"] = details
    
    if suggestions:
        response["suggestions"] = suggestions
    
    # Log error para debugging
    logger.error(
        f"API Error: {message} (code: {status_code}, error_code: {error_code})"
    )
    
    return jsonify(response), status_code


def paginated_response(
    data: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: str = "Success"
) -> tuple[Response, int]:
    """
    Crear respuesta paginada estandarizada.
    
    Args:
        data: Lista de items de la página actual
        page: Número de página actual (1-indexed)
        per_page: Items por página
        total: Total de items disponibles
        message: Mensaje descriptivo
    
    Returns:
        tuple: (Response JSON, 200)
    
    Formato de respuesta:
        {
            "status": "success",
            "message": "Data retrieved successfully",
            "data": [...],
            "meta": {
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 100,
                    "total_pages": 5,
                    "has_next": true,
                    "has_prev": false
                }
            }
        }
    
    Example:
        return paginated_response(
            data=users,
            page=1,
            per_page=20,
            total=100,
            message="Users retrieved successfully"
        )
    """
    total_pages = (total + per_page - 1) // per_page  # Ceiling division
    
    meta = {
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
    
    return success_response(data=data, message=message, meta=meta)


def validation_error_response(
    errors: Union[Dict[str, List[str]], List[str]],
    message: str = "Validation failed"
) -> tuple[Response, int]:
    """
    Crear respuesta de error de validación estandarizada.
    
    Args:
        errors: Errores de validación (dict de campo -> errores o lista de errores)
        message: Mensaje principal
    
    Returns:
        tuple: (Response JSON, 422)
    
    Formato de respuesta:
        {
            "status": "error",
            "message": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "field_name": ["Error 1", "Error 2"],
                ...
            }
        }
    
    Example:
        return validation_error_response(
            errors={
                "email": ["Email is required", "Email format is invalid"],
                "password": ["Password must be at least 8 characters"]
            }
        )
    """
    return error_response(
        message=message,
        status_code=422,
        error_code="VALIDATION_ERROR",
        details=errors
    )


def not_found_response(
    resource: str,
    identifier: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de recurso no encontrado estandarizada.
    
    Args:
        resource: Tipo de recurso (ej: "User", "RFX", "Product")
        identifier: Identificador del recurso (opcional)
        suggestions: Sugerencias para resolver (opcional)
    
    Returns:
        tuple: (Response JSON, 404)
    
    Example:
        return not_found_response(
            resource="RFX",
            identifier="abc-123",
            suggestions=["Check if the RFX ID is correct", "Verify RFX exists"]
        )
    """
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    
    return error_response(
        message=message,
        status_code=404,
        error_code=f"{resource.upper()}_NOT_FOUND",
        details={"identifier": identifier} if identifier else None,
        suggestions=suggestions
    )


def unauthorized_response(
    message: str = "Unauthorized access",
    details: Optional[str] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de no autorizado estandarizada.
    
    Args:
        message: Mensaje de error
        details: Detalles adicionales
    
    Returns:
        tuple: (Response JSON, 401)
    
    Example:
        return unauthorized_response(
            message="Invalid or expired token",
            details="Please login again"
        )
    """
    return error_response(
        message=message,
        status_code=401,
        error_code="UNAUTHORIZED",
        details=details,
        suggestions=["Verify your authentication token", "Login again if token expired"]
    )


def forbidden_response(
    message: str = "Access forbidden",
    details: Optional[str] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de acceso prohibido estandarizada.
    
    Args:
        message: Mensaje de error
        details: Detalles adicionales
    
    Returns:
        tuple: (Response JSON, 403)
    
    Example:
        return forbidden_response(
            message="You don't have permission to access this resource",
            details="Admin role required"
        )
    """
    return error_response(
        message=message,
        status_code=403,
        error_code="FORBIDDEN",
        details=details,
        suggestions=["Contact your administrator for access"]
    )


def server_error_response(
    message: str = "Internal server error",
    error_id: Optional[str] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de error del servidor estandarizada.
    
    Args:
        message: Mensaje de error
        error_id: ID del error para tracking (opcional)
    
    Returns:
        tuple: (Response JSON, 500)
    
    Example:
        return server_error_response(
            message="Database connection failed",
            error_id="ERR-2026-02-05-12345"
        )
    """
    details = {"error_id": error_id} if error_id else None
    
    return error_response(
        message=message,
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        details=details,
        suggestions=["Please try again later", "Contact support if the problem persists"]
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully",
    resource_id: Optional[str] = None
) -> tuple[Response, int]:
    """
    Crear respuesta de recurso creado estandarizada.
    
    Args:
        data: Datos del recurso creado
        message: Mensaje descriptivo
        resource_id: ID del recurso creado (opcional)
    
    Returns:
        tuple: (Response JSON, 201)
    
    Example:
        return created_response(
            data={"user": user_data},
            message="User created successfully",
            resource_id="user-123"
        )
    """
    meta = {"resource_id": resource_id} if resource_id else None
    return success_response(data=data, message=message, status_code=201, meta=meta)


def no_content_response() -> tuple[Response, int]:
    """
    Crear respuesta sin contenido estandarizada (para DELETE exitoso).
    
    Returns:
        tuple: (Response vacía, 204)
    
    Example:
        return no_content_response()
    """
    return jsonify({}), 204


# ==================== ERROR CODES CONSTANTS ====================

class ErrorCodes:
    """Códigos de error estandarizados para toda la API"""
    
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resources
    USER_NOT_FOUND = "USER_NOT_FOUND"
    RFX_NOT_FOUND = "RFX_NOT_FOUND"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    ORGANIZATION_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
    
    # Business Logic
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    
    # External Services
    OPENAI_ERROR = "OPENAI_ERROR"
    CLOUDINARY_ERROR = "CLOUDINARY_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Server
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
