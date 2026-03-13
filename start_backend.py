#!/usr/bin/env python3
"""
🚀 Backend Startup Script - AI-RFX System
Checks configuration, validates environment, and starts the backend with proper logging
"""
import os
import sys
import subprocess
import argparse
import hashlib
import json
from pathlib import Path
from dotenv import load_dotenv  # 👈 Agregar esta línea

# Global variable to store virtual environment Python path
VENV_PYTHON = None
DEPENDENCY_STAMP_FILE = Path(".cache/dependency-state.json")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version OK: {sys.version}")
    return True

def configure_cairo_environment():
    """Configure Cairo library paths for macOS and check system dependencies"""
    import platform
    
    print("🔧 Configuring system environment...")
    
    if platform.system() == 'Darwin':  # macOS
        print("🍎 Detected macOS - configuring Cairo environment...")
        
        # Add Homebrew library paths
        homebrew_paths = [
            "/opt/homebrew/lib",  # Apple Silicon
            "/usr/local/lib"      # Intel Mac
        ]
        
        pkg_config_paths = [
            "/opt/homebrew/lib/pkgconfig",
            "/opt/homebrew/share/pkgconfig",
            "/usr/local/lib/pkgconfig"
        ]
        
        # Set DYLD_LIBRARY_PATH
        current_dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
        new_dyld = ':'.join(homebrew_paths + ([current_dyld] if current_dyld else []))
        os.environ['DYLD_LIBRARY_PATH'] = new_dyld
        
        # Set PKG_CONFIG_PATH
        current_pkg = os.environ.get('PKG_CONFIG_PATH', '')
        new_pkg = ':'.join(pkg_config_paths + ([current_pkg] if current_pkg else []))
        os.environ['PKG_CONFIG_PATH'] = new_pkg
        
        print("✅ Cairo environment configured")
    else:
        print("✅ Cairo configuration not needed (not macOS)")
    
    # Check critical system dependencies
    print("🔍 Checking system dependencies...")
    
    # Check Poppler (for PDF processing)
    try:
        result = subprocess.run(['pdfinfo', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Poppler is installed")
        else:
            print("⚠️  Poppler not found - PDF processing may fail")
            print("   💡 Install with: brew install poppler (macOS)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  Poppler not found - PDF processing may fail")
        if platform.system() == 'Darwin':
            print("   💡 Install with: brew install poppler")
        elif platform.system() == 'Linux':
            print("   💡 Install with: sudo apt-get install poppler-utils")
        else:
            print("   💡 See INSTALL_SYSTEM_DEPENDENCIES.md for instructions")
    
    return True

def check_system_dependencies():
    """Check if system dependencies verification script exists and run it"""
    deps_script = Path("scripts/check_system_dependencies.py")
    
    if deps_script.exists():
        print("🔍 Running system dependencies check...")
        
        # Use virtual environment Python if available
        python_executable = VENV_PYTHON if VENV_PYTHON else sys.executable
        
        try:
            result = subprocess.run([
                python_executable, str(deps_script)
            ], capture_output=True, text=True, timeout=30)
            
            # Always show the output (both success and warnings)
            if result.stdout:
                print(result.stdout.strip())
            
            if result.returncode == 0:
                print("✅ All critical system dependencies are ready")
                return True
            else:
                print("⚠️  Some system dependencies are missing (see above)")
                print("   ℹ️  System will use fallback methods where possible")
                return True  # Don't fail startup, just warn
                
        except subprocess.TimeoutExpired:
            print("⚠️  System dependencies check timed out")
            return True
        except Exception as e:
            print(f"⚠️  Could not run system dependencies check: {e}")
            return True
    else:
        print("ℹ️  System dependencies checker not found - skipping")
        return True

def check_virtual_environment():
    """Check if virtual environment is activated or activate automatically"""
    venv_path = Path("venv")
    
    # If virtual environment doesn't exist, create it
    if not venv_path.exists():
        print("⚠️  Virtual environment not found")
        print("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    # Check if we're already in the virtual environment
    if sys.prefix != sys.base_prefix:
        print("✅ Virtual environment already activated")
        return True
    
    # Not in virtual environment - try to use it automatically
    print("⚠️  Virtual environment not activated")
    print("🔄 Will use virtual environment automatically...")
    
    # Set the virtual environment python path
    if os.name == 'nt':  # Windows
        venv_python = venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/MacOS
        venv_python = venv_path / "bin" / "python"
    
    if not venv_python.exists():
        print(f"❌ Virtual environment Python not found at: {venv_python}")
        return False
    
    # Store the venv python path for later use
    global VENV_PYTHON
    VENV_PYTHON = str(venv_python)
    
    print(f"✅ Virtual environment Python found: {venv_python}")
    return True

def _requirements_hash(requirements_file: Path) -> str:
    """Return a stable hash of requirements file content."""
    hasher = hashlib.sha256()
    hasher.update(requirements_file.read_bytes())
    return hasher.hexdigest()


def _load_dependency_state() -> dict:
    """Load dependency state file if present."""
    try:
        if DEPENDENCY_STAMP_FILE.exists():
            return json.loads(DEPENDENCY_STAMP_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_dependency_state(requirements_hash: str, python_executable: str) -> None:
    """Persist dependency state after successful installation."""
    DEPENDENCY_STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEPENDENCY_STAMP_FILE.write_text(
        json.dumps(
            {
                "requirements_hash": requirements_hash,
                "python_executable": python_executable,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _dependencies_need_install(requirements_file: Path, python_executable: str, force_install: bool) -> bool:
    """Install only when dependencies changed or when forced."""
    if force_install:
        return True

    if not requirements_file.exists():
        return False

    current_hash = _requirements_hash(requirements_file)
    state = _load_dependency_state()

    return (
        state.get("requirements_hash") != current_hash
        or state.get("python_executable") != python_executable
    )


def install_dependencies(force_install: bool = False, skip_install: bool = False):
    """Install required dependencies"""
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("⚠️  requirements.txt not found")
        return False
    
    # Use virtual environment Python if available
    python_executable = VENV_PYTHON if VENV_PYTHON else sys.executable

    if skip_install:
        print("⏭️  Skipping dependency installation (--skip-deps)")
        return True

    needs_install = _dependencies_need_install(
        requirements_file=requirements_file,
        python_executable=python_executable,
        force_install=force_install,
    )
    if not needs_install:
        print("✅ Dependencies unchanged - skipping installation")
        print("💡 Use --force-install-deps to reinstall anyway")
        return True
    
    print("📦 Installing dependencies...")
    print(f"🐍 Using Python: {python_executable}")
    
    try:
        subprocess.run([
            python_executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        _save_dependency_state(
            requirements_hash=_requirements_hash(requirements_file),
            python_executable=python_executable,
        )
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_environment_file():
    """Check env files, load .env and optional .env.<environment> override."""
    from dotenv import load_dotenv
    
    env_file = Path(".env")
    template_file = Path("environment_template.txt")
    
    if not env_file.exists():
        print("⚠️  .env file not found")
        if template_file.exists():
            print(f"📄 Please copy {template_file} to .env and configure it")
        else:
            print("📄 Please create a .env file with the required environment variables")
        
        print("\n📋 Required environment variables:")
        print("- SUPABASE_URL")
        print("- SUPABASE_ANON_KEY") 
        print("- OPENAI_API_KEY")
        print("- SECRET_KEY")
        return False
    
    print("🔄 Loading environment variables from .env...")
    load_dotenv(env_file)

    env_name = os.environ.get("ENVIRONMENT", "development").strip().lower()
    env_specific_file = Path(f".env.{env_name}")
    if env_specific_file.exists():
        print(f"🔄 Loading environment override from {env_specific_file}...")
        load_dotenv(env_specific_file, override=True)
    
    # Check for required variables (ahora desde os.environ)
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing or empty environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ Environment variables loaded successfully")
    return True

def test_backend_startup():
    """Test if backend can start successfully"""
    print("🧪 Testing backend startup...")
    
    # Use virtual environment Python if available
    python_executable = VENV_PYTHON if VENV_PYTHON else sys.executable
    
    try:
        # Test imports using the correct Python executable
        test_script = '''
import sys
sys.path.insert(0, ".")
try:
    from backend.app import create_app
    app = create_app()
    with app.test_client() as client:
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ Health check endpoint working")
            exit(0)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            exit(1)
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Backend startup error: {e}")
    exit(1)
'''
        
        # Run test in subprocess with correct Python
        result = subprocess.run([
            python_executable, "-c", test_script
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Backend imports successfully")
            print(result.stdout.strip())
            return True
        else:
            print("❌ Backend test failed")
            if result.stdout:
                print("STDOUT:", result.stdout.strip())
            if result.stderr:
                print("STDERR:", result.stderr.strip())
            return False
                
    except subprocess.TimeoutExpired:
        print("❌ Backend test timed out")
        return False
    except Exception as e:
        print(f"❌ Backend test error: {e}")
        return False

def start_backend():
    """Start the backend server with enhanced logging"""
    print("🚀 Starting AI-RFX Backend...")
    print("📊 Server will be available at: http://localhost:5001")
    print("🔍 API endpoints will be at: http://localhost:5001/api/")
    print("📋 Health check: http://localhost:5001/health")
    print("💰 Pricing API: http://localhost:5001/api/pricing/")
    print("\n📋 Key Pricing Endpoints:")
    print("   GET  /api/pricing/config/{rfx_id}    - Get configuration")
    print("   PUT  /api/pricing/config/{rfx_id}    - Save configuration") 
    print("   POST /api/pricing/calculate/{rfx_id} - Calculate pricing")
    print("   GET  /api/pricing/presets            - Get presets")
    print("\n💡 Press Ctrl+C to stop the server")
    print("💡 Check logs below for detailed startup information")
    print("=" * 60)
    
    try:
        # Set environment variables for enhanced logging
        env = os.environ.copy()
        env['FLASK_ENV'] = 'development'
        env['FLASK_DEBUG'] = '1'
        env['PYTHONUNBUFFERED'] = '1'  # Force Python to not buffer output
        env['PORT'] = '5001'  # Configure Flask to use port 5001 for local development
        env['ENVIRONMENT'] = 'development'  # Ensure development environment
        
        # 🔥 FIX: Add current directory to PYTHONPATH so Python can find 'backend' module
        current_dir = os.path.abspath(".")
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{current_dir}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = current_dir
        
        print("🔍 Starting backend with detailed logging...")
        print("📄 Backend logs will appear below:")
        print("-" * 40)
        
        # 🔥 FIX: Determine the correct Python executable path BEFORE changing directory
        if VENV_PYTHON:
            # Convert to absolute path to avoid issues when changing directories
            python_executable = os.path.abspath(VENV_PYTHON)
        else:
            python_executable = sys.executable
        
        print(f"🐍 Using Python: {python_executable}")
        
        # Verify the Python executable exists
        if not os.path.exists(python_executable):
            print(f"❌ Error: Python executable not found at: {python_executable}")
            # Fallback to system Python
            python_executable = sys.executable
            print(f"🔄 Falling back to system Python: {python_executable}")
        
        # Stay in current directory - app.py expects to be run from project root
        original_dir = os.getcwd()  # Save current directory for safety
        
        # Use Popen to get real-time output - run from project root
        process = subprocess.Popen(
            [python_executable, "backend/app.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output in real-time
        try:
            for line in process.stdout:
                print(line.rstrip())
        except KeyboardInterrupt:
            print("\n👋 Stopping backend...")
            process.terminate()
            process.wait()
            print("✅ Backend stopped cleanly")
        finally:
            # Always return to original directory
            os.chdir(original_dir)
            
    except KeyboardInterrupt:
        print("\n👋 Backend stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Backend failed to start: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("1. Check if .env file exists and is configured")
        print("2. Verify database connection (SUPABASE_URL, SUPABASE_ANON_KEY)")
        print("3. Check OpenAI API key (OPENAI_API_KEY)")
        print("4. Run: python3 diagnose_pricing.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("\n🔍 Try running: python3 diagnose_pricing.py")
        return False

def main():
    """Main startup sequence"""
    parser = argparse.ArgumentParser(
        description="AI-RFX backend bootstrap and startup script"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run startup checks without starting the backend server",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Ask for confirmation before starting the backend (legacy behavior)",
    )
    parser.add_argument(
        "--force-install-deps",
        action="store_true",
        help="Force reinstalling Python dependencies even when unchanged",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation step",
    )
    args = parser.parse_args()

    print("🚀 AI-RFX Backend Startup Script")
    print("=" * 40)
    
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Run startup checks
    checks = [
        ("Python Version", check_python_version),
        ("System Environment", configure_cairo_environment),
        ("Virtual Environment", check_virtual_environment),
        (
            "Dependencies",
            lambda: install_dependencies(
                force_install=args.force_install_deps,
                skip_install=args.skip_deps,
            ),
        ),
        ("System Dependencies", check_system_dependencies),
        ("Environment Configuration", check_environment_file),
        ("Backend Startup Test", test_backend_startup)
    ]
    
    for check_name, check_func in checks:
        print(f"\n🔍 Checking {check_name}...")
        if not check_func():
            print(f"\n❌ {check_name} check failed. Please fix the issues above and try again.")
            return False
    
    print("\n✅ All checks passed!")
    print("🎯 Ready to start backend")

    if args.check_only:
        print("✅ Check-only mode completed successfully")
        return True

    # New default behavior: start automatically to simplify local workflow
    if args.prompt:
        try:
            start_now = input("\n🚀 Start backend server now? (y/N): ").lower().strip()
            if start_now in ['y', 'yes']:
                start_backend()
            else:
                print("👋 Startup cancelled by user")
                print("💡 Run 'python3 start_backend.py' to start the server when ready")
        except KeyboardInterrupt:
            print("\n👋 Startup cancelled by user")
    else:
        print("▶️  Auto-start enabled (use --prompt to ask before starting)")
        start_backend()

if __name__ == "__main__":
    main()
