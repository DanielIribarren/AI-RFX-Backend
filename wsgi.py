"""
WSGI configuration for AI-RFX Backend
For production deployment with gunicorn, uvicorn, etc.
"""
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the Flask application
from backend.app import app

# WSGI callable
application = app

if __name__ == "__main__":
    application.run()
