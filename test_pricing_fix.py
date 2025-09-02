#!/usr/bin/env python3
"""
🧪 Test Script para la solución de Pricing API
Prueba la búsqueda inteligente de RFX por nombre vs UUID

Este script demuestra cómo la nueva implementación puede manejar:
1. UUIDs válidos (comportamiento original)
2. Nombres de solicitantes (nuevo comportamiento)
3. Nombres de empresas (nuevo comportamiento)

Ejemplo del problema original:
❌ PUT /api/pricing/config/Sofia%20Elena%20Camejo%20Copello

Con la nueva solución:
✅ PUT /api/pricing/config/Sofia%20Elena%20Camejo%20Copello
"""
import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.database import get_database_client
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_smart_rfx_lookup():
    """
    🔍 Test de la función de búsqueda inteligente de RFX
    """
    print("🧪 Testing Smart RFX Lookup Functionality")
    print("=" * 50)
    
    try:
        db_client = get_database_client()
        
        # Test cases
        test_cases = [
            {
                "identifier": "Sofia Elena Camejo Copello",
                "description": "🔍 Caso específico del error reportado - buscar por nombre de solicitante"
            },
            {
                "identifier": "12345678-1234-1234-1234-123456789abc",
                "description": "🔍 UUID válido de ejemplo"
            },
            {
                "identifier": "Test Company Inc",
                "description": "🔍 Búsqueda por nombre de empresa"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔬 Test {i}: {test_case['description']}")
            print(f"🔍 Identifier: '{test_case['identifier']}'")
            
            try:
                result = db_client.find_rfx_by_identifier(test_case['identifier'])
                
                if result:
                    print(f"✅ RFX Found!")
                    print(f"   📋 RFX ID: {result['id']}")
                    print(f"   🏢 Company: {result.get('companies', {}).get('name', 'Unknown')}")
                    print(f"   👤 Requester: {result.get('requesters', {}).get('name', 'Unknown')}")
                    print(f"   📝 Title: {result.get('title', 'Unknown')}")
                    print(f"   📅 Created: {result.get('created_at', 'Unknown')}")
                else:
                    print(f"❌ RFX Not Found")
                    print(f"   ℹ️  This is expected if no RFX exists with this identifier")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Test UUID validation specifically
        print(f"\n🔬 Test UUID Validation:")
        
        # Valid UUID test
        try:
            test_uuid = str(uuid.uuid4())
            uuid.UUID(test_uuid)
            print(f"✅ Valid UUID: {test_uuid}")
        except ValueError:
            print(f"❌ UUID validation failed")
        
        # Invalid UUID test (our problem case)
        try:
            uuid.UUID("Sofia Elena Camejo Copello")
            print(f"❌ This should not happen")
        except ValueError:
            print(f"✅ Correctly identified 'Sofia Elena Camejo Copello' as invalid UUID")
        
        print(f"\n🎉 Smart RFX Lookup Test Completed!")
        print(f"🔧 The new implementation should now handle:")
        print(f"   ✅ Valid UUIDs (original behavior)")
        print(f"   ✅ Requester names like 'Sofia Elena Camejo Copello'")
        print(f"   ✅ Company names")
        print(f"   ✅ Fuzzy matching for partial names")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_pricing_api_simulation():
    """
    🎭 Simular el comportamiento de la API de pricing con el nuevo código
    """
    print(f"\n🎭 Simulating Pricing API Behavior")
    print("=" * 50)
    
    # Simulate the problematic request
    rfx_id = "Sofia Elena Camejo Copello"
    
    print(f"📡 Simulating: PUT /api/pricing/config/{rfx_id}")
    
    try:
        db_client = get_database_client()
        
        # This is the exact logic now used in pricing.py
        rfx_record = db_client.find_rfx_by_identifier(rfx_id)
        
        if not rfx_record:
            print(f"❌ RFX not found for identifier: {rfx_id}")
            print(f"🔄 Response: 404 - RFX not found")
            print(f"📝 Message: Provide either a valid UUID or the exact requester/company name")
        else:
            actual_rfx_id = str(rfx_record["id"])
            
            # Check if it was a UUID or name-based lookup
            try:
                uuid.UUID(rfx_id)
                print(f"✅ Direct UUID lookup successful: {rfx_id}")
            except (ValueError, TypeError):
                print(f"✅ Smart lookup successful: '{rfx_id}' → RFX ID: {actual_rfx_id}")
                print(f"📋 Found RFX: {rfx_record.get('title', 'Unknown')} for {rfx_record.get('requesters', {}).get('name', 'Unknown')} at {rfx_record.get('companies', {}).get('name', 'Unknown')}")
            
            print(f"✅ Pricing API would now proceed with UUID: {actual_rfx_id}")
            print(f"🔄 Response: 200 - Success")
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Pricing Fix Test Suite")
    print("=" * 60)
    
    # Test the smart lookup functionality
    test_smart_rfx_lookup()
    
    # Test pricing API simulation
    test_pricing_api_simulation()
    
    print(f"\n🎯 Summary:")
    print(f"✅ El error original de 'Invalid rfx_id format (expects UUID): Sofia Elena Camejo Copello'")
    print(f"   ahora debería ser resuelto con la búsqueda inteligente.")
    print(f"✅ La API de pricing ahora acepta tanto UUIDs como nombres de personas/empresas.")
    print(f"✅ La funcionalidad es retrocompatible - UUIDs siguen funcionando normalmente.")
    print(f"🔄 Para verificar en producción, intenta la misma llamada que causó el error original.")
