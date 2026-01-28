#!/bin/bash

# 🚀 Setup Automático de Dependencias - AI-RFX Backend
# Este script se ejecuta ANTES de iniciar el servidor PM2
# Garantiza que todas las dependencias estén instaladas y actualizadas

set -e  # Salir si hay algún error

echo "🚀 =========================================="
echo "🚀 SETUP DE DEPENDENCIAS - INICIANDO..."
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

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================
# 1. VERIFICAR PYTHON Y PIP
# ============================================
log "🐍 Verificando Python y pip..."

if ! command_exists python3; then
    log "❌ Error: Python3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log "✅ Python encontrado: $PYTHON_VERSION"

if ! command_exists pip3; then
    log "❌ Error: pip3 no está instalado"
    exit 1
fi

log "✅ pip3 encontrado"

# ============================================
# 2. CREAR/ACTIVAR ENTORNO VIRTUAL
# ============================================
log "📦 Configurando entorno virtual..."

if [ ! -d "venv" ]; then
    log "🔨 Creando entorno virtual..."
    python3 -m venv venv
    log "✅ Entorno virtual creado"
else
    log "✅ Entorno virtual ya existe"
fi

# Activar entorno virtual
log "🔄 Activando entorno virtual..."
source venv/bin/activate
log "✅ Entorno virtual activado"

# Verificar que estamos en el venv
if [ -z "$VIRTUAL_ENV" ]; then
    log "❌ Error: No se pudo activar el entorno virtual"
    exit 1
fi

log "✅ Usando Python: $(which python)"
log "✅ Usando pip: $(which pip)"

# ============================================
# 3. ACTUALIZAR PIP Y SETUPTOOLS
# ============================================
log "⬆️  Actualizando pip y setuptools..."
pip install --upgrade pip setuptools wheel --quiet
log "✅ pip y setuptools actualizados"

# ============================================
# 4. INSTALAR/ACTUALIZAR DEPENDENCIAS
# ============================================
log "📦 Instalando dependencias desde requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    log "❌ Error: requirements.txt no encontrado"
    exit 1
fi

# Instalar dependencias con pip
# --no-cache-dir: No usar caché (garantiza versiones frescas)
# --upgrade: Actualizar paquetes si hay versiones nuevas
pip install -r requirements.txt --no-cache-dir --upgrade --quiet

if [ $? -eq 0 ]; then
    log "✅ Todas las dependencias instaladas correctamente"
else
    log "❌ Error instalando dependencias"
    exit 1
fi

# ============================================
# 5. INSTALAR PLAYWRIGHT BROWSERS
# ============================================
log "🌐 Configurando Playwright..."

# Verificar si Playwright está instalado
if python -c "import playwright" 2>/dev/null; then
    log "✅ Playwright Python package instalado"
    
    # Verificar si Chromium está instalado
    log "🔍 Verificando navegadores de Playwright..."
    
    if python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(headless=True); browser.close(); p.stop()" 2>/dev/null; then
        log "✅ Chromium ya está instalado y funciona"
    else
        log "📥 Instalando Chromium para Playwright..."
        playwright install chromium --with-deps
        
        if [ $? -eq 0 ]; then
            log "✅ Chromium instalado correctamente"
        else
            log "⚠️  Error instalando Chromium, intentando sin dependencias del sistema..."
            playwright install chromium
        fi
    fi
else
    log "❌ Error: Playwright no está en requirements.txt"
    exit 1
fi

# ============================================
# 6. VERIFICAR DEPENDENCIAS DEL SISTEMA
# ============================================
log "🔍 Verificando dependencias del sistema..."

# Verificar Poppler (para PDF processing)
if command_exists pdfinfo; then
    log "✅ Poppler instalado"
else
    log "⚠️  Poppler no encontrado - PDF processing FALLARÁ"
    
    # Intentar instalar automáticamente
    if command_exists apt-get; then
        log "📦 Instalando Poppler (Ubuntu/Debian)..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq poppler-utils
        
        # Verificar instalación exitosa
        if command_exists pdfinfo; then
            log "✅ Poppler instalado correctamente"
        else
            log "❌ Error: Poppler no se pudo instalar automáticamente"
            log "   💡 Ejecutar manualmente: sudo apt-get install -y poppler-utils"
            exit 1
        fi
    elif command_exists yum; then
        log "📦 Instalando Poppler (CentOS/RHEL)..."
        sudo yum install -y -q poppler-utils
        
        # Verificar instalación exitosa
        if command_exists pdfinfo; then
            log "✅ Poppler instalado correctamente"
        else
            log "❌ Error: Poppler no se pudo instalar automáticamente"
            log "   💡 Ejecutar manualmente: sudo yum install -y poppler-utils"
            exit 1
        fi
    elif command_exists brew; then
        log "📦 Instalando Poppler (macOS)..."
        brew install poppler
        
        # Verificar instalación exitosa
        if command_exists pdfinfo; then
            log "✅ Poppler instalado correctamente"
        else
            log "❌ Error: Poppler no se pudo instalar automáticamente"
            log "   💡 Ejecutar manualmente: brew install poppler"
            exit 1
        fi
    else
        log "❌ Error: No se pudo detectar gestor de paquetes"
        log "   💡 Instalar Poppler manualmente según tu sistema operativo:"
        log "      Ubuntu/Debian: sudo apt-get install -y poppler-utils"
        log "      CentOS/RHEL:   sudo yum install -y poppler-utils"
        log "      macOS:         brew install poppler"
        exit 1
    fi
fi

# ============================================
# 7. CREAR DIRECTORIOS NECESARIOS
# ============================================
log "📁 Verificando directorios necesarios..."

# Directorio de logs
mkdir -p logs
log "✅ Directorio logs verificado"

# Directorio de uploads
mkdir -p /tmp/rfx_uploads
chmod 755 /tmp/rfx_uploads
log "✅ Directorio de uploads verificado"

# Directorio de branding
mkdir -p backend/static/branding
log "✅ Directorio de branding verificado"

# ============================================
# 8. VERIFICAR ARCHIVO .env
# ============================================
log "🔍 Verificando configuración de entorno..."

if [ ! -f ".env" ]; then
    log "⚠️  Archivo .env no encontrado"
    
    if [ -f ".env.example" ]; then
        log "📋 Copiando .env.example a .env..."
        cp .env.example .env
        log "⚠️  IMPORTANTE: Editar .env con las credenciales correctas"
    else
        log "❌ Error: No se encontró .env ni .env.example"
        log "   💡 Crear archivo .env con las variables necesarias"
    fi
else
    log "✅ Archivo .env encontrado"
fi

# ============================================
# 9. TEST DE IMPORTACIONES CRÍTICAS
# ============================================
log "🧪 Verificando importaciones críticas..."

python -c "
import sys
sys.path.insert(0, '.')

try:
    # Core dependencies
    import flask
    import supabase
    import openai
    import playwright
    from playwright.sync_api import sync_playwright
    
    # Backend modules
    from backend.core.config import Config
    from backend.core.database import DatabaseClient
    
    print('✅ Todas las dependencias críticas importadas correctamente')
    sys.exit(0)
except ImportError as e:
    print(f'❌ Error de importación: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error inesperado: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    log "✅ Test de importaciones exitoso"
else
    log "❌ Error en test de importaciones"
    exit 1
fi

# ============================================
# 10. TEST DE PLAYWRIGHT FUNCIONAL
# ============================================
log "🧪 Verificando funcionalidad de Playwright..."

python -c "
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content('<html><body><h1>Test</h1></body></html>')
        content = page.content()
        browser.close()
        
        if 'Test' in content:
            print('✅ Playwright funciona correctamente')
            exit(0)
        else:
            print('❌ Playwright no renderiza contenido correctamente')
            exit(1)
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

# ============================================
# RESUMEN FINAL
# ============================================
echo ""
log "🎉 =========================================="
log "🎉 SETUP COMPLETADO EXITOSAMENTE"
log "🎉 =========================================="
echo ""
log "📋 Resumen:"
log "   ✅ Entorno virtual activado"
log "   ✅ Dependencias Python instaladas/actualizadas"
log "   ✅ Playwright configurado y funcional"
log "   ✅ Directorios necesarios creados"
log "   ✅ Configuración de entorno verificada"
log "   ✅ Tests de funcionalidad exitosos"
echo ""
log "🚀 El servidor está listo para iniciar!"
echo ""

# Mantener el entorno virtual activado para PM2
# PM2 usará el Python del venv automáticamente
