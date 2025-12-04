#!/bin/bash
# ============================================================================
# SETUP PARA PM2 (Servidor de Producción)
# ============================================================================
# Este script configura el entorno para PM2 de forma rápida y eficiente.
#
# Uso en servidor:
#   chmod +x setup_pm2.sh
#   ./setup_pm2.sh
# ============================================================================

set -e  # Exit on error

echo "🚀 Configurando entorno para PM2..."

# 1. Instalar dependencias base (sin LangChain)
echo "📦 Instalando dependencias base..."
pip install -r requirements.txt --no-deps || true

# 2. Instalar dependencias que SÍ necesitan resolver (las críticas)
echo "📦 Instalando dependencias críticas con resolución..."
pip install \
    flask \
    flask-cors \
    supabase \
    openai \
    python-dotenv \
    pydantic \
    playwright \
    PyPDF2 \
    python-docx \
    pytesseract \
    Pillow \
    pdf2image

# 3. Instalar LangChain (modo rápido)
echo "🦜 Instalando LangChain (modo rápido)..."
./install_langchain_fast.sh

# 4. Instalar navegadores de Playwright
echo "🌐 Instalando navegadores de Playwright..."
playwright install chromium

echo ""
echo "✅ Configuración completada!"
echo ""
echo "Para iniciar con PM2:"
echo "  pm2 start ecosystem.dev.config.js"
echo "  pm2 logs"
