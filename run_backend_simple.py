#!/usr/bin/env python3
"""
🚀 AI-RFX Application Launcher
Unified entry point for the cleaned architecture
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load base + environment-specific variables.
load_dotenv(".env")
_env_name = os.getenv("ENVIRONMENT", "development").strip().lower()
_env_specific_file = Path(f".env.{_env_name}")
if _env_specific_file.exists():
    load_dotenv(_env_specific_file, override=True)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main application
from backend.app import app

if __name__ == "__main__":
    # Get configuration from environment variables
    port = int(os.getenv('PORT', '3186'))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    environment = os.getenv('ENVIRONMENT', 'development')
    
    print("🚀 Starting AI-RFX Backend (Unified Architecture)")
    print(f"🌍 Environment: {environment}")
    print(f"📡 API available at: http://{host}:{port}")
    print("🔧 Endpoints:")
    print("   - POST /api/rfx/process")
    print("   - POST /api/proposals/generate")
    print("   - GET  /api/rfx/history")
    print("   - GET  /health/detailed")
    print("=" * 50)
    
    # Start the application with environment configuration
    app.run(host=host, port=port, debug=debug)
