#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE="${1:-.env}"
TARGETS_RAW="${2:-production,preview}"

if ! command -v vercel >/dev/null 2>&1; then
  echo "❌ Vercel CLI no está instalado. Instala con: npm i -g vercel"
  exit 1
fi

if ! vercel whoami >/dev/null 2>&1; then
  echo "❌ No hay sesión activa en Vercel. Ejecuta: vercel login"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Archivo de variables no encontrado: $ENV_FILE"
  exit 1
fi

if [ ! -f ".vercel/project.json" ]; then
  if [ -n "${VERCEL_PROJECT_NAME:-}" ]; then
    vercel link --yes --project "$VERCEL_PROJECT_NAME"
  else
    vercel link --yes
  fi
fi

NORMALIZED_FILE="$(mktemp)"

awk '
  /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
  index($0, "=") == 0 { next }
  {
    key = $0
    sub(/=.*/, "", key)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)

    value = $0
    sub(/^[^=]*=/, "", value)
    if (value ~ /^\".*\"$/) {
      sub(/^\"/, "", value)
      sub(/\"$/, "", value)
    }
    if (value ~ /^'\''.*'\''$/) {
      sub(/^'\''/, "", value)
      sub(/'\''$/, "", value)
    }

    if (key == "UDINARY_CLOUD_NAME") key = "CLOUDINARY_CLOUD_NAME"
    if (key ~ /^(PORT|HOST|FLASK_ENV|FLASK_DEBUG|DEBUG|LOG_LEVEL|LOG_FILE)$/) next
    if (key == "ENVIRONMENT") value = "production"
    if (key == "UPLOAD_FOLDER") value = "/tmp/rfx_uploads"

    env[key] = value
  }
  END {
    for (key in env) {
      print key "=" env[key]
    }
  }
' "$ENV_FILE" > "$NORMALIZED_FILE"

required_keys=(
  SUPABASE_URL
  SUPABASE_ANON_KEY
  OPENAI_API_KEY
  SECRET_KEY
  CORS_ORIGINS
)

for key in "${required_keys[@]}"; do
  if ! grep -q "^${key}=" "$NORMALIZED_FILE"; then
    echo "❌ Falta variable requerida en $ENV_FILE: $key"
    rm -f "$NORMALIZED_FILE"
    exit 1
  fi
done

IFS=',' read -r -a TARGETS <<< "$TARGETS_RAW"

for target in "${TARGETS[@]}"; do
  target="$(echo "$target" | xargs)"
  if [[ "$target" != "production" && "$target" != "preview" && "$target" != "development" ]]; then
    echo "❌ Target inválido: $target (usa production,preview,development)"
    exit 1
  fi

  echo "🔄 Sincronizando variables para target: $target"
  while IFS= read -r line || [ -n "$line" ]; do
    key="${line%%=*}"
    value="${line#*=}"
    printf "%s" "$value" | vercel env add "$key" "$target" --force --sensitive >/dev/null
    echo "   ✅ $key"
  done < "$NORMALIZED_FILE"
done

rm -f "$NORMALIZED_FILE"

echo ""
echo "✅ Variables sincronizadas desde $ENV_FILE -> $TARGETS_RAW"
