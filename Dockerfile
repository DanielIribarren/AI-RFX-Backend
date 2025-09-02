FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias mínimas para la aplicación básica
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Usar requirements mínimos (sin PDF/OCR/Playwright)
COPY requirements-minimal.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway usa la variable PORT automáticamente
ENV PORT=${PORT:-8080}
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 180 --access-logfile - --error-logfile -
