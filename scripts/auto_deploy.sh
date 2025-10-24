#!/bin/bash

# 🚀 Script de Deploy Automático con Setup de Playwright
# Ejecuta todos los pasos necesarios para actualizar el servidor

set -e

echo "🚀 =========================================="
echo "🚀 DEPLOY AUTOMÁTICO INICIANDO..."
echo "🚀 =========================================="

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Actualizar código del repositorio (si estás usando git)
if [ -d ".git" ]; then
    log "📥 Actualizando código desde repositorio..."
    git pull origin main || git pull origin master
    log "✅ Código actualizado"
fi

# 2. Instalar/actualizar dependencias Python
log "📦 Actualizando dependencias Python..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install -r requirements.txt --upgrade
log "✅ Dependencias actualizadas"

# 3. Ejecutar setup automático (Playwright, directorios, etc.)
log "🎭 Ejecutando setup automático..."
./scripts/post_deploy_setup.sh
log "✅ Setup completado"

# 4. Reiniciar PM2 con nueva configuración
log "🔄 Reiniciando PM2..."
pm2 reload ecosystem.dev.config.js --env development

# 5. Verificar estado
log "🔍 Verificando estado del servidor..."
sleep 5
pm2 status

# 6. Test de salud
log "🧪 Ejecutando test de salud..."
if curl -f http://localhost:3186/health > /dev/null 2>&1; then
    log "✅ Servidor funcionando correctamente"
else
    log "⚠️  Servidor no responde en /health, verificar logs"
    pm2 logs RFX-dev --lines 10
fi

echo ""
log "🎉 =========================================="
log "🎉 DEPLOY AUTOMÁTICO COMPLETADO"
log "🎉 =========================================="
echo ""
log "📋 Para monitorear:"
log "   pm2 status"
log "   pm2 logs RFX-dev"
log "   pm2 monit"
echo ""
