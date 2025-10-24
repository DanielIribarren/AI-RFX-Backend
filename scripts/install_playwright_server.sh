#!/bin/bash

# 🎭 Script de Instalación de Playwright para Servidor PM2
# Soluciona el problema: "Executable doesn't exist at /root/.cache/ms-playwright/chromium-1134/chrome-linux/chrome"

set -e  # Salir si hay algún error

echo "🎭 =========================================="
echo "🎭 INSTALACIÓN DE PLAYWRIGHT PARA SERVIDOR"
echo "🎭 =========================================="

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Ejecutar desde el directorio raíz del proyecto (donde está requirements.txt)"
    exit 1
fi

# Verificar si playwright está instalado
echo "🔍 Verificando instalación de Playwright..."
if ! python -c "import playwright" 2>/dev/null; then
    echo "❌ Playwright no está instalado. Instalando desde requirements.txt..."
    pip install playwright
else
    echo "✅ Playwright Python package ya está instalado"
fi

# Instalar navegadores de Playwright
echo "🌐 Instalando navegadores de Playwright..."
echo "📥 Descargando Chromium (necesario para PDF generation)..."

# Instalar solo Chromium para ahorrar espacio
playwright install chromium

# Verificar instalación
echo "🔍 Verificando instalación..."
if playwright --version > /dev/null 2>&1; then
    echo "✅ Playwright instalado correctamente!"
    playwright --version
else
    echo "❌ Error en la instalación de Playwright"
    exit 1
fi

# Verificar que Chromium esté disponible
echo "🔍 Verificando Chromium..."
if python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(); browser.close(); p.stop()" 2>/dev/null; then
    echo "✅ Chromium funciona correctamente!"
else
    echo "❌ Chromium no funciona. Instalando dependencias del sistema..."
    
    # Detectar sistema operativo e instalar dependencias
    if command -v apt-get &> /dev/null; then
        echo "📦 Instalando dependencias en Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
        playwright install-deps chromium
    elif command -v yum &> /dev/null; then
        echo "📦 Instalando dependencias en CentOS/RHEL..."
        sudo yum install -y nss atk at-spi2-atk libdrm libxkbcommon libXcomposite libXdamage libXrandr mesa-libgbm libXScrnSaver alsa-lib
        playwright install-deps chromium
    else
        echo "⚠️  Sistema operativo no reconocido. Instalar dependencias manualmente:"
        echo "   playwright install-deps chromium"
    fi
fi

echo ""
echo "🎉 =========================================="
echo "🎉 INSTALACIÓN COMPLETADA EXITOSAMENTE"
echo "🎉 =========================================="
echo ""
echo "📋 Próximos pasos:"
echo "   1. Reiniciar el servidor PM2:"
echo "      pm2 restart all"
echo ""
echo "   2. Verificar que los PDFs se generen correctamente"
echo ""
echo "🔧 Si sigues teniendo problemas:"
echo "   - Verificar permisos del directorio ~/.cache/ms-playwright/"
echo "   - Ejecutar: playwright install --force chromium"
echo ""
