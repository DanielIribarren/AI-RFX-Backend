"""
🛣️ RFX API Endpoints - Clean endpoint layer using improved services
Provides backward compatibility while using new architecture
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
from typing import Optional, Dict, Any
import logging
import time
import random
from datetime import datetime

from backend.models.rfx_models import (
    RFXInput, RFXResponse, RFXType, RFXHistoryItem,
    # Legacy aliases
    TipoRFX
)
from backend.services.rfx_processor import RFXProcessorService
from backend.core.config import get_file_upload_config

logger = logging.getLogger(__name__)

# Create blueprint
rfx_bp = Blueprint("rfx_api", __name__, url_prefix="/api/rfx")


@rfx_bp.route("/process", methods=["POST"])
def process_rfx():
    """
    🎯 Main RFX processing endpoint - Improved version
    Processes uploaded PDF/DOCX/TXT files using the new service architecture
    """
    try:
        # Get file upload configuration
        upload_config = get_file_upload_config()
        
        # Validate request has files (supports legacy 'pdf_file' or modern 'files[]')
        if 'pdf_file' not in request.files and 'files' not in request.files:
            return jsonify({"status":"error","message":"No file provided","error":"File upload is required"}), 400

        upload_config = get_file_upload_config()
        # Expand allowed extensions safely
        extra_exts = ['.pdf','.doc','.docx','.txt','.xlsx','.csv','.png','.jpg','.jpeg','.tiff','.zip']
        try:
            upload_config.allowed_extensions = list(sorted(set(upload_config.allowed_extensions) | set(extra_exts)))
        except Exception:
            pass

        files = request.files.getlist('files') if 'files' in request.files else [request.files['pdf_file']]
        valid_files, total_size = [], 0
        for f in files:
            if not f or f.filename == '':
                continue
            if not _is_allowed_file(f.filename, upload_config.allowed_extensions):
                return jsonify({"status":"error","message":f"File type not allowed. Supported: {', '.join(upload_config.allowed_extensions)}","error":"Invalid file type"}), 400
            content = f.read()
            total_size += len(content)
            if len(content) > upload_config.max_file_size:
                return jsonify({"status":"error","message":f"File too large. Maximum size: {upload_config.max_file_size // (1024*1024)}MB","error":"File size exceeded"}), 413
            valid_files.append({"filename": f.filename, "content": content})

        if not valid_files:
            return jsonify({"status":"error","message":"No file selected","error":"Empty filename"}), 400

        # Optional total limit
        if total_size > getattr(upload_config, "max_total_size", 32*1024*1024):
            return jsonify({"status":"error","message":"Total upload too large. Maximum total size: 32MB","error":"Total size exceeded"}), 413
        
        rfx_id = request.form.get('id', f"RFX-{int(time.time())}-{random.randint(1000, 9999)}")
        tipo_rfx = request.form.get('tipo_rfx', 'catering')
        rfx_input = RFXInput(id=rfx_id, rfx_type=RFXType(tipo_rfx))

        processor_service = RFXProcessorService()
        # New multi-file pipeline:
        rfx_processed = processor_service.process_rfx_case(rfx_input, valid_files)
        
        # NOTE: Proposal generation is now handled separately by user request
        # The user will review extracted data, set product costs, then request proposal generation
        
        # Create response using new models (without automatic proposal)
        response = RFXResponse(
            status="success",
            message="RFX data extracted and saved successfully. Review the extracted data and set product costs to generate proposal.",
            data=rfx_processed,
            propuesta_id=None,  # No automatic proposal generated
            propuesta_url=None  # User will generate proposal manually
        )
        
        logger.info(f"✅ RFX processed successfully: {rfx_id}")
        return jsonify({"status":"success","data":rfx_processed.model_dump(mode='json')}), 200
    except Exception as e:
        logger.exception("❌ Error processing RFX")
        return jsonify({"status":"error","message":str(e),"error":"internal"}), 500


@rfx_bp.route("/recent", methods=["GET"])
def get_recent_rfx():
    """Get recent RFX for sidebar (limited to 12 items)"""
    try:
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Get last 12 RFX records for sidebar
        rfx_records = db_client.get_rfx_history(limit=12, offset=0)
        
        # Format for sidebar display with consistent structure (V2.0)
        recent_items = []
        for record in rfx_records:
            # V2.0 uses 'status' field directly
            rfx_status = record.get("status", "in_progress")
            status = "completed" if rfx_status == "completed" else "In progress"
            
            # V2.0 structure with joined tables
            company_name = record.get("companies", {}).get("name", "Unknown Company") if record.get("companies") else "Unknown Company"
            requester_name = record.get("requesters", {}).get("name", "Unknown Requester") if record.get("requesters") else "Unknown Requester"
            
            recent_item = {
                "id": record["id"],
                "title": record.get("title", f"RFX: {company_name}"),
                "client": requester_name,
                "date": record["received_at"],
                "status": status,
                "rfxId": record["id"],
                # Additional fields for consistency with history
                "tipo": record.get("rfx_type", "catering"),
                "numero_productos": len(record.get("requested_products", [])) if record.get("requested_products") else 0,
                "costo_total": record.get("actual_cost", 0.0) or 0.0
            }
            recent_items.append(recent_item)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(recent_items)} recent RFX records",
            "data": recent_items
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting recent RFX: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve recent RFX",
            "error": str(e)
        }), 500


@rfx_bp.route("/history", methods=["GET"])
def get_rfx_history():
    """Get RFX processing history with pagination"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        # Validate pagination parameters
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({
                "status": "error",
                "message": "Invalid pagination parameters",
                "error": "Page must be >= 1, limit between 1-100"
            }), 400
        
        # Get data from database
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        rfx_records = db_client.get_rfx_history(limit=limit, offset=offset)
        
        # Format response data with V2.0 structure
        history_items = []
        for record in rfx_records:
            # V2.0: Extract company and requester data from related tables
            company_data = record.get("companies", {}) or {}
            requester_data = record.get("requesters", {}) or {}
            metadata = record.get("metadata_json", {}) or {}
            
            # Map V2.0 status to legacy format
            rfx_status = record.get("status", "in_progress")
            legacy_status = "completed" if rfx_status == "completed" else "In progress"
            
            # Extract empresa information
            empresa_info = {
                "nombre_empresa": company_data.get("name", metadata.get("nombre_empresa", "")),
                "email_empresa": company_data.get("email", metadata.get("email_empresa", "")),
                "telefono_empresa": company_data.get("phone", metadata.get("telefono_empresa", ""))
            }
            
            # Get structured products count
            structured_products = db_client.get_rfx_products(record["id"])
            productos_count = len(structured_products) if structured_products else len(record.get("requested_products", []))
            
            history_item = {
                # V2.0 fields
                "id": record["id"],
                "company_id": record.get("company_id"),
                "requester_id": record.get("requester_id"),
                "company_name": company_data.get("name", "Unknown Company"),
                "requester_name": requester_data.get("name", "Unknown Requester"),
                "rfx_type": record.get("rfx_type", "catering"),
                "title": record.get("title", f"RFX Request - {record.get('rfx_type', 'catering')}"),
                "status": rfx_status,
                "location": record.get("location", ""),
                "delivery_date": record.get("delivery_date"),
                "received_at": record.get("received_at"),
                "estimated_budget": record.get("estimated_budget"),
                "actual_cost": record.get("actual_cost"),
                
                # Legacy compatibility fields
                "cliente_id": record.get("requester_id"),  # Map for backwards compatibility
                "nombre_solicitante": requester_data.get("name", "Unknown Requester"),
                "tipo": record.get("rfx_type", "catering"),
                "fecha_recepcion": record.get("received_at"),
                "costo_total": record.get("actual_cost", 0.0),
                "pdf_url": "",  # TODO: Add PDF URL if available
                "estado": legacy_status,
                "numero_productos": productos_count,
                
                # Empresa information
                "empresa": empresa_info,
                
                # Additional fields for frontend consistency
                "client": requester_data.get("name", "Unknown Requester"),
                "date": record.get("received_at"),
                "rfxId": record["id"]
            }
            history_items.append(history_item)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(history_items)} RFX records",
            "data": history_items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": len(history_items),
                "has_more": len(history_items) == limit
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting RFX history: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve RFX history",
            "error": str(e)
        }), 500


@rfx_bp.route("/<rfx_id>/finalize", methods=["POST"])
def finalize_rfx(rfx_id: str):
    """Mark an RFX as finalized/completed"""
    try:
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Update RFX status to completed
        result = db_client.update_rfx_status(rfx_id, "completed")
        
        if not result:
            return jsonify({
                "status": "error",
                "message": "RFX not found or could not be updated",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        response = {
            "status": "success",
            "message": f"RFX {rfx_id} finalized successfully",
            "data": {
                "id": rfx_id,
                "estado": "completed"
            }
        }
        
        logger.info(f"✅ RFX finalized successfully: {rfx_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error finalizing RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to finalize RFX",
            "error": str(e)
        }), 500


@rfx_bp.route("/<rfx_id>", methods=["GET"])
def get_rfx_by_id(rfx_id: str):
    """Get specific RFX by ID"""
    try:
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        rfx_record = db_client.get_rfx_by_id(rfx_id)
        
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        # Convert V2.0 database record to response format
        company_data = rfx_record.get("companies", {}) or {}
        requester_data = rfx_record.get("requesters", {}) or {}
        metadata = rfx_record.get("metadata_json", {}) or {}
        
        # Get proposals to determine processing state
        proposals = db_client.get_proposals_by_rfx_id(rfx_id)
        estado = "completed" if proposals else "in_progress"
        
        # Get structured products with real database IDs
        structured_products = db_client.get_rfx_products(rfx_id)
        products_list = []
        if structured_products:
            products_list = [{
                "id": p.get("id", ""),  # ✅ Include real database ID
                "nombre": p.get("product_name", ""),
                "cantidad": p.get("quantity", 0),
                "unidad": p.get("unit", ""),
                "precio_unitario": p.get("estimated_unit_price"),
                "subtotal": p.get("total_estimated_cost")
            } for p in structured_products]
        else:
            # Fallback to requested_products JSONB (without real IDs)
            products_list = rfx_record.get("requested_products", [])
        
        rfx_data = {
            # V2.0 fields
            "id": rfx_record["id"],
            "company_id": rfx_record.get("company_id"),
            "requester_id": rfx_record.get("requester_id"),
            "rfx_type": rfx_record.get("rfx_type", "catering"),
            "title": rfx_record.get("title", "RFX Request"),
            "location": rfx_record.get("location", ""),
            "delivery_date": rfx_record.get("delivery_date"),
            "delivery_time": rfx_record.get("delivery_time"),
            "status": rfx_record.get("status", "in_progress"),
            "priority": rfx_record.get("priority", "medium"),
            "estimated_budget": rfx_record.get("estimated_budget"),
            "actual_cost": rfx_record.get("actual_cost"),
            "received_at": rfx_record.get("received_at"),
            "original_pdf_text": rfx_record.get("original_pdf_text", ""),
            "requested_products": rfx_record.get("requested_products", []),
            "metadata_json": metadata,
            
            # Legacy compatibility fields
            "email": requester_data.get("email", ""),
            "nombre_solicitante": requester_data.get("name", ""),
            "productos": products_list,
            "hora_entrega": rfx_record.get("delivery_time"),
            "fecha": rfx_record.get("delivery_date"),
            "lugar": rfx_record.get("location", ""),
            "tipo": rfx_record.get("rfx_type", "catering"),
            "estado": estado,
            "fecha_recepcion": rfx_record.get("received_at"),
            "metadatos": metadata,
            
            # Company and requester information
            "company_name": company_data.get("name", ""),
            "company_email": company_data.get("email", ""),
            "company_phone": company_data.get("phone", ""),
            "requester_name": requester_data.get("name", ""),
            "requester_position": requester_data.get("position", ""),
            "requester_phone": requester_data.get("phone", ""),
            
            # Legacy empresa fields for backwards compatibility
            "nombre_empresa": company_data.get("name", metadata.get("nombre_empresa", "")),
            "email_empresa": company_data.get("email", metadata.get("email_empresa", "")),
            "telefono_empresa": company_data.get("phone", metadata.get("telefono_empresa", "")),
            "telefono_solicitante": requester_data.get("phone", metadata.get("telefono_solicitante", "")),
            "cargo_solicitante": requester_data.get("position", metadata.get("cargo_solicitante", ""))
        }
        
        response = {
            "status": "success",
            "message": "RFX retrieved successfully",
            "data": rfx_data
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve RFX {rfx_id}",
            "error": str(e)
        }), 500


@rfx_bp.route("/<rfx_id>/data", methods=["PUT"])
def update_rfx_data(rfx_id: str):
    """Actualizar datos del RFX (empresa, cliente, solicitud, etc.)"""
    try:
        logger.info(f"🔄 DEBUG: update_rfx_data endpoint called for RFX: {rfx_id}")
        logger.info(f"🔄 DEBUG: Request headers: {dict(request.headers)}")
        logger.info(f"🔄 DEBUG: Request content-type: {request.content_type}")
        
        if not request.is_json:
            logger.error(f"❌ DEBUG: Invalid content type: {request.content_type}")
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        field_name = data.get("field")
        field_value = data.get("value")
        
        logger.info(f"🔄 DEBUG: Request data received: {data}")
        logger.info(f"🔄 DEBUG: Field name: {field_name}, Field value: {field_value}")
        
        if not field_name:
            logger.error(f"❌ DEBUG: Missing field name in request")
            return jsonify({
                "status": "error",
                "message": "field name is required",
                "error": "Missing field name"
            }), 400
        
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        logger.info(f"🔄 DEBUG: Database client obtained, checking if RFX exists: {rfx_id}")
        
        # Verificar que el RFX existe
        rfx_record = db_client.get_rfx_by_id(rfx_id)
        if not rfx_record:
            logger.error(f"❌ DEBUG: RFX not found: {rfx_id}")
            return jsonify({
                "status": "error",
                "message": "RFX not found",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        logger.info(f"✅ DEBUG: RFX found: {rfx_id}")
        logger.info(f"🔍 DEBUG: Current RFX data keys: {list(rfx_record.keys()) if rfx_record else 'None'}")
        
        # Mapear campos del frontend a su ubicación correcta en el esquema V2.0 normalizado
        field_mapping = {
            # Campos que van a la tabla requesters
            "solicitante": "requesters.name",
            "email": "requesters.email", 
            "telefonoSolicitante": "requesters.phone",
            "cargoSolicitante": "requesters.position",
            
            # Campos que van a la tabla companies  
            "nombreEmpresa": "companies.name",
            "emailEmpresa": "companies.email",
            "telefonoEmpresa": "companies.phone",
            
            # Campos que van directamente a rfx_v2
            "fechaEntrega": "rfx_v2.delivery_date",
            "lugarEntrega": "rfx_v2.location", 
            "requirements": "rfx_v2.requirements"
        }
        
        logger.info(f"🔄 DEBUG: Field mapping lookup for '{field_name}'")
        db_field = field_mapping.get(field_name)
        if not db_field:
            logger.error(f"❌ DEBUG: Field '{field_name}' not found in mapping")
            logger.error(f"❌ DEBUG: Available fields: {list(field_mapping.keys())}")
            return jsonify({
                "status": "error",
                "message": f"Field '{field_name}' is not updateable",
                "error": "Invalid field name"
            }), 400
        
        logger.info(f"✅ DEBUG: Field '{field_name}' mapped to '{db_field}'")
        
        # Categorizar campos según su tabla de destino
        requester_fields = ["solicitante", "email", "telefonoSolicitante", "cargoSolicitante"]
        company_fields = ["nombreEmpresa", "emailEmpresa", "telefonoEmpresa"] 
        rfx_direct_fields = ["fechaEntrega", "lugarEntrega", "requirements"]
        
        if field_name in requester_fields:
            # Actualizar en tabla requesters
            logger.info(f"🔄 DEBUG: Field '{field_name}' goes to requesters table")
            
            requester_id = rfx_record.get("requester_id")
            if not requester_id:
                logger.error(f"❌ DEBUG: No requester_id found in RFX {rfx_id}")
                return jsonify({
                    "status": "error",
                    "message": "No requester found for this RFX",
                    "error": "Missing requester_id"
                }), 400
            
            # Mapear campo frontend a columna de requesters
            requester_field_mapping = {
                "solicitante": "name",
                "email": "email", 
                "telefonoSolicitante": "phone",
                "cargoSolicitante": "position"
            }
            
            db_column = requester_field_mapping[field_name]
            
            # Actualizar en tabla requesters usando método estructurado
            try:
                success = db_client.update_requester(requester_id, {db_column: field_value})
                
                if not success:
                    logger.error(f"❌ DEBUG: Failed to update requester {requester_id}")
                    return jsonify({
                        "status": "error",
                        "message": "Failed to update requester data"
                    }), 500
                
                logger.info(f"✅ DEBUG: Updated requester {requester_id} field '{db_column}' = '{field_value}'")
                
            except Exception as e:
                logger.error(f"❌ DEBUG: Error updating requester: {e}")
                return jsonify({
                    "status": "error",
                    "message": "Database error updating requester",
                    "error": str(e)
                }), 500
            
        elif field_name in company_fields:
            # Actualizar en tabla companies
            logger.info(f"🔄 DEBUG: Field '{field_name}' goes to companies table")
            
            company_id = rfx_record.get("company_id")
            if not company_id:
                logger.error(f"❌ DEBUG: No company_id found in RFX {rfx_id}")
                return jsonify({
                    "status": "error",
                    "message": "No company found for this RFX",
                    "error": "Missing company_id"
                }), 400
            
            # Mapear campo frontend a columna de companies
            company_field_mapping = {
                "nombreEmpresa": "name",
                "emailEmpresa": "email",
                "telefonoEmpresa": "phone"
            }
            
            db_column = company_field_mapping[field_name]
            
            # Actualizar en tabla companies usando método estructurado
            try:
                success = db_client.update_company(company_id, {db_column: field_value})
                
                if not success:
                    logger.error(f"❌ DEBUG: Failed to update company {company_id}")
                    return jsonify({
                        "status": "error",
                        "message": "Failed to update company data"
                    }), 500
                
                logger.info(f"✅ DEBUG: Updated company {company_id} field '{db_column}' = '{field_value}'")
                
            except Exception as e:
                logger.error(f"❌ DEBUG: Error updating company: {e}")
                return jsonify({
                    "status": "error",
                    "message": "Database error updating company",
                    "error": str(e)
                }), 500
            
        elif field_name in rfx_direct_fields:
            # Actualizar directamente en rfx_v2
            logger.info(f"🔄 DEBUG: Field '{field_name}' goes to rfx_v2 table")
            
            # Mapear campo frontend a columna de rfx_v2
            rfx_field_mapping = {
                "fechaEntrega": "delivery_date",
                "lugarEntrega": "location", 
                "requirements": "requirements"
            }
            
            db_column = rfx_field_mapping[field_name]
            update_data = {db_column: field_value}
            
            # Usar la función existente para actualizar rfx_v2
            logger.info(f"🔄 DEBUG: Calling db_client.update_rfx_data for rfx_v2...")
            success = db_client.update_rfx_data(rfx_id, update_data)
            
            if not success:
                logger.error(f"❌ DEBUG: Failed to update RFX {rfx_id}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to update RFX data"
                }), 500
            
        else:
            logger.error(f"❌ DEBUG: Field '{field_name}' not found in any category")
            return jsonify({
                "status": "error", 
                "message": f"Field '{field_name}' is not configured for updates",
                "error": "Field not in allowed categories"
            }), 400
        
        # Si llegamos aquí, la actualización fue exitosa
        response = {
            "status": "success",
            "message": f"Campo '{field_name}' actualizado exitosamente",
            "data": {
                "rfx_id": rfx_id,
                "field": field_name,
                "value": field_value
            }
        }
        
        logger.info(f"✅ DEBUG: Field '{field_name}' updated successfully for RFX {rfx_id}")
        logger.info(f"✅ DEBUG: Sending response: {response}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ DEBUG: Exception in update_rfx_data endpoint for {rfx_id}: {e}")
        logger.error(f"❌ DEBUG: Exception type: {type(e)}")
        import traceback
        logger.error(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to update RFX data",
            "error": str(e)
        }), 500


@rfx_bp.route("/<rfx_id>/products/costs", methods=["PUT"])
def update_product_costs(rfx_id: str):
    """Actualizar costos unitarios de productos RFX proporcionados por el usuario"""
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        product_costs = data.get("product_costs", [])
        
        if not product_costs or not isinstance(product_costs, list):
            return jsonify({
                "status": "error",
                "message": "product_costs array is required",
                "error": "Invalid product costs data"
            }), 400
        
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Verificar que el RFX existe
        rfx_record = db_client.get_rfx_by_id(rfx_id)
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        # Obtener productos reales del RFX para mapeo correcto
        real_products = db_client.get_rfx_products(rfx_id)
        product_mapping = {}
        
        logger.info(f"🔍 DEBUG: Found {len(real_products)} real products for RFX {rfx_id}")
        for i, product in enumerate(real_products):
            logger.debug(f"Product {i}: ID={product.get('id')}, Name={product.get('product_name')}")
        
        # Si no hay productos reales, verificar si hay productos en el RFX principal
        if not real_products:
            # Intentar obtener el RFX completo para ver si hay productos en requested_products
            rfx_record = db_client.get_rfx_by_id(rfx_id)
            requested_products = rfx_record.get("requested_products", []) if rfx_record else []
            
            logger.warning(f"No structured products found for RFX {rfx_id}")
            logger.info(f"However, found {len(requested_products)} products in requested_products field")
            
            if not requested_products:
                return jsonify({
                    "status": "error",
                    "message": "No products found for this RFX",
                    "error": "Products must be processed and saved before setting costs",
                    "debug_info": {
                        "rfx_id": str(rfx_id),
                        "structured_products_count": 0,
                        "requested_products_count": 0
                    }
                }), 404
            else:
                return jsonify({
                    "status": "error", 
                    "message": "Products found in RFX but not structured",
                    "error": "Products need to be re-processed to create structured products table",
                    "debug_info": {
                        "rfx_id": str(rfx_id),
                        "structured_products_count": 0,
                        "requested_products_count": len(requested_products)
                    }
                }), 404
        
        # Crear mapeo por índice para IDs falsos como "product-0"
        for i, real_product in enumerate(real_products):
            fake_id = f"product-{i}"
            product_mapping[fake_id] = real_product["id"]
            # También mapear el ID real a sí mismo
            product_mapping[real_product["id"]] = real_product["id"]
        
        # Actualizar costos de productos
        updated_products = []
        for cost_data in product_costs:
            product_id = cost_data.get("product_id")
            unit_price = cost_data.get("unit_price")
            
            if not product_id or unit_price is None:
                continue
                
            try:
                unit_price = float(unit_price)
                if unit_price < 0:
                    continue
                
                # Convertir ID falso a ID real si es necesario
                real_product_id = product_mapping.get(product_id, product_id)
                
                # Actualizar producto en BD con ID real
                success = db_client.update_rfx_product_cost(rfx_id, real_product_id, unit_price)
                if success:
                    updated_products.append({
                        "product_id": real_product_id,
                        "original_id": product_id,
                        "unit_price": unit_price
                    })
                else:
                    logger.warning(f"Failed to update product {product_id} -> {real_product_id}")
                    
            except (ValueError, TypeError):
                logger.warning(f"Invalid unit_price for product {product_id}: {unit_price}")
                continue
        
        # Registrar evento en historial
        history_event = {
            "rfx_id": str(rfx_id),
            "event_type": "product_costs_updated",
            "description": f"Usuario actualizó costos de {len(updated_products)} productos",
            "new_values": {
                "updated_products": updated_products,
                "timestamp": datetime.now().isoformat()
            },
            "performed_by": "user"
        }
        db_client.insert_rfx_history(history_event)
        
        response = {
            "status": "success",
            "message": f"Costos actualizados para {len(updated_products)} productos",
            "data": {
                "rfx_id": rfx_id,
                "updated_products": updated_products
            }
        }
        
        logger.info(f"✅ Product costs updated for RFX {rfx_id}: {len(updated_products)} products")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating product costs for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update product costs",
            "error": str(e)
        }), 500


def _is_allowed_file(filename: str, allowed_extensions: list) -> bool:
    """Check if file extension is allowed"""
    if not filename:
        return False
    
    file_extension = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return file_extension in allowed_extensions


def _get_latest_proposal_for_rfx(rfx_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest generated proposal for an RFX"""
    try:
        from backend.core.database import get_database_client
        db_client = get_database_client()
        
        # Get the most recent proposal for this RFX
        proposals = db_client.get_proposals_by_rfx_id(rfx_id)
        if proposals:
            # Return the most recent proposal
            return proposals[0] if proposals else None
        return None
    except Exception as e:
        logger.warning(f"⚠️ Could not retrieve proposal for RFX {rfx_id}: {e}")
        return None


# For backward compatibility with existing webhook endpoint
@rfx_bp.route("/webhook", methods=["POST"])
def rfx_webhook_compatibility():
    """
    🔄 Backward compatibility endpoint
    Redirects to the new process endpoint for existing integrations
    """
    logger.info("📡 Legacy webhook endpoint called, redirecting to new process endpoint")
    return process_rfx()


@rfx_bp.route("/<rfx_id>/products/<product_id>", methods=["PUT"])
def update_rfx_product(rfx_id: str, product_id: str):
    """Actualizar un producto específico del RFX"""
    try:
        logger.info(f"🔄 DEBUG: update_rfx_product endpoint called for RFX: {rfx_id}, Product: {product_id}")
        
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        field_name = data.get("field")
        field_value = data.get("value")
        
        logger.info(f"🔄 DEBUG: Product update data: field='{field_name}', value='{field_value}'")
        
        if not field_name:
            return jsonify({
                "status": "error",
                "message": "field name is required"
            }), 400
        
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Verificar que el RFX existe
        rfx_record = db_client.get_rfx_by_id(rfx_id)
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found"
            }), 404
        
        # Mapear campos de productos (frontend → backend)
        product_field_mapping = {
            # Nombres en español (frontend) → Nombres en inglés (BD)
            "nombre": "product_name",                    # Nombre del producto
            "cantidad": "quantity",                      # Cantidad
            "unidad": "unit",                           # Unidad de medida
            "precio_unitario": "estimated_unit_price",   # Precio unitario
            "subtotal": "total_estimated_cost",         # Costo total
            "descripcion": "description",               # Descripción
            "notas": "notes",                          # Notas
            
            # También soportar nombres en inglés por compatibilidad
            "product_name": "product_name",
            "quantity": "quantity", 
            "unit": "unit",
            "estimated_unit_price": "estimated_unit_price",
            "total_estimated_cost": "total_estimated_cost",
            "description": "description",
            "notes": "notes"
        }
        
        db_field = product_field_mapping.get(field_name)
        if not db_field:
            return jsonify({
                "status": "error",
                "message": f"Field '{field_name}' is not updateable for products"
            }), 400
        
        # Validar y convertir tipos de datos según el campo
        processed_value = field_value
        try:
            if db_field in ["quantity"]:
                # Campos numéricos enteros
                processed_value = int(field_value) if field_value is not None else 0
            elif db_field in ["estimated_unit_price", "total_estimated_cost"]:
                # Campos numéricos decimales
                processed_value = float(field_value) if field_value is not None else None
            # Los demás campos (text) no necesitan conversión
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid data type for field {field_name}: {field_value}")
            return jsonify({
                "status": "error",
                "message": f"Invalid value for field '{field_name}'. Expected number but got '{field_value}'",
                "error": "Data type validation failed"
            }), 400
        
        # Actualizar el producto usando método estructurado
        try:
            update_data = {db_field: processed_value}
            success = db_client.update_rfx_product(product_id, rfx_id, update_data)
            
            if success:
                logger.info(f"✅ Product updated: {product_id} field '{field_name}' = '{processed_value}'")
                return jsonify({
                    "status": "success",
                    "message": f"Product field '{field_name}' updated successfully",
                    "data": {
                        "rfx_id": rfx_id,
                        "product_id": product_id,
                        "field": field_name,
                        "value": processed_value
                    }
                }), 200
            else:
                logger.error(f"❌ Product update failed: {product_id}")
                return jsonify({
                    "status": "error",
                    "message": "Product not found or update failed",
                    "details": f"Product {product_id} not found in RFX {rfx_id}"
                }), 404
                
        except Exception as db_e:
            logger.error(f"❌ Database error updating product: {db_e}")
            return jsonify({
                "status": "error",
                "message": "Failed to update product",
                "error": str(db_e)
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Exception in update_rfx_product: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500
