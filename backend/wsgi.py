"""
🚀 WSGI Entry Point - Production deployment entry point
For use with Gunicorn, uWSGI, or other WSGI servers
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the application factory
from backend.app import create_app

# Create application instance for WSGI server
application = create_app()

if __name__ == "__main__":
    # This won't be called when using a WSGI server, but useful for testing
    application.run()
