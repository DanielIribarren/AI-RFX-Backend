#!/bin/bash
set -euo pipefail

# Dev wrapper: usa el flujo central de start_backend.py con auto-start.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

exec python3 start_backend.py "$@"
