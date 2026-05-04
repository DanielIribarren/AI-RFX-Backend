"""
Lightweight session review chat service.

Purpose:
- Keep the new intake/review flow independent from the legacy LangChain ChatAgent
- Convert user review feedback into structured changes over the session preview
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from backend.core.config import get_openai_config
from backend.models.chat_models import (
    ChangeType,
    ChatMetadata,
    ChatResponse,
    ConfirmationOption,
    RFXChange,
)

logger = logging.getLogger(__name__)


class SessionReviewChatService:
    """OpenAI-backed structured chat for review sessions."""

    def __init__(self, client: Optional[OpenAI] = None, model: Optional[str] = None):
        config = get_openai_config()
        self.client = client or OpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=0,
        )
        self.model = model or config.chat_model or "gpt-4o-mini"

    def process_message(
        self,
        *,
        session_id: str,
        message: str,
        context: Dict[str, Any],
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        started_at = time.perf_counter()

        system_prompt = (
            "You help a sales operator review an extracted service request before proposal generation. "
            "Your job is to transform the operator feedback into structured changes over the review session. "
            "Return ONLY valid JSON with keys: message, confidence, requires_confirmation, options, changes. "
            "Never include markdown fences. "
            "Allowed change types: update_field, add_product, update_product, delete_product. "
            "For update_field, target must be a field name and data must contain the new value. "
            "For add_product, target must be 'new' and data must include nombre, cantidad, unidad. "
            "Do not invent prices or costs unless the user explicitly provided them. "
            "If pricing is unknown, leave precio_unitario and costo_unitario as 0. "
            "For update_product and delete_product, prefer using an existing product id from current_products. "
            "If the request is ambiguous, set requires_confirmation=true, provide options, and avoid destructive changes. "
            "Use the same language as the user message."
        )

        user_payload = {
            "session_id": session_id,
            "user_message": message,
            "attached_files": [
                {
                    "name": f.get("name"),
                    "type": f.get("type"),
                }
                for f in (files or [])
            ],
            "session_context": self._compact_context(context),
        }

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )

        raw_content = (response.choices[0].message.content or "").strip()
        payload = self._parse_json_payload(raw_content)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        usage = getattr(response, "usage", None)
        tokens_used = getattr(usage, "total_tokens", None)

        return self._build_chat_response(
            payload=payload,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            model_used=getattr(response, "model", self.model) or self.model,
        )

    def _compact_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        products = []
        for product in list(context.get("current_products") or [])[:25]:
            products.append(
                {
                    "id": product.get("id"),
                    "nombre": product.get("nombre") or product.get("product_name") or product.get("name"),
                    "cantidad": product.get("cantidad") if product.get("cantidad") is not None else product.get("quantity"),
                    "unidad": product.get("unidad") or product.get("unit"),
                    "precio_unitario": (
                        product.get("precio_unitario")
                        if product.get("precio_unitario") is not None
                        else product.get("estimated_unit_price", product.get("unit_price"))
                    ),
                    "costo_unitario": (
                        product.get("costo_unitario")
                        if product.get("costo_unitario") is not None
                        else product.get("unit_cost")
                    ),
                    "descripcion": product.get("descripcion") or product.get("description"),
                }
            )

        return {
            "client_name": context.get("client_name"),
            "client_email": context.get("client_email"),
            "delivery_date": context.get("delivery_date"),
            "delivery_location": context.get("delivery_location"),
            "source_text": context.get("source_text"),
            "conversation_requires_clarification": bool(context.get("conversation_requires_clarification", False)),
            "current_total": context.get("current_total", 0),
            "current_products": products,
            "recent_events": list(context.get("recent_events") or [])[-6:],
        }

    def _parse_json_payload(self, raw_content: str) -> Dict[str, Any]:
        if not raw_content:
            return {}
        try:
            payload = json.loads(raw_content)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            logger.warning("⚠️ SessionReviewChatService returned non-JSON content: %s", raw_content[:300])
            return {}

    def _build_chat_response(
        self,
        *,
        payload: Dict[str, Any],
        duration_ms: int,
        tokens_used: Optional[int],
        model_used: str,
    ) -> ChatResponse:
        changes: List[RFXChange] = []
        for raw_change in payload.get("changes") or []:
            normalized_change = self._normalize_change(raw_change)
            if normalized_change is not None:
                changes.append(normalized_change)

        options: List[ConfirmationOption] = []
        for raw_option in payload.get("options") or []:
            if not isinstance(raw_option, dict):
                continue
            try:
                options.append(
                    ConfirmationOption(
                        value=str(raw_option.get("value") or "").strip() or "option",
                        label=str(raw_option.get("label") or "Review option").strip(),
                        emoji=str(raw_option.get("emoji") or "•"),
                        context=raw_option.get("context") if isinstance(raw_option.get("context"), dict) else None,
                    )
                )
            except Exception:
                continue

        confidence = payload.get("confidence", 0.65)
        try:
            confidence_value = max(0.0, min(1.0, float(confidence)))
        except Exception:
            confidence_value = 0.65

        message = str(payload.get("message") or "").strip()
        if not message:
            message = (
                "I reviewed your request and applied the suggested updates."
                if changes
                else "I reviewed your message, but I could not infer a safe structured change."
            )

        requires_confirmation = bool(payload.get("requires_confirmation", False))
        if requires_confirmation and not options:
            requires_confirmation = False

        return ChatResponse(
            status="success",
            message=message,
            confidence=confidence_value,
            reasoning=None,
            changes=changes,
            requires_confirmation=requires_confirmation,
            options=options,
            metadata=ChatMetadata(
                tokens_used=tokens_used,
                cost_usd=None,
                processing_time_ms=duration_ms,
                model_used=model_used,
            ),
        )

    def _normalize_change(self, raw_change: Any) -> Optional[RFXChange]:
        if not isinstance(raw_change, dict):
            return None

        type_value = str(raw_change.get("type") or "").strip().lower()
        valid_types = {change_type.value for change_type in ChangeType}
        if type_value not in valid_types:
            return None

        target = str(raw_change.get("target") or "").strip() or "new"
        data = raw_change.get("data")
        if not isinstance(data, dict):
            data = {}
        description = str(raw_change.get("description") or "").strip() or f"{type_value} {target}"

        try:
            return RFXChange(
                type=ChangeType(type_value),
                target=target,
                data=data,
                description=description,
            )
        except Exception:
            return None
