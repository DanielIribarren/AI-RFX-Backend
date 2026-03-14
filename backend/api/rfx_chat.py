"""
API endpoints para el chat conversacional RFX.

KISS: Endpoints simples que delegan todo a los servicios.
Sin lógica de negocio en los endpoints.
"""

from flask import Blueprint, request, jsonify
from typing import Any, Dict, List
import logging
import uuid
import asyncio
import json
import random
import time
from datetime import datetime

from backend.services.rfx_conversation_state_service import RFXConversationStateService
from backend.services.rfx_processing_session_service import RFXProcessingSessionService
from backend.utils.auth_middleware import jwt_required, get_current_user, get_current_user_organization_id

logger = logging.getLogger(__name__)

# Crear blueprint
rfx_chat_bp = Blueprint('rfx_chat', __name__, url_prefix='/api/rfx')


def _create_chat_agent():
    """Importar el agente solo cuando un endpoint de chat lo necesita."""
    from backend.services.chat_agent import ChatAgent

    return ChatAgent()


def _create_chat_service():
    from backend.services.rfx_chat_service import RFXChatService

    return RFXChatService()


def _get_credits_service_instance():
    from backend.services.credits_service import get_credits_service

    return get_credits_service()


def _get_database_client_instance():
    from backend.core.database import get_database_client

    return get_database_client()


def _get_rfx_ownership_validator():
    from backend.utils.rfx_ownership import get_and_validate_rfx_ownership

    return get_and_validate_rfx_ownership


def _get_rfx_processing_types():
    from backend.models.rfx_models import RFXInput, RFXType
    from backend.services.rfx_processor import RFXProcessorService

    return RFXInput, RFXType, RFXProcessorService


def _is_review_phase(conversation_state: dict) -> bool:
    state = (conversation_state or {}).get("state", {}) or {}
    return bool(state.get("review_required", False) and not state.get("review_confirmed", False))


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


def _sync_validated_data_with_preview(preview_data: Dict[str, Any], validated_data: Dict[str, Any]) -> bool:
    """Mantiene validated_data alineado con los campos editables en preview_data."""
    changed = False
    sync_mapping = {
        "requester_name": "nombre_solicitante",
        "company_name": "nombre_empresa",
        "location": "lugar",
        "delivery_date": "fecha",
        "email": "email",
        "requirements": "requirements",
        "description": "description",
        "title": "title",
    }

    for preview_key, validated_key in sync_mapping.items():
        value = preview_data.get(preview_key)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
        if value in ("", None):
            continue
        if validated_data.get(validated_key) != value:
            validated_data[validated_key] = value
            changed = True

    return changed


def _apply_session_field_update(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    field_name: str,
    value: Any,
) -> bool:
    """Aplica un cambio de campo (update_field) usando aliases conocidos."""
    if value is None:
        return False

    normalized_field = str(field_name or "").strip().lower().replace("-", "_")
    if not normalized_field:
        return False

    field_aliases = {
        "client_name": ("requester_name", "nombre_solicitante"),
        "requester_name": ("requester_name", "nombre_solicitante"),
        "nombre_solicitante": ("requester_name", "nombre_solicitante"),
        "cliente_nombre": ("requester_name", "nombre_solicitante"),
        "company_name": ("company_name", "nombre_empresa"),
        "nombre_empresa": ("company_name", "nombre_empresa"),
        "empresa": ("company_name", "nombre_empresa"),
        "delivery_location": ("location", "lugar"),
        "location": ("location", "lugar"),
        "lugar": ("location", "lugar"),
        "delivery_date": ("delivery_date", "fecha"),
        "event_date": ("delivery_date", "fecha"),
        "fecha": ("delivery_date", "fecha"),
        "client_email": ("email", "email"),
        "requester_email": ("email", "email"),
        "email": ("email", "email"),
        "requirements": ("requirements", "requirements"),
        "description": ("description", "description"),
        "title": ("title", "title"),
    }

    target = field_aliases.get(normalized_field)
    if not target:
        return False

    if isinstance(value, str):
        value = value.strip()

    preview_key, validated_key = target
    changed = False

    if preview_data.get(preview_key) != value:
        preview_data[preview_key] = value
        changed = True

    if validated_key and validated_data.get(validated_key) != value:
        validated_data[validated_key] = value
        changed = True

    return changed


def _apply_session_chat_changes(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    changes: List[Any],
) -> bool:
    """
    Aplica defensivamente cambios del agente a la sesión.

    Esto cubre casos donde el agente devuelve JSON de `changes` pero no ejecutó la tool.
    """
    changed = False

    for change in changes or []:
        change_type = getattr(change, "type", None)
        if hasattr(change_type, "value"):
            change_type = change_type.value
        if not change_type and isinstance(change, dict):
            change_type = change.get("type")
        if str(change_type) != "update_field":
            continue

        target = getattr(change, "target", None)
        data = getattr(change, "data", None)
        if isinstance(change, dict):
            target = change.get("target", target)
            data = change.get("data", data)

        if isinstance(data, dict):
            for key, value in data.items():
                if _apply_session_field_update(preview_data, validated_data, str(key), value):
                    changed = True

            if target:
                target_value = None
                if target in data:
                    target_value = data.get(target)
                elif len(data) == 1:
                    target_value = next(iter(data.values()))
                if target_value is not None and _apply_session_field_update(
                    preview_data, validated_data, str(target), target_value
                ):
                    changed = True
        elif target and _apply_session_field_update(preview_data, validated_data, str(target), data):
            changed = True

    if _sync_validated_data_with_preview(preview_data, validated_data):
        changed = True

    return changed


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
            request_context = json.loads(context_str)
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
        
        db = _get_database_client_instance()
        
        rfx = db.get_rfx_by_id(rfx_id)
        if not rfx:
            # Compatibilidad: si llega session_id por endpoint legacy de RFX, enrutar a session flow.
            session_service = RFXProcessingSessionService()
            session = session_service.get_session_for_user(
                rfx_id,
                user_id=user_id,
                organization_id=organization_id,
            )
            if session:
                logger.info(
                    f"↪️ Legacy RFX chat endpoint received session_id={rfx_id}; routing to session chat flow"
                )
                return send_session_chat_message(rfx_id)

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
        
        # 📚 Memoria conversacional por RFX (scope estricto: rfx_id)
        conversation_service = RFXConversationStateService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_state = loop.run_until_complete(conversation_service.get_state(rfx_id))
        recent_events = loop.run_until_complete(conversation_service.get_recent_events(rfx_id, limit=10))
        loop.close()

        in_review_phase = _is_review_phase(conversation_state)

        # 💳 VERIFICAR CRÉDITOS DISPONIBLES (chat normal); en review no consume créditos
        credits_service = _get_credits_service_instance()
        if in_review_phase:
            logger.info(f"✅ Review phase chat for RFX {rfx_id}: credits bypass enabled")
        else:
            has_credits, available, msg = credits_service.check_credits_available(
                organization_id,
                'chat_message',
                user_id=user_id
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
                }), 402

            credits_context = "organization" if organization_id else "personal"
            logger.info(f"✅ Credits verified ({credits_context}): {available} available")

        enriched_context = {
            **(request_context or {}),
            "rfx_id": rfx_id,
            "conversation_state": conversation_state.get("state", {}),
            "conversation_status": conversation_state.get("status", "active"),
            "conversation_requires_clarification": conversation_state.get("requires_clarification", False),
            "recent_events": recent_events,
        }
        
        # 2. Llamar al agente de IA (ÉL DECIDE TODO)
        chat_agent = _create_chat_agent()
        
        # Ejecutar async en sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(
            chat_agent.process_message(
                message=message,
                context=enriched_context,
                rfx_id=rfx_id,
                files=files
            )
        )
        
        loop.close()
        
        # 3. Guardar en historial
        chat_service = _create_chat_service()
        
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

        # Persistir memoria por RFX (estado + eventos)
        loop.run_until_complete(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="user",
                message=message,
                payload={"source": "chat_api"}
            )
        )
        loop.run_until_complete(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="assistant",
                message=response.message,
                payload={
                    "changes_count": len(response.changes),
                    "requires_confirmation": response.requires_confirmation,
                    "confidence": response.confidence,
                }
            )
        )
        current_state_data = conversation_state.get("state", {}) or {}
        if in_review_phase:
            current_state_data["workflow_status"] = "in_review_chat"
            current_state_data["review_required"] = True
            current_state_data["review_confirmed"] = False

        next_status = "clarification" if (response.requires_confirmation or in_review_phase) else "active"
        loop.run_until_complete(
            conversation_service.upsert_state(
                rfx_id=rfx_id,
                state=current_state_data,
                status=next_status,
                last_user_message=message,
                last_assistant_message=response.message,
                requires_clarification=response.requires_confirmation,
            )
        )
        
        loop.close()
        
        # 💳 CONSUMIR CRÉDITO SOLO FUERA DE REVIEW
        if not in_review_phase:
            consume_result = credits_service.consume_credits(
                organization_id=organization_id,
                operation='chat_message',
                rfx_id=rfx_id,
                user_id=user_id,
                description=f"Chat message for RFX {rfx_id}"
            )

            if consume_result["status"] == "success":
                credits_context = "organization" if organization_id else "personal"
                logger.info(f"✅ Credits consumed ({credits_context}): 1 (remaining: {consume_result['credits_remaining']})")
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
            'review_mode': in_review_phase,
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
        
        chat_service = _create_chat_service()
        
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


@rfx_chat_bp.route('/<rfx_id>/review/state', methods=['GET'])
@jwt_required
def get_review_state(rfx_id):
    """Estado de revisión conversacional por RFX."""
    try:
        user = get_current_user()
        user_id = user.get('id') or user.get('sub')
        organization_id = get_current_user_organization_id()

        db = _get_database_client_instance()
        rfx = db.get_rfx_by_id(rfx_id)
        if not rfx:
            # Compatibilidad: session_id llegando por endpoint legacy de RFX.
            session_service = RFXProcessingSessionService()
            session = session_service.get_session_for_user(
                rfx_id,
                user_id=user_id,
                organization_id=organization_id,
            )
            if session:
                logger.info(
                    f"↪️ Legacy review/state endpoint received session_id={rfx_id}; routing to session review state"
                )
                return get_session_review_state(rfx_id)

        _, error = _get_rfx_ownership_validator()(db, rfx_id, user_id, organization_id)
        if error:
            return error

        conversation_service = RFXConversationStateService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_state = loop.run_until_complete(conversation_service.get_state(rfx_id))
        recent_events = loop.run_until_complete(conversation_service.get_recent_events(rfx_id, limit=10))
        loop.close()

        state_data = conversation_state.get("state", {}) or {}
        return jsonify({
            "status": "success",
            "data": {
                "rfx_id": rfx_id,
                "workflow_status": state_data.get("workflow_status", "extracted_pending_review"),
                "review_required": bool(state_data.get("review_required", True)),
                "review_confirmed": bool(state_data.get("review_confirmed", False)),
                "can_proceed_without_answers": bool(state_data.get("can_proceed_without_answers", True)),
                "suggested_first_message": state_data.get("suggested_first_message"),
                "requires_clarification": bool(conversation_state.get("requires_clarification", False)),
                "status": conversation_state.get("status", "clarification"),
                "recent_events": recent_events,
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXReview] Error getting state: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error getting review state"}), 500


@rfx_chat_bp.route('/<rfx_id>/review/confirm', methods=['POST'])
@jwt_required
def confirm_review(rfx_id):
    """Confirma revisión y habilita Data View."""
    try:
        user = get_current_user()
        user_id = user.get('id') or user.get('sub')
        organization_id = get_current_user_organization_id()

        db = _get_database_client_instance()
        rfx = db.get_rfx_by_id(rfx_id)
        if not rfx:
            # Compatibilidad: session_id llegando por endpoint legacy de RFX.
            session_service = RFXProcessingSessionService()
            session = session_service.get_session_for_user(
                rfx_id,
                user_id=user_id,
                organization_id=organization_id,
            )
            if session:
                logger.info(
                    f"↪️ Legacy review/confirm endpoint received session_id={rfx_id}; routing to session confirm"
                )
                return confirm_session_review(rfx_id)

        rfx, error = _get_rfx_ownership_validator()(db, rfx_id, user_id, organization_id)
        if error:
            return error

        products = db.get_rfx_products(rfx_id)
        confirmed_at = datetime.utcnow().isoformat()

        snapshot = {
            "confirmed_at": confirmed_at,
            "confirmed_by": user_id,
            "rfx_context": {
                "id": rfx.get("id"),
                "title": rfx.get("title"),
                "location": rfx.get("location"),
                "delivery_date": rfx.get("delivery_date"),
                "requester_name": (rfx.get("requesters") or {}).get("name") if isinstance(rfx.get("requesters"), dict) else None,
                "company_name": (rfx.get("companies") or {}).get("name") if isinstance(rfx.get("companies"), dict) else None,
            },
            "products": [
                {
                    "id": p.get("id"),
                    "product_name": p.get("product_name"),
                    "quantity": p.get("quantity"),
                    "unit": p.get("unit"),
                    "estimated_unit_price": p.get("estimated_unit_price"),
                    "unit_cost": p.get("unit_cost"),
                    "specifications": p.get("specifications", {}),
                }
                for p in (products or [])
            ],
        }

        conversation_service = RFXConversationStateService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        current_state = loop.run_until_complete(conversation_service.get_state(rfx_id))
        state_data = current_state.get("state", {}) or {}
        state_data.update({
            "workflow_status": "review_confirmed",
            "review_required": True,
            "review_confirmed": True,
            "review_confirmed_by": user_id,
            "review_confirmed_at": confirmed_at,
            "review_snapshot": snapshot,
            "can_proceed_without_answers": True,
        })

        loop.run_until_complete(
            conversation_service.upsert_state(
                rfx_id=rfx_id,
                state=state_data,
                status="ready_for_proposal",
                last_intent="review_confirm",
                last_assistant_message="Revisión confirmada. Ya puedes continuar al Data View.",
                requires_clarification=False,
            )
        )
        loop.run_until_complete(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="system",
                message="Review confirmed by user",
                payload={"confirmed_by": user_id, "confirmed_at": confirmed_at},
            )
        )
        loop.close()

        # Note: processing_status column doesn't exist in rfx_processing_status table
        # Status tracking is handled by rfx_processing_sessions table instead

        return jsonify({
            "status": "success",
            "message": "Revisión confirmada. Continuando a Data View.",
            "data": {
                "rfx_id": rfx_id,
                "workflow_status": "review_confirmed",
                "review_confirmed": True,
                "next_step": "data_view",
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXReview] Error confirming review: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error confirming review"}), 500


@rfx_chat_bp.route('/<rfx_id>/review/reopen', methods=['POST'])
@jwt_required
def reopen_review(rfx_id):
    """Reabre fase de review por RFX."""
    try:
        user = get_current_user()
        user_id = user.get('id') or user.get('sub')
        organization_id = get_current_user_organization_id()

        db = _get_database_client_instance()
        _, error = _get_rfx_ownership_validator()(db, rfx_id, user_id, organization_id)
        if error:
            return error

        conversation_service = RFXConversationStateService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        current_state = loop.run_until_complete(conversation_service.get_state(rfx_id))
        state_data = current_state.get("state", {}) or {}
        state_data.update({
            "workflow_status": "in_review_chat",
            "review_required": True,
            "review_confirmed": False,
            "can_proceed_without_answers": True,
        })

        loop.run_until_complete(
            conversation_service.upsert_state(
                rfx_id=rfx_id,
                state=state_data,
                status="clarification",
                last_intent="review_reopen",
                requires_clarification=True,
            )
        )
        loop.run_until_complete(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="system",
                message="Review reopened",
                payload={"reopened_by": user_id, "reopened_at": datetime.utcnow().isoformat()},
            )
        )
        loop.close()

        # Note: processing_status column doesn't exist in rfx_processing_status table
        # Status tracking is handled by rfx_processing_sessions table instead

        return jsonify({
            "status": "success",
            "message": "Review reabierta",
            "data": {"rfx_id": rfx_id, "workflow_status": "in_review_chat"},
        }), 200
    except Exception as e:
        logger.error(f"[RFXReview] Error reopening review: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error reopening review"}), 500


# =========================
# SESSION-FIRST REVIEW FLOW
# =========================

@rfx_chat_bp.route('/session/<session_id>/chat', methods=['POST'])
@jwt_required
def send_session_chat_message(session_id):
    """Procesa chat conversacional sobre sesión pre-RFX (sin rfx_v2 persistido aún)."""
    correlation_id = str(uuid.uuid4())
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        organization_id = get_current_user_organization_id()

        message = request.form.get('message')
        context_str = request.form.get('context')
        if not message or not context_str:
            return jsonify({"status": "error", "message": "Request inválido: se requiere message y context"}), 400

        try:
            request_context = json.loads(context_str)
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "Context debe ser JSON válido"}), 400

        files = []
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            for file in uploaded_files:
                if file and file.filename:
                    files.append({
                        'name': file.filename,
                        'type': file.content_type or 'application/octet-stream',
                        'content': file.read()
                    })
                    file.seek(0)

        session_service = RFXProcessingSessionService()
        session = session_service.get_session_for_user(session_id, user_id=user_id, organization_id=organization_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found or access denied"}), 404

        preview_data = session.get("preview_data") or {}
        conversation_state = session.get("conversation_state") or {}
        recent_events = session.get("recent_events") or []

        enriched_context = {
            **(request_context or {}),
            "rfx_id": session_id,
            "conversation_state": conversation_state,
            "conversation_status": session.get("status", "clarification"),
            "conversation_requires_clarification": bool(conversation_state.get("requires_clarification", False)),
            "recent_events": recent_events,
            "current_products": preview_data.get("products") or [],
            "delivery_date": preview_data.get("delivery_date"),
            "delivery_location": preview_data.get("location"),
            "client_name": preview_data.get("requester_name"),
            "client_email": preview_data.get("email"),
            "source_text": preview_data.get("source_text", ""),
        }

        chat_agent = _create_chat_agent()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            chat_agent.process_message(
                message=message,
                context=enriched_context,
                rfx_id=session_id,
                files=files
            )
        )
        loop.close()

        # Refrescar snapshot de sesión luego de tool-calls
        updated_session = session_service.get_session(session_id) or session
        updated_preview = dict(updated_session.get("preview_data") or preview_data)
        updated_validated = dict(updated_session.get("validated_data") or (session.get("validated_data") or {}))

        # Aplicar cambios reportados por el agente aunque no haya ejecutado tools.
        # Evita desalineación entre "mensaje" y estado real persistido.
        if _apply_session_chat_changes(updated_preview, updated_validated, response.changes):
            session_service.update_session(
                session_id,
                {
                    "preview_data": updated_preview,
                    "validated_data": updated_validated,
                },
            )
            updated_session = session_service.get_session(session_id) or updated_session
            updated_preview = dict(updated_session.get("preview_data") or updated_preview)

        updated_state = updated_session.get("conversation_state") or conversation_state

        session_service.append_event(
            session_id=session_id,
            role="user",
            message=message,
            payload={"source": "session_chat_api"}
        )
        session_service.append_event(
            session_id=session_id,
            role="assistant",
            message=response.message,
            payload={
                "changes_count": len(response.changes),
                "requires_confirmation": response.requires_confirmation,
                "confidence": response.confidence,
            }
        )

        updated_state["workflow_status"] = "in_review_chat"
        updated_state["review_required"] = True
        updated_state["review_confirmed"] = False
        updated_state["requires_clarification"] = bool(response.requires_confirmation)

        session_service.update_session(
            session_id,
            {
                "conversation_state": updated_state,
                "status": "clarification" if response.requires_confirmation else "active",
            }
        )

        return jsonify({
            "status": "success",
            "message": response.message,
            "confidence": response.confidence,
            "changes": [change.dict() for change in response.changes],
            "requires_confirmation": response.requires_confirmation,
            "review_mode": True,
            "refresh": {
                "needs_refresh": True,
                "scope": "full",
                "components": ["products", "pricing", "totals", "details"],
            },
            "preview_data": updated_preview,
            "metadata": {
                "correlation_id": correlation_id,
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXSessionChat] Error processing message: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Lo siento, ocurrió un error al procesar tu mensaje.",
            "confidence": 0.0,
            "changes": [],
            "requires_confirmation": False,
            "options": [],
            "metadata": {
                "correlation_id": correlation_id,
                "error": str(e)
            }
        }), 500


@rfx_chat_bp.route('/session/<session_id>/review/state', methods=['GET'])
@jwt_required
def get_session_review_state(session_id):
    """Estado de review para sesión pre-RFX."""
    try:
        user = get_current_user()
        user_id = user.get('id') or user.get('sub')
        organization_id = get_current_user_organization_id()

        session_service = RFXProcessingSessionService()
        session = session_service.get_session_for_user(session_id, user_id=user_id, organization_id=organization_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found or access denied"}), 404

        state_data = session.get("conversation_state") or {}
        return jsonify({
            "status": "success",
            "data": {
                "rfx_id": session_id,
                "session_id": session_id,
                "entity_type": "session",
                "workflow_status": state_data.get("workflow_status", "extracted_pending_review"),
                "review_required": bool(state_data.get("review_required", True)),
                "review_confirmed": bool(session.get("review_confirmed", False)),
                "can_proceed_without_answers": bool(state_data.get("can_proceed_without_answers", True)),
                "suggested_first_message": state_data.get("suggested_first_message"),
                "requires_clarification": bool(state_data.get("requires_clarification", False)),
                "status": session.get("status", "clarification"),
                "recent_events": session.get("recent_events") or [],
                "preview_data": session.get("preview_data") or {},
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXSessionReview] Error getting state: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error getting session review state"}), 500


@rfx_chat_bp.route('/session/<session_id>/review/confirm', methods=['POST'])
@jwt_required
def confirm_session_review(session_id):
    """Confirma sesión pre-RFX y persiste rfx_v2 + rfx_products."""
    try:
        user = get_current_user()
        user_id = user.get('id') or user.get('sub')
        organization_id = get_current_user_organization_id()

        session_service = RFXProcessingSessionService()
        session = session_service.get_session_for_user(session_id, user_id=user_id, organization_id=organization_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found or access denied"}), 404

        already_confirmed = bool(session.get("review_confirmed")) and session.get("confirmed_rfx_id")
        if already_confirmed:
            return jsonify({
                "status": "success",
                "message": "Session already confirmed.",
                "data": {
                    "rfx_id": session.get("confirmed_rfx_id"),
                    "workflow_status": "review_confirmed",
                    "review_confirmed": True,
                    "next_step": "data_view",
                }
            }), 200

        preview_data = dict(session.get("preview_data") or {})
        validated_data = dict(session.get("validated_data") or {})

        # Asegurar consistencia entre snapshot de preview y payload persistible.
        _sync_validated_data_with_preview(preview_data, validated_data)

        # Fuente de verdad en revisión conversacional: preview_data.products
        # (los tools de sesión actualizan este snapshot en tiempo real).
        preview_products = list(preview_data.get("products") or [])
        if preview_products:
            validated_data["productos"] = preview_products
        evaluation_metadata = session.get("evaluation_metadata") or {}

        rfx_temp_id = f"RFX-{int(time.time())}-{random.randint(1000, 9999)}"
        rfx_type_raw = str(preview_data.get("rfx_type") or "catering").lower()
        RFXInput, RFXType, RFXProcessorService = _get_rfx_processing_types()
        try:
            rfx_type = RFXType(rfx_type_raw)
        except Exception:
            rfx_type = RFXType.CATERING

        rfx_input = RFXInput(id=rfx_temp_id, rfx_type=rfx_type)
        rfx_input.extracted_content = str(preview_data.get("source_text") or "")

        processor_service = RFXProcessorService()
        rfx_processed = processor_service._create_rfx_processed(validated_data, rfx_input, evaluation_metadata)
        processor_service._save_rfx_to_database(rfx_processed, user_id=user_id, organization_id=organization_id)
        final_rfx_id = str(rfx_processed.id)

        # Estado de conversación final ya asociado al rfx real
        conversation_service = RFXConversationStateService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            conversation_service.upsert_state(
                rfx_id=final_rfx_id,
                state={
                    "workflow_status": "review_confirmed",
                    "review_required": True,
                    "review_confirmed": True,
                    "can_proceed_without_answers": True,
                    "review_confirmed_by": user_id,
                    "review_confirmed_at": datetime.utcnow().isoformat(),
                },
                status="ready_for_proposal",
                last_intent="review_confirm_session",
                last_assistant_message="Revisión confirmada. Ya puedes continuar al Data View.",
                requires_clarification=False,
            )
        )
        loop.close()

        # Consumir créditos de extracción al confirmar persistencia
        credits_service = _get_credits_service_instance()
        try:
            consume_result = credits_service.consume_credits(
                organization_id=organization_id,
                operation='extraction',
                rfx_id=final_rfx_id,
                user_id=user_id,
                description=f"RFX extraction confirmed from session {session_id}"
            )
            if consume_result.get("status") != "success":
                logger.error(f"❌ Failed to consume extraction credits on confirm: {consume_result}")
        except Exception as consume_err:
            logger.error(f"❌ Error consuming extraction credits on confirm: {consume_err}")

        db = _get_database_client_instance()
        db.upsert_processing_status(final_rfx_id, {
            "has_extracted_data": True,
            "has_generated_proposal": False,
            "extraction_completed_at": datetime.utcnow().isoformat(),
            "generation_completed_at": None,
            "processing_status": "review_confirmed",
        })

        session_service.mark_confirmed(session_id, final_rfx_id)
        session_service.update_session(
            session_id,
            {
                "status": "confirmed",
                "review_confirmed": True,
            }
        )
        session_service.append_event(
            session_id=session_id,
            role="system",
            message="Review confirmed and RFX persisted",
            payload={"final_rfx_id": final_rfx_id},
        )

        return jsonify({
            "status": "success",
            "message": "Revisión confirmada. RFX creado y listo para Data View.",
            "data": {
                "rfx_id": final_rfx_id,
                "workflow_status": "review_confirmed",
                "review_confirmed": True,
                "next_step": "data_view",
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXSessionReview] Error confirming session review: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error confirming session review"}), 500


# Exportar blueprint
__all__ = ['rfx_chat_bp']
