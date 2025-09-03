# ===========================================
# AI-RFX Backend - Railway Optimized Dockerfile
# ===========================================
# Dockerfile optimizado específicamente para Railway
# Basado en las mejores prácticas de Railway

FROM python:3.12-slim

# Configuración de entorno optimizada para Railway
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (mínimas necesarias)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar y instalar dependencias de Python
COPY requirements.railway.txt .
RUN pip install --no-cache-dir -r requirements.railway.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para archivos temporales si no existe
RUN mkdir -p /tmp/rfx_uploads

# Configuración de salud y puerto (Railway inyecta PORT en runtime); exponemos 8080 por defecto
ENV PORT=8080
EXPOSE 8080

# Health check optimizado para Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'python - <<"PY" || exit 1
import os, sys
import requests
port = os.getenv("PORT", "8080")
try:
    r = requests.get(f"http://localhost:{port}/health", timeout=5)
    sys.exit(0 if r.status_code == 200 else 1)
except Exception:
    sys.exit(1)
PY'

# Comando optimizado para Railway
CMD sh -c 'exec gunicorn \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    --max-requests 100 \
    --max-requests-jitter 10 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class sync \
    --worker-tmp-dir /tmp \
    backend.wsgi:application'
