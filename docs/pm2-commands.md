# 🚀 Guía de Comandos PM2 para AI-RFX Backend

## 📋 Comandos Básicos

### Iniciar la aplicación

```bash
# Desarrollo
pm2 start ecosystem.config.js --only ai-rfx-backend-dev

# Producción (con Gunicorn)
pm2 start ecosystem.config.js --only ai-rfx-backend-prod --env production

# Staging
pm2 start ecosystem.config.js --only ai-rfx-backend-staging --env staging

# Iniciar todas las configuraciones
pm2 start ecosystem.config.js
```

### Gestión de procesos

```bash
# Ver estado de todos los procesos
pm2 status

# Ver logs en tiempo real
pm2 logs ai-rfx-backend-dev

# Ver logs de todos los procesos
pm2 logs

# Reiniciar aplicación
pm2 restart ai-rfx-backend-dev

# Reiniciar con zero-downtime (producción)
pm2 reload ai-rfx-backend-prod

# Detener aplicación
pm2 stop ai-rfx-backend-dev

# Eliminar proceso de PM2
pm2 delete ai-rfx-backend-dev
```

### Monitoreo

```bash
# Monitor en tiempo real
pm2 monit

# Información detallada del proceso
pm2 show ai-rfx-backend-dev

# Métricas avanzadas
pm2 web
```

## 🔧 Configuración Inicial

### 1. Instalar PM2 (si no está instalado)

```bash
npm install -g pm2
```

### 2. Configurar variables de entorno

Asegúrate de que tu archivo `.env` contenga:

```bash
# Base de datos
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Aplicación
SECRET_KEY=your_secret_key
ENVIRONMENT=development  # development, staging, production
PORT=5001
HOST=0.0.0.0
```

### 3. Verificar virtual environment

```bash
# Activar virtual environment
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Verificar que Gunicorn está instalado (para producción)
pip install gunicorn
```

## 🏭 Comandos para Producción

### Deploy con PM2

```bash
# Setup inicial en servidor
pm2 deploy ecosystem.config.js production setup

# Deploy
pm2 deploy ecosystem.config.js production

# Revert al deploy anterior
pm2 deploy ecosystem.config.js production revert 1
```

### Auto-startup

```bash
# Guardar configuración actual
pm2 save

# Generar script de auto-startup
pm2 startup

# Aplicar configuración de startup
sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u $USER --hp $HOME
```

## 📊 Scripts de Gestión

### Health Check Script

```bash
# Verificar que la aplicación responde
curl http://localhost:5001/health

# Health check detallado
curl http://localhost:5001/health/detailed
```

### Rotación de Logs

```bash
# Instalar módulo de rotación de logs
pm2 install pm2-logrotate

# Configurar rotación (opcional)
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:compress true
pm2 set pm2-logrotate:rotateInterval '0 0 * * *'  # Diario a medianoche
```

## 🛠️ Troubleshooting

### Problemas Comunes

```bash
# Limpiar logs
pm2 flush

# Restart PM2 daemon
pm2 kill
pm2 resurrect

# Verificar configuración
pm2 prettylist

# Logs con más contexto
pm2 logs --lines 100
```

### Debug Mode

```bash
# Ejecutar con más verbosidad
pm2 start ecosystem.config.js --only ai-rfx-backend-dev --log-type

# Ver variables de entorno
pm2 show ai-rfx-backend-dev
```

## 📈 Optimizaciones

### Para Desarrollo

- Usa `ai-rfx-backend-dev` con watch mode activado
- Logs detallados habilitados
- Single instance
- **Feature Flags**: ENABLE_EVALS=true, EVAL_DEBUG_MODE=true
- **Debug**: Logs detallados de evaluaciones AI-RFX

### Para Producción

- Usa `ai-rfx-backend-prod` con Gunicorn
- Multiple workers según CPU cores
- Health checks configurados
- Auto-restart en caso de memoria alta
- **Feature Flags**: EVAL_DEBUG_MODE=false (para performance)
- **Security**: Cambiar SECRET_KEY de producción

### Para Staging

- Usa `ai-rfx-backend-staging`
- Watch mode para testing
- Configuración intermedia entre dev y prod
- **Feature Flags**: ENABLE_META_PROMPTING=true (para testing)
- **Testing**: Ideal para probar nuevas features de AI antes de producción

## 🔗 Enlaces Útiles

- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Flask Deployment](https://flask.palletsprojects.com/en/2.0.x/deploying/)

## ⚡ Quick Start

```bash
# Start development server
pm2 start ecosystem.config.js --only ai-rfx-backend-dev

# Monitor
pm2 monit

# View logs
pm2 logs ai-rfx-backend-dev

# Stop when done
pm2 stop ai-rfx-backend-dev
```

## 🤖 AI-RFX Endpoints Específicos

### Endpoints Principales del Proyecto

```bash
# RFX Processing - Procesar documentos RFX
curl -X POST http://localhost:5001/api/rfx/process \
  -H "Content-Type: multipart/form-data" \
  -F "file=@documento.pdf"

# Propuesta Generation - Generar propuestas
curl -X POST http://localhost:5001/api/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"rfx_id": "12345"}'

# Pricing Configuration - Configuración de precios
curl http://localhost:5001/api/pricing/config/12345

# Pricing Calculation - Cálculo de precios
curl -X POST http://localhost:5001/api/pricing/calculate/12345

# Download PDF - Descargar propuesta generada
curl http://localhost:5001/api/download/12345
```

### Testing con Feature Flags

```bash
# Test evaluaciones (ENABLE_EVALS=true)
curl http://localhost:5001/health/detailed | jq '.checks.evals'

# Ver logs de evaluaciones en desarrollo
pm2 logs ai-rfx-backend-dev | grep "EVAL"

# Monitoring específico para AI-RFX
pm2 logs ai-rfx-backend-dev | grep -E "(RFX|Pricing|Proposal|OpenAI)"
```

### Variables de Entorno Específicas del Proyecto

```bash
# Ver configuración actual
pm2 show ai-rfx-backend-dev | grep -A 20 "env:"

# Verificar feature flags
pm2 show ai-rfx-backend-dev | grep -E "(ENABLE_|EVAL_)"

# Verificar configuración de Supabase y OpenAI
pm2 show ai-rfx-backend-dev | grep -E "(SUPABASE|OPENAI)"
```
