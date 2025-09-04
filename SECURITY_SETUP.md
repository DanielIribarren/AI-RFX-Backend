# 🔒 Configuración Segura de Variables de Entorno

## ⚠️ **IMPORTANTE: Nunca subas claves API al repositorio**

GitHub bloquea automáticamente commits que contengan claves API para proteger tu cuenta.

## 🛠️ **Configuración Correcta**

### 1. **Crear archivo `.env` local** (NO se sube al repo)

```bash
# Crear tu archivo .env personal
cp env-variables.txt .env

# Editar con tus claves reales
nano .env
```

### 2. **Contenido del archivo `.env`**

```bash
# =============================================================================
# 🗄️ DATABASE CONFIGURATION  
# =============================================================================
SUPABASE_URL="https://tu-proyecto.supabase.co"
SUPABASE_ANON_KEY="tu_clave_supabase_aqui"

# =============================================================================
# 🤖 OPENAI CONFIGURATION
# =============================================================================
OPENAI_API_KEY="tu_clave_openai_aqui"

# =============================================================================
# 🚀 APPLICATION CONFIGURATION
# =============================================================================
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=3186
SECRET_KEY=tu-clave-secreta-aqui

# =============================================================================
# 🌐 SERVER CONFIGURATION
# =============================================================================
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001

# =============================================================================
# 📁 FILE UPLOAD CONFIGURATION
# =============================================================================
MAX_FILE_SIZE=16777216
UPLOAD_FOLDER=/tmp/rfx_uploads

# =============================================================================
# 🧪 FEATURE FLAGS
# =============================================================================
ENABLE_EVALS=true
ENABLE_META_PROMPTING=false
ENABLE_VERTICAL_AGENT=false
EVAL_DEBUG_MODE=true
```

## 🔧 **Configuración PM2**

Los archivos `ecosystem.*.config.js` ya están limpios con placeholders. PM2 tomará las variables del archivo `.env`.

### **Desarrollo Local:**
```bash
pm2 start ecosystem.config.js --only ai-rfx-backend-dev
```

### **Servidor Ubuntu:**
```bash
pm2 start ecosystem.ubuntu.config.js --only ai-rfx-backend-dev
```

## 🛡️ **Protecciones Implementadas**

### ✅ **Archivos protegidos por `.gitignore`:**
- `.env` - Variables de entorno reales
- `venv/` - Virtual environment 
- `logs/` - Archivos de log
- `__pycache__/` - Cache de Python

### ✅ **Archivos seguros en el repo:**
- `ecosystem.*.config.js` - Con placeholders
- `env.*.example` - Ejemplos sin claves reales
- `.env.example` - Template para usuarios

## 🚨 **Si accidentalmente subes claves:**

1. **Regenerar las claves inmediatamente:**
   - OpenAI: https://platform.openai.com/api-keys
   - Supabase: https://app.supabase.com/project/settings/api

2. **Limpiar el historial de Git:**
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch ecosystem.config.js' \
     --prune-empty --tag-name-filter cat -- --all
   ```

## 🌐 **Configuración en Servidor de Producción**

### **Método 1: Variables de entorno del sistema**
```bash
export OPENAI_API_KEY="tu_clave_openai"
export SUPABASE_URL="https://tu-proyecto.supabase.co"
export SUPABASE_ANON_KEY="tu_clave_supabase"
```

### **Método 2: Archivo `.env` en servidor**
```bash
# En el servidor (no en el repo)
nano /home/ubuntu/nodejs/AI-RFX-Backend-Clean/.env
```

### **Método 3: PM2 con archivo de configuración externo**
```bash
# ecosystem.production.config.js (no subir al repo)
pm2 start ecosystem.production.config.js --env production
```

## 🔗 **Enlaces Útiles**

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OpenAI API Keys Best Practices](https://platform.openai.com/docs/guides/production-best-practices)
- [Supabase Security](https://supabase.com/docs/guides/auth/security)

## ⚡ **Quick Check**

Verificar que no hay claves expuestas:
```bash
grep -r "sk-" . --exclude-dir=venv --exclude-dir=node_modules
grep -r "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" . --exclude-dir=venv
```

Si estos comandos devuelven resultados, **tienes claves expuestas** que debes limpiar.

## ✅ **Estado Actual del Proyecto**

- ✅ Claves API removidas de archivos de configuración
- ✅ `.gitignore` configurado  
- ✅ Archivos PM2 con placeholders
- ✅ Documentación de seguridad creada
- ✅ Listo para hacer push seguro al repositorio
