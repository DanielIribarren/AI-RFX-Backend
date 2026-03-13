#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

TARGET="${1:-preview}"

if [[ "$TARGET" == "--prod" ]]; then
  TARGET="production"
fi
if [[ "$TARGET" == "--preview" ]]; then
  TARGET="preview"
fi

if [[ "$TARGET" != "preview" && "$TARGET" != "production" ]]; then
  echo "Uso: ./scripts/vercel_deploy.sh [preview|production|--preview|--prod]"
  exit 1
fi

if ! command -v vercel >/dev/null 2>&1; then
  echo "❌ Vercel CLI no está instalado. Instala con: npm i -g vercel"
  exit 1
fi

if ! vercel whoami >/dev/null 2>&1; then
  echo "❌ No hay sesión activa en Vercel. Ejecuta: vercel login"
  exit 1
fi

if [ ! -f ".vercel/project.json" ]; then
  if [ -n "${VERCEL_PROJECT_NAME:-}" ]; then
    vercel link --yes --project "$VERCEL_PROJECT_NAME"
  else
    vercel link --yes
  fi
fi

echo "🚀 Deploy backend a Vercel ($TARGET)..."

if [ "$TARGET" = "production" ]; then
  vercel deploy --prod --yes
else
  vercel deploy --yes
fi
