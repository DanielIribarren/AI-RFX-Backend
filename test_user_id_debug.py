#!/usr/bin/env python3
"""
Script de debug para verificar el problema del user_id=None
"""

import logging
import sys
from pathlib import Path

# Agregar el backend al path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_user_id_issue():
    """Test para reproducir el problema del user_id=None"""
    
    logger.info("🔍 Testing user_id issue in proposal generation...")
    
    # Datos de prueba simulando lo que llega al generador
    test_rfx_data = {
        "user_id": "186ea35f-3cf8-480f-a7d3-0af178c09498",  # Usuario conocido de las memorias
        "companies": {
            "name": "Test Company",
            "contact_email": "test@company.com"
        },
        "productos": [
            {
                "name": "Test Product",
                "estimated_unit_price": 100.0,
                "quantity": 2,
                "unit": "pieces"
            }
        ]
    }
    
    # Datos de prueba sin user_id para simular el problema
    test_rfx_data_no_user = {
        "companies": {
            "name": "Test Company",
            "contact_email": "test@company.com"
        },
        "productos": [
            {
                "name": "Test Product",
                "estimated_unit_price": 100.0,
                "quantity": 2,
                "unit": "pieces"
            }
        ]
    }
    
    logger.info(f"📋 Test data WITH user_id: {test_rfx_data.get('user_id')}")
    logger.info(f"📋 Test data WITHOUT user_id: {test_rfx_data_no_user.get('user_id')}")
    
    # Simular ProposalRequest
    class MockProposalRequest:
        def __init__(self):
            self.rfx_id = "test-rfx-123"
            self.currency = "USD"
    
    try:
        from services.proposal_generator import ProposalGenerationService
        
        # Inicializar el servicio
        proposal_service = ProposalGenerationService()
        mock_request = MockProposalRequest()
        
        logger.info("🚀 Testing WITH user_id...")
        
        # Test 1: Con user_id
        try:
            result1 = await proposal_service.generate_proposal(test_rfx_data, mock_request)
            logger.info("✅ Test WITH user_id completed")
        except Exception as e:
            logger.error(f"❌ Test WITH user_id failed: {e}")
        
        logger.info("🚀 Testing WITHOUT user_id...")
        
        # Test 2: Sin user_id (debería activar fallbacks)
        try:
            result2 = await proposal_service.generate_proposal(test_rfx_data_no_user, mock_request)
            logger.info("✅ Test WITHOUT user_id completed")
        except Exception as e:
            logger.error(f"❌ Test WITHOUT user_id failed: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error importing or initializing service: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_user_id_issue())
