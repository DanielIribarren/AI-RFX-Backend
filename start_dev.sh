#!/bin/bash

# 🛠️ Script de arranque para desarrollo - instala dependencias y levanta Flask

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "⚠️  venv no encontrado o inválido. Creando entorno virtual..."
  python3 -m venv "$VENV_DIR"
fi

echo "📦 Instalando dependencias desde requirements.txt..."
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS" --quiet

echo "🚀 Levantando backend Flask en puerto ${PORT:-5001}..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/run_backend_simple.py"
