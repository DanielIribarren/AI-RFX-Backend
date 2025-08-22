# 🚀 AI-RFX Backend

Backend modular con arquitectura de servicios para procesamiento inteligente de documentos RFX.

## 📁 Estructura

\`\`\`
backend/
├── 🏗️ core/              # Configuración y funcionalidades centrales
│   ├── config.py          # Sistema de configuración unificado
│   ├── database.py        # Cliente Supabase con health checks
│   └── __init__.py
├── 🌐 api/                # Endpoints RESTful
│   ├── rfx.py             # APIs RFX con paginación y validación
│   └── __init__.py
├── 🧪 services/           # Lógica de negocio
│   ├── rfx_processor.py   # Procesamiento RFX con IA
│   └── __init__.py
├── 📊 models/             # DTOs y validación
│   ├── rfx_models.py      # Modelos RFX con Pydantic
│   ├── proposal_models.py # Modelos de propuestas
│   └── __init__.py
├── 🔧 utils/              # Utilidades reutilizables
│   ├── validators.py      # Validadores modulares
│   ├── text_utils.py      # Procesamiento de texto
│   └── __init__.py
├── 🚀 app.py              # Aplicación principal (App Factory)
└── 🏭 wsgi.py             # Punto de entrada WSGI para producción
\`\`\`

## ⚡ Inicio Rápido

\`\`\`bash
# Configuración automática
python setup-new-architecture.py

# Configurar credenciales
cp .env.example .env
nano .env  # Agregar OPENAI_API_KEY y Supabase

# Ejecutar aplicación
python backend/app.py
\`\`\`

## ✨ Características

### **App Factory Pattern**

\`\`\`python
from backend.app import create_app

app = create_app()  # Configuración automática por entorno
\`\`\`

### **DTOs con Validación Automática**

\`\`\`python
from backend.models.rfx_models import RFXInput

# Pydantic valida automáticamente
rfx = RFXInput(
    email="test@example.com",  # ✅ Validación email
    tipo_rfx="catering"        # ✅ Validación enum
)
\`\`\`

### **Configuración por Entorno**

\`\`\`python
from backend.core.config import config

# Detecta automáticamente desarrollo/producción
print(config.openai.api_key)  # Validado y seguro
print(config.database.url)    # Con health checks
\`\`\`

## 🌐 API Endpoints

### **Health Monitoring**

- `GET /health` - Estado básico
- `GET /health/detailed` - Estado completo con dependencias

### **RFX Management**

- `POST /api/rfx/process` - Procesar documento
- `GET /api/rfx/history?page=1&limit=10` - Historial paginado
- `GET /api/rfx/{id}` - Obtener RFX específico
- `PUT /api/rfx/{id}` - Actualizar RFX
- `DELETE /api/rfx/{id}` - Eliminar RFX

### **Proposals**

- `POST /api/proposals/generate` - Generar propuesta
- `GET /api/proposals/history` - Historial propuestas

## 🛠️ Desarrollo

### **Estructura Modular**

\`\`\`python
# Servicios separados
from backend.services.rfx_processor import RFXProcessor
processor = RFXProcessor()
result = processor.process_document(pdf_file)

# Validación automática
from backend.models.rfx_models import RFXProcessed
# Pydantic garantiza tipos correctos
\`\`\`

### **Logging Estructurado**

\`\`\`python
# Configuración automática por entorno
logger.info("🚀 Processing RFX...")     # Solo desarrollo
logger.error("❌ Processing failed")     # Siempre visible
\`\`\`

## 🔧 Configuración

### **Variables de Entorno**

\`\`\`bash
# Básicas (requeridas)
OPENAI_API_KEY=your-key
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key

# Entorno
ENVIRONMENT=development  # o 'production'
FLASK_PORT=5001
FLASK_DEBUG=true

# Seguridad
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000
\`\`\`

### **Configuración Avanzada**

\`\`\`python
from backend.core.config import config, Environment

# Detecta automáticamente el entorno
if config.environment == Environment.PRODUCTION:
    # Configuración de producción
    pass
elif config.environment == Environment.DEVELOPMENT:
    # Configuración de desarrollo
    pass
\`\`\`

## 🚦 Health Checks

\`\`\`bash
# Estado básico
curl http://localhost:5001/health

# Estado detallado
curl http://localhost:5001/health/detailed
\`\`\`

Respuesta detallada:

\`\`\`json
{
  "status": "healthy",
  "environment": "development",
  "version": "2.0",
  "checks": {
    "database": { "status": "healthy" },
    "openai": { "status": "healthy" }
  }
}
\`\`\`

## 🚀 Despliegue

### **Desarrollo**

\`\`\`bash
python backend/app.py
\`\`\`

### **Producción**

\`\`\`bash
# Con Gunicorn (recomendado)
pip install gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:5001

# Con configuración específica
ENVIRONMENT=production gunicorn backend.wsgi:application
\`\`\`

## 📊 Beneficios

- **🔧 Configuración automática** - Zero-setup con validación
- **✅ Validación robusta** - Pydantic elimina bugs de tipos
- **🚀 Rendimiento optimizado** - Conexiones reutilizadas
- **📊 Monitoreo incluido** - Health checks integrados
- **🔒 Seguridad mejorada** - Validación de entrada automática
- **🧪 Testing simplificado** - Servicios aislados y modulares

## 🚨 Troubleshooting

### **Import Errors**

\`\`\`bash
# Verificar estructura
python -c "from backend.core.config import config; print('✅ OK')"
\`\`\`

### **Database Connection**

\`\`\`bash
# Verificar health check
curl http://localhost:5001/health/detailed
\`\`\`

### **WeasyPrint Issues** (macOS)

\`\`\`bash
brew install pango gdk-pixbuf libffi
\`\`\`

---

**🎯 Backend modular, escalable y listo para producción**
