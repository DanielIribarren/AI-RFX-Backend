#!/usr/bin/env python3
"""
Script para ejecutar tests de agentes AI con variables de entorno
"""

import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Verificar que las variables estén cargadas
required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
    print("💡 Asegúrate de tener un archivo .env con las variables necesarias")
    sys.exit(1)

print("✅ Variables de entorno cargadas correctamente")
print("")

# Ahora ejecutar los tests
import subprocess
result = subprocess.run(
    [sys.executable, "tests/test_ai_agents_system.py"],
    cwd=Path(__file__).parent
)

sys.exit(result.returncode)
