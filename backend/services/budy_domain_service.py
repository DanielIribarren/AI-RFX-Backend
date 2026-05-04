"""
Budy domain service.

Provides the business-unit, catalog, opportunity, publishing, and payment
operations used by the Budy Phase 1 experience.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
import mimetypes
import os
import secrets
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from backend.core.database import get_database_client, retry_on_connection_error
from backend.services.bcv_rate_service import bcv_rate_service
from backend.utils.rfx_ownership import get_and_validate_rfx_ownership

logger = logging.getLogger(__name__)

SALES_STAGES = {
    "draft",
    "sent",
    "viewed",
    "accepted",
    "payment_pending",
    "partially_paid",
    "confirmed",
    "in_execution",
    "completed",
    "cancelled",
}

VIRTUAL_BUSINESS_UNIT_PREFIX = "virtual-"


def is_virtual_business_unit_id(business_unit_id: Optional[str]) -> bool:
    # Virtual ids (e.g. "virtual-<org-id>") are placeholders returned when the
    # backend can't persist a real business_units row (RLS / no service_role).
    # They aren't UUIDs, so forwarding them to Postgres triggers 22P02.
    return bool(business_unit_id) and business_unit_id.startswith(VIRTUAL_BUSINESS_UNIT_PREFIX)


class BudyDomainService:
    """Business operations for the Budy workspace and public proposal flow."""

    def __init__(self) -> None:
        self.db = get_database_client()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def require_organization(self, organization_id: Optional[str]) -> str:
        if not organization_id:
            raise ValueError("Budy Phase 1 requires an organization context")
        return organization_id

    def _is_rls_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "row-level security" in message or "violates row-level security policy" in message

    def _build_virtual_default_business_unit(self, organization_id: str) -> Dict[str, Any]:
        organization = self.db.get_organization(organization_id) or {}
        name = organization.get("name", "Default Area")
        slug = organization.get("slug", "default-area")
        return {
            "id": f"virtual-{organization_id}",
            "organization_id": organization_id,
            "name": name,
            "slug": slug,
            "description": "Virtual default area generated because Budy configuration could not be persisted yet.",
            "industry_context": "services",
            "brand_name": name,
            "brand_tagline": None,
            "logo_url": None,
            "primary_color": None,
            "secondary_color": None,
            "accent_color": None,
            "support_email": None,
            "support_phone": None,
            "website_url": None,
            "is_default": True,
            "is_active": True,
            "metadata": {
                "virtual": True,
                "reason": "missing_service_role_or_rls_write_access",
            },
        }

    def _raise_write_access_error(self, entity_label: str, exc: Exception) -> None:
        if self._is_rls_error(exc):
            raise ValueError(
                f"No se pudo guardar {entity_label} porque el backend no tiene acceso service_role a Supabase."
            ) from exc
        raise exc

    @retry_on_connection_error()
    def ensure_default_business_unit(self, organization_id: str) -> Dict[str, Any]:
        existing = (
            self.db.client.table("business_units")
            .select("*")
            .eq("organization_id", organization_id)
            .order("is_default", desc=True)
            .order("created_at")
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]

        organization = self.db.get_organization(organization_id)
        name = organization.get("name", "Business Unit") if organization else "Business Unit"
        slug = organization.get("slug", "default-business-unit") if organization else "default-business-unit"
        payload = {
            "organization_id": organization_id,
            "name": name,
            "slug": slug,
            "description": "Default Budy business unit",
            "industry_context": "services",
            "brand_name": name,
            "is_default": True,
            "is_active": True,
        }
        try:
            created = self.db.client.table("business_units").insert(payload).execute()
            if not created.data:
                raise RuntimeError("Unable to create default business unit")
            return created.data[0]
        except Exception as exc:
            if self._is_rls_error(exc):
                logger.warning(
                    "⚠️ Falling back to virtual default business unit for org %s because insert was blocked by RLS",
                    organization_id,
                )
                return self._build_virtual_default_business_unit(organization_id)
            raise

    def _ensure_business_unit_access(self, organization_id: str, business_unit_id: str) -> Dict[str, Any]:
        if is_virtual_business_unit_id(business_unit_id):
            raise ValueError(
                "La organización no tiene una business unit persistida. "
                "Configure el service_role de Supabase para crear una antes de continuar."
            )
        response = (
            self.db.client.table("business_units")
            .select("*")
            .eq("id", business_unit_id)
            .eq("organization_id", organization_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise ValueError("Business unit not found")
        return response.data[0]

    def _ownership_error_message(self, error: Any) -> str:
        if not error:
            return "Access denied"
        response = error[0] if isinstance(error, tuple) else error
        try:
            payload = response.get_json(silent=True) if hasattr(response, "get_json") else None
            if isinstance(payload, dict) and payload.get("message"):
                return str(payload["message"])
        except Exception:
            pass
        return "Access denied"

    def _owner_filter(self, query, user_id: str, organization_id: Optional[str]):
        if organization_id:
            return query.eq("organization_id", organization_id)
        return query.eq("user_id", user_id).is_("organization_id", "null")

    def _get_latest_proposal_for_rfx(self, rfx_id: str) -> Optional[Dict[str, Any]]:
        proposals = self.db.get_proposals_by_rfx_id(rfx_id)
        return proposals[0] if proposals else None

    def _get_active_payment_methods(self, business_unit_id: Optional[str]) -> List[Dict[str, Any]]:
        if not business_unit_id:
            return []
        response = (
            self.db.client.table("payment_methods")
            .select("*")
            .eq("business_unit_id", business_unit_id)
            .eq("is_active", True)
            .order("sort_order")
            .order("created_at")
            .execute()
        )
        return response.data or []

    def list_payment_methods(self, organization_id: str, business_unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if is_virtual_business_unit_id(business_unit_id):
            business_unit_id = None
        query = (
            self.db.client.table("payment_methods")
            .select("*, business_units(id, name, slug)")
            .eq("organization_id", organization_id)
            .order("business_unit_id")
            .order("sort_order")
            .order("created_at")
        )
        if business_unit_id:
            query = query.eq("business_unit_id", business_unit_id)
        response = query.execute()
        return response.data or []

    def create_payment_method(self, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        business_unit_id = payload.get("business_unit_id")
        if not business_unit_id:
            business_unit_id = self.ensure_default_business_unit(organization_id)["id"]
        self._ensure_business_unit_access(organization_id, business_unit_id)
        method_type = payload.get("method_type")
        display_name = (payload.get("display_name") or "").strip()
        if not method_type or not display_name:
            raise ValueError("method_type and display_name are required")
        create_payload = {
            "organization_id": organization_id,
            "business_unit_id": business_unit_id,
            "method_type": method_type,
            "display_name": display_name,
            "account_holder": payload.get("account_holder"),
            "bank_name": payload.get("bank_name"),
            "phone": payload.get("phone"),
            "national_id": payload.get("national_id"),
            "email": payload.get("email"),
            "account_number": payload.get("account_number"),
            "instructions": payload.get("instructions"),
            "sort_order": int(payload.get("sort_order") or 0),
            "is_active": bool(payload.get("is_active", True)),
            "metadata": payload.get("metadata") or {},
        }
        try:
            response = self.db.client.table("payment_methods").insert(create_payload).execute()
            if not response.data:
                raise RuntimeError("Failed to create payment method")
            return response.data[0]
        except Exception as exc:
            self._raise_write_access_error("la configuracion de cobro", exc)

    def update_payment_method(self, organization_id: str, payment_method_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = (
            self.db.client.table("payment_methods")
            .select("*")
            .eq("id", payment_method_id)
            .eq("organization_id", organization_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            raise ValueError("Payment method not found")
        update_payload = {
            key: value
            for key, value in payload.items()
            if key
            in {
                "business_unit_id",
                "method_type",
                "display_name",
                "account_holder",
                "bank_name",
                "phone",
                "national_id",
                "email",
                "account_number",
                "instructions",
                "sort_order",
                "is_active",
                "metadata",
            }
        }
        if "business_unit_id" in update_payload:
            self._ensure_business_unit_access(organization_id, update_payload["business_unit_id"])
        try:
            response = self.db.client.table("payment_methods").update(update_payload).eq("id", payment_method_id).execute()
            if not response.data:
                raise RuntimeError("Failed to update payment method")
            return response.data[0]
        except Exception as exc:
            self._raise_write_access_error("la configuracion de cobro", exc)

    def delete_payment_method(self, organization_id: str, payment_method_id: str) -> None:
        try:
            response = (
                self.db.client.table("payment_methods")
                .delete()
                .eq("id", payment_method_id)
                .eq("organization_id", organization_id)
                .execute()
            )
            if not response.data:
                raise ValueError("Payment method not found")
        except Exception as exc:
            self._raise_write_access_error("la configuracion de cobro", exc)

    def _get_acceptance(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.db.client.table("proposal_acceptances")
            .select("*")
            .eq("proposal_id", proposal_id)
            .order("accepted_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def _normalize_public_file_url(self, url: Optional[str]) -> Optional[str]:
        if not isinstance(url, str):
            return url
        return url.rstrip("?")

    def _resolve_payment_proof_url(self, url: Optional[str]) -> Optional[str]:
        normalized_url = self._normalize_public_file_url(url)
        if not normalized_url:
            return normalized_url

        file_path = self.db.extract_storage_path_from_url("payment-proofs", normalized_url)
        if not file_path:
            return normalized_url

        try:
            return self.db.create_signed_storage_url("payment-proofs", file_path)
        except Exception:
            logger.warning("⚠️ Falling back to stored proof URL because signed URL generation failed")
            return normalized_url

    def _get_payment_submissions(self, proposal_id: str) -> List[Dict[str, Any]]:
        response = (
            self.db.client.table("payment_submissions")
            .select("*, payment_methods(*)")
            .eq("proposal_id", proposal_id)
            .order("submitted_at", desc=False)
            .execute()
        )
        payments = response.data or []
        for payment in payments:
            payment["proof_file_url"] = self._resolve_payment_proof_url(payment.get("proof_file_url"))
        return payments

    def _calculate_payment_summary(self, proposal: Dict[str, Any], payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_usd = float(
            ((proposal.get("pricing_snapshot") or {}).get("reference_total_usd"))
            or proposal.get("total_cost")
            or 0
        )
        confirmed = 0.0
        submitted = 0.0
        for payment in payments:
            amount = float(payment.get("amount_usd") or 0)
            if payment.get("status") == "confirmed":
                confirmed += amount
            elif payment.get("status") == "submitted":
                submitted += amount

        remaining = max(total_usd - confirmed, 0)
        return {
            "contract_total_usd": round(total_usd, 2),
            "confirmed_total_usd": round(confirmed, 2),
            "submitted_total_usd": round(submitted, 2),
            "remaining_total_usd": round(remaining, 2),
            "is_fully_paid": remaining <= 0.01 and total_usd > 0,
        }

    def _build_missing_line_items_message(self, items: List[str], label: str) -> Optional[str]:
        if not items:
            return None
        preview = ", ".join(items[:3])
        if len(items) > 3:
            preview = f"{preview} and {len(items) - 3} more"
        return f"Add a {label} for: {preview}."

    def _proposal_readiness_issues(
        self,
        rfx: Dict[str, Any],
        latest_proposal: Optional[Dict[str, Any]],
        products: List[Dict[str, Any]],
    ) -> List[str]:
        issues: List[str] = []

        title = str(rfx.get("title") or "").strip()
        if not title:
            issues.append("Add a title in Data View.")

        company = rfx.get("companies") or {}
        client_name = str(company.get("name") or "").strip()
        if not client_name:
            issues.append("Add the client name in Data View.")

        if not products:
            issues.append("Add at least one product or service line in Data View.")
        else:
            missing_prices: List[str] = []
            missing_costs: List[str] = []
            for product in products:
                product_name = str(
                    product.get("product_name")
                    or product.get("nombre")
                    or product.get("name")
                    or "Unnamed line"
                ).strip() or "Unnamed line"

                unit_price = float(
                    product.get("estimated_unit_price")
                    or product.get("precio_unitario")
                    or product.get("unit_price")
                    or 0
                )
                unit_cost = float(
                    product.get("unit_cost")
                    or product.get("costo_unitario")
                    or 0
                )

                if unit_price <= 0:
                    missing_prices.append(product_name)
                if unit_cost <= 0:
                    missing_costs.append(product_name)

            price_issue = self._build_missing_line_items_message(missing_prices, "unit price")
            if price_issue:
                issues.append(price_issue)

            cost_issue = self._build_missing_line_items_message(missing_costs, "unit cost")
            if cost_issue:
                issues.append(cost_issue)

        if not latest_proposal:
            issues.append("Generate the proposal draft from Budget before publishing.")
        else:
            contract_total_usd = float(latest_proposal.get("total_cost") or 0)
            if contract_total_usd <= 0:
                issues.append("Configure pricing so the proposal total is greater than $0.")

        return issues

    def _map_rfx_to_opportunity(self, rfx: Dict[str, Any], latest_proposal: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        company = rfx.get("companies") or {}
        requester = rfx.get("requesters") or {}
        proposal_metadata = (latest_proposal or {}).get("metadata") or {}
        return {
            "id": rfx.get("id"),
            "title": rfx.get("title"),
            "sales_stage": rfx.get("sales_stage") or "draft",
            "origin_channel": rfx.get("origin_channel") or "document_upload",
            "industry_context": rfx.get("industry_context") or rfx.get("rfx_type") or "services",
            "business_unit_id": rfx.get("business_unit_id"),
            "client": {
                "id": company.get("id"),
                "name": company.get("name") or "",
                "email": company.get("email"),
                "industry": company.get("industry"),
            },
            "contact": {
                "id": requester.get("id"),
                "name": requester.get("name"),
                "email": requester.get("email"),
                "phone": requester.get("phone"),
            },
            "proposal": {
                "id": latest_proposal.get("id") if latest_proposal else None,
                "proposal_code": proposal_metadata.get("proposal_code") if latest_proposal else None,
                "public_token": latest_proposal.get("public_token") if latest_proposal else None,
                "public_visibility": latest_proposal.get("public_visibility") if latest_proposal else None,
                "commercial_status": proposal_metadata.get("commercial_status", "generated") if latest_proposal else None,
                "sent_at": proposal_metadata.get("sent_at") if latest_proposal else None,
                "accepted_at": proposal_metadata.get("accepted_at") if latest_proposal else None,
                "total_cost": float(latest_proposal.get("total_cost") or 0) if latest_proposal else 0,
                "public_view_count": int(latest_proposal.get("public_view_count") or 0) if latest_proposal else 0,
                "public_last_viewed_at": latest_proposal.get("public_last_viewed_at") if latest_proposal else None,
            },
            "service": {
                "service_start_at": rfx.get("service_start_at"),
                "service_end_at": rfx.get("service_end_at"),
                "service_location": rfx.get("service_location") or rfx.get("event_location"),
            },
            "created_at": rfx.get("created_at"),
            "updated_at": rfx.get("updated_at"),
        }

    def _update_rfx_sales_stage(self, rfx_id: str, stage: str, extra_updates: Optional[Dict[str, Any]] = None) -> None:
        if stage not in SALES_STAGES:
            raise ValueError(f"Invalid sales stage: {stage}")
        payload: Dict[str, Any] = {"sales_stage": stage}
        if extra_updates:
            payload.update(extra_updates)
        self.db.client.table("rfx_v2").update(payload).eq("id", rfx_id).execute()

    def _proposal_metadata(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        metadata = proposal.get("metadata") or {}
        return metadata if isinstance(metadata, dict) else {}

    def _set_proposal_metadata(self, proposal_id: str, updates: Dict[str, Any], extra_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        proposal = self.db.get_document_by_id(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        metadata = self._proposal_metadata(proposal)
        metadata.update(updates)
        payload = {"metadata": metadata}
        if extra_fields:
            payload.update(extra_fields)
        response = self.db.client.table("generated_documents").update(payload).eq("id", proposal_id).execute()
        if not response.data:
            raise RuntimeError("Failed to update proposal")
        return response.data[0]

    # ------------------------------------------------------------------
    # Business units
    # ------------------------------------------------------------------
    @retry_on_connection_error()
    def list_business_units(self, organization_id: str) -> List[Dict[str, Any]]:
        default_unit = self.ensure_default_business_unit(organization_id)
        response = (
            self.db.client.table("business_units")
            .select("*")
            .eq("organization_id", organization_id)
            .order("is_default", desc=True)
            .order("name")
            .execute()
        )
        units = response.data or []
        if units:
            return units
        return [default_unit]

    def create_business_unit(self, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        name = (payload.get("name") or "").strip()
        slug = (payload.get("slug") or "").strip()
        if not name:
            raise ValueError("Business unit name is required")
        if not slug:
            slug = "-".join(name.lower().split())
        create_payload = {
            "organization_id": organization_id,
            "name": name,
            "slug": slug,
            "description": payload.get("description"),
            "industry_context": payload.get("industry_context") or "services",
            "brand_name": payload.get("brand_name") or name,
            "brand_tagline": payload.get("brand_tagline"),
            "logo_url": payload.get("logo_url"),
            "primary_color": payload.get("primary_color"),
            "secondary_color": payload.get("secondary_color"),
            "accent_color": payload.get("accent_color"),
            "support_email": payload.get("support_email"),
            "support_phone": payload.get("support_phone"),
            "website_url": payload.get("website_url"),
            "is_default": bool(payload.get("is_default", False)),
            "is_active": bool(payload.get("is_active", True)),
            "metadata": payload.get("metadata") or {},
        }
        try:
            if create_payload["is_default"]:
                self.db.client.table("business_units").update({"is_default": False}).eq("organization_id", organization_id).execute()
            response = self.db.client.table("business_units").insert(create_payload).execute()
            if not response.data:
                raise RuntimeError("Failed to create business unit")
            return response.data[0]
        except Exception as exc:
            if self._is_rls_error(exc):
                raise ValueError(
                    "No se pudo guardar el area de negocio porque el backend no tiene acceso service_role a Supabase."
                ) from exc
            raise

    def update_business_unit(self, organization_id: str, business_unit_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_business_unit_access(organization_id, business_unit_id)
        allowed = {
            "name",
            "slug",
            "description",
            "industry_context",
            "brand_name",
            "brand_tagline",
            "logo_url",
            "primary_color",
            "secondary_color",
            "accent_color",
            "support_email",
            "support_phone",
            "website_url",
            "is_default",
            "is_active",
            "metadata",
        }
        update_payload = {key: value for key, value in payload.items() if key in allowed}
        if "is_default" in update_payload and update_payload["is_default"]:
            self.db.client.table("business_units").update({"is_default": False}).eq("organization_id", organization_id).execute()
        response = self.db.client.table("business_units").update(update_payload).eq("id", business_unit_id).execute()
        if not response.data:
            raise RuntimeError("Failed to update business unit")
        return response.data[0]

    # ------------------------------------------------------------------
    # Catalog items
    # ------------------------------------------------------------------
    def list_catalog_items(self, organization_id: str, business_unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if is_virtual_business_unit_id(business_unit_id):
            business_unit_id = None
        query = (
            self.db.client.table("catalog_items")
            .select("*, business_units(id, name, slug, industry_context)")
            .eq("organization_id", organization_id)
            .order("category")
            .order("name")
        )
        if business_unit_id:
            query = query.eq("business_unit_id", business_unit_id)
        response = query.execute()
        return response.data or []

    def create_catalog_item(self, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        business_unit_id = payload.get("business_unit_id")
        if not business_unit_id:
            business_unit_id = self.ensure_default_business_unit(organization_id)["id"]
        self._ensure_business_unit_access(organization_id, business_unit_id)
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Catalog item name is required")
        create_payload = {
            "organization_id": organization_id,
            "business_unit_id": business_unit_id,
            "name": name,
            "description": payload.get("description"),
            "category": payload.get("category"),
            "unit": payload.get("unit") or "servicio",
            "pricing_model": payload.get("pricing_model") or "fixed_price",
            "base_price_usd": float(payload.get("base_price_usd") or 0),
            "is_active": bool(payload.get("is_active", True)),
            "metadata": payload.get("metadata") or {},
        }
        try:
            response = self.db.client.table("catalog_items").insert(create_payload).execute()
            if not response.data:
                raise RuntimeError("Failed to create catalog item")
            return response.data[0]
        except Exception as exc:
            self._raise_write_access_error("el item del catalogo", exc)

    def update_catalog_item(self, organization_id: str, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = (
            self.db.client.table("catalog_items")
            .select("*")
            .eq("id", item_id)
            .eq("organization_id", organization_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            raise ValueError("Catalog item not found")
        update_payload = {
            key: value
            for key, value in payload.items()
            if key in {"name", "description", "category", "unit", "pricing_model", "base_price_usd", "is_active", "metadata", "business_unit_id"}
        }
        if "business_unit_id" in update_payload:
            self._ensure_business_unit_access(organization_id, update_payload["business_unit_id"])
        try:
            response = self.db.client.table("catalog_items").update(update_payload).eq("id", item_id).execute()
            if not response.data:
                raise RuntimeError("Failed to update catalog item")
            return response.data[0]
        except Exception as exc:
            self._raise_write_access_error("el item del catalogo", exc)

    def delete_catalog_item(self, organization_id: str, item_id: str) -> None:
        try:
            response = (
                self.db.client.table("catalog_items")
                .delete()
                .eq("id", item_id)
                .eq("organization_id", organization_id)
                .execute()
            )
            if not response.data:
                raise ValueError("Catalog item not found")
        except Exception as exc:
            self._raise_write_access_error("el item del catalogo", exc)

    # ------------------------------------------------------------------
    # Clients and opportunities
    # ------------------------------------------------------------------
    def list_clients(self, user_id: str, organization_id: Optional[str], search: str = "") -> List[Dict[str, Any]]:
        records = self.db.get_rfx_history(user_id=user_id, organization_id=organization_id, limit=200, offset=0)
        grouped: Dict[str, Dict[str, Any]] = {}
        for record in records:
            company = record.get("companies") or {}
            requester = record.get("requesters") or {}
            company_id = company.get("id") or f"company:{company.get('name', 'unknown')}"
            if search and search.lower() not in f"{company.get('name', '')} {requester.get('name', '')}".lower():
                continue
            current = grouped.setdefault(
                company_id,
                {
                    "id": company.get("id"),
                    "name": company.get("name") or "Cliente",
                    "email": company.get("email"),
                    "phone": company.get("phone"),
                    "industry": company.get("industry"),
                    "contacts": [],
                    "opportunities_count": 0,
                    "last_activity_at": record.get("updated_at") or record.get("created_at"),
                },
            )
            current["opportunities_count"] += 1
            if requester.get("id") and all(contact["id"] != requester.get("id") for contact in current["contacts"]):
                current["contacts"].append(
                    {
                        "id": requester.get("id"),
                        "name": requester.get("name"),
                        "email": requester.get("email"),
                        "phone": requester.get("phone"),
                        "position": requester.get("position"),
                    }
                )
            record_activity = record.get("updated_at") or record.get("created_at")
            if record_activity and (not current["last_activity_at"] or record_activity > current["last_activity_at"]):
                current["last_activity_at"] = record_activity
        return sorted(grouped.values(), key=lambda item: item.get("last_activity_at") or "", reverse=True)

    def create_client(self, user_id: str, organization_id: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = (payload.get("company_name") or payload.get("name") or "").strip()
        contact_name = (payload.get("contact_name") or "").strip()
        if not company_name:
            raise ValueError("company_name is required")
        company_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "organization_id": organization_id,
            "name": company_name,
            "email": payload.get("company_email"),
            "phone": payload.get("company_phone"),
            "industry": payload.get("industry"),
            "address": payload.get("address"),
        }
        company = self.db.insert_company(company_data)
        requester = None
        if contact_name:
            requester = self.db.insert_requester(
                {
                    "id": str(uuid4()),
                    "organization_id": organization_id,
                    "company_id": company["id"],
                    "name": contact_name,
                    "email": payload.get("contact_email") or payload.get("company_email") or f"{company['id']}@placeholder.local",
                    "phone": payload.get("contact_phone"),
                    "position": payload.get("position"),
                    "is_primary_contact": True,
                }
            )
        return {"company": company, "contact": requester}

    def _batch_latest_proposals(self, rfx_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not rfx_ids:
            return {}
        response = (
            self.db.client.table("generated_documents")
            .select("*")
            .in_("rfx_id", rfx_ids)
            .eq("document_type", "proposal")
            .order("created_at", desc=True)
            .execute()
        )
        latest: Dict[str, Dict[str, Any]] = {}
        for doc in response.data or []:
            rfx_id = str(doc.get("rfx_id") or "")
            if rfx_id and rfx_id not in latest:
                latest[rfx_id] = doc
        return latest

    def list_opportunities(
        self,
        user_id: str,
        organization_id: Optional[str],
        *,
        business_unit_id: Optional[str] = None,
        sales_stage: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if is_virtual_business_unit_id(business_unit_id):
            business_unit_id = None
        records = self.db.get_rfx_history(
            user_id=user_id,
            organization_id=organization_id,
            limit=1000,
            offset=0,
            business_unit_id=business_unit_id,
            sales_stage=sales_stage,
        )
        rfx_ids = [str(r["id"]) for r in records if r.get("id")]
        proposals_by_rfx = self._batch_latest_proposals(rfx_ids)
        return [
            self._map_rfx_to_opportunity(record, proposals_by_rfx.get(str(record["id"])))
            for record in records
        ]

    def get_opportunity(self, user_id: str, organization_id: Optional[str], rfx_id: str) -> Dict[str, Any]:
        rfx, error = get_and_validate_rfx_ownership(self.db, rfx_id, user_id, organization_id)
        if error:
            raise ValueError(self._ownership_error_message(error))
        latest_proposal = self._get_latest_proposal_for_rfx(rfx_id)
        products = self.db.get_rfx_products(rfx_id)
        payments = self._get_payment_submissions(latest_proposal["id"]) if latest_proposal else []
        payment_summary = self._calculate_payment_summary(latest_proposal or {}, payments) if latest_proposal else None
        proposal_readiness_issues = self._proposal_readiness_issues(rfx, latest_proposal, products)
        return {
            **self._map_rfx_to_opportunity(rfx, latest_proposal),
            "description": rfx.get("description"),
            "requirements": rfx.get("requirements"),
            "products": products,
            "payments": payments,
            "payment_summary": payment_summary,
            "proposal_readiness_issues": proposal_readiness_issues,
            "can_publish_proposal": len(proposal_readiness_issues) == 0,
        }

    def update_opportunity(self, user_id: str, organization_id: Optional[str], rfx_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        rfx, error = get_and_validate_rfx_ownership(self.db, rfx_id, user_id, organization_id)
        if error:
            raise ValueError(self._ownership_error_message(error))

        update_payload = {}
        if "sales_stage" in payload:
            sales_stage = payload["sales_stage"]
            if sales_stage not in SALES_STAGES:
                raise ValueError("Invalid sales stage")
            update_payload["sales_stage"] = sales_stage
        if "origin_channel" in payload:
            update_payload["origin_channel"] = payload["origin_channel"]
        if "industry_context" in payload:
            update_payload["industry_context"] = payload["industry_context"]
        if "service_start_at" in payload:
            update_payload["service_start_at"] = payload["service_start_at"]
        if "service_end_at" in payload:
            update_payload["service_end_at"] = payload["service_end_at"]
        if "service_location" in payload:
            update_payload["service_location"] = payload["service_location"]
        if "business_unit_id" in payload and payload["business_unit_id"]:
            if not organization_id:
                raise ValueError("Business units require an organization")
            business_unit = self._ensure_business_unit_access(organization_id, payload["business_unit_id"])
            update_payload["business_unit_id"] = business_unit["id"]
            update_payload["industry_context"] = payload.get("industry_context") or business_unit.get("industry_context")

        if not update_payload:
            return self.get_opportunity(user_id, organization_id, rfx_id)

        self.db.client.table("rfx_v2").update(update_payload).eq("id", rfx_id).execute()
        return self.get_opportunity(user_id, organization_id, rfx_id)

    # ------------------------------------------------------------------
    # Proposal publishing and public flow
    # ------------------------------------------------------------------
    def publish_proposal(
        self,
        user_id: str,
        organization_id: Optional[str],
        proposal_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        proposal = self.db.get_document_by_id(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        rfx_id = str(proposal.get("rfx_id"))
        rfx, error = get_and_validate_rfx_ownership(self.db, rfx_id, user_id, organization_id)
        if error:
            raise ValueError(self._ownership_error_message(error))

        business_unit_id = payload.get("business_unit_id") or rfx.get("business_unit_id")
        if organization_id:
            if business_unit_id:
                business_unit = self._ensure_business_unit_access(organization_id, business_unit_id)
            else:
                business_unit = self.ensure_default_business_unit(organization_id)
                business_unit_id = business_unit["id"]
        else:
            business_unit = None

        products = self.db.get_rfx_products(rfx_id)
        readiness_issues = self._proposal_readiness_issues(rfx, proposal, products)
        if readiness_issues:
            raise ValueError(f"This proposal cannot be published yet. {' '.join(readiness_issues)}")

        rate_snapshot = bcv_rate_service.get_current_rate(allow_stale=True)
        contract_total_usd = float(proposal.get("total_cost") or 0)
        pricing_snapshot = {
            "contract_currency": "USD",
            "reference_total_usd": contract_total_usd,
            "published_rate": rate_snapshot["rate"],
            "published_rate_fetched_at": rate_snapshot.get("fetched_at"),
            "published_rate_is_stale": rate_snapshot.get("is_stale", False),
        }
        public_token = proposal.get("public_token") or secrets.token_urlsafe(24)
        updated_proposal = self._set_proposal_metadata(
            proposal_id,
            {
                "commercial_status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "business_unit_id": business_unit_id,
                "public_token": public_token,
                "public_visibility": "public",
                "public_published_at": datetime.now(timezone.utc).isoformat(),
                "pricing_snapshot": pricing_snapshot,
            },
        )

        extra_updates = {"business_unit_id": business_unit_id} if business_unit_id else {}
        if business_unit and not rfx.get("industry_context"):
            extra_updates["industry_context"] = business_unit.get("industry_context")
        self._update_rfx_sales_stage(rfx_id, "sent", extra_updates=extra_updates)

        return {
            "proposal_id": proposal_id,
            "public_token": public_token,
            "public_url": f"/p/{public_token}",
            "pricing_snapshot": pricing_snapshot,
            "proposal": updated_proposal,
        }

    def get_public_proposal(self, token: str) -> Dict[str, Any]:
        response = (
            self.db.client.table("generated_documents")
            .select("*")
            .eq("public_token", token)
            .eq("document_type", "proposal")
            .eq("public_visibility", "public")
            .limit(1)
            .execute()
        )
        if not response.data:
            raise ValueError("Public proposal not found")

        proposal = response.data[0]
        rfx = self.db.get_rfx_by_id(proposal["rfx_id"])
        if not rfx:
            raise ValueError("Associated opportunity not found")
        business_unit = None
        if proposal.get("business_unit_id") or rfx.get("business_unit_id"):
            unit_id = proposal.get("business_unit_id") or rfx.get("business_unit_id")
            unit_response = self.db.client.table("business_units").select("*").eq("id", unit_id).limit(1).execute()
            business_unit = unit_response.data[0] if unit_response.data else None

        rate_snapshot = bcv_rate_service.get_current_rate(allow_stale=True)
        payment_methods = self._get_active_payment_methods((business_unit or {}).get("id"))
        acceptance = self._get_acceptance(proposal["id"])
        payments = self._get_payment_submissions(proposal["id"])
        payment_summary = self._calculate_payment_summary(proposal, payments)
        contract_total_usd = payment_summary["contract_total_usd"]
        equivalent_ves = bcv_rate_service.convert_usd_to_ves(contract_total_usd, rate_snapshot)

        try:
            next_view_count = int(proposal.get("public_view_count") or 0) + 1
            self.db.client.table("generated_documents").update(
                {
                    "public_view_count": next_view_count,
                    "public_last_viewed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", proposal["id"]).execute()
            current_stage = rfx.get("sales_stage") or "draft"
            if current_stage in {"draft", "sent"}:
                self._update_rfx_sales_stage(str(rfx["id"]), "viewed")
        except Exception as exc:
            logger.warning("⚠️ Failed to update public view tracking: %s", exc)

        return {
            "proposal": proposal,
            "opportunity": {
                "id": rfx.get("id"),
                "title": rfx.get("title"),
                "description": rfx.get("description"),
                "requirements": rfx.get("requirements"),
                "sales_stage": rfx.get("sales_stage"),
                "client": rfx.get("companies") or {},
                "contact": rfx.get("requesters") or {},
                "service_start_at": rfx.get("service_start_at"),
                "service_end_at": rfx.get("service_end_at"),
                "service_location": rfx.get("service_location") or rfx.get("event_location"),
            },
            "business_unit": business_unit,
            "payment_methods": payment_methods,
            "acceptance": acceptance,
            "payments": payments,
            "payment_summary": payment_summary,
            "exchange_rate": rate_snapshot,
            "pricing": {
                "contract_total_usd": contract_total_usd,
                "equivalent_total_ves": equivalent_ves,
                "display_note": "El precio en USD es la referencia contractual. El equivalente en VES usa tasa BCV al momento de abrir la propuesta.",
            },
        }

    def accept_public_proposal(self, token: str, payload: Dict[str, Any], *, ip_address: Optional[str], user_agent: Optional[str]) -> Dict[str, Any]:
        public_data = self.get_public_proposal(token)
        proposal = public_data["proposal"]
        existing = self._get_acceptance(proposal["id"])
        if existing:
            return {"acceptance": existing, "payment_methods": public_data["payment_methods"]}

        accepted_name = (payload.get("accepted_name") or payload.get("name") or "").strip()
        if not accepted_name:
            raise ValueError("accepted_name is required")
        acceptance_payload = {
            "proposal_id": proposal["id"],
            "rfx_id": proposal["rfx_id"],
            "business_unit_id": (public_data.get("business_unit") or {}).get("id"),
            "accepted_name": accepted_name,
            "accepted_email": payload.get("accepted_email"),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": {"source": "public_proposal_acceptance"},
        }
        response = self.db.client.table("proposal_acceptances").insert(acceptance_payload).execute()
        if not response.data:
            raise RuntimeError("Failed to store proposal acceptance")

        self._set_proposal_metadata(
            proposal["id"],
            {
                "commercial_status": "accepted",
                "accepted_at": acceptance_payload["accepted_at"],
            },
        )
        self._update_rfx_sales_stage(str(proposal["rfx_id"]), "payment_pending")
        return {"acceptance": response.data[0], "payment_methods": public_data["payment_methods"]}

    def submit_public_payment(
        self,
        token: str,
        form_data: Dict[str, Any],
        proof_file: Any,
    ) -> Dict[str, Any]:
        public_data = self.get_public_proposal(token)
        proposal = public_data["proposal"]
        acceptance = self._get_acceptance(proposal["id"])
        if not acceptance:
            raise ValueError("Proposal must be accepted before uploading a payment proof")

        payment_method_id = form_data.get("payment_method_id")
        payment_methods = public_data["payment_methods"]
        if not any(str(method["id"]) == str(payment_method_id) for method in payment_methods):
            raise ValueError("Invalid payment_method_id")

        amount_usd = float(form_data.get("amount_usd") or 0)
        amount_ves = float(form_data.get("amount_ves") or 0) if form_data.get("amount_ves") else None
        if amount_usd <= 0 and not amount_ves:
            raise ValueError("A positive payment amount is required")

        rate_snapshot = bcv_rate_service.get_current_rate(allow_stale=True)
        if amount_usd <= 0 and amount_ves:
            amount_usd = round(amount_ves / float(rate_snapshot["rate"]), 2)
        if amount_ves is None:
            amount_ves = bcv_rate_service.convert_usd_to_ves(amount_usd, rate_snapshot)

        proof_url = None
        if proof_file and getattr(proof_file, "filename", ""):
            file_bytes = proof_file.read()
            if not file_bytes:
                raise ValueError("Uploaded proof file is empty")
            ext = os.path.splitext(proof_file.filename)[1] or ".bin"
            mime_type = proof_file.mimetype or mimetypes.guess_type(proof_file.filename)[0] or "application/octet-stream"
            file_path = f"{proposal['id']}/{uuid4().hex}{ext}"
            proof_url = self.db.upload_file_to_storage("payment-proofs", file_path, file_bytes, content_type=mime_type)

        payment_payload = {
            "proposal_id": proposal["id"],
            "rfx_id": proposal["rfx_id"],
            "business_unit_id": (public_data.get("business_unit") or {}).get("id"),
            "payment_method_id": payment_method_id,
            "acceptance_id": acceptance["id"],
            "payer_name": form_data.get("payer_name"),
            "payer_email": form_data.get("payer_email"),
            "payment_reference": form_data.get("payment_reference"),
            "amount_usd": amount_usd,
            "amount_ves": amount_ves,
            "exchange_rate": rate_snapshot["rate"],
            "proof_file_url": proof_url,
            "notes": form_data.get("notes"),
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"rate_is_stale": rate_snapshot.get("is_stale", False)},
        }
        response = self.db.client.table("payment_submissions").insert(payment_payload).execute()
        if not response.data:
            raise RuntimeError("Failed to create payment submission")
        self._update_rfx_sales_stage(str(proposal["rfx_id"]), "payment_pending")
        return response.data[0]

    def confirm_payment(self, user_id: str, organization_id: Optional[str], payment_id: str) -> Dict[str, Any]:
        response = (
            self.db.client.table("payment_submissions")
            .select("*, generated_documents(*)")
            .eq("id", payment_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise ValueError("Payment submission not found")
        payment = response.data[0]
        proposal = payment.get("generated_documents") or self.db.get_document_by_id(payment["proposal_id"])
        rfx_id = str(payment["rfx_id"])
        _, error = get_and_validate_rfx_ownership(self.db, rfx_id, user_id, organization_id)
        if error:
            raise ValueError(self._ownership_error_message(error))

        try:
            updated_response = (
                self.db.client.table("payment_submissions")
                .update(
                    {
                        "status": "confirmed",
                        "confirmed_at": datetime.now(timezone.utc).isoformat(),
                        "confirmed_by": user_id,
                    }
                )
                .eq("id", payment_id)
                .execute()
            )
        except Exception as exc:
            self._raise_write_access_error("la confirmacion del pago", exc)
        updated_payment = updated_response.data[0] if updated_response.data else payment
        payments = self._get_payment_submissions(payment["proposal_id"])
        summary = self._calculate_payment_summary(proposal, payments)
        next_stage = "confirmed" if summary["is_fully_paid"] else "partially_paid"
        self._update_rfx_sales_stage(rfx_id, next_stage)

        service_order = None
        if summary["is_fully_paid"]:
            existing_order = (
                self.db.client.table("service_orders")
                .select("*")
                .eq("rfx_id", rfx_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if existing_order.data:
                service_order = existing_order.data[0]
            else:
                rfx = self.db.get_rfx_by_id(rfx_id)
                order_payload = {
                    "rfx_id": rfx_id,
                    "proposal_id": payment["proposal_id"],
                    "business_unit_id": payment.get("business_unit_id") or (rfx or {}).get("business_unit_id"),
                    "status": "scheduled",
                    "service_start_at": (rfx or {}).get("service_start_at"),
                    "service_end_at": (rfx or {}).get("service_end_at"),
                    "service_location": (rfx or {}).get("service_location") or (rfx or {}).get("event_location"),
                    "created_by": user_id,
                    "notes": "Service order created automatically after full payment confirmation",
                }
                try:
                    order_response = self.db.client.table("service_orders").insert(order_payload).execute()
                    service_order = order_response.data[0] if order_response.data else None
                except Exception as exc:
                    self._raise_write_access_error("la orden de servicio", exc)

        return {
            "payment": updated_payment,
            "payment_summary": summary,
            "service_order": service_order,
            "next_sales_stage": next_stage,
        }


budy_domain_service = BudyDomainService()
