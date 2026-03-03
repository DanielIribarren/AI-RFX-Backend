"""
Tool: add_products_tool

Propósito: Insertar productos al request
Wrapper de: DatabaseClient.create_rfx_product()

Fase 2 - Sprint 2
"""

from langchain.tools import tool
from typing import List, Dict, Any
import logging
from uuid import uuid4

from backend.core.database import get_database_client
from backend.services.catalog_helpers import get_catalog_search_service_for_rfx
from backend.services.product_resolution_service import ProductResolutionService
from backend.services.rfx_processing_session_service import RFXProcessingSessionService

logger = logging.getLogger(__name__)


@tool
def add_products_tool(request_id: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agrega productos al request.
    
    Esta tool permite al agente insertar uno o múltiples productos
    en el request actual.
    
    Args:
        request_id: ID del request (rfx_id) donde agregar productos
        products: Lista de productos a agregar. Cada producto debe tener:
            - name (str): Nombre del producto
            - quantity (int): Cantidad
            - price_unit (float): Precio unitario
            - category (str, opcional): Categoría del producto
            - unit (str, opcional): Unidad de medida (default: "unidades")
    
    Returns:
        Diccionario con resultado de la operación:
        {
            "status": "success" | "error",
            "products_added": int,
            "product_ids": List[str],
            "message": str
        }
    
    Ejemplos de uso:
        Usuario: "Agrega 10 sillas a $150 cada una"
        Agente: Llama a esta tool con una lista de productos
        
        Usuario: "Inserta los productos del archivo que te pasé"
        Agente: Extrae productos del archivo y llama a esta tool
    """
    
    try:
        logger.info(f"🔧 add_products_tool called: request_id={request_id}, products_count={len(products)}")
        
        if not products or len(products) == 0:
            logger.warning("⚠️ No products provided")
            return {
                "status": "error",
                "message": "No se proporcionaron productos para agregar",
                "products_added": 0,
                "product_ids": []
            }
        
        db = get_database_client()
        session_service = RFXProcessingSessionService()
        session = session_service.get_session(request_id)

        rfx_record = {}
        if session:
            preview_data = session.get("preview_data") or {}
            validated_data = session.get("validated_data") or {}
            organization_id = session.get("organization_id")
            source_text = str(preview_data.get("source_text") or "")
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
        rfx_context = {
            "source_text": source_text,
            "rfx_type": rfx_record.get("rfx_type"),
            "location": rfx_record.get("location"),
            "delivery_date": rfx_record.get("delivery_date"),
        }

        resolver = ProductResolutionService()
        try:
            resolver.catalog_search = get_catalog_search_service_for_rfx()
        except Exception as catalog_error:
            logger.warning(f"⚠️ Catalog service unavailable in add_products_tool: {catalog_error}")
            resolver.catalog_search = None

        normalized_input = []
        for p in products:
            normalized_input.append(
                {
                    "nombre": p.get("name") or p.get("product_name") or p.get("nombre"),
                    "cantidad": p.get("quantity", p.get("cantidad", 1)),
                    "unidad": p.get("unit", p.get("unidad", "unidades")),
                    "precio_unitario": p.get("price_unit", p.get("precio_unitario", p.get("estimated_unit_price", 0))),
                    "costo_unitario": p.get("unit_cost", p.get("costo_unitario", 0)),
                    "descripcion": p.get("description", p.get("descripcion", "")),
                    "notas": p.get("notes", p.get("notas", "")),
                }
            )

        resolved_products = resolver.resolve_for_chat_products(
            products=normalized_input,
            organization_id=organization_id,
            rfx_context=rfx_context,
        )

        added_ids = []
        added_products = []

        if session:
            existing_preview_products = list(preview_data.get("products") or [])
            existing_validated_products = list(validated_data.get("productos") or [])

            for product in resolved_products:
                product_id = str(uuid4())
                item = {
                    "id": product_id,
                    "nombre": product.get("nombre"),
                    "descripcion": product.get("descripcion"),
                    "cantidad": product.get("cantidad"),
                    "unidad": product.get("unidad"),
                    "precio_unitario": product.get("precio_unitario", 0),
                    "costo_unitario": product.get("costo_unitario", 0),
                    "notas": product.get("notas"),
                    "specifications": product.get("specifications") or {
                        "is_bundle": bool(product.get("bundle_breakdown")),
                        "inferred_bundle": False,
                        "requires_clarification": bool(product.get("requires_clarification", False)),
                        "bundle_breakdown": product.get("bundle_breakdown") or [],
                    },
                    "especificaciones": product.get("specifications") or {
                        "is_bundle": bool(product.get("bundle_breakdown")),
                        "inferred_bundle": False,
                        "requires_clarification": bool(product.get("requires_clarification", False)),
                        "bundle_breakdown": product.get("bundle_breakdown") or [],
                    },
                    "bundle_breakdown": product.get("bundle_breakdown") or [],
                    "requires_clarification": bool(product.get("requires_clarification", False)),
                }
                existing_preview_products.append(item)
                existing_validated_products.append(item)
                added_ids.append(product_id)
                added_products.append(item)

            preview_data["products"] = existing_preview_products
            validated_data["productos"] = existing_validated_products
            session_service.update_session(
                request_id,
                {
                    "preview_data": preview_data,
                    "validated_data": validated_data,
                },
            )

            return {
                "status": "success",
                "message": f"Se agregaron {len(added_ids)} producto(s) en sesión",
                "products_added": len(added_ids),
                "product_ids": added_ids,
                "products": added_products,
                "resolved_with_shared_resolver": True,
                "source": "processing_session",
            }
        
        # Insertar cada producto
        for i, product in enumerate(resolved_products, 1):
            # Validar campos requeridos
            if not product.get('nombre'):
                logger.warning(f"⚠️ Product {i} missing 'name' field, skipping")
                continue
            
            if product.get('cantidad') is None or float(product.get('cantidad') or 0) <= 0:
                logger.warning(f"⚠️ Product {i} has invalid quantity, skipping")
                continue
            
            # Preparar datos del producto
            product_data = {
                "product_name": product.get('nombre'),
                "quantity": product.get('cantidad'),
                "estimated_unit_price": product.get('precio_unitario', 0),
                "unit_cost": product.get('costo_unitario', 0),
                "unit": product.get('unidad', 'unidades'),
                "description": product.get('descripcion'),
                "notes": product.get('notas'),
                "specifications": product.get('specifications') or {
                    "is_bundle": bool(product.get("bundle_breakdown")),
                    "inferred_bundle": False,
                    "requires_clarification": bool(product.get("requires_clarification", False)),
                    "bundle_breakdown": product.get("bundle_breakdown") or [],
                },
            }
            
            # Insertar en BD
            try:
                inserted = db.insert_rfx_products(request_id, [product_data])
                if inserted and len(inserted) > 0:
                    product_id = inserted[0].get('id')
                    added_ids.append(product_id)
                    added_products.append(inserted[0])
                    logger.info(f"✅ Product added: {product.get('nombre')} (ID: {product_id})")
            except Exception as e:
                logger.error(f"❌ Error adding product {product.get('nombre')}: {e}")
                continue
        
        # Retornar JSON raw estructurado
        if len(added_ids) > 0:
            logger.info(f"✅ Successfully added {len(added_ids)} products to request {request_id}")
            return {
                "status": "success",
                "message": f"Se agregaron {len(added_ids)} producto(s) exitosamente",
                "products_added": len(added_ids),
                "product_ids": added_ids,
                "products": added_products,
                "resolved_with_shared_resolver": True,
            }
        else:
            logger.warning(f"⚠️ No products were added to request {request_id}")
            return {
                "status": "error",
                "message": "No se pudo agregar ningún producto (verifica los datos)",
                "products_added": 0,
                "product_ids": []
            }
    
    except Exception as e:
        error_msg = f"Error adding products: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
