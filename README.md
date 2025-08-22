# 🚀 AI-RFX Backend API

Backend API desarrollado con Flask para el procesamiento de RFX (Request for X) usando Inteligencia Artificial.

## 🏗️ Arquitectura

- **Framework**: Flask 3.0.2
- **Base de datos**: Supabase
- **IA**: OpenAI GPT-4o
- **Deploy**: Railway/Heroku compatible

## 📁 Estructura del Proyecto

```
AI-RFX-Backend/
├── backend/              # Código fuente principal
│   ├── api/             # Endpoints REST
│   ├── core/            # Configuración y DB
│   ├── models/          # Modelos de datos
│   ├── services/        # Lógica de negocio
│   ├── utils/           # Utilidades
│   └── tests/           # Tests unitarios
├── database/            # Scripts SQL (si aplica)
└── requirements.txt     # Dependencias Python
```

## 🚀 Quick Start

### 1. Instalación

```bash
pip install -r requirements.txt
```

### 2. Configuración

```bash
cp env.template .env
# Configurar variables en .env
```

### 3. Ejecutar

```bash
python start.py
```

## 🌐 API Endpoints

- `POST /api/rfx/process` - Procesar documento RFX
- `POST /api/proposals/generate` - Generar propuesta
- `GET /api/rfx/history` - Historial de RFX
- `GET /health/detailed` - Health check

## 🔧 Variables de Entorno

Ver `env.template` para la configuración completa.

## 🚢 Deploy

### Railway

```bash
railway deploy
```

### Heroku

```bash
heroku create tu-app
git push heroku main
```

## 🧪 Tests

```bash
pytest backend/tests/
```

## 📚 Funcionalidades

### 🤖 Procesamiento Inteligente
- Extracción automática de información de documentos RFX
- Soporte para PDF, DOC, DOCX, XLS, XLSX
- Procesamiento con OCR para documentos escaneados

### 📋 Generación de Propuestas
- Creación automática de propuestas comerciales
- Integración con plantillas HTML
- Exportación a PDF

### 📊 Sistema de Evaluación
- Métricas de calidad automáticas
- Sistema de evaluación A/B
- Monitoreo de performance de IA

### 🔧 Arquitectura Modular
- Separación clara de responsabilidades
- Configuración centralizada
- Sistema de feature flags

## 🛠️ Tecnologías

- **Backend**: Flask 3.0.2, Python 3.8+
- **IA**: OpenAI GPT-4o (128k context)
- **Base de datos**: Supabase
- **PDF**: WeasyPrint, ReportLab
- **Tests**: pytest
- **Deployment**: Gunicorn, Railway, Heroku

## 📝 Licencia

Proyecto privado - Todos los derechos reservados
