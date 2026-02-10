"""
Credits Service - Sistema de Créditos para Multi-Tenancy

VERSIÓN: 1.0
Fecha: 9 de Diciembre, 2025

Responsabilidades:
- Verificar disponibilidad de créditos (usuario u organización)
- Consumir créditos de operaciones
- Registrar transacciones en historial
- Calcular regeneraciones gratuitas disponibles
- Reset mensual de créditos (via cron job)

Principio KISS: Lógica simple y directa, sin over-engineering.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from backend.core.database import get_database_client, retry_on_connection_error
from backend.core.plans import (
    get_operation_cost,
    get_free_regenerations,
    has_unlimited_regenerations,
    CREDIT_COSTS
)

logger = logging.getLogger(__name__)


class CreditsService:
    """Servicio para gestión de créditos en sistema multi-tenant"""
    
    def __init__(self):
        self.db = get_database_client()
    
    # ========================
    # VERIFICACIÓN DE CRÉDITOS
    # ========================
    
    @retry_on_connection_error(max_retries=3, initial_delay=0.5, backoff_factor=2.0)
    def check_credits_available(
        self, 
        organization_id: Optional[str], 
        operation: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, int, str]:
        """
        Verificar si hay créditos disponibles para una operación.
        
        Args:
            organization_id: ID de la organización (None para usuarios personales)
            operation: Tipo de operación ('extraction', 'generation', 'complete', etc.)
            user_id: ID del usuario (requerido para créditos personales)
        
        Returns:
            Tuple (tiene_creditos, creditos_disponibles, mensaje)
        
        Ejemplo:
            has_credits, available, msg = service.check_credits_available(org_id, 'extraction')
            if not has_credits:
                raise InsufficientCreditsError(msg)
        """
        try:
            # Obtener costo de la operación
            cost = get_operation_cost(operation)
            
            # Si NO hay organización → usuario personal
            if not organization_id:
                if not user_id:
                    return False, 0, "User ID required for personal plan credits"
                
                # Obtener créditos del usuario personal
                user_result = self.db.client.table("user_credits")\
                    .select("credits_total, credits_used, plan_tier")\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()
                
                if not user_result.data:
                    # Inicializar créditos si no existen
                    self.db.client.rpc("initialize_user_credits", {"p_user_id": user_id}).execute()
                    # Reintentar
                    user_result = self.db.client.table("user_credits")\
                        .select("credits_total, credits_used, plan_tier")\
                        .eq("user_id", user_id)\
                        .single()\
                        .execute()
                
                if not user_result.data:
                    return False, 0, f"Could not initialize credits for user {user_id}"
                
                user_data = user_result.data
                credits_total = user_data.get("credits_total", 0)
                credits_used = user_data.get("credits_used", 0)
                credits_available = credits_total - credits_used
                
                # Verificar si hay suficientes créditos
                if credits_available >= cost:
                    return True, credits_available, f"OK - {credits_available} credits available (personal plan)"
                else:
                    return False, credits_available, (
                        f"Insufficient credits. Required: {cost}, Available: {credits_available}. "
                        f"Personal plan (free tier). Consider joining an organization."
                    )
            
            # Si hay organización → créditos organizacionales
            org_result = self.db.client.table("organizations")\
                .select("credits_total, credits_used, plan_tier")\
                .eq("id", organization_id)\
                .single()\
                .execute()
            
            if not org_result.data:
                return False, 0, f"Organization {organization_id} not found"
            
            org_data = org_result.data
            credits_total = org_data.get("credits_total", 0)
            credits_used = org_data.get("credits_used", 0)
            credits_available = credits_total - credits_used
            
            # Verificar si hay suficientes créditos
            if credits_available >= cost:
                return True, credits_available, f"OK - {credits_available} credits available"
            else:
                plan_tier = org_data.get("plan_tier", "unknown")
                return False, credits_available, (
                    f"Insufficient credits. Required: {cost}, Available: {credits_available}. "
                    f"Current plan: {plan_tier}. Consider upgrading."
                )
        
        except Exception as e:
            logger.error(f"Error checking credits: {e}")
            return False, 0, f"Error checking credits: {str(e)}"
    
    @retry_on_connection_error(max_retries=3, initial_delay=0.5, backoff_factor=2.0)
    def get_credits_info(self, organization_id: str, user_id: Optional[str] = None) -> Dict:
        """
        Obtener información completa de créditos de una organización.
        
        Args:
            organization_id: ID de la organización
        
        Returns:
            Diccionario con información de créditos
        """
        try:
            # Validar que organization_id no sea None
            if not organization_id:
                return self.get_credits_info_for_user(user_id)
            
            org_result = self.db.client.table("organizations")\
                .select("credits_total, credits_used, credits_reset_date, plan_tier")\
                .eq("id", organization_id)\
                .single()\
                .execute()
            
            if not org_result.data:
                return {
                    "status": "error",
                    "message": "Organization not found"
                }
            
            org_data = org_result.data
            credits_total = org_data.get("credits_total", 0)
            credits_used = org_data.get("credits_used", 0)
            credits_available = credits_total - credits_used
            reset_date = org_data.get("credits_reset_date")
            
            logger.info(f"✅ Organization credits - Total: {credits_total}, Used: {credits_used}, Available: {credits_available}")
            
            return {
                "status": "success",
                "credits_total": credits_total,
                "credits_used": credits_used,
                "credits_available": credits_available,
                "credits_percentage": round((credits_available / credits_total * 100), 2) if credits_total > 0 else 0,
                "reset_date": reset_date,
                "plan_tier": org_data.get("plan_tier", "free"),
                "plan_type": "organizational"
            }
        
        except Exception as e:
            logger.error(f"Error getting credits info: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @retry_on_connection_error(max_retries=3, initial_delay=0.5, backoff_factor=2.0)
    def get_credits_info_for_user(self, user_id: str) -> Dict:
        """
        Obtener información de créditos para un usuario (organización o personal).
        
        LÓGICA DE FALLBACK:
        1. Buscar usuario en tabla users
        2. Si tiene organization_id → retornar créditos de organización
        3. Si NO tiene organization_id → retornar créditos personales
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con información de créditos
        """
        try:
            logger.info(f"🔍 Getting credits info for user: {user_id}")
            
            # Obtener información del usuario (usar maybe_single para evitar error si no existe)
            user_result = self.db.client.table("users")\
                .select("organization_id")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            logger.info(f"📊 User query result: {user_result.data}")
            
            if not user_result.data:
                logger.warning(f"⚠️ User {user_id} not found in database")
                return {
                    "status": "error",
                    "message": "User not found"
                }
            
            organization_id = user_result.data.get("organization_id")
            
            # Si el usuario pertenece a una organización
            if organization_id:
                logger.info(f"✅ User has organization: {organization_id} - fetching org credits")
                return self.get_credits_info(organization_id, user_id)
            
            # Si el usuario NO pertenece a una organización → plan personal
            logger.info(f"✅ User has NO organization - fetching personal credits")
            return self.get_personal_plan_credits_info(user_id)
        
        except Exception as e:
            logger.error(f"❌ Error getting credits info for user {user_id}: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Error details: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @retry_on_connection_error(max_retries=3, initial_delay=0.5, backoff_factor=2.0)
    def get_personal_plan_credits_info(self, user_id: str) -> Dict:
        """
        Obtener información de créditos para plan personal (free tier).
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Información de créditos del plan gratuito
        """
        try:
            logger.info(f"🔍 Getting personal plan credits for user: {user_id}")
            
            # Obtener créditos del usuario desde la tabla user_credits
            # Usar maybe_single() en lugar de single() para evitar error cuando no existe
            user_result = self.db.client.table("user_credits")\
                .select("credits_total, credits_used, plan_tier, credits_reset_date")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            
            logger.info(f"📊 User credits query result: {user_result.data}")
            
            if not user_result.data:
                logger.warning(f"⚠️ No user_credits found for user {user_id}, initializing...")
                # Inicializar créditos si no existen
                init_result = self.db.client.rpc("initialize_user_credits", {"p_user_id": user_id}).execute()
                logger.info(f"✅ Initialize result: {init_result}")
                
                # Reintentar
                user_result = self.db.client.table("user_credits")\
                    .select("credits_total, credits_used, plan_tier, credits_reset_date")\
                    .eq("user_id", user_id)\
                    .maybe_single()\
                    .execute()
                
                logger.info(f"📊 User credits after init: {user_result.data}")
            
            if not user_result.data:
                logger.error(f"❌ Could not retrieve user credits after initialization for user {user_id}")
                return {
                    "status": "error",
                    "message": "Could not retrieve user credits"
                }
            
            user_data = user_result.data
            credits_total = user_data.get("credits_total", 0)
            credits_used = user_data.get("credits_used", 0)
            credits_available = credits_total - credits_used
            reset_date = user_data.get("credits_reset_date")
            
            return {
                "status": "success",
                "credits_total": credits_total,
                "credits_used": credits_used,
                "credits_available": credits_available,
                "credits_percentage": round((credits_available / credits_total * 100), 2) if credits_total > 0 else 0,
                "reset_date": reset_date,
                "plan_tier": user_data.get("plan_tier", "free"),
                "plan_type": "personal"  # Indica que es plan personal
            }
        
        except Exception as e:
            logger.error(f"Error getting personal plan credits: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @retry_on_connection_error(max_retries=3, initial_delay=0.5, backoff_factor=2.0)
    def consume_credits(
        self,
        organization_id: Optional[str],
        operation: str,
        amount: Optional[int] = None,
        rfx_id: Optional[str] = None,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Consumir créditos de una organización o usuario personal y registrar transacción.
        
        Args:
            organization_id: ID de la organización (None para usuarios personales)
            operation: Tipo de operación
            amount: Cantidad de créditos (si None, usa costo de operación)
            rfx_id: ID del RFX relacionado (opcional)
            user_id: ID del usuario que ejecuta (requerido para usuarios personales)
            description: Descripción personalizada (opcional)
            metadata: Metadata adicional (opcional)
        
        Returns:
            Diccionario con resultado de la operación
        
        Ejemplo:
            result = service.consume_credits(
                organization_id=org_id,
                operation='extraction',
                rfx_id=rfx_id,
                user_id=user_id
            )
        """
        # Obtener costo si no se especificó
        if amount is None:
            amount = get_operation_cost(operation)
        
        # Verificar disponibilidad
        has_credits, available, msg = self.check_credits_available(
            organization_id, operation, user_id
        )
        
        if not has_credits:
            return {
                "status": "error",
                "message": msg,
                "credits_available": available
            }
        
        # Si NO hay organización → consumir créditos de usuario personal
        if not organization_id:
            if not user_id:
                return {
                    "status": "error",
                    "message": "User ID required for personal plan credits"
                }
            
            try:
                # 1. Obtener créditos actuales del usuario
                user_data = self.db.client.table("user_credits")\
                    .select("credits_used")\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()
                
                current_used = user_data.data.get("credits_used", 0) if user_data.data else 0
                new_used = current_used + amount
                
                # 2. Actualizar con nuevo valor
                self.db.client.table("user_credits")\
                    .update({"credits_used": new_used})\
                    .eq("user_id", user_id)\
                    .execute()
                
                logger.info(f"✅ Personal credits updated: {current_used} → {new_used} (user: {user_id})")
                
                return {
                    "status": "success",
                    "message": f"Successfully consumed {amount} credits (personal plan)",
                    "credits_consumed": amount,
                    "credits_remaining": available - amount
                }
                
            except Exception as e:
                logger.error(f"❌ Failed to update user credits: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to update user credits: {str(e)}"
                }
        
        # Si hay organización → consumir créditos organizacionales
        try:
            # 1. Obtener créditos actuales
            org_data = self.db.client.table("organizations")\
                .select("credits_used")\
                .eq("id", organization_id)\
                .single()\
                .execute()
            
            current_used = org_data.data.get("credits_used", 0) if org_data.data else 0
            new_used = current_used + amount
            
            # 2. Actualizar con nuevo valor
            self.db.client.table("organizations")\
                .update({"credits_used": new_used})\
                .eq("id", organization_id)\
                .execute()
            
            logger.info(f"✅ Credits updated: {current_used} → {new_used}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update credits_used: {e}")
            return {
                "status": "error",
                "message": f"Failed to update organization credits: {str(e)}"
            }
        
        # KISS: Registrar transacción (separado para identificar errores)
        try:
            transaction_data = {
                "organization_id": organization_id,
                "user_id": user_id,
                "amount": -amount,  # Negativo para consumo
                "type": operation,
                "description": description or f"Credits consumed for {operation}",
                "metadata": metadata or {},
                "rfx_id": rfx_id  # Siempre presente (usamos ID del RFX guardado)
            }
            
            transaction_result = self.db.client.table("credit_transactions")\
                .insert(transaction_data)\
                .execute()
            
            transaction_id = transaction_result.data[0]["id"] if transaction_result.data else None
            logger.info(f"✅ Transaction recorded: {transaction_id} (rfx_id: {rfx_id})")
            
        except Exception as e:
            logger.error(f"❌ Failed to record transaction: {e}")
            # No retornar error - los créditos ya se consumieron
            transaction_id = None
        
        logger.info(f"✅ Credits consumed: {amount} for '{operation}' (org: {organization_id})")
        
        return {
            "status": "success",
            "message": f"Successfully consumed {amount} credits",
            "credits_consumed": amount,
            "credits_remaining": available - amount,
            "transaction_id": transaction_id
        }
    
    # ========================
    # REGENERACIONES GRATUITAS
    # ========================
    
    def check_free_regeneration_available(
        self,
        organization_id: str,
        rfx_id: str
    ) -> Tuple[bool, int, str]:
        """
        Verificar si hay regeneraciones gratuitas disponibles.
        
        Args:
            organization_id: ID de la organización
            rfx_id: ID del RFX
        
        Returns:
            Tuple (tiene_regeneracion_gratis, regeneraciones_usadas, mensaje)
        """
        try:
            # Obtener plan de la organización
            org_result = self.db.client.table("organizations")\
                .select("plan_tier")\
                .eq("id", organization_id)\
                .single()\
                .execute()
            
            if not org_result.data:
                return False, 0, "Organization not found"
            
            plan_tier = org_result.data.get("plan_tier", "free")
            
            # Verificar si tiene regeneraciones ilimitadas
            if has_unlimited_regenerations(plan_tier):
                return True, 0, "Unlimited regenerations available"
            
            # Obtener límite de regeneraciones gratuitas
            free_limit = get_free_regenerations(plan_tier)
            
            # Obtener estado de procesamiento del RFX
            processing_result = self.db.client.table("rfx_processing_status")\
                .select("free_regenerations_used")\
                .eq("rfx_id", rfx_id)\
                .single()\
                .execute()
            
            if not processing_result.data:
                # Si no existe, asumir 0 regeneraciones usadas
                return True, 0, f"{free_limit} free regenerations available"
            
            used = processing_result.data.get("free_regenerations_used", 0)
            
            if used < free_limit:
                return True, used, f"{free_limit - used} free regenerations remaining"
            else:
                return False, used, f"Free regeneration limit reached ({free_limit}). Credits will be consumed."
        
        except Exception as e:
            logger.error(f"Error checking free regenerations: {e}")
            return False, 0, f"Error: {str(e)}"
    
    def use_free_regeneration(self, rfx_id: str) -> bool:
        """
        Marcar una regeneración gratuita como usada.
        
        Args:
            rfx_id: ID del RFX
        
        Returns:
            True si se marcó exitosamente
        """
        try:
            # Incrementar contador de regeneraciones gratuitas usadas
            self.db.client.rpc(
                "increment_free_regenerations",
                {"rfx_id_param": rfx_id}
            ).execute()
            
            logger.info(f"✅ Free regeneration used for RFX {rfx_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error using free regeneration: {e}")
            return False
    
    # ========================
    # HISTORIAL DE TRANSACCIONES
    # ========================
    
    def get_transaction_history(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Obtener historial de transacciones de créditos.
        
        Args:
            organization_id: ID de la organización
            limit: Número máximo de transacciones
            offset: Offset para paginación
        
        Returns:
            Diccionario con transacciones
        """
        try:
            result = self.db.client.table("credit_transactions")\
                .select("*")\
                .eq("organization_id", organization_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return {
                "status": "success",
                "transactions": result.data,
                "count": len(result.data)
            }
        
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return {
                "status": "error",
                "message": str(e),
                "transactions": []
            }
    
    # ========================
    # RESET MENSUAL (CRON JOB)
    # ========================
    
    def reset_monthly_credits(self) -> Dict:
        """
        Reset mensual de créditos para todas las organizaciones.
        
        NOTA: Este método debe ser llamado por un cron job mensual.
        
        Returns:
            Diccionario con resultado del reset
        """
        try:
            # Obtener todas las organizaciones que necesitan reset
            now = datetime.now()
            
            orgs_result = self.db.client.table("organizations")\
                .select("id, plan_tier, credits_reset_date")\
                .lte("credits_reset_date", now.isoformat())\
                .execute()
            
            reset_count = 0
            
            for org in orgs_result.data:
                org_id = org["id"]
                plan_tier = org.get("plan_tier", "free")
                
                # Obtener créditos del plan
                from backend.core.plans import get_plan
                plan = get_plan(plan_tier)
                
                if not plan:
                    logger.warning(f"Plan not found for organization {org_id}")
                    continue
                
                # Reset créditos
                self.db.client.table("organizations")\
                    .update({
                        "credits_used": 0,
                        "credits_total": plan.credits_per_month,
                        "credits_reset_date": (now + timedelta(days=30)).isoformat()
                    })\
                    .eq("id", org_id)\
                    .execute()
                
                # Registrar transacción de reset
                self.db.client.table("credit_transactions")\
                    .insert({
                        "organization_id": org_id,
                        "amount": plan.credits_per_month,
                        "type": "monthly_reset",
                        "description": f"Monthly credits reset for {plan_tier} plan"
                    })\
                    .execute()
                
                reset_count += 1
                logger.info(f"✅ Credits reset for organization {org_id} ({plan_tier})")
            
            return {
                "status": "success",
                "message": f"Credits reset for {reset_count} organizations",
                "reset_count": reset_count
            }
        
        except Exception as e:
            logger.error(f"Error resetting monthly credits: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# ========================
# INSTANCIA GLOBAL
# ========================

_credits_service_instance = None

def get_credits_service() -> CreditsService:
    """Obtener instancia singleton del servicio de créditos"""
    global _credits_service_instance
    if _credits_service_instance is None:
        _credits_service_instance = CreditsService()
    return _credits_service_instance
