# 🚀 Deploy Automático PM2 - Configuración Completa

## 🎯 Problema Solucionado

**ANTES:** Cada vez que actualizabas el servidor tenías que ejecutar manualmente:
```bash
cd /ruta/del/proyecto
./scripts/install_playwright_server.sh
pm2 restart all
```

**AHORA:** Todo se ejecuta automáticamente con PM2 hooks! 🎉

## 🔧 Configuración Implementada

### 1. **Hooks Automáticos en PM2**
El archivo `ecosystem.dev.config.js` ahora incluye:

```javascript
// 🎭 HOOKS AUTOMÁTICOS - Setup automático de Playwright
post_update: './scripts/post_deploy_setup.sh',
pre_start: './scripts/post_deploy_setup.sh',
```

**Qué hace cada hook:**
- `pre_start`: Se ejecuta ANTES de iniciar la aplicación
- `post_update`: Se ejecuta DESPUÉS de actualizar el código

### 2. **Scripts Creados**

#### 📁 `scripts/post_deploy_setup.sh`
- ✅ Verifica e instala Playwright automáticamente
- ✅ Configura navegadores (Chromium)
- ✅ Crea directorios necesarios
- ✅ Verifica permisos
- ✅ Ejecuta tests de funcionalidad
- ✅ Instala dependencias del sistema si es necesario

#### 📁 `scripts/auto_deploy.sh`
- ✅ Actualiza código desde Git
- ✅ Instala dependencias Python
- ✅ Ejecuta setup automático
- ✅ Reinicia PM2
- ✅ Verifica estado del servidor

## 🚀 Cómo Usar el Sistema Automatizado

### **Opción 1: Deploy Completo (Recomendado)**
```bash
# En el servidor, ejecutar UNA SOLA VEZ:
./scripts/auto_deploy.sh
```

### **Opción 2: Solo Reiniciar PM2 (automático)**
```bash
# PM2 ejecutará automáticamente el setup:
pm2 restart RFX-dev
# O
pm2 reload ecosystem.dev.config.js --env development
```

### **Opción 3: Deploy con PM2 (avanzado)**
```bash
# Desde tu máquina local (configurar primero):
pm2 deploy ecosystem.dev.config.js development
```

## 📋 Configuración Inicial (Solo Una Vez)

### 1. **En el Servidor:**
```bash
# Asegurar que los scripts tengan permisos
chmod +x scripts/*.sh

# Primera ejecución manual (solo una vez)
./scripts/post_deploy_setup.sh
```

### 2. **Configurar Deploy Remoto (Opcional):**
Editar `ecosystem.dev.config.js` y cambiar:
```javascript
deploy: {
  development: {
    user: 'ubuntu',
    host: ['TU-IP-SERVIDOR'], // ← Cambiar aquí
    repo: 'git@github.com:TU-REPO.git', // ← Cambiar aquí
    // ...
  }
}
```

## 🎉 Beneficios del Sistema Automatizado

### ✅ **Cero Intervención Manual**
- No más comandos manuales después de updates
- Setup de Playwright completamente automático
- Verificación automática de dependencias

### ✅ **Detección Inteligente**
- Solo instala Playwright si no está disponible
- Detecta sistema operativo automáticamente
- Instala dependencias del sistema según la distribución

### ✅ **Logs Detallados**
- Timestamp en cada operación
- Logs de éxito/error claros
- Verificación de funcionalidad automática

### ✅ **Rollback Seguro**
- Backup automático de configuración
- Tests de funcionalidad antes de completar
- Reinicio automático solo si todo funciona

## 🔍 Monitoreo y Debugging

### **Ver Logs de Deploy:**
```bash
# Logs del setup automático
tail -f logs/ai-rfx-dev-combined.log

# Logs específicos de PM2
pm2 logs RFX-dev

# Estado del servidor
pm2 status
pm2 monit
```

### **Verificar Playwright:**
```bash
# Test manual de Playwright
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(); browser.close(); p.stop(); print('✅ OK')"
```

### **Test de PDFs:**
```bash
# Probar endpoint de descarga
curl -X POST http://localhost:3186/api/download/html-to-pdf \
  -H "Content-Type: application/json" \
  -d '{"html": "<h1>Test</h1>", "client_name": "Test"}'
```

## 🚨 Troubleshooting

### **Si el setup falla:**
```bash
# Ejecutar manualmente para ver errores
./scripts/post_deploy_setup.sh

# Ver logs detallados
pm2 logs RFX-dev --lines 50
```

### **Si Playwright no funciona:**
```bash
# Reinstalar forzado
playwright install --force chromium

# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0
```

### **Restaurar configuración anterior:**
```bash
# Si algo sale mal, restaurar backup
cp ecosystem.dev.config.js.backup ecosystem.dev.config.js
pm2 reload ecosystem.dev.config.js --env development
```

## 🎯 Resultado Final

**Ahora cada vez que actualices el servidor:**

1. **Haces push a tu repositorio** → Git actualizado ✅
2. **Ejecutas `./scripts/auto_deploy.sh`** → Todo automático ✅
3. **El servidor funciona inmediatamente** → PDFs generan correctamente ✅

**¡No más comandos manuales de Playwright! 🎉**

---

## 📞 Soporte

Si tienes problemas:
1. Revisar logs: `pm2 logs RFX-dev`
2. Ejecutar test manual: `./scripts/post_deploy_setup.sh`
3. Verificar permisos: `ls -la scripts/`
4. Contactar soporte con logs específicos
