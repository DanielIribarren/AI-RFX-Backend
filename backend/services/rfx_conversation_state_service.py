"""
Servicio de memoria/estado conversacional por RFX.

Regla de diseño:
- El scope de memoria es SIEMPRE rfx_id.
- No hay estado global ni por usuario.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)


class RFXConversationStateService:
    """Persistencia de estado conversacional por rfx_id."""

    def __init__(self):
        self.supabase = get_supabase()

    async def get_state(self, rfx_id: str) -> Dict[str, Any]:
        try:
            result = (
                self.supabase
                .table("rfx_conversation_state")
                .select("*")
                .eq("rfx_id", rfx_id)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
            return {
                "rfx_id": rfx_id,
                "state": {},
                "status": "active",
                "last_intent": None,
                "last_user_message": None,
                "last_assistant_message": None,
                "requires_clarification": False,
            }
        except Exception as e:
            logger.error(f"❌ Error getting conversation state for rfx_id={rfx_id}: {e}")
            return {
                "rfx_id": rfx_id,
                "state": {},
                "status": "active",
                "requires_clarification": False,
            }

    async def upsert_state(
        self,
        rfx_id: str,
        state: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        last_intent: Optional[str] = None,
        last_user_message: Optional[str] = None,
        last_assistant_message: Optional[str] = None,
        requires_clarification: Optional[bool] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"rfx_id": rfx_id}

        if state is not None:
            payload["state"] = state
        if status is not None:
            payload["status"] = status
        if last_intent is not None:
            payload["last_intent"] = last_intent
        if last_user_message is not None:
            payload["last_user_message"] = last_user_message
        if last_assistant_message is not None:
            payload["last_assistant_message"] = last_assistant_message
        if requires_clarification is not None:
            payload["requires_clarification"] = bool(requires_clarification)

        try:
            result = (
                self.supabase
                .table("rfx_conversation_state")
                .upsert(payload, on_conflict="rfx_id")
                .execute()
            )
            return result.data[0] if result.data else payload
        except Exception as e:
            logger.error(f"❌ Error upserting conversation state for rfx_id={rfx_id}: {e}")
            return payload

    async def add_event(
        self,
        rfx_id: str,
        role: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = {
            "rfx_id": rfx_id,
            "role": role,
            "message": message,
            "payload": payload or {},
        }
        try:
            result = self.supabase.table("rfx_conversation_events").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"❌ Error adding conversation event for rfx_id={rfx_id}: {e}")
            return data

    async def get_recent_events(self, rfx_id: str, limit: int = 12) -> List[Dict[str, Any]]:
        try:
            result = (
                self.supabase
                .table("rfx_conversation_events")
                .select("role, message, payload, created_at")
                .eq("rfx_id", rfx_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            events = result.data or []
            events.reverse()
            return events
        except Exception as e:
            logger.error(f"❌ Error getting conversation events for rfx_id={rfx_id}: {e}")
            return []


__all__ = ["RFXConversationStateService"]
