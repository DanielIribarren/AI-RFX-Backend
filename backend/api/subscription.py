"""
Subscription API Endpoints - Solicitud y Aprobación de Planes

Flujo MVP (aprobación manual):
1. Usuario solicita un plan → POST /api/subscription/request
2. Se crea un registro en plan_requests con status='pending'
3. Admin revisa y aprueba/rechaza → POST /api/subscription/admin/review/<request_id>
4. Al aprobar, se actualiza el plan_tier de la organización y se reinician créditos

IMPORTANTE: Los planes NO se activan automáticamente.
El usuario debe esperar aprobación manual del admin.
"""

from flask import Blueprint, jsonify, g, request
import logging
from datetime import datetime, timedelta

from backend.utils.auth_middleware import jwt_required, get_current_user_id
from backend.core.database import get_database_client
from backend.core.plans import get_plan, get_all_plans, PLANS

logger = logging.getLogger(__name__)

subscription_bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')

# Orden de planes para validar upgrades/downgrades
PLAN_ORDER = ['free', 'starter', 'pro', 'enterprise']


# ========================
# ENDPOINTS DE USUARIO
# ========================

@subscription_bp.route('/request', methods=['POST'])
@jwt_required
def request_plan():
    """
    Solicitar un cambio de plan.

    El usuario solicita un upgrade/downgrade. La solicitud queda en estado
    'pending' hasta que un admin la apruebe manualmente.

    NO se activa el plan inmediatamente. Requiere aprobación.

    Request Body:
        {
            "requested_tier": "pro",         // plan solicitado
            "notes": "Necesitamos más usuarios"  // comentario opcional
        }

    Returns:
        JSON con la solicitud creada
    """
    try:
        current_user = g.current_user
        current_user_id = str(current_user['id'])
        db = get_database_client()

        data = request.get_json()
        if not data or not data.get('requested_tier'):
            return jsonify({
                "status": "error",
                "message": "requested_tier is required"
            }), 400

        requested_tier = data['requested_tier'].lower().strip()
        notes = data.get('notes', '').strip()

        # Validar que el plan existe
        if requested_tier not in PLANS:
            return jsonify({
                "status": "error",
                "message": f"Invalid plan tier. Available plans: {list(PLANS.keys())}"
            }), 400

        # Determinar contexto: organización o usuario personal
        organization_id = current_user.get('organization_id')

        if organization_id:
            # Usuario en organización: solo el owner puede solicitar cambio de plan
            user_role = current_user.get('role')
            if user_role not in ['owner', 'admin']:
                return jsonify({
                    "status": "error",
                    "message": "Only organization owners or admins can request plan changes"
                }), 403

            # Obtener plan actual de la organización
            org_result = db.client.table("organizations")\
                .select("plan_tier, name")\
                .eq("id", organization_id)\
                .single()\
                .execute()

            if not org_result.data:
                return jsonify({
                    "status": "error",
                    "message": "Organization not found"
                }), 404

            current_tier = org_result.data.get('plan_tier', 'free')
            org_name = org_result.data.get('name', 'Unknown')
        else:
            # Usuario personal
            user_credits = db.client.table("user_credits")\
                .select("plan_tier")\
                .eq("user_id", current_user_id)\
                .maybe_single()\
                .execute()

            current_tier = user_credits.data.get('plan_tier', 'free') if user_credits.data else 'free'
            org_name = None

        # No permitir solicitar el mismo plan que ya tiene
        if requested_tier == current_tier:
            return jsonify({
                "status": "error",
                "message": f"You already have the '{requested_tier}' plan"
            }), 409

        # Verificar si ya tiene una solicitud pendiente
        existing_request_query = db.client.table("plan_requests")\
            .select("id, requested_tier, status")\
            .eq("user_id", current_user_id)\
            .eq("status", "pending")

        if organization_id:
            existing_request_query = existing_request_query.eq("organization_id", organization_id)

        existing_request = existing_request_query.execute()

        if existing_request.data:
            pending = existing_request.data[0]
            return jsonify({
                "status": "error",
                "message": f"You already have a pending plan request for '{pending['requested_tier']}'. "
                           f"Please wait for admin review before requesting again.",
                "pending_request_id": pending['id']
            }), 409

        # Crear la solicitud en estado 'pending'
        request_data = {
            "user_id": current_user_id,
            "organization_id": organization_id,
            "current_tier": current_tier,
            "requested_tier": requested_tier,
            "status": "pending",
            "user_notes": notes if notes else None
        }

        result = db.client.table("plan_requests")\
            .insert(request_data)\
            .execute()

        if not result.data:
            return jsonify({
                "status": "error",
                "message": "Failed to create plan request"
            }), 500

        new_request = result.data[0]
        requested_plan = get_plan(requested_tier)

        logger.info(
            f"✅ Plan request created: user={current_user_id}, "
            f"{current_tier} → {requested_tier}, request_id={new_request['id']}"
        )

        return jsonify({
            "status": "success",
            "message": (
                f"Plan upgrade request submitted successfully. "
                f"Your request is pending manual review by an administrator. "
                f"You will be notified when it is approved."
            ),
            "data": {
                "request_id": new_request['id'],
                "current_tier": current_tier,
                "requested_tier": requested_tier,
                "status": "pending",
                "requested_plan": requested_plan.to_dict() if requested_plan else None,
                "created_at": new_request.get('created_at')
            }
        }), 201

    except Exception as e:
        logger.error(f"❌ Error creating plan request: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to create plan request"
        }), 500


@subscription_bp.route('/my-requests', methods=['GET'])
@jwt_required
def get_my_requests():
    """
    Obtener las solicitudes de plan del usuario actual.

    Returns:
        JSON con lista de solicitudes del usuario
    """
    try:
        current_user_id = get_current_user_id()
        db = get_database_client()

        result = db.client.table("plan_requests")\
            .select("*")\
            .eq("user_id", current_user_id)\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()

        return jsonify({
            "status": "success",
            "data": result.data,
            "count": len(result.data)
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting plan requests: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get plan requests"
        }), 500


@subscription_bp.route('/current', methods=['GET'])
@jwt_required
def get_current_subscription():
    """
    Obtener el plan actual del usuario u organización.

    Returns:
        JSON con información del plan actual y solicitudes pendientes
    """
    try:
        current_user = g.current_user
        current_user_id = str(current_user['id'])
        db = get_database_client()

        organization_id = current_user.get('organization_id')

        if organization_id:
            org_result = db.client.table("organizations")\
                .select("plan_tier, credits_total, credits_used, credits_reset_date, name")\
                .eq("id", organization_id)\
                .single()\
                .execute()

            if not org_result.data:
                return jsonify({"status": "error", "message": "Organization not found"}), 404

            org = org_result.data
            current_tier = org.get('plan_tier', 'free')
            credits_info = {
                "credits_total": org.get('credits_total', 0),
                "credits_used": org.get('credits_used', 0),
                "credits_available": org.get('credits_total', 0) - org.get('credits_used', 0),
                "reset_date": org.get('credits_reset_date')
            }
            scope = "organizational"
        else:
            user_credits = db.client.table("user_credits")\
                .select("plan_tier, credits_total, credits_used, credits_reset_date")\
                .eq("user_id", current_user_id)\
                .maybe_single()\
                .execute()

            if user_credits.data:
                current_tier = user_credits.data.get('plan_tier', 'free')
                credits_info = {
                    "credits_total": user_credits.data.get('credits_total', 0),
                    "credits_used": user_credits.data.get('credits_used', 0),
                    "credits_available": user_credits.data.get('credits_total', 0) - user_credits.data.get('credits_used', 0),
                    "reset_date": user_credits.data.get('credits_reset_date')
                }
            else:
                current_tier = 'free'
                credits_info = {"credits_total": 100, "credits_used": 0, "credits_available": 100, "reset_date": None}
            scope = "personal"

        # Buscar solicitud pendiente
        pending_query = db.client.table("plan_requests")\
            .select("id, requested_tier, status, created_at, user_notes")\
            .eq("user_id", current_user_id)\
            .eq("status", "pending")

        if organization_id:
            pending_query = pending_query.eq("organization_id", organization_id)

        pending_result = pending_query.execute()
        pending_request = pending_result.data[0] if pending_result.data else None

        current_plan = get_plan(current_tier)

        return jsonify({
            "status": "success",
            "data": {
                "current_tier": current_tier,
                "current_plan": current_plan.to_dict() if current_plan else None,
                "scope": scope,
                "credits": credits_info,
                "pending_request": pending_request
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting current subscription: {e}")
        return jsonify({"status": "error", "message": "Failed to get subscription info"}), 500


# ========================
# ENDPOINTS DE ADMIN
# ========================

@subscription_bp.route('/admin/pending', methods=['GET'])
@jwt_required
def admin_get_pending_requests():
    """
    [ADMIN] Obtener todas las solicitudes de plan pendientes.

    NOTA: En MVP no hay sistema de roles de admin. Este endpoint
    está protegido con JWT pero cualquier usuario autenticado puede
    verlo. Para producción, agregar middleware de verificación de admin.

    Returns:
        JSON con lista de solicitudes pendientes
    """
    try:
        db = get_database_client()

        result = db.client.table("plan_requests")\
            .select("*")\
            .eq("status", "pending")\
            .order("created_at", desc=False)\
            .execute()

        # Enriquecer con info del plan solicitado
        enriched = []
        for req in result.data:
            requested_plan = get_plan(req.get('requested_tier', 'free'))
            enriched.append({
                **req,
                "requested_plan_info": requested_plan.to_dict() if requested_plan else None
            })

        return jsonify({
            "status": "success",
            "data": enriched,
            "count": len(enriched)
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting pending requests: {e}")
        return jsonify({"status": "error", "message": "Failed to get pending requests"}), 500


@subscription_bp.route('/admin/review/<request_id>', methods=['POST'])
@jwt_required
def admin_review_request(request_id: str):
    """
    [ADMIN] Aprobar o rechazar una solicitud de plan.

    Al APROBAR:
    - Se actualiza plan_tier en organizations o user_credits
    - Se actualiza credits_total según el nuevo plan
    - Se reinician créditos usados a 0
    - Se establece credits_reset_date a 30 días desde hoy

    Al RECHAZAR:
    - Solo se cambia el status a 'rejected' con la razón

    Request Body:
        {
            "action": "approve",     // "approve" o "reject"
            "admin_notes": "Pago verificado, plan activado"  // opcional
        }

    Returns:
        JSON con resultado de la revisión
    """
    try:
        admin_user = g.current_user
        admin_user_id = str(admin_user['id'])
        db = get_database_client()

        data = request.get_json()
        if not data or not data.get('action'):
            return jsonify({
                "status": "error",
                "message": "action is required ('approve' or 'reject')"
            }), 400

        action = data['action'].lower().strip()
        admin_notes = data.get('admin_notes', '').strip()

        if action not in ['approve', 'reject']:
            return jsonify({
                "status": "error",
                "message": "action must be 'approve' or 'reject'"
            }), 400

        # Obtener la solicitud
        req_result = db.client.table("plan_requests")\
            .select("*")\
            .eq("id", request_id)\
            .single()\
            .execute()

        if not req_result.data:
            return jsonify({
                "status": "error",
                "message": "Plan request not found"
            }), 404

        plan_req = req_result.data

        if plan_req['status'] != 'pending':
            return jsonify({
                "status": "error",
                "message": f"This request has already been reviewed (status: {plan_req['status']})"
            }), 409

        now = datetime.utcnow()

        if action == 'reject':
            # Solo rechazar, no cambiar el plan
            db.client.table("plan_requests")\
                .update({
                    "status": "rejected",
                    "reviewed_by": admin_user_id,
                    "reviewed_at": now.isoformat(),
                    "admin_notes": admin_notes if admin_notes else None
                })\
                .eq("id", request_id)\
                .execute()

            logger.info(f"❌ Plan request {request_id} rejected by admin {admin_user_id}")

            return jsonify({
                "status": "success",
                "message": "Plan request rejected",
                "data": {
                    "request_id": request_id,
                    "action": "rejected",
                    "user_id": plan_req['user_id']
                }
            }), 200

        # APROBAR: actualizar plan y créditos
        requested_tier = plan_req['requested_tier']
        new_plan = get_plan(requested_tier)

        if not new_plan:
            return jsonify({
                "status": "error",
                "message": f"Plan '{requested_tier}' no longer exists"
            }), 400

        reset_date = (now + timedelta(days=30)).isoformat()
        organization_id = plan_req.get('organization_id')
        user_id = plan_req['user_id']

        if organization_id:
            # Actualizar plan de la organización
            db.client.table("organizations")\
                .update({
                    "plan_tier": requested_tier,
                    "max_users": new_plan.max_users,
                    "max_rfx_per_month": new_plan.max_rfx_per_month,
                    "credits_total": new_plan.credits_per_month,
                    "credits_used": 0,
                    "credits_reset_date": reset_date
                })\
                .eq("id", organization_id)\
                .execute()

            # Registrar transacción de créditos
            db.client.table("credit_transactions")\
                .insert({
                    "organization_id": organization_id,
                    "user_id": admin_user_id,
                    "amount": new_plan.credits_per_month,
                    "type": "plan_upgrade",
                    "description": f"Plan upgraded to {requested_tier} by admin. Credits reset.",
                    "metadata": {"request_id": request_id, "admin_id": admin_user_id}
                })\
                .execute()

            logger.info(f"✅ Organization {organization_id} plan upgraded to {requested_tier}")

        else:
            # Actualizar créditos del usuario personal
            existing_credits = db.client.table("user_credits")\
                .select("id")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()

            if existing_credits.data:
                db.client.table("user_credits")\
                    .update({
                        "plan_tier": requested_tier,
                        "credits_total": new_plan.credits_per_month,
                        "credits_used": 0,
                        "credits_reset_date": reset_date
                    })\
                    .eq("user_id", user_id)\
                    .execute()
            else:
                db.client.table("user_credits")\
                    .insert({
                        "user_id": user_id,
                        "plan_tier": requested_tier,
                        "credits_total": new_plan.credits_per_month,
                        "credits_used": 0,
                        "credits_reset_date": reset_date
                    })\
                    .execute()

            logger.info(f"✅ User {user_id} personal plan upgraded to {requested_tier}")

        # Marcar solicitud como aprobada
        db.client.table("plan_requests")\
            .update({
                "status": "approved",
                "reviewed_by": admin_user_id,
                "reviewed_at": now.isoformat(),
                "admin_notes": admin_notes if admin_notes else None
            })\
            .eq("id", request_id)\
            .execute()

        logger.info(f"✅ Plan request {request_id} approved by admin {admin_user_id}: {plan_req['current_tier']} → {requested_tier}")

        return jsonify({
            "status": "success",
            "message": f"Plan successfully upgraded to '{requested_tier}'",
            "data": {
                "request_id": request_id,
                "action": "approved",
                "user_id": user_id,
                "organization_id": organization_id,
                "previous_tier": plan_req['current_tier'],
                "new_tier": requested_tier,
                "new_credits_total": new_plan.credits_per_month,
                "credits_reset_to_zero": True,
                "next_reset_date": reset_date
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Error reviewing plan request: {e}")
        return jsonify({"status": "error", "message": "Failed to review plan request"}), 500


@subscription_bp.route('/admin/reset-credits', methods=['POST'])
@jwt_required
def admin_trigger_monthly_reset():
    """
    [ADMIN] Disparar manualmente el reset mensual de créditos.

    Resetea créditos de todas las organizaciones y usuarios personales
    cuya fecha de reset ya venció (credits_reset_date <= NOW).

    Útil para MVP donde no hay cron job configurado.
    En producción esto debería ser un cron job automático.

    Returns:
        JSON con resultado del reset
    """
    try:
        from backend.services.credits_service import get_credits_service

        credits_service = get_credits_service()
        result = credits_service.reset_monthly_credits()

        admin_user_id = str(g.current_user['id'])
        logger.info(f"🔄 Monthly credits reset triggered by admin {admin_user_id}: {result}")

        return jsonify({
            "status": result.get("status", "success"),
            "message": result.get("message", "Reset completed"),
            "data": {
                "org_reset_count": result.get("org_reset_count", 0),
                "user_reset_count": result.get("user_reset_count", 0),
                "total_reset": result.get("reset_count", 0),
                "triggered_by": admin_user_id
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Error triggering monthly reset: {e}")
        return jsonify({"status": "error", "message": "Failed to trigger monthly reset"}), 500
