# ⚡ Guía de Inicio Rápido - AI-RFX Backend

## 🚀 **START EN 5 MINUTOS**

### **1. Configurar Entorno (2 minutos)**

```bash
# Clonar repositorio
git clone <repository-url>
cd AI-RFX-Backend

# Instalar dependencias
pip install -r requirements.txt

# Configurar credenciales
cp env.template .env
nano .env
# Agregar tu OPENAI_API_KEY y credenciales de Supabase
```

### **2. Ejecutar Aplicación (2 minutos)**

```bash
# Backend
python start.py

# O con Puerto personalizado
FLASK_PORT=5002 python start.py
```

### **3. Verificar Funcionamiento (1 minuto)**

```bash
# Health check
curl http://localhost:5001/health

# Health check detallado
curl http://localhost:5001/health/detailed
```

---

## 🌐 **ENDPOINTS PRINCIPALES**

### **Health & Monitoring**

```bash
GET /health                    # Estado básico
GET /health/detailed          # Estado completo con dependencias
```

### **RFX Management**

```bash
POST /api/rfx/process                    # Procesar documento RFX
GET /api/rfx/history?page=1&limit=10    # Historial con paginación
GET /api/rfx/{id}                       # Obtener RFX específico
PUT /api/rfx/{id}                       # Actualizar RFX
DELETE /api/rfx/{id}                    # Eliminar RFX
```

### **Proposals**

```bash
POST /api/proposals/generate             # Generar propuesta
GET /api/proposals/history              # Historial propuestas
GET /api/download/{id}                  # Descargar documento
```

---

## 💻 **COMANDOS ÚTILES**

### **Desarrollo**

```bash
# Aplicación principal
python start.py

# Con Gunicorn (producción)
gunicorn wsgi:application --bind 0.0.0.0:5001
```

### **Testing de APIs**

```bash
# Health checks
curl http://localhost:5001/health
curl http://localhost:5001/health/detailed

# Procesar RFX (requiere archivo PDF)
curl -X POST -F "pdf_file=@test.pdf" -F "id=TEST-001" \
  http://localhost:5001/api/rfx/process

# Historial con paginación
curl "http://localhost:5001/api/rfx/history?page=1&limit=5"

# Generar propuesta
curl -X POST -H "Content-Type: application/json" \
  -d '{"rfx_id":"TEST-001","costos":[100,200]}' \
  http://localhost:5001/api/proposals/generate
```

---

## 🔧 **CONFIGURACIÓN**

### **Variables de Entorno Clave**

```bash
# Básicas (requeridas)
OPENAI_API_KEY=your-openai-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-key

# Entorno
ENVIRONMENT=development  # o 'production'
DEBUG=true              # Solo desarrollo
PORT=5001

# Seguridad
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 🚨 **TROUBLESHOOTING**

### **Error: ModuleNotFoundError**

```bash
# Verificar directorio
pwd  # Debería mostrar .../AI-RFX-Backend

# Verificar entorno virtual
which python

# Reinstalar dependencias
pip install -r requirements.txt
```

### **Error: Database Connection**

```bash
# Verificar configuración
curl http://localhost:5001/health/detailed

# Verificar variables de entorno
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

### **Error: Puerto Ocupado**

```bash
# Verificar proceso usando puerto 5001
lsof -i :5001

# Usar puerto diferente
PORT=5002 python start.py
```

---

## 📝 **FLUJO DE TRABAJO**

1. **📄 Upload PDF** → Subir documento RFX
2. **🤖 AI Analysis** → IA extrae y estructura información
3. **💾 Store Data** → Datos guardados en Supabase
4. **📋 Generate Proposal** → IA crea propuesta comercial
5. **📥 Download** → Descargar documento final

---

## 🎉 **¡LISTO!**

El sistema está funcionando. Puedes:

1. **🔍 Explorar APIs** usando los endpoints documentados
2. **📄 Procesar documentos** subiendo PDFs reales
3. **📊 Monitorear salud** con `/health/detailed`
4. **🚀 Integrar frontend** usando las APIs REST

**¡Disfruta procesando documentos RFX con IA! 🤖**
