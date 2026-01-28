#!/bin/bash

# 🚀 Script para Iniciar/Reiniciar el Backend con PM2
# Garantiza que las dependencias estén instaladas antes de iniciar

set -e

echo "🚀 =========================================="
echo "🚀 INICIANDO BACKEND CON PM2"
echo "🚀 =========================================="

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# ============================================
# 1. SETUP DE DEPENDENCIAS
# ============================================
log "📦 Ejecutando setup de dependencias..."

if [ -f "scripts/setup_dependencies.sh" ]; then
    bash scripts/setup_dependencies.sh
    
    if [ $? -ne 0 ]; then
        log "❌ Error en setup de dependencias"
        exit 1
    fi
else
    log "⚠️  Script de setup no encontrado, continuando..."
fi

# ============================================
# 2. VERIFICAR PM2
# ============================================
log "🔍 Verificando PM2..."

if ! command -v pm2 >/dev/null 2>&1; then
    log "❌ Error: PM2 no está instalado"
    log "   💡 Instalar con: npm install -g pm2"
    exit 1
fi

log "✅ PM2 encontrado: $(pm2 --version)"

# ============================================
# 3. INICIAR/REINICIAR CON PM2
# ============================================
log "🚀 Iniciando aplicación con PM2..."

# Verificar si la app ya está corriendo
if pm2 describe RFX-dev >/dev/null 2>&1; then
    log "🔄 Aplicación ya existe, reiniciando..."
    pm2 reload ecosystem.dev.config.js --env development
else
    log "🆕 Iniciando nueva instancia..."
    pm2 start ecosystem.dev.config.js --env development
fi

if [ $? -eq 0 ]; then
    log "✅ Aplicación iniciada correctamente"
else
    log "❌ Error iniciando aplicación"
    exit 1
fi

# ============================================
# 4. MOSTRAR STATUS
# ============================================
echo ""
log "📊 Status de la aplicación:"
pm2 status

echo ""
log "📋 Logs disponibles:"
log "   - Combined: ./logs/ai-rfx-dev-combined.log"
log "   - Output:   ./logs/ai-rfx-dev-out.log"
log "   - Errors:   ./logs/ai-rfx-dev-error.log"

echo ""
log "💡 Comandos útiles:"
log "   pm2 logs RFX-dev          - Ver logs en tiempo real"
log "   pm2 restart RFX-dev       - Reiniciar aplicación"
log "   pm2 stop RFX-dev          - Detener aplicación"
log "   pm2 monit                 - Monitor en tiempo real"

echo ""
log "🎉 =========================================="
log "🎉 BACKEND INICIADO EXITOSAMENTE"
log "🎉 =========================================="
