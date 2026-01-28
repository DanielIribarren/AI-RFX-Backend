"""
🔒 RFX Security Patch V3.0 - CRÍTICO para seguridad por usuario
Parche para agregar autenticación y filtrado por user_id a endpoints RFX existentes

PROBLEMA CRÍTICO:
- Los endpoints actuales NO filtran por user_id
- Cualquier usuario puede ver RFX de otros usuarios
- Los RFX nuevos no se asocian automáticamente al usuario creador

SOLUCIÓN:
- Wrapper functions que agregan validación de user_id
- Endpoints seguros que reemplazan los inseguros
- Auto-asignación de user_id en creación
"""
from flask import Blueprint, request, jsonify, g
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from backend.utils.auth_middleware import jwt_required, get_current_user, get_current_user_id
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

# Create secure blueprint  
rfx_secure_bp = Blueprint("rfx_secure_api", __name__, url_prefix="/api/rfx-secure")

# ========================
# SECURE DATABASE WRAPPERS
# ========================

def get_rfx_by_id_secure(rfx_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    🔒 Versión SEGURA de get_rfx_by_id que filtra por user_id
    
    Args:
        rfx_id: ID del RFX a obtener
        user_id: ID del usuario (debe ser dueño del RFX)
        
    Returns:
        Dict con datos del RFX si es dueño, None si no existe o no es dueño
    """
    try:
        db_client = get_database_client()
        
        # CRÍTICO: Usar Supabase client directamente (no query_one con JOINs)
        # Filtrar por id Y user_id para seguridad
        response = db_client.client.table("rfx_v2")\
            .select("*")\
            .eq("id", rfx_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"✅ RFX {rfx_id} accessed by owner {user_id}")
            return response.data[0]
        else:
            logger.warning(f"⚠️ RFX {rfx_id} access denied for user {user_id} (not found or not owner)")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting RFX {rfx_id} for user {user_id}: {e}")
        return None

def list_user_rfx(user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    🔒 Listar RFX del usuario autenticado solamente
    
    Args:
        user_id: ID del usuario
        limit: Límite de resultados
        offset: Offset para paginación
        
    Returns:
        Dict con RFX del usuario y metadatos de paginación
    """
    try:
        db_client = get_database_client()
        
        # Contar total de RFX del usuario
        total_count = db_client.query_one("""
            SELECT COUNT(*) as total
            FROM rfx_v2
            WHERE user_id = %s
        """, (user_id,))['total']
        
        # Obtener RFX del usuario con paginación
        rfx_list = db_client.query_all("""
            SELECT 
                rfx.id,
                rfx.title,
                rfx.description,
                rfx.rfx_type,
                rfx.status,
                rfx.priority,
                rfx.user_id,
                rfx.created_at,
                rfx.updated_at,
                companies.name as company_name,
                companies.email as company_email
            FROM rfx_v2 rfx
            LEFT JOIN companies ON rfx.company_id = companies.id
            WHERE rfx.user_id = %s
            ORDER BY rfx.created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        return {
            "rfx_list": [dict(rfx) for rfx in rfx_list] if rfx_list else [],
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing RFX for user {user_id}: {e}")
        return {
            "rfx_list": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False
        }

def create_rfx_with_user(rfx_data: Dict[str, Any], user_id: str) -> Optional[str]:
    """
    🔒 Crear RFX asignando automáticamente user_id
    
    Args:
        rfx_data: Datos del RFX
        user_id: ID del usuario creador (se asigna automáticamente)
        
    Returns:
        String con ID del RFX creado o None si falló
    """
    try:
        db_client = get_database_client()
        
        # CRÍTICO: Asignar user_id automáticamente (no del request)
        result = db_client.query_one("""
            INSERT INTO rfx_v2 (
                title, description, rfx_type, status, priority,
                user_id,  -- ← CRÍTICO: Asignar automáticamente
                company_id, requester_id,
                submission_deadline, expected_decision_date,
                project_start_date, project_end_date,
                budget_range_min, budget_range_max, currency,
                event_location, event_city, event_state, event_country,
                requirements, requested_products,
                evaluation_criteria, metadata_json
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s,  -- user_id  
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s
            )
            RETURNING id
        """, (
            rfx_data.get('title', 'Sin título'),
            rfx_data.get('description', ''),
            rfx_data.get('rfx_type', 'rfq'),
            rfx_data.get('status', 'draft'),
            rfx_data.get('priority', 'medium'),
            user_id,  # ← Auto-asignación de usuario
            rfx_data.get('company_id'),
            rfx_data.get('requester_id'),
            rfx_data.get('submission_deadline'),
            rfx_data.get('expected_decision_date'),
            rfx_data.get('project_start_date'),
            rfx_data.get('project_end_date'),
            rfx_data.get('budget_range_min'),
            rfx_data.get('budget_range_max'),
            rfx_data.get('currency', 'MXN'),
            rfx_data.get('event_location'),
            rfx_data.get('event_city'),
            rfx_data.get('event_state'),
            rfx_data.get('event_country', 'Mexico'),
            rfx_data.get('requirements'),
            rfx_data.get('requested_products', '[]'),
            rfx_data.get('evaluation_criteria', '{}'),
            rfx_data.get('metadata_json', '{}')
        ))
        
        if result:
            rfx_id = result['id']
            logger.info(f"✅ RFX created: {rfx_id} by user: {user_id}")
            return str(rfx_id)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error creating RFX for user {user_id}: {e}")
        return None

# ========================
# SECURE ENDPOINTS
# ========================

@rfx_secure_bp.route("/<rfx_id>", methods=["GET"])
@jwt_required
def get_my_rfx(rfx_id: str):
    """
    🔒 Obtener RFX específico (solo si soy dueño)
    
    Headers: Authorization: Bearer <token>
    """
    try:
        current_user_id = get_current_user_id()
        
        rfx_record = get_rfx_by_id_secure(rfx_id, current_user_id)
        
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found or access denied",
                "error": f"RFX {rfx_id} does not exist or you don't have permission to view it"
            }), 404
        
        return jsonify({
            "status": "success",
            "rfx": rfx_record
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@rfx_secure_bp.route("/my-rfx", methods=["GET"])
@jwt_required  
def list_my_rfx():
    """
    🔒 Listar MIS RFX (solo los que yo creé)
    
    Headers: Authorization: Bearer <token>
    Query params: limit, offset
    """
    try:
        current_user_id = get_current_user_id()
        
        # Parámetros de paginación
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = max(int(request.args.get('offset', 0)), 0)
        
        result = list_user_rfx(current_user_id, limit, offset)
        
        return jsonify({
            "status": "success",
            "user_id": current_user_id,
            **result
        })
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": "Invalid pagination parameters",
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Error listing RFX: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@rfx_secure_bp.route("/create", methods=["POST"])
@jwt_required
def create_my_rfx():
    """
    🔒 Crear RFX (se asigna automáticamente mi user_id)
    
    Headers: Authorization: Bearer <token>
    Body: RFX data (user_id se asigna automáticamente)
    """
    try:
        current_user_id = get_current_user_id()
        rfx_data = request.get_json()
        
        if not rfx_data:
            return jsonify({
                "status": "error",
                "message": "JSON body required"
            }), 400
        
        # Validar campos obligatorios
        if not rfx_data.get('title'):
            return jsonify({
                "status": "error",
                "message": "title is required"
            }), 400
        
        # CRÍTICO: Ignorar user_id del request y usar el del token JWT
        if 'user_id' in rfx_data:
            logger.warning(f"⚠️ Ignoring user_id from request, using authenticated user: {current_user_id}")
        
        rfx_id = create_rfx_with_user(rfx_data, current_user_id)
        
        if not rfx_id:
            return jsonify({
                "status": "error",
                "message": "Failed to create RFX"
            }), 500
        
        # Obtener RFX creado para respuesta
        rfx_record = get_rfx_by_id_secure(rfx_id, current_user_id)
        
        return jsonify({
            "status": "success",
            "message": "RFX created successfully",
            "rfx_id": rfx_id,
            "rfx": rfx_record
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error creating RFX: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@rfx_secure_bp.route("/<rfx_id>", methods=["PUT"])
@jwt_required
def update_my_rfx(rfx_id: str):
    """
    🔒 Actualizar RFX (solo si soy dueño)
    
    Headers: Authorization: Bearer <token>
    """
    try:
        current_user_id = get_current_user_id()
        
        # Verificar que el RFX existe y soy dueño
        existing_rfx = get_rfx_by_id_secure(rfx_id, current_user_id)
        if not existing_rfx:
            return jsonify({
                "status": "error",
                "message": "RFX not found or access denied"
            }), 404
        
        update_data = request.get_json()
        if not update_data:
            return jsonify({
                "status": "error",
                "message": "JSON body required"
            }), 400
        
        # CRÍTICO: No permitir cambio de user_id
        if 'user_id' in update_data:
            logger.warning(f"⚠️ Attempted to change user_id for RFX {rfx_id}, ignoring")
            del update_data['user_id']
        
        # Construir query de actualización dinámicamente
        set_clauses = []
        values = []
        
        allowed_fields = {
            'title', 'description', 'rfx_type', 'status', 'priority',
            'company_id', 'requester_id',
            'submission_deadline', 'expected_decision_date',
            'project_start_date', 'project_end_date',
            'budget_range_min', 'budget_range_max', 'currency',
            'event_location', 'event_city', 'event_state', 'event_country',
            'requirements', 'requested_products',
            'evaluation_criteria', 'metadata_json'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = %s")
                values.append(value)
        
        if not set_clauses:
            return jsonify({
                "status": "error",
                "message": "No valid fields to update"
            }), 400
        
        # Agregar updated_at y WHERE clause
        set_clauses.append("updated_at = NOW()")
        values.extend([rfx_id, current_user_id])
        
        db_client = get_database_client()
        query = f"""
            UPDATE rfx_v2 
            SET {', '.join(set_clauses)}
            WHERE id = %s AND user_id = %s
        """
        
        db_client.execute(query, tuple(values))
        
        # Obtener RFX actualizado
        updated_rfx = get_rfx_by_id_secure(rfx_id, current_user_id)
        
        return jsonify({
            "status": "success",
            "message": "RFX updated successfully",
            "rfx": updated_rfx
        })
        
    except Exception as e:
        logger.error(f"❌ Error updating RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@rfx_secure_bp.route("/<rfx_id>", methods=["DELETE"])
@jwt_required
def delete_my_rfx(rfx_id: str):
    """
    🔒 Eliminar RFX (solo si soy dueño)
    
    Headers: Authorization: Bearer <token>
    """
    try:
        current_user_id = get_current_user_id()
        
        # Verificar que el RFX existe y soy dueño
        existing_rfx = get_rfx_by_id_secure(rfx_id, current_user_id)
        if not existing_rfx:
            return jsonify({
                "status": "error",
                "message": "RFX not found or access denied"
            }), 404
        
        db_client = get_database_client()
        
        # PASO 1: Obtener pricing_config_id del RFX
        pricing_configs = db_client.client.table("rfx_pricing_configurations")\
            .select("id")\
            .eq("rfx_id", rfx_id)\
            .execute()
        
        # PASO 2: Eliminar configuraciones hijas (coordination, cost_per_person, tax)
        if pricing_configs.data:
            pricing_config_ids = [pc["id"] for pc in pricing_configs.data]
            
            # Eliminar coordination_configurations
            db_client.client.table("coordination_configurations")\
                .delete()\
                .in_("pricing_config_id", pricing_config_ids)\
                .execute()
            
            # Eliminar cost_per_person_configurations
            db_client.client.table("cost_per_person_configurations")\
                .delete()\
                .in_("pricing_config_id", pricing_config_ids)\
                .execute()
            
            # Eliminar tax_configurations
            db_client.client.table("tax_configurations")\
                .delete()\
                .in_("pricing_config_id", pricing_config_ids)\
                .execute()
            
            logger.info(f"🗑️ Deleted pricing sub-configurations for RFX {rfx_id}")
        
        # PASO 3: Eliminar rfx_pricing_configurations
        db_client.client.table("rfx_pricing_configurations")\
            .delete()\
            .eq("rfx_id", rfx_id)\
            .execute()
        
        # PASO 4: Eliminar productos del RFX
        db_client.client.table("rfx_products")\
            .delete()\
            .eq("rfx_id", rfx_id)\
            .execute()
        
        # PASO 5: Finalmente eliminar el RFX (solo si soy dueño)
        delete_response = db_client.client.table("rfx_v2")\
            .delete()\
            .eq("id", rfx_id)\
            .eq("user_id", current_user_id)\
            .execute()
        
        if not delete_response.data and delete_response.data != []:
            logger.warning(f"⚠️ RFX {rfx_id} deletion returned no data - may not exist")
        
        logger.info(f"✅ RFX {rfx_id} and all related data deleted by user {current_user_id}")
        
        return jsonify({
            "status": "success",
            "message": "RFX deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error deleting RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# ========================
# MIGRATION ENDPOINT (TEMPORAL)
# ========================

@rfx_secure_bp.route("/migrate-existing", methods=["POST"])
@jwt_required
def migrate_existing_rfx():
    """
    🔧 TEMPORAL: Migrar RFX existentes sin user_id al usuario actual
    
    SOLO para migración inicial - eliminar después del deploy
    Headers: Authorization: Bearer <token>
    
    Ejemplo de uso:
    curl -X POST http://localhost:5001/api/rfx-secure/migrate-existing \
      -H "Authorization: Bearer YOUR_TOKEN"
    """
    try:
        current_user_id = get_current_user_id()
        
        logger.info(f"🔄 Starting RFX migration for user: {current_user_id}")
        
        db_client = get_database_client()
        
        # Buscar RFX sin user_id usando Supabase client
        response = db_client.client.table("rfx_v2")\
            .select("id, title")\
            .is_("user_id", "null")\
            .limit(50)\
            .execute()
        
        orphaned_rfx = response.data if response.data else []
        
        if not orphaned_rfx:
            logger.info("✅ No orphaned RFX found")
            return jsonify({
                "status": "success",
                "message": "No orphaned RFX found - all RFX already have user_id assigned",
                "migrated_count": 0
            })
        
        logger.info(f"📋 Found {len(orphaned_rfx)} orphaned RFX to migrate")
        
        # Asignar al usuario actual (actualizar uno por uno)
        migrated_count = 0
        migrated_rfx = []
        
        for rfx in orphaned_rfx:
            try:
                update_response = db_client.client.table("rfx_v2")\
                    .update({"user_id": current_user_id})\
                    .eq("id", rfx['id'])\
                    .execute()
                
                if update_response.data:
                    migrated_count += 1
                    migrated_rfx.append({
                        "id": rfx['id'],
                        "title": rfx.get('title', 'Untitled')
                    })
                    logger.info(f"✅ Migrated RFX: {rfx['id']} - {rfx.get('title', 'Untitled')}")
            except Exception as update_error:
                logger.error(f"❌ Failed to migrate RFX {rfx['id']}: {update_error}")
                continue
        
        logger.info(f"✅ Successfully migrated {migrated_count} orphaned RFX to user {current_user_id}")
        
        return jsonify({
            "status": "success",
            "message": f"Successfully migrated {migrated_count} RFX to your account",
            "migrated_count": migrated_count,
            "migrated_rfx": migrated_rfx,
            "user_id": current_user_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error migrating RFX: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Internal server error during migration",
            "error": str(e)
        }), 500

# ========================
# TESTING ENDPOINT
# ========================

@rfx_secure_bp.route("/test", methods=["GET"])
@jwt_required
def test_secure_rfx():
    """
    🧪 Test endpoint para verificar autenticación
    """
    current_user = get_current_user()
    
    return jsonify({
        "status": "success",
        "message": "Secure RFX API is working",
        "user": {
            "id": str(current_user['id']),
            "email": current_user['email'],
            "full_name": current_user['full_name']
        },
        "endpoints": [
            "GET /<rfx_id> - Get my RFX",
            "GET /my-rfx - List my RFX", 
            "POST /create - Create RFX",
            "PUT /<rfx_id> - Update my RFX",
            "DELETE /<rfx_id> - Delete my RFX"
        ]
    })

# ========================
# LOGGING
# ========================

logger.info("🔒 Secure RFX API endpoints initialized")
logger.info("✅ All endpoints require JWT authentication")
logger.info("✅ All operations filtered by user_id for security")
