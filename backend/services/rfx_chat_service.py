"""
Servicio de persistencia para el chat conversacional RFX.

Responsabilidad: Guardar y recuperar mensajes del chat en Supabase.
KISS: Solo hace operaciones CRUD simples, sin lógica de negocio.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)


class RFXChatService:
    """
    Servicio para persistir mensajes del chat.
    
    KISS: Solo hace 3 cosas:
    1. Guardar mensajes en BD
    2. Recuperar historial
    3. Guardar confirmaciones pendientes
    
    Sin lógica de negocio - solo persistencia.
    """
    
    def __init__(self):
        """Inicializa el cliente de Supabase."""
        self.supabase = get_supabase()
    
    async def save_chat_message(
        self,
        rfx_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
        changes_applied: List[Dict[str, Any]],
        confidence: float,
        requires_confirmation: bool = False,
        user_files: List[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        processing_time_ms: int = 0,
        model_used: str = ""
    ) -> Dict[str, Any]:
        """
        Guarda un mensaje del chat en la base de datos.
        
        KISS: Inserción directa sin validaciones complejas.
        La IA ya validó todo.
        """
        try:
            data = {
                "rfx_id": rfx_id,
                "user_id": user_id,
                "user_message": user_message,
                "user_files": user_files or [],
                "assistant_message": assistant_message,
                "confidence": confidence,
                "changes_applied": changes_applied,
                "requires_confirmation": requires_confirmation,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "processing_time_ms": processing_time_ms,
                "model_used": model_used,
            }
            
            result = self.supabase.table("rfx_chat_history").insert(data).execute()
            
            logger.info(
                f"[RFXChatService] Message saved: "
                f"rfx_id={rfx_id}, confidence={confidence:.2f}"
            )
            
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logger.error(f"[RFXChatService] Error saving message: {e}", exc_info=True)
            raise
    
    async def get_chat_history(
        self,
        rfx_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Recupera el historial de chat de un RFX.
        
        KISS: Query simple ordenado por fecha.
        """
        try:
            result = (
                self.supabase
                .table("rfx_chat_history")
                .select("*")
                .eq("rfx_id", rfx_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            messages = result.data if result.data else []
            
            logger.info(
                f"[RFXChatService] History retrieved: "
                f"rfx_id={rfx_id}, count={len(messages)}"
            )
            
            return messages
            
        except Exception as e:
            logger.error(f"[RFXChatService] Error getting history: {e}", exc_info=True)
            return []
    
    async def save_pending_confirmation(
        self,
        rfx_id: str,
        user_id: str,
        chat_message_id: str,
        options: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Guarda una confirmación pendiente.
        
        KISS: Inserción simple con expiración automática (1 hora).
        """
        try:
            data = {
                "rfx_id": rfx_id,
                "user_id": user_id,
                "chat_message_id": chat_message_id,
                "options": options,
            }
            
            result = (
                self.supabase
                .table("rfx_pending_confirmations")
                .insert(data)
                .execute()
            )
            
            logger.info(
                f"[RFXChatService] Confirmation saved: "
                f"rfx_id={rfx_id}, options={len(options)}"
            )
            
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logger.error(f"[RFXChatService] Error saving confirmation: {e}", exc_info=True)
            raise
    
    async def confirm_option(
        self,
        confirmation_id: str,
        option_value: str
    ) -> bool:
        """
        Marca una confirmación como confirmada.
        
        KISS: Update simple.
        """
        try:
            result = (
                self.supabase
                .table("rfx_pending_confirmations")
                .update({
                    "confirmed_at": datetime.utcnow().isoformat(),
                    "confirmed_option": option_value
                })
                .eq("id", confirmation_id)
                .execute()
            )
            
            success = bool(result.data)
            
            logger.info(
                f"[RFXChatService] Confirmation updated: "
                f"id={confirmation_id}, option={option_value}, success={success}"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"[RFXChatService] Error confirming option: {e}", exc_info=True)
            return False


# Exportar
__all__ = ["RFXChatService"]
