"""
Vercel serverless entrypoint for the Flask backend.
"""
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Keep relative paths stable for modules that read/write files.
os.chdir(PROJECT_ROOT)

# Force production defaults in Vercel unless explicitly overridden.
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("UPLOAD_FOLDER", "/tmp/rfx_uploads")

from backend.app import app  # noqa: E402
