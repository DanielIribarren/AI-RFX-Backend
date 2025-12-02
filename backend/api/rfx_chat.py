"""
API endpoints para el chat conversacional RFX.

KISS: Endpoints simples que delegan todo a los servicios.
Sin lógica de negocio en los endpoints.
"""

from flask import Blueprint, request, jsonify
import logging
import uuid
import asyncio

from backend.services.chat_agent import ChatAgent
from backend.services.rfx_chat_service import RFXChatService
from backend.models.chat_models import ChatRequest, ChatContext
from backend.utils.auth_middleware import jwt_required, get_current_user

logger = logging.getLogger(__name__)

# Crear blueprint
rfx_chat_bp = Blueprint('rfx_chat', __name__, url_prefix='/api/rfx')


@rfx_chat_bp.route('/<rfx_id>/chat', methods=['POST'])
@jwt_required
def send_chat_message(rfx_id):
    """
    Procesa un mensaje del chat conversacional.
    
    KISS: 
    1. Validar request
    2. Llamar a ChatAgent (ÉL DECIDE TODO)
    3. Guardar en BD
    4. Retornar respuesta
    
    Sin lógica de negocio - solo orquestación.
    """
    correlation_id = str(uuid.uuid4())
    
    try:
        # Obtener usuario actual (del decorator jwt_required)
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        
        # 1. Parsear request
        data = request.get_json()
        
        if not data or 'message' not in data or 'context' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Request inválido: se requiere message y context'
            }), 400
        
        message = data['message']
        context = data['context']
        files = data.get('files', [])
        
        logger.info(
            f"[RFXChat] Message received: "
            f"rfx_id={rfx_id}, user_id={user_id}, "
            f"message_length={len(message)}, correlation_id={correlation_id}"
        )
        
        # 2. Llamar al agente de IA (ÉL DECIDE TODO)
        chat_agent = ChatAgent()
        
        # Ejecutar async en sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(
            chat_agent.process_message(
                message=message,
                context=context,
                rfx_id=rfx_id,
                files=files
            )
        )
        
        loop.close()
        
        # 3. Guardar en historial
        chat_service = RFXChatService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(
            chat_service.save_chat_message(
                rfx_id=rfx_id,
                user_id=user_id,
                user_message=message,
                assistant_message=response.message,
                changes_applied=[change.dict() for change in response.changes],
                confidence=response.confidence,
                requires_confirmation=response.requires_confirmation,
                user_files=files,
                tokens_used=response.metadata.tokens_used if response.metadata else 0,
                cost_usd=response.metadata.cost_usd if response.metadata else 0.0,
                processing_time_ms=response.metadata.processing_time_ms if response.metadata else 0,
                model_used=response.metadata.model_used if response.metadata else ""
            )
        )
        
        loop.close()
        
        logger.info(
            f"[RFXChat] Message processed: "
            f"rfx_id={rfx_id}, confidence={response.confidence:.2f}, "
            f"changes={len(response.changes)}, correlation_id={correlation_id}"
        )
        
        # 4. Retornar respuesta (KISS: conversión directa a dict)
        return jsonify({
            'status': response.status,
            'message': response.message,
            'confidence': response.confidence,
            'changes': [change.dict() for change in response.changes],
            'requires_confirmation': response.requires_confirmation,
            'options': [opt.dict() for opt in response.options],
            'metadata': response.metadata.dict() if response.metadata else {}
        }), 200
        
    except Exception as e:
        logger.error(
            f"[RFXChat] Error processing message: {e}",
            exc_info=True,
            extra={'correlation_id': correlation_id}
        )
        
        return jsonify({
            'status': 'error',
            'message': 'Lo siento, ocurrió un error al procesar tu mensaje.',
            'confidence': 0.0,
            'changes': [],
            'requires_confirmation': False,
            'options': [],
            'metadata': {
                'correlation_id': correlation_id,
                'error': str(e)
            }
        }), 500


@rfx_chat_bp.route('/<rfx_id>/chat/history', methods=['GET'])
@jwt_required
def get_chat_history(rfx_id):
    """
    Obtiene el historial de chat de un RFX.
    
    KISS: Query simple, sin paginación compleja.
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        
        chat_service = RFXChatService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        history = loop.run_until_complete(
            chat_service.get_chat_history(rfx_id, limit)
        )
        
        loop.close()
        
        logger.info(
            f"[RFXChat] History retrieved: "
            f"rfx_id={rfx_id}, count={len(history)}"
        )
        
        return jsonify({
            'status': 'success',
            'history': history,
            'count': len(history)
        }), 200
        
    except Exception as e:
        logger.error(f"[RFXChat] Error getting history: {e}", exc_info=True)
        
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener el historial',
            'history': []
        }), 500


# Exportar blueprint
__all__ = ['rfx_chat_bp']
