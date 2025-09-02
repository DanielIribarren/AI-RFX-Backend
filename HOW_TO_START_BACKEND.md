# 🚀 Cómo Iniciar el Backend - AI-RFX

## ⚡ **OPCIÓN RÁPIDA - Sin Virtual Environment**

Si solo quieres ejecutar el backend rápidamente:

```bash
cd AI-RFX-Backend-Clean
python3 run_backend_simple.py
```

**✅ Pros:**

- Funciona inmediatamente
- No necesita virtual environment
- Logging detallado automático

**⚠️ Contras:**

- Instala dependencias globalmente
- Puede tener conflictos con otros proyectos

---

## 🔧 **OPCIÓN COMPLETA - Con Virtual Environment**

Para desarrollo profesional con entorno aislado:

```bash
cd AI-RFX-Backend-Clean
python3 start_backend.py
```

**✅ Pros:**

- Entorno aislado
- Manejo automático de dependencias
- Checks completos de configuración
- Mejor para desarrollo a largo plazo

**📝 Nota:** Ahora maneja automáticamente el virtual environment

---

## 📋 **CONFIGURACIÓN REQUERIDA**

Antes de ejecutar cualquier opción, configura el archivo `.env`:

```bash
# 1. Copiar template
cp environment_template.txt .env

# 2. Editar con tus credenciales
nano .env  # o usar tu editor favorito
```

**Variables críticas:**

```bash
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
OPENAI_API_KEY=sk-tu-api-key
```

---

## 🔍 **Si Hay Problemas**

### Error: Virtual Environment

```bash
# Usa la opción simple
python3 run_backend_simple.py
```

### Error: Dependencias

```bash
# Instalar manualmente
pip install -r requirements.txt
```

### Error: Configuración

```bash
# Ejecutar diagnóstico
python3 diagnose_pricing.py
```

### Error: Base de datos

```bash
# Verificar credenciales en .env
# Ejecutar schema SQL en Supabase
```

---

## 🎯 **Verificar que Funciona**

Después de iniciar el backend:

```bash
# En otra terminal:
curl http://localhost:5001/health

# Debe retornar:
{"status": "healthy", ...}
```

---

## 📊 **URLs Disponibles**

Una vez iniciado:

- 🏠 **Health Check**: http://localhost:5001/health
- 🔧 **API Principal**: http://localhost:5001/api/
- 💰 **Pricing API**: http://localhost:5001/api/pricing/
- 📋 **Presets**: http://localhost:5001/api/pricing/presets

---

## 💡 **Recomendaciones**

### Para Desarrollo Rápido:

```bash
python3 run_backend_simple.py
```

### Para Desarrollo Profesional:

```bash
python3 start_backend.py
```

### Para Debugging:

```bash
python3 diagnose_pricing.py
```

**¡Usa la opción que mejor se adapte a tu flujo de trabajo!** 🚀
