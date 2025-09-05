#!/usr/bin/env python3
"""
🚀 Backend Startup Script - AI-RFX System
Checks configuration, validates environment, and starts the backend with proper logging
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv  # 👈 Agregar esta línea

# Global variable to store virtual environment Python path
VENV_PYTHON = None

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version OK: {sys.version}")
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

def install_dependencies():
    """Install required dependencies"""
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("⚠️  requirements.txt not found")
        return False
    
    # Use virtual environment Python if available
    python_executable = VENV_PYTHON if VENV_PYTHON else sys.executable
    
    print("📦 Installing dependencies...")
    print(f"🐍 Using Python: {python_executable}")
    
    try:
        subprocess.run([
            python_executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_environment_file():
    """Check if .env file exists, has required variables, and load them"""
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
    
    # 🔥 AQUÍ ESTÁ LA CLAVE: Cargar las variables del .env
    print("🔄 Loading environment variables from .env...")
    load_dotenv(env_file)
    
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
        env['PORT'] = '5001'  # Configure Flask to use port 5001
        
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
    print("🚀 AI-RFX Backend Startup Script")
    print("=" * 40)
    
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Run startup checks
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", install_dependencies),
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
    
    # Ask user if they want to start the server
    try:
        start_now = input("\n🚀 Start backend server now? (y/N): ").lower().strip()
        if start_now in ['y', 'yes']:
            start_backend()
        else:
            print("👋 Startup cancelled by user")
            print("💡 Run 'python3 start_backend.py' to start the server when ready")
    except KeyboardInterrupt:
        print("\n👋 Startup cancelled by user")

if __name__ == "__main__":
    main()
