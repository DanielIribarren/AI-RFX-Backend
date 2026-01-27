"""
API endpoints para el chat conversacional RFX.

KISS: Endpoints simples que delegan todo a los servicios.
Sin lógica de negocio en los endpoints.
"""

from flask import Blueprint, request, jsonify
from typing import List
import logging
import uuid
import asyncio
import json

from backend.services.chat_agent import ChatAgent
from backend.services.rfx_chat_service import RFXChatService
from backend.services.credits_service import get_credits_service
from backend.models.chat_models import ChatRequest, ChatContext
from backend.utils.auth_middleware import jwt_required, get_current_user, get_current_user_organization_id
from backend.exceptions import InsufficientCreditsError

logger = logging.getLogger(__name__)

# Crear blueprint
rfx_chat_bp = Blueprint('rfx_chat', __name__, url_prefix='/api/rfx')


def _determine_refresh_needs(changes: List) -> tuple[bool, str]:
    """
    Determina si se necesita refresh y el alcance del mismo.
    
    Returns:
        tuple: (needs_refresh: bool, scope: str)
        scope puede ser: 'none', 'products', 'details', 'full'
    """
    if not changes:
        return False, 'none'
    
    change_types = {change.type for change in changes}
    
    # Cambios en productos requieren refresh de productos (para recalcular ganancias)
    product_changes = {'add_product', 'update_product', 'delete_product'}
    if change_types & product_changes:
        return True, 'products'
    
    # Cambios en detalles del RFX solo requieren refresh de detalles
    if 'update_field' in change_types:
        return True, 'details'
    
    return False, 'none'


def _get_components_to_refresh(changes: List) -> List[str]:
    """
    Retorna lista específica de componentes que necesitan refresh.
    
    Returns:
        List[str]: Lista de componentes a refrescar
        Ejemplos: ['products', 'pricing', 'totals', 'details', 'header']
    """
    if not changes:
        return []
    
    components = set()
    
    for change in changes:
        if change.type in ['add_product', 'update_product', 'delete_product']:
            components.add('products')
            components.add('pricing')  # Recalcular pricing
            components.add('totals')   # Recalcular totales
        elif change.type == 'update_field':
            # Determinar qué campo se actualizó
            field = change.target
            if field in ['fechaEntrega', 'lugarEntrega']:
                components.add('details')
            elif field in ['clienteNombre', 'clienteEmail']:
                components.add('header')
            else:
                components.add('details')
    
    return sorted(list(components))


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
        
        # 1. Parsear request (FormData igual que /api/rfx/process)
        message = request.form.get('message')
        context_str = request.form.get('context')
        
        if not message or not context_str:
            return jsonify({
                'status': 'error',
                'message': 'Request inválido: se requiere message y context'
            }), 400
        
        # Parse context JSON
        try:
            context = json.loads(context_str)
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Context debe ser JSON válido'
            }), 400
        
        # Procesar archivos (igual que /api/rfx/process)
        files = []
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            for file in uploaded_files:
                if file and file.filename:
                    files.append({
                        'name': file.filename,
                        'type': file.content_type or 'application/octet-stream',
                        'content': file.read()  # bytes directamente
                    })
                    file.seek(0)  # Reset para posible relectura
        
        logger.info(
            f"[RFXChat] Message received: "
            f"rfx_id={rfx_id}, user_id={user_id}, "
            f"message_length={len(message)}, files_count={len(files)}, "
            f"correlation_id={correlation_id}"
        )
        
        # 🔒 VALIDAR OWNERSHIP DEL RFX
        organization_id = get_current_user_organization_id()
        
        from ..core.database import get_database_client
        db = get_database_client()
        
        rfx = db.get_rfx_by_id(rfx_id)
        if not rfx:
            logger.error(f"❌ RFX not found: {rfx_id}")
            return jsonify({
                "status": "error",
                "message": "RFX not found"
            }), 404
        
        # Validar ownership
        rfx_org_id = rfx.get("organization_id")
        rfx_user_id = rfx.get("user_id")
        
        if rfx_org_id:
            # RFX organizacional
            if rfx_org_id != organization_id:
                logger.warning(f"🚨 Access denied: User {user_id} tried to access RFX from org {rfx_org_id}")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - RFX belongs to different organization"
                }), 403
        else:
            # RFX personal
            if rfx_user_id != user_id:
                logger.warning(f"🚨 Access denied: User {user_id} tried to access RFX of user {rfx_user_id}")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - RFX belongs to different user"
                }), 403
            
            if organization_id:
                logger.warning(f"🚨 Access denied: User {user_id} in org tried to access personal RFX")
                return jsonify({
                    "status": "error",
                    "message": "Access denied - Personal RFX not accessible while in organization"
                }), 403
        
        logger.info(f"✅ Ownership validated for RFX {rfx_id}")
        
        # 💳 VERIFICAR CRÉDITOS DISPONIBLES (1 crédito por mensaje de chat)
        credits_service = get_credits_service()
        
        # Verificar créditos según contexto del usuario
        has_credits, available, msg = credits_service.check_credits_available(
            organization_id,  # None para usuarios personales
            'chat_message',   # 1 crédito
            user_id=user_id   # Requerido para usuarios personales
        )
        
        if not has_credits:
            context = "organization" if organization_id else "personal plan"
            logger.warning(f"⚠️ Insufficient credits for chat message ({context}): {msg}")
            return jsonify({
                "status": "error",
                "error_type": "insufficient_credits",
                "message": msg,
                "credits_required": 1,
                "credits_available": available
            }), 402  # 402 Payment Required
        
        context = "organization" if organization_id else "personal"
        logger.info(f"✅ Credits verified ({context}): {available} available")
        
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
        
        # Convertir files a formato serializable (sin bytes)
        files_metadata = [
            {
                'name': f.get('name'),
                'type': f.get('type'),
                'size': len(f.get('content', b''))
            }
            for f in files
        ]
        
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
                user_files=files_metadata,  # Solo metadata, no bytes
                tokens_used=response.metadata.tokens_used if response.metadata else 0,
                cost_usd=response.metadata.cost_usd if response.metadata else 0.0,
                processing_time_ms=response.metadata.processing_time_ms if response.metadata else 0,
                model_used=response.metadata.model_used if response.metadata else ""
            )
        )
        
        loop.close()
        
        # 💳 CONSUMIR CRÉDITO (1 crédito por mensaje de chat)
        consume_result = credits_service.consume_credits(
            organization_id=organization_id,  # None para usuarios personales
            operation='chat_message',
            rfx_id=rfx_id,
            user_id=user_id,  # Requerido para usuarios personales
            description=f"Chat message for RFX {rfx_id}"
        )
        
        if consume_result["status"] == "success":
            context = "organization" if organization_id else "personal"
            logger.info(f"✅ Credits consumed ({context}): 1 (remaining: {consume_result['credits_remaining']})")
        else:
            logger.error(f"❌ Failed to consume credits: {consume_result.get('message')})")
        
        logger.info(
            f"[RFXChat] Message processed: "
            f"rfx_id={rfx_id}, confidence={response.confidence:.2f}, "
            f"changes={len(response.changes)}, correlation_id={correlation_id}"
        )
        
        # 4. Determinar qué componentes necesitan refresh
        needs_refresh, refresh_scope = _determine_refresh_needs(response.changes)
        
        # 5. Retornar respuesta completa con metadata de refresh
        return jsonify({
            'status': 'success',
            'message': response.message,
            'confidence': response.confidence,
            'changes': [change.dict() for change in response.changes],
            'requires_confirmation': response.requires_confirmation,
            'refresh': {
                'needs_refresh': needs_refresh,
                'scope': refresh_scope,
                'components': _get_components_to_refresh(response.changes)
            }
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
        limit = request.args.get('limit', 20, type=int)  # Default 20 mensajes (10 turnos)
        
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
