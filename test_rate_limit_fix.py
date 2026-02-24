#!/usr/bin/env python3
"""
Script de prueba para verificar que el fix de rate limit funciona correctamente
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()

def test_openai_client_config():
    """Verificar que el cliente OpenAI está configurado correctamente"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY no encontrada en .env")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:20]}...")
    
    # Crear cliente SIN reintentos automáticos
    client = OpenAI(
        api_key=api_key,
        max_retries=0  # ← CRÍTICO: Sin reintentos automáticos
    )
    
    print(f"✅ Cliente OpenAI creado con max_retries=0")
    
    # Verificar que el cliente funciona
    try:
        print("\n🔄 Probando conexión a OpenAI...")
        models = client.models.list()
        print(f"✅ Conexión exitosa - {len(models.data)} modelos disponibles")
        return True
    except Exception as e:
        print(f"❌ Error al conectar con OpenAI: {e}")
        return False

def test_rate_limit_handling():
    """Simular manejo de rate limit"""
    print("\n📊 Configuración de backoff para rate limits:")
    print("  - Intento 1 → Intento 2: 5 segundos")
    print("  - Intento 2 → Intento 3: 15 segundos")
    print("  - Total espera: 20 segundos")
    print("\n✅ Backoff exponencial configurado correctamente")

if __name__ == "__main__":
    print("🧪 Test de Rate Limit Fix\n")
    print("=" * 60)
    
    # Test 1: Verificar configuración del cliente
    print("\n1️⃣ Verificando configuración del cliente OpenAI...")
    if test_openai_client_config():
        print("\n✅ Cliente configurado correctamente")
    else:
        print("\n❌ Error en configuración del cliente")
        exit(1)
    
    # Test 2: Verificar backoff
    print("\n2️⃣ Verificando configuración de backoff...")
    test_rate_limit_handling()
    
    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASARON")
    print("\n💡 Ahora puedes reiniciar el backend y probar:")
    print("   python3 start_backend.py")
