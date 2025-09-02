FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=0

WORKDIR /app

# Dependencias nativas para WeasyPrint, pdf2image, Tesseract y wkhtmltopdf + Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libasound2 libgbm1 \
    poppler-utils tesseract-ocr wkhtmltopdf \
    fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium || true

# Usa .dockerignore para reducir el contexto
COPY . .

# Railway usa la variable PORT automáticamente
ENV PORT=${PORT:-8080}
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 180 --access-logfile - --error-logfile -
