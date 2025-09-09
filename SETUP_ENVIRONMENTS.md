# 🚀 AI-RFX Backend - Configuración de Entornos

## 📋 Arquitectura Coherente Final

**Sistema unificado** con configuraciones separadas y puertos específicos:

- **🏠 Local Development**: Puerto 5001 (tu máquina)
- **🖥️ Ubuntu Development**: Puerto 3186 (servidor Ubuntu)
- **🏭 Ubuntu Production**: Puerto 3187 (servidor Ubuntu)

**Problema resuelto**: El error `ModuleNotFoundError: No module named 'flask'` se soluciona con el script de setup que instala todas las dependencias en el virtual environment correcto.

## 🔧 Configuraciones Disponibles

### 1. **Desarrollo Local** (Puerto 5001)

```bash
# Ejecutar en tu máquina local
python3 start_backend.py
```

- **Puerto**: 5001
- **Configuración**: Automática con variables de entorno locales
- **Debug**: Activado
- **CORS**: Configurado para localhost

### 2. **Ubuntu Development** (Puerto 3186)

```bash
# Ejecutar en servidor Ubuntu
pm2 start ecosystem.dev.config.js

# O usar el script interactivo
./start-pm2.sh dev
```

- **Puerto**: 3186
- **Configuración**: Variables en `ecosystem.dev.config.js` con credenciales reales
- **Script**: `run_backend_simple.py` con Flask development server
- **Logs**: `./logs/ai-rfx-dev-*-log`
- **Features**: EVALS activado, DEBUG mode activado

### 3. **Ubuntu Production** (Puerto 3187)

```bash
# Ejecutar en servidor Ubuntu
pm2 start ecosystem.prod.config.js

# O usar el script interactivo
./start-pm2.sh prod
```

- **Puerto**: 3187
- **Configuración**: Gunicorn con 2 workers, optimizado para producción
- **Script**: Gunicorn WSGI server para mejor rendimiento
- **Logs**: `./logs/ai-rfx-prod-*-log`
- **Features**: EVALS activado, DEBUG mode desactivado

## 🛠️ Solución al Error de PM2

### En el servidor Ubuntu, ejecuta:

```bash
# 1. Ve al directorio del proyecto
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# 2. Hacer ejecutable los scripts
chmod +x setup_ubuntu_server.sh
chmod +x start-pm2.sh

# 3. Ejecutar el script de setup (OBLIGATORIO primera vez)
./setup_ubuntu_server.sh

# 4. Una vez completado, iniciar con PM2:
# Opción A: Directo
pm2 start ecosystem.dev.config.js

# Opción B: Script interactivo (RECOMENDADO)
./start-pm2.sh

# 5. Verificar estado
pm2 status
pm2 logs ai-rfx-backend-dev
```

### Script de setup incluye:

- ✅ Creación del virtual environment
- ✅ Instalación de todas las dependencias de `requirements.txt`
- ✅ Verificación de importaciones de Flask y de la aplicación
- ✅ Configuración de permisos
- ✅ Creación de directorios necesarios

## 📊 Verificación Post-Setup

```bash
# Verificar que Flask está instalado
./venv/bin/python -c "import flask; print('✅ Flask OK')"

# Verificar que la app importa correctamente
./venv/bin/python -c "from backend.app import app; print('✅ App OK')"

# Iniciar con PM2
pm2 start ecosystem.dev.config.js

# Probar health check
curl http://localhost:3186/health
```

## 🌍 Resumen de Puertos

| Entorno         | Puerto | Comando                              | Ubicación       |
| --------------- | ------ | ------------------------------------ | --------------- |
| **Local Dev**   | 5001   | `python3 start_backend.py`           | Tu máquina      |
| **Ubuntu Dev**  | 3186   | `pm2 start ecosystem.dev.config.js`  | Servidor Ubuntu |
| **Ubuntu Prod** | 3187   | `pm2 start ecosystem.prod.config.js` | Servidor Ubuntu |

## 🔍 Troubleshooting

### Si aún hay errores después del setup:

1. **Verificar virtual environment**:

```bash
which python3
./venv/bin/python --version
```

2. **Reinstalar dependencias**:

```bash
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt --force-reinstall
```

3. **Verificar permisos**:

```bash
ls -la venv/bin/python
ls -la venv/bin/gunicorn
```

4. **Ver logs detallados**:

```bash
pm2 logs ai-rfx-backend-dev --lines 50
```

## 📝 Variables de Entorno

## 📁 Archivos de Configuración Coherentes

### **Archivos principales:**

- **`ecosystem.dev.config.js`** - Ubuntu Development (puerto 3186)
- **`ecosystem.prod.config.js`** - Ubuntu Production (puerto 3187)
- **`start_backend.py`** - Local Development (puerto 5001)
- **`setup_ubuntu_server.sh`** - Script de instalación Ubuntu
- **`start-pm2.sh`** - Gestor interactivo PM2

### **Archivos eliminados** (para evitar confusión):

- ~~`ecosystem.config.js`~~ - Reemplazado por configuraciones separadas
- ~~`ecosystem.simple.config.js`~~ - Redundante

### **Variables incluidas en cada configuración:**

- **Database**: SUPABASE_URL, SUPABASE_ANON_KEY (credenciales reales)
- **AI**: OPENAI_API_KEY (credenciales reales)
- **Server**: PORT, HOST, CORS_ORIGINS
- **Features**: ENABLE_EVALS, EVAL_DEBUG_MODE

**No necesitas crear archivos `.env` adicionales en el servidor Ubuntu** - todo está en las configuraciones PM2.
