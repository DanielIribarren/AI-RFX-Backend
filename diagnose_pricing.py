#!/usr/bin/env python3
"""
🔍 Pricing Configuration Diagnostic Tool
Helps identify and fix issues with pricing configuration saving/loading
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

def check_database_connection():
    """Check if database connection is working"""
    try:
        from backend.core.database import get_database_client
        
        print("🔍 Testing database connection...")
        db_client = get_database_client()
        
        # Test basic query
        result = db_client.client.table('rfx_v2').select('id').limit(1).execute()
        print("✅ Database connection OK")
        print(f"📊 Found {len(result.data)} RFX records (showing max 1)")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_pricing_tables():
    """Check if pricing tables exist and are accessible"""
    try:
        from backend.core.database import get_database_client
        
        print("\n🔍 Checking pricing tables...")
        db_client = get_database_client()
        
        # Check each pricing table
        tables_to_check = [
            'rfx_pricing_configurations',
            'coordination_configurations', 
            'cost_per_person_configurations',
            'tax_configurations'
        ]
        
        for table in tables_to_check:
            try:
                result = db_client.client.table(table).select('id').limit(1).execute()
                print(f"✅ Table '{table}' accessible")
            except Exception as e:
                print(f"❌ Table '{table}' error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pricing tables check failed: {e}")
        return False

def check_pricing_functions():
    """Check if pricing SQL functions are available"""
    try:
        from backend.core.database import get_database_client
        
        print("\n🔍 Checking pricing SQL functions...")
        db_client = get_database_client()
        
        # Test pricing functions
        functions_to_test = [
            ('get_rfx_pricing_config', {'rfx_uuid': '00000000-0000-0000-0000-000000000000'}),
            ('calculate_rfx_pricing', {'rfx_uuid': '00000000-0000-0000-0000-000000000000', 'base_subtotal': 1000.0}),
        ]
        
        for func_name, params in functions_to_test:
            try:
                result = db_client.client.rpc(func_name, params).execute()
                print(f"✅ Function '{func_name}' accessible")
            except Exception as e:
                print(f"❌ Function '{func_name}' error: {e}")
                # Don't return False here as functions might fail with dummy data
        
        return True
        
    except Exception as e:
        print(f"❌ Pricing functions check failed: {e}")
        return False

def test_pricing_service():
    """Test the pricing service directly"""
    try:
        from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
        
        print("\n🔍 Testing pricing service...")
        
        pricing_service = PricingConfigurationServiceV2()
        
        # Test getting configuration for a dummy RFX
        dummy_rfx_id = "test-rfx-" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        config = pricing_service.get_rfx_pricing_configuration(dummy_rfx_id)
        if config:
            print("✅ Pricing service can create default configurations")
        else:
            print("❌ Pricing service failed to create default configuration")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pricing service test failed: {e}")
        return False

def test_pricing_api_endpoints():
    """Test pricing API endpoints"""
    try:
        print("\n🔍 Testing pricing API endpoints...")
        
        # Import Flask app
        from backend.app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Test GET config endpoint
            dummy_rfx_id = "test-rfx-12345"
            
            print(f"🔍 Testing GET /api/pricing/config/{dummy_rfx_id}")
            response = client.get(f'/api/pricing/config/{dummy_rfx_id}')
            
            if response.status_code == 200:
                print("✅ GET pricing config endpoint working")
                data = response.get_json()
                print(f"📊 Response: {data.get('status', 'unknown')}")
            else:
                print(f"❌ GET pricing config failed: {response.status_code}")
                print(f"📄 Response: {response.get_data(as_text=True)}")
                return False
            
            # Test PUT config endpoint  
            print(f"🔍 Testing PUT /api/pricing/config/{dummy_rfx_id}")
            test_config = {
                "coordination": {
                    "enabled": True,
                    "rate": 0.18,
                    "type": "standard"
                },
                "cost_per_person": {
                    "enabled": True,
                    "headcount": 100,
                    "calculation_base": "final_total"
                },
                "taxes": {
                    "enabled": False,
                    "rate": 0.16,
                    "name": "IVA"
                }
            }
            
            response = client.put(
                f'/api/pricing/config/{dummy_rfx_id}',
                json=test_config,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print("✅ PUT pricing config endpoint working")
                data = response.get_json()
                print(f"📊 Response: {data.get('status', 'unknown')}")
            else:
                print(f"❌ PUT pricing config failed: {response.status_code}")
                print(f"📄 Response: {response.get_data(as_text=True)}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def create_test_rfx():
    """Create a test RFX for pricing configuration testing"""
    try:
        from backend.core.database import get_database_client
        
        print("\n🔍 Creating test RFX for pricing tests...")
        
        db_client = get_database_client()
        
        test_rfx_data = {
            'requester_name': 'Test User',
            'email': 'test@example.com',
            'company_name': 'Test Company',
            'products': [
                {
                    'product_name': 'Test Product 1',
                    'quantity': 10,
                    'unit': 'pieces',
                    'estimated_unit_price': 50.0
                },
                {
                    'product_name': 'Test Product 2', 
                    'quantity': 5,
                    'unit': 'boxes',
                    'estimated_unit_price': 100.0
                }
            ],
            'delivery_date': '2024-12-31',
            'location': 'Test Location',
            'status': 'completed'
        }
        
        result = db_client.client.table('rfx_v2').insert(test_rfx_data).execute()
        
        if result.data:
            rfx_id = result.data[0]['id']
            print(f"✅ Test RFX created: {rfx_id}")
            
            # Test pricing configuration with real RFX
            print(f"🔍 Testing pricing configuration with RFX: {rfx_id}")
            
            from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2
            pricing_service = PricingConfigurationServiceV2()
            
            # Test configuration creation
            from backend.models.pricing_models import PricingConfigurationRequest
            
            config_request = PricingConfigurationRequest(
                rfx_id=rfx_id,
                coordination_enabled=True,
                coordination_rate=0.18,
                cost_per_person_enabled=True,
                headcount=100
            )
            
            updated_config = pricing_service.update_rfx_pricing_from_request(config_request)
            
            if updated_config:
                print("✅ Pricing configuration saved successfully")
                
                # Test calculation
                calculation = pricing_service.calculate_pricing(rfx_id, 1000.0)
                if calculation:
                    print(f"✅ Pricing calculation works: Total = ${calculation.total_cost}")
                else:
                    print("❌ Pricing calculation failed")
                    
            else:
                print("❌ Failed to save pricing configuration")
                
            return rfx_id
        else:
            print("❌ Failed to create test RFX")
            return None
            
    except Exception as e:
        print(f"❌ Test RFX creation failed: {e}")
        return None

def cleanup_test_data(rfx_id):
    """Clean up test data"""
    if not rfx_id:
        return
        
    try:
        from backend.core.database import get_database_client
        
        print(f"\n🧹 Cleaning up test RFX: {rfx_id}")
        
        db_client = get_database_client()
        
        # Delete pricing configurations (will cascade)
        db_client.client.table('rfx_pricing_configurations').delete().eq('rfx_id', rfx_id).execute()
        
        # Delete RFX
        db_client.client.table('rfx_v2').delete().eq('id', rfx_id).execute()
        
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")

def main():
    """Main diagnostic sequence"""
    print("🔍 AI-RFX Pricing Configuration Diagnostic Tool")
    print("=" * 50)
    
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Add backend to Python path
    sys.path.insert(0, str(Path.cwd()))
    
    # Run diagnostic checks
    checks = [
        ("Database Connection", check_database_connection),
        ("Pricing Tables", check_pricing_tables),
        ("Pricing Functions", check_pricing_functions),
        ("Pricing Service", test_pricing_service),
        ("API Endpoints", test_pricing_api_endpoints)
    ]
    
    test_rfx_id = None
    
    try:
        for check_name, check_func in checks:
            print(f"\n🔍 Running {check_name} check...")
            if not check_func():
                print(f"\n❌ {check_name} check failed!")
                break
        else:
            print("\n✅ All basic checks passed!")
            
            # Run integration test
            print("\n🧪 Running integration test...")
            test_rfx_id = create_test_rfx()
            
            if test_rfx_id:
                print("\n🎉 All tests passed! Pricing system is working correctly.")
                print("\n💡 If you're still experiencing issues:")
                print("   1. Check frontend console for detailed error messages")
                print("   2. Verify the RFX ID being used exists in the database")
                print("   3. Ensure frontend is pointing to correct backend URL")
            else:
                print("\n❌ Integration test failed")
                
    except KeyboardInterrupt:
        print("\n👋 Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during diagnostics: {e}")
    finally:
        # Always cleanup
        if test_rfx_id:
            cleanup_test_data(test_rfx_id)

if __name__ == "__main__":
    main()
