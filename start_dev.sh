#!/bin/bash

# 🛠️ Script de arranque para desarrollo - instala dependencias y levanta Flask

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

echo "📦 Instalando dependencias desde requirements.txt..."
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" --quiet

echo "🚀 Levantando backend Flask en puerto ${PORT:-3186}..."
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/run_backend_simple.py"
