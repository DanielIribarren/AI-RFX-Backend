"""
Custom Exceptions para el Sistema RFX

VERSIÓN: 1.0
Fecha: 9 de Diciembre, 2025

Excepciones personalizadas para manejo de errores específicos del negocio.
"""


class RFXException(Exception):
    """Excepción base para errores del sistema RFX"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientCreditsError(RFXException):
    """
    Excepción cuando no hay suficientes créditos para una operación.
    
    Ejemplo:
        raise InsufficientCreditsError(
            "Insufficient credits for extraction. Required: 5, Available: 2",
            credits_required=5,
            credits_available=2
        )
    """
    def __init__(
        self, 
        message: str, 
        credits_required: int = 0,
        credits_available: int = 0,
        plan_tier: str = "unknown"
    ):
        self.credits_required = credits_required
        self.credits_available = credits_available
        self.plan_tier = plan_tier
        super().__init__(message, status_code=402)  # 402 Payment Required
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para respuesta JSON"""
        return {
            "status": "error",
            "error_type": "insufficient_credits",
            "message": self.message,
            "credits_required": self.credits_required,
            "credits_available": self.credits_available,
            "plan_tier": self.plan_tier,
            "suggestion": "Consider upgrading your plan or waiting for monthly credit reset"
        }


class PlanLimitExceededError(RFXException):
    """
    Excepción cuando se excede un límite del plan (usuarios, RFX, etc.)
    
    Ejemplo:
        raise PlanLimitExceededError(
            "User limit reached for Free plan",
            limit_type="users",
            current_value=2,
            limit_value=2
        )
    """
    def __init__(
        self,
        message: str,
        limit_type: str,
        current_value: int,
        limit_value: int,
        plan_tier: str = "unknown"
    ):
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.plan_tier = plan_tier
        super().__init__(message, status_code=403)  # 403 Forbidden
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para respuesta JSON"""
        return {
            "status": "error",
            "error_type": "plan_limit_exceeded",
            "message": self.message,
            "limit_type": self.limit_type,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "plan_tier": self.plan_tier,
            "suggestion": f"Upgrade your plan to increase {self.limit_type} limit"
        }


class ProcessingStatusError(RFXException):
    """
    Excepción cuando hay un error con el estado de procesamiento de un RFX.
    
    Ejemplo:
        raise ProcessingStatusError(
            "Cannot generate proposal: extraction not completed",
            rfx_id=rfx_id,
            required_status="extracted"
        )
    """
    def __init__(
        self,
        message: str,
        rfx_id: str,
        required_status: str = None
    ):
        self.rfx_id = rfx_id
        self.required_status = required_status
        super().__init__(message, status_code=400)
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para respuesta JSON"""
        return {
            "status": "error",
            "error_type": "processing_status_error",
            "message": self.message,
            "rfx_id": self.rfx_id,
            "required_status": self.required_status
        }


class OrganizationNotFoundError(RFXException):
    """Excepción cuando no se encuentra una organización"""
    def __init__(self, organization_id: str):
        message = f"Organization not found: {organization_id}"
        self.organization_id = organization_id
        super().__init__(message, status_code=404)
    
    def to_dict(self) -> dict:
        return {
            "status": "error",
            "error_type": "organization_not_found",
            "message": self.message,
            "organization_id": self.organization_id
        }


class RFXNotFoundError(RFXException):
    """Excepción cuando no se encuentra un RFX"""
    def __init__(self, rfx_id: str):
        message = f"RFX not found: {rfx_id}"
        self.rfx_id = rfx_id
        super().__init__(message, status_code=404)
    
    def to_dict(self) -> dict:
        return {
            "status": "error",
            "error_type": "rfx_not_found",
            "message": self.message,
            "rfx_id": self.rfx_id
        }
