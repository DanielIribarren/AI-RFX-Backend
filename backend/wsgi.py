"""
🚀 WSGI Entry Point - Production deployment entry point
For use with Gunicorn, uWSGI, or other WSGI servers
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load base + environment-specific variables.
load_dotenv(".env")
_env_name = os.getenv("ENVIRONMENT", "development").strip().lower()
_env_specific_file = Path(f".env.{_env_name}")
if _env_specific_file.exists():
    load_dotenv(_env_specific_file, override=True)

# Import the application factory
from backend.app import create_app

# Create application instance for WSGI server with robust error logging
try:
    application = create_app()
except Exception as e:
    import traceback, sys
    # Print full traceback so Railway/Gunicorn logs show the real root cause
    print("❌ Failed to initialize WSGI application:", e, file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    # Re-raise to let Gunicorn crash with clear logs
    raise

if __name__ == "__main__":
    # This won't be called when using a WSGI server, but useful for testing
    application.run()
