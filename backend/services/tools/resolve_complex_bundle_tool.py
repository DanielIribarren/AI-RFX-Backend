"""
Tool: resolve_complex_bundle_tool

Resuelve selección de desglose para productos complejos (menus/bundles)
a partir de restricciones del cliente.
"""

from __future__ import annotations

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def _score_option(option: Dict[str, Any], hints_text: str) -> float:
    tags = [
        _normalize_text(t)
        for t in (option.get("tags") or [])
        if isinstance(t, str)
    ]
    name = _normalize_text(option.get("name", ""))
    description = _normalize_text(option.get("description", ""))

    score = 0.0
    haystack = f"{name} {description} {' '.join(tags)}"

    for token in hints_text.split():
        if token and token in haystack:
            score += 1.0

    # Preferir explícitamente opciones low-carb cuando aparece el requerimiento
    if "low" in hints_text and "carb" in hints_text:
        if "low_carb" in tags or "sin_carbohidratos" in tags or "keto" in tags:
            score += 3.0
        if "carb" in tags and "low_carb" not in tags:
            score -= 2.0

    return score


def resolve_complex_bundle_tool(
    bundle_schema: Dict[str, Any],
    requirement_hints: List[str],
    fallback_policy: str = "ask_user",
) -> Dict[str, Any]:
    """
    bundle_schema esperado:
    {
      "slots": [
        {"slot": "lunes", "required": true, "options": [{"name": "...", "tags": ["..."]}]}
      ]
    }
    """
    try:
        schema = bundle_schema or {}
        slots = schema.get("slots") or []
        hints_text = _normalize_text(" ".join([h for h in (requirement_hints or []) if isinstance(h, str)]))

        if not slots:
            return {
                "status": "error",
                "message": "bundle_schema without slots",
                "requires_clarification": True,
                "breakdown": [],
            }

        breakdown: List[Dict[str, Any]] = []
        unresolved = 0

        for slot in slots:
            slot_name = slot.get("slot") or "slot"
            options = slot.get("options") or []
            required = bool(slot.get("required", True))

            if not options:
                breakdown.append(
                    {
                        "slot": slot_name,
                        "selected": None,
                        "reason": "no_options_available",
                    }
                )
                if required:
                    unresolved += 1
                continue

            scored = sorted(
                (
                    {
                        "option": opt,
                        "score": _score_option(opt, hints_text),
                    }
                    for opt in options
                ),
                key=lambda x: x["score"],
                reverse=True,
            )

            top = scored[0]
            selected = top["option"] if top["score"] > 0 else None

            if selected is None:
                if fallback_policy == "first_option":
                    selected = options[0]
                else:
                    unresolved += 1

            breakdown.append(
                {
                    "slot": slot_name,
                    "selected": selected,
                    "score": top["score"],
                    "required": required,
                }
            )

        requires_clarification = unresolved > 0
        return {
            "status": "success",
            "message": "bundle resolved",
            "requires_clarification": requires_clarification,
            "unresolved_slots": unresolved,
            "breakdown": breakdown,
        }
    except Exception as e:
        logger.error(f"❌ resolve_complex_bundle_tool failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "requires_clarification": True,
            "breakdown": [],
        }
