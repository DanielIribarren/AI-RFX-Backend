# 🚂 AI-RFX Backend - Railway Deployment Guide

Guía completa para hacer deploy del backend en Railway con auto-deploy desde GitHub.

## 🌟 Ventajas de Railway

- ✅ **Auto-deploy**: Cada push a `main` despliega automáticamente
- ✅ **Zero-config**: Detecta automáticamente el Dockerfile
- ✅ **Escalado automático**: Se ajusta según el tráfico
- ✅ **HTTPS gratuito**: Dominio personalizado con SSL
- ✅ **Logs en tiempo real**: Monitoreo integrado
- ✅ **Variables de entorno**: Interfaz web fácil de usar

## 🚀 Setup Paso a Paso

### 1. Preparar el Repositorio

Los archivos ya están listos:

- ✅ `Dockerfile` optimizado para Railway
- ✅ `railway.json` con configuración específica
- ✅ `.dockerignore` para builds eficientes
- ✅ `env.railway.example` con todas las variables necesarias

### 2. Crear Cuenta en Railway

1. Ve a [railway.app](https://railway.app)
2. Regístrate con tu cuenta de GitHub
3. Autoriza Railway para acceder a tus repositorios

### 3. Crear Nuevo Proyecto

1. **Dashboard** → **New Project** → **Deploy from GitHub repo**
2. Selecciona tu repositorio `AI-RFX-Backend-Clean`
3. Railway detectará automáticamente el `Dockerfile`
4. Haz click en **Deploy**

### 4. Configurar Variables de Entorno

1. Ve a tu proyecto → **Variables**
2. Añade todas las variables del archivo `env.railway.example`:

```bash
# Variables obligatorias
ENVIRONMENT=production
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-proj-...
SECRET_KEY=genera-una-clave-super-segura-aqui

# Variables opcionales pero recomendadas
CORS_ORIGINS=https://tu-frontend.vercel.app,https://tu-dominio.com
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4096
```

### 5. Configurar Auto-Deploy

1. Ve a **Settings** → **Service**
2. En **Source Repo**, verifica que esté conectado a tu repo
3. En **Production Branch**, asegúrate que sea `main`
4. **Auto-Deploy** debe estar habilitado (por defecto)

### 6. Configurar Dominio (Opcional)

1. Ve a **Settings** → **Networking**
2. En **Custom Domain**, añade tu dominio
3. Configura los DNS records según las instrucciones
4. Railway generará automáticamente el certificado SSL

## 🔧 Configuración Avanzada

### Health Check

Railway usará automáticamente el endpoint `/health` definido en `railway.json`:

```bash
# Verificar que funciona
curl https://tu-app.railway.app/health
```

### Logs y Monitoreo

1. **Deploy Logs**: Ve a la pestaña **Deployments**
2. **Runtime Logs**: Ve a la pestaña **Logs**
3. **Métricas**: Ve a la pestaña **Metrics**

### Configuración de Build

El archivo `railway.json` ya está configurado:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 180 --access-logfile - --error-logfile -",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

## 🔄 Workflow de Desarrollo

### Auto-Deploy Activado

1. **Desarrolla localmente**:

```bash
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main
```

2. **Railway detecta el push** y automáticamente:

   - Construye la nueva imagen Docker
   - Ejecuta tests (si están configurados)
   - Despliega la nueva versión
   - Hace rollback automático si falla

3. **Verifica el deployment**:
   - Ve a Railway Dashboard → tu proyecto
   - Revisa los logs en tiempo real
   - Prueba el endpoint: `https://tu-app.railway.app/health`

### Rollback Manual

Si necesitas hacer rollback:

1. Ve a **Deployments**
2. Encuentra la versión anterior que funcionaba
3. Haz click en **Redeploy**

## 🛠️ Troubleshooting

### Build Fails

**Error común**: "Failed to build Docker image" o "Package 'wkhtmltopdf' has no installation candidate"

**Solución**:

1. **Opción 1 (Recomendada)**: Usa `Dockerfile.minimal` si no necesitas PDF/OCR:

   ```bash
   # Renombra el archivo
   mv Dockerfile.minimal Dockerfile
   ```

2. **Opción 2**: El `Dockerfile` principal ya está arreglado para instalar wkhtmltopdf correctamente

3. Revisa los logs de build en Railway para errores específicos
4. Verifica que `requirements.txt` esté en la raíz

### App Crashes on Start

**Error común**: "Application failed to start"

**Solución**:

1. Revisa **Runtime Logs**
2. Verifica que todas las variables de entorno estén configuradas
3. Prueba el comando localmente:

```bash
gunicorn backend.wsgi:application --bind 0.0.0.0:8080
```

### Health Check Fails

**Error común**: "Health check timeout"

**Solución**:

1. Verifica que `/health` responda localmente
2. Aumenta `healthcheckTimeout` en `railway.json`
3. Revisa logs para errores de conexión a DB/OpenAI

### Variables de Entorno

**Error común**: "Required environment variable not set"

**Solución**:

1. Ve a **Variables** en Railway Dashboard
2. Compara con `env.railway.example`
3. Asegúrate que no hay espacios extra en los valores

## 📊 Monitoreo y Optimización

### Métricas Importantes

1. **CPU Usage**: Debería estar < 80%
2. **Memory Usage**: Debería estar < 90%
3. **Response Time**: Debería estar < 2s
4. **Error Rate**: Debería estar < 1%

### Optimización de Performance

1. **Ajustar Workers**:

```dockerfile
# En Dockerfile, ajusta según tu tráfico
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --threads 4
```

2. **Configurar Caching**:

```bash
# Añadir a variables de entorno
REDIS_URL=redis://...  # Si usas Redis
```

3. **Optimizar Imagen Docker**:

```dockerfile
# Para imagen más ligera, usa requirements-minimal.txt
COPY requirements-minimal.txt requirements.txt
```

## 💰 Costos y Límites

### Plan Gratuito (Hobby)

- ✅ $5 USD de crédito mensual
- ✅ Auto-sleep después de inactividad
- ✅ 1GB RAM, 1 vCPU
- ✅ 1GB storage

### Plan Pro ($20/mes)

- ✅ Sin auto-sleep
- ✅ Más recursos
- ✅ Métricas avanzadas
- ✅ Priority support

## 🔒 Seguridad

### Variables Sensibles

1. **Nunca** subas archivos `.env` con valores reales
2. Usa Railway Variables para secretos
3. Rota las API keys regularmente

### CORS Configuration

```bash
# Configura CORS_ORIGINS específicamente
CORS_ORIGINS=https://tu-frontend.vercel.app,https://tu-dominio.com
```

### HTTPS

Railway proporciona HTTPS automáticamente para todos los dominios.

## 🎯 Próximos Pasos

1. **Configurar CI/CD avanzado** con tests automáticos
2. **Implementar staging environment** con branch `develop`
3. **Configurar alertas** para errores críticos
4. **Optimizar costos** con auto-scaling inteligente

## 📞 Soporte

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [railway.app/discord](https://railway.app/discord)
- **GitHub Issues**: Para problemas específicos del código

---

## ✅ Checklist de Deployment

- [ ] Cuenta de Railway creada y conectada a GitHub
- [ ] Proyecto creado desde el repositorio
- [ ] Variables de entorno configuradas
- [ ] Primer deployment exitoso
- [ ] Health check funcionando
- [ ] Dominio personalizado configurado (opcional)
- [ ] Auto-deploy verificado con un push de prueba

¡Listo! Tu backend estará disponible en `https://tu-app.railway.app` y se actualizará automáticamente con cada push a `main`. 🚀
