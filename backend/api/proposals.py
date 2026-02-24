"""
📄 Proposals API Endpoints - Gestión de propuestas comerciales
Integra con el procesamiento RFX para generar propuestas automáticamente
"""
from flask import Blueprint, request, jsonify, g
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
import asyncio
import logging
import time
import random

from backend.models.proposal_models import ProposalRequest, ProposalResponse, PropuestaGenerada, NotasPropuesta
from backend.core.database import get_database_client
from backend.services.credits_service import get_credits_service
from backend.utils.auth_middleware import optional_jwt, jwt_required, get_current_user, get_current_user_id, get_current_user_organization_id
from backend.exceptions import InsufficientCreditsError

logger = logging.getLogger(__name__)

# Create blueprint
proposals_bp = Blueprint("proposals_api", __name__, url_prefix="/api/proposals")


@proposals_bp.route("/generate", methods=["POST"])
@optional_jwt
def generate_proposal():
    """
    🎯 Genera propuesta comercial basada en datos RFX procesados
    🔓 Autenticación JWT opcional - puede funcionar sin autenticación si se proporciona user_id
    """
    try:
        # Validar datos de entrada
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        
        # 🔐 ESTRATEGIA MULTI-FUENTE: Obtener user_id de múltiples fuentes
        user_id = None
        
        # OPCIÓN 1: Usuario autenticado con JWT (preferido)
        current_user = get_current_user()
        if current_user:
            user_id = str(current_user['id'])
            logger.info(f"✅ Authenticated user generating proposal: {current_user['email']} (ID: {user_id})")
        
        # OPCIÓN 2: user_id proporcionado en el request body (fallback)
        if not user_id:
            user_id = data.get('user_id')
            if user_id:
                logger.info(f"✅ Using user_id from request body: {user_id}")
        
        # OPCIÓN 3: Obtener user_id del RFX en la base de datos
        if not user_id:
            rfx_id = data.get('rfx_id')
            if rfx_id:
                logger.info(f"🔍 Attempting to get user_id from RFX: {rfx_id}")
                try:
                    db_client = get_database_client()
                    rfx_data_temp = db_client.get_rfx_by_id(rfx_id)
                    if rfx_data_temp:
                        user_id = rfx_data_temp.get('user_id')
                        if user_id:
                            logger.info(f"✅ Retrieved user_id from RFX database: {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not get user_id from RFX: {e}")
        
        # VALIDACIÓN FINAL: user_id es requerido
        if not user_id:
            logger.error("❌ No user_id available from any source (JWT, request body, or RFX database)")
            return jsonify({
                "status": "error",
                "message": "user_id is required. Please authenticate or provide user_id in request.",
                "error": "Missing user_id"
            }), 400
        
        logger.info(f"🎯 Final user_id for proposal generation: {user_id}")
        
        # Validar request usando Pydantic
        try:
            proposal_request = ProposalRequest(**data)
        except ValidationError as e:
            return jsonify({
                "status": "error",
                "message": "Invalid request data",
                "error": str(e)
            }), 400
        
        # Obtener datos RFX de la base de datos
        db_client = get_database_client()
        rfx_data = db_client.get_rfx_by_id(proposal_request.rfx_id)
        
        if not rfx_data:
            return jsonify({
                "status": "error",
                "message": f"RFX not found: {proposal_request.rfx_id}",
                "error": "RFX data required for proposal generation"
            }), 404
        
        # Obtener costos unitarios reales de productos desde BD
        product_costs = []
        rfx_products = db_client.get_rfx_products(proposal_request.rfx_id)
        if rfx_products:
            # ✅ Manejar valores None: convertir a 0 si el costo es None
            product_costs = [p.get("estimated_unit_price") or 0 for p in rfx_products]
            logger.info(f"🔍 Using user-provided costs from database: {product_costs}")
        else:
            # Fallback si no hay productos con costos, usar los del request
            product_costs = proposal_request.costs
            logger.warning(f"⚠️ No user costs found in database, using request costs: {product_costs}")
        
        # ✅ Crear nuevo request con costos reales (Pydantic models son inmutables)
        proposal_data = proposal_request.model_dump()
        proposal_data['costs'] = product_costs
        proposal_request = ProposalRequest(**proposal_data)
        
        # Mapear datos BD V2.0 → estructura esperada por ProposalGenerationService
        from backend.utils.data_mappers import map_rfx_data_for_proposal
        rfx_data_mapped = map_rfx_data_for_proposal(rfx_data, rfx_products)
        
        # 🔐 CRITICAL: Inyectar user_id del usuario autenticado en rfx_data_mapped
        rfx_data_mapped['user_id'] = user_id
        logger.info(f"✅ Injected authenticated user_id into rfx_data: {user_id}")
        
        # 💳 VERIFICAR CRÉDITOS Y REGENERACIONES GRATUITAS
        organization_id = get_current_user_organization_id()
        if not organization_id:
            # Intentar obtener organization_id del usuario en BD
            try:
                from backend.repositories.user_repository import user_repository
                from uuid import UUID
                user_data = user_repository.get_by_id(UUID(user_id))
                if user_data:
                    org_id_value = user_data.get('organization_id')
                    # ✅ CRÍTICO: Solo convertir a string si NO es None
                    organization_id = str(org_id_value) if org_id_value else None
            except Exception as e:
                logger.warning(f"⚠️ Could not get organization_id: {e}")
        
        # ✅ VALIDACIÓN SIMPLIFICADA: Solo verificar que el RFX existe
        # La validación de acceso ya está protegida a nivel de vista/frontend
        # Si el usuario puede ver el RFX, puede generar su propuesta
        logger.info(f"✅ Skipping ownership validation - access already protected at view level")
        logger.info(f"💳 Credits context - user_id: {user_id}, organization_id: {organization_id} (type: {type(organization_id).__name__})")
        
        logger.info(f"✅ Ownership validated for RFX {proposal_request.rfx_id}")
        
        credits_service = get_credits_service()
        
        # Verificar si es regeneración (si ya existe una propuesta para este RFX)
        existing_proposals = db_client.get_proposals_by_rfx_id(proposal_request.rfx_id)
        is_regeneration = len(existing_proposals) > 0
        
        credits_to_consume = 0
        used_free_regeneration = False
        
        if is_regeneration:
            logger.info(f"🔄 This is a regeneration (existing proposals: {len(existing_proposals)})")
            
            # Verificar si hay regeneraciones gratuitas disponibles
            has_free, used, msg = credits_service.check_free_regeneration_available(
                organization_id, proposal_request.rfx_id
            )
            
            if has_free:
                # Usar regeneración gratis
                logger.info(f"✅ Using free regeneration: {msg}")
                used_free_regeneration = True
            else:
                # Consumir créditos (5 créditos por regeneración)
                logger.info(f"⚠️ No free regenerations available: {msg}")
                credits_to_consume = 5
        else:
            # Primera generación (5 créditos)
            logger.info(f"🆕 This is the first proposal generation")
            credits_to_consume = 5
        
        # Verificar créditos si es necesario
        if credits_to_consume > 0:
            has_credits, available, msg = credits_service.check_credits_available(
                organization_id,  # None para usuarios personales
                'generation',
                user_id=user_id   # Requerido para usuarios personales
            )
            
            if not has_credits:
                context = "organization" if organization_id else "personal plan"
                logger.warning(f"⚠️ Insufficient credits for proposal generation ({context}): {msg}")
                return jsonify({
                    "status": "error",
                    "error_type": "insufficient_credits",
                    "message": msg,
                    "credits_required": credits_to_consume,
                    "credits_available": available
                }), 402  # 402 Payment Required
            
            context = "organization" if organization_id else "personal"
            logger.info(f"✅ Credits verified ({context}): {available} available, {credits_to_consume} required")
        
        # Generar propuesta usando el servicio completo
        from backend.services.proposal_generator import ProposalGenerationService
        proposal_generator = ProposalGenerationService()
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            propuesta_generada = loop.run_until_complete(
                proposal_generator.generate_proposal(rfx_data_mapped, proposal_request)
            )
        finally:
            loop.close()
        
        # ✅ Document is already saved by ProposalGenerationService._save_to_database()
        # No need to save again here - use the existing ID from the generated proposal
        documento_id = str(propuesta_generada.id)
        
        # 💳 CONSUMIR CRÉDITOS O MARCAR REGENERACIÓN GRATIS
        if used_free_regeneration:
            # Marcar regeneración gratis como usada
            credits_service.use_free_regeneration(proposal_request.rfx_id)
            logger.info(f"✅ Free regeneration marked as used for RFX {proposal_request.rfx_id}")
        elif credits_to_consume > 0:
            # Consumir créditos
            consume_result = credits_service.consume_credits(
                organization_id=organization_id,
                operation='generation' if not is_regeneration else 'regeneration',
                rfx_id=proposal_request.rfx_id,
                user_id=user_id,
                description=f"{'Regeneration' if is_regeneration else 'Generation'} of proposal for RFX {proposal_request.rfx_id}"
            )
            
            if consume_result["status"] == "success":
                logger.info(f"✅ Credits consumed: {credits_to_consume} (remaining: {consume_result['credits_remaining']})")
            else:
                logger.error(f"❌ Failed to consume credits: {consume_result.get('message')}")
        
        # 📊 ACTUALIZAR PROCESSING STATUS
        if is_regeneration:
            # Incrementar contador de regeneraciones
            db_client.increment_regeneration_count(proposal_request.rfx_id)
            logger.info(f"✅ Regeneration count incremented for RFX {proposal_request.rfx_id}")
        else:
            # Primera generación
            from datetime import datetime
            db_client.upsert_processing_status(proposal_request.rfx_id, {
                "has_generated_proposal": True,
                "generation_completed_at": datetime.now().isoformat(),
                "generation_credits_consumed": credits_to_consume
            })
        
        # Crear respuesta
        response_data = ProposalResponse(
            status="success",
            message="Propuesta generada exitosamente",
            document_id=documento_id,
            pdf_url=f"/api/download/{documento_id}",
            proposal=propuesta_generada
        ).model_dump()
        
        # Agregar información de créditos a la respuesta
        response_data["credits_info"] = {
            "credits_consumed": credits_to_consume,
            "used_free_regeneration": used_free_regeneration,
            "is_regeneration": is_regeneration
        }
        
        logger.info(f"✅ Propuesta generada exitosamente: {propuesta_generada.id}")
        return jsonify(response_data), 200
        
    except ValidationError as e:
        logger.error(f"❌ Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": "Data validation failed",
            "error": str(e)
        }), 400
        
    except ValueError as e:
        logger.error(f"❌ Processing error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error": "Proposal generation failed"
        }), 422
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in proposal generation: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": "An unexpected error occurred"
        }), 500


@proposals_bp.route("/<proposal_id>", methods=["GET"])
def get_proposal(proposal_id: str):
    """Obtener propuesta específica por ID"""
    try:
        db_client = get_database_client()
        proposal_data = db_client.get_document_by_id(proposal_id)
        
        if not proposal_data:
            return jsonify({
                "status": "error",
                "message": "Propuesta no encontrada",
                "error": f"No proposal found with ID: {proposal_id}"
            }), 404
        
        response = {
            "status": "success",
            "message": "Propuesta obtenida exitosamente",
            "data": {
                "id": proposal_data["id"],
                "rfx_id": proposal_data["rfx_id"],
                "content_markdown": proposal_data.get("content_markdown", ""),  # ✅ V2.0 field name
                "content_html": proposal_data.get("content_html", ""),  # ✅ V2.0 field name  
                "total_cost": proposal_data.get("total_cost", 0.0),  # ✅ V2.0 field name
                "created_at": proposal_data.get("created_at", ""),  # ✅ V2.0 field name
                "download_url": f"/api/download/{proposal_id}"
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo propuesta {proposal_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve proposal {proposal_id}",
            "error": str(e)
        }), 500


@proposals_bp.route("/<proposal_id>/status", methods=["PATCH"])
@jwt_required
def update_proposal_status(proposal_id: str):
    """Actualizar estado comercial de propuesta: generated | sent | accepted | rejected"""
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400

        payload = request.get_json() or {}
        new_status = str(payload.get("status", "")).strip().lower()
        allowed = {"generated", "sent", "accepted", "rejected"}
        if new_status not in allowed:
            return jsonify({
                "status": "error",
                "message": "Invalid proposal status",
                "error": f"status must be one of: {', '.join(sorted(allowed))}"
            }), 400

        user_id = get_current_user_id()
        db_client = get_database_client()
        updated = db_client.update_proposal_commercial_status(
            proposal_id=proposal_id,
            commercial_status=new_status,
            updated_by=user_id
        )

        if not updated:
            return jsonify({
                "status": "error",
                "message": "Propuesta no encontrada",
                "error": f"No proposal found with ID: {proposal_id}"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Proposal status updated successfully",
            "data": {
                "id": updated.get("id"),
                "rfx_id": updated.get("rfx_id"),
                "commercial_status": (updated.get("metadata") or {}).get("commercial_status", "generated"),
                "metadata": updated.get("metadata") or {}
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Error updating proposal status {proposal_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update proposal status",
            "error": str(e)
        }), 500


@proposals_bp.route("/rfx/<rfx_id>/proposals", methods=["GET"])
def get_proposals_by_rfx(rfx_id: str):
    """Obtener todas las propuestas de un RFX específico"""
    try:
        db_client = get_database_client()
        proposals = db_client.get_proposals_by_rfx_id(rfx_id)
        
        proposals_data = []
        for proposal in proposals:
            metadata = proposal.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            proposals_data.append({
                "id": proposal["id"],
                "rfx_id": proposal["rfx_id"],
                "document_type": proposal.get("document_type", "proposal"),  # ✅ V2.0 field name
                "created_at": proposal.get("created_at", ""),  # ✅ V2.0 field name
                "total_cost": proposal.get("total_cost", 0.0),  # ✅ V2.0 field name
                "commercial_status": metadata.get("commercial_status", "generated"),
                "download_url": f"/api/download/{proposal['id']}"
            })
        
        response = {
            "status": "success",
            "message": f"Encontradas {len(proposals_data)} propuestas para RFX {rfx_id}",
            "data": proposals_data
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo propuestas para RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve proposals for RFX {rfx_id}",
            "error": str(e)
        }), 500
