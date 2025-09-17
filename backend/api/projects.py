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
        if project_type in ['catering', 'events', 'consulting', 'supply_chain', 'other']:
            project_type_enum = ProjectTypeEnum(project_type)
        else:
            project_type_enum = ProjectTypeEnum.OTHER
        
        project_input = ProjectInput(
            id=project_id,
            project_type=project_type_enum,
            organization_id=organization_id
        )

        logger.info(f"🚀 Starting project processing: {project_id} (type: {project_type})")
        logger.info(f"📊 Processing summary: {len(valid_files)} files, total_size: {total_size} bytes")

        # Use legacy RFX processor service for now (will be migrated separately)
        from backend.services.rfx_processor import RFXProcessorService
        processor_service = RFXProcessorService()
        
        # Create legacy RFXInput for compatibility
        legacy_rfx_input = RFXInput(
            id=project_id,
            rfx_type=project_type  # This will be mapped appropriately
        )
        
        # Process through legacy service (returns RFXProcessed)
        processed_result = processor_service.process_rfx_case(legacy_rfx_input, valid_files)
        
        # Map legacy result to new project response
        project_response = ProjectResponse(
            status="success",
            message="Project data extracted and processed successfully. Review the extracted data and set item costs to generate quotes.",
            data=processed_result,  # For now, keep the legacy structure
            quote_id=None,  # No automatic quote generation
            quote_url=None  # User will generate quotes manually
        )
        
        logger.info(f"✅ Project processed successfully: {project_id}")
        return jsonify({
            "status": "success", 
            "data": processed_result.model_dump(mode='json')
        }), 200
        
    except Exception as e:
        logger.exception("❌ Error processing project")
        return jsonify({
            "status": "error", 
            "message": str(e), 
            "error": "internal"
        }), 500


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
                "name": item.get("item_name", ""),
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
                "item_name": item.get("item_name"),
                "description": item.get("description"),
                "category": item.get("category"),
                "quantity": item.get("quantity"),
                "unit_of_measure": item.get("unit_of_measure"),
                "unit_price": item.get("unit_price"),
                "total_price": item.get("total_price"),
                "specifications": item.get("specifications"),
                "is_mandatory": item.get("is_mandatory"),
                "notes": item.get("notes"),
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
            "user_name": "users.name",
            "user_email": "users.email", 
            "user_phone": "users.phone",
            
            # Fields that go to organizations table  
            "organization_name": "organizations.name",
            "organization_email": "organizations.email",
            "organization_phone": "organizations.phone",
            
            # Fields that go directly to projects table
            "delivery_date": "projects.delivery_date",
            "location": "projects.location", 
            "requirements": "projects.requirements",
            "title": "projects.title",
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
            
            user_field_mapping = {
                "user_name": "name",
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
            # Update in organizations table
            organization_id = project_record.get("organization_id")
            if not organization_id:
                return jsonify({
                    "status": "error",
                    "message": "No organization found for this project",
                    "error": "Missing organization_id"
                }), 400
            
            organization_field_mapping = {
                "organization_name": "name",
                "organization_email": "email",
                "organization_phone": "phone"
            }
            
            db_column = organization_field_mapping[field_name]
            success = db_client.update_organization(organization_id, {db_column: field_value})
            
            if not success:
                return jsonify({
                    "status": "error",
                    "message": "Failed to update organization data"
                }), 500
            
        elif field_name in project_direct_fields:
            # Update directly in projects table
            project_field_mapping = {
                "delivery_date": "delivery_date",
                "location": "location", 
                "requirements": "requirements",
                "title": "title",
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
            # Spanish names (frontend) → English names (database)
            "nombre": "item_name",
            "cantidad": "quantity",
            "unidad": "unit_of_measure",
            "precio_unitario": "unit_price",
            "precio_total": "total_price",
            "descripcion": "description",
            "notas": "notes",
            
            # English names for compatibility
            "item_name": "item_name",
            "quantity": "quantity", 
            "unit_of_measure": "unit_of_measure",
            "unit_price": "unit_price",
            "total_price": "total_price",
            "description": "description",
            "notes": "notes"
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
