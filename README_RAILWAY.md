# 🚂 AI-RFX Backend - Railway Ready!

Tu backend está **100% listo** para deploy en Railway con auto-deploy desde GitHub.

## 🎯 Resumen de Archivos Creados

### ✅ Archivos de Deployment

- **`Dockerfile`** - Imagen optimizada para Railway con todas las dependencias
- **`railway.json`** - Configuración específica de Railway (health checks, restart policy)
- **`.dockerignore`** - Optimiza el build excluyendo archivos innecesarios
- **`env.railway.example`** - Template con todas las variables de entorno necesarias

### 📚 Documentación

- **`RAILWAY_DEPLOYMENT_GUIDE.md`** - Guía completa paso a paso
- **`DEPLOYMENT_GUIDE.md`** - Guía alternativa para self-hosted (si la necesitas después)

## 🚀 Próximos Pasos (5 minutos)

### 1. Crear Proyecto en Railway

1. Ve a [railway.app](https://railway.app) y regístrate con GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Selecciona este repositorio
4. Railway detectará automáticamente el `Dockerfile`

### 2. Configurar Variables de Entorno

En Railway Dashboard → Variables, añade:

```bash
# OBLIGATORIAS
ENVIRONMENT=production
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
OPENAI_API_KEY=sk-proj-tu-api-key
SECRET_KEY=genera-una-clave-super-segura

# RECOMENDADAS
CORS_ORIGINS=https://tu-frontend.vercel.app
OPENAI_MODEL=gpt-4o
```

### 3. ¡Deploy Automático!

- Railway desplegará automáticamente
- Tu app estará en `https://tu-app.railway.app`
- **Cada push a `main` se desplegará automáticamente** 🎉

## 🔄 Auto-Deploy Configurado

✅ **Trigger**: Cada `git push origin main`  
✅ **Build**: Dockerfile automáticamente detectado  
✅ **Deploy**: Zero-downtime deployment  
✅ **Rollback**: Automático si falla  
✅ **Health Check**: Endpoint `/health` configurado

## 🛠️ Comandos Útiles

```bash
# Hacer cambios y desplegar
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main  # ← Esto dispara el auto-deploy

# Ver logs en tiempo real
# Ve a Railway Dashboard → Logs

# Verificar deployment
curl https://tu-app.railway.app/health
```

## 💡 Características Incluidas

- **Dependencias completas**: WeasyPrint, Tesseract, Playwright, pdf2image
- **Gunicorn optimizado**: 2 workers, 8 threads, timeout 180s
- **Health checks**: Configurados para Railway
- **Logs estructurados**: Acceso y error logs habilitados
- **Auto-restart**: En caso de fallos
- **HTTPS gratuito**: Certificado SSL automático

## 🎯 Todo Listo!

Tu backend está **production-ready** para Railway. Solo necesitas:

1. ⏱️ **2 min**: Crear cuenta y proyecto en Railway
2. ⏱️ **2 min**: Configurar variables de entorno
3. ⏱️ **1 min**: Verificar que funciona

**Total: 5 minutos** y tendrás auto-deploy funcionando! 🚀

---

**¿Necesitas ayuda?** Revisa `RAILWAY_DEPLOYMENT_GUIDE.md` para instrucciones detalladas.
