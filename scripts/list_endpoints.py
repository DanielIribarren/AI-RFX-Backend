#!/usr/bin/env python3
"""
Script to list all active endpoints in the Flask application.
Used for pre-refactor validation.
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.app import create_app

def list_endpoints():
    """List all registered endpoints"""
    app = create_app()
    
    print("=" * 80)
    print("🔍 ACTIVE ENDPOINTS IN BACKEND")
    print("=" * 80)
    print()
    
    # Group by blueprint
    endpoints_by_blueprint = {}
    
    for rule in app.url_map.iter_rules():
        # Skip static
        if rule.endpoint == 'static':
            continue
            
        # Extract blueprint name
        if '.' in rule.endpoint:
            blueprint = rule.endpoint.split('.')[0]
        else:
            blueprint = 'main'
        
        if blueprint not in endpoints_by_blueprint:
            endpoints_by_blueprint[blueprint] = []
        
        methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
        endpoints_by_blueprint[blueprint].append({
            'endpoint': rule.endpoint,
            'path': rule.rule,
            'methods': methods
        })
    
    # Print grouped by blueprint
    for blueprint, endpoints in sorted(endpoints_by_blueprint.items()):
        print(f"📦 {blueprint.upper()}")
        print("-" * 80)
        for ep in sorted(endpoints, key=lambda x: x['path']):
            methods_str = ', '.join(ep['methods'])
            print(f"  {methods_str:20} {ep['path']:50} [{ep['endpoint']}]")
        print()
    
    # Summary
    total = sum(len(eps) for eps in endpoints_by_blueprint.values())
    print("=" * 80)
    print(f"📊 TOTAL: {total} endpoints across {len(endpoints_by_blueprint)} blueprints")
    print("=" * 80)

if __name__ == '__main__':
    list_endpoints()
