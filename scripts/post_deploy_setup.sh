#!/bin/bash

# 🚀 Script de Post-Deploy Automático para PM2
# Se ejecuta automáticamente después de cada deploy/restart
# Configura Playwright y verifica dependencias

set -e  # Salir si hay algún error

echo "🚀 =========================================="
echo "🚀 POST-DEPLOY SETUP - INICIANDO..."
echo "🚀 =========================================="

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📁 Directorio del proyecto: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Función para logging con timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    log "❌ Error: No se encontró requirements.txt. Verificar directorio."
    exit 1
fi

log "✅ Directorio del proyecto verificado"

# 2. Activar entorno virtual si existe
if [ -d "venv" ]; then
    log "🐍 Activando entorno virtual..."
    source venv/bin/activate
    log "✅ Entorno virtual activado"
else
    log "⚠️  No se encontró entorno virtual, usando Python del sistema"
fi

# 3. Verificar instalación de Playwright
log "🔍 Verificando Playwright..."
if python -c "import playwright" 2>/dev/null; then
    log "✅ Playwright Python package instalado"
else
    log "📦 Instalando Playwright desde requirements.txt..."
    pip install playwright
fi

# 4. Verificar navegadores de Playwright
log "🌐 Verificando navegadores de Playwright..."
if python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(headless=True); browser.close(); p.stop()" 2>/dev/null; then
    log "✅ Chromium ya está instalado y funciona correctamente"
else
    log "📥 Instalando navegadores de Playwright..."
    
    # Instalar solo Chromium para ahorrar espacio y tiempo
    playwright install chromium
    
    # Verificar instalación
    if python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(headless=True); browser.close(); p.stop()" 2>/dev/null; then
        log "✅ Chromium instalado y verificado correctamente"
    else
        log "⚠️  Chromium instalado pero necesita dependencias del sistema"
        
        # Instalar dependencias del sistema automáticamente
        if command -v apt-get &> /dev/null; then
            log "📦 Instalando dependencias del sistema (Ubuntu/Debian)..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
            playwright install-deps chromium
        elif command -v yum &> /dev/null; then
            log "📦 Instalando dependencias del sistema (CentOS/RHEL)..."
            sudo yum install -y -q nss atk at-spi2-atk libdrm libxkbcommon libXcomposite libXdamage libXrandr mesa-libgbm libXScrnSaver alsa-lib
        fi
    fi
fi

# 5. Verificar estructura de directorios necesarios
log "📁 Verificando directorios necesarios..."

# Crear directorio de logs si no existe
if [ ! -d "logs" ]; then
    mkdir -p logs
    log "✅ Directorio logs creado"
fi

# Crear directorio de uploads si no existe
if [ ! -d "/tmp/rfx_uploads" ]; then
    sudo mkdir -p /tmp/rfx_uploads
    sudo chmod 755 /tmp/rfx_uploads
    log "✅ Directorio de uploads creado"
fi

# Verificar directorio de branding
if [ ! -d "backend/static/branding" ]; then
    mkdir -p backend/static/branding
    log "✅ Directorio de branding creado"
fi

# 6. Verificar permisos
log "🔒 Verificando permisos..."
chmod +x scripts/*.sh 2>/dev/null || true

# 7. Test rápido de funcionalidad crítica
log "🧪 Ejecutando tests de funcionalidad..."

# Test de importación de módulos críticos
python -c "
try:
    import flask
    import supabase
    import playwright
    from playwright.sync_api import sync_playwright
    print('✅ Todas las dependencias críticas importadas correctamente')
except ImportError as e:
    print(f'❌ Error de importación: {e}')
    exit(1)
" || exit 1

# Test de Playwright funcional
python -c "
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content('<html><body><h1>Test</h1></body></html>')
        browser.close()
    print('✅ Playwright funciona correctamente')
except Exception as e:
    print(f'❌ Error en Playwright: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    log "✅ Test de Playwright exitoso"
else
    log "❌ Error en test de Playwright"
    exit 1
fi

echo ""
log "🎉 =========================================="
log "🎉 POST-DEPLOY SETUP COMPLETADO EXITOSAMENTE"
log "🎉 =========================================="
echo ""
log "📋 Resumen:"
log "   ✅ Playwright instalado y configurado"
log "   ✅ Navegadores verificados y funcionales"
log "   ✅ Directorios necesarios creados"
log "   ✅ Permisos configurados"
log "   ✅ Tests de funcionalidad exitosos"
echo ""
log "🚀 El servidor está listo para generar PDFs!"
