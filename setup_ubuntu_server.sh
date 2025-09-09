#!/bin/bash
# 🚀 Setup script for Ubuntu Server - AI-RFX Backend

echo "🚀 Setting up AI-RFX Backend on Ubuntu Server"
echo "============================================="

# Change to project directory
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Create upload directory
echo "📁 Creating upload directory..."
mkdir -p /tmp/rfx_uploads

# Set permissions
echo "🔐 Setting permissions..."
chmod +x ./venv/bin/python
chmod +x ./venv/bin/gunicorn

# Test installation
echo "🧪 Testing Flask installation..."
./venv/bin/python -c "import flask; print('✅ Flask installed successfully')" || {
    echo "❌ Flask installation failed"
    exit 1
}

echo "🧪 Testing application imports..."
./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from backend.app import app
    print('✅ Application imports successfully')
except Exception as e:
    print(f'❌ Application import failed: {e}')
    exit(1)
" || {
    echo "❌ Application test failed"
    exit 1
}

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 To start the applications:"
echo "   🖥️  Ubuntu Development (port 3186): pm2 start ecosystem.dev.config.js"
echo "   🏭 Ubuntu Production (port 3187):  pm2 start ecosystem.prod.config.js"
echo "   📱 Interactive Management:         ./start-pm2.sh"
echo ""
echo "📊 Management commands:"
echo "   Check status: pm2 status"
echo "   View logs:    pm2 logs ai-rfx-backend-dev"
echo "   Stop all:     pm2 stop all"
echo ""
echo "🔗 Endpoints after starting:"
echo "   Development: http://localhost:3186/health"
echo "   Production:  http://localhost:3187/health"
echo ""
echo "💡 For local development (port 5001): python3 start_backend.py"
