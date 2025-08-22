# 🚀 AI-RFX-Backend

Backend inteligente para automatización de procesamiento de documentos RFX (Request for eXchange) con IA.

## 📋 Descripción

Sistema backend modular construido con Flask que procesa documentos RFX utilizando inteligencia artificial para extraer información, generar propuestas automáticas y gestionar el flujo completo de solicitudes de cotización.

## ✨ Características Principales

- **🤖 Procesamiento IA**: Extracción automática de datos de PDFs/DOCX usando OpenAI GPT-4o
- **📊 Gestión RFX**: API completa para manejo de solicitudes, empresas y productos
- **📄 Generación Automática**: Creación de propuestas comerciales en HTML/PDF
- **🔧 Arquitectura Modular**: Servicios separados, validación Pydantic, configuración por entorno
- **🏥 Health Checks**: Monitoreo de estado de base de datos y servicios externos
- **🌐 API RESTful**: Endpoints documentados con paginación y validación

## 📁 Estructura del Proyecto

```
backend/
├── 🏗️ core/              # Configuración y funcionalidades centrales
│   ├── config.py          # Sistema de configuración unificado
│   ├── database.py        # Cliente Supabase con health checks
│   └── feature_flags.py   # Flags de características
├── 🌐 api/                # Endpoints RESTful
│   ├── rfx.py             # APIs RFX con paginación
│   ├── proposals.py       # Gestión de propuestas
│   └── download.py        # Descarga de documentos
├── 🧪 services/           # Lógica de negocio
│   ├── rfx_processor.py   # Procesamiento RFX con IA
│   ├── proposal_generator.py # Generación de propuestas
│   └── evaluation_orchestrator.py # Evaluaciones
├── 📊 models/             # Modelos de datos y validación
│   ├── rfx_models.py      # Modelos RFX con Pydantic
│   └── proposal_models.py # Modelos de propuestas
├── 🔧 utils/              # Utilidades reutilizables
│   ├── validators.py      # Validadores modulares
│   └── text_utils.py      # Procesamiento de texto
├── 🧪 evals/              # Sistema de evaluaciones
│   ├── base_evaluator.py  # Evaluador base
│   └── extraction_evals.py # Evaluaciones de extracción
├── 📋 tests/              # Suite de pruebas
│   ├── unit/              # Pruebas unitarias
│   └── integration/       # Pruebas de integración
├── 🚀 app.py              # Aplicación principal (App Factory)
└── 🏭 wsgi.py             # Punto de entrada WSGI para producción
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.9+
- Cuenta OpenAI (API Key)
- Base de datos Supabase

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/DanielIribarren/AI-RFX-Backend.git
cd AI-RFX-Backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Configuración de Variables de Entorno

```bash
# Básicas (requeridas)
OPENAI_API_KEY=tu-api-key-de-openai
SUPABASE_URL=tu-url-de-supabase
SUPABASE_ANON_KEY=tu-anon-key-de-supabase

# Entorno
ENVIRONMENT=development
PORT=5001
DEBUG=true

# Seguridad
SECRET_KEY=tu-clave-secreta

# CORS (opcional)
CORS_ORIGINS=http://localhost:3000
```

### Ejecutar la Aplicación

```bash
# Desarrollo
python backend/app.py

# Producción con Gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:5001
```

## 🌐 API Endpoints

### Health Monitoring
- `GET /health` - Estado básico del sistema
- `GET /health/detailed` - Estado detallado con dependencias

### RFX Management
- `POST /api/rfx/process` - Procesar documento RFX
- `GET /api/rfx/history` - Historial paginado de RFX
- `GET /api/rfx/recent` - RFX recientes para sidebar
- `GET /api/rfx/{id}` - Obtener RFX específico
- `PUT /api/rfx/{id}/data` - Actualizar datos del RFX
- `PUT /api/rfx/{id}/products/costs` - Actualizar costos de productos

### Proposals
- `POST /api/proposals/generate` - Generar propuesta comercial
- `GET /api/proposals/history` - Historial de propuestas

### Downloads
- `GET /api/download/{document_id}` - Descargar documento generado

## 🛠️ Desarrollo

### Estructura de Servicios

```python
# Procesamiento RFX
from backend.services.rfx_processor import RFXProcessorService
processor = RFXProcessorService()
result = processor.process_rfx_case(rfx_input, files)

# Validación automática con Pydantic
from backend.models.rfx_models import RFXInput, RFXType
rfx = RFXInput(id="RFX-001", rfx_type=RFXType.CATERING)
```

### Ejecutar Tests

```bash
# Todas las pruebas
pytest

# Pruebas específicas
pytest backend/tests/unit/
pytest backend/tests/integration/

# Con cobertura
pytest --cov=backend
```

### Linting y Formato

```bash
# Formato de código
black backend/

# Linting
flake8 backend/

# Ordenar imports
isort backend/
```

## 🔧 Configuración Avanzada

### Feature Flags

```bash
# Habilitar evaluaciones
ENABLE_EVALS=true

# Habilitar meta-prompting
ENABLE_META_PROMPTING=true

# Modo debug para evaluaciones
EVAL_DEBUG_MODE=true
```

### Configuración de OpenAI

```bash
# Modelo y parámetros
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4096
OPENAI_TEMPERATURE=0.1
OPENAI_TIMEOUT=60
```

## 📊 Características Técnicas

- **⚡ Alto Rendimiento**: GPT-4o con 128k tokens de contexto
- **🔒 Validación Robusta**: Pydantic para tipos y validación automática
- **🏗️ App Factory**: Configuración modular por entorno
- **💾 Base de Datos Normalizada**: Esquema V2.0 con relaciones optimizadas
- **📈 Monitoreo**: Health checks y logging estructurado
- **🔄 Compatibilidad**: Mantiene endpoints legacy para migración

## 🚦 Health Checks

```bash
# Estado básico
curl http://localhost:5001/health

# Estado detallado
curl http://localhost:5001/health/detailed
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "2.0",
  "checks": {
    "database": { "status": "healthy" },
    "openai": { "status": "healthy" }
  }
}
```

## 🤝 Contribuciones

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🎯 Roadmap

- [ ] Integración con más formatos de documento
- [ ] Dashboard de analytics
- [ ] API de webhooks
- [ ] Integración con sistemas ERP
- [ ] Soporte multiidioma
- [ ] Cache distribuido con Redis

## 📞 Soporte

Para soporte o preguntas:
- 📧 Email: [tu-email@ejemplo.com]
- 🐛 Issues: [GitHub Issues](https://github.com/DanielIribarren/AI-RFX-Backend/issues)
- 📖 Docs: [Documentación completa](./docs/)

---

**🎯 Sistema RFX inteligente - Automatiza tu flujo de cotizaciones con IA**
