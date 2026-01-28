# 🚀 Guía de Deployment - AI-RFX Backend

## Problema Resuelto

**Antes:** PM2 no gestionaba automáticamente las dependencias de Python, causando errores al reiniciar el servidor.

**Ahora:** Sistema automático que garantiza que todas las dependencias estén instaladas y actualizadas antes de cada inicio.

---

## 📋 Arquitectura de la Solución

```
┌─────────────────────────────────────────────────────────┐
│  PM2 Start/Restart                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  scripts/setup_dependencies.sh                          │
│  ✅ Verifica Python/pip                                 │
│  ✅ Crea/activa entorno virtual                         │
│  ✅ Instala/actualiza dependencias                      │
│  ✅ Configura Playwright                                │
│  ✅ Verifica dependencias del sistema                   │
│  ✅ Ejecuta tests de funcionalidad                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Backend Inicia con Dependencias Garantizadas           │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Scripts Disponibles

### 1. `scripts/setup_dependencies.sh` ⭐ NUEVO
**Propósito:** Setup automático completo de dependencias

**Qué hace:**
- ✅ Verifica Python 3 y pip
- ✅ Crea/activa entorno virtual
- ✅ Actualiza pip y setuptools
- ✅ Instala/actualiza todas las dependencias de `requirements.txt`
- ✅ Instala navegadores de Playwright (Chromium)
- ✅ Verifica dependencias del sistema (Poppler)
- ✅ Crea directorios necesarios (logs, uploads, branding)
- ✅ Ejecuta tests de importaciones críticas
- ✅ Verifica funcionalidad de Playwright

**Cuándo se ejecuta:**
- Automáticamente en cada `pm2 start` o `pm2 reload`
- Manualmente: `bash scripts/setup_dependencies.sh`

---

### 2. `scripts/pm2_start.sh` ⭐ NUEVO
**Propósito:** Wrapper para iniciar PM2 con setup automático

**Uso:**
```bash
# Iniciar/reiniciar el backend
bash scripts/pm2_start.sh
```

**Qué hace:**
1. Ejecuta `setup_dependencies.sh`
2. Verifica que PM2 esté instalado
3. Inicia o reinicia la aplicación con PM2
4. Muestra status y comandos útiles

---

### 3. `scripts/post_deploy_setup.sh` (Existente)
**Propósito:** Setup específico para Playwright (legacy)

**Nota:** Ahora reemplazado por `setup_dependencies.sh` que es más completo.

---

## 🚀 Cómo Usar en Servidor

### Primera Vez (Setup Inicial)

```bash
# 1. Clonar repositorio
cd /home/ubuntu/nodejs
git clone <repo-url> AI-RFX-Backend-Clean
cd AI-RFX-Backend-Clean

# 2. Dar permisos a los scripts
chmod +x scripts/*.sh

# 3. Instalar PM2 (si no está instalado)
npm install -g pm2

# 4. Iniciar con setup automático
bash scripts/pm2_start.sh
```

---

### Reiniciar el Servidor

```bash
# Opción 1: Usando el script (RECOMENDADO)
bash scripts/pm2_start.sh

# Opción 2: Directamente con PM2
pm2 reload ecosystem.dev.config.js --env development
# Nota: Esto también ejecuta setup_dependencies.sh automáticamente
```

---

### Deploy Automático con Git

```bash
# El ecosystem.dev.config.js ya está configurado
pm2 deploy ecosystem.dev.config.js development setup    # Primera vez
pm2 deploy ecosystem.dev.config.js development update   # Actualizaciones

# Esto ejecuta automáticamente:
# 1. git pull
# 2. setup_dependencies.sh
# 3. pm2 reload
```

---

## 📊 Verificar Estado

```bash
# Ver status de la aplicación
pm2 status

# Ver logs en tiempo real
pm2 logs RFX-dev

# Ver logs específicos
tail -f logs/ai-rfx-dev-out.log      # Output normal
tail -f logs/ai-rfx-dev-error.log    # Errores
tail -f logs/ai-rfx-dev-combined.log # Todo junto

# Monitor en tiempo real
pm2 monit
```

---

## 🔧 Comandos PM2 Útiles

```bash
# Reiniciar aplicación
pm2 restart RFX-dev

# Detener aplicación
pm2 stop RFX-dev

# Eliminar aplicación de PM2
pm2 delete RFX-dev

# Ver información detallada
pm2 describe RFX-dev

# Guardar configuración de PM2
pm2 save

# Configurar PM2 para auto-inicio en boot
pm2 startup
```

---

## 🐛 Troubleshooting

### Error: "Module not found"

**Causa:** Dependencias no instaladas o entorno virtual no activado

**Solución:**
```bash
# Ejecutar setup manualmente
bash scripts/setup_dependencies.sh

# Verificar que el venv existe
ls -la venv/

# Reinstalar dependencias
source venv/bin/activate
pip install -r requirements.txt
```

---

### Error: "Playwright browser not found"

**Causa:** Navegadores de Playwright no instalados

**Solución:**
```bash
# Activar venv y reinstalar
source venv/bin/activate
playwright install chromium --with-deps
```

---

### Error: "Poppler not found"

**Causa:** Dependencia del sistema faltante

**Solución:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y poppler-utils

# CentOS/RHEL
sudo yum install -y poppler-utils

# macOS
brew install poppler
```

---

### Error: "Permission denied"

**Causa:** Scripts sin permisos de ejecución

**Solución:**
```bash
chmod +x scripts/*.sh
```

---

### Backend no inicia después de reiniciar servidor

**Causa:** PM2 no configurado para auto-inicio

**Solución:**
```bash
# Configurar PM2 startup
pm2 startup

# Ejecutar el comando que PM2 te muestra (con sudo)
# Ejemplo: sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu

# Guardar configuración actual
pm2 save
```

---

## 📦 Dependencias del Sistema Requeridas

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    git
```

### CentOS/RHEL
```bash
sudo yum install -y \
    python3 \
    python3-pip \
    poppler-utils \
    git
```

### macOS
```bash
brew install python3 poppler
```

---

## 🔐 Variables de Entorno

El archivo `.env` debe contener:

```bash
# Base de datos
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# OpenAI
OPENAI_API_KEY=sk-your-api-key

# Aplicación
SECRET_KEY=your-secret-key
DEBUG=true
ENVIRONMENT=development

# Servidor
PORT=3186
HOST=0.0.0.0

# CORS
CORS_ORIGINS=http://localhost:3000,http://your-domain.com

# File Upload
MAX_FILE_SIZE=16777216
UPLOAD_FOLDER=/tmp/rfx_uploads
```

**Nota:** El archivo `.env` NO debe estar en git. Usa `.env.example` como template.

---

## 📝 Logs y Debugging

### Ubicación de Logs

```
logs/
├── ai-rfx-dev-combined.log  # Todo junto
├── ai-rfx-dev-out.log       # Output normal
└── ai-rfx-dev-error.log     # Solo errores
```

### Ver Logs en Tiempo Real

```bash
# Todos los logs
pm2 logs RFX-dev

# Solo errores
pm2 logs RFX-dev --err

# Solo output
pm2 logs RFX-dev --out

# Últimas 100 líneas
pm2 logs RFX-dev --lines 100
```

---

## ✅ Checklist de Deployment

- [ ] Python 3.8+ instalado
- [ ] pip y venv instalados
- [ ] PM2 instalado globalmente
- [ ] Dependencias del sistema instaladas (Poppler)
- [ ] Archivo `.env` configurado
- [ ] Scripts con permisos de ejecución (`chmod +x scripts/*.sh`)
- [ ] Entorno virtual creado (`venv/`)
- [ ] Dependencias Python instaladas
- [ ] Playwright browsers instalados
- [ ] PM2 configurado para auto-inicio (`pm2 startup`)
- [ ] Configuración guardada (`pm2 save`)

---

## 🎯 Ventajas de Esta Solución

✅ **Automático:** Setup se ejecuta en cada inicio/reinicio  
✅ **Consistente:** Mismo proceso en desarrollo y producción  
✅ **Robusto:** Verifica cada paso con tests funcionales  
✅ **Debuggeable:** Logs detallados de cada operación  
✅ **Idempotente:** Puede ejecutarse múltiples veces sin problemas  
✅ **Completo:** Maneja Python, dependencias del sistema y Playwright  
✅ **Rápido:** Solo instala/actualiza lo necesario  

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs: `pm2 logs RFX-dev`
2. Ejecuta setup manualmente: `bash scripts/setup_dependencies.sh`
3. Verifica dependencias del sistema: `bash scripts/check_system_dependencies.py`
4. Revisa esta guía de troubleshooting

---

**Última actualización:** Enero 2026  
**Versión:** 2.0 - Setup Automático Completo
