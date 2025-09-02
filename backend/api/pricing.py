"""
💰 Pricing Configuration API - Endpoints para configuración de pricing
Permite al usuario configurar coordinación, costo por persona y otras opciones
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError
import logging
from datetime import datetime

from backend.models.pricing_models import (
    PricingConfigurationRequest, PricingConfigurationResponse,
    PricingCalculation
)
from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

# Create blueprint
pricing_bp = Blueprint("pricing_api", __name__, url_prefix="/api/pricing")


@pricing_bp.route("/config/<rfx_id>", methods=["GET"])
def get_pricing_configuration(rfx_id: str):
    """
    📋 Obtener configuración de pricing para un RFX
    """
    try:
        logger.info(f"🔍 Getting pricing configuration for RFX: {rfx_id}")
        
        # 🧠 Smart RFX lookup: Try UUID first, then search by name
        db_client = get_database_client()
        rfx_record = db_client.find_rfx_by_identifier(rfx_id)
        
        if not rfx_record:
            logger.error(f"❌ RFX not found for identifier: {rfx_id}")
            return jsonify({
                "status": "error",
                "message": f"RFX not found for identifier: {rfx_id}",
                "error": "rfx_not_found",
                "help": "Provide either a valid UUID or the exact requester/company name"
            }), 404
        
        # Extract the actual UUID for subsequent operations
        actual_rfx_id = str(rfx_record["id"])
        
        # Log the successful lookup
        try:
            import uuid as _uuid
            _ = _uuid.UUID(rfx_id)
            logger.info(f"✅ Direct UUID lookup successful: {rfx_id}")
        except (ValueError, TypeError):
            logger.info(f"✅ Smart lookup successful: '{rfx_id}' → RFX ID: {actual_rfx_id}")
            logger.info(f"📋 Found RFX: {rfx_record.get('title', 'Unknown')} for {rfx_record.get('requesters', {}).get('name', 'Unknown')} at {rfx_record.get('companies', {}).get('name', 'Unknown')}")
        
        # Use the actual UUID for pricing service
        pricing_service = PricingConfigurationServiceV2()
        config = pricing_service.get_rfx_pricing_configuration(actual_rfx_id)
        
        if not config:
            # Return default configuration structure
            response = {
                "status": "success",
                "message": "No pricing configuration found, returning defaults",
                "data": {
                    "rfx_id": actual_rfx_id,
                    "coordination_enabled": False,
                    "coordination_rate": 0.18,
                    "cost_per_person_enabled": False,
                    "headcount": None,
                    "taxes_enabled": False,
                    "has_configuration": False
                }
            }
            return jsonify(response), 200
        
        # Get currency from RFX record  
        rfx_currency = rfx_record.get("currency", "USD")
        
        # Convert to response format
        response_data = {
            "rfx_id": str(config.rfx_id),
            "currency": rfx_currency,  # ✅ Incluir moneda del RFX
            "coordination_enabled": config.has_coordination(),
            "coordination_rate": config.get_coordination_rate(),
            "cost_per_person_enabled": config.has_cost_per_person(),
            "headcount": config.get_headcount(),
            "taxes_enabled": config.taxes and config.taxes.is_enabled if config.taxes else False,
            "tax_rate": config.taxes.config_value.tax_rate if config.taxes and config.taxes.is_enabled else None,
            "tax_type": config.taxes.config_value.tax_type if config.taxes and config.taxes.is_enabled else None,
            "has_configuration": True,
            "last_updated": config.updated_at.isoformat() if config.updated_at else None,
            "enabled_configs": [cfg.config_type for cfg in config.get_enabled_configs()]
        }
        
        response = {
            "status": "success",
            "message": "Pricing configuration retrieved successfully",
            "data": response_data
        }
        
        logger.info(f"✅ Pricing configuration retrieved for RFX {actual_rfx_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing configuration for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/config/<rfx_id>", methods=["PUT"])
def update_pricing_configuration(rfx_id: str):
    """
    ⚙️ Actualizar configuración de pricing para un RFX
    """
    try:
        logger.info(f"🔄 Updating pricing configuration for RFX: {rfx_id}")
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json",
                "error": "Invalid content type"
            }), 400
        
        data = request.get_json()
        # Log de payload entrante (sanitizado)
        try:
            logger.info(f"📡 Received pricing update payload for {rfx_id}: "
                        f"keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        except Exception:
            pass
        
        # 🧠 Smart RFX lookup: Try UUID first, then search by name
        db_client = get_database_client()
        rfx_record = db_client.find_rfx_by_identifier(rfx_id)
        
        if not rfx_record:
            logger.error(f"❌ RFX not found for identifier: {rfx_id}")
            return jsonify({
                "status": "error",
                "message": f"RFX not found for identifier: {rfx_id}",
                "error": "rfx_not_found",
                "help": "Provide either a valid UUID or the exact requester/company name"
            }), 404
        
        # Extract the actual UUID for subsequent operations
        actual_rfx_id = str(rfx_record["id"])
        
        # If the identifier was not a UUID, log the successful lookup
        try:
            import uuid as _uuid
            _ = _uuid.UUID(rfx_id)
            logger.info(f"✅ Direct UUID lookup successful: {rfx_id}")
        except (ValueError, TypeError):
            logger.info(f"✅ Smart lookup successful: '{rfx_id}' → RFX ID: {actual_rfx_id}")
            logger.info(f"📋 Found RFX: {rfx_record.get('title', 'Unknown')} for {rfx_record.get('requesters', {}).get('name', 'Unknown')} at {rfx_record.get('companies', {}).get('name', 'Unknown')}")
        
        # Update rfx_id to use the actual UUID for the rest of the function
        rfx_id = actual_rfx_id

        # Add rfx_id to request data
        data["rfx_id"] = rfx_id
        
        # Validate request using Pydantic
        try:
            pricing_request = PricingConfigurationRequest(**data)
        except ValidationError as e:
            logger.error(f"❌ Validation error for pricing configuration: {e}")
            return jsonify({
                "status": "error",
                "message": "Invalid request data",
                "error": str(e)
            }), 400
        
        # Update configuration
        pricing_service = PricingConfigurationServiceV2()
        updated_config = pricing_service.update_rfx_pricing_from_request(pricing_request)
        
        if not updated_config:
            return jsonify({
                "status": "error",
                "message": "Failed to update pricing configuration",
                "error": "Configuration update failed"
            }), 500
        
        # Create response
        response = PricingConfigurationResponse(
            status="success",
            message="Pricing configuration updated successfully",
            data=updated_config,
            timestamp=datetime.now()
        )
        
        logger.info(f"✅ Pricing configuration updated for RFX {rfx_id}")
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating pricing configuration for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to update pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/calculate/<rfx_id>", methods=["POST"])
def calculate_pricing(rfx_id: str):
    """
    🧮 Calcular pricing total para un RFX aplicando configuraciones
    """
    try:
        logger.info(f"🧮 Calculating pricing for RFX: {rfx_id}")
        
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
        
        # Calculate pricing
        pricing_service = PricingConfigurationServiceV2()
        calculation = pricing_service.calculate_pricing(rfx_id, float(base_subtotal))
        
        # Get currency from RFX for display
        db_client = get_database_client()
        rfx_record = db_client.find_rfx_by_identifier(rfx_id)
        rfx_currency = rfx_record.get("currency", "USD") if rfx_record else "USD"
        
        # Create response
        response = {
            "status": "success",
            "message": "Pricing calculated successfully",
            "data": {
                "rfx_id": rfx_id,
                "currency": rfx_currency,  # ✅ Incluir moneda en cálculos
                "input_subtotal": base_subtotal,
                "calculation": calculation.model_dump(),
                "summary": {
                    "subtotal": calculation.subtotal,
                    "coordination_amount": calculation.coordination_amount,
                    "tax_amount": calculation.tax_amount,
                    "total_cost": calculation.total_cost,
                    "cost_per_person": calculation.cost_per_person,
                    "applied_configs": calculation.applied_configs
                }
            }
        }
        
        logger.info(f"✅ Pricing calculated for RFX {rfx_id}: ${calculation.total_cost:.2f}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error calculating pricing for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to calculate pricing",
            "error": str(e)
        }), 500


@pricing_bp.route("/presets", methods=["GET"])
def get_pricing_presets():
    """
    📋 Obtener presets de configuración disponibles
    """
    try:
        logger.info("📋 Getting available pricing presets")
        
        pricing_service = PricingConfigurationServiceV2()
        presets = pricing_service.get_available_presets()
        
        # Convert to response format
        presets_data = []
        for preset in presets:
            preset_data = {
                "id": preset.name.lower().replace(" ", "_"),
                "name": preset.name,
                "description": preset.description,
                "preset_type": preset.preset_type,
                "coordination_enabled": preset.coordination_enabled,
                "coordination_rate": preset.coordination_rate,
                "cost_per_person_enabled": preset.cost_per_person_enabled,
                "default_headcount": preset.default_headcount,
                "taxes_enabled": preset.taxes_enabled,
                "default_tax_rate": preset.default_tax_rate,
                "default_tax_type": preset.default_tax_type,
                "is_default": preset.is_default
            }
            presets_data.append(preset_data)
        
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


@pricing_bp.route("/summary/<rfx_id>", methods=["GET"])
def get_pricing_summary(rfx_id: str):
    """
    📊 Obtener resumen de configuración de pricing para un RFX
    """
    try:
        logger.info(f"📊 Getting pricing summary for RFX: {rfx_id}")
        
        pricing_service = PricingConfigurationServiceV2()
        summary = pricing_service.get_pricing_summary_for_rfx(rfx_id)
        
        response = {
            "status": "success",
            "message": "Pricing summary retrieved successfully",
            "data": {
                "rfx_id": rfx_id,
                **summary
            }
        }
        
        logger.info(f"✅ Pricing summary retrieved for RFX {rfx_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing summary for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve pricing summary",
            "error": str(e)
        }), 500


@pricing_bp.route("/quick-config/<rfx_id>", methods=["POST"])
def quick_pricing_config(rfx_id: str):
    """
    ⚡ Configuración rápida de pricing con opciones comunes
    """
    try:
        logger.info(f"⚡ Quick pricing configuration for RFX: {rfx_id}")
        
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
                "rfx_id": rfx_id,
                "coordination_enabled": True,
                "coordination_rate": custom_coordination_rate or 0.18,
                "cost_per_person_enabled": False
            }
        elif config_type == "cost_per_person_only":
            if not custom_headcount:
                return jsonify({
                    "status": "error",
                    "message": "headcount is required for cost_per_person configuration",
                    "error": "Missing headcount"
                }), 400
            config_data = {
                "rfx_id": rfx_id,
                "coordination_enabled": False,
                "cost_per_person_enabled": True,
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
                "rfx_id": rfx_id,
                "coordination_enabled": True,
                "coordination_rate": custom_coordination_rate or 0.18,
                "cost_per_person_enabled": True,
                "headcount": custom_headcount
            }
        elif config_type == "none":
            config_data = {
                "rfx_id": rfx_id,
                "coordination_enabled": False,
                "cost_per_person_enabled": False
            }
        else:  # "basic" or default
            config_data = {
                "rfx_id": rfx_id,
                "coordination_enabled": True,
                "coordination_rate": 0.15,  # 15% basic coordination
                "cost_per_person_enabled": bool(custom_headcount),
                "headcount": custom_headcount if custom_headcount else None
            }
        
        # Create and process request
        try:
            pricing_request = PricingConfigurationRequest(**config_data)
        except ValidationError as e:
            logger.error(f"❌ Validation error for quick pricing configuration: {e}")
            return jsonify({
                "status": "error",
                "message": "Invalid configuration data",
                "error": str(e)
            }), 400
        
        # Update configuration
        pricing_service = PricingConfigurationServiceV2()
        updated_config = pricing_service.update_rfx_pricing_from_request(pricing_request)
        
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
                "rfx_id": rfx_id,
                "config_type": config_type,
                "coordination_enabled": updated_config.has_coordination(),
                "coordination_rate": updated_config.get_coordination_rate(),
                "cost_per_person_enabled": updated_config.has_cost_per_person(),
                "headcount": updated_config.get_headcount()
            }
        }
        
        logger.info(f"✅ Quick pricing configuration '{config_type}' applied for RFX {rfx_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error applying quick pricing configuration for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to apply quick pricing configuration",
            "error": str(e)
        }), 500


@pricing_bp.route("/validate-config", methods=["POST"])
def validate_pricing_configuration():
    """
    ✅ Validar configuración de pricing sin guardar
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
        
        # Validate using Pydantic model
        try:
            pricing_request = PricingConfigurationRequest(**data)
            
            # Additional business logic validation
            validation_errors = []
            
            if pricing_request.coordination_enabled and not pricing_request.coordination_rate:
                validation_errors.append("coordination_rate is required when coordination is enabled")
            
            if pricing_request.cost_per_person_enabled and not pricing_request.headcount:
                validation_errors.append("headcount is required when cost_per_person is enabled")
            
            if pricing_request.taxes_enabled and not pricing_request.tax_rate:
                validation_errors.append("tax_rate is required when taxes are enabled")
            
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
                    "coordination_enabled": pricing_request.coordination_enabled,
                    "coordination_rate": pricing_request.coordination_rate,
                    "cost_per_person_enabled": pricing_request.cost_per_person_enabled,
                    "headcount": pricing_request.headcount,
                    "taxes_enabled": pricing_request.taxes_enabled,
                    "tax_rate": pricing_request.tax_rate,
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


@pricing_bp.route("/calculate-from-rfx/<rfx_id>", methods=["GET"])
def calculate_pricing_from_rfx(rfx_id: str):
    """
    🧮 Calcular pricing automáticamente basado en productos del RFX
    """
    try:
        logger.info(f"🧮 Auto-calculating pricing for RFX: {rfx_id}")
        
        # 🧠 Smart RFX lookup: Try UUID first, then search by name
        db_client = get_database_client()
        rfx_record = db_client.find_rfx_by_identifier(rfx_id)
        
        if not rfx_record:
            logger.error(f"❌ RFX not found for identifier: {rfx_id}")
            return jsonify({
                "status": "error",
                "message": f"RFX not found for identifier: {rfx_id}",
                "error": "rfx_not_found",
                "help": "Provide either a valid UUID or the exact requester/company name"
            }), 404
        
        # Extract the actual UUID for subsequent operations
        actual_rfx_id = str(rfx_record["id"])
        
        # Log the successful lookup
        try:
            import uuid as _uuid
            _ = _uuid.UUID(rfx_id)
            logger.info(f"✅ Direct UUID lookup successful: {rfx_id}")
        except (ValueError, TypeError):
            logger.info(f"✅ Smart lookup successful: '{rfx_id}' → RFX ID: {actual_rfx_id}")
            logger.info(f"📋 Found RFX: {rfx_record.get('title', 'Unknown')} for {rfx_record.get('requesters', {}).get('name', 'Unknown')} at {rfx_record.get('companies', {}).get('name', 'Unknown')}")
        
        # Use the actual UUID for subsequent operations
        rfx_id = actual_rfx_id
        
        # Obtener productos y calcular subtotal
        rfx_products = db_client.get_rfx_products(rfx_id)
        if not rfx_products:
            return jsonify({
                "status": "error",
                "message": "No products found for RFX",
                "error": "RFX must have products with prices to calculate pricing",
                "suggestion": "Please set product costs first"
            }), 404
        
        # Calcular subtotal de productos
        subtotal = 0.0
        for product in rfx_products:
            unit_price = product.get("estimated_unit_price", 0.0) or 0.0
            quantity = product.get("quantity", 0) or 0
            subtotal += unit_price * quantity
        
        if subtotal <= 0:
            return jsonify({
                "status": "error",
                "message": "Cannot calculate pricing with zero subtotal",
                "error": "Products must have valid prices and quantities",
                "debug": {
                    "products_count": len(rfx_products),
                    "calculated_subtotal": subtotal
                }
            }), 400
        
        # Calcular pricing
        pricing_service = PricingConfigurationServiceV2()
        calculation = pricing_service.calculate_pricing(rfx_id, subtotal)
        
        # Obtener configuración para contexto adicional
        config = pricing_service.get_rfx_pricing_configuration(rfx_id)
        
        # Crear respuesta detallada
        response = {
            "status": "success",
            "message": "Pricing calculated successfully from RFX products",
            "data": {
                "rfx_id": rfx_id,
                "products_analyzed": len(rfx_products),
                "calculation": calculation.model_dump(),
                "breakdown": {
                    "subtotal": calculation.subtotal,
                    "coordination": {
                        "enabled": calculation.coordination_enabled,
                        "rate": calculation.coordination_rate,
                        "amount": calculation.coordination_amount
                    },
                    "cost_per_person": {
                        "enabled": calculation.cost_per_person_enabled,
                        "headcount": calculation.headcount,
                        "cost_per_person": calculation.cost_per_person
                    },
                    "taxes": {
                        "enabled": calculation.taxes_enabled,
                        "rate": calculation.tax_rate,
                        "amount": calculation.tax_amount
                    },
                    "totals": {
                        "before_tax": calculation.total_before_tax,
                        "final_total": calculation.total_cost
                    }
                },
                "configuration_status": {
                    "has_configuration": config is not None,
                    "enabled_configs": calculation.applied_configs if calculation.applied_configs else []
                }
            }
        }
        
        logger.info(f"✅ Auto-pricing calculated for RFX {rfx_id}: ${calculation.total_cost:.2f}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error auto-calculating pricing for RFX {rfx_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to calculate pricing from RFX",
            "error": str(e)
        }), 500
