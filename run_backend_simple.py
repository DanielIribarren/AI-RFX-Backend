#!/usr/bin/env python3
"""
🚀 AI-RFX Application Launcher
Unified entry point for the cleaned architecture
"""
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main application
from backend.app import app

if __name__ == "__main__":
    print("🚀 Starting AI-RFX Backend (Unified Architecture)")
    print("📡 API available at: http://localhost:3186")
    print("🔧 Endpoints:")
    print("   - POST /api/rfx/process")
    print("   - POST /api/proposals/generate")
    print("   - GET  /api/rfx/history")
    print("   - GET  /health/detailed")
    print("=" * 50)
    
    # Start the application
    app.run(host='0.0.0.0', port=3186, debug=True)