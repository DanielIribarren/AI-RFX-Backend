"""
🔍 Script de Diagnóstico - Estado de Cloudinary
Verifica si los logos están en Cloudinary y si la BD está actualizada
"""
import os
import sys
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from core.database import DatabaseClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def diagnose_user_logo(user_id: str):
    """Diagnostica el estado del logo de un usuario"""
    print(f"\n{'='*60}")
    print(f"🔍 DIAGNÓSTICO DE LOGO - User ID: {user_id}")
    print(f"{'='*60}\n")
    
    # Conectar a BD
    db = DatabaseClient()
    
    try:
        # 1. Verificar si existe registro en BD
        print("📊 PASO 1: Verificando registro en BD...")
        response = db.client.table("company_branding_assets")\
            .select("user_id, logo_filename, logo_path, logo_url, logo_uploaded_at, is_active")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()
        
        if not response.data:
            print("❌ No se encontró registro de branding para este usuario")
            print("💡 Acción: Subir logo desde Company Branding Settings")
            return
        
        branding = response.data[0]
        print("✅ Registro encontrado en BD")
        print(f"   - Logo filename: {branding.get('logo_filename')}")
        print(f"   - Logo path: {branding.get('logo_path')}")
        print(f"   - Logo URL: {branding.get('logo_url')}")
        print(f"   - Uploaded at: {branding.get('logo_uploaded_at')}")
        
        # 2. Verificar tipo de URL
        print("\n📍 PASO 2: Analizando tipo de URL...")
        logo_url = branding.get('logo_url')
        
        if not logo_url:
            print("❌ logo_url es NULL en la BD")
            print("💡 Acción: Re-subir logo para generar URL")
            return
        
        if logo_url.startswith('http://') or logo_url.startswith('https://'):
            print("✅ URL es PÚBLICA (absoluta)")
            
            if 'cloudinary.com' in logo_url:
                print("✅ URL es de CLOUDINARY")
                print(f"   🌥️ URL: {logo_url}")
                print("\n🎉 CONFIGURACIÓN CORRECTA - Logo en Cloudinary")
                print("   El logo debería verse en los PDFs generados")
            else:
                print("⚠️ URL pública pero NO es de Cloudinary")
                print(f"   URL: {logo_url}")
                print("💡 Puede funcionar si la URL es accesible públicamente")
        else:
            print("❌ URL es RELATIVA (local)")
            print(f"   URL: {logo_url}")
            print("   Esto NO funciona en servidor PM2")
            print("\n💡 ACCIÓN REQUERIDA:")
            print("   1. Re-subir logo desde Company Branding Settings")
            print("   2. El sistema lo subirá automáticamente a Cloudinary")
            print("   3. La URL se actualizará a URL pública")
        
        # 3. Verificar si archivo local existe
        print("\n📁 PASO 3: Verificando archivo local...")
        logo_path = branding.get('logo_path')
        
        if logo_path and not logo_path.startswith('http'):
            # Es path local
            if Path(logo_path).exists():
                print(f"✅ Archivo local existe: {logo_path}")
            else:
                print(f"❌ Archivo local NO existe: {logo_path}")
        else:
            print("ℹ️ No hay path local (logo en Cloudinary)")
        
        # 4. Verificar configuración de Cloudinary
        print("\n⚙️ PASO 4: Verificando configuración de Cloudinary...")
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        if cloud_name and api_key and api_secret:
            print("✅ Variables de entorno de Cloudinary configuradas")
            print(f"   - Cloud Name: {cloud_name}")
            print(f"   - API Key: {api_key}")
            print(f"   - API Secret: {'*' * len(api_secret) if api_secret else 'NOT SET'}")
        else:
            print("❌ Variables de entorno de Cloudinary NO configuradas")
            print("💡 Acción: Agregar a .env:")
            print("   CLOUDINARY_CLOUD_NAME=dffys3mxv")
            print("   CLOUDINARY_API_KEY=287712473884852")
            print("   CLOUDINARY_API_SECRET=your_secret_here")
        
        # 5. Resumen y recomendaciones
        print(f"\n{'='*60}")
        print("📋 RESUMEN Y RECOMENDACIONES")
        print(f"{'='*60}\n")
        
        if logo_url and 'cloudinary.com' in logo_url:
            print("🎉 ESTADO: CORRECTO")
            print("   - Logo en Cloudinary: ✅")
            print("   - URL pública en BD: ✅")
            print("   - Debería funcionar en PDFs: ✅")
            print("\n💡 Si el logo NO se ve en PDFs:")
            print("   1. Verificar que Playwright esté instalado")
            print("   2. Verificar logs del servidor")
            print("   3. Probar generar nuevo presupuesto")
        else:
            print("⚠️ ESTADO: REQUIERE ACCIÓN")
            print("   - Logo en Cloudinary: ❌")
            print("   - URL pública en BD: ❌")
            print("   - Funcionará en PDFs: ❌")
            print("\n💡 PASOS PARA CORREGIR:")
            print("   1. Ir a Company Branding Settings en el frontend")
            print("   2. Re-subir el logo (mismo archivo está bien)")
            print("   3. El sistema lo subirá automáticamente a Cloudinary")
            print("   4. Ejecutar este script nuevamente para verificar")
            print("   5. Generar nuevo presupuesto y descargar PDF")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def list_all_users_with_branding():
    """Lista todos los usuarios con branding configurado"""
    print(f"\n{'='*60}")
    print("📋 USUARIOS CON BRANDING CONFIGURADO")
    print(f"{'='*60}\n")
    
    db = DatabaseClient()
    
    try:
        response = db.client.table("company_branding_assets")\
            .select("user_id, logo_filename, logo_url, is_active")\
            .eq("is_active", True)\
            .execute()
        
        if not response.data:
            print("ℹ️ No hay usuarios con branding configurado")
            return []
        
        print(f"Total usuarios: {len(response.data)}\n")
        
        user_ids = []
        for idx, branding in enumerate(response.data, 1):
            user_id = branding.get('user_id')
            logo_url = branding.get('logo_url', '')
            
            status = "🌥️ Cloudinary" if 'cloudinary.com' in logo_url else "📁 Local"
            
            print(f"{idx}. User ID: {user_id}")
            print(f"   Logo: {branding.get('logo_filename')}")
            print(f"   Status: {status}")
            print(f"   URL: {logo_url[:60]}..." if len(logo_url) > 60 else f"   URL: {logo_url}")
            print()
            
            user_ids.append(user_id)
        
        return user_ids
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE CLOUDINARY - LOGOS")
    print("="*60)
    
    # Listar todos los usuarios
    user_ids = list_all_users_with_branding()
    
    # Si hay argumentos, diagnosticar usuario específico
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        diagnose_user_logo(user_id)
    elif user_ids:
        # Diagnosticar el primer usuario encontrado
        print(f"\n💡 Diagnosticando primer usuario: {user_ids[0]}")
        print("   (Usa: python scripts/diagnose_cloudinary_status.py <user_id> para otro usuario)")
        diagnose_user_logo(user_ids[0])
    else:
        print("\n💡 No hay usuarios con branding configurado")
        print("   Sube un logo desde Company Branding Settings")
    
    print("\n" + "="*60)
    print("✅ Diagnóstico completado")
    print("="*60 + "\n")
