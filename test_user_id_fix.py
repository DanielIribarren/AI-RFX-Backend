#!/usr/bin/env python3
"""
🧪 Script de Prueba: User ID Authentication Fix V3.2

Prueba los 3 escenarios de obtención de user_id:
1. Con JWT token (autenticado)
2. Con user_id en request body (sin autenticación)
3. Con user_id en base de datos del RFX

Uso:
    python test_user_id_fix.py
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuración
BASE_URL = "http://localhost:5001"
TEST_RFX_ID = "b11b67b7-e6a3-4014-bfc4-6f83f24d74fb"
TEST_USER_ID = "186ea35f-3cf8-480f-a7d3-0af178c09498"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name: str):
    """Imprime header de test"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 TEST: {name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(message: str):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message: str):
    """Imprime mensaje de error"""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_warning(message: str):
    """Imprime mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_info(message: str):
    """Imprime mensaje informativo"""
    print(f"ℹ️  {message}")

def test_scenario_1_with_jwt():
    """
    ESCENARIO 1: Usuario autenticado con JWT
    - Primero hacer login para obtener token
    - Usar token en request de propuesta
    """
    print_test("Escenario 1: Con JWT Token (Usuario Autenticado)")
    
    # Paso 1: Login
    print_info("Paso 1: Intentando login...")
    login_data = {
        "email": "daniel@example.com",  # Ajustar según tu usuario
        "password": "password123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            user_info = data.get("user", {})
            print_success(f"Login exitoso: {user_info.get('email')} (ID: {user_info.get('id')})")
            
            # Paso 2: Generar propuesta con JWT
            print_info("Paso 2: Generando propuesta con JWT token...")
            proposal_data = {
                "rfx_id": TEST_RFX_ID,
                "costs": [5.0, 6.0, 4.0, 3.0, 2.0, 6.0, 6.0, 2.0, 1.0]
            }
            
            response = requests.post(
                f"{BASE_URL}/api/proposals/generate",
                json=proposal_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"Propuesta generada: {result.get('document_id')}")
                print_success("✅ ESCENARIO 1 PASÓ - JWT funciona correctamente")
                return True
            else:
                print_error(f"Error generando propuesta: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        else:
            print_warning(f"Login falló: {response.status_code}")
            print_warning("Continuando con otros escenarios...")
            return None
            
    except Exception as e:
        print_error(f"Error en escenario 1: {e}")
        return False

def test_scenario_2_with_user_id_in_body():
    """
    ESCENARIO 2: Sin autenticación, user_id en request body
    - No enviar JWT token
    - Incluir user_id en el body del request
    """
    print_test("Escenario 2: Sin JWT, user_id en Request Body")
    
    print_info("Generando propuesta sin JWT, con user_id en body...")
    proposal_data = {
        "rfx_id": TEST_RFX_ID,
        "user_id": TEST_USER_ID,  # ⭐ user_id explícito
        "costs": [5.0, 6.0, 4.0, 3.0, 2.0, 6.0, 6.0, 2.0, 1.0]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/proposals/generate",
            json=proposal_data,
            headers={"Content-Type": "application/json"}
            # ⭐ Sin Authorization header
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Propuesta generada: {result.get('document_id')}")
            print_success("✅ ESCENARIO 2 PASÓ - user_id en body funciona")
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error en escenario 2: {e}")
        return False

def test_scenario_3_user_id_from_database():
    """
    ESCENARIO 3: Sin JWT, sin user_id en body, obtener de DB
    - No enviar JWT token
    - No incluir user_id en body
    - Sistema debe buscar en base de datos por rfx_id
    """
    print_test("Escenario 3: user_id desde Base de Datos del RFX")
    
    print_info("Generando propuesta sin JWT ni user_id (debe buscar en DB)...")
    proposal_data = {
        "rfx_id": TEST_RFX_ID,
        # ⭐ Sin user_id - debe obtenerlo de la DB
        "costs": [5.0, 6.0, 4.0, 3.0, 2.0, 6.0, 6.0, 2.0, 1.0]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/proposals/generate",
            json=proposal_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Propuesta generada: {result.get('document_id')}")
            print_success("✅ ESCENARIO 3 PASÓ - Búsqueda en DB funciona")
            return True
        elif response.status_code == 400:
            error_data = response.json()
            if "user_id is required" in error_data.get("message", ""):
                print_warning("RFX no tiene user_id en la base de datos")
                print_warning("Esto es esperado si el RFX no tiene user_id asignado")
                print_info("Para que este escenario funcione, el RFX debe tener user_id en la DB")
                return None
            else:
                print_error(f"Error inesperado: {error_data}")
                return False
        else:
            print_error(f"Error: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error en escenario 3: {e}")
        return False

def test_scenario_4_no_user_id_available():
    """
    ESCENARIO 4: Error esperado - Sin user_id disponible
    - No JWT
    - No user_id en body
    - RFX sin user_id en DB
    - Debe retornar error 400
    """
    print_test("Escenario 4: Error Esperado - Sin user_id Disponible")
    
    print_info("Intentando generar propuesta sin ninguna fuente de user_id...")
    proposal_data = {
        "rfx_id": "rfx-inexistente-sin-user-id",
        "costs": [5.0]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/proposals/generate",
            json=proposal_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 400:
            error_data = response.json()
            if "user_id is required" in error_data.get("message", ""):
                print_success("Error 400 retornado correctamente")
                print_success("✅ ESCENARIO 4 PASÓ - Validación funciona")
                return True
            else:
                print_error(f"Error 400 pero mensaje incorrecto: {error_data}")
                return False
        else:
            print_error(f"Debería retornar 400, pero retornó: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error en escenario 4: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🚀 INICIANDO TESTS DE USER ID FIX V3.2{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test RFX ID: {TEST_RFX_ID}")
    print(f"Test User ID: {TEST_USER_ID}")
    
    results = {
        "Escenario 1 (JWT)": test_scenario_1_with_jwt(),
        "Escenario 2 (Body)": test_scenario_2_with_user_id_in_body(),
        "Escenario 3 (DB)": test_scenario_3_user_id_from_database(),
        "Escenario 4 (Error)": test_scenario_4_no_user_id_available()
    }
    
    # Resumen
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}📊 RESUMEN DE RESULTADOS{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for scenario, result in results.items():
        if result is True:
            print_success(f"{scenario}: PASÓ")
            passed += 1
        elif result is False:
            print_error(f"{scenario}: FALLÓ")
            failed += 1
        else:
            print_warning(f"{scenario}: OMITIDO (no aplicable)")
            skipped += 1
    
    print(f"\n{Colors.BLUE}Total:{Colors.RESET} {passed + failed + skipped}")
    print(f"{Colors.GREEN}Pasados:{Colors.RESET} {passed}")
    print(f"{Colors.RED}Fallados:{Colors.RESET} {failed}")
    print(f"{Colors.YELLOW}Omitidos:{Colors.RESET} {skipped}")
    
    if failed == 0 and passed > 0:
        print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
        print(f"{Colors.GREEN}✅ TODOS LOS TESTS PASARON EXITOSAMENTE{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}")
        return 0
    elif failed > 0:
        print(f"\n{Colors.RED}{'='*60}{Colors.RESET}")
        print(f"{Colors.RED}❌ ALGUNOS TESTS FALLARON{Colors.RESET}")
        print(f"{Colors.RED}{'='*60}{Colors.RESET}")
        return 1
    else:
        print(f"\n{Colors.YELLOW}{'='*60}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  NO SE PUDIERON EJECUTAR TESTS{Colors.RESET}")
        print(f"{Colors.YELLOW}{'='*60}{Colors.RESET}")
        return 2

if __name__ == "__main__":
    sys.exit(main())
