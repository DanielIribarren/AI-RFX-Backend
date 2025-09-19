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

from backend.models.project_models import (
    # Unified models (with legacy aliases)
    ProjectInput as RFXInput, ProjectModel as RFXProcessed,
    ProjectTypeEnum as RFXType, ProjectStatusEnum as RFXStatus,
    # Legacy types that were in rfx_models
    RFXType as TipoRFX, PriorityLevel,
    # Response and utility models
    RFXResponse, ProjectResponse, RFXHistoryItem, 
    PaginationInfo, RFXListResponse, LoadMoreRequest
)
# from backend.services.rfx_processor import RFXProcessorService  # REMOVED: Replaced by BudyAgent
from backend.services.budy_agent import get_budy_agent  # NEW: BudyAgent integration
from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter  # UPDATED: Unified adapter
from backend.core.config import get_file_upload_config
from backend.core.database import get_database_client  # NEW: BD integration
from uuid import uuid4
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
rfx_bp = Blueprint("rfx_api", __name__, url_prefix="/api/rfx")




@rfx_bp.route("/process", methods=["POST"])
def process_rfx():
    """
    🎯 Main RFX processing endpoint - FLEXIBLE version
    Processes: SOLO ARCHIVOS | SOLO TEXTO | ARCHIVOS + TEXTO
    
    Casos de uso:
    1. Solo archivos: frontend envía files → procesa archivos
    2. Solo texto: frontend envía contenido_extraido → procesa texto
    3. Ambos: frontend envía files + contenido_extraido → procesa todo
    """
    try:
        # 🔍 LOGGING INICIAL - Debug para entender qué llega
        logger.info(f"🔍 RFX Process Request received")
        logger.info(f"📄 Request files: {list(request.files.keys())}")
        logger.info(f"📝 Request form keys: {list(request.form.keys())}")
        
        # Get file upload configuration
        upload_config = get_file_upload_config()
        
        # 🆕 NUEVA LÓGICA FLEXIBLE: Obtener archivos Y contenido de texto
        files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'pdf_file' in request.files:
            files = [request.files['pdf_file']]
            
        contenido_extraido = request.form.get('contenido_extraido', '').strip()
        
        # 🔍 LOGGING DETALLADO
        logger.info(f"📄 Files count: {len(files)}")
        if contenido_extraido:
            logger.info(f"📝 Text content length: {len(contenido_extraido)} characters")
            logger.info(f"📝 Text preview: {contenido_extraido[:200]}...")
        
        # ✅ VALIDACIÓN FLEXIBLE: Debe tener AL MENOS archivos O texto
        has_files = any(f and f.filename for f in files)
        has_text = bool(contenido_extraido)
        
        if not has_files and not has_text:
            logger.error("❌ No content provided - neither files nor text")
            return jsonify({
                "status": "error",
                "message": "Debe proporcionar archivos o contenido de texto",
                "error": "Content required"
            }), 400
        
        logger.info(f"✅ Content validation passed - has_files: {has_files}, has_text: {has_text}")

        # 📄 PROCESAR ARCHIVOS (si existen) - WITH DETAILED DEBUG
        upload_config = get_file_upload_config()
        extra_exts = ['.pdf','.doc','.docx','.txt','.xlsx','.csv','.png','.jpg','.jpeg','.tiff','.zip']
        try:
            upload_config.allowed_extensions = list(sorted(set(upload_config.allowed_extensions) | set(extra_exts)))
        except Exception:
            pass

        valid_files, total_size = [], 0
        if has_files:
            logger.info(f"📄 PROCESSING {len(files)} FILES:")
            for file_index, f in enumerate(files):
                if not f or f.filename == '':
                    logger.warning(f"⚠️ SKIPPING EMPTY FILE {file_index+1}")
                    continue
                    
                logger.info(f"📄 PROCESSING FILE {file_index+1}: '{f.filename}' (type: {f.content_type if hasattr(f, 'content_type') else 'unknown'})")
                
                if not _is_allowed_file(f.filename, upload_config.allowed_extensions):
                    logger.error(f"❌ FILE TYPE NOT ALLOWED: {f.filename}")
                    return jsonify({"status":"error","message":f"File type not allowed. Supported: {', '.join(upload_config.allowed_extensions)}","error":"Invalid file type"}), 400
                
                content = f.read()
                content_size = len(content)
                total_size += content_size
                
                logger.info(f"📄 FILE READ: '{f.filename}' → {content_size} bytes")
                
                # Check content type by looking at first few bytes
                if content_size > 0:
                    header = content[:20]
                    if header.startswith(b'%PDF'):
                        logger.info(f"📄 DETECTED: {f.filename} is PDF format")
                    elif header.startswith(b'PK'):
                        logger.info(f"📄 DETECTED: {f.filename} is ZIP-based format (DOCX/XLSX)")
                    else:
                        logger.info(f"📄 DETECTED: {f.filename} other format (first bytes: {header[:10]})")
                
                if content_size > upload_config.max_file_size:
                    logger.error(f"❌ FILE TOO LARGE: {f.filename} ({content_size} bytes > {upload_config.max_file_size})")
                    return jsonify({"status":"error","message":f"File too large. Maximum size: {upload_config.max_file_size // (1024*1024)}MB","error":"File size exceeded"}), 413
                
                valid_files.append({"filename": f.filename, "content": content})
                logger.info(f"✅ FILE VALIDATED: '{f.filename}' ({content_size} bytes) - READY FOR PROCESSING")
            
            logger.info(f"📊 FILES SUMMARY: {len(valid_files)} valid files, total size: {total_size} bytes")

        # 📝 PROCESAR CONTENIDO DE TEXTO (si existe)
        if has_text:
            # Crear archivo virtual con el contenido de texto
            rfx_id_temp = f"RFX-{int(time.time())}-{random.randint(1000, 9999)}"
            text_filename = f"{rfx_id_temp}_contenido_extraido.txt"
            text_content = contenido_extraido.encode('utf-8')
            
            valid_files.append({
                "filename": text_filename,
                "content": text_content
            })
            total_size += len(text_content)
            logger.info(f"✅ Text content processed as virtual file: {text_filename} ({len(text_content)} bytes)")

        # Validación final de contenido
        if not valid_files:
            logger.error("❌ No valid content after processing")
            return jsonify({"status":"error","message":"No se pudo procesar el contenido proporcionado","error":"No valid content"}), 400

        # Optional total limit
        if total_size > getattr(upload_config, "max_total_size", 32*1024*1024):
            return jsonify({"status":"error","message":"Total upload too large. Maximum total size: 32MB","error":"Total size exceeded"}), 413
        
        # 🆔 Generar ID y configuración RFX
        rfx_id = request.form.get('id', f"RFX-{int(time.time())}-{random.randint(1000, 9999)}")
        tipo_rfx = request.form.get('tipo_rfx', 'catering')
        rfx_input = RFXInput(id=rfx_id, rfx_type=RFXType(tipo_rfx))

        logger.info(f"🚀 Starting RFX processing: {rfx_id} (type: {tipo_rfx})")
        logger.info(f"📊 Processing summary: {len(valid_files)} files, total_size: {total_size} bytes")

        # 🤖 PROCESAR CON BUDY AGENT - NUEVO WORKFLOW INTELIGENTE
        logger.info(f"🤖 Starting processing with BudyAgent (MOMENTO 1)")
        
        # Preparar documento/contenido para BudyAgent
        document_content = ""
        
        # Si hay contenido de texto, usarlo directamente
        if contenido_extraido:
            document_content = contenido_extraido
            logger.info("📝 Using provided text content for BudyAgent")
        
        # Si hay archivos, extraer texto (fallback al procesador legacy si es necesario)
        if valid_files and not document_content:
            logger.info("📄 Extracting text from files for BudyAgent")
            try:
                # Usar RFXProcessorService solo para extracción de texto
                processor_service = RFXProcessorService()
                temp_result = processor_service.process_rfx_case(rfx_input, valid_files)
                
                # Extraer texto del resultado legacy
                if hasattr(temp_result, 'extracted_content'):
                    document_content = temp_result.extracted_content
                elif isinstance(temp_result, dict) and 'extracted_content' in temp_result:
                    document_content = temp_result['extracted_content']
                else:
                    document_content = str(temp_result)
                    
                logger.info(f"📄 Extracted {len(document_content)} characters from files")
            except Exception as e:
                logger.warning(f"⚠️ File extraction failed, using basic content: {e}")
                document_content = f"Archivos subidos: {[f.filename for f in valid_files]}"
        
        # Preparar metadatos del request
        metadata = {
            'rfx_id': rfx_id,
            'tipo_rfx': tipo_rfx,
            'files_info': [{'filename': f.filename if hasattr(f, 'filename') else str(f)} for f in valid_files] if valid_files else [],
            'processing_mode': 'files_and_text' if (valid_files and contenido_extraido) else 'files_only' if valid_files else 'text_only',
            'request_timestamp': datetime.utcnow().isoformat()
        }
        
        # Ejecutar BudyAgent MOMENTO 1: Análisis y Extracción
        budy_agent = get_budy_agent()
        
        # Limpiar contexto previo para nuevo proyecto
        budy_agent.clear_project_context()
        
        # Ejecutar análisis inteligente
        import asyncio
        budy_result = asyncio.run(budy_agent.analyze_and_extract(document_content, metadata))
        
        logger.info(f"✅ BudyAgent MOMENTO 1 completed successfully")
        
        # 🗄️ GUARDAR EN BUDY-AI-SCHEMA DATABASE
        db_client = get_database_client()
        
        # Extraer datos para guardar en BD
        extracted_data = budy_result.get('extracted_data', {})
        project_details = extracted_data.get('project_details', {})
        client_info = extracted_data.get('client_information', {})
        timeline = extracted_data.get('timeline', {})
        budget_financial = extracted_data.get('budget_financial', {})
        requirements = extracted_data.get('requirements', {})
        location_logistics = extracted_data.get('location_logistics', {})
        requested_products = extracted_data.get('requested_products', [])
        
        # 1. GUARDAR ORGANIZACIÓN (si no existe)
        organization_data = {
            'name': client_info.get('company', 'Empresa No Especificada'),
            'email': client_info.get('company_email'),
            'phone': client_info.get('company_phone'),
            'industry': project_details.get('industry_domain', 'general'),
            'created_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Buscar organización existente por nombre o crear nueva
            existing_org = None
            if organization_data['name'] != 'Empresa No Especificada':
                # Intentar buscar por nombre similar
                all_orgs = db_client.get_organizations()
                for org in all_orgs:
                    if org.get('name', '').lower() == organization_data['name'].lower():
                        existing_org = org
                        break
            
            if existing_org:
                organization_id = existing_org['id']
                logger.info(f"🏢 Using existing organization: {existing_org['name']} ({organization_id})")
            else:
                created_org = db_client.insert_organization(organization_data)
                organization_id = created_org['id']
                logger.info(f"🏢 Created new organization: {created_org['name']} ({organization_id})")
        except Exception as e:
            logger.warning(f"⚠️ Organization handling failed: {e}, proceeding without organization")
            organization_id = None
        
        # 2. GUARDAR USUARIO (si no existe)
        user_data = {
            'name': client_info.get('name', 'Usuario No Especificado'),
            'email': client_info.get('requester_email'),
            'phone': client_info.get('requester_phone'),
            'position': client_info.get('requester_position'),
            'organization_id': organization_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Buscar usuario existente por email o crear nuevo
            existing_user = None
            if user_data['email']:
                existing_user = db_client.get_user_by_email(user_data['email'])
            
            if existing_user:
                user_id = existing_user['id']
                logger.info(f"👤 Using existing user: {existing_user['name']} ({user_id})")
            else:
                created_user = db_client.insert_user(user_data)
                user_id = created_user['id']
                logger.info(f"👤 Created new user: {created_user['name']} ({user_id})")
        except Exception as e:
            logger.warning(f"⚠️ User handling failed: {e}, proceeding without user")
            user_id = None
        
        # 3. GUARDAR PROYECTO
        project_data = {
            'id': metadata.get('project_id', str(uuid4())),
            'name': project_details.get('title', 'Proyecto Sin Título'),
            'description': project_details.get('description', ''),
            'project_type': project_details.get('industry_domain', 'general'),
            'status': 'analyzed',  # Estado después del análisis
            'priority': 3,  # Por defecto
            'organization_id': organization_id,
            'user_id': user_id,
            'project_number': f"PROJ-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}",
            'requirements': requirements.get('functional', []) + requirements.get('technical', []),
            'estimated_budget': budget_financial.get('estimated_budget'),
            'budget_range_min': budget_financial.get('budget_range_min'),
            'budget_range_max': budget_financial.get('budget_range_max'),
            'currency': budget_financial.get('currency', 'USD'),
            'delivery_date': timeline.get('delivery_date'),
            'start_date': timeline.get('start_date'),
            'end_date': timeline.get('end_date'),
            'location': location_logistics.get('primary_location'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        try:
            saved_project = db_client.insert_project(project_data)
            project_id = saved_project['id']
            logger.info(f"📋 Project saved successfully: {saved_project['name']} ({project_id})")
        except Exception as e:
            logger.error(f"❌ Failed to save project: {e}")
            project_id = project_data['id']  # Use original ID as fallback
        
        # 4. GUARDAR PRODUCTOS/SERVICIOS (PROJECT_ITEMS)
        if requested_products:
            try:
                project_items_data = []
                for product in requested_products:
                    item_data = {
                        'project_id': project_id,
                        'name': product.get('product_name', 'Producto Sin Nombre'),
                        'description': product.get('specifications', ''),
                        'quantity': product.get('quantity', 1),
                        'unit': product.get('unit', 'unidades'),
                        'unit_price': 0.0,  # Será actualizado posteriormente
                        'category': product.get('category', 'general'),
                        'created_at': datetime.utcnow().isoformat()
                    }
                    project_items_data.append(item_data)
                
                saved_items = db_client.insert_project_items(project_id, project_items_data)
                logger.info(f"📦 Saved {len(saved_items)} project items")
            except Exception as e:
                logger.error(f"❌ Failed to save project items: {e}")
        
        # 5. GUARDAR CONTEXTO DEL AGENTE
        try:
            agent_context = budy_agent.get_project_context()
            if agent_context:
                context_data = {
                    'project_id': project_id,
                    'context_type': 'analysis_result',
                    'context_data': agent_context,
                    'created_at': datetime.utcnow().isoformat()
                }
                db_client.insert_project_context(project_id, context_data)
                logger.info(f"🧠 Saved BudyAgent context for project {project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save agent context: {e}")
        
        # 6. GUARDAR ESTADO DEL WORKFLOW
        try:
            workflow_state = {
                'project_id': project_id,
                'step_name': 'momento_1_analysis',
                'step_status': 'completed',
                'step_data': {
                    'model_used': budy_result.get('metadata', {}).get('model_used', 'gpt-4o'),
                    'generation_time': budy_result.get('metadata', {}).get('generation_time', 0),
                    'confidence_level': budy_result.get('quality_assessment', {}).get('confidence_level', 0),
                    'extraction_method': 'budy_agent_v1.0'
                },
                'created_at': datetime.utcnow().isoformat()
            }
            db_client.insert_workflow_state(workflow_state)
            logger.info(f"🔄 Saved workflow state for MOMENTO 1")
        except Exception as e:
            logger.error(f"❌ Failed to save workflow state: {e}")
        
        # 🔄 CONVERTIR A FORMATO LEGACY CON ADAPTADOR UNIFICADO
        unified_adapter = UnifiedLegacyAdapter()
        
        # Agregar IDs de BD al resultado de BudyAgent para el adaptador
        budy_result['database_ids'] = {
            'project_id': project_id,
            'organization_id': organization_id,
            'user_id': user_id
        }
        
        # Usar API unificada del nuevo adaptador
        legacy_result = unified_adapter.convert_to_format(budy_result, target_format='rfx')
        
        # Asegurar que el ID del proyecto esté en la respuesta legacy
        legacy_result['id'] = project_id
        legacy_result['project_id'] = project_id
        
        logger.info(f"🔄 Successfully converted to legacy format with BD integration")
        logger.info(f"✅ Complete RFX processing finished: Analysis + BD Save + Legacy Format")
        
        # 📤 RESPUESTA EN FORMATO TOTALMENTE COMPATIBLE CON FRONTEND EXISTENTE
        return jsonify(legacy_result), 200
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
                "costo_total": record.get("actual_cost", 0.0) or 0.0,
                "currency": record.get("currency", "USD")  # ✅ Incluir moneda en listado
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
        
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
        
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
        
        # 🆕 Get generated document HTML content for frontend
        generated_html = None
        if proposals:
            # Get the most recent proposal/document
            latest_proposal = proposals[0]  # proposals are ordered by created_at DESC
            # Extract HTML content from the document
            html_content = latest_proposal.get("content_html") or latest_proposal.get("content")
            if html_content:
                generated_html = html_content
                logger.info(f"✅ Including HTML content for RFX {rfx_id}: {len(html_content)} characters")
            else:
                logger.warning(f"⚠️ No HTML content found in latest proposal for RFX {rfx_id}")
        else:
            logger.info(f"ℹ️ No proposals found for RFX {rfx_id}, no HTML to include")
        
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
            "currency": rfx_record.get("currency", "USD"),  # ✅ Exponer moneda del RFX
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
            "cargo_solicitante": requester_data.get("position", metadata.get("cargo_solicitante", "")),
            
            # 🆕 Generated HTML content for frontend preview
            "generated_html": generated_html
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


@rfx_bp.route("/<rfx_id>/products", methods=["GET"])
def get_rfx_products(rfx_id: str):
    """Get products for a specific RFX with currency information"""
    try:
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Verificar que el RFX existe y obtener su moneda
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        # Obtener productos
        products = db_client.get_rfx_products(rfx_id)
        rfx_currency = rfx_record.get("currency", "USD")
        
        # Formatear productos con información de moneda
        products_response = []
        for product in products:
            product_data = {
                "id": product.get("id"),
                "product_name": product.get("product_name"),
                "description": product.get("description"),
                "category": product.get("category"),
                "quantity": product.get("quantity"),
                "unit_of_measure": product.get("unit_of_measure"),
                "estimated_unit_price": product.get("estimated_unit_price"),
                "total_estimated_cost": product.get("total_estimated_cost"),
                "specifications": product.get("specifications"),
                "is_mandatory": product.get("is_mandatory"),
                "notes": product.get("notes"),
                "created_at": product.get("created_at"),
                "updated_at": product.get("updated_at")
            }
            products_response.append(product_data)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(products)} products for RFX {rfx_id}",
            "data": {
                "rfx_id": rfx_id,
                "currency": rfx_currency,  # ✅ Moneda del RFX
                "products": products_response,
                "total_items": len(products),
                "subtotal": sum(p.get("total_estimated_cost", 0) or 0 for p in products)
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting products for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve RFX products",
            "error": str(e)
        }), 500


@rfx_bp.route("/<rfx_id>/currency", methods=["PUT"])
def update_rfx_currency(rfx_id: str):
    """Update currency for an RFX (simple version - no conversions)"""
    try:
        logger.info(f"🔄 Updating currency for RFX: {rfx_id}")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        new_currency = data.get("currency")
        
        if not new_currency:
            return jsonify({
                "status": "error",
                "message": "Currency is required",
                "error": "Missing currency field"
            }), 400
        
        # Basic currency validation (ISO 4217 format)
        new_currency = new_currency.upper().strip()
        if len(new_currency) != 3 or not new_currency.isalpha():
            return jsonify({
                "status": "error",
                "message": "Invalid currency format. Use 3-letter ISO code (e.g., USD, EUR, MXN)",
                "error": "Invalid currency format"
            }), 400
        
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        # Verificar que el RFX existe
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
        if not rfx_record:
            return jsonify({
                "status": "error",
                "message": "RFX not found",
                "error": f"No RFX found with ID: {rfx_id}"
            }), 404
        
        current_currency = rfx_record.get("currency", "USD")
        
        # Check if currency is already the same
        if current_currency == new_currency:
            return jsonify({
                "status": "success",
                "message": f"RFX currency is already {new_currency}",
                "data": {
                    "rfx_id": rfx_id,
                    "currency": new_currency,
                    "changed": False
                }
            }), 200
        
        # Check if RFX has products with prices (for warnings, not blocking)
        products = db_client.get_rfx_products(rfx_id)
        priced_products_count = sum(1 for p in products if p.get("estimated_unit_price", 0) > 0)
        
        # Prepare warnings for response
        warnings = []
        if priced_products_count > 0:
            warnings.append("prices_not_converted")
            logger.warning(f"⚠️ Currency change for RFX {rfx_id}: {priced_products_count} products have prices that will NOT be converted")
        
        # Update currency in database
        try:
            response = db_client.client.table("rfx_v2")\
                .update({"currency": new_currency})\
                .eq("id", rfx_id)\
                .execute()
            
            if response.data:
                # Log the change in history with pricing context
                history_data = {
                    "rfx_id": rfx_id,
                    "event_type": "currency_updated",
                    "description": f"Currency changed from {current_currency} to {new_currency}. {priced_products_count} products with prices were not converted.",
                    "old_values": {"currency": current_currency},
                    "new_values": {
                        "currency": new_currency, 
                        "priced_products_count": priced_products_count,
                        "conversion_applied": False
                    },
                    "performed_by": "user"
                }
                db_client.insert_rfx_history(history_data)
                
                logger.info(f"✅ Currency updated for RFX {rfx_id}: {current_currency} → {new_currency}")
                
                # Prepare response with warnings
                response_data = {
                    "rfx_id": rfx_id,
                    "old_currency": current_currency,
                    "new_currency": new_currency,
                    "changed": True,
                    "priced_products_count": priced_products_count
                }
                
                if warnings:
                    response_data["warnings"] = warnings
                
                message = f"Currency updated successfully from {current_currency} to {new_currency}"
                if priced_products_count > 0:
                    message += f". {priced_products_count} product prices were NOT converted and require manual adjustment."
                
                return jsonify({
                    "status": "success",
                    "message": message,
                    "data": response_data
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "Failed to update currency",
                    "error": "Database update returned no data"
                }), 500
                
        except Exception as db_error:
            logger.error(f"❌ Database error updating currency: {db_error}")
            return jsonify({
                "status": "error",
                "message": "Database error while updating currency",
                "error": str(db_error)
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating currency for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update RFX currency",
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
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
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
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
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
            # Use modern method and ensure legacy format
            project_record = db_client.get_project_by_id(rfx_id)
            if project_record:
                # Convert to RFX format for backward compatibility
                from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
                adapter = UnifiedLegacyAdapter()
                rfx_record = adapter.convert_to_format(project_record, 'rfx')
            else:
                rfx_record = None
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
        # Use modern method and ensure legacy format
        project_record = db_client.get_project_by_id(rfx_id)
        if project_record:
            # Convert to RFX format for backward compatibility
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            rfx_record = adapter.convert_to_format(project_record, 'rfx')
        else:
            rfx_record = None
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


@rfx_bp.route("/latest", methods=["GET"])
def get_latest_rfx():
    """
    🎯 Get the latest 10 RFX records ordered by creation date (most recent first)
    
    This endpoint returns the first 10 most recent RFX records with optimized 
    load-more pagination information for infinite scroll UI patterns.
    
    Query Parameters:
    - limit (optional): Number of items to return (default: 10, max: 50)
    
    Response:
    - data: Array of RFX records
    - pagination: Load-more pagination info with next_offset
    """
    try:
        # Get and validate limit parameter
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            return jsonify({
                "status": "error",
                "message": "Invalid limit parameter",
                "error": "Limit must be between 1 and 50"
            }), 400
        
        logger.info(f"🎯 Getting latest {limit} RFX records")
        
        # Get data from database using optimized method
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        rfx_records = db_client.get_latest_rfx(limit=limit, offset=0)
        
        # Format response data with consistent structure
        latest_items = []
        for record in rfx_records:
            # Extract company and requester data from V2.0 schema
            company_data = record.get("companies", {}) or {}
            requester_data = record.get("requesters", {}) or {}
            metadata = record.get("metadata_json", {}) or {}
            
            # Map V2.0 status to frontend format
            rfx_status = record.get("status", "in_progress")
            display_status = "completed" if rfx_status == "completed" else "In progress"
            
            # Get structured products count
            structured_products = db_client.get_rfx_products(record["id"])
            products_count = len(structured_products) if structured_products else len(record.get("requested_products", []))
            
            latest_item = {
                # Core RFX data
                "id": record["id"],
                "rfxId": record["id"],  # Legacy compatibility
                "title": record.get("title", f"RFX: {company_data.get('name', 'Unknown Company')}"),
                "description": record.get("description"),
                
                # Company and requester info
                "client": requester_data.get("name", metadata.get("requester_name", "Unknown Requester")),
                "company_name": company_data.get("name", metadata.get("company_name", "Unknown Company")),
                "requester_name": requester_data.get("name", metadata.get("requester_name", "Unknown Requester")),
                "requester_email": requester_data.get("email", metadata.get("email", "")),
                
                # Status and classification
                "status": display_status,
                "rfx_status": rfx_status,  # Raw status
                "tipo": record.get("rfx_type", "catering"),
                "priority": record.get("priority", "medium"),
                
                # Financial data
                "estimated_budget": record.get("estimated_budget", 0.0) or 0.0,
                "actual_cost": record.get("actual_cost", 0.0) or 0.0,
                "costo_total": record.get("actual_cost", 0.0) or 0.0,  # Legacy compatibility
                "currency": record.get("currency", "MXN"),
                
                # Location and logistics
                "location": record.get("location") or record.get("event_location", ""),
                "event_city": record.get("event_city"),
                "event_state": record.get("event_state"),
                
                # Products info
                "numero_productos": products_count,
                "products_count": products_count,
                
                # Dates
                "date": record.get("created_at"),
                "created_at": record.get("created_at"),
                "received_at": record.get("received_at"),
                "delivery_date": record.get("delivery_date"),
                "submission_deadline": record.get("submission_deadline"),
                
                # Additional metadata
                "requirements": record.get("requirements"),
                "requirements_confidence": record.get("requirements_confidence")
            }
            latest_items.append(latest_item)
        
        # Build pagination info for load-more pattern
        pagination_info = {
            "offset": 0,
            "limit": limit,
            "total_items": len(latest_items),
            "has_more": len(latest_items) == limit,  # If we got exactly limit items, there might be more
            "next_offset": limit if len(latest_items) == limit else None
        }
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(latest_items)} latest RFX records",
            "data": latest_items,
            "pagination": pagination_info,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(latest_items)} latest RFX records")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting latest RFX: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve latest RFX records",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@rfx_bp.route("/load-more", methods=["GET"])
def load_more_rfx():
    """
    ⏩ Load more RFX records for infinite scroll pagination
    
    This endpoint loads additional RFX records starting from a given offset,
    perfect for "Load More" button functionality in the frontend.
    
    Query Parameters:
    - offset (required): Number of items to skip
    - limit (optional): Number of items to return (default: 10, max: 50)
    
    Response:
    - data: Array of RFX records
    - pagination: Updated pagination info with next_offset
    """
    try:
        # Get and validate parameters
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 10))
        
        # Validate parameters
        if offset < 0:
            return jsonify({
                "status": "error",
                "message": "Invalid offset parameter",
                "error": "Offset must be >= 0"
            }), 400
        
        if limit < 1 or limit > 50:
            return jsonify({
                "status": "error",
                "message": "Invalid limit parameter", 
                "error": "Limit must be between 1 and 50"
            }), 400
        
        logger.info(f"⏩ Loading more RFX records: offset={offset}, limit={limit}")
        
        # Get data from database
        from ..core.database import get_database_client
        db_client = get_database_client()
        
        rfx_records = db_client.get_latest_rfx(limit=limit, offset=offset)
        
        if not rfx_records:
            logger.info(f"📄 No more RFX records found at offset {offset}")
            return jsonify({
                "status": "success",
                "message": "No more records available",
                "data": [],
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total_items": 0,
                    "has_more": False,
                    "next_offset": None
                },
                "timestamp": datetime.now().isoformat()
            }), 200
        
        # Format response data (same format as /latest endpoint)
        more_items = []
        for record in rfx_records:
            company_data = record.get("companies", {}) or {}
            requester_data = record.get("requesters", {}) or {}
            metadata = record.get("metadata_json", {}) or {}
            
            rfx_status = record.get("status", "in_progress")
            display_status = "completed" if rfx_status == "completed" else "In progress"
            
            structured_products = db_client.get_rfx_products(record["id"])
            products_count = len(structured_products) if structured_products else len(record.get("requested_products", []))
            
            more_item = {
                # Core RFX data
                "id": record["id"],
                "rfxId": record["id"],
                "title": record.get("title", f"RFX: {company_data.get('name', 'Unknown Company')}"),
                "description": record.get("description"),
                
                # Company and requester info  
                "client": requester_data.get("name", metadata.get("requester_name", "Unknown Requester")),
                "company_name": company_data.get("name", metadata.get("company_name", "Unknown Company")),
                "requester_name": requester_data.get("name", metadata.get("requester_name", "Unknown Requester")),
                "requester_email": requester_data.get("email", metadata.get("email", "")),
                
                # Status and classification
                "status": display_status,
                "rfx_status": rfx_status,
                "tipo": record.get("rfx_type", "catering"),
                "priority": record.get("priority", "medium"),
                
                # Financial data
                "estimated_budget": record.get("estimated_budget", 0.0) or 0.0,
                "actual_cost": record.get("actual_cost", 0.0) or 0.0,
                "costo_total": record.get("actual_cost", 0.0) or 0.0,
                "currency": record.get("currency", "MXN"),
                
                # Location and logistics
                "location": record.get("location") or record.get("event_location", ""),
                "event_city": record.get("event_city"),
                "event_state": record.get("event_state"),
                
                # Products info
                "numero_productos": products_count,
                "products_count": products_count,
                
                # Dates
                "date": record.get("created_at"),
                "created_at": record.get("created_at"),
                "received_at": record.get("received_at"),
                "delivery_date": record.get("delivery_date"),
                "submission_deadline": record.get("submission_deadline"),
                
                # Additional metadata
                "requirements": record.get("requirements"),
                "requirements_confidence": record.get("requirements_confidence")
            }
            more_items.append(more_item)
        
        # Build updated pagination info
        pagination_info = {
            "offset": offset,
            "limit": limit,
            "total_items": len(more_items),
            "has_more": len(more_items) == limit,  # If we got exactly limit items, there might be more
            "next_offset": offset + limit if len(more_items) == limit else None
        }
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(more_items)} more RFX records",
            "data": more_items,
            "pagination": pagination_info,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(more_items)} more RFX records (offset: {offset})")
        return jsonify(response), 200
        
    except ValueError as ve:
        logger.error(f"❌ Parameter validation error: {ve}")
        return jsonify({
            "status": "error", 
            "message": "Invalid parameters",
            "error": str(ve),
            "timestamp": datetime.now().isoformat()
        }), 400
        
    except Exception as e:
        logger.error(f"❌ Error loading more RFX records: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to load more RFX records",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
