"""
💰 Pricing Configuration API - Modern pricing management system
Aligned with budy-ai-schema.sql (pricing_configurations table)
Supports both new project-based and legacy RFX-based pricing
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

# Updated imports for new schema
from backend.models.pricing_models import (
    PricingConfigurationModel, PricingCalculationModel, PricingPresetModel,
    # Legacy aliases for backward compatibility
    PricingConfigurationRequest, PricingConfigurationResponse, PricingCalculation,
    # Helper functions
    map_legacy_pricing_request, get_default_presets
)
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

# Create blueprint with enhanced functionality
pricing_bp = Blueprint("pricing_api", __name__, url_prefix="/api/pricing")


@pricing_bp.route("/config/<project_id>", methods=["GET"])
def get_pricing_configuration(project_id: str):
    """
    📋 Get pricing configuration for a project
    Modern endpoint using pricing_configurations table with legacy RFX support
    """
    try:
        logger.info(f"🔍 Getting pricing configuration for project: {project_id}")
        
        db_client = get_database_client()
        
        # Smart lookup: Try new projects table first, then fall back to RFX
        project_record = None
        if hasattr(db_client, 'get_project_by_id'):
            project_record = db_client.get_project_by_id(project_id)
        
        # Fallback to legacy RFX lookup
        if not project_record:
            if hasattr(db_client, 'find_rfx_by_identifier'):
                project_record = db_client.find_rfx_by_identifier(project_id)
                logger.info(f"📚 Using legacy RFX lookup for {project_id}")
            elif hasattr(db_client, 'get_rfx_by_id'):
                project_record = db_client.get_project_by_id(project_id)
                logger.info(f"📚 Using legacy RFX direct lookup for {project_id}")
        
        if not project_record:
            logger.error(f"❌ Project/RFX not found for identifier: {project_id}")
            return jsonify({
                "status": "error",
                "message": f"Project not found for identifier: {project_id}",
                "error": "project_not_found",
                "help": "Provide a valid project ID or RFX ID"
            }), 404
        
        # Extract the actual UUID
        actual_project_id = str(project_record["id"])
        
        # Get pricing configuration from new table
        pricing_config = None
        if hasattr(db_client, 'get_pricing_configuration_by_project'):
            pricing_config = db_client.get_pricing_configuration_by_project(actual_project_id)
        
        # Fallback to legacy pricing service
        if not pricing_config:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                legacy_config = pricing_service.get_rfx_pricing_configuration(actual_project_id)
                
                if legacy_config:
                    # Convert legacy config to new format
                    pricing_config = {
                        "id": None,
                        "project_id": actual_project_id,
                        "pricing_model": "fixed_price",
                        "coordination_enabled": legacy_config.has_coordination(),
                        "coordination_rate": legacy_config.get_coordination_rate(),
                        "cost_per_person_enabled": legacy_config.has_cost_per_person(),
                        "headcount": legacy_config.get_headcount(),
                        "tax_enabled": legacy_config.taxes and legacy_config.taxes.is_enabled if hasattr(legacy_config, 'taxes') else False,
                        "tax_rate": legacy_config.taxes.config_value.tax_rate if hasattr(legacy_config, 'taxes') and legacy_config.taxes else None,
                        "is_active": True,
                        "updated_at": legacy_config.updated_at if hasattr(legacy_config, 'updated_at') else None
                    }
                    logger.info(f"📚 Using legacy pricing configuration for {actual_project_id}")
            except ImportError:
                logger.warning("⚠️ Legacy pricing service not available")
        
        if not pricing_config:
            # Return default configuration structure
            response = {
                "status": "success",
                "message": "No pricing configuration found, returning defaults",
                "data": {
                    "project_id": actual_project_id,
                    "rfx_id": actual_project_id,  # Legacy compatibility
                    "coordination_enabled": False,
                    "coordination_rate": 0.15,
                    "cost_per_person_enabled": False,
                    "headcount": None,
                    "tax_enabled": False,
                    "tax_rate": None,
                    "has_configuration": False
                }
            }
            return jsonify(response), 200
        
        # Get currency from project record  
        project_currency = project_record.get("currency", "USD")
        
        # Convert to response format (supporting both new and legacy fields)
        response_data = {
            "project_id": actual_project_id,
            "rfx_id": actual_project_id,  # Legacy compatibility
            "currency": project_currency,
            "pricing_model": pricing_config.get("pricing_model", "fixed_price"),
            "coordination_enabled": pricing_config.get("coordination_enabled", False),
            "coordination_rate": pricing_config.get("coordination_rate", 0.0),
            "coordination_type": pricing_config.get("coordination_type", "percentage"),
            "cost_per_person_enabled": pricing_config.get("cost_per_person_enabled", False),
            "headcount": pricing_config.get("headcount"),
            "tax_enabled": pricing_config.get("tax_enabled", False),
            "tax_rate": pricing_config.get("tax_rate"),
            "tax_type": pricing_config.get("tax_type", "percentage"),
            "discount_enabled": pricing_config.get("discount_enabled", False),
            "discount_rate": pricing_config.get("discount_rate"),
            "margin_target": pricing_config.get("margin_target"),
            "minimum_margin": pricing_config.get("minimum_margin"),
            "has_configuration": True,
            "last_updated": pricing_config.get("updated_at"),
            "is_active": pricing_config.get("is_active", True)
        }
        
        response = {
            "status": "success",
            "message": "Pricing configuration retrieved successfully",
            "data": response_data
        }
        
        logger.info(f"✅ Pricing configuration retrieved for project {actual_project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing configuration for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/config/<project_id>", methods=["PUT"])
def update_pricing_configuration(project_id: str):
    """
    ⚙️ Update pricing configuration for a project
    Modern endpoint using pricing_configurations table with legacy RFX support
    """
    try:
        logger.info(f"🔄 Updating pricing configuration for project: {project_id}")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        logger.info(f"📡 Received pricing update payload for {project_id}: "
                    f"keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        db_client = get_database_client()
        
        # Smart lookup: Try new projects table first, then fall back to RFX
        project_record = None
        if hasattr(db_client, 'get_project_by_id'):
            project_record = db_client.get_project_by_id(project_id)
        
        # Fallback to legacy RFX lookup
        if not project_record:
            if hasattr(db_client, 'find_rfx_by_identifier'):
                project_record = db_client.find_rfx_by_identifier(project_id)
                logger.info(f"📚 Using legacy RFX lookup for update: {project_id}")
            elif hasattr(db_client, 'get_rfx_by_id'):
                project_record = db_client.get_project_by_id(project_id)
        
        if not project_record:
            logger.error(f"❌ Project/RFX not found for identifier: {project_id}")
            return jsonify({
                "status": "error",
                "message": f"Project not found for identifier: {project_id}",
                "error": "project_not_found",
                "help": "Provide a valid project ID or RFX ID"
            }), 404
        
        # Extract the actual UUID
        actual_project_id = str(project_record["id"])
        
        # Handle legacy data format
        if 'rfx_id' in data:
            logger.info("🔄 Converting legacy pricing request to project format")
            data = map_legacy_pricing_request(data)
        
        # Add project_id to request data
        data["project_id"] = actual_project_id
        
        # Validate request using new Pydantic model
        try:
            pricing_config = PricingConfigurationModel(**data)
        except ValidationError as e:
            logger.error(f"❌ Validation error for pricing configuration: {e}")
            
            # Try legacy validation as fallback
            try:
                pricing_request = PricingConfigurationRequest(**data)
                # Convert legacy request to new format
                pricing_config = PricingConfigurationModel(
                    project_id=actual_project_id,
                    pricing_model=data.get("pricing_model", "fixed_price"),
                    coordination_enabled=pricing_request.coordination_enabled,
                    coordination_rate=pricing_request.coordination_rate or 0.0,
                    headcount=pricing_request.headcount,
                    tax_enabled=pricing_request.taxes_enabled,
                    tax_rate=pricing_request.tax_rate,
                    is_active=True
                )
                logger.info("🔄 Using legacy pricing request format")
            except ValidationError as legacy_e:
                return jsonify({
                    "status": "error",
                    "message": "Invalid request data",
                    "error": f"New format: {str(e)}, Legacy format: {str(legacy_e)}"
                }), 400
        
        # Save/update configuration in new table
        updated_config = None
        if hasattr(db_client, 'upsert_pricing_configuration'):
            updated_config = db_client.upsert_pricing_configuration(pricing_config.model_dump())
        
        # Fallback to legacy service
        if not updated_config:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                
                # Create legacy request format
                legacy_data = {
                    "rfx_id": actual_project_id,
                    "coordination_enabled": pricing_config.coordination_enabled,
                    "coordination_rate": pricing_config.coordination_rate,
                    "cost_per_person_enabled": pricing_config.headcount is not None,
                    "headcount": pricing_config.headcount,
                    "taxes_enabled": pricing_config.tax_enabled,
                    "tax_rate": pricing_config.tax_rate
                }
                legacy_request = PricingConfigurationRequest(**legacy_data)
                
                updated_config = pricing_service.update_rfx_pricing_from_request(legacy_request)
                logger.info("📚 Using legacy pricing service for update")
            except ImportError:
                logger.error("❌ Neither new nor legacy pricing service available")
                return jsonify({
                    "status": "error",
                    "message": "Pricing service not available"
                }), 500
        
        if not updated_config:
            return jsonify({
                "status": "error",
                "message": "Failed to update pricing configuration",
                "error": "Configuration update failed"
            }), 500
        
        # Create modern response format
        response_data = {
            "project_id": actual_project_id,
            "rfx_id": actual_project_id,  # Legacy compatibility
            "pricing_model": pricing_config.pricing_model,
            "coordination_enabled": pricing_config.coordination_enabled,
            "coordination_rate": pricing_config.coordination_rate,
            "headcount": pricing_config.headcount,
            "tax_enabled": pricing_config.tax_enabled,
            "tax_rate": pricing_config.tax_rate,
            "discount_enabled": pricing_config.discount_enabled,
            "discount_rate": pricing_config.discount_rate,
            "is_active": pricing_config.is_active,
            "updated_at": datetime.now().isoformat()
        }
        
        response = {
            "status": "success",
            "message": "Pricing configuration updated successfully",
            "data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Pricing configuration updated for project {actual_project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating pricing configuration for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/calculate/<project_id>", methods=["POST"])
def calculate_pricing(project_id: str):
    """
    🧮 Calculate pricing total for a project applying configurations
    Modern endpoint using pricing_configurations table with legacy RFX support
    """
    try:
        logger.info(f"🧮 Calculating pricing for project: {project_id}")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        base_subtotal = data.get("subtotal", 0.0)
        
        if not isinstance(base_subtotal, (int, float)) or base_subtotal < 0:
            return jsonify({
                "status": "error",
                "message": "Valid subtotal is required",
                "error": "Invalid subtotal value"
            }), 400
        
        db_client = get_database_client()
        
        # Get project record for currency info
        project_record = None
        if hasattr(db_client, 'get_project_by_id'):
            project_record = db_client.get_project_by_id(project_id)
        
        # Fallback to legacy RFX lookup
        if not project_record and hasattr(db_client, 'find_rfx_by_identifier'):
            project_record = db_client.find_rfx_by_identifier(project_id)
        
        project_currency = project_record.get("currency", "USD") if project_record else "USD"
        
        # Calculate pricing using modern approach
        calculation = None
        
        # Try new pricing configuration approach
        if hasattr(db_client, 'get_pricing_configuration_by_project'):
            pricing_config = db_client.get_pricing_configuration_by_project(project_id)
            if pricing_config:
                # Use new PricingConfigurationModel to calculate
                config_model = PricingConfigurationModel(**pricing_config)
                calculation = PricingCalculationModel.calculate_from_config(
                    config_model, float(base_subtotal)
                )
        
        # Fallback to legacy pricing service
        if not calculation:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                legacy_calculation = pricing_service.calculate_pricing(project_id, float(base_subtotal))
                
                # Convert legacy calculation to new format
                calculation = PricingCalculationModel(
                    subtotal=legacy_calculation.subtotal,
                    coordination_enabled=legacy_calculation.coordination_enabled,
                    coordination_amount=legacy_calculation.coordination_amount,
                    coordination_rate=legacy_calculation.coordination_rate,
                    tax_amount=legacy_calculation.tax_amount,
                    total_cost=legacy_calculation.total_cost,
                    cost_per_person=legacy_calculation.cost_per_person,
                    applied_configs=legacy_calculation.applied_configs
                )
                logger.info("📚 Using legacy pricing service for calculation")
            except ImportError:
                # Basic calculation without configuration
                calculation = PricingCalculationModel(
                    subtotal=float(base_subtotal),
                    total_cost=float(base_subtotal)
                )
                logger.warning("⚠️ No pricing service available, using basic calculation")
        
        # Create response
        response = {
            "status": "success",
            "message": "Pricing calculated successfully",
            "data": {
                "project_id": project_id,
                "rfx_id": project_id,  # Legacy compatibility
                "currency": project_currency,
                "input_subtotal": base_subtotal,
                "calculation": calculation.model_dump() if hasattr(calculation, 'model_dump') else calculation,
                "summary": {
                    "subtotal": calculation.subtotal,
                    "coordination_amount": getattr(calculation, 'coordination_amount', 0.0),
                    "tax_amount": getattr(calculation, 'tax_amount', 0.0),
                    "discount_amount": getattr(calculation, 'discount_amount', 0.0),
                    "total_cost": calculation.total_cost,
                    "cost_per_person": getattr(calculation, 'cost_per_person', None),
                    "applied_configs": getattr(calculation, 'applied_configs', [])
                }
            }
        }
        
        logger.info(f"✅ Pricing calculated for project {project_id}: ${calculation.total_cost:.2f}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error calculating pricing for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to calculate pricing",
            "error": str(e)
        }), 500


@pricing_bp.route("/presets", methods=["GET"])
def get_pricing_presets():
    """
    📋 Get available pricing configuration presets
    Modern endpoint using new PricingPresetModel with legacy fallback
    """
    try:
        logger.info("📋 Getting available pricing presets")
        
        # Try modern approach first
        presets = get_default_presets()
        
        # Convert to response format
        presets_data = []
        for preset in presets:
            preset_data = {
                "id": preset.name.lower().replace(" ", "_"),
                "name": preset.name,
                "description": preset.description,
                "preset_type": preset.preset_type,
                "pricing_model": preset.pricing_model,
                "coordination_enabled": preset.coordination_enabled,
                "coordination_rate": preset.coordination_rate,
                "coordination_type": preset.coordination_type,
                "cost_per_person_enabled": preset.cost_per_person_enabled,
                "default_headcount": preset.default_headcount,
                "tax_enabled": preset.tax_enabled,
                "default_tax_rate": preset.default_tax_rate,
                "discount_enabled": preset.discount_enabled,
                "default_discount_rate": preset.default_discount_rate,
                "margin_target": preset.margin_target,
                "minimum_margin": preset.minimum_margin,
                "is_default": preset.is_default
            }
            presets_data.append(preset_data)
        
        # If no modern presets, try legacy service
        if not presets_data:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                legacy_presets = pricing_service.get_available_presets()
                
                for preset in legacy_presets:
                    preset_data = {
                        "id": preset.name.lower().replace(" ", "_"),
                        "name": preset.name,
                        "description": preset.description,
                        "preset_type": preset.preset_type,
                        "pricing_model": "fixed_price",  # Default for legacy
                        "coordination_enabled": preset.coordination_enabled,
                        "coordination_rate": preset.coordination_rate,
                        "coordination_type": "percentage",
                        "cost_per_person_enabled": preset.cost_per_person_enabled,
                        "default_headcount": preset.default_headcount,
                        "tax_enabled": preset.taxes_enabled,
                        "default_tax_rate": preset.default_tax_rate,
                        "is_default": preset.is_default
                    }
                    presets_data.append(preset_data)
                    
                logger.info("📚 Using legacy pricing presets")
            except ImportError:
                logger.warning("⚠️ No pricing preset service available")
        
        response = {
            "status": "success",
            "message": f"Found {len(presets_data)} available presets",
            "data": presets_data
        }
        
        logger.info(f"✅ Retrieved {len(presets_data)} pricing presets")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing presets: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve pricing presets",
            "error": str(e)
        }), 500


@pricing_bp.route("/summary/<project_id>", methods=["GET"])
def get_pricing_summary(project_id: str):
    """
    📊 Get pricing configuration summary for a project
    Modern endpoint with legacy RFX support
    """
    try:
        logger.info(f"📊 Getting pricing summary for project: {project_id}")
        
        db_client = get_database_client()
        
        # Get project info
        project_record = None
        if hasattr(db_client, 'get_project_by_id'):
            project_record = db_client.get_project_by_id(project_id)
        if not project_record and hasattr(db_client, 'find_rfx_by_identifier'):
            project_record = db_client.find_rfx_by_identifier(project_id)
        
        summary = {}
        
        # Try modern approach first
        if hasattr(db_client, 'get_pricing_configuration_by_project'):
            pricing_config = db_client.get_pricing_configuration_by_project(project_id)
            if pricing_config:
                summary = {
                    "has_configuration": True,
                    "pricing_model": pricing_config.get("pricing_model", "fixed_price"),
                    "coordination_enabled": pricing_config.get("coordination_enabled", False),
                    "tax_enabled": pricing_config.get("tax_enabled", False),
                    "discount_enabled": pricing_config.get("discount_enabled", False),
                    "is_active": pricing_config.get("is_active", True)
                }
        
        # Fallback to legacy service
        if not summary:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                summary = pricing_service.get_pricing_summary_for_rfx(project_id)
                logger.info("📚 Using legacy pricing summary")
            except ImportError:
                summary = {"has_configuration": False}
        
        response = {
            "status": "success",
            "message": "Pricing summary retrieved successfully",
            "data": {
                "project_id": project_id,
                "rfx_id": project_id,  # Legacy compatibility
                **summary
            }
        }
        
        logger.info(f"✅ Pricing summary retrieved for project {project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing summary for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve pricing summary",
            "error": str(e)
        }), 500


@pricing_bp.route("/quick-config/<project_id>", methods=["POST"])
def quick_pricing_config(project_id: str):
    """
    ⚡ Quick pricing configuration with common options
    Modern endpoint with legacy RFX support
    """
    try:
        logger.info(f"⚡ Quick pricing configuration for project: {project_id}")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        
        # Quick configuration options
        config_type = data.get("config_type", "basic")
        custom_headcount = data.get("headcount")
        custom_coordination_rate = data.get("coordination_rate")
        
        # Build configuration request based on type
        if config_type == "coordination_only":
            config_data = {
                "project_id": project_id,
                "coordination_enabled": True,
                "coordination_rate": custom_coordination_rate or 0.15,
                "headcount": None
            }
        elif config_type == "cost_per_person_only":
            if not custom_headcount:
                return jsonify({
                    "status": "error",
                    "message": "headcount is required for cost_per_person configuration",
                    "error": "Missing headcount"
                }), 400
            config_data = {
                "project_id": project_id,
                "coordination_enabled": False,
                "headcount": custom_headcount
            }
        elif config_type == "full":
            if not custom_headcount:
                return jsonify({
                    "status": "error",
                    "message": "headcount is required for full configuration",
                    "error": "Missing headcount"
                }), 400
            config_data = {
                "project_id": project_id,
                "coordination_enabled": True,
                "coordination_rate": custom_coordination_rate or 0.15,
                "headcount": custom_headcount
            }
        elif config_type == "none":
            config_data = {
                "project_id": project_id,
                "coordination_enabled": False,
                "headcount": None
            }
        else:  # "basic" or default
            config_data = {
                "project_id": project_id,
                "coordination_enabled": True,
                "coordination_rate": 0.15,  # 15% basic coordination
                "headcount": custom_headcount if custom_headcount else None
            }
        
        # Create pricing configuration
        try:
            pricing_config = PricingConfigurationModel(**config_data)
        except ValidationError as e:
            logger.error(f"❌ Validation error for quick pricing configuration: {e}")
            return jsonify({
                "status": "error",
                "message": "Invalid configuration data",
                "error": str(e)
            }), 400
        
        # Save configuration
        db_client = get_database_client()
        updated_config = None
        
        # Try modern approach
        if hasattr(db_client, 'upsert_pricing_configuration'):
            updated_config = db_client.upsert_pricing_configuration(pricing_config.model_dump())
        
        # Fallback to legacy service
        if not updated_config:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                
                # Convert to legacy format
                legacy_data = {
                    "rfx_id": project_id,
                    "coordination_enabled": pricing_config.coordination_enabled,
                    "coordination_rate": pricing_config.coordination_rate,
                    "cost_per_person_enabled": pricing_config.headcount is not None,
                    "headcount": pricing_config.headcount
                }
                legacy_request = PricingConfigurationRequest(**legacy_data)
                updated_config = pricing_service.update_rfx_pricing_from_request(legacy_request)
                logger.info("📚 Using legacy pricing service for quick config")
            except ImportError:
                logger.error("❌ No pricing service available")
        
        if not updated_config:
            return jsonify({
                "status": "error",
                "message": "Failed to apply quick configuration",
                "error": "Configuration update failed"
            }), 500
        
        # Create response
        response = {
            "status": "success",
            "message": f"Quick pricing configuration '{config_type}' applied successfully",
            "data": {
                "project_id": project_id,
                "rfx_id": project_id,  # Legacy compatibility
                "config_type": config_type,
                "coordination_enabled": pricing_config.coordination_enabled,
                "coordination_rate": pricing_config.coordination_rate,
                "headcount": pricing_config.headcount,
                "cost_per_person_enabled": pricing_config.headcount is not None
            }
        }
        
        logger.info(f"✅ Quick pricing configuration '{config_type}' applied for project {project_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error applying quick pricing configuration for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to apply quick pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/validate-config", methods=["POST"])
def validate_pricing_configuration():
    """
    ✅ Validate pricing configuration without saving
    Modern validation using new PricingConfigurationModel
    """
    try:
        logger.info("✅ Validating pricing configuration")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        
        # Validate using new Pydantic model
        try:
            pricing_config = PricingConfigurationModel(**data)
            
            # Additional business logic validation
            validation_errors = []
            
            if pricing_config.coordination_enabled and not pricing_config.coordination_rate:
                validation_errors.append("coordination_rate is required when coordination is enabled")
            
            if pricing_config.tax_enabled and not pricing_config.tax_rate:
                validation_errors.append("tax_rate is required when tax is enabled")
            
            if pricing_config.discount_enabled and not pricing_config.discount_rate:
                validation_errors.append("discount_rate is required when discount is enabled")
            
            if validation_errors:
                return jsonify({
                    "status": "error",
                    "message": "Configuration validation failed",
                    "errors": validation_errors
                }), 400
            
            # Configuration is valid
            response = {
                "status": "success",
                "message": "Pricing configuration is valid",
                "data": {
                    "coordination_enabled": pricing_config.coordination_enabled,
                    "coordination_rate": pricing_config.coordination_rate,
                    "headcount": pricing_config.headcount,
                    "tax_enabled": pricing_config.tax_enabled,
                    "tax_rate": pricing_config.tax_rate,
                    "discount_enabled": pricing_config.discount_enabled,
                    "discount_rate": pricing_config.discount_rate,
                    "is_valid": True
                }
            }
            
            logger.info("✅ Pricing configuration validation passed")
            return jsonify(response), 200
            
        except ValidationError as e:
            logger.error(f"❌ Pricing configuration validation failed: {e}")
            return jsonify({
                "status": "error",
                "message": "Configuration validation failed",
                "error": str(e),
                "is_valid": False
            }), 400
        
    except Exception as e:
        logger.error(f"❌ Error validating pricing configuration: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to validate pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/calculate-from-project/<project_id>", methods=["GET"])
def calculate_pricing_from_project(project_id: str):
    """
    🧮 Calculate pricing automatically based on project items
    Modern endpoint with legacy RFX support
    """
    try:
        logger.info(f"🧮 Auto-calculating pricing for project: {project_id}")
        
        db_client = get_database_client()
        
        # Smart lookup: Try projects table first, then RFX
        project_record = None
        if hasattr(db_client, 'get_project_by_id'):
            project_record = db_client.get_project_by_id(project_id)
        if not project_record and hasattr(db_client, 'find_rfx_by_identifier'):
            project_record = db_client.find_rfx_by_identifier(project_id)
        
        if not project_record:
            return jsonify({
                "status": "error",
                "message": f"Project not found for identifier: {project_id}",
                "error": "project_not_found"
            }), 404
        
        actual_project_id = str(project_record["id"])
        
        # Get project items and calculate subtotal
        project_items = None
        if hasattr(db_client, 'get_project_items'):
            project_items = db_client.get_project_items(actual_project_id)
        elif hasattr(db_client, 'get_rfx_products'):
            project_items = db_client.get_rfx_products(actual_project_id)
        
        if not project_items:
            return jsonify({
                "status": "error",
                "message": "No items found for project",
                "error": "Project must have items with prices to calculate pricing",
                "suggestion": "Please set item costs first"
            }), 404
        
        # Calculate subtotal from project items
        subtotal = 0.0
        for item in project_items:
            unit_price = item.get("unit_price", item.get("estimated_unit_price", 0.0)) or 0.0
            quantity = item.get("quantity", 0) or 0
            subtotal += unit_price * quantity
        
        if subtotal <= 0:
            return jsonify({
                "status": "error",
                "message": "Cannot calculate pricing with zero subtotal",
                "error": "Items must have valid prices and quantities",
                "debug": {
                    "items_count": len(project_items),
                    "calculated_subtotal": subtotal
                }
            }), 400
        
        # Calculate pricing using modern approach
        calculation = None
        
        # Try new pricing configuration approach
        if hasattr(db_client, 'get_pricing_configuration_by_project'):
            pricing_config = db_client.get_pricing_configuration_by_project(actual_project_id)
            if pricing_config:
                config_model = PricingConfigurationModel(**pricing_config)
                calculation = PricingCalculationModel.calculate_from_config(config_model, subtotal)
        
        # Fallback to legacy pricing service
        if not calculation:
            try:
                from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
                pricing_service = PricingConfigurationServiceV2()
                legacy_calculation = pricing_service.calculate_pricing(actual_project_id, subtotal)
                
                # Convert to new format
                calculation = PricingCalculationModel(
                    subtotal=legacy_calculation.subtotal,
                    coordination_enabled=legacy_calculation.coordination_enabled,
                    coordination_amount=legacy_calculation.coordination_amount,
                    tax_amount=legacy_calculation.tax_amount,
                    total_cost=legacy_calculation.total_cost
                )
                logger.info("📚 Using legacy pricing service for auto calculation")
            except ImportError:
                calculation = PricingCalculationModel(subtotal=subtotal, total_cost=subtotal)
        
        # Get pricing configuration for context
        config_exists = hasattr(db_client, 'get_pricing_configuration_by_project') and \
                       db_client.get_pricing_configuration_by_project(actual_project_id) is not None
        
        # Create detailed response
        response = {
            "status": "success",
            "message": "Pricing calculated successfully from project items",
            "data": {
                "project_id": actual_project_id,
                "rfx_id": actual_project_id,  # Legacy compatibility
                "items_analyzed": len(project_items),
                "calculation": calculation.model_dump() if hasattr(calculation, 'model_dump') else calculation,
                "breakdown": {
                    "subtotal": calculation.subtotal,
                    "coordination": {
                        "enabled": getattr(calculation, 'coordination_enabled', False),
                        "rate": getattr(calculation, 'coordination_rate', 0.0),
                        "amount": getattr(calculation, 'coordination_amount', 0.0)
                    },
                    "cost_per_person": {
                        "enabled": getattr(calculation, 'headcount', None) is not None,
                        "headcount": getattr(calculation, 'headcount', None),
                        "cost_per_person": getattr(calculation, 'cost_per_person', None)
                    },
                    "taxes": {
                        "enabled": getattr(calculation, 'tax_enabled', False),
                        "rate": getattr(calculation, 'tax_rate', 0.0),
                        "amount": getattr(calculation, 'tax_amount', 0.0)
                    },
                    "totals": {
                        "final_total": calculation.total_cost
                    }
                },
                "configuration_status": {
                    "has_configuration": config_exists,
                    "applied_configs": getattr(calculation, 'applied_configs', [])
                }
            }
        }
        
        logger.info(f"✅ Auto-pricing calculated for project {actual_project_id}: ${calculation.total_cost:.2f}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error auto-calculating pricing for project {project_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to calculate pricing from project",
            "error": str(e)
        }), 500


# ========================
# LEGACY COMPATIBILITY ENDPOINTS
# ========================

@pricing_bp.route("/legacy/config/<rfx_id>", methods=["GET"])
def get_legacy_pricing_configuration(rfx_id: str):
    """Legacy compatibility endpoint for RFX pricing configuration"""
    logger.info(f"📚 Legacy pricing config endpoint called for RFX: {rfx_id}")
    return get_pricing_configuration(rfx_id)


@pricing_bp.route("/calculate-from-rfx/<rfx_id>", methods=["GET"])
def calculate_pricing_from_rfx(rfx_id: str):
    """Legacy compatibility endpoint for RFX-based pricing calculation"""
    logger.info(f"📚 Legacy pricing calculation endpoint called for RFX: {rfx_id}")
    return calculate_pricing_from_project(rfx_id)
