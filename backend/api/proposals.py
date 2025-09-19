"""
📄 Proposals/Quotes API Endpoints - Modern quote management system
Aligned with budy-ai-schema.sql (quotes table)
Maintains backward compatibility with legacy proposal endpoints
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
import asyncio
import logging
import time
import random
from typing import Optional, Dict, Any
from uuid import UUID

# Updated imports for new schema
from backend.models.proposal_models import (
    QuoteRequest, QuoteResponse, QuoteModel, QuoteNotes,
    # Legacy aliases for backward compatibility
    ProposalRequest, ProposalResponse, PropuestaGenerada, NotasPropuesta,
    # Helper functions
    map_legacy_quote_request
)
from backend.core.database import get_database_client
from backend.services.budy_agent import get_budy_agent  # NEW: BudyAgent integration
from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter  # UPDATED: Unified adapter
from uuid import uuid4
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint with enhanced functionality
proposals_bp = Blueprint("proposals_api", __name__, url_prefix="/api/proposals")


@proposals_bp.route("/generate", methods=["POST"])
def generate_proposal():
    """
    🎯 Generate commercial quote based on processed project data
    Modern version using quotes table (budy-ai-schema.sql)
    Maintains backward compatibility with legacy proposal format
    """
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        logger.info(f"🔍 Quote generation request received: {list(data.keys())}")
        
        # Handle legacy request format
        if 'rfx_id' in data:
            logger.info("🔄 Converting legacy proposal request to quote format")
            data = map_legacy_quote_request(data)
        
        # Validate request using Pydantic
        try:
            quote_request = QuoteRequest(**data)
        except ValidationError as e:
            logger.error(f"❌ Quote request validation failed: {e}")
            return jsonify({
                "status": "error",
                "message": "Invalid request data",
                "error": str(e)
            }), 400
        
        # Get project/RFX data from database (support both new and legacy)
        db_client = get_database_client()
        
        # Try new projects table first, then fall back to legacy RFX
        if hasattr(quote_request, 'project_id'):
            project_data = db_client.get_project_by_id(quote_request.project_id)
            project_id = quote_request.project_id
        else:
            # Legacy support: convert rfx_id to project lookup using modern method
            project_data = db_client.get_project_by_id(data.get('rfx_id', ''))
            project_id = data.get('rfx_id', '')
        
        if not project_data:
            return jsonify({
                "status": "error",
                "message": f"Project not found: {project_id}",
                "error": "Project data required for quote generation"
            }), 404
        
        # Get real unit costs from database
        item_costs = []
        project_items = db_client.get_project_items(project_id) if hasattr(db_client, 'get_project_items') else db_client.get_rfx_products(project_id)
        
        if project_items:
            item_costs = [item.get("unit_price", item.get("estimated_unit_price", 0)) for item in project_items]
            logger.info(f"🔍 Using user-provided costs from database: {len(item_costs)} items")
        else:
            # Fallback to request costs if no items in database
            item_costs = getattr(quote_request, 'itemized_costs', [])
            logger.warning(f"⚠️ No items found in database, using request costs: {len(item_costs)} items")
        
        # Map database data to expected format for generation service
        try:
            from backend.utils.data_mappers import map_rfx_data_for_proposal
            project_data_mapped = map_rfx_data_for_proposal(project_data, project_items)
        except ImportError:
            # If mapper doesn't exist, use data as-is
            project_data_mapped = project_data
            logger.warning("⚠️ Data mapper not available, using raw project data")
        
        # 🤖 GENERAR PRESUPUESTO CON BUDY AGENT - MOMENTO 3
        logger.info(f"🤖 Starting quote generation with BudyAgent (MOMENTO 3)")
        
        # Obtener BudyAgent
        budy_agent = get_budy_agent()
        
        # Verificar que tenemos contexto del MOMENTO 1
        agent_context = budy_agent.get_project_context()
        if not agent_context:
            logger.warning("⚠️ No BudyAgent context found, this may affect quote quality")
        
        # Preparar datos confirmados por el usuario
        confirmed_data = {
            'project_id': project_id,
            'project_data': project_data_mapped,
            'item_costs': item_costs,
            'user_notes': getattr(quote_request, 'notes', {}),
            'service_modality': getattr(quote_request, 'service_modality', 'standard'),
            'confirmed_at': datetime.utcnow().isoformat()
        }
        
        # Preparar configuración de pricing
        pricing_config = {
            'currency': 'USD',  # Default, puede ser configurado
            'include_coordination': True,
            'coordination_rate': 0.15,
            'include_tax': False,
            'tax_rate': 0.0,
            'margin_target': 0.20,
            'payment_terms': '30 días',
            'validity_days': 30
        }
        
        # Ejecutar BudyAgent MOMENTO 3: Generación de presupuesto
        try:
            budy_quote_result = asyncio.run(budy_agent.generate_quote(confirmed_data, pricing_config))
        except Exception as e:
            logger.error(f"❌ BudyAgent quote generation failed: {e}")
            # Fallback a respuesta de error compatible
            return jsonify({
                "status": "error",
                "message": f"Quote generation failed: {str(e)}",
                "error": "budy_agent_generation_failed"
            }), 500
        
        logger.info(f"✅ BudyAgent MOMENTO 3 completed successfully")
        
        # 🗄️ GUARDAR QUOTE EN BUDY-AI-SCHEMA DATABASE
        db_client = get_database_client()
        
        try:
            # Extraer datos del quote generado por BudyAgent
            quote_data_raw = budy_quote_result.get('quote', {})
            quote_metadata = quote_data_raw.get('quote_metadata', {})
            pricing_breakdown = quote_data_raw.get('pricing_breakdown', {})
            quote_structure = quote_data_raw.get('quote_structure', {})
            html_content = quote_data_raw.get('html_content', '')
            
            # Preparar datos para tabla QUOTES
            quote_record = {
                'id': quote_metadata.get('quote_number', str(uuid4())),
                'project_id': project_id,
                'title': quote_metadata.get('project_title', 'Presupuesto sin título'),
                'description': f"Presupuesto generado por BudyAgent para {quote_metadata.get('client_name', 'cliente')}",
                'status': 'generated',
                'version': 1,  # Primera versión
                'total_amount': pricing_breakdown.get('total', quote_metadata.get('total_amount', 0.0)),
                'currency': quote_metadata.get('currency', 'USD'),
                'tax_amount': pricing_breakdown.get('tax', 0.0),
                'discount_amount': 0.0,  # No aplica descuentos por defecto
                'subtotal': pricing_breakdown.get('subtotal', 0.0),
                'valid_until': quote_metadata.get('valid_until'),
                'notes': f"Generado con BudyAgent v1.0 - Complejidad: {quote_metadata.get('complexity_level', 'medium')}",
                'template_used': 'budy_agent_standard',
                'generation_data': {
                    'model_used': budy_quote_result.get('metadata', {}).get('model_used', 'gpt-4o'),
                    'generation_time': budy_quote_result.get('metadata', {}).get('generation_time', 0),
                    'budy_agent_version': '1.0',
                    'momento_3_timestamp': datetime.utcnow().isoformat(),
                    'quote_structure': quote_structure,
                    'pricing_breakdown': pricing_breakdown,
                    'recommendations': quote_data_raw.get('recommendations', [])
                },
                'html_content': html_content,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Guardar quote en BD
            saved_quote = db_client.insert_quote(quote_record)
            quote_id = saved_quote['id']
            logger.info(f"💰 Quote saved to database: {quote_id}")
            
            # Actualizar estado del proyecto a 'quoted'
            try:
                db_client.update_project_status(project_id, 'quoted')
                logger.info(f"📋 Project status updated to 'quoted'")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update project status: {e}")
            
            # Guardar estado del workflow - MOMENTO 3
            try:
                workflow_state = {
                    'project_id': project_id,
                    'step_name': 'momento_3_generation',
                    'step_status': 'completed',
                    'step_data': {
                        'quote_id': quote_id,
                        'model_used': budy_quote_result.get('metadata', {}).get('model_used', 'gpt-4o'),
                        'generation_time': budy_quote_result.get('metadata', {}).get('generation_time', 0),
                        'total_amount': quote_record['total_amount'],
                        'currency': quote_record['currency'],
                        'generation_method': 'budy_agent_v1.0'
                    },
                    'created_at': datetime.utcnow().isoformat()
                }
                db_client.insert_workflow_state(workflow_state)
                logger.info(f"🔄 Saved workflow state for MOMENTO 3")
            except Exception as e:
                logger.error(f"❌ Failed to save workflow state: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save quote to database: {e}")
            # Continuar con adaptador legacy incluso si BD falla
            quote_id = quote_metadata.get('quote_number', 'UNKNOWN')
        
        # 🔄 CONVERTIR A FORMATO LEGACY CON ADAPTADOR UNIFICADO
        unified_adapter = UnifiedLegacyAdapter()
        
        # Agregar project_id y quote_id al resultado para el adaptador
        budy_quote_result['project_id'] = project_id
        budy_quote_result['quote_id'] = quote_id
        
        # Convertir a formato legacy usando adaptador unificado
        legacy_proposal = unified_adapter.convert_to_format(budy_quote_result, target_format='proposal')
        
        # Estructurar respuesta API compatible con frontend
        response_data = {
            'status': budy_quote_result.get('status', 'success'),
            'message': 'Quote generated successfully with BudyAgent',
            'data': {
                'id': legacy_proposal.get('id'),
                'project_id': legacy_proposal.get('project_id'),
                'rfx_id': legacy_proposal.get('rfx_id'),  # Legacy compatibility
                'quote': legacy_proposal,
                'download_url': legacy_proposal.get('download_url'),
                'pdf_url': legacy_proposal.get('pdf_url'),
                'metadata': {
                    'generation_method': 'budy_agent_v1.0',
                    'momento_3_completed': True,
                    'context_used': True,
                    'generation_time': legacy_proposal.get('generation_time', 0.0),
                    'quality_indicators': legacy_proposal.get('quality_indicators', {})
                }
            }
        }
        
        # Asegurar que los IDs estén en la respuesta
        response_data['data']['id'] = quote_id
        response_data['data']['quote_id'] = quote_id
        response_data['data']['project_id'] = project_id
        
        logger.info(f"🔄 Successfully converted quote to legacy API format with BD integration")
        logger.info(f"✅ Complete quote generation finished: BudyAgent + BD Save + Legacy Format")
        logger.info(f"💰 Quote ID: {quote_id} | Project ID: {project_id}")
        
        return jsonify(response_data), 200
        
    except ValidationError as e:
        logger.error(f"❌ Validation error: {e}")
        return jsonify({
            "status": "error",
            "message": "Data validation failed",
            "error": str(e)
        }), 400
        
    except ValueError as e:
        logger.error(f"❌ Processing error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error": "Quote generation failed"
        }), 422
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in quote generation: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": "An unexpected error occurred"
        }), 500


@proposals_bp.route("/<quote_id>", methods=["GET"])
def get_proposal(quote_id: str):
    """
    Get specific quote/proposal by ID
    Modern endpoint using quotes table with legacy compatibility
    """
    try:
        db_client = get_database_client()
        
        # Try new quotes table first, then fall back to legacy documents
        quote_data = None
        if hasattr(db_client, 'get_quote_by_id'):
            quote_data = db_client.get_quote_by_id(quote_id)
        
        # Fallback to legacy documents table
        if not quote_data and hasattr(db_client, 'get_document_by_id'):
            quote_data = db_client.get_document_by_id(quote_id)
            logger.info(f"📚 Using legacy document data for quote {quote_id}")
        
        if not quote_data:
            return jsonify({
                "status": "error",
                "message": "Quote not found",
                "error": f"No quote found with ID: {quote_id}"
            }), 404
        
        # Modern response format with legacy compatibility
        response = {
            "status": "success",
            "message": "Quote retrieved successfully",
            "data": {
                "id": quote_data["id"],
                "project_id": quote_data.get("project_id", quote_data.get("rfx_id")),
                "rfx_id": quote_data.get("project_id", quote_data.get("rfx_id")),  # Legacy compatibility
                "quote_number": quote_data.get("quote_number"),
                "status": quote_data.get("status", "draft"),
                "html_content": quote_data.get("html_content", quote_data.get("content_html", "")),
                "content_html": quote_data.get("html_content", quote_data.get("content_html", "")),  # Legacy compatibility
                "content_markdown": quote_data.get("content_markdown", ""),  # Legacy compatibility
                "subtotal": quote_data.get("subtotal", 0.0),
                "total_amount": quote_data.get("total_amount", quote_data.get("total_cost", 0.0)),
                "total_cost": quote_data.get("total_amount", quote_data.get("total_cost", 0.0)),  # Legacy compatibility
                "currency": quote_data.get("currency", "USD"),
                "valid_until": quote_data.get("valid_until"),
                "created_at": quote_data.get("created_at", ""),
                "generated_at": quote_data.get("generated_at", quote_data.get("created_at", "")),
                "download_url": f"/api/download/{quote_id}",
                "pdf_url": f"/api/download/{quote_id}"  # Legacy compatibility
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error retrieving quote {quote_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve quote {quote_id}",
            "error": str(e)
        }), 500


@proposals_bp.route("/rfx/<project_id>/proposals", methods=["GET"])
def get_proposals_by_rfx(project_id: str):
    """
    Get all quotes/proposals for a specific project/RFX
    Modern endpoint using quotes table with legacy compatibility
    """
    try:
        db_client = get_database_client()
        
        # Try new quotes table first
        quotes = None
        if hasattr(db_client, 'get_quotes_by_project'):
            quotes = db_client.get_quotes_by_project(project_id)
            
        # Fallback to legacy proposals table
        if not quotes and hasattr(db_client, 'get_proposals_by_rfx_id'):
            quotes = db_client.get_proposals_by_rfx_id(project_id)
            logger.info(f"📚 Using legacy proposals data for project {project_id}")
        
        if not quotes:
            quotes = []
        
        quotes_data = []
        for quote in quotes:
            quote_item = {
                "id": quote["id"],
                "project_id": quote.get("project_id", quote.get("rfx_id")),
                "rfx_id": quote.get("project_id", quote.get("rfx_id")),  # Legacy compatibility
                "quote_number": quote.get("quote_number"),
                "status": quote.get("status", "draft"),
                "generation_method": quote.get("generation_method", "automatic"),
                "document_type": quote.get("document_type", "quote"),  # Legacy compatibility
                "subtotal": quote.get("subtotal", 0.0),
                "total_amount": quote.get("total_amount", quote.get("total_cost", 0.0)),
                "total_cost": quote.get("total_amount", quote.get("total_cost", 0.0)),  # Legacy compatibility
                "currency": quote.get("currency", "USD"),
                "valid_until": quote.get("valid_until"),
                "created_at": quote.get("created_at", ""),
                "generated_at": quote.get("generated_at", quote.get("created_at", "")),
                "sent_at": quote.get("sent_at"),
                "viewed_at": quote.get("viewed_at"),
                "download_url": f"/api/download/{quote['id']}",
                "pdf_url": f"/api/download/{quote['id']}"  # Legacy compatibility
            }
            quotes_data.append(quote_item)
        
        response = {
            "status": "success",
            "message": f"Found {len(quotes_data)} quotes for project {project_id}",
            "data": quotes_data,
            "pagination": {
                "total_items": len(quotes_data),
                "page": 1,
                "limit": len(quotes_data)
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error retrieving quotes for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve quotes for project {project_id}",
            "error": str(e)
        }), 500


# ========================
# NEW MODERN QUOTE ENDPOINTS
# ========================

@proposals_bp.route("/quotes", methods=["GET"])
def get_quotes():
    """Get all quotes with pagination (modern endpoint)"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        # Validate pagination
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({
                "status": "error",
                "message": "Invalid pagination parameters",
                "error": "Page must be >= 1, limit between 1-100"
            }), 400
        
        db_client = get_database_client()
        
        # Get quotes with pagination
        if hasattr(db_client, 'get_all_quotes'):
            quotes = db_client.get_all_quotes(limit=limit, offset=offset)
        else:
            # Fallback for legacy system
            quotes = []
            logger.warning("⚠️ get_all_quotes method not available, returning empty list")
        
        # Format quotes data
        quotes_data = []
        for quote in quotes:
            quote_item = {
                "id": quote["id"],
                "project_id": quote.get("project_id"),
                "organization_id": quote.get("organization_id"),
                "quote_number": quote.get("quote_number"),
                "status": quote.get("status", "draft"),
                "subtotal": quote.get("subtotal", 0.0),
                "total_amount": quote.get("total_amount", 0.0),
                "currency": quote.get("currency", "USD"),
                "valid_until": quote.get("valid_until"),
                "created_at": quote.get("created_at"),
                "created_by": quote.get("created_by"),
                "sent_at": quote.get("sent_at"),
                "viewed_at": quote.get("viewed_at")
            }
            quotes_data.append(quote_item)
        
        response = {
            "status": "success",
            "message": f"Retrieved {len(quotes_data)} quotes",
            "data": quotes_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": len(quotes_data),
                "has_more": len(quotes_data) == limit
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error retrieving quotes: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve quotes",
            "error": str(e)
        }), 500


@proposals_bp.route("/quotes/<quote_id>/status", methods=["PUT"])
def update_quote_status(quote_id: str):
    """Update quote status (modern endpoint)"""
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        new_status = data.get("status")
        
        if not new_status:
            return jsonify({
                "status": "error",
                "message": "Status is required"
            }), 400
        
        # Validate status values
        valid_statuses = ["draft", "generated", "sent", "viewed", "accepted", "rejected", "expired", "cancelled"]
        if new_status not in valid_statuses:
            return jsonify({
                "status": "error",
                "message": f"Invalid status. Valid values: {', '.join(valid_statuses)}"
            }), 400
        
        db_client = get_database_client()
        
        # Update quote status
        if hasattr(db_client, 'update_quote_status'):
            success = db_client.update_quote_status(quote_id, new_status)
        else:
            # Fallback for legacy system
            success = False
            logger.warning("⚠️ update_quote_status method not available")
        
        if success:
            response = {
                "status": "success",
                "message": f"Quote status updated to {new_status}",
                "data": {
                    "quote_id": quote_id,
                    "status": new_status
                }
            }
            return jsonify(response), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to update quote status",
                "error": "Quote not found or update failed"
            }), 404
        
    except Exception as e:
        logger.error(f"❌ Error updating quote status {quote_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update quote status",
            "error": str(e)
        }), 500


# ========================
# LEGACY COMPATIBILITY ENDPOINTS
# ========================

@proposals_bp.route("/legacy/<proposal_id>", methods=["GET"])
def get_legacy_proposal(proposal_id: str):
    """
    Legacy compatibility endpoint for old proposal format
    """
    logger.info(f"📚 Legacy proposal endpoint called for ID: {proposal_id}")
    return get_proposal(proposal_id)
