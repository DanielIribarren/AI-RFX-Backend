"""
💳 Credits API Endpoints - Gestión de créditos para multi-tenancy

Endpoints para consultar créditos disponibles, historial de transacciones,
y información de planes de suscripción.
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Optional

from backend.services.credits_service import get_credits_service
from backend.core.plans import PLANS, get_plan
from backend.utils.auth_middleware import jwt_required, get_current_user_organization_id, get_current_user_id

logger = logging.getLogger(__name__)

# Create blueprint
credits_bp = Blueprint("credits_api", __name__, url_prefix="/api/credits")


@credits_bp.route("/info", methods=["GET"])
@jwt_required
def get_credits_info():
    """
    Obtener información de créditos del usuario actual.
    
    Funciona tanto para usuarios con organización como para usuarios con plan personal.
    
    Requiere autenticación JWT.
    
    Retorna:
        - credits_total: Total de créditos del plan
        - credits_used: Créditos consumidos (0 para plan personal)
        - credits_available: Créditos disponibles
        - credits_percentage: Porcentaje de créditos disponibles
        - reset_date: Fecha de reset mensual
        - plan_tier: Tier del plan actual
        - plan_type: "organizational" o "personal"
    """
    try:
        user_id = get_current_user_id()
        logger.info(f"🔍 Getting credits info for user: {user_id}")
        
        credits_service = get_credits_service()
        credits_info = credits_service.get_credits_info_for_user(user_id)
        
        logger.info(f"📊 Credits info result: {credits_info}")
        
        if credits_info.get("status") == "error":
            logger.error(f"❌ Credits info returned error: {credits_info.get('message')}")
            return jsonify(credits_info), 404
        
        return jsonify({
            "status": "success",
            "data": credits_info
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting credits info: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve credits information",
            "error": str(e)
        }), 500


@credits_bp.route("/history", methods=["GET"])
@jwt_required
def get_credits_history():
    """
    Obtener historial de transacciones de créditos.
    
    Para usuarios con organización: muestra historial organizacional
    Para usuarios con plan personal: muestra historial vacío (no hay transacciones)
    
    Query params:
        - limit: Número máximo de transacciones (default: 50)
        - offset: Offset para paginación (default: 0)
    
    Requiere autenticación JWT.
    """
    try:
        user_id = get_current_user_id()
        
        # Obtener organización del usuario (puede ser None)
        organization_id = get_current_user_organization_id()
        
        # Obtener parámetros de paginación
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validar límites
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 50
        if offset < 0:
            offset = 0
        
        credits_service = get_credits_service()
        
        # Si el usuario pertenece a una organización, mostrar historial organizacional
        if organization_id:
            history = credits_service.get_transaction_history(
                organization_id=organization_id,
                limit=limit,
                offset=offset
            )
        else:
            # Usuario con plan personal - no hay historial de transacciones
            history = {
                "status": "success",
                "transactions": [],
                "count": 0
            }
        
        if history.get("status") == "error":
            return jsonify(history), 500
        
        return jsonify({
            "status": "success",
            "data": history.get("transactions", []),
            "count": history.get("count", 0),
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting credits history: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve credits history",
            "error": str(e)
        }), 500


@credits_bp.route("/plans", methods=["GET"])
def get_available_plans():
    """
    Obtener información de todos los planes disponibles.
    
    No requiere autenticación (información pública).
    
    Retorna lista de planes con:
        - tier: Identificador del plan
        - name: Nombre del plan
        - price_monthly_usd: Precio mensual
        - credits_per_month: Créditos mensuales
        - max_users: Usuarios máximos
        - max_rfx_per_month: RFX máximos por mes
        - free_regenerations: Regeneraciones gratuitas
        - features: Lista de características
    """
    try:
        plans_list = []
        
        for tier, plan in PLANS.items():
            plan_dict = plan.to_dict()
            plans_list.append(plan_dict)
        
        # Ordenar por precio
        plans_list.sort(key=lambda x: x["price_monthly_usd"])
        
        return jsonify({
            "status": "success",
            "data": plans_list,
            "count": len(plans_list)
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting plans: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve plans",
            "error": str(e)
        }), 500


@credits_bp.route("/plan/<tier>", methods=["GET"])
def get_plan_details(tier: str):
    """
    Obtener detalles de un plan específico.
    
    No requiere autenticación (información pública).
    
    Path params:
        - tier: Tier del plan (free, starter, pro, enterprise)
    """
    try:
        plan = get_plan(tier)
        
        if not plan:
            return jsonify({
                "status": "error",
                "message": f"Plan not found: {tier}",
                "available_tiers": list(PLANS.keys())
            }), 404
        
        return jsonify({
            "status": "success",
            "data": plan.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting plan {tier}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve plan {tier}",
            "error": str(e)
        }), 500


@credits_bp.route("/costs", methods=["GET"])
def get_operation_costs():
    """
    Obtener costos de operaciones en créditos.
    
    No requiere autenticación (información pública).
    
    Retorna:
        - extraction: Costo de extracción de datos (5 créditos)
        - generation: Costo de generación de propuesta (5 créditos)
        - complete: Costo de proceso completo (10 créditos)
        - chat_message: Costo de mensaje de chat (1 crédito)
        - regeneration: Costo de regeneración (5 créditos)
    """
    try:
        from backend.core.plans import CREDIT_COSTS
        
        return jsonify({
            "status": "success",
            "data": CREDIT_COSTS
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting operation costs: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve operation costs",
            "error": str(e)
        }), 500


@credits_bp.route("/regenerations/<rfx_id>", methods=["GET"])
@jwt_required
def get_regeneration_info(rfx_id: str):
    """
    Obtener información de regeneraciones para un RFX específico.
    
    Para usuarios con organización: verifica regeneraciones organizacionales
    Para usuarios con plan personal: usa regeneraciones del plan gratuito
    
    Requiere autenticación JWT.
    
    Path params:
        - rfx_id: ID del RFX
    
    Retorna:
        - has_free_regeneration: Si tiene regeneración gratis disponible
        - free_regenerations_used: Regeneraciones gratuitas usadas
        - free_regenerations_limit: Límite de regeneraciones gratuitas del plan
        - regeneration_count: Total de regeneraciones realizadas
    """
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        
        credits_service = get_credits_service()
        from backend.core.database import get_database_client
        
        # Determinar plan a usar
        if organization_id:
            # Usuario con organización - usar regeneraciones organizacionales
            has_free, used, msg = credits_service.check_free_regeneration_available(
                organization_id, rfx_id
            )
            
            # Obtener plan de la organización
            org_result = get_database_client().client.table("organizations")\
                .select("plan_tier")\
                .eq("id", organization_id)\
                .single()\
                .execute()
            
            plan_tier = org_result.data.get("plan_tier", "free") if org_result.data else "free"
        else:
            # Usuario con plan personal - usar regeneraciones del plan gratuito
            from backend.core.plans import get_free_regenerations, has_unlimited_regenerations
            
            plan_tier = "free"
            
            if has_unlimited_regenerations(plan_tier):
                has_free, used, msg = True, 0, "Unlimited regenerations available"
            else:
                free_limit = get_free_regenerations(plan_tier)
                
                # Para usuarios personales, siempre tienen regeneraciones disponibles
                # (no hay límite acumulado por RFX como en organizaciones)
                has_free, used, msg = True, 0, f"{free_limit} free regenerations available"
        
        # Obtener contador total de regeneraciones
        db = get_database_client()
        regeneration_count = db.get_regeneration_count(rfx_id)
        
        from backend.core.plans import get_free_regenerations
        free_limit = get_free_regenerations(plan_tier)
        
        return jsonify({
            "status": "success",
            "data": {
                "rfx_id": rfx_id,
                "has_free_regeneration": has_free,
                "free_regenerations_used": used,
                "free_regenerations_limit": free_limit if free_limit != float('inf') else "unlimited",
                "regeneration_count": regeneration_count,
                "plan_tier": plan_tier,
                "plan_type": "organizational" if organization_id else "personal",
                "message": msg
            }
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error getting regeneration info for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve regeneration info for RFX {rfx_id}",
            "error": str(e)
        }), 500
