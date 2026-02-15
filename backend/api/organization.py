"""
Organization API Endpoints

Endpoints para gestionar organizaciones multi-tenant.
Sigue principios KISS: simple, directo, sin overengineering.
"""

from flask import Blueprint, jsonify, g, request
from backend.utils.auth_middleware import jwt_required
from backend.utils.organization_middleware import require_organization, require_role, optional_organization
from backend.core.database import get_database_client
from backend.core.plans import get_all_plans, get_plan, PLANS
import logging
import re

logger = logging.getLogger(__name__)

# Blueprint
organization_bp = Blueprint('organization', __name__, url_prefix='/api/organization')


@organization_bp.route('', methods=['POST'])
@organization_bp.route('/create', methods=['POST'])
@jwt_required
def create_organization():
    """
    Crear una nueva organización para el usuario actual.

    El usuario que crea la organización queda automáticamente como 'owner'.
    Solo se puede crear una organización si el usuario NO pertenece ya a una.

    La organización se crea con el plan solicitado. Si el plan es pagado (no free),
    se crea automáticamente un plan_request pendiente para aprobación del admin.

    Request Body:
        {
            "name": "Mi Empresa S.A.",
            "slug": "mi-empresa",          // opcional, se genera desde el nombre
            "plan_tier": "starter",         // opcional, default "free"
            "billing_email": "billing@..."  // opcional, se guarda en plan_request
        }

    Returns:
        JSON con la organización creada y plan_request si aplica
    """
    try:
        current_user = g.current_user
        current_user_id = str(current_user['id'])
        db = get_database_client()

        # Verificar que el usuario no tenga ya una organización
        if current_user.get('organization_id'):
            return jsonify({
                "status": "error",
                "message": "You already belong to an organization. Leave it first before creating a new one."
            }), 409

        # Validar request body
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({
                "status": "error",
                "message": "Organization name is required"
            }), 400

        name = data['name'].strip()
        if len(name) < 2:
            return jsonify({
                "status": "error",
                "message": "Organization name must be at least 2 characters"
            }), 400

        # Generar slug si no se proporciona
        slug = data.get('slug', '').strip()
        if not slug:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        if len(slug) < 2:
            return jsonify({
                "status": "error",
                "message": "Slug must be at least 2 characters"
            }), 400

        # Verificar que el slug no esté en uso
        existing_slug = db.client.table("organizations")\
            .select("id")\
            .eq("slug", slug)\
            .execute()

        if existing_slug.data:
            return jsonify({
                "status": "error",
                "message": f"Slug '{slug}' is already in use. Please choose a different one."
            }), 409

        # Determinar plan solicitado (default: free)
        requested_tier = data.get('plan_tier', 'free').lower().strip()
        billing_email = data.get('billing_email', '').strip()

        if requested_tier not in PLANS:
            return jsonify({
                "status": "error",
                "message": f"Invalid plan tier. Available: {list(PLANS.keys())}"
            }), 400

        # Siempre crear la organización con plan free inicialmente
        # Si pidieron un plan pagado, se crea un plan_request pendiente
        free_plan = get_plan('free')

        new_org_data = {
            "name": name,
            "slug": slug,
            "plan_tier": "free",
            "max_users": free_plan.max_users,
            "max_rfx_per_month": free_plan.max_rfx_per_month,
            "credits_total": free_plan.credits_per_month,
            "credits_used": 0,
            "is_active": True
        }

        org_result = db.client.table("organizations")\
            .insert(new_org_data)\
            .execute()

        if not org_result.data:
            return jsonify({
                "status": "error",
                "message": "Failed to create organization"
            }), 500

        new_org = org_result.data[0]
        organization_id = new_org['id']

        # Asignar al usuario como owner de la organización
        db.client.table("users")\
            .update({
                "organization_id": organization_id,
                "role": "owner"
            })\
            .eq("id", current_user_id)\
            .execute()

        logger.info(f"✅ Organization '{name}' created by user {current_user_id} (org_id: {organization_id})")

        # Si pidieron un plan pagado, crear plan_request automáticamente
        plan_request_data = None
        if requested_tier != 'free':
            notes_parts = []
            if billing_email:
                notes_parts.append(f"Billing email: {billing_email}")
            notes_parts.append(f"Requested during organization creation")

            pr_data = {
                "user_id": current_user_id,
                "organization_id": organization_id,
                "current_tier": "free",
                "requested_tier": requested_tier,
                "status": "pending",
                "user_notes": " | ".join(notes_parts)
            }

            pr_result = db.client.table("plan_requests")\
                .insert(pr_data)\
                .execute()

            if pr_result.data:
                plan_request_data = pr_result.data[0]
                requested_plan = get_plan(requested_tier)
                logger.info(
                    f"📋 Auto-created plan_request: free → {requested_tier} "
                    f"for org '{name}' (request_id: {plan_request_data['id']})"
                )

        # Construir respuesta compatible con frontend
        org_response = {
            "id": organization_id,
            "name": new_org['name'],
            "slug": new_org['slug'],
            "is_active": new_org['is_active'],
            "trial_ends_at": new_org.get('trial_ends_at'),
            "created_at": new_org.get('created_at'),
            "plan": free_plan.to_dict(),
            "usage": {
                "users": {
                    "current": 1,
                    "limit": free_plan.max_users,
                    "can_add_more": False
                },
                "rfx_this_month": {
                    "current": 0,
                    "limit": free_plan.max_rfx_per_month,
                    "can_create_more": True
                }
            },
            "your_role": "owner"
        }

        message = "Organization created successfully"
        if requested_tier != 'free':
            message += (
                f". Your '{requested_tier}' plan request has been submitted "
                f"and is pending admin approval. You'll be notified when approved."
            )

        response_data = {
            "organization": org_response,
            "stripe_checkout_url": None
        }

        if plan_request_data:
            response_data["plan_request"] = {
                "id": plan_request_data['id'],
                "requested_tier": requested_tier,
                "status": "pending"
            }

        return jsonify({
            "status": "success",
            "message": message,
            "data": response_data
        }), 201

    except Exception as e:
        logger.error(f"❌ Error creating organization: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to create organization"
        }), 500


@organization_bp.route('/test', methods=['GET'])
def test_organization_endpoint():
    """
    🧪 ENDPOINT DE PRUEBA - Sin autenticación
    
    Verifica que el backend funciona correctamente.
    Retorna información de la organización Sabra Corporation (hardcoded).
    
    Este endpoint NO requiere autenticación y es solo para testing.
    """
    try:
        # Hardcoded organization ID para testing
        organization_id = "8ed7f53e-86c7-4dec-861b-822b8a25ed6d"  # Sabra Corporation PRO
        
        db = get_database_client()
        
        # Obtener organización
        org = db.get_organization(organization_id)
        if not org:
            return jsonify({
                "status": "error",
                "message": "Test organization not found"
            }), 404
        
        # Obtener plan
        plan_tier = org.get('plan_tier', 'free')
        plan = get_plan(plan_tier)
        
        # Verificar límites
        users_limit = db.check_organization_limit(organization_id, 'users')
        rfx_limit = db.check_organization_limit(organization_id, 'rfx_monthly')
        
        return jsonify({
            "status": "success",
            "message": "✅ Backend is working! This is a test endpoint without authentication.",
            "note": "For production, use /api/organization/current with JWT token",
            "data": {
                "id": org['id'],
                "name": org['name'],
                "slug": org['slug'],
                "is_active": org.get('is_active', True),
                "trial_ends_at": org.get('trial_ends_at'),
                "created_at": org.get('created_at'),
                "plan": plan.to_dict() if plan else None,
                "usage": {
                    "users": {
                        "current": users_limit.get('current_count', 0),
                        "limit": users_limit.get('limit', 2),
                        "can_add_more": users_limit.get('can_proceed', False)
                    },
                    "rfx_this_month": {
                        "current": rfx_limit.get('current_count', 0),
                        "limit": rfx_limit.get('limit', 10),
                        "can_create_more": rfx_limit.get('can_proceed', False)
                    }
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in test endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": f"Test endpoint failed: {str(e)}"
        }), 500


@organization_bp.route('/current', methods=['GET'])
@jwt_required
@optional_organization
def get_current_organization():
    """
    Obtener información de la organización actual del usuario.
    
    Si el usuario NO tiene organización, retorna información de usuario personal.
    
    Returns:
        JSON con datos de la organización/usuario, plan actual, y límites
    
    Ejemplo Response (con organización):
        {
            "status": "success",
            "has_organization": true,
            "data": {
                "id": "uuid",
                "name": "Sabra Corporation",
                "slug": "sabra-corp",
                "plan": {...},
                "usage": {...}
            }
        }
    
    Ejemplo Response (sin organización):
        {
            "status": "success",
            "has_organization": false,
            "message": "User has no organization. Using personal credits.",
            "data": null
        }
    """
    try:
        organization_id = g.organization_id
        
        # Usuario NO tiene organización (usuario personal)
        if not organization_id:
            logger.info(f"✅ User {g.current_user.get('id')} has no organization - personal user")
            return jsonify({
                "status": "success",
                "has_organization": False,
                "message": "User has no organization. Using personal credits.",
                "data": None
            }), 200
        
        # Usuario SÍ tiene organización
        db = get_database_client()
        
        # Obtener organización
        org = db.get_organization(organization_id)
        if not org:
            return jsonify({
                "status": "error",
                "message": "Organization not found"
            }), 404
        
        # Obtener plan
        plan_tier = org.get('plan_tier', 'free')
        plan = get_plan(plan_tier)
        
        # Verificar límites
        users_limit = db.check_organization_limit(organization_id, 'users')
        rfx_limit = db.check_organization_limit(organization_id, 'rfx_monthly')
        
        return jsonify({
            "status": "success",
            "has_organization": True,
            "data": {
                "id": org['id'],
                "name": org['name'],
                "slug": org['slug'],
                "is_active": org.get('is_active', True),
                "trial_ends_at": org.get('trial_ends_at'),
                "created_at": org.get('created_at'),
                "plan": plan.to_dict() if plan else None,
                "usage": {
                    "users": {
                        "current": users_limit.get('current_count', 0),
                        "limit": users_limit.get('limit', 2),
                        "can_add_more": users_limit.get('can_proceed', False)
                    },
                    "rfx_this_month": {
                        "current": rfx_limit.get('current_count', 0),
                        "limit": rfx_limit.get('limit', 10),
                        "can_create_more": rfx_limit.get('can_proceed', False)
                    }
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting current organization: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get organization"
        }), 500


@organization_bp.route('/members', methods=['GET'])
@jwt_required
@require_organization
def get_organization_members():
    """
    Obtener todos los miembros de la organización.
    
    Returns:
        JSON con lista de miembros
    
    Ejemplo Response:
        {
            "status": "success",
            "data": [
                {
                    "id": "uuid",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "role": "owner",
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ]
        }
    """
    try:
        organization_id = g.organization_id
        db = get_database_client()
        
        members = db.get_organization_members(organization_id)
        
        return jsonify({
            "status": "success",
            "data": members,
            "count": len(members)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting organization members: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get members"
        }), 500


@organization_bp.route('/plans', methods=['GET'])
@jwt_required
def get_available_plans():
    """
    Obtener todos los planes disponibles.
    
    No requiere @require_organization porque puede usarse antes de tener org.
    
    Returns:
        JSON con lista de planes
    
    Ejemplo Response:
        {
            "status": "success",
            "data": [
                {
                    "tier": "free",
                    "name": "Free Plan",
                    "max_users": 2,
                    "max_rfx_per_month": 10,
                    "price_monthly_usd": 0.0,
                    "features": [...]
                },
                ...
            ]
        }
    """
    try:
        plans = get_all_plans()
        
        return jsonify({
            "status": "success",
            "data": plans
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting plans: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get plans"
        }), 500


@organization_bp.route('/upgrade-info', methods=['GET'])
@jwt_required
@require_organization
def get_upgrade_info():
    """
    Obtener información sobre upgrade disponible.
    
    Returns:
        JSON con plan actual y siguiente plan disponible
    
    Ejemplo Response:
        {
            "status": "success",
            "data": {
                "current_plan": {...},
                "upgrade_available": true,
                "next_plan": {...},
                "benefits": ["More users", "More RFX", ...]
            }
        }
    """
    try:
        organization_id = g.organization_id
        db = get_database_client()
        
        # Obtener organización
        org = db.get_organization(organization_id)
        if not org:
            return jsonify({
                "status": "error",
                "message": "Organization not found"
            }), 404
        
        current_tier = org.get('plan_tier', 'free')
        current_plan = get_plan(current_tier)
        
        # Determinar siguiente plan
        next_tier = None
        if current_tier == 'free':
            next_tier = 'pro'
        elif current_tier == 'pro':
            next_tier = 'enterprise'
        
        next_plan = get_plan(next_tier) if next_tier else None
        
        # Calcular beneficios del upgrade
        benefits = []
        if next_plan and current_plan:
            if next_plan.max_users > current_plan.max_users:
                benefits.append(f"Increase users from {current_plan.max_users} to {next_plan.max_users}")
            if next_plan.max_rfx_per_month > current_plan.max_rfx_per_month:
                benefits.append(f"Increase RFX from {current_plan.max_rfx_per_month} to {next_plan.max_rfx_per_month}/month")
            
            # Features adicionales
            new_features = set(next_plan.features) - set(current_plan.features)
            benefits.extend(new_features)
        
        return jsonify({
            "status": "success",
            "data": {
                "current_plan": current_plan.to_dict() if current_plan else None,
                "upgrade_available": next_plan is not None,
                "next_plan": next_plan.to_dict() if next_plan else None,
                "benefits": benefits
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting upgrade info: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to get upgrade info"
        }), 500


# ========================
# ENDPOINTS DE GESTIÓN
# ========================

@organization_bp.route('/current', methods=['PATCH'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])
def update_organization_info():
    """
    Actualizar información de la organización.
    
    Solo owners y admins pueden actualizar la organización.
    
    Request Body:
        {
            "name": "New Organization Name",  // opcional
            "slug": "new-org-slug"            // opcional
        }
    
    Returns:
        JSON con organización actualizada
    """
    try:
        from flask import request
        
        organization_id = g.organization_id
        db = get_database_client()
        
        # Validar request
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Campos permitidos para actualizar
        allowed_fields = ['name', 'slug']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({
                "status": "error",
                "message": "No valid fields to update"
            }), 400
        
        # Validar slug si se proporciona
        if 'slug' in update_data:
            slug = update_data['slug']
            if not slug or len(slug) < 3:
                return jsonify({
                    "status": "error",
                    "message": "Slug must be at least 3 characters"
                }), 400
            
            # Verificar que el slug no esté en uso por otra organización
            existing = db.client.table("organizations")\
                .select("id")\
                .eq("slug", slug)\
                .neq("id", str(organization_id))\
                .execute()
            
            if existing.data:
                return jsonify({
                    "status": "error",
                    "message": "Slug already in use by another organization"
                }), 409
        
        # Actualizar organización
        updated_org = db.update_organization(organization_id, update_data)
        
        if not updated_org:
            return jsonify({
                "status": "error",
                "message": "Failed to update organization"
            }), 500
        
        logger.info(f"✅ Organization updated by user {g.current_user['id']}: {update_data}")
        
        return jsonify({
            "status": "success",
            "message": "Organization updated successfully",
            "data": updated_org
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating organization: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update organization"
        }), 500


@organization_bp.route('/members/<user_id>/role', methods=['PATCH'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])
def update_member_role(user_id: str):
    """
    Cambiar el rol de un miembro de la organización.
    
    Solo owners y admins pueden cambiar roles.
    Restricciones:
    - No puedes cambiar tu propio rol
    - Solo owners pueden crear/modificar otros owners
    - No puedes eliminar el último owner
    
    Request Body:
        {
            "role": "admin"  // "owner", "admin", o "member"
        }
    
    Returns:
        JSON con usuario actualizado
    """
    try:
        from flask import request
        
        organization_id = g.organization_id
        current_user_id = g.current_user['id']
        current_user_role = g.user_role
        db = get_database_client()
        
        # Validar request
        data = request.get_json()
        if not data or 'role' not in data:
            return jsonify({
                "status": "error",
                "message": "Role is required"
            }), 400
        
        new_role = data['role']
        valid_roles = ['owner', 'admin', 'member']
        
        if new_role not in valid_roles:
            return jsonify({
                "status": "error",
                "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            }), 400
        
        # No puedes cambiar tu propio rol
        if str(user_id) == str(current_user_id):
            return jsonify({
                "status": "error",
                "message": "You cannot change your own role"
            }), 403
        
        # Obtener usuario a modificar
        target_user = db.get_user_by_id(user_id)
        if not target_user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
        
        # Verificar que el usuario pertenece a la misma organización
        if str(target_user.get('organization_id')) != str(organization_id):
            return jsonify({
                "status": "error",
                "message": "User does not belong to your organization"
            }), 403
        
        # Solo owners pueden crear/modificar otros owners
        if new_role == 'owner' and current_user_role != 'owner':
            return jsonify({
                "status": "error",
                "message": "Only owners can assign the owner role"
            }), 403
        
        # Si estás quitando el rol de owner, verificar que no sea el último
        if target_user.get('role') == 'owner' and new_role != 'owner':
            owners_count = db.client.table("users")\
                .select("id", count="exact")\
                .eq("organization_id", str(organization_id))\
                .eq("role", "owner")\
                .execute()
            
            if owners_count.count <= 1:
                return jsonify({
                    "status": "error",
                    "message": "Cannot remove the last owner. Assign another owner first."
                }), 403
        
        # Actualizar rol
        success = db.update_user_role(user_id, new_role)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": "Failed to update user role"
            }), 500
        
        logger.info(f"✅ User {user_id} role changed to {new_role} by {current_user_id}")
        
        # Obtener usuario actualizado
        updated_user = db.get_user_by_id(user_id)
        
        return jsonify({
            "status": "success",
            "message": f"User role updated to {new_role}",
            "data": {
                "id": updated_user['id'],
                "email": updated_user['email'],
                "full_name": updated_user.get('full_name'),
                "role": updated_user['role']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating member role: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update member role"
        }), 500


@organization_bp.route('/members/<user_id>', methods=['DELETE'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])
def remove_member(user_id: str):
    """
    Remover un usuario de la organización.
    
    El usuario NO es eliminado de la base de datos, solo removido de la organización.
    Después de esto:
    - organization_id = NULL
    - role = NULL
    - El usuario tendrá plan personal
    - Puede ser agregado a otra organización después
    
    Solo owners y admins pueden remover usuarios.
    Restricciones:
    - No puedes removerte a ti mismo
    - No puedes remover al último owner
    
    Returns:
        JSON con confirmación de remoción
    """
    try:
        from flask import request
        
        organization_id = g.organization_id
        current_user_id = g.current_user['id']
        db = get_database_client()
        
        # No puedes eliminarte a ti mismo
        if str(user_id) == str(current_user_id):
            return jsonify({
                "status": "error",
                "message": "You cannot remove yourself from the organization"
            }), 403
        
        # Obtener usuario a eliminar
        target_user = db.get_user_by_id(user_id)
        if not target_user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
        
        # Verificar que el usuario pertenece a la misma organización
        if str(target_user.get('organization_id')) != str(organization_id):
            return jsonify({
                "status": "error",
                "message": "User does not belong to your organization"
            }), 403
        
        # Si es owner, verificar que no sea el último
        if target_user.get('role') == 'owner':
            owners_count = db.client.table("users")\
                .select("id", count="exact")\
                .eq("organization_id", str(organization_id))\
                .eq("role", "owner")\
                .execute()
            
            if owners_count.count <= 1:
                return jsonify({
                    "status": "error",
                    "message": "Cannot remove the last owner"
                }), 403
        
        # Remover usuario de la organización (set organization_id = NULL)
        success = db.remove_user_from_organization(user_id)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": "Failed to remove user from organization"
            }), 500
        
        logger.info(f"✅ User {user_id} removed from organization by {current_user_id}")
        
        return jsonify({
            "status": "success",
            "message": "User removed from organization successfully",
            "note": "User now has personal plan and can be added to another organization",
            "data": {
                "removed_user_id": user_id,
                "removed_user_email": target_user.get('email'),
                "new_status": "personal_plan"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error removing user from organization: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to remove user from organization"
        }), 500


@organization_bp.route('/invite', methods=['POST'])
@jwt_required
@require_organization
@require_role(['owner', 'admin'])
def invite_member():
    """
    Invitar un nuevo miembro a la organización.
    
    Solo owners y admins pueden invitar usuarios.
    
    Request Body:
        {
            "email": "user@example.com",
            "role": "member"  // "admin" o "member" (solo owners pueden invitar owners)
        }
    
    Returns:
        JSON con información de la invitación
    
    Nota: Esta es una implementación básica. En producción, deberías:
    - Enviar un email de invitación
    - Crear un token de invitación temporal
    - Permitir al usuario aceptar/rechazar la invitación
    """
    try:
        from flask import request
        
        organization_id = g.organization_id
        current_user_role = g.user_role
        db = get_database_client()
        
        # Validar request
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({
                "status": "error",
                "message": "Email is required"
            }), 400
        
        email = data['email'].lower().strip()
        role = data.get('role', 'member')
        
        # Validar rol
        valid_roles = ['admin', 'member']
        if current_user_role == 'owner':
            valid_roles.append('owner')
        
        if role not in valid_roles:
            return jsonify({
                "status": "error",
                "message": f"Invalid role. You can invite: {', '.join(valid_roles)}"
            }), 400
        
        # Verificar límite de usuarios
        limit_check = db.check_organization_limit(organization_id, 'users')
        if not limit_check.get('can_proceed'):
            return jsonify({
                "status": "error",
                "message": f"User limit reached ({limit_check.get('current_count')}/{limit_check.get('limit')}). Upgrade your plan to add more users."
            }), 403
        
        # Verificar si el usuario ya existe
        existing_user = db.client.table("users")\
            .select("id, organization_id")\
            .eq("email", email)\
            .execute()
        
        if existing_user.data:
            user = existing_user.data[0]
            if user.get('organization_id'):
                return jsonify({
                    "status": "error",
                    "message": "User already belongs to an organization"
                }), 409
            else:
                # Usuario existe pero no tiene organización - asignarlo
                success = db.client.table("users")\
                    .update({
                        "organization_id": str(organization_id),
                        "role": role
                    })\
                    .eq("id", user['id'])\
                    .execute()
                
                if success.data:
                    logger.info(f"✅ Existing user {email} added to organization {organization_id}")
                    return jsonify({
                        "status": "success",
                        "message": f"User {email} added to organization",
                        "data": {
                            "email": email,
                            "role": role,
                            "user_id": user['id']
                        }
                    }), 200
        
        # TODO: Implementar sistema de invitaciones con email
        # Por ahora, retornamos un mensaje indicando que el usuario debe registrarse
        
        logger.info(f"📧 Invitation requested for {email} to organization {organization_id}")
        
        return jsonify({
            "status": "success",
            "message": "Invitation functionality coming soon",
            "note": "For now, ask the user to register first, then you can add them to your organization",
            "data": {
                "email": email,
                "role": role,
                "organization_id": organization_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error inviting member: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to invite member"
        }), 500
