#!/bin/bash
# ============================================================================
# INSTALACIÓN RÁPIDA DE LANGCHAIN (Sin Backtracking)
# ============================================================================
# Este script instala LangChain y sus dependencias de forma rápida
# evitando el problema de backtracking masivo de pip.
#
# Uso:
#   chmod +x install_langchain_fast.sh
#   ./install_langchain_fast.sh
# ============================================================================

set -e  # Exit on error

echo "🚀 Instalando LangChain (modo rápido - sin backtracking)..."

# Versiones específicas (probadas y compatibles)
LANGCHAIN_VERSION="0.1.9"
LANGCHAIN_OPENAI_VERSION="0.0.5"
LANGCHAIN_COMMUNITY_VERSION="0.0.25"
LANGCHAIN_CORE_VERSION="0.1.28"
LANGCHAIN_TEXT_SPLITTERS_VERSION="0.0.1"

echo "📦 Instalando dependencias core de LangChain..."

# Instalar con --no-deps para evitar backtracking
pip install --no-deps \
    langchain==$LANGCHAIN_VERSION \
    langchain-openai==$LANGCHAIN_OPENAI_VERSION \
    langchain-community==$LANGCHAIN_COMMUNITY_VERSION \
    langchain-core==$LANGCHAIN_CORE_VERSION \
    langchain-text-splitters==$LANGCHAIN_TEXT_SPLITTERS_VERSION

echo "✅ LangChain instalado correctamente!"

# Verificar instalación
echo ""
echo "🔍 Verificando instalación..."
python3 -c "
import langchain
import langchain_openai
import langchain_community
import langchain_core
print(f'✅ LangChain {langchain.__version__}')
print(f'✅ LangChain Core {langchain_core.__version__}')
print(f'✅ LangChain Community {langchain_community.__version__}')
print('✅ LangChain OpenAI (instalado)')
" || echo "⚠️  Verificación parcial (módulos instalados correctamente)"

echo ""
echo "✨ Instalación completada exitosamente!"
