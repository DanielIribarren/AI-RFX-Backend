"""
Servicio de sesión temporal para revisión pre-RFX.

Objetivo:
- Guardar extracción/resolución antes de crear rfx_v2.
- Permitir chat de ajustes con memoria por session_id.
- Crear RFX final solo cuando el usuario confirma.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

from backend.core.database import get_supabase

logger = logging.getLogger(__name__)


class RFXProcessingSessionService:
    """Persistencia de sesiones temporales de procesamiento."""

    DEFAULT_TTL_HOURS = 24
    _MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.supabase = get_supabase()

    def create_session(
        self,
        user_id: str,
        organization_id: Optional[str],
        preview_data: Dict[str, Any],
        validated_data: Dict[str, Any],
        evaluation_metadata: Optional[Dict[str, Any]] = None,
        *,
        status: str = "clarification",
        conversation_state: Optional[Dict[str, Any]] = None,
        recent_events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        session_id = str(uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.DEFAULT_TTL_HOURS)
        state = {
            "workflow_status": "extracted_pending_review",
            "review_required": True,
            "review_confirmed": False,
            "can_proceed_without_answers": True,
        }
        state.update(conversation_state or {})

        preview_copy = dict(preview_data or {})
        if preview_copy.get("products"):
            preview_copy["products"] = self._ensure_preview_product_ids(preview_copy.get("products") or [])

        if not state.get("suggested_first_message"):
            if preview_copy:
                state["suggested_first_message"] = self._build_first_message(preview_copy)
            else:
                state["suggested_first_message"] = (
                    "We received your request and are preparing the extraction preview. "
                    "This usually takes a few seconds."
                )

        initial_events = list(recent_events or [])
        if not initial_events:
            initial_events = [
                {
                    "role": "assistant",
                    "message": state["suggested_first_message"],
                    "payload": {"event_type": "review_kickoff"},
                    "created_at": now.isoformat(),
                }
            ]

        payload = {
            "id": session_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "status": status,
            "review_required": True,
            "review_confirmed": False,
            "preview_data": preview_copy,
            "validated_data": validated_data or {},
            "evaluation_metadata": evaluation_metadata or {},
            "conversation_state": state,
            "recent_events": initial_events,
            "expires_at": expires_at.isoformat(),
        }

        try:
            result = self.supabase.table("rfx_processing_sessions").insert(payload).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"⚠️ Session table unavailable, using in-memory fallback: {e}")
            self._MEMORY_SESSIONS[session_id] = payload
        return payload

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                self.supabase
                .table("rfx_processing_sessions")
                .select("*")
                .eq("id", session_id)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
            return self._MEMORY_SESSIONS.get(session_id)
        except Exception as e:
            logger.warning(f"⚠️ Error fetching session from DB, trying memory fallback: {e}")
            return self._MEMORY_SESSIONS.get(session_id)

    def get_session_for_user(
        self,
        session_id: str,
        user_id: str,
        organization_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            return None

        session_user_id = str(session.get("user_id") or "")
        session_org_id = session.get("organization_id")
        if session_org_id:
            if organization_id:
                if str(session_org_id) != str(organization_id):
                    return None
            else:
                # Fallback defensivo: si por algún motivo no llega org en el contexto,
                # permitir al owner de la sesión continuar el flujo de revisión.
                if session_user_id != str(user_id):
                    return None
                logger.warning(
                    "⚠️ Missing organization_id in auth context for session %s; "
                    "falling back to owner-based session access",
                    session_id,
                )
        else:
            if session_user_id != str(user_id):
                return None
        return session

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            update_payload = {**(updates or {}), "updated_at": datetime.utcnow().isoformat()}
            result = (
                self.supabase
                .table("rfx_processing_sessions")
                .update(update_payload)
                .eq("id", session_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            if session_id in self._MEMORY_SESSIONS:
                self._MEMORY_SESSIONS[session_id].update(update_payload)
                return self._MEMORY_SESSIONS[session_id]
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error updating session in DB, trying memory fallback: {e}")
            if session_id in self._MEMORY_SESSIONS:
                self._MEMORY_SESSIONS[session_id].update({**(updates or {}), "updated_at": datetime.utcnow().isoformat()})
                return self._MEMORY_SESSIONS[session_id]
            return None

    def append_event(
        self,
        session_id: str,
        role: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        session = self.get_session(session_id)
        if not session:
            return

        events: List[Dict[str, Any]] = list(session.get("recent_events") or [])
        events.append(
            {
                "role": role,
                "message": message,
                "payload": payload or {},
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        events = events[-40:]
        self.update_session(session_id, {"recent_events": events})

    def update_preview_data(self, session_id: str, preview_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"preview_data": preview_data or {}})

    def update_validated_data(self, session_id: str, validated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.update_session(session_id, {"validated_data": validated_data or {}})

    def mark_confirmed(self, session_id: str, rfx_id: str) -> Optional[Dict[str, Any]]:
        return self.update_session(
            session_id,
            {
                "status": "confirmed",
                "review_confirmed": True,
                "confirmed_rfx_id": rfx_id,
            },
        )

    def _build_first_message(self, preview_data: Dict[str, Any]) -> str:
        requester_name = preview_data.get("requester_name") or "solicitante"
        location = preview_data.get("location") or "por definir"
        delivery_date = str(preview_data.get("delivery_date") or "por definir")
        products = preview_data.get("products") or []
        names = []
        for p in products[:6]:
            names.append(str((p or {}).get("nombre") or (p or {}).get("product_name") or "producto"))
        product_preview = ", ".join(names) if names else "sin productos claros"

        return (
            f"I identified a request for {requester_name}. "
            f"Preliminary context: delivery on {delivery_date} in {location}. "
            f"Detected products: {product_preview}. "
            f"Confirm whether this looks correct or tell me what should change before we continue."
        )

    def _ensure_preview_product_ids(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for p in products:
            item = dict(p or {})
            if not item.get("id"):
                item["id"] = str(uuid4())
            result.append(item)
        return result


__all__ = ["RFXProcessingSessionService"]
