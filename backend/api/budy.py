"""
Budy API endpoints.

Adds the Budy Phase 1 domain surface while keeping legacy AI-RFX routes intact.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from backend.services.bcv_rate_service import bcv_rate_service
from backend.services.budy_domain_service import budy_domain_service
from backend.utils.auth_middleware import (
    get_current_user_id,
    get_current_user_organization_id,
    jwt_required,
)

logger = logging.getLogger(__name__)

bdy_bp = Blueprint("budy_api", __name__, url_prefix="/api")


def _json_error(message: str, status_code: int = 400):
    return jsonify({"status": "error", "message": message}), status_code


@bdy_bp.route("/business-units", methods=["GET"])
@jwt_required
def list_business_units():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        data = budy_domain_service.list_business_units(organization_id)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ list_business_units failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/business-units", methods=["POST"])
@jwt_required
def create_business_unit():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.create_business_unit(organization_id, payload)
        return jsonify({"status": "success", "data": data}), 201
    except Exception as exc:
        logger.error("❌ create_business_unit failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/business-units/<business_unit_id>", methods=["PATCH"])
@jwt_required
def update_business_unit(business_unit_id: str):
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.update_business_unit(organization_id, business_unit_id, payload)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ update_business_unit failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/catalog-items", methods=["GET"])
@jwt_required
def list_catalog_items():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        business_unit_id = request.args.get("business_unit_id")
        data = budy_domain_service.list_catalog_items(organization_id, business_unit_id)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ list_catalog_items failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/catalog-items", methods=["POST"])
@jwt_required
def create_catalog_item():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.create_catalog_item(organization_id, payload)
        return jsonify({"status": "success", "data": data}), 201
    except Exception as exc:
        logger.error("❌ create_catalog_item failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/catalog-items/<item_id>", methods=["PATCH"])
@jwt_required
def update_catalog_item(item_id: str):
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.update_catalog_item(organization_id, item_id, payload)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ update_catalog_item failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/catalog-items/<item_id>", methods=["DELETE"])
@jwt_required
def delete_catalog_item(item_id: str):
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        budy_domain_service.delete_catalog_item(organization_id, item_id)
        return jsonify({"status": "success", "message": "Catalog item deleted"}), 200
    except Exception as exc:
        logger.error("❌ delete_catalog_item failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/clients", methods=["GET"])
@jwt_required
def list_clients():
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        search = request.args.get("search", "").strip()
        data = budy_domain_service.list_clients(user_id, organization_id, search=search)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ list_clients failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/clients", methods=["POST"])
@jwt_required
def create_client():
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        payload = request.get_json() or {}
        data = budy_domain_service.create_client(user_id, organization_id, payload)
        return jsonify({"status": "success", "data": data}), 201
    except Exception as exc:
        logger.error("❌ create_client failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/payment-methods", methods=["GET"])
@jwt_required
def list_payment_methods():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        business_unit_id = request.args.get("business_unit_id")
        data = budy_domain_service.list_payment_methods(organization_id, business_unit_id)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ list_payment_methods failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/payment-methods", methods=["POST"])
@jwt_required
def create_payment_method():
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.create_payment_method(organization_id, payload)
        return jsonify({"status": "success", "data": data}), 201
    except Exception as exc:
        logger.error("❌ create_payment_method failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/payment-methods/<payment_method_id>", methods=["PATCH"])
@jwt_required
def update_payment_method(payment_method_id: str):
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        payload = request.get_json() or {}
        data = budy_domain_service.update_payment_method(organization_id, payment_method_id, payload)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ update_payment_method failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/payment-methods/<payment_method_id>", methods=["DELETE"])
@jwt_required
def delete_payment_method(payment_method_id: str):
    try:
        organization_id = budy_domain_service.require_organization(get_current_user_organization_id())
        budy_domain_service.delete_payment_method(organization_id, payment_method_id)
        return jsonify({"status": "success", "message": "Payment method deleted"}), 200
    except Exception as exc:
        logger.error("❌ delete_payment_method failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/opportunities", methods=["GET"])
@jwt_required
def list_opportunities():
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        business_unit_id = request.args.get("business_unit_id")
        sales_stage = request.args.get("sales_stage")
        data = budy_domain_service.list_opportunities(
            user_id,
            organization_id,
            business_unit_id=business_unit_id,
            sales_stage=sales_stage,
        )
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ list_opportunities failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/opportunities/<opportunity_id>", methods=["GET"])
@jwt_required
def get_opportunity(opportunity_id: str):
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        data = budy_domain_service.get_opportunity(user_id, organization_id, opportunity_id)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ get_opportunity failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/opportunities/<opportunity_id>", methods=["PATCH"])
@jwt_required
def update_opportunity(opportunity_id: str):
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        payload = request.get_json() or {}
        data = budy_domain_service.update_opportunity(user_id, organization_id, opportunity_id, payload)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ update_opportunity failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/proposals/<proposal_id>/publish", methods=["POST"])
@jwt_required
def publish_proposal(proposal_id: str):
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        payload = request.get_json() or {}
        data = budy_domain_service.publish_proposal(user_id, organization_id, proposal_id, payload)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ publish_proposal failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/public/proposals/<token>", methods=["GET"])
def get_public_proposal(token: str):
    try:
        data = budy_domain_service.get_public_proposal(token)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ get_public_proposal failed: %s", exc)
        return _json_error(str(exc), 404)


@bdy_bp.route("/public/proposals/<token>/accept", methods=["POST"])
def accept_public_proposal(token: str):
    try:
        payload = request.get_json() or {}
        data = budy_domain_service.accept_public_proposal(
            token,
            payload,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
        )
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ accept_public_proposal failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/public/proposals/<token>/payments", methods=["POST"])
def submit_public_payment(token: str):
    try:
        form_data = request.form.to_dict()
        proof_file = request.files.get("proof_file")
        data = budy_domain_service.submit_public_payment(token, form_data, proof_file)
        return jsonify({"status": "success", "data": data}), 201
    except Exception as exc:
        logger.error("❌ submit_public_payment failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/payments/<payment_id>/confirm", methods=["POST"])
@jwt_required
def confirm_payment(payment_id: str):
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        data = budy_domain_service.confirm_payment(user_id, organization_id, payment_id)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ confirm_payment failed: %s", exc)
        return _json_error(str(exc), 400)


@bdy_bp.route("/exchange-rates/bcv/current", methods=["GET"])
def get_bcv_rate():
    try:
        force_refresh = request.args.get("force_refresh", "false").lower() == "true"
        data = bcv_rate_service.get_current_rate(force_refresh=force_refresh, allow_stale=True)
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        logger.error("❌ get_bcv_rate failed: %s", exc)
        return _json_error(str(exc), 503)
