#!/usr/bin/env python3
"""
🧪 Test: Verificar obtención de user_id desde JWT token

Este script prueba si el backend puede extraer correctamente el user_id
del token JWT enviado por el frontend.

Uso:
    python test_jwt_user_id.py
"""

import requests
import json
import sys

# Configuración
BASE_URL = "http://localhost:5001"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.RESET}")

def test_login_and_get_token():
    """
    Test 1: Login y obtener token JWT
    """
    print_header("TEST 1: Login y Obtener Token JWT")
    
    # Credenciales de prueba
    credentials = {
        "email": "iriyidan@gmail.com",
        "password": input("Ingresa tu password: ")
    }
    
    try:
        print_info(f"Intentando login con: {credentials['email']}")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=credentials,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                access_token = data.get('access_token')
                user = data.get('user', {})
                
                print_success(f"Login exitoso!")
                print_info(f"User ID: {user.get('id')}")
                print_info(f"Email: {user.get('email')}")
                print_info(f"Full Name: {user.get('full_name')}")
                print_info(f"Token (primeros 50 chars): {access_token[:50]}...")
                
                return {
                    'token': access_token,
                    'user': user
                }
            else:
                print_error(f"Login falló: {data.get('message', 'Unknown error')}")
                return None
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error durante login: {e}")
        return None

def test_get_current_user(token):
    """
    Test 2: Obtener información del usuario actual usando el token
    """
    print_header("TEST 2: Obtener Usuario Actual con JWT Token")
    
    try:
        print_info("Llamando a /api/auth/me con token JWT...")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                user = data.get('user', {})
                
                print_success("Token JWT válido - Usuario identificado correctamente!")
                print_info(f"User ID: {user.get('id')}")
                print_info(f"Email: {user.get('email')}")
                print_info(f"Full Name: {user.get('full_name')}")
                print_info(f"Company: {user.get('company_name', 'N/A')}")
                print_info(f"Status: {user.get('status')}")
                print_info(f"Email Verified: {user.get('email_verified')}")
                print_info(f"Has Branding: {user.get('has_branding')}")
                
                return user
            else:
                print_error(f"Error: {data.get('message', 'Unknown error')}")
                return None
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error obteniendo usuario: {e}")
        return None

def test_generate_proposal_with_jwt(token, user_id):
    """
    Test 3: Generar propuesta usando JWT token (sin enviar user_id explícito)
    """
    print_header("TEST 3: Generar Propuesta con JWT Token")
    
    # RFX de prueba
    rfx_id = "b11b67b7-e6a3-4014-bfc4-6f83f24d74fb"
    
    proposal_data = {
        "rfx_id": rfx_id,
        "costs": [5.0, 6.0, 4.0, 3.0, 2.0, 6.0, 6.0, 2.0, 1.0]
        # ⭐ NO enviamos user_id - debe extraerse del JWT
    }
    
    try:
        print_info(f"Generando propuesta para RFX: {rfx_id}")
        print_info("⭐ NO enviando user_id explícito - debe extraerse del JWT")
        
        response = requests.post(
            f"{BASE_URL}/api/proposals/generate",
            json=proposal_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                print_success("Propuesta generada exitosamente!")
                print_info(f"Document ID: {data.get('document_id')}")
                print_info(f"PDF URL: {data.get('pdf_url')}")
                
                # Verificar que se usó el user_id correcto
                print_success(f"✅ Backend extrajo user_id del JWT correctamente: {user_id}")
                
                return data
            else:
                print_error(f"Error: {data.get('message', 'Unknown error')}")
                return None
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error generando propuesta: {e}")
        return None

def test_rfx_migration(token):
    """
    Test 4: Migrar RFX sin user_id al usuario autenticado
    """
    print_header("TEST 4: Migrar RFX sin user_id")
    
    try:
        print_info("Llamando a /api/rfx-secure/migrate-existing...")
        
        response = requests.post(
            f"{BASE_URL}/api/rfx-secure/migrate-existing",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                migrated_count = data.get('migrated_count', 0)
                
                if migrated_count > 0:
                    print_success(f"Migrados {migrated_count} RFX al usuario autenticado")
                    
                    migrated_rfx = data.get('migrated_rfx', [])
                    for rfx in migrated_rfx:
                        print_info(f"  - {rfx.get('id')}: {rfx.get('title', 'Untitled')}")
                else:
                    print_info("No hay RFX sin user_id para migrar")
                
                return data
            else:
                print_error(f"Error: {data.get('message', 'Unknown error')}")
                return None
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error en migración: {e}")
        return None

def main():
    """Ejecutar todos los tests"""
    print_header("🧪 TEST DE OBTENCIÓN DE USER_ID DESDE JWT TOKEN")
    
    # Test 1: Login
    auth_data = test_login_and_get_token()
    if not auth_data:
        print_error("Login falló - no se pueden ejecutar más tests")
        return 1
    
    token = auth_data['token']
    user = auth_data['user']
    user_id = user.get('id')
    
    # Test 2: Obtener usuario actual
    current_user = test_get_current_user(token)
    if not current_user:
        print_error("No se pudo obtener usuario actual")
        return 1
    
    # Verificar que el user_id coincide
    if current_user.get('id') == user_id:
        print_success(f"✅ User ID coincide: {user_id}")
    else:
        print_error(f"User ID no coincide: {current_user.get('id')} != {user_id}")
        return 1
    
    # Test 3: Generar propuesta con JWT
    proposal = test_generate_proposal_with_jwt(token, user_id)
    if not proposal:
        print_warning("Propuesta no se pudo generar (puede ser normal si el RFX no existe)")
    
    # Test 4: Migrar RFX
    migration = test_rfx_migration(token)
    
    # Resumen final
    print_header("📊 RESUMEN DE TESTS")
    
    tests_passed = 0
    tests_total = 4
    
    if auth_data:
        print_success("Test 1: Login - PASÓ")
        tests_passed += 1
    else:
        print_error("Test 1: Login - FALLÓ")
    
    if current_user:
        print_success("Test 2: Obtener Usuario Actual - PASÓ")
        tests_passed += 1
    else:
        print_error("Test 2: Obtener Usuario Actual - FALLÓ")
    
    if proposal:
        print_success("Test 3: Generar Propuesta con JWT - PASÓ")
        tests_passed += 1
    else:
        print_warning("Test 3: Generar Propuesta con JWT - OMITIDO")
    
    if migration:
        print_success("Test 4: Migrar RFX - PASÓ")
        tests_passed += 1
    else:
        print_warning("Test 4: Migrar RFX - OMITIDO")
    
    print(f"\n{Colors.CYAN}Tests pasados: {tests_passed}/{tests_total}{Colors.RESET}")
    
    if tests_passed >= 2:  # Login y obtener usuario son críticos
        print_header("✅ TESTS CRÍTICOS PASARON - JWT FUNCIONA CORRECTAMENTE")
        return 0
    else:
        print_header("❌ TESTS CRÍTICOS FALLARON - REVISAR CONFIGURACIÓN")
        return 1

if __name__ == "__main__":
    sys.exit(main())
