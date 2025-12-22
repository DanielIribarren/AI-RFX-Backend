# 🔧 Backend Troubleshooting Guide - AI-RFX System

## 🎯 **PROBLEMA IDENTIFICADO Y SOLUCIONES**

### **📋 Resumen de Problemas Reportados:**

1. ❌ **Backend no arranca** con `python3 app.py`
2. ❌ **Configuraciones de pricing no se guardan**
3. ❌ **No se pueden ver logs** en terminal
4. ❌ **Errores al guardar coordinación y costo por persona**

---

## 🚀 **SOLUCIÓN RÁPIDA - 3 Pasos**

### **Paso 1: Configurar Entorno**

```bash
# 1. Navegar al directorio del backend
cd AI-RFX-Backend-Clean

# 2. Crear archivo .env (copiar template)
cp environment_template.txt .env

# 3. Editar .env con tus credenciales reales
nano .env  # o usar tu editor preferido
```

### **Paso 2: Usar Script de Inicio Mejorado**

```bash
# Usar el nuevo script que detecta y soluciona problemas automáticamente
python3 start_backend.py
```

### **Paso 3: Diagnosticar Problemas de Pricing**

```bash
# Si siguen los errores de pricing, ejecutar diagnóstico
python3 diagnose_pricing.py
```

---

## 📋 **CONFIGURACIÓN REQUERIDA EN .env**

```bash
# ========================
# CONFIGURACIÓN MÍNIMA REQUERIDA
# ========================

# Database (Supabase) - REQUERIDO
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key-aqui
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-aqui

# OpenAI API - REQUERIDO
OPENAI_API_KEY=sk-tu-api-key-aqui

# Server Config - OPCIONAL
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=5001
SECRET_KEY=tu-secret-key-aqui

# CORS - IMPORTANTE para frontend
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## 🔍 **DIAGNÓSTICOS PASO A PASO**

### **🔧 Problema 1: Backend No Arranca**

**Síntomas:**

- `python3 app.py` no funciona
- ImportError o ModuleNotFoundError
- Conexión rechazada

**Soluciones:**

```bash
# 1. Verificar Python y dependencias
python3 --version  # Debe ser 3.8+
pip3 --version

# 2. Activar entorno virtual
cd AI-RFX-Backend-Clean
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Usar el script mejorado
python3 start_backend.py
```

### **🔧 Problema 2: Configuraciones No Se Guardan**

**Síntomas:**

- Error: "Failed to retrieve pricing configuration"
- Configuraciones se pierden al recargar
- PUT requests fallan

**Causa:** Base de datos no configurada o tablas de pricing no existen

**Soluciones:**

```bash
# 1. Verificar conexión a base de datos
python3 diagnose_pricing.py

# 2. Si faltan tablas, ejecutar schema
# (Conectar a tu Supabase y ejecutar Complete-Schema-V2.2.sql)

# 3. Verificar credenciales en .env
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

### **🔧 Problema 3: No Se Ven Logs**

**Síntomas:**

- Terminal sin output
- No hay información de debug
- Errores sin detalles

**Soluciones:**

```bash
# 1. Usar script mejorado (logs en tiempo real)
python3 start_backend.py

# 2. O ejecutar con debug manual
cd backend
FLASK_DEBUG=1 PYTHONUNBUFFERED=1 python3 app.py

# 3. Verificar archivo de logs
tail -f ../backend.log
```

---

## 🎯 **TESTING DE FUNCIONALIDAD**

### **📊 Test 1: Verificar Backend Básico**

```bash
# 1. Iniciar backend
python3 start_backend.py

# 2. En otra terminal, test health check
curl http://localhost:5001/health

# Debe retornar: {"status": "healthy", ...}
```

### **📊 Test 2: Verificar API de Pricing**

```bash
# Test GET configuration
curl http://localhost:5001/api/pricing/config/test-rfx-123

# Test presets disponibles
curl http://localhost:5001/api/pricing/presets

# Deben retornar JSON con status: "success"
```

### **📊 Test 3: Verificar Guardado**

```bash
# Test configuración completa
curl -X PUT http://localhost:5001/api/pricing/config/test-rfx-123 \
  -H "Content-Type: application/json" \
  -d '{
    "coordination": {
      "enabled": true,
      "rate": 0.18,
      "type": "standard"
    },
    "cost_per_person": {
      "enabled": true,
      "headcount": 100,
      "calculation_base": "final_total"
    },
    "taxes": {
      "enabled": false,
      "rate": 0.16,
      "name": "IVA"
    }
  }'

# Debe retornar: {"status": "success", ...}
```

---

## 🛠️ **SOLUCIONES A ERRORES ESPECÍFICOS**

### **Error: "BackendPricingApiError: Failed to retrieve pricing configuration"**

**Causa:** Frontend no puede conectar al backend

**Soluciones:**

1. ✅ **Verificar backend corriendo**: `curl http://localhost:5001/health`
2. ✅ **Verificar CORS**: Agregar `CORS_ORIGINS=http://localhost:3000` a `.env`
3. ✅ **Verificar puerto**: Frontend debe apuntar a `localhost:5001`

### **Error: "Connection refused" o "Network error"**

**Causa:** Backend no está corriendo o puerto bloqueado

**Soluciones:**

1. ✅ **Iniciar backend**: `python3 start_backend.py`
2. ✅ **Verificar puerto libre**: `lsof -i :5001`
3. ✅ **Cambiar puerto**: Modificar `PORT=5002` en `.env`

### **Error: "No module named 'backend'"**

**Causa:** Python path o working directory incorrectos

**Soluciones:**

1. ✅ **Navegar al directorio correcto**: `cd AI-RFX-Backend-Clean`
2. ✅ **Ejecutar desde directorio raíz**: `python3 backend/app.py`
3. ✅ **Usar script mejorado**: `python3 start_backend.py`

### **Error: Database tables not found**

**Causa:** Schema de base de datos no inicializado

**Soluciones:**

1. ✅ **Conectar a Supabase Dashboard**
2. ✅ **Ejecutar SQL**: Copiar y ejecutar `Database/Complete-Schema-V2.2.sql`
3. ✅ **Verificar tablas**: Debe existir `rfx_pricing_configurations`

---

## 📱 **VERIFICACIÓN FRONTEND-BACKEND**

### **🔗 Conectividad Correcta:**

1. **Backend corriendo**: `localhost:5001` ✅
2. **Frontend corriendo**: `localhost:3000` ✅
3. **API URL configurada**: `NEXT_PUBLIC_API_URL=http://localhost:5001` ✅
4. **CORS configurado**: Backend permite origen frontend ✅

### **🔍 Debugging Steps:**

```bash
# 1. Backend health
curl http://localhost:5001/health

# 2. Pricing API test
curl http://localhost:5001/api/pricing/presets

# 3. Frontend console (navegador)
# Verificar Network tab en DevTools

# 4. Backend logs
# Usar: python3 start_backend.py (logs en tiempo real)
```

---

## 🎉 **ESTADO FINAL ESPERADO**

### **✅ Backend Funcionando:**

```
🚀 Starting AI-RFX Backend...
📊 Server will be available at: http://localhost:5001
💰 Pricing API: http://localhost:5001/api/pricing/
✅ Database connection OK
✅ All blueprints registered successfully
✅ Pricing configuration tables accessible
* Running on http://0.0.0.0:5001
```

### **✅ Frontend Conectado:**

```
🔄 Attempting to load pricing config for RFX: 12345
✅ Successfully loaded pricing config from backend
💾 Saving configuration...
✅ Configuration saved successfully
```

### **✅ Logs Visibles:**

- ✅ Logs del backend en tiempo real
- ✅ Requests HTTP visibles
- ✅ Errores de base de datos detectables
- ✅ Debugging información completa

---

## 🆘 **CONTACTO DE EMERGENCIA**

Si después de seguir esta guía sigues teniendo problemas:

1. **Ejecutar diagnóstico completo**: `python3 diagnose_pricing.py`
2. **Capturar logs**: Copiar salida completa de `python3 start_backend.py`
3. **Verificar Network tab**: En DevTools del navegador
4. **Compartir configuración**: Archivo `.env` (sin credenciales)

**Los archivos de diagnóstico generarán reportes detallados para identificar el problema exacto.** 🔍
