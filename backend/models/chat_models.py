"""
Modelos Pydantic para el Chat Conversacional RFX.

Estos modelos definen la estructura de datos para:
- Requests del cliente
- Responses del servidor
- Cambios a aplicar en el RFX
- Opciones de confirmación
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ChangeType(str, Enum):
    """Tipos de cambios que se pueden aplicar."""
    ADD_PRODUCT = "add_product"
    UPDATE_PRODUCT = "update_product"
    DELETE_PRODUCT = "delete_product"
    UPDATE_FIELD = "update_field"


class ChatContext(BaseModel):
    """
    Contexto actual del RFX para el agente de IA.
    
    Este contexto se envía con cada mensaje para que la IA
    tenga información completa del estado actual.
    """
    current_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de productos actuales en el RFX"
    )
    current_total: float = Field(
        default=0.0,
        description="Total actual del RFX"
    )
    delivery_date: Optional[str] = Field(
        default=None,
        description="Fecha de entrega (formato: YYYY-MM-DD)"
    )
    delivery_location: Optional[str] = Field(
        default=None,
        description="Ubicación de entrega"
    )
    client_name: Optional[str] = Field(
        default=None,
        description="Nombre del cliente"
    )
    client_email: Optional[str] = Field(
        default=None,
        description="Email del cliente"
    )
    currency: Optional[str] = Field(
        default="MXN",
        description="Moneda del RFX"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_products": [
                    {
                        "id": "prod_1",
                        "nombre": "Pasos salados variados",
                        "cantidad": 50,
                        "precio": 5.0,
                        "unidad": "unidades"
                    }
                ],
                "current_total": 250.0,
                "delivery_date": "2025-12-15",
                "delivery_location": "Salón Gardenia",
                "client_name": "María González",
                "currency": "MXN"
            }
        }


class ChatRequest(BaseModel):
    """
    Request para enviar un mensaje al chat.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Mensaje del usuario"
    )
    files: List[str] = Field(
        default_factory=list,
        description="URLs o paths de archivos adjuntos"
    )
    context: ChatContext = Field(
        ...,
        description="Contexto actual del RFX"
    )
    
    @validator('message')
    def message_not_empty(cls, v):
        """Valida que el mensaje no esté vacío."""
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Agregar 20 refrescos",
                "files": [],
                "context": {
                    "current_products": [],
                    "current_total": 0.0
                }
            }
        }


class RFXChange(BaseModel):
    """
    Cambio a aplicar en el RFX.
    
    Representa una operación específica que el backend debe ejecutar.
    """
    type: ChangeType = Field(
        ...,
        description="Tipo de cambio a aplicar"
    )
    target: str = Field(
        ...,
        description="ID del producto o nombre del campo a modificar"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Datos específicos del cambio"
    )
    description: str = Field(
        ...,
        description="Descripción legible del cambio"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "add_product",
                "target": "new",
                "data": {
                    "nombre": "Refrescos variados",
                    "cantidad": 20,
                    "precio": 2.50,
                    "unidad": "unidades"
                },
                "description": "Agregado: Refrescos variados (20 unidades)"
            }
        }


class ConfirmationOption(BaseModel):
    """
    Opción de confirmación para el usuario.
    
    Cuando la IA detecta ambigüedad o duplicados, ofrece opciones
    para que el usuario elija cómo proceder.
    """
    value: str = Field(
        ...,
        description="Valor único de la opción"
    )
    label: str = Field(
        ...,
        description="Texto descriptivo de la opción"
    )
    emoji: str = Field(
        ...,
        description="Emoji para la opción"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Contexto adicional para aplicar esta opción"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": "add_only_new",
                "label": "Solo agregar productos nuevos",
                "emoji": "1️⃣",
                "context": {
                    "new_products": [
                        {"nombre": "Jugos", "cantidad": 15, "precio": 3.0}
                    ]
                }
            }
        }


class ChatMetadata(BaseModel):
    """Metadata adicional de la respuesta del chat."""
    tokens_used: Optional[int] = Field(
        default=None,
        description="Tokens consumidos en la llamada"
    )
    cost_usd: Optional[float] = Field(
        default=None,
        description="Costo en USD de la llamada"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Tiempo de procesamiento en milisegundos"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Modelo de IA utilizado"
    )
    
    class Config:
        protected_namespaces = ()  # Permite usar 'model_' como prefijo


class ChatResponse(BaseModel):
    """
    Response del chat con mensaje y cambios a aplicar.
    
    Esta es la respuesta principal que el backend envía al frontend.
    """
    status: str = Field(
        default="success",
        description="Estado de la respuesta (success, error)"
    )
    message: str = Field(
        ...,
        description="Mensaje amigable para el usuario"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza de la IA (0.0-1.0)"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Razonamiento interno del agente (Chain-of-Thought) - solo para logs"
    )
    changes: List[RFXChange] = Field(
        default_factory=list,
        description="Lista de cambios a aplicar"
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Indica si se requiere confirmación del usuario"
    )
    options: List[ConfirmationOption] = Field(
        default_factory=list,
        description="Opciones de confirmación (si requires_confirmation=true)"
    )
    metadata: Optional[ChatMetadata] = Field(
        default=None,
        description="Metadata adicional de la respuesta"
    )
    
    @validator('options')
    def options_required_if_confirmation(cls, v, values):
        """Valida que haya opciones si se requiere confirmación."""
        if values.get('requires_confirmation') and not v:
            raise ValueError(
                'Se requieren opciones cuando requires_confirmation es true'
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "✅ ¡Listo! He agregado:\n\n📦 Refrescos variados\n   20 unidades\n   $2.50 c/u\n\n💰 Total actualizado: $0 → $50",
                "confidence": 0.95,
                "changes": [
                    {
                        "type": "add_product",
                        "target": "new",
                        "data": {
                            "nombre": "Refrescos variados",
                            "cantidad": 20,
                            "precio": 2.50,
                            "unidad": "unidades"
                        },
                        "description": "Agregado: Refrescos variados (20 unidades)"
                    }
                ],
                "requires_confirmation": False,
                "options": [],
                "metadata": {
                    "tokens_used": 450,
                    "cost_usd": 0.0003,
                    "processing_time_ms": 1200,
                    "model_used": "gpt-4o"
                }
            }
        }


class ConfirmRequest(BaseModel):
    """
    Request para confirmar una opción seleccionada por el usuario.
    """
    option_value: str = Field(
        ...,
        description="Valor de la opción seleccionada"
    )
    context: Dict[str, Any] = Field(
        ...,
        description="Contexto de la opción seleccionada"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "option_value": "add_only_new",
                "context": {
                    "new_products": [
                        {"nombre": "Jugos", "cantidad": 15, "precio": 3.0}
                    ]
                }
            }
        }


class ChatHistoryEntry(BaseModel):
    """
    Entrada del historial de chat.
    
    Representa un mensaje guardado en la base de datos.
    """
    id: str
    rfx_id: str
    user_id: str
    user_message: str
    user_files: List[str] = Field(default_factory=list)
    assistant_message: str
    confidence: Optional[float] = None
    changes_applied: List[Dict[str, Any]] = Field(default_factory=list)
    requires_confirmation: bool = False
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    processing_time_ms: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        protected_namespaces = ()  # Permite usar 'model_' como prefijo


# Exportar todos los modelos
__all__ = [
    "ChangeType",
    "ChatContext",
    "ChatRequest",
    "RFXChange",
    "ConfirmationOption",
    "ChatMetadata",
    "ChatResponse",
    "ConfirmRequest",
    "ChatHistoryEntry",
]
