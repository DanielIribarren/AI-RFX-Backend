# 📦 Instalación de Dependencias del Sistema

Este proyecto requiere algunas dependencias del sistema operativo que **NO** pueden instalarse desde `requirements.txt`.

## ⚠️ Dependencias Requeridas

### 1. Poppler (para conversión de PDF a imagen)

Requerido por `pdf2image` para analizar templates PDF con GPT-4 Vision.

#### macOS
```bash
brew install poppler
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

#### Linux (CentOS/RHEL)
```bash
sudo yum install -y poppler-utils
```

#### Windows
1. Descargar desde: https://github.com/oschwartz10612/poppler-windows/releases
2. Extraer a `C:\Program Files\poppler`
3. Agregar al PATH: `C:\Program Files\poppler\Library\bin`

### 2. Cairo (para conversión de SVG a PNG)

Requerido por `cairosvg` para procesar logos SVG.

#### macOS
```bash
brew install cairo
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install -y libcairo2-dev
```

#### Linux (CentOS/RHEL)
```bash
sudo yum install -y cairo-devel
```

#### Windows
CairoSVG en Windows puede ser complicado. Alternativa: usar solo `svglib` (ya incluida en requirements.txt)

## ✅ Verificación de Instalación

Ejecuta este script para verificar que todo está instalado:

```bash
python scripts/check_system_dependencies.py
```

O manualmente:

```bash
# Verificar Poppler
pdfinfo --version

# Verificar Cairo (si usas cairosvg)
pkg-config --modversion cairo
```

## 🚀 Instalación Completa (Recomendada)

### macOS
```bash
# 1. Instalar dependencias del sistema
brew install poppler cairo

# 2. Instalar dependencias Python
pip install -r requirements.txt
```

### Linux
```bash
# 1. Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y poppler-utils libcairo2-dev

# 2. Instalar dependencias Python
pip install -r requirements.txt
```

## 🐳 Alternativa: Docker

Si prefieres evitar instalar dependencias del sistema, usa Docker:

```bash
docker-compose up
```

El `Dockerfile` ya incluye todas las dependencias necesarias.

## ❓ Solución de Problemas

### Error: "Unable to get page count. Is poppler installed and in PATH?"
- **Causa:** Poppler no está instalado o no está en el PATH
- **Solución:** Instalar poppler según tu sistema operativo (ver arriba)

### Error: "cannot identify image file '...logo.svg'"
- **Causa:** Cairo no está instalado (para cairosvg)
- **Solución:** El sistema usará automáticamente `svglib` como fallback (no requiere Cairo)

### Error al importar cairosvg
- **Causa:** Cairo no está instalado en el sistema
- **Solución:** El sistema usará automáticamente `svglib` como fallback
