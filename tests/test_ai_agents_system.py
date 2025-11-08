"""
🧪 Tests para el Sistema de 3 Agentes AI
Fecha: 2025-11-05

Tests incluidos:
1. Test de generación de template HTML desde branding
2. Test del Agente 1: Proposal Generator
3. Test del Agente 2: Template Validator
4. Test del Agente 3: PDF Optimizer
5. Test del Orquestador completo
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.user_branding_service import user_branding_service
from backend.services.ai_agents.proposal_generator_agent import proposal_generator_agent
from backend.services.ai_agents.template_validator_agent import template_validator_agent
from backend.services.ai_agents.pdf_optimizer_agent import pdf_optimizer_agent
from backend.services.ai_agents.agent_orchestrator import agent_orchestrator

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATOS DE PRUEBA
# ============================================================================

MOCK_LOGO_ANALYSIS = {
    "primary_color": "#0e2541",
    "secondary_color": "#ffffff",
    "dominant_colors": ["#0e2541", "#ffffff"]
}

MOCK_TEMPLATE_ANALYSIS = {
    "color_scheme": {
        "primary": "#0e2541",
        "secondary": "#ffffff",
        "text": "#333333",
        "borders": "#000000"
    },
    "table_style": {
        "header_background": "#0e2541",
        "header_text_color": "#ffffff",
        "border_color": "#000000"
    },
    "typography": {
        "font_family": "Arial, sans-serif",
        "body_size": "11pt",
        "title_size": "24pt"
    },
    "spacing_rules": {
        "between_sections": "30px"
    }
}

MOCK_RFX_DATA = {
    "client_name": "Empresa Test S.A.",
    "solicitud": "Solicitud de prueba para testing del sistema",
    "products": [
        {
            "nombre": "Producto 1",
            "cantidad": 10,
            "precio_unitario": 100.00,
            "total": 1000.00
        },
        {
            "nombre": "Producto 2",
            "cantidad": 5,
            "precio_unitario": 200.00,
            "total": 1000.00
        }
    ],
    "pricing": {
        "subtotal_formatted": "$2,000.00",
        "coordination_formatted": "$200.00",
        "tax_formatted": "$0.00",
        "total_formatted": "$2,200.00",
        "cost_per_person_formatted": "$110.00"
    }
}


# ============================================================================
# TEST 1: GENERACIÓN DE TEMPLATE HTML
# ============================================================================

async def test_html_template_generation():
    """Test de generación de template HTML desde análisis de branding"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 1: Generación de Template HTML")
    logger.info("="*60)
    
    try:
        # Generar template HTML
        html_template = await user_branding_service._generate_html_template(
            MOCK_LOGO_ANALYSIS,
            MOCK_TEMPLATE_ANALYSIS
        )
        
        # Validaciones
        assert html_template is not None, "Template HTML no debe ser None"
        assert len(html_template) > 0, "Template HTML no debe estar vacío"
        assert "<!DOCTYPE html>" in html_template, "Debe contener DOCTYPE"
        assert "{{CLIENT_NAME}}" in html_template, "Debe contener variable CLIENT_NAME"
        assert "{{PRODUCT_ROWS}}" in html_template, "Debe contener variable PRODUCT_ROWS"
        assert "#0e2541" in html_template, "Debe usar color primario del branding"
        
        logger.info("✅ Template HTML generado correctamente")
        logger.info(f"   - Longitud: {len(html_template)} caracteres")
        logger.info(f"   - Variables encontradas: CLIENT_NAME, PRODUCT_ROWS, LOGO_URL")
        
        return html_template
        
    except Exception as e:
        logger.error(f"❌ Error en test de template HTML: {e}")
        raise


# ============================================================================
# TEST 2: AGENTE 1 - PROPOSAL GENERATOR
# ============================================================================

async def test_proposal_generator_agent(html_template):
    """Test del Agente 1: Proposal Generator"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 2: Agente 1 - Proposal Generator")
    logger.info("="*60)
    
    try:
        request = {
            "html_template": html_template,
            "user_id": "test-user-123",
            "logo_url": "/api/branding/files/test-user-123/logo",
            "data": MOCK_RFX_DATA
        }
        
        result = await proposal_generator_agent.generate(request)
        
        # Validaciones
        assert result["status"] == "success", "Debe retornar status success"
        assert result["html_generated"] is not None, "Debe generar HTML"
        assert "Empresa Test S.A." in result["html_generated"], "Debe incluir nombre del cliente"
        assert "Producto 1" in result["html_generated"], "Debe incluir productos"
        assert "$2,200.00" in result["html_generated"], "Debe incluir total"
        
        logger.info("✅ Agente 1 funcionando correctamente")
        logger.info(f"   - HTML generado: {len(result['html_generated'])} caracteres")
        logger.info(f"   - Variables reemplazadas: {result['metadata']['variables_replaced']}")
        logger.info(f"   - Productos procesados: {result['metadata']['products_count']}")
        
        return result["html_generated"]
        
    except Exception as e:
        logger.error(f"❌ Error en Agente 1: {e}")
        raise


# ============================================================================
# TEST 3: AGENTE 2 - TEMPLATE VALIDATOR
# ============================================================================

async def test_template_validator_agent(html_generated, html_template):
    """Test del Agente 2: Template Validator"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 3: Agente 2 - Template Validator")
    logger.info("="*60)
    
    try:
        branding_config = {
            "primary_color": "#0e2541",
            "table_header_bg": "#0e2541",
            "table_header_text": "#ffffff"
        }
        
        request = {
            "html_generated": html_generated,
            "html_template": html_template,
            "branding_config": branding_config
        }
        
        result = await template_validator_agent.validate(request)
        
        # Validaciones
        assert "is_valid" in result, "Debe retornar is_valid"
        assert "issues" in result, "Debe retornar lista de issues"
        assert "similarity_score" in result, "Debe retornar similarity_score"
        
        logger.info(f"✅ Agente 2 funcionando correctamente")
        logger.info(f"   - Válido: {result['is_valid']}")
        logger.info(f"   - Issues encontrados: {len(result['issues'])}")
        logger.info(f"   - Similarity score: {result['similarity_score']}")
        
        if result['issues']:
            logger.warning(f"   ⚠️ Issues detectados:")
            for issue in result['issues']:
                logger.warning(f"      - {issue}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en Agente 2: {e}")
        raise


# ============================================================================
# TEST 4: AGENTE 3 - PDF OPTIMIZER
# ============================================================================

async def test_pdf_optimizer_agent(html_content):
    """Test del Agente 3: PDF Optimizer"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 4: Agente 3 - PDF Optimizer")
    logger.info("="*60)
    
    try:
        request = {
            "html_content": html_content,
            "page_config": {
                "size": "letter",
                "orientation": "portrait"
            },
            "quality_requirements": {
                "professional_spacing": True,
                "table_centering": True,
                "min_margin": "15mm",
                "max_table_width": "190mm"
            }
        }
        
        result = await pdf_optimizer_agent.optimize(request)
        
        # Validaciones
        assert result["status"] == "success", "Debe retornar status success"
        assert result["html_optimized"] is not None, "Debe retornar HTML optimizado"
        assert "analysis" in result, "Debe incluir análisis"
        
        logger.info("✅ Agente 3 funcionando correctamente")
        logger.info(f"   - HTML optimizado: {len(result['html_optimized'])} caracteres")
        logger.info(f"   - Ajustes realizados: {len(result['analysis']['adjustments_made'])}")
        logger.info(f"   - Warnings: {len(result['analysis']['warnings'])}")
        
        if result['analysis']['adjustments_made']:
            logger.info("   📝 Ajustes aplicados:")
            for adjustment in result['analysis']['adjustments_made']:
                logger.info(f"      - {adjustment}")
        
        return result["html_optimized"]
        
    except Exception as e:
        logger.error(f"❌ Error en Agente 3: {e}")
        raise


# ============================================================================
# TEST 5: ORQUESTADOR COMPLETO
# ============================================================================

async def test_agent_orchestrator(html_template):
    """Test del flujo completo del orquestador"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 5: Agent Orchestrator - Flujo Completo")
    logger.info("="*60)
    
    try:
        branding_config = {
            "primary_color": "#0e2541",
            "secondary_color": "#ffffff",
            "table_header_bg": "#0e2541",
            "table_header_text": "#ffffff",
            "table_border": "#000000"
        }
        
        result = await agent_orchestrator.generate_professional_proposal(
            html_template=html_template,
            rfx_data=MOCK_RFX_DATA,
            branding_config=branding_config,
            user_id="test-user-123"
        )
        
        # Validaciones
        assert result["status"] == "success", "Debe retornar status success"
        assert result["html_final"] is not None, "Debe retornar HTML final"
        assert "metadata" in result, "Debe incluir metadata"
        
        metadata = result["metadata"]
        assert "generation" in metadata, "Debe incluir metadata de generación"
        assert "validation" in metadata, "Debe incluir metadata de validación"
        assert "optimization" in metadata, "Debe incluir metadata de optimización"
        assert "total_time_ms" in metadata, "Debe incluir tiempo total"
        
        logger.info("✅ Orquestador funcionando correctamente")
        logger.info(f"   - Tiempo total: {metadata['total_time_ms']}ms")
        logger.info(f"   - Validación exitosa: {metadata['validation']['is_valid']}")
        logger.info(f"   - Retries realizados: {metadata['validation']['retries']}")
        logger.info(f"   - Agentes usados: {', '.join(metadata['agents_used'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en Orquestador: {e}")
        raise


# ============================================================================
# EJECUTAR TODOS LOS TESTS
# ============================================================================

async def run_all_tests():
    """Ejecuta todos los tests en secuencia"""
    logger.info("\n" + "🚀 "+"="*58)
    logger.info("🚀 INICIANDO SUITE DE TESTS - SISTEMA DE 3 AGENTES AI")
    logger.info("🚀 "+"="*58 + "\n")
    
    try:
        # Test 1: Generación de template HTML
        html_template = await test_html_template_generation()
        
        # Test 2: Agente 1 - Proposal Generator
        html_generated = await test_proposal_generator_agent(html_template)
        
        # Test 3: Agente 2 - Template Validator
        validation_result = await test_template_validator_agent(html_generated, html_template)
        
        # Test 4: Agente 3 - PDF Optimizer
        html_optimized = await test_pdf_optimizer_agent(html_generated)
        
        # Test 5: Orquestador completo
        orchestrator_result = await test_agent_orchestrator(html_template)
        
        # Resumen final
        logger.info("\n" + "="*60)
        logger.info("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        logger.info("="*60)
        logger.info("\n📊 RESUMEN:")
        logger.info(f"   ✅ Test 1: Template HTML Generation - PASSED")
        logger.info(f"   ✅ Test 2: Proposal Generator Agent - PASSED")
        logger.info(f"   ✅ Test 3: Template Validator Agent - PASSED")
        logger.info(f"   ✅ Test 4: PDF Optimizer Agent - PASSED")
        logger.info(f"   ✅ Test 5: Agent Orchestrator - PASSED")
        logger.info("\n🎉 Sistema de 3 Agentes AI funcionando correctamente!\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TESTS FALLIDOS: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
