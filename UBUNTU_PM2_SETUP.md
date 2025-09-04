# 🚀 Configuración PM2 para Servidor Ubuntu

## ⚠️ Diferencias importantes con macOS

Este servidor Ubuntu requiere configuración específica debido a las diferencias de rutas y sistema.

## 📋 Pasos para configurar PM2 en Ubuntu

### 1. 🔧 **En tu servidor Ubuntu**, ajusta la ruta en el archivo de configuración

Edita el archivo `ecosystem.ubuntu.config.js` y cambia esta línea:

```javascript
// Línea 7 y 70 - AJUSTAR SEGÚN TU SERVIDOR
cwd: '/home/ubuntu/nodejs/AI-RFX-Backend-Clean', // 👈 Cambia por tu ruta real
```

**Para encontrar tu ruta real:**

```bash
# En el servidor Ubuntu, dentro del directorio del proyecto:
pwd
```

### 2. 📁 **Verificar estructura del proyecto en Ubuntu**

Asegúrate de que existan estos archivos en tu servidor:

```bash
ls -la run_backend_simple.py  # ✅ Debe existir
ls -la venv/bin/python       # ✅ Virtual environment
ls -la .env                  # ✅ Variables de entorno
ls -la backend/             # ✅ Directorio del código
```

### 3. 🔄 **Limpiar PM2 actual**

```bash
# Detener procesos conflictivos
pm2 stop all
pm2 delete all
pm2 save --force
```

### 4. 🚀 **Iniciar con la configuración Ubuntu**

```bash
# Usar la configuración específica para Ubuntu
pm2 start ecosystem.ubuntu.config.js --only ai-rfx-backend-dev

# Verificar estado
pm2 status
```

### 5. 📊 **Verificar funcionamiento**

```bash
# Health check
curl http://localhost:3095/health

# Health detallado
curl http://localhost:3095/health/detailed

# Ver logs
pm2 logs ai-rfx-backend-dev
```

## 🛠️ **Solución de problemas comunes**

### Error: Script not found

```bash
# Verificar que el archivo existe
ls -la run_backend_simple.py

# Verificar permisos
chmod +x run_backend_simple.py
```

### Error: venv/bin/python not found

```bash
# Recrear virtual environment si es necesario
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Error: Module not found

```bash
# Verificar PYTHONPATH
cd /ruta/a/tu/proyecto
export PYTHONPATH=.
source venv/bin/activate
python -c "import backend.app; print('OK')"
```

## 🌐 **Configuración de puertos en Ubuntu**

Si el puerto 3095 está ocupado:

```bash
# Verificar qué usa el puerto
sudo lsof -ti:3095

# Cambiar puerto en ecosystem.ubuntu.config.js
# Buscar todas las líneas con "3095" y cambiar al puerto deseado
```

## 📋 **Comandos de gestión**

```bash
# Iniciar desarrollo
pm2 start ecosystem.ubuntu.config.js --only ai-rfx-backend-dev

# Iniciar producción
pm2 start ecosystem.ubuntu.config.js --only ai-rfx-backend-prod --env production

# Reiniciar
pm2 restart ai-rfx-backend-dev

# Ver logs
pm2 logs ai-rfx-backend-dev --lines 50

# Monitor
pm2 monit
```

## 🔄 **Auto-start en Ubuntu**

Para que PM2 se inicie automáticamente:

```bash
# Configurar auto-startup
pm2 startup ubuntu

# Ejecutar el comando que PM2 te muestre (con sudo)
# Después guardar la configuración actual:
pm2 save
```

## 📂 **Estructura de archivos esperada en Ubuntu**

```
/home/ubuntu/nodejs/AI-RFX-Backend-Clean/  # 👈 Tu ruta real
├── run_backend_simple.py
├── venv/
│   └── bin/
│       └── python
├── backend/
│   ├── app.py
│   ├── core/
│   └── ...
├── .env
├── ecosystem.ubuntu.config.js  # 👈 Usar este archivo
├── logs/                       # Se crea automáticamente
└── requirements.txt
```

## 🎯 **URLs del proyecto en Ubuntu**

Una vez funcionando:

- **Servidor**: `http://tu-servidor-ip:3095`
- **Health**: `http://tu-servidor-ip:3095/health`
- **API**: `http://tu-servidor-ip:3095/api/rfx/process`

## ⚡ **Quick Start Ubuntu**

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/tu/proyecto

# 2. Verificar archivos
ls -la run_backend_simple.py venv/bin/python .env

# 3. Limpiar PM2
pm2 delete all

# 4. Ajustar ruta en ecosystem.ubuntu.config.js
nano ecosystem.ubuntu.config.js  # Editar líneas 7 y 70

# 5. Iniciar
pm2 start ecosystem.ubuntu.config.js --only ai-rfx-backend-dev

# 6. Verificar
curl http://localhost:3095/health
```
