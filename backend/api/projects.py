"""
🚀 Projects API Endpoints - Modern project management API aligned with budy-ai-schema
Migrated from RFX system to general-purpose project management
Compatible with budy-ai-schema.sql (organizations, projects, project_items, quotes, etc.)
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
from typing import Optional, Dict, Any, List
import logging
import time
import random
from datetime import datetime
from uuid import UUID, uuid4

from backend.models.project_models import (
    ProjectInput, ProjectResponse, ProjectTypeEnum, ProjectStatusEnum,
    ProjectModel, OrganizationModel, UserModel, ProjectItemModel,
    # Legacy aliases for backward compatibility
    RFXInput, RFXResponse
)
from backend.core.config import get_file_upload_config
from backend.core.database import get_database_client
from backend.services.project_processor import get_project_processor
from backend.services.ai_context_service import get_ai_context_service

logger = logging.getLogger(__name__)

# Create blueprint with new endpoint structure
projects_bp = Blueprint("projects_api", __name__, url_prefix="/api/projects")


@projects_bp.route("/", methods=["POST"])
def create_project():
    """
    🎯 Create a new project (modern replacement for RFX processing)
    Supports: FILE PROCESSING | TEXT CONTENT | MIXED INPUT
    
    Use cases:
    1. File-only: Upload documents → process files
    2. Text-only: Send extracted content → process text  
    3. Mixed: Upload files + text → process everything
    """
    try:
        logger.info(f"🔍 Create Project Request received")
        logger.info(f"📄 Request files: {list(request.files.keys())}")
        logger.info(f"📝 Request form keys: {list(request.form.keys())}")
        
        # Get file upload configuration
        upload_config = get_file_upload_config()
        
        # Extract files and text content (flexible input)
        files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'pdf_file' in request.files:
            files = [request.files['pdf_file']]
            
        text_content = request.form.get('text_content', '').strip()
        extracted_content = request.form.get('contenido_extraido', '').strip()  # Legacy support
        
        # Use either text_content or legacy field
        content_text = text_content or extracted_content
        
        logger.info(f"📄 Files count: {len(files)}")
        if content_text:
            logger.info(f"📝 Text content length: {len(content_text)} characters")
        
        # Validation: Must have at least files OR text
        has_files = any(f and f.filename for f in files)
        has_text = bool(content_text)
        
        if not has_files and not has_text:
            logger.error("❌ No content provided - neither files nor text")
            return jsonify({
                "status": "error",
                "message": "Must provide files or text content",
                "error": "Content required"
            }), 400
        
        logger.info(f"✅ Content validation passed - has_files: {has_files}, has_text: {has_text}")

        # Process files if provided
        upload_config = get_file_upload_config()
        extra_exts = ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.csv', '.png', '.jpg', '.jpeg', '.tiff', '.zip']
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
                    return jsonify({
                        "status": "error", 
                        "message": f"File type not allowed. Supported: {', '.join(upload_config.allowed_extensions)}", 
                        "error": "Invalid file type"
                    }), 400
                
                content = f.read()
                content_size = len(content)
                total_size += content_size
                
                logger.info(f"📄 FILE READ: '{f.filename}' → {content_size} bytes")
                
                if content_size > upload_config.max_file_size:
                    logger.error(f"❌ FILE TOO LARGE: {f.filename} ({content_size} bytes > {upload_config.max_file_size})")
                    return jsonify({
                        "status": "error", 
                        "message": f"File too large. Maximum size: {upload_config.max_file_size // (1024*1024)}MB", 
                        "error": "File size exceeded"
                    }), 413
                
                valid_files.append({"filename": f.filename, "content": content})
                logger.info(f"✅ FILE VALIDATED: '{f.filename}' ({content_size} bytes) - READY FOR PROCESSING")
            
            logger.info(f"📊 FILES SUMMARY: {len(valid_files)} valid files, total size: {total_size} bytes")

        # Process text content as virtual file if provided
        if has_text:
            project_id_temp = f"PROJECT-{int(time.time())}-{random.randint(1000, 9999)}"
            text_filename = f"{project_id_temp}_text_content.txt"
            text_bytes = content_text.encode('utf-8')
            
            valid_files.append({
                "filename": text_filename,
                "content": text_bytes
            })
            total_size += len(text_bytes)
            logger.info(f"✅ Text content processed as virtual file: {text_filename} ({len(text_bytes)} bytes)")

        # Final validation
        if not valid_files:
            logger.error("❌ No valid content after processing")
            return jsonify({
                "status": "error", 
                "message": "Could not process the provided content", 
                "error": "No valid content"
            }), 400

        # Optional total size limit
        if total_size > getattr(upload_config, "max_total_size", 32*1024*1024):
            return jsonify({
                "status": "error", 
                "message": "Total upload too large. Maximum total size: 32MB", 
                "error": "Total size exceeded"
            }), 413
        
        # Extract project configuration from request
        project_id = request.form.get('id', f"PROJECT-{int(time.time())}-{random.randint(1000, 9999)}")
        project_type = request.form.get('project_type', request.form.get('tipo_rfx', 'catering'))
        organization_id = request.form.get('organization_id', request.form.get('company_id'))
        
        # Create project input (maintain compatibility with legacy RFXInput)
        if project_type in ['catering', 'events', 'consulting', 'construction', 'marketing', 'technology', 'general']:
            project_type_enum = ProjectTypeEnum(project_type)
        else:
            project_type_enum = ProjectTypeEnum.GENERAL
        
        # Crear un project input más completo con la información disponible
        project_input = ProjectInput(
            id=project_id,
            project_type=project_type_enum,
            name=f"Project {project_type} - {project_id[:8]}",
            extracted_content=content_text if has_text else None,
            requirements=content_text if has_text else f"Project created via API upload for {project_type}"
        )

        logger.info(f"🚀 Starting project processing: {project_id} (type: {project_type})")
        logger.info(f"📊 Processing summary: {len(valid_files)} files, total_size: {total_size} bytes")

        # PROCESO COMPLETO CON ANÁLISIS PRIMERO
        try:
            # 1. Obtener instancias de servicios
            project_processor = get_project_processor()
            db_client = get_database_client()
            
            # 2. Crear organización y usuario por defecto si no existen (para development)
            if not organization_id:
                organization_id = _ensure_default_organization(db_client)
            
            default_user_id = _ensure_default_user(db_client, organization_id)
            
            # 3. EJECUTAR ANÁLISIS IA PRIMERO (antes de insertar en BD)
            logger.info(f"🤖 Starting BudyAgent analysis BEFORE project insertion: {project_id}")
            
            # Preparar contenido para análisis
            combined_content = ""
            for file_data in valid_files:
                content_str = file_data["content"].decode('utf-8', errors='ignore') if isinstance(file_data["content"], bytes) else str(file_data["content"])
                combined_content += f"\n--- {file_data['filename']} ---\n{content_str}\n"
            
            # Ejecutar análisis
            metadata = {
                "project_id": project_id,
                "project_type": project_type,
                "files_count": len(valid_files),
                "total_size": total_size,
                "organization_id": organization_id,
                "created_by": default_user_id
            }
            
            # Variable para almacenar resultado del análisis
            analysis_result = None
            
            try:
                # Usar el project processor para análisis completo
                import asyncio
                if asyncio.iscoroutinefunction(project_processor.process_project_documents):
                    analysis_result = asyncio.run(project_processor.process_project_documents(
                        project_input, valid_files, metadata
                    ))
                else:
                    analysis_result = project_processor.process_project_documents(
                        project_input, valid_files, metadata
                    )
                
                logger.info(f"✅ BudyAgent analysis completed for project: {project_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ BudyAgent analysis failed: {e}")
                # Continuar sin análisis - usar datos básicos
                analysis_result = None
            
            # 4. Preparar datos COMPLETOS del proyecto (análisis + básicos)
            complete_project_data = {
                "id": project_id,
                "name": f"Project {project_type} - {project_id[:8]}",
                "description": f"Project created via API upload for {project_type}",
                "project_type": project_type,
                "status": "draft",
                "organization_id": organization_id,
                "created_by": default_user_id,
                "tags": [project_type, "api_upload"],
                "priority": 3
            }
            
            # Enriquecer con datos del análisis IA (si está disponible)
            if analysis_result and hasattr(analysis_result, 'client_name'):
                if analysis_result.client_name:
                    complete_project_data["client_name"] = analysis_result.client_name
                if analysis_result.client_email:
                    complete_project_data["client_email"] = analysis_result.client_email
                if analysis_result.client_phone:
                    complete_project_data["client_phone"] = analysis_result.client_phone
                if analysis_result.client_company:
                    complete_project_data["client_company"] = analysis_result.client_company
                if analysis_result.service_location:
                    complete_project_data["service_location"] = analysis_result.service_location
                if hasattr(analysis_result, 'estimated_scope_size') and analysis_result.estimated_scope_size:
                    complete_project_data["estimated_attendees"] = analysis_result.estimated_scope_size
                if hasattr(analysis_result, 'budget_range_max') and analysis_result.budget_range_max:
                    complete_project_data["estimated_budget"] = analysis_result.budget_range_max
                
                # Actualizar status si se analizó correctamente
                complete_project_data["status"] = "analyzed"
            
            logger.info(f"💾 Inserting COMPLETE project with analysis data: {project_id}")
            inserted_project = db_client.insert_project(complete_project_data)
            logger.info(f"✅ Complete project inserted successfully: {inserted_project.get('id')}")
            
            # 5. Guardar documentos subidos
            if valid_files:
                logger.info(f"📄 Saving {len(valid_files)} documents to database")
                for i, file_data in enumerate(valid_files):
                    document_data = {
                        "project_id": project_id,
                        "filename": file_data["filename"],
                        "original_filename": file_data["filename"],
                        "file_path": f"/uploads/{project_id}/{file_data['filename']}",
                        "file_size_bytes": len(file_data["content"]),
                        "file_type": _get_file_extension(file_data["filename"]),
                        "mime_type": _get_mime_type(file_data["filename"]),
                        "document_type": "attachment",
                        "is_primary": (i == 0),
                        "uploaded_by": default_user_id,
                        "is_processed": True,
                        "processing_status": "completed"
                    }
                    
                    try:
                        saved_doc = db_client.client.table("project_documents").insert(document_data).execute()
                        logger.info(f"✅ Document saved: {file_data['filename']}")
                    except Exception as e:
                        logger.error(f"❌ Failed to save document {file_data['filename']}: {e}")
            
            # 6. Inicializar estado de workflow (usando status del análisis)
            workflow_stage = "intelligent_extraction" if analysis_result else "document_uploaded"
            stage_progress = 60.0 if analysis_result else 25.0
            overall_progress = 60.0 if analysis_result else 25.0
            quality_gates_passed = 4 if analysis_result else 1
            
            workflow_data = {
                "project_id": project_id,
                "current_stage": workflow_stage,
                "stage_progress": stage_progress,
                "overall_progress": overall_progress,
                "requires_human_review": False,
                "quality_score": 0.8,
                "quality_gates_passed": quality_gates_passed,
                "quality_gates_total": 7,
                "workflow_version": "3.0"
            }
            
            try:
                saved_workflow = db_client.client.table("workflow_states").insert(workflow_data).execute()
                logger.info(f"✅ Workflow state initialized: {project_id}")
            except Exception as e:
                logger.error(f"❌ Failed to save workflow state: {e}")
            
            # 7. Guardar contexto de análisis (si está disponible)
            if analysis_result and hasattr(analysis_result, 'context_analysis') and analysis_result.context_analysis:
                context_data = {
                    "project_id": project_id,
                    "detected_project_type": project_type,
                    "complexity_score": getattr(analysis_result, 'requirements_confidence', 0.5),
                    "analysis_confidence": getattr(analysis_result, 'requirements_confidence', 0.5),
                    "analysis_reasoning": "Analysis completed via BudyAgent - project created with complete data",
                    "ai_model_used": "gpt-4o",
                    "key_requirements": [],
                    "implicit_needs": [],
                    "market_context": {},
                    "risk_factors": []
                }
                
                try:
                    saved_context = db_client.client.table("project_context").insert(context_data).execute()
                    logger.info(f"✅ Project context saved: {project_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to save project context: {e}")
            
            # 8. Crear resultado compatible (análisis ya completado)
            processed_result = {
                "id": project_id,
                "project_id": project_id,
                "status": "analyzed" if analysis_result else "basic_processed",
                "extraction_method": "budy_agent_complete_v1.0" if analysis_result else "basic_upload_only",
                
                # Project information from analysis
                "project_title": getattr(analysis_result, 'name', f"Project {project_type} - {project_id[:8]}") if analysis_result else f"Project {project_type} - {project_id[:8]}",
                "project_description": getattr(analysis_result, 'description', f"Project created via API upload for {project_type}") if analysis_result else f"Project created via API upload for {project_type}",
                "project_type": project_type,
                "complexity_score": getattr(analysis_result, 'requirements_confidence', 0.5) if analysis_result else 0.5,
                
                # Client information from analysis
                "client_name": getattr(analysis_result, 'client_name', '') if analysis_result else '',
                "client_company": getattr(analysis_result, 'client_company', '') if analysis_result else '',
                "client_email": getattr(analysis_result, 'client_email', '') if analysis_result else '',
                "client_phone": getattr(analysis_result, 'client_phone', '') if analysis_result else '',
                
                # Timeline from analysis
                "proposal_deadline": getattr(analysis_result, 'proposal_deadline', None) if analysis_result else None,
                "service_start_date": getattr(analysis_result, 'service_start_date', None) if analysis_result else None,
                "service_end_date": getattr(analysis_result, 'service_end_date', None) if analysis_result else None,
                
                # Budget from analysis
                "budget_range_min": getattr(analysis_result, 'budget_range_min', None) if analysis_result else None,
                "budget_range_max": getattr(analysis_result, 'budget_range_max', None) if analysis_result else None,
                "currency": getattr(analysis_result, 'currency', 'USD') if analysis_result else 'USD',
                
                # Location from analysis
                "service_location": getattr(analysis_result, 'service_location', '') if analysis_result else '',
                "service_city": getattr(analysis_result, 'service_city', '') if analysis_result else '',
                "service_state": getattr(analysis_result, 'service_state', '') if analysis_result else '',
                "service_country": getattr(analysis_result, 'service_country', '') if analysis_result else '',
                
                # Processing metadata
                "processing_timestamp": datetime.utcnow().isoformat(),
                "files_processed": len(valid_files),
                "total_size_processed": total_size,
                
                # Success indicators
                "database_saved": True,
                "analysis_completed": bool(analysis_result),
                "workflow_initialized": True,
                "analysis_error": None if analysis_result else "Analysis was skipped or failed"
            }
        
        except Exception as e:
            logger.error(f"❌ Complete project processing failed: {e}")
            
            # ROLLBACK MANUAL: Mark project as failed if it was created
            if 'inserted_project' in locals() and inserted_project and inserted_project.get('id'):
                try:
                    logger.info(f"🔄 Attempting rollback for project: {project_id}")
                    
                    # Update project status to failed
                    rollback_data = {
                        "status": "cancelled",  # ✅ Valor válido del enum project_status_enum
                        "description": f"Project processing failed: {str(e)}",
                        "tags": [project_type, "api_upload", "processing_failed"]
                    }
                    
                    success = db_client.update_project_data(project_id, rollback_data)
                    
                    if success:
                        logger.info(f"✅ Project marked as cancelled due to processing failure: {project_id}")
                        
                        # Log audit event for troubleshooting
                        try:
                            audit_data = {
                                'action': 'update',
                                'table_name': 'projects', 
                                'record_id': project_id,
                                'organization_id': organization_id,
                                'user_id': default_user_id,
                                'action_reason': f'Processing failed: {str(e)}',
                                'new_values': rollback_data
                            }
                            db_client.insert_audit_log(audit_data)
                        except Exception as audit_e:
                            logger.warning(f"⚠️ Failed to log audit event: {audit_e}")
                    else:
                        logger.error(f"❌ Failed to update project status during rollback: {project_id}")
                        
                except Exception as rollback_e:
                    logger.error(f"❌ Rollback failed for project {project_id}: {rollback_e}")
            
            return jsonify({
                "status": "error",
                "message": f"Failed to process project: {str(e)}",
                "error": "Processing failed",
                "project_id": project_id if 'project_id' in locals() else None,
                "rollback_attempted": 'inserted_project' in locals() and inserted_project is not None
            }), 500
        
        # Final success response
        logger.info(f"✅ Project processed successfully: {project_id}")
        
        return jsonify({
            "status": "success",
            "message": "Project processed successfully",
            "data": processed_result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in project creation: {e}")
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error": "Unexpected error"
        }), 500


# Funciones auxiliares para procesamiento de archivos
def _get_file_extension(filename: str) -> str:
    """Obtener extensión del archivo"""
    return filename.split('.')[-1].lower() if '.' in filename else 'unknown'


def _get_mime_type(filename: str) -> str:
    """Obtener tipo MIME basado en la extensión"""
    ext = _get_file_extension(filename)
    mime_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'tiff': 'image/tiff',
        'zip': 'application/zip'
    }
    return mime_types.get(ext, 'application/octet-stream')


# Funciones auxiliares para manejo de organizaciones y usuarios por defecto
def _ensure_default_organization(db_client) -> str:
    """Asegurar que existe una organización por defecto para development"""
    try:
        # Buscar organización por defecto
        org = db_client.get_organization_by_slug("default-dev-org")
        if org:
            logger.info(f"✅ Using existing default organization: {org['id']}")
            return org['id']
        
        # Crear organización por defecto
        org_data = {
            "name": "Default Development Organization",
            "slug": "default-dev-org",
            "plan_type": "free",
            "business_sector": "technology",
            "country_code": "US",
            "language_preference": "es"
        }
        
        created_org = db_client.insert_organization(org_data)
        logger.info(f"✅ Created default organization: {created_org['id']}")
        return created_org['id']
        
    except Exception as e:
        logger.error(f"❌ Failed to ensure default organization: {e}")
        # Fallback: usar UUID por defecto
        return "00000000-0000-0000-0000-000000000001"


def _ensure_default_user(db_client, organization_id: str) -> str:
    """Asegurar que existe un usuario por defecto para development"""
    try:
        # Buscar usuario por defecto
        user = db_client.get_user_by_email("dev@default.local")
        if user:
            logger.info(f"✅ Using existing default user: {user['id']}")
            return user['id']
        
        # Crear usuario por defecto
        user_data = {
            "email": "dev@default.local",
            "password_hash": "dev-password-hash",  # No se usa en development
            "first_name": "Development",
            "last_name": "User",
            "is_active": True,
            "email_verified": True
        }
        
        created_user = db_client.insert_user(user_data)
        
        # Crear relación usuario-organización
        org_user_data = {
            "organization_id": organization_id,
            "user_id": created_user['id'],
            "role": "owner",
            "status": "active",
            "can_create_projects": True,
            "can_manage_users": True
        }
        
        try:
            db_client.client.table("organization_users").insert(org_user_data).execute()
            logger.info(f"✅ Created default user and organization relationship: {created_user['id']}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create organization relationship: {e}")
        
        return created_user['id']
        
    except Exception as e:
        logger.error(f"❌ Failed to ensure default user: {e}")
        # Fallback: usar UUID por defecto
        return "00000000-0000-0000-0000-000000000002"


@projects_bp.route("/recent", methods=["GET"])
def get_recent_projects():
    """Get recent projects for sidebar (limited to 12 items)"""
    try:
        db_client = get_database_client()
        
        # Get last 12 project records for sidebar
        projects = db_client.get_latest_projects(limit=12, offset=0)
        
        # Format for sidebar display
        recent_items = []
        for project in projects:
            project_status = project.get("status", "in_progress")
            status = "completed" if project_status == "completed" else "In progress"
            
            # Extract organization and user info
            organization_data = project.get("organizations", {}) or {}
            user_data = project.get("users", {}) or {}
            
            recent_item = {
                "id": project["id"],
                "title": project.get("title", f"Project: {organization_data.get('name', 'Unknown Organization')}"),
                "client": user_data.get("name", "Unknown User"),
                "date": project["created_at"],
                "status": status,
                "projectId": project["id"],
                # Additional fields for consistency
                "type": project.get("project_type", "other"),
                "number_items": len(project.get("project_items", [])) if project.get("project_items") else 0,
                "estimated_budget": project.get("estimated_budget", 0.0) or 0.0,
                "currency": project.get("currency", "USD")
            }
            recent_items.append(recent_item)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(recent_items)} recent project records",
            "data": recent_items
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting recent projects: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve recent projects",
            "error": str(e)
        }), 500


@projects_bp.route("/history", methods=["GET"])
def get_project_history():
    """Get project processing history with pagination"""
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
        db_client = get_database_client()
        projects = db_client.get_projects_history(limit=limit, offset=offset)
        
        # Format response data
        history_items = []
        for project in projects:
            organization_data = project.get("organizations", {}) or {}
            user_data = project.get("users", {}) or {}
            
            # Map status
            project_status = project.get("status", "in_progress")
            legacy_status = "completed" if project_status == "completed" else "In progress"
            
            # Get items count
            items = db_client.get_project_items(project["id"])
            items_count = len(items) if items else 0
            
            history_item = {
                # New schema fields
                "id": project["id"],
                "organization_id": project.get("organization_id"),
                "created_by": project.get("created_by"),
                "organization_name": organization_data.get("name", "Unknown Organization"),
                "user_name": user_data.get("name", "Unknown User"),
                "project_type": project.get("project_type", "other"),
                "title": project.get("title", f"Project - {project.get('project_type', 'other')}"),
                "status": project_status,
                "priority": project.get("priority", "medium"),
                "delivery_date": project.get("delivery_date"),
                "created_at": project.get("created_at"),
                "estimated_budget": project.get("estimated_budget"),
                "actual_cost": project.get("actual_cost"),
                
                # Legacy compatibility fields  
                "cliente_id": project.get("created_by"),
                "nombre_solicitante": user_data.get("name", "Unknown User"),
                "tipo": project.get("project_type", "other"),
                "fecha_recepcion": project.get("created_at"),
                "costo_total": project.get("actual_cost", 0.0),
                "estado": legacy_status,
                "numero_productos": items_count,
                
                # Organization information
                "organization": {
                    "name": organization_data.get("name", ""),
                    "email": organization_data.get("email", ""),
                    "phone": organization_data.get("phone", "")
                },
                
                # Additional fields for frontend consistency
                "client": user_data.get("name", "Unknown User"),
                "date": project.get("created_at"),
                "projectId": project["id"]
            }
            history_items.append(history_item)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(history_items)} project records",
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
        logger.error(f"❌ Error getting project history: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve project history",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/finalize", methods=["POST"])
def finalize_project(project_id: str):
    """Mark a project as finalized/completed"""
    try:
        db_client = get_database_client()
        
        # Update project status to completed
        result = db_client.update_project_status(project_id, "completed")
        
        if not result:
            return jsonify({
                "status": "error",
                "message": "Project not found or could not be updated",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        response = {
            "status": "success",
            "message": f"Project {project_id} finalized successfully",
            "data": {
                "id": project_id,
                "status": "completed"
            }
        }
        
        logger.info(f"✅ Project finalized successfully: {project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error finalizing project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to finalize project",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>", methods=["GET"])
def get_project_by_id(project_id: str):
    """Get specific project by ID"""
    try:
        db_client = get_database_client()
        
        project_record = db_client.get_project_by_id(project_id)
        
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        # Extract organization and user data
        organization_data = project_record.get("organizations", {}) or {}
        user_data = project_record.get("users", {}) or {}
        
        # Get quotes to determine processing state
        quotes = db_client.get_quotes_by_project(project_id)
        status = "completed" if quotes else "in_progress"
        
        # Get latest quote HTML content for frontend
        generated_html = None
        if quotes:
            latest_quote = quotes[0]  # quotes ordered by created_at DESC
            html_content = latest_quote.get("html_content") or latest_quote.get("content")
            if html_content:
                generated_html = html_content
                logger.info(f"✅ Including HTML content for project {project_id}: {len(html_content)} characters")
        
        # Get project items
        project_items = db_client.get_project_items(project_id)
        items_list = []
        if project_items:
            items_list = [{
                "id": item.get("id", ""),
                "name": item.get("name", ""),  # Schema uses 'name' not 'item_name'
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 0),
                "unit_of_measure": item.get("unit_of_measure", ""),
                "unit_price": item.get("unit_price"),
                "total_price": item.get("total_price")
            } for item in project_items]
        
        project_data = {
            # New schema fields
            "id": project_record["id"],
            "organization_id": project_record.get("organization_id"),
            "created_by": project_record.get("created_by"),
            "project_type": project_record.get("project_type", "other"),
            "title": project_record.get("title", "Project"),
            "description": project_record.get("description", ""),
            "status": project_record.get("status", "in_progress"),
            "priority": project_record.get("priority", "medium"),
            "currency": project_record.get("currency", "USD"),
            "estimated_budget": project_record.get("estimated_budget"),
            "actual_cost": project_record.get("actual_cost"),
            "delivery_date": project_record.get("delivery_date"),
            "created_at": project_record.get("created_at"),
            
            # Legacy compatibility fields
            "tipo": project_record.get("project_type", "other"),
            "estado": status,
            "fecha_recepcion": project_record.get("created_at"),
            "costo_total": project_record.get("actual_cost", 0.0) or 0.0,
            
            # Organization and user information
            "organization_name": organization_data.get("name", ""),
            "organization_email": organization_data.get("email", ""),
            "organization_phone": organization_data.get("phone", ""),
            "user_name": user_data.get("name", ""),
            "user_email": user_data.get("email", ""),
            "user_phone": user_data.get("phone", ""),
            
            # Items/Products
            "items": items_list,
            "products": items_list,  # Legacy compatibility
            
            # Generated content
            "generated_html": generated_html
        }
        
        response = {
            "status": "success",
            "message": "Project retrieved successfully",
            "data": project_data
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve project {project_id}",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/items", methods=["GET"])
def get_project_items(project_id: str):
    """Get items for a specific project with currency information"""
    try:
        db_client = get_database_client()
        
        # Verify project exists and get its currency
        project_record = db_client.get_project_by_id(project_id)
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        # Get project items
        items = db_client.get_project_items(project_id)
        project_currency = project_record.get("currency", "USD")
        
        # Format items response
        items_response = []
        for item in items:
            item_data = {
                "id": item.get("id"),
                "item_name": item.get("name"),  # Map 'name' from schema to 'item_name' for frontend compatibility
                "name": item.get("name"),       # Also include 'name' for consistency
                "description": item.get("description"),
                "category": item.get("category"),
                "quantity": item.get("quantity"),
                "unit_of_measure": item.get("unit_of_measure"),
                "unit_price": item.get("unit_price"),
                "total_price": item.get("total_price"),
                "specifications": item.get("description"),  # Map description to specifications for legacy
                "is_mandatory": item.get("is_included", True),  # Map is_included to is_mandatory for legacy
                "notes": item.get("validation_notes", ""),     # Map validation_notes to notes for legacy
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at")
            }
            items_response.append(item_data)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(items)} items for project {project_id}",
            "data": {
                "project_id": project_id,
                "currency": project_currency,
                "items": items_response,
                "total_items": len(items),
                "subtotal": sum(item.get("total_price", 0) or 0 for item in items)
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting items for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve project items",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/currency", methods=["PUT"])
def update_project_currency(project_id: str):
    """Update currency for a project (simple version - no conversions)"""
    try:
        logger.info(f"🔄 Updating currency for project: {project_id}")
        
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
        
        db_client = get_database_client()
        
        # Verify project exists
        project_record = db_client.get_project_by_id(project_id)
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        current_currency = project_record.get("currency", "USD")
        
        # Check if currency is already the same
        if current_currency == new_currency:
            return jsonify({
                "status": "success",
                "message": f"Project currency is already {new_currency}",
                "data": {
                    "project_id": project_id,
                    "currency": new_currency,
                    "changed": False
                }
            }), 200
        
        # Check if project has items with prices (for warnings)
        items = db_client.get_project_items(project_id)
        priced_items_count = sum(1 for item in items if item.get("unit_price", 0) > 0)
        
        # Update currency
        success = db_client.update_project_data(project_id, {"currency": new_currency})
        
        if success:
            logger.info(f"✅ Currency updated for project {project_id}: {current_currency} → {new_currency}")
            
            response_data = {
                "project_id": project_id,
                "old_currency": current_currency,
                "new_currency": new_currency,
                "changed": True,
                "priced_items_count": priced_items_count
            }
            
            message = f"Currency updated successfully from {current_currency} to {new_currency}"
            if priced_items_count > 0:
                message += f". {priced_items_count} item prices were NOT converted and require manual adjustment."
                response_data["warnings"] = ["prices_not_converted"]
            
            return jsonify({
                "status": "success",
                "message": message,
                "data": response_data
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to update currency",
                "error": "Database update failed"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error updating currency for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update project currency",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/data", methods=["PUT"])
def update_project_data(project_id: str):
    """Update project data (organization, user, request details, etc.)"""
    try:
        logger.info(f"🔄 update_project_data endpoint called for project: {project_id}")
        
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        field_name = data.get("field")
        field_value = data.get("value")
        
        if not field_name:
            return jsonify({
                "status": "error",
                "message": "field name is required",
                "error": "Missing field name"
            }), 400
        
        db_client = get_database_client()
        
        # Verify project exists
        project_record = db_client.get_project_by_id(project_id)
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        # Map frontend fields to their correct location in the new schema
        field_mapping = {
            # Fields that go to users table
            "user_name": "users.first_name",  # Schema uses first_name, last_name not name
            "user_email": "users.email", 
            "user_phone": "users.phone",
            
            # Fields that go to organizations table  
            "organization_name": "organizations.name",
            "organization_email": "organizations.email",  # Schema might not have email in organizations
            "organization_phone": "organizations.phone",   # Schema might not have phone in organizations
            
            # Fields that go directly to projects table (corrected to match schema)
            "delivery_date": "projects.service_date",      # Schema uses service_date not delivery_date
            "location": "projects.service_location",       # Schema uses service_location not location
            "requirements": "projects.description",        # Schema uses description for requirements
            "title": "projects.name",                      # Schema uses name not title
            "description": "projects.description"
        }
        
        db_field = field_mapping.get(field_name)
        if not db_field:
            return jsonify({
                "status": "error",
                "message": f"Field '{field_name}' is not updateable",
                "error": "Invalid field name"
            }), 400
        
        # Categorize fields by destination table
        user_fields = ["user_name", "user_email", "user_phone"]
        organization_fields = ["organization_name", "organization_email", "organization_phone"] 
        project_direct_fields = ["delivery_date", "location", "requirements", "title", "description"]
        
        if field_name in user_fields:
            # Update in users table
            user_id = project_record.get("created_by")
            if not user_id:
                return jsonify({
                    "status": "error",
                    "message": "No user found for this project",
                    "error": "Missing user_id"
                }), 400
            
            # Handle user_name specially (split into first_name and last_name)
            if field_name == "user_name":
                # Split full name into first and last name
                name_parts = field_value.split(' ', 1) if field_value else ['', '']
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                update_data = {
                    "first_name": first_name,
                    "last_name": last_name
                }
                success = db_client.update_user(user_id, update_data)
            else:
                user_field_mapping = {
                    "user_email": "email", 
                    "user_phone": "phone"
                }
                
                db_column = user_field_mapping[field_name]
                success = db_client.update_user(user_id, {db_column: field_value})
            
            if not success:
                return jsonify({
                    "status": "error",
                    "message": "Failed to update user data"
                }), 500
            
        elif field_name in organization_fields:
            # Handle organization fields (note: schema doesn't have email/phone for organizations)
            organization_id = project_record.get("organization_id")
            if not organization_id:
                return jsonify({
                    "status": "error",
                    "message": "No organization found for this project",
                    "error": "Missing organization_id"
                }), 400
            
            if field_name == "organization_name":
                # Only name field exists in organizations table
                success = db_client.update_organization(organization_id, {"name": field_value})
                
                if not success:
                    return jsonify({
                        "status": "error",
                        "message": "Failed to update organization data"
                    }), 500
            else:
                # organization_email and organization_phone don't exist in schema
                return jsonify({
                    "status": "error",
                    "message": f"Field '{field_name}' is not available in the organization schema",
                    "error": "Schema limitation - organization email/phone not supported"
                }), 400
            
        elif field_name in project_direct_fields:
            # Update directly in projects table
            project_field_mapping = {
                "delivery_date": "service_date",      # Schema uses service_date
                "location": "service_location",       # Schema uses service_location
                "requirements": "description",        # Schema uses description
                "title": "name",                      # Schema uses name
                "description": "description"
            }
            
            db_column = project_field_mapping[field_name]
            update_data = {db_column: field_value}
            
            success = db_client.update_project_data(project_id, update_data)
            
            if not success:
                return jsonify({
                    "status": "error",
                    "message": "Failed to update project data"
                }), 500
        else:
            return jsonify({
                "status": "error", 
                "message": f"Field '{field_name}' is not configured for updates",
                "error": "Field not in allowed categories"
            }), 400
        
        # Success response
        response = {
            "status": "success",
            "message": f"Field '{field_name}' updated successfully",
            "data": {
                "project_id": project_id,
                "field": field_name,
                "value": field_value
            }
        }
        
        logger.info(f"✅ Field '{field_name}' updated successfully for project {project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Exception in update_project_data endpoint for {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update project data",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/items/costs", methods=["PUT"])
def update_item_costs(project_id: str):
    """Update unit costs of project items provided by the user"""
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        item_costs = data.get("item_costs", data.get("product_costs", []))  # Support legacy field name
        
        if not item_costs or not isinstance(item_costs, list):
            return jsonify({
                "status": "error",
                "message": "item_costs array is required",
                "error": "Invalid item costs data"
            }), 400
        
        db_client = get_database_client()
        
        # Verify project exists
        project_record = db_client.get_project_by_id(project_id)
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found",
                "error": f"No project found with ID: {project_id}"
            }), 404
        
        # Get real project items for mapping
        real_items = db_client.get_project_items(project_id)
        item_mapping = {}
        
        logger.info(f"🔍 Found {len(real_items)} real items for project {project_id}")
        
        if not real_items:
            return jsonify({
                "status": "error",
                "message": "No items found for this project",
                "error": "Items must be processed and saved before setting costs"
            }), 404
        
        # Create mapping by index for fake IDs like "item-0" 
        for i, real_item in enumerate(real_items):
            fake_id = f"item-{i}"
            item_mapping[fake_id] = real_item["id"]
            # Also map real ID to itself
            item_mapping[real_item["id"]] = real_item["id"]
        
        # Update item costs
        updated_items = []
        for cost_data in item_costs:
            item_id = cost_data.get("item_id", cost_data.get("product_id"))  # Support legacy field
            unit_price = cost_data.get("unit_price")
            
            if not item_id or unit_price is None:
                continue
                
            try:
                unit_price = float(unit_price)
                if unit_price < 0:
                    continue
                
                # Convert fake ID to real ID if needed
                real_item_id = item_mapping.get(item_id, item_id)
                
                # Update item in database with real ID
                success = db_client.update_project_item_cost(project_id, real_item_id, unit_price)
                if success:
                    updated_items.append({
                        "item_id": real_item_id,
                        "original_id": item_id,
                        "unit_price": unit_price
                    })
                else:
                    logger.warning(f"Failed to update item {item_id} -> {real_item_id}")
                    
            except (ValueError, TypeError):
                logger.warning(f"Invalid unit_price for item {item_id}: {unit_price}")
                continue
        
        response = {
            "status": "success",
            "message": f"Costs updated for {len(updated_items)} items",
            "data": {
                "project_id": project_id,
                "updated_items": updated_items
            }
        }
        
        logger.info(f"✅ Item costs updated for project {project_id}: {len(updated_items)} items")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating item costs for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update item costs",
            "error": str(e)
        }), 500


@projects_bp.route("/<project_id>/items/<item_id>", methods=["PUT"])
def update_project_item(project_id: str, item_id: str):
    """Update a specific project item"""
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        field_name = data.get("field")
        field_value = data.get("value")
        
        if not field_name:
            return jsonify({
                "status": "error",
                "message": "field name is required"
            }), 400
        
        db_client = get_database_client()
        
        # Verify project exists
        project_record = db_client.get_project_by_id(project_id)
        if not project_record:
            return jsonify({
                "status": "error",
                "message": "Project not found"
            }), 404
        
        # Map item fields (frontend → backend)
        item_field_mapping = {
            # Spanish names (frontend) → English names (database schema)
            "nombre": "name",           # Schema uses 'name' not 'item_name'
            "cantidad": "quantity",
            "unidad": "unit_of_measure",
            "precio_unitario": "unit_price",
            "precio_total": "total_price",
            "descripcion": "description",
            "notas": "validation_notes",  # Schema uses 'validation_notes' not 'notes'
            
            # English names for compatibility
            "item_name": "name",        # Map item_name to name in schema
            "name": "name",
            "quantity": "quantity", 
            "unit_of_measure": "unit_of_measure",
            "unit_price": "unit_price",
            "total_price": "total_price",
            "description": "description",
            "notes": "validation_notes"  # Map to actual schema field
        }
        
        db_field = item_field_mapping.get(field_name)
        if not db_field:
            return jsonify({
                "status": "error",
                "message": f"Field '{field_name}' is not updateable for items"
            }), 400
        
        # Validate and convert data types by field
        processed_value = field_value
        try:
            if db_field in ["quantity"]:
                processed_value = int(field_value) if field_value is not None else 0
            elif db_field in ["unit_price", "total_price"]:
                processed_value = float(field_value) if field_value is not None else None
        except (ValueError, TypeError) as e:
            return jsonify({
                "status": "error",
                "message": f"Invalid value for field '{field_name}'. Expected number but got '{field_value}'",
                "error": "Data type validation failed"
            }), 400
        
        # Update item
        try:
            update_data = {db_field: processed_value}
            success = db_client.update_project_item(item_id, project_id, update_data)
            
            if success:
                logger.info(f"✅ Item updated: {item_id} field '{field_name}' = '{processed_value}'")
                return jsonify({
                    "status": "success",
                    "message": f"Item field '{field_name}' updated successfully",
                    "data": {
                        "project_id": project_id,
                        "item_id": item_id,
                        "field": field_name,
                        "value": processed_value
                    }
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "Item not found or update failed",
                    "details": f"Item {item_id} not found in project {project_id}"
                }), 404
                
        except Exception as db_e:
            logger.error(f"❌ Database error updating item: {db_e}")
            return jsonify({
                "status": "error",
                "message": "Failed to update item",
                "error": str(db_e)
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Exception in update_project_item: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500


@projects_bp.route("/latest", methods=["GET"])
def get_latest_projects():
    """Get the latest projects with load-more pagination"""
    try:
        # Get and validate limit parameter
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            return jsonify({
                "status": "error",
                "message": "Invalid limit parameter",
                "error": "Limit must be between 1 and 50"
            }), 400
        
        logger.info(f"🎯 Getting latest {limit} projects")
        
        # Get data from database
        db_client = get_database_client()
        projects = db_client.get_latest_projects(limit=limit, offset=0)
        
        # Format response data
        latest_items = []
        for project in projects:
            # Extract organization and user data
            organization_data = project.get("organizations", {}) or {}
            user_data = project.get("users", {}) or {}
            
            # Map status
            project_status = project.get("status", "in_progress")
            display_status = "completed" if project_status == "completed" else "In progress"
            
            # Get items count
            items = db_client.get_project_items(project["id"])
            items_count = len(items) if items else 0
            
            latest_item = {
                # Core project data
                "id": project["id"],
                "projectId": project["id"],  # Legacy compatibility
                "title": project.get("title", f"Project: {organization_data.get('name', 'Unknown Organization')}"),
                "description": project.get("description"),
                
                # Organization and user info
                "client": user_data.get("name", "Unknown User"),
                "organization_name": organization_data.get("name", "Unknown Organization"),
                "user_name": user_data.get("name", "Unknown User"),
                "user_email": user_data.get("email", ""),
                
                # Status and classification
                "status": display_status,
                "project_status": project_status,
                "type": project.get("project_type", "other"),
                "priority": project.get("priority", "medium"),
                
                # Financial data
                "estimated_budget": project.get("estimated_budget", 0.0) or 0.0,
                "actual_cost": project.get("actual_cost", 0.0) or 0.0,
                "currency": project.get("currency", "USD"),
                
                # Items info
                "number_items": items_count,
                "items_count": items_count,
                
                # Dates
                "date": project.get("created_at"),
                "created_at": project.get("created_at"),
                "delivery_date": project.get("delivery_date")
            }
            latest_items.append(latest_item)
        
        # Build pagination info
        pagination_info = {
            "offset": 0,
            "limit": limit,
            "total_items": len(latest_items),
            "has_more": len(latest_items) == limit,
            "next_offset": limit if len(latest_items) == limit else None
        }
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(latest_items)} latest projects",
            "data": latest_items,
            "pagination": pagination_info,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(latest_items)} latest projects")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting latest projects: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve latest projects",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@projects_bp.route("/load-more", methods=["GET"])
def load_more_projects():
    """Load more projects for infinite scroll pagination"""
    try:
        # Get and validate parameters
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 10))
        
        if offset < 0 or limit < 1 or limit > 50:
            return jsonify({
                "status": "error",
                "message": "Invalid parameters",
                "error": "Offset must be >= 0, limit between 1-50"
            }), 400
        
        logger.info(f"⏩ Loading more projects: offset={offset}, limit={limit}")
        
        # Get data from database
        db_client = get_database_client()
        projects = db_client.get_latest_projects(limit=limit, offset=offset)
        
        if not projects:
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
        for project in projects:
            organization_data = project.get("organizations", {}) or {}
            user_data = project.get("users", {}) or {}
            
            project_status = project.get("status", "in_progress")
            display_status = "completed" if project_status == "completed" else "In progress"
            
            items = db_client.get_project_items(project["id"])
            items_count = len(items) if items else 0
            
            more_item = {
                # Core project data
                "id": project["id"],
                "projectId": project["id"],
                "title": project.get("title", f"Project: {organization_data.get('name', 'Unknown Organization')}"),
                "description": project.get("description"),
                
                # Organization and user info  
                "client": user_data.get("name", "Unknown User"),
                "organization_name": organization_data.get("name", "Unknown Organization"),
                "user_name": user_data.get("name", "Unknown User"),
                "user_email": user_data.get("email", ""),
                
                # Status and classification
                "status": display_status,
                "project_status": project_status,
                "type": project.get("project_type", "other"),
                "priority": project.get("priority", "medium"),
                
                # Financial data
                "estimated_budget": project.get("estimated_budget", 0.0) or 0.0,
                "actual_cost": project.get("actual_cost", 0.0) or 0.0,
                "currency": project.get("currency", "USD"),
                
                # Items info
                "number_items": items_count,
                "items_count": items_count,
                
                # Dates
                "date": project.get("created_at"),
                "created_at": project.get("created_at"),
                "delivery_date": project.get("delivery_date")
            }
            more_items.append(more_item)
        
        # Build pagination info
        pagination_info = {
            "offset": offset,
            "limit": limit,
            "total_items": len(more_items),
            "has_more": len(more_items) == limit,
            "next_offset": offset + limit if len(more_items) == limit else None
        }
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(more_items)} more projects",
            "data": more_items,
            "pagination": pagination_info,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(more_items)} more projects (offset: {offset})")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error loading more projects: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to load more projects",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


def _convert_project_model_to_legacy_format(project_model):
    """
    Convert new ProjectModel to legacy format for frontend compatibility
    """
    from backend.models.project_models import ProjectModel
    
    # Base structure for legacy compatibility
    legacy_format = {
        "id": str(project_model.id) if project_model.id else None,
        "project_id": str(project_model.id) if project_model.id else None,
        "status": "processed",
        "extraction_method": "budy_agent_v1.0",
        
        # Project basic information
        "project_title": project_model.name or "",
        "project_description": project_model.description or "",
        "project_type": project_model.project_type.value if hasattr(project_model.project_type, 'value') else str(project_model.project_type) if project_model.project_type else "other",
        "complexity_score": getattr(project_model, 'complexity_score', 0.5),
        
        # Client information
        "client_name": project_model.client_name or "",
        "client_company": project_model.client_company or "",
        "client_email": project_model.client_email or "",
        "client_phone": project_model.client_phone or "",
        
        # Timeline
        "proposal_deadline": project_model.proposal_deadline.isoformat() if project_model.proposal_deadline else None,
        "service_start_date": project_model.service_start_date.isoformat() if project_model.service_start_date else None,
        "service_end_date": project_model.service_end_date.isoformat() if project_model.service_end_date else None,
        
        # Budget
        "budget_range_min": project_model.budget_range_min,
        "budget_range_max": project_model.budget_range_max,
        "currency": project_model.currency or "USD",
        
        # Location
        "service_location": project_model.service_location or "",
        "service_city": project_model.service_city or "",
        "service_state": project_model.service_state or "",
        "service_country": project_model.service_country or "",
        
        # Scope
        "estimated_scope_size": project_model.estimated_scope_size,
        "scope_unit": project_model.scope_unit or "",
        "service_category": project_model.service_category or "",
        "target_audience": project_model.target_audience or "",
        
        # Requirements and analysis
        "requirements": project_model.requirements or "",
        "requirements_confidence": project_model.requirements_confidence or 0.5,
        
        # Context analysis (if available)
        "context_analysis": getattr(project_model, 'context_analysis', {}),
        
        # Metadata
        "metadata": project_model.metadata_json or {},
        
        # Timestamps
        "created_at": project_model.created_at.isoformat() if project_model.created_at else None,
        "updated_at": project_model.updated_at.isoformat() if project_model.updated_at else None,
        
        # Additional fields for compatibility
        "ready_for_review": True,
        "processing_status": "completed",
        "ai_analysis_available": bool(project_model.context_analysis)
    }
    
    return legacy_format


def _is_allowed_file(filename: str, allowed_extensions: list) -> bool:
    """Check if file extension is allowed"""
    if not filename:
        return False
    
    file_extension = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return file_extension in allowed_extensions


# ========================
# LEGACY COMPATIBILITY ENDPOINTS
# ========================

# For backward compatibility with existing RFX API calls
@projects_bp.route("/rfx-compat/<rfx_id>", methods=["GET"])
def get_rfx_compatibility(rfx_id: str):
    """
    🔄 Legacy compatibility endpoint for RFX API calls
    Maps old RFX endpoints to new project structure
    """
    logger.info("📡 Legacy RFX compatibility endpoint called, mapping to project endpoint")
    return get_project_by_id(rfx_id)


@projects_bp.route("/webhook", methods=["POST"])
def project_webhook_compatibility():
    """
    🔄 Backward compatibility webhook endpoint
    Redirects to the new create project endpoint for existing integrations
    """
    logger.info("📡 Legacy webhook endpoint called, redirecting to new create project endpoint")
    return create_project()


# ========================
# 🧠 AI CONTEXTUAL ANALYSIS ENDPOINTS (DÍA 6)
# ========================

@projects_bp.route("/<project_id>/analyze-context", methods=["POST"])
def analyze_project_context(project_id):
    """
    🆕 NUEVA FUNCIONALIDAD: Análisis contextual del proyecto
    Implementación completa del Día 6 según implementation_plan_a.md
    """
    try:
        logger.info(f"🧠 Starting context analysis for project: {project_id}")
        
        db_client = get_database_client()
        ai_context_service = get_ai_context_service()
        
        # Obtener proyecto
        project_result = db_client.get_project_by_id(project_id)
        if not project_result:
            return jsonify({
                "status": "error", 
                "message": "Project not found",
                "error_code": "PROJECT_NOT_FOUND"
            }), 404
        
        # Convertir a ProjectInput para análisis
        project_input = ProjectInput(**project_result)
        
        # Obtener documentos relacionados si están disponibles
        documents_text = request.json.get('documents_text', '') if request.is_json else ''
        
        # Análisis contextual con IA (usar asyncio para correr función async)
        start_time = time.time()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        context_analysis = loop.run_until_complete(
            ai_context_service.analyze_project_context(
                project=project_input,
                documents_text=documents_text,
                project_id=project_id
            )
        )
        
        # Calcular duración
        processing_duration = time.time() - start_time
        context_analysis['analysis_metadata']['processing_duration_seconds'] = round(processing_duration, 2)
        
        # Generar workflow inteligente
        workflow_steps = loop.run_until_complete(
            ai_context_service.generate_workflow_steps(
                project_id=project_id,
                context_analysis=context_analysis
            )
        )
        
        logger.info(f"✅ Context analysis completed in {processing_duration:.2f}s")
        
        return jsonify({
            "status": "success",
            "message": "Context analysis completed successfully",
            "data": {
                "project_id": project_id,
                "context_analysis": context_analysis,
                "workflow_steps": workflow_steps,
                "recommendations": _generate_actionable_recommendations(context_analysis),
                "next_steps": _determine_next_steps(workflow_steps),
                "processing_time": processing_duration
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in context analysis: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Context analysis failed: {str(e)}",
            "error_code": "CONTEXT_ANALYSIS_FAILED"
        }), 500


@projects_bp.route("/<project_id>/workflow", methods=["GET"])
def get_project_workflow(project_id):
    """
    🔄 Obtener workflow actual del proyecto
    """
    try:
        db_client = get_database_client()
        
        # Verificar que el proyecto existe
        project_result = db_client.get_project_by_id(project_id)
        if not project_result:
            return jsonify({
                "status": "error",
                "message": "Project not found"
            }), 404
        
        # Obtener pasos del workflow desde BD
        try:
            workflow_steps = db_client.table('workflow_steps')\
                .select('*')\
                .eq('project_id', project_id)\
                .order('step_number')\
                .execute()
            
            steps_data = workflow_steps.data if workflow_steps.data else []
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch workflow from modern schema: {e}")
            steps_data = []
        
        # Calcular progreso
        total_steps = len(steps_data)
        completed_steps = len([s for s in steps_data if s.get('status') == 'completed'])
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Determinar próximo paso
        next_step = None
        for step in steps_data:
            if step.get('status') == 'pending':
                next_step = step
                break
        
        return jsonify({
            "status": "success",
            "data": {
                "project_id": project_id,
                "workflow_steps": steps_data,
                "progress": {
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "progress_percentage": round(progress_percentage, 1),
                    "current_status": "in_progress" if next_step else "completed"
                },
                "next_step": next_step,
                "estimated_remaining_time": _calculate_remaining_time(steps_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting workflow: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get workflow: {str(e)}"
        }), 500


@projects_bp.route("/<project_id>/workflow/<int:step_number>", methods=["POST"])
def update_workflow_step(project_id, step_number):
    """
    ✅ Actualizar estado de un paso del workflow
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "JSON data required"
            }), 400
        
        new_status = data.get('status')
        step_data = data.get('step_data', {})
        
        if new_status not in ['pending', 'in_progress', 'completed', 'skipped', 'error']:
            return jsonify({
                "status": "error",
                "message": "Invalid status. Must be: pending, in_progress, completed, skipped, or error"
            }), 400
        
        db_client = get_database_client()
        
        # Actualizar paso en BD
        try:
            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if new_status == 'completed':
                update_data['completed_at'] = datetime.utcnow().isoformat()
            elif new_status == 'in_progress':
                update_data['started_at'] = datetime.utcnow().isoformat()
            
            if step_data:
                update_data['output_data'] = step_data
            
            result = db_client.table('workflow_steps')\
                .update(update_data)\
                .eq('project_id', project_id)\
                .eq('step_number', step_number)\
                .execute()
            
            if not result.data:
                return jsonify({
                    "status": "error",
                    "message": "Workflow step not found"
                }), 404
            
        except Exception as e:
            logger.warning(f"⚠️ Could not update workflow in modern schema: {e}")
            return jsonify({
                "status": "error",
                "message": "Database update failed"
            }), 500
        
        logger.info(f"✅ Workflow step {step_number} updated to {new_status}")
        
        return jsonify({
            "status": "success",
            "message": f"Workflow step {step_number} updated to {new_status}",
            "data": result.data[0] if result.data else {}
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating workflow step: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to update workflow step: {str(e)}"
        }), 500


@projects_bp.route("/<project_id>/context", methods=["GET"])
def get_project_context(project_id):
    """
    📊 Obtener análisis contextual guardado del proyecto
    """
    try:
        db_client = get_database_client()
        
        # Verificar que el proyecto existe
        project_result = db_client.get_project_by_id(project_id)
        if not project_result:
            return jsonify({
                "status": "error",
                "message": "Project not found"
            }), 404
        
        # Obtener contexto desde BD
        try:
            context_result = db_client.table('project_context')\
                .select('*')\
                .eq('project_id', project_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not context_result.data:
                return jsonify({
                    "status": "error",
                    "message": "No context analysis found for this project"
                }), 404
            
            context_data = context_result.data[0]
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch context from modern schema: {e}")
            return jsonify({
                "status": "error",
                "message": "Context data not available"
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "project_id": project_id,
                "context_analysis": context_data.get('context_data', {}),
                "last_updated": context_data.get('created_at'),
                "context_type": context_data.get('context_type', 'ai_analysis')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting project context: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get project context: {str(e)}"
        }), 500


# ========================
# 🧠 HELPER FUNCTIONS FOR AI CONTEXTUAL ENDPOINTS
# ========================

def _generate_actionable_recommendations(context_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Genera recomendaciones accionables basadas en análisis contextual"""
    
    industry = context_analysis.get("industry_analysis", {}).get("detected_industry", "general")
    complexity_level = context_analysis.get("complexity_analysis", {}).get("complexity_level", "medium")
    
    recommendations = {
        "immediate_actions": [],
        "strategic_considerations": [],
        "risk_mitigations": [],
        "optimization_opportunities": []
    }
    
    # Recomendaciones por industria
    if industry == "catering":
        recommendations["immediate_actions"].extend([
            "Confirm guest count and dietary restrictions",
            "Verify venue accessibility and kitchen facilities",
            "Review service timeline and setup requirements"
        ])
        recommendations["strategic_considerations"].extend([
            "Consider seasonal menu pricing",
            "Plan for service staff coordination",
            "Include equipment and logistics costs"
        ])
    elif industry == "construction":
        recommendations["immediate_actions"].extend([
            "Conduct site survey and feasibility assessment",
            "Verify permits and regulatory requirements",
            "Review technical specifications and materials"
        ])
        recommendations["strategic_considerations"].extend([
            "Factor in seasonal construction constraints",
            "Plan for material procurement lead times",
            "Include safety and compliance costs"
        ])
    elif industry == "it_services":
        recommendations["immediate_actions"].extend([
            "Define technical architecture and stack",
            "Assess integration requirements",
            "Plan development methodology and timeline"
        ])
        recommendations["strategic_considerations"].extend([
            "Consider scalability and maintenance",
            "Plan for testing and quality assurance",
            "Include ongoing support and updates"
        ])
    
    # Ajustes por complejidad
    if complexity_level == "high":
        recommendations["risk_mitigations"].extend([
            "Implement staged delivery approach",
            "Increase stakeholder communication frequency",
            "Add buffer time for unexpected challenges",
            "Consider bringing in additional expertise"
        ])
        recommendations["optimization_opportunities"].extend([
            "Break project into smaller, manageable phases",
            "Implement rigorous change management process",
            "Consider premium pricing for high complexity"
        ])
    elif complexity_level == "low":
        recommendations["optimization_opportunities"].extend([
            "Streamline approval processes",
            "Consider bulk pricing efficiencies", 
            "Automate routine tasks where possible"
        ])
    
    return recommendations

def _determine_next_steps(workflow_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Determina próximos pasos basado en workflow"""
    
    if not workflow_steps:
        return {
            "action": "create_workflow",
            "description": "Generate workflow steps for this project",
            "priority": "high"
        }
    
    # Encontrar próximo paso pendiente
    next_pending = None
    for step in workflow_steps:
        if step.get('status') == 'pending':
            next_pending = step
            break
    
    if next_pending:
        return {
            "action": "execute_step",
            "step_number": next_pending.get('step_number'),
            "step_name": next_pending.get('step_name'),
            "description": next_pending.get('description', ''),
            "requires_human_input": next_pending.get('requires_human_input', False),
            "estimated_duration": next_pending.get('estimated_duration_minutes', 0),
            "priority": "high" if next_pending.get('requires_human_input') else "medium"
        }
    
    # Si todos están completos
    completed_count = len([s for s in workflow_steps if s.get('status') == 'completed'])
    if completed_count == len(workflow_steps):
        return {
            "action": "project_ready",
            "description": "All workflow steps completed - project ready for next phase",
            "priority": "low"
        }
    
    return {
        "action": "review_workflow",
        "description": "Review workflow status and resolve any blocked steps",
        "priority": "medium"
    }

def _calculate_remaining_time(workflow_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula tiempo restante estimado"""
    
    pending_steps = [s for s in workflow_steps if s.get('status') == 'pending']
    
    if not pending_steps:
        return {
            "estimated_minutes": 0,
            "estimated_hours": 0,
            "status": "completed"
        }
    
    total_minutes = sum(step.get('estimated_duration_minutes', 10) for step in pending_steps)
    
    return {
        "estimated_minutes": total_minutes,
        "estimated_hours": round(total_minutes / 60, 1),
        "pending_steps_count": len(pending_steps),
        "status": "in_progress"
    }
