"""
API endpoints para el chat conversacional RFX.

KISS: Endpoints simples que delegan todo a los servicios.
Sin lógica de negocio en los endpoints.
"""

from flask import Blueprint, request, jsonify
from typing import Any, Dict, List, Optional
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


def _create_session_review_chat_service():
    from backend.services.session_review_chat_service import SessionReviewChatService

    return SessionReviewChatService()


def _create_data_view_chat_service():
    from backend.services.data_view_chat_service import DataViewChatService

    return DataViewChatService()


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


def _get_product_resolution_service():
    from backend.services.product_resolution_service import ProductResolutionService

    return ProductResolutionService()


def _get_catalog_search_service_for_rfx():
    from backend.services.catalog_helpers import get_catalog_search_service_for_rfx

    return get_catalog_search_service_for_rfx()


def _get_pricing_configuration_types():
    from backend.models.pricing_models import PricingConfigurationRequest
    from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2

    return PricingConfigurationRequest, PricingConfigurationServiceV2


def _generate_initial_proposal_for_rfx(
    rfx_id: str,
    user_id: str,
    organization_id: Optional[str],
) -> Dict[str, Any]:
    from backend.models.proposal_models import ProposalRequest
    from backend.services.proposal_generator import ProposalGenerationService
    from backend.utils.data_mappers import map_rfx_data_for_proposal

    db = _get_database_client_instance()
    existing_proposals = db.get_proposals_by_rfx_id(rfx_id)
    if existing_proposals:
        return existing_proposals[0]

    rfx_data = db.get_rfx_by_id(rfx_id)
    if not rfx_data:
        raise ValueError("RFX not found for proposal generation")

    rfx_products = db.get_rfx_products(rfx_id) or []
    mapped_rfx_data = map_rfx_data_for_proposal(rfx_data, rfx_products)
    mapped_rfx_data["user_id"] = user_id

    extracted_costs = [
        float(
            product.get("estimated_unit_price")
            or product.get("unit_price")
            or product.get("precio_unitario")
            or 0.0
        )
        for product in rfx_products
    ]
    if not extracted_costs:
        fallback_products = mapped_rfx_data.get("productos") or []
        extracted_costs = [
            float(
                product.get("estimated_unit_price")
                or product.get("unit_price")
                or product.get("precio_unitario")
                or 0.0
            )
            for product in fallback_products
        ]
    if not extracted_costs:
        extracted_costs = [0.0]

    credits_service = _get_credits_service_instance()
    has_credits, available, msg = credits_service.check_credits_available(
        organization_id,
        "generation",
        user_id=user_id,
    )
    if not has_credits:
        raise ValueError(msg or f"Not enough credits to generate the proposal ({available} available).")

    proposal_request = ProposalRequest(rfx_id=rfx_id, costs=extracted_costs)
    generator = ProposalGenerationService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        proposal = loop.run_until_complete(generator.generate_proposal(mapped_rfx_data, proposal_request))
    finally:
        loop.close()

    try:
        consume_result = credits_service.consume_credits(
            organization_id=organization_id,
            operation="generation",
            rfx_id=rfx_id,
            user_id=user_id,
            description=f"Automatic proposal generation after review confirmation for RFX {rfx_id}",
        )
        if consume_result.get("status") != "success":
            logger.error("❌ Failed to consume generation credits after review confirm: %s", consume_result)
    except Exception as consume_err:
        logger.error("❌ Error consuming generation credits after review confirm: %s", consume_err)

    db.upsert_processing_status(rfx_id, {
        "has_extracted_data": True,
        "has_generated_proposal": True,
        "extraction_completed_at": datetime.utcnow().isoformat(),
        "generation_completed_at": datetime.utcnow().isoformat(),
        "processing_status": "proposal_generated",
    })

    return {
        "id": str(getattr(proposal, "id", "")),
    }


def _resolve_rfx_type_for_industry(industry_context: str | None) -> str:
    normalized = str(industry_context or "services").strip().lower()
    return "catering" if normalized == "corporate_catering" else "services"


def _resolve_business_unit_context(organization_id: str | None, business_unit_id: str | None) -> Dict[str, Any] | None:
    if not organization_id:
        if business_unit_id:
            raise ValueError("business_unit_id requires an organization")
        return None

    if not business_unit_id:
        return None

    db = _get_database_client_instance()
    response = (
        db.client
        .table("business_units")
        .select("id, organization_id, name, slug, industry_context, is_default, is_active")
        .eq("organization_id", organization_id)
        .eq("id", business_unit_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise ValueError("Invalid business_unit_id for the current organization")
    return response.data[0]


def _apply_review_pricing_config(rfx_id: str, pricing_config: Dict[str, Any]) -> bool:
    if not pricing_config:
        return False

    PricingConfigurationRequest, PricingConfigurationServiceV2 = _get_pricing_configuration_types()
    pricing_request = PricingConfigurationRequest(
        rfx_id=rfx_id,
        coordination_enabled=bool(pricing_config.get("coordination_enabled", False)),
        coordination_rate=pricing_config.get("coordination_rate"),
        coordination_level=pricing_config.get("coordination_level"),
        cost_per_person_enabled=bool(pricing_config.get("cost_per_person_enabled", False)),
        headcount=pricing_config.get("headcount"),
        per_person_display=True,
        taxes_enabled=bool(pricing_config.get("taxes_enabled", False)),
        tax_rate=pricing_config.get("tax_rate"),
        tax_type=pricing_config.get("tax_name") or pricing_config.get("tax_type") or "IVA",
    )
    pricing_service = PricingConfigurationServiceV2()
    updated_config = pricing_service.update_rfx_pricing_from_request(pricing_request)
    return bool(updated_config)


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


def _run_async(coro):
    """Run an async coroutine from sync Flask endpoints without leaking loops."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def _process_persisted_rfx_chat_with_fallback(
    *,
    rfx_id: str,
    message: str,
    context: Dict[str, Any],
    files: List[Dict[str, Any]],
) -> tuple[Any, str, List[Dict[str, str]]]:
    """
    Prefer the legacy ChatAgent when available, but fall back to the lightweight
    structured chat service instead of surfacing a 500 to the user.
    """
    backend_errors: List[Dict[str, str]] = []

    try:
        chat_agent = _create_chat_agent()
        response = _run_async(
            chat_agent.process_message(
                message=message,
                context=context,
                rfx_id=rfx_id,
                files=files,
            )
        )
        return response, "legacy_chat_agent", backend_errors
    except Exception as legacy_error:
        logger.warning(
            "⚠️ Legacy ChatAgent unavailable for RFX %s, switching to fallback service: %s",
            rfx_id,
            legacy_error,
            exc_info=True,
        )
        backend_errors.append(
            {
                "backend": "legacy_chat_agent",
                "error_type": type(legacy_error).__name__,
                "message": str(legacy_error),
            }
        )

    try:
        fallback_service = _create_data_view_chat_service()
        response = fallback_service.process_message(
            rfx_id=rfx_id,
            message=message,
            context=context,
            files=files,
        )
        return response, "fallback_structured_chat", backend_errors
    except Exception as fallback_error:
        logger.error(
            "❌ Fallback Data View chat also failed for RFX %s: %s",
            rfx_id,
            fallback_error,
            exc_info=True,
        )
        backend_errors.append(
            {
                "backend": "fallback_structured_chat",
                "error_type": type(fallback_error).__name__,
                "message": str(fallback_error),
            }
        )
        raise RuntimeError("No chat backends available for persisted RFX chat")


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


def _build_session_resolution_context(preview_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_text": str(preview_data.get("source_text") or ""),
        "rfx_type": preview_data.get("rfx_type"),
        "location": preview_data.get("location"),
        "delivery_date": preview_data.get("delivery_date"),
        "business_unit_id": preview_data.get("business_unit_id"),
    }


def _resolve_session_products(
    products: List[Dict[str, Any]],
    preview_data: Dict[str, Any],
    organization_id: Optional[str],
) -> List[Dict[str, Any]]:
    resolver = _get_product_resolution_service()
    try:
        resolver.catalog_search = _get_catalog_search_service_for_rfx()
    except Exception as catalog_error:
        logger.warning("⚠️ Catalog service unavailable in session chat: %s", catalog_error)
        resolver.catalog_search = None

    return resolver.resolve_for_chat_products(
        products=products,
        organization_id=organization_id,
        rfx_context=_build_session_resolution_context(preview_data),
    )


def _build_session_preview_product_record(product: Dict[str, Any], product_id: Optional[str] = None) -> Dict[str, Any]:
    qty = float(product.get("cantidad") or product.get("quantity") or 1)
    price = float(
        product.get("precio_unitario")
        if product.get("precio_unitario") is not None
        else product.get("estimated_unit_price", product.get("unit_price", 0))
    )
    cost = float(
        product.get("costo_unitario")
        if product.get("costo_unitario") is not None
        else product.get("unit_cost", 0)
    )
    specs = product.get("specifications") or product.get("especificaciones") or {}
    breakdown = product.get("bundle_breakdown") or specs.get("bundle_breakdown") or []
    requires_clarification = bool(product.get("requires_clarification", False))

    return {
        "id": product_id or str(product.get("id") or uuid.uuid4()),
        "nombre": product.get("nombre") or product.get("name") or product.get("product_name"),
        "descripcion": product.get("descripcion") or product.get("description") or "",
        "cantidad": qty,
        "unidad": product.get("unidad") or product.get("unit") or "unidades",
        "precio_unitario": price,
        "estimated_unit_price": price,
        "costo_unitario": cost,
        "unit_cost": cost,
        "total_estimated_cost": float(product.get("estimated_line_total") or (qty * price)),
        "estimated_line_total": float(product.get("estimated_line_total") or (qty * price)),
        "notas": product.get("notas") or product.get("notes") or "",
        "specifications": specs or {
            "is_bundle": bool(breakdown),
            "inferred_bundle": False,
            "requires_clarification": requires_clarification,
            "bundle_breakdown": breakdown,
        },
        "especificaciones": specs or {
            "is_bundle": bool(breakdown),
            "inferred_bundle": False,
            "requires_clarification": requires_clarification,
            "bundle_breakdown": breakdown,
        },
        "bundle_breakdown": breakdown,
        "requires_clarification": requires_clarification,
    }


def _find_session_product_index(
    products: List[Dict[str, Any]],
    target: Optional[str],
    data: Optional[Dict[str, Any]] = None,
) -> int:
    normalized_target = str(target or "").strip().lower()
    if normalized_target:
        for idx, product in enumerate(products):
            if str(product.get("id") or "").strip().lower() == normalized_target:
                return idx

    candidate_names = [
        str((data or {}).get("nombre") or "").strip().lower(),
        str((data or {}).get("name") or "").strip().lower(),
        str((data or {}).get("product_name") or "").strip().lower(),
        normalized_target,
    ]
    candidate_names = [name for name in candidate_names if name]

    for candidate_name in candidate_names:
        for idx, product in enumerate(products):
            product_name = str(
                product.get("nombre")
                or product.get("product_name")
                or product.get("name")
                or ""
            ).strip().lower()
            if product_name == candidate_name:
                return idx

    return -1


def _apply_session_product_add(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    data: Dict[str, Any],
    organization_id: Optional[str],
) -> bool:
    resolved_products = _resolve_session_products([data], preview_data, organization_id)
    if not resolved_products:
        return False

    preview_products = list(preview_data.get("products") or [])
    validated_products = list(validated_data.get("productos") or preview_products)
    changed = False

    for resolved_product in resolved_products:
        record = _build_session_preview_product_record(resolved_product)
        preview_products.append(record)
        validated_products.append(record)
        changed = True

    if changed:
        preview_data["products"] = preview_products
        validated_data["productos"] = validated_products

    return changed


def _apply_session_product_update(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    target: Optional[str],
    data: Dict[str, Any],
    organization_id: Optional[str],
) -> bool:
    preview_products = list(preview_data.get("products") or [])
    product_index = _find_session_product_index(preview_products, target, data)
    if product_index < 0:
        return False

    current = dict(preview_products[product_index])
    merged = {
        "nombre": data.get("nombre") or data.get("name") or data.get("product_name") or current.get("nombre"),
        "cantidad": (
            data.get("cantidad")
            if data.get("cantidad") is not None
            else data.get("quantity", current.get("cantidad", current.get("quantity", 1)))
        ),
        "unidad": data.get("unidad") or data.get("unit") or current.get("unidad") or current.get("unit") or "unidades",
        "precio_unitario": (
            data.get("precio_unitario")
            if data.get("precio_unitario") is not None
            else data.get("price_unit", data.get("unit_price", current.get("precio_unitario", current.get("estimated_unit_price", 0))))
        ),
        "costo_unitario": (
            data.get("costo_unitario")
            if data.get("costo_unitario") is not None
            else data.get("unit_cost", current.get("costo_unitario", current.get("unit_cost", 0)))
        ),
        "descripcion": data.get("descripcion") or data.get("description") or current.get("descripcion", current.get("description", "")),
        "notas": data.get("notas") or data.get("notes") or current.get("notas", current.get("notes", "")),
        "specifications": data.get("specifications") or data.get("especificaciones") or current.get("specifications") or current.get("especificaciones") or {},
    }
    if isinstance(data.get("bundle_breakdown"), list):
        merged["bundle_breakdown"] = data.get("bundle_breakdown")

    resolved_products = _resolve_session_products([merged], preview_data, organization_id)
    resolved_product = resolved_products[0] if resolved_products else merged

    updated_record = _build_session_preview_product_record(
        resolved_product,
        product_id=str(current.get("id") or uuid.uuid4()),
    )
    preview_products[product_index] = updated_record
    preview_data["products"] = preview_products
    validated_data["productos"] = preview_products
    return True


def _apply_session_product_delete(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    target: Optional[str],
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    preview_products = list(preview_data.get("products") or [])
    product_index = _find_session_product_index(preview_products, target, data)
    if product_index < 0:
        return False

    del preview_products[product_index]
    preview_data["products"] = preview_products
    validated_data["productos"] = preview_products
    return True


def _apply_session_chat_changes(
    preview_data: Dict[str, Any],
    validated_data: Dict[str, Any],
    changes: List[Any],
    organization_id: Optional[str] = None,
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

        target = getattr(change, "target", None)
        data = getattr(change, "data", None)
        if isinstance(change, dict):
            target = change.get("target", target)
            data = change.get("data", data)

        if not isinstance(data, dict):
            data = {}

        if str(change_type) == "add_product":
            if _apply_session_product_add(preview_data, validated_data, data, organization_id):
                changed = True
            continue

        if str(change_type) == "update_product":
            if _apply_session_product_update(preview_data, validated_data, target, data, organization_id):
                changed = True
            continue

        if str(change_type) == "delete_product":
            if _apply_session_product_delete(preview_data, validated_data, target, data):
                changed = True
            continue

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
        conversation_state = _run_async(conversation_service.get_state(rfx_id))
        recent_events = _run_async(conversation_service.get_recent_events(rfx_id, limit=10))

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
        
        # 2. Procesar mensaje con el backend de chat disponible.
        # Preferimos el agente legacy si está sano; si no, usamos el servicio
        # estructurado ligero para no romper la UX del Data View.
        response, chat_backend, backend_errors = _process_persisted_rfx_chat_with_fallback(
            rfx_id=rfx_id,
            message=message,
            context=enriched_context,
            files=files,
        )
        
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
        
        _run_async(
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
                model_used=(
                    f"{chat_backend}:{response.metadata.model_used}"
                    if response.metadata and response.metadata.model_used
                    else chat_backend
                )
            )
        )

        # Persistir memoria por RFX (estado + eventos)
        _run_async(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="user",
                message=message,
                payload={"source": "chat_api"}
            )
        )
        _run_async(
            conversation_service.add_event(
                rfx_id=rfx_id,
                role="assistant",
                message=response.message,
                payload={
                    "changes_count": len(response.changes),
                    "requires_confirmation": response.requires_confirmation,
                    "confidence": response.confidence,
                    "chat_backend": chat_backend,
                }
            )
        )
        current_state_data = conversation_state.get("state", {}) or {}
        if in_review_phase:
            current_state_data["workflow_status"] = "in_review_chat"
            current_state_data["review_required"] = True
            current_state_data["review_confirmed"] = False

        next_status = "clarification" if (response.requires_confirmation or in_review_phase) else "active"
        _run_async(
            conversation_service.upsert_state(
                rfx_id=rfx_id,
                state=current_state_data,
                status=next_status,
                last_user_message=message,
                last_assistant_message=response.message,
                requires_clarification=response.requires_confirmation,
            )
        )
        
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
            },
            'metadata': {
                'correlation_id': correlation_id,
                'chat_backend': chat_backend,
                'degraded_mode': chat_backend != 'legacy_chat_agent',
                'backend_errors': backend_errors,
                'model_used': getattr(response.metadata, 'model_used', None) if response.metadata else None,
            },
        }), 200
        
    except Exception as e:
        logger.error(
            f"[RFXChat] Error processing message: {e}",
            exc_info=True,
            extra={'correlation_id': correlation_id}
        )
        
        return jsonify({
            'status': 'error',
            'message': (
                'Conversational edits are temporarily unavailable right now. '
                'You can still update products and request details manually in Data View.'
            ),
            'confidence': 0.0,
            'changes': [],
            'requires_confirmation': False,
            'options': [],
            'metadata': {
                'correlation_id': correlation_id,
                'error': str(e),
                'chat_backend': 'unavailable',
                'retryable': True,
            }
        }), 503


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

        review_chat_service = _create_session_review_chat_service()
        response = review_chat_service.process_message(
            session_id=session_id,
            message=message,
            context=enriched_context,
            files=files,
        )

        # Refrescar snapshot de sesión luego de tool-calls
        updated_session = session_service.get_session(session_id) or session
        updated_preview = dict(updated_session.get("preview_data") or preview_data)
        updated_validated = dict(updated_session.get("validated_data") or (session.get("validated_data") or {}))

        # Aplicar cambios reportados por el agente aunque no haya ejecutado tools.
        # Evita desalineación entre "mensaje" y estado real persistido.
        if _apply_session_chat_changes(
            updated_preview,
            updated_validated,
            response.changes,
            organization_id=organization_id,
        ):
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
                "model_used": getattr(response.metadata, "model_used", None) if response.metadata else None,
            }
        }), 200
    except Exception as e:
        logger.error(f"[RFXSessionChat] Error processing message: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Conversational review adjustments are unavailable right now.",
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
        workflow_status = state_data.get("workflow_status", "extracted_pending_review")
        preview_error = None
        if workflow_status == "preview_failed":
            recent_events = session.get("recent_events") or []
            if recent_events:
                preview_error = str((recent_events[-1] or {}).get("message") or "").strip() or "Preview extraction failed"
            else:
                preview_error = "Preview extraction failed"
        return jsonify({
            "status": "success",
            "data": {
                "rfx_id": session_id,
                "session_id": session_id,
                "confirmed_rfx_id": session.get("confirmed_rfx_id"),
                "entity_type": "session",
                "workflow_status": workflow_status,
                "review_required": bool(state_data.get("review_required", True)),
                "review_confirmed": bool(session.get("review_confirmed", False)),
                "can_proceed_without_answers": bool(state_data.get("can_proceed_without_answers", True)),
                "suggested_first_message": state_data.get("suggested_first_message"),
                "requires_clarification": bool(state_data.get("requires_clarification", False)),
                "status": session.get("status", "clarification"),
                "preview_ready": workflow_status not in {"processing_preview", "preview_failed"},
                "preview_error": preview_error,
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
        payload = request.get_json(silent=True) or {}

        session_service = RFXProcessingSessionService()
        session = session_service.get_session_for_user(session_id, user_id=user_id, organization_id=organization_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found or access denied"}), 404
        session_state = session.get("conversation_state") or {}
        workflow_status = str(session_state.get("workflow_status") or "").strip().lower()
        if workflow_status == "processing_preview":
            return jsonify({
                "status": "error",
                "message": "Preview extraction is still running. Wait for the review to finish loading before confirming.",
            }), 409
        if workflow_status == "preview_failed":
            return jsonify({
                "status": "error",
                "message": "Preview extraction failed. Retry the intake before confirming this review.",
            }), 409

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
        if not preview_data:
            return jsonify({
                "status": "error",
                "message": "Preview data is not ready yet. Refresh the review and try again.",
            }), 409
        requested_business_unit_id = str(
            payload.get("business_unit_id")
            or preview_data.get("business_unit_id")
            or ""
        ).strip() or None
        business_unit = _resolve_business_unit_context(organization_id, requested_business_unit_id)
        if organization_id and not business_unit:
            return jsonify({
                "status": "error",
                "message": "business_unit_id is required for organization review confirmation",
            }), 400
        if business_unit:
            preview_data["business_unit_id"] = business_unit["id"]
            preview_data["industry_context"] = business_unit.get("industry_context") or preview_data.get("industry_context") or "services"
            validated_data["industry_context"] = preview_data["industry_context"]

        # Asegurar consistencia entre snapshot de preview y payload persistible.
        _sync_validated_data_with_preview(preview_data, validated_data)

        # Fuente de verdad en revisión conversacional: preview_data.products
        # (los tools de sesión actualizan este snapshot en tiempo real).
        preview_products = list(preview_data.get("products") or [])
        if preview_products:
            validated_data["productos"] = preview_products
        evaluation_metadata = session.get("evaluation_metadata") or {}
        business_unit_id = str(preview_data.get("business_unit_id") or "").strip() or None
        industry_context = str(preview_data.get("industry_context") or validated_data.get("industry_context") or "services").strip().lower()

        rfx_temp_id = f"RFX-{int(time.time())}-{random.randint(1000, 9999)}"
        rfx_type_raw = str(preview_data.get("rfx_type") or _resolve_rfx_type_for_industry(industry_context)).lower()
        RFXInput, RFXType, RFXProcessorService = _get_rfx_processing_types()
        try:
            rfx_type = RFXType(rfx_type_raw)
        except Exception:
            fallback_type = _resolve_rfx_type_for_industry(industry_context)
            rfx_type = RFXType.CATERING if fallback_type == "catering" else RFXType.SERVICES

        rfx_input = RFXInput(
            id=rfx_temp_id,
            rfx_type=rfx_type,
            business_unit_id=business_unit_id,
            industry_context=industry_context,
        )
        rfx_input.extracted_content = str(preview_data.get("source_text") or "")

        processor_service = RFXProcessorService()
        rfx_processed = processor_service._create_rfx_processed(validated_data, rfx_input, evaluation_metadata)
        processor_service._save_rfx_to_database(
            rfx_processed,
            user_id=user_id,
            organization_id=organization_id,
            business_unit_id=business_unit_id,
            industry_context=industry_context,
        )
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

        pricing_config_applied = False
        pricing_config_error = None
        raw_pricing_config = payload.get("pricing_config")
        if isinstance(raw_pricing_config, dict) and raw_pricing_config:
            try:
                pricing_config_applied = _apply_review_pricing_config(final_rfx_id, raw_pricing_config)
            except Exception as pricing_err:
                pricing_config_error = str(pricing_err)
                logger.error("❌ Failed to apply review pricing config before proposal generation: %s", pricing_err, exc_info=True)

        proposal_generated = False
        proposal_id = None
        proposal_error = None
        proposal_skipped = False

        # Conditional auto-generation: only if total_estimated > 0
        total_estimated = sum(
            float(
                p.get("total_estimated_cost")
                or p.get("line_total")
                or (
                    (float(p.get("quantity") or p.get("cantidad") or 0))
                    * float(p.get("estimated_unit_price") or p.get("unit_price") or p.get("precio_unitario") or 0)
                )
            )
            for p in preview_products
        ) if preview_products else 0.0

        if total_estimated > 0:
            try:
                generated_proposal = _generate_initial_proposal_for_rfx(
                    rfx_id=final_rfx_id,
                    user_id=user_id,
                    organization_id=organization_id,
                )
                proposal_id = str(generated_proposal.get("id") or "")
                proposal_generated = bool(proposal_id)
            except Exception as proposal_err:
                proposal_error = str(proposal_err)
                logger.error("❌ Proposal generation after review confirm failed: %s", proposal_err, exc_info=True)
        else:
            proposal_skipped = True
            logger.info("⏭️ Skipping auto-proposal generation: total_estimated=%.2f (no pricing data yet)", total_estimated)

        session_service.mark_confirmed(session_id, final_rfx_id)
        session_service.update_session(
            session_id,
            {
                "status": "confirmed",
                "review_confirmed": True,
            }
        )
        if proposal_skipped:
            confirm_message = "Review confirmed. Opportunity created. Configure pricing in the Data View to generate a proposal."
        elif proposal_generated:
            confirm_message = "Review confirmed, RFX persisted, and proposal generated."
        else:
            confirm_message = "Review confirmed and RFX persisted, but proposal generation needs attention."

        session_service.append_event(
            session_id=session_id,
            role="system",
            message=confirm_message,
            payload={
                "final_rfx_id": final_rfx_id,
                "proposal_generated": proposal_generated,
                "proposal_id": proposal_id,
                "proposal_error": proposal_error,
                "proposal_skipped": proposal_skipped,
                "total_estimated": total_estimated,
                "pricing_config_applied": pricing_config_applied,
                "pricing_config_error": pricing_config_error,
            },
        )

        return jsonify({
            "status": "success",
            "message": confirm_message,
            "data": {
                "rfx_id": final_rfx_id,
                "workflow_status": "review_confirmed",
                "review_confirmed": True,
                "next_step": "opportunity_detail",
                "proposal_generated": proposal_generated,
                "proposal_id": proposal_id,
                "proposal_error": proposal_error,
                "proposal_skipped": proposal_skipped,
                "total_estimated": total_estimated,
                "pricing_config_applied": pricing_config_applied,
                "pricing_config_error": pricing_config_error,
            }
        }), 200
    except ValueError as e:
        logger.warning(f"[RFXSessionReview] Validation error confirming session review: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"[RFXSessionReview] Error confirming session review: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error confirming session review"}), 500


# Exportar blueprint
__all__ = ['rfx_chat_bp']
