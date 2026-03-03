"""
Tool: update_product_tool

Propósito: Actualizar producto existente del request
Wrapper de: DatabaseClient.update_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import Dict, Any
import logging
import json

from backend.core.database import get_database_client
from backend.services.catalog_helpers import get_catalog_search_service_for_rfx
from backend.services.product_resolution_service import ProductResolutionService
from backend.services.rfx_processing_session_service import RFXProcessingSessionService

logger = logging.getLogger(__name__)


def _to_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


@tool
def update_product_tool(request_id: str, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza un producto existente del request.
    
    Esta tool permite al agente modificar campos de un producto específico.
    
    Args:
        request_id: ID del request (rfx_id)
        product_id: ID del producto a actualizar
        updates: Diccionario con campos a actualizar:
            - name (str, opcional): Nuevo nombre
            - quantity (int, opcional): Nueva cantidad
            - price_unit (float, opcional): Nuevo precio unitario
            - category (str, opcional): Nueva categoría
            - unit (str, opcional): Nueva unidad de medida
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "product_id": str,
            "updated_fields": List[str],
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Cambia la cantidad de sillas a 20"
        Agente: Primero obtiene el product_id y luego llama a esta tool
        
        Usuario: "Actualiza el precio de las mesas a $350"
        Agente: Primero obtiene el product_id y luego llama a esta tool
    """
    
    try:
        logger.info(f"🔧 update_product_tool called: request_id={request_id}, product_id={product_id}, updates={updates}")
        
        if not updates or len(updates) == 0:
            logger.warning("⚠️ No updates provided")
            return {
                "status": "error",
                "product_id": product_id,
                "updated_fields": [],
                "message": "No se proporcionaron campos para actualizar"
            }
        
        db = get_database_client()
        session_service = RFXProcessingSessionService()
        session = session_service.get_session(request_id)
        explicit_specs_update = _to_dict(updates.get("specifications"))
        explicit_breakdown_update = updates.get("bundle_breakdown")

        rfx_record = {}
        if session:
            preview_data = session.get("preview_data") or {}
            validated_data = session.get("validated_data") or {}
            organization_id = session.get("organization_id")
            source_text = str(preview_data.get("source_text") or "")
            existing_products = list(preview_data.get("products") or [])
            rfx_record = {
                "rfx_type": preview_data.get("rfx_type"),
                "location": preview_data.get("location"),
                "delivery_date": preview_data.get("delivery_date"),
            }
        else:
            rfx_record = db.get_rfx_by_id(request_id) or {}
            organization_id = rfx_record.get("organization_id")
            source_text = str(
                rfx_record.get("original_pdf_text")
                or (rfx_record.get("metadata_json") or {}).get("texto_original_relevante")
                or ""
            )
            existing_products = db.get_rfx_products(request_id) or []
        rfx_context = {
            "source_text": source_text,
            "rfx_type": rfx_record.get("rfx_type"),
            "location": rfx_record.get("location"),
            "delivery_date": rfx_record.get("delivery_date"),
        }

        # Cargar producto actual para re-resolver estructura/precios de forma consistente
        current = next((p for p in existing_products if str(p.get("id")) == str(product_id)), None)
        if not current:
            logger.warning(f"⚠️ Product {product_id} not found in RFX {request_id}")
            return {
                "status": "error",
                "product_id": product_id,
                "updated_fields": [],
                "message": "Producto no encontrado en el RFX",
            }

        field_mapping = {
            "name": "product_name",
            "quantity": "quantity",
            "price_unit": "estimated_unit_price",
            "unit": "unit",
            "description": "description",
            "notes": "notes",
        }
        db_updates_raw = {}
        for key, value in updates.items():
            db_key = field_mapping.get(key, key)
            db_updates_raw[db_key] = value

        merged = {
            "nombre": db_updates_raw.get("product_name")
            or current.get("product_name")
            or current.get("nombre"),
            "cantidad": db_updates_raw.get("quantity")
            if db_updates_raw.get("quantity") is not None
            else (current.get("quantity") if current.get("quantity") is not None else current.get("cantidad", 1)),
            "unidad": db_updates_raw.get("unit")
            or current.get("unit")
            or current.get("unidad")
            or "unidades",
            "precio_unitario": db_updates_raw.get("estimated_unit_price")
            if db_updates_raw.get("estimated_unit_price") is not None
            else (
                current.get("estimated_unit_price")
                if current.get("estimated_unit_price") is not None
                else current.get("precio_unitario", 0)
            ),
            "costo_unitario": db_updates_raw.get("unit_cost")
            if db_updates_raw.get("unit_cost") is not None
            else (
                current.get("unit_cost")
                if current.get("unit_cost") is not None
                else current.get("costo_unitario", 0)
            ),
            "descripcion": db_updates_raw.get("description")
            or current.get("description")
            or current.get("descripcion", ""),
            "notas": db_updates_raw.get("notes")
            or current.get("notes")
            or current.get("notas", ""),
            "specifications": explicit_specs_update or current.get("specifications") or current.get("especificaciones") or {},
        }
        if isinstance(explicit_breakdown_update, list):
            merged["bundle_breakdown"] = explicit_breakdown_update

        resolver = ProductResolutionService()
        try:
            resolver.catalog_search = get_catalog_search_service_for_rfx()
        except Exception as catalog_error:
            logger.warning(f"⚠️ Catalog service unavailable in update_product_tool: {catalog_error}")
            resolver.catalog_search = None

        resolved_items = resolver.resolve_for_chat_products(
            products=[merged],
            organization_id=organization_id,
            rfx_context=rfx_context,
        )
        resolved = resolved_items[0] if resolved_items else merged

        # Si el usuario pasó specifications/breakdown explícito, no permitir que el resolver los pise.
        if explicit_specs_update or isinstance(explicit_breakdown_update, list):
            final_specs = dict(resolved.get("specifications") or {})
            if explicit_specs_update:
                final_specs.update(explicit_specs_update)

            if isinstance(explicit_breakdown_update, list):
                final_specs["bundle_breakdown"] = explicit_breakdown_update
            elif "bundle_breakdown" in explicit_specs_update and isinstance(explicit_specs_update.get("bundle_breakdown"), list):
                final_specs["bundle_breakdown"] = explicit_specs_update.get("bundle_breakdown")

            if final_specs.get("bundle_breakdown"):
                final_specs["is_bundle"] = True
                final_specs["inferred_bundle"] = bool(final_specs.get("inferred_bundle", True))
                final_specs["requires_clarification"] = bool(final_specs.get("requires_clarification", False))

            resolved["specifications"] = final_specs
            resolved["bundle_breakdown"] = final_specs.get("bundle_breakdown") or []
            resolved["requires_clarification"] = bool(final_specs.get("requires_clarification", resolved.get("requires_clarification", False)))
            resolved["pricing_source"] = resolved.get("pricing_source") or "chat_explicit_specifications_update"

        db_updates = {
            "product_name": resolved.get("nombre"),
            "quantity": resolved.get("cantidad"),
            "unit": resolved.get("unidad"),
            "estimated_unit_price": resolved.get("precio_unitario"),
            "unit_cost": resolved.get("costo_unitario"),
            "description": resolved.get("descripcion"),
            "notes": resolved.get("notas"),
            "specifications": resolved.get("specifications") or {
                "is_bundle": bool(resolved.get("bundle_breakdown")),
                "inferred_bundle": False,
                "requires_clarification": bool(resolved.get("requires_clarification", False)),
                "bundle_breakdown": resolved.get("bundle_breakdown") or [],
            },
        }
        
        if session:
            for idx, p in enumerate(existing_products):
                if str(p.get("id")) == str(product_id):
                    existing_products[idx] = {
                        **p,
                        "nombre": resolved.get("nombre"),
                        "cantidad": resolved.get("cantidad"),
                        "unidad": resolved.get("unidad"),
                        "precio_unitario": resolved.get("precio_unitario"),
                        "costo_unitario": resolved.get("costo_unitario"),
                        "descripcion": resolved.get("descripcion"),
                        "notas": resolved.get("notas"),
                        "specifications": resolved.get("specifications") or {},
                        "especificaciones": resolved.get("specifications") or {},
                        "bundle_breakdown": resolved.get("bundle_breakdown") or [],
                        "requires_clarification": bool(resolved.get("requires_clarification", False)),
                    }
                    break

            preview_data["products"] = existing_products
            validated_data["productos"] = existing_products
            session_service.update_session(
                request_id,
                {
                    "preview_data": preview_data,
                    "validated_data": validated_data,
                },
            )
            return {
                "status": "success",
                "product_id": product_id,
                "updated_fields": list(updates.keys()),
                "message": f"Producto actualizado en sesión: {', '.join(updates.keys())}",
                "resolved_with_shared_resolver": True,
                "source": "processing_session",
            }

        # Actualizar en BD
        try:
            # CORRECTO: product_id primero, rfx_id segundo
            success = db.update_rfx_product(product_id, request_id, db_updates)
            
            if success:
                logger.info(f"✅ Product {product_id} updated successfully")
                return {
                    "status": "success",
                    "product_id": product_id,
                    "updated_fields": list(updates.keys()),
                    "message": f"Producto actualizado: {', '.join(updates.keys())}",
                    "resolved_with_shared_resolver": True,
                }
            else:
                logger.error(f"❌ Failed to update product {product_id}")
                return {
                    "status": "error",
                    "product_id": product_id,
                    "updated_fields": [],
                    "message": "No se pudo actualizar el producto"
                }
        except Exception as e:
            logger.error(f"❌ Error updating product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "updated_fields": [],
                "message": f"Error al actualizar: {str(e)}"
            }
    
    except Exception as e:
        error_msg = f"Error updating product: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
