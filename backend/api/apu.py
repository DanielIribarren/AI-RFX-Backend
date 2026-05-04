"""
APU API — Análisis de Precios Unitarios for Venezuelan construction RFXs.

Single endpoint:
  POST /api/apu/generate   Generate an APU Excel from an existing RFX.

Auth follows the same pattern as /api/proposals/generate (optional JWT,
multi-source user_id resolution).
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from backend.core.database import get_database_client
from backend.models.apu_models import APUGenerateRequest
from backend.services.apu_generator import APUGenerationError, APUGeneratorService
from backend.utils.auth_middleware import get_current_user, optional_jwt

logger = logging.getLogger(__name__)

apu_bp = Blueprint("apu_api", __name__, url_prefix="/api/apu")


@apu_bp.route("/<rfx_id>", methods=["GET"])
@optional_jwt
def get_latest_apu(rfx_id: str):
    """Return the latest persisted APU for an RFX, or null if none exists.

    Response shape mirrors the POST /generate endpoint so the frontend can
    rehydrate APU state on page load using the same `APUResult` interface.
    """
    db = get_database_client()
    rfx = db.get_rfx_by_id(rfx_id)
    if not rfx:
        return jsonify({
            "status": "error",
            "message": f"RFX {rfx_id} not found",
        }), 404

    excel_url = rfx.get("apu_excel_url")
    if not excel_url:
        # Valid state: the RFX exists but has never generated an APU.
        return jsonify({"status": "success", "data": None}), 200

    return jsonify({
        "status": "success",
        "data": {
            "rfx_id": rfx_id,
            "excel_url": excel_url,
            "excel_storage_path": rfx.get("apu_excel_storage_path") or "",
            "prompt_version": rfx.get("apu_prompt_version") or "unknown",
            "llm_attempts": 1,
            "warnings": [],
            "partidas_count": rfx.get("apu_partidas_count") or 0,
        },
    }), 200


@apu_bp.route("/generate", methods=["POST"])
@optional_jwt
def generate_apu():
    """Generate an APU Excel for the given RFX.

    Body:
        rfx_id (str, required)
        tasa_bcv (float, optional)
        pct_costos_indirectos (float, optional)
        pct_utilidad (float, optional)
    """
    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "Content-Type must be application/json",
        }), 400

    try:
        payload = APUGenerateRequest(**(request.get_json() or {}))
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": "Invalid request body",
            "error": e.errors(),
        }), 400

    user_id = _resolve_user_id(payload.rfx_id)
    if not user_id:
        return jsonify({
            "status": "error",
            "message": "user_id is required (authenticate or supply via RFX).",
        }), 400

    logger.info("APU generation requested rfx_id=%s user_id=%s", payload.rfx_id, user_id)

    try:
        service = APUGeneratorService()
        result = service.generate(
            rfx_id=payload.rfx_id,
            tasa_bcv=payload.tasa_bcv,
            pct_costos_indirectos=payload.pct_costos_indirectos,
            pct_utilidad=payload.pct_utilidad,
        )
    except APUGenerationError as e:
        logger.error("APU generation failed rfx_id=%s: %s", payload.rfx_id, e)
        return jsonify({
            "status": "error",
            "message": "APU generation failed",
            "error": str(e),
        }), 422
    except Exception as e:
        logger.exception("APU generation crashed rfx_id=%s", payload.rfx_id)
        return jsonify({
            "status": "error",
            "message": "Internal error during APU generation",
            "error": str(e),
        }), 500

    return jsonify({
        "status": "success",
        "data": result.model_dump(),
    }), 200


def _resolve_user_id(rfx_id: str) -> str | None:
    """Multi-source user_id resolution mirroring /api/proposals/generate."""
    current_user = get_current_user()
    if current_user:
        return str(current_user["id"])

    body_user_id = (request.get_json() or {}).get("user_id")
    if body_user_id:
        return str(body_user_id)

    try:
        rfx_data = get_database_client().get_rfx_by_id(rfx_id)
        if rfx_data and rfx_data.get("user_id"):
            return str(rfx_data["user_id"])
    except Exception as e:
        logger.warning("Could not resolve user_id from RFX %s: %s", rfx_id, e)

    return None
