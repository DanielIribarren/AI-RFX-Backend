"""
🔄 Script de Migración - Logos Locales a Cloudinary
Migra logos existentes del filesystem local a Cloudinary CDN
"""
import os
import sys
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from core.database import DatabaseClient
from services.cloudinary_service import upload_logo
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def migrate_user_logo(user_id: str, dry_run: bool = True):
    """
    Migra el logo de un usuario de filesystem local a Cloudinary
    
    Args:
        user_id: ID del usuario
        dry_run: Si True, solo simula la migración sin ejecutarla
    """
    print(f"\n{'='*60}")
    print(f"🔄 MIGRACIÓN DE LOGO - User ID: {user_id}")
    print(f"   Modo: {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"{'='*60}\n")
    
    db = DatabaseClient()
    
    try:
        # 1. Obtener información actual de BD
        print("📊 PASO 1: Obteniendo información de BD...")
        response = db.client.table("company_branding_assets")\
            .select("user_id, logo_filename, logo_path, logo_url")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()
        
        if not response.data:
            print("❌ No se encontró registro de branding para este usuario")
            return False
        
        branding = response.data[0]
        logo_url = branding.get('logo_url', '')
        logo_path = branding.get('logo_path', '')
        
        print(f"✅ Registro encontrado")
        print(f"   - Logo URL actual: {logo_url}")
        print(f"   - Logo path actual: {logo_path}")
        
        # 2. Verificar si ya está en Cloudinary
        if 'cloudinary.com' in logo_url:
            print("\n✅ Logo YA está en Cloudinary")
            print(f"   URL: {logo_url}")
            print("   No se requiere migración")
            return True
        
        # 3. Verificar si el archivo local existe
        print("\n📁 PASO 2: Verificando archivo local...")
        
        if not logo_path or logo_path.startswith('http'):
            print("❌ No hay path local válido para migrar")
            return False
        
        local_file = Path(logo_path)
        
        if not local_file.exists():
            print(f"❌ Archivo local NO existe: {logo_path}")
            print("💡 Acción: Re-subir logo desde Company Branding Settings")
            return False
        
        print(f"✅ Archivo local encontrado: {logo_path}")
        print(f"   Tamaño: {local_file.stat().st_size / 1024:.2f} KB")
        
        # 4. Subir a Cloudinary (si no es dry run)
        if dry_run:
            print("\n🔍 PASO 3: SIMULACIÓN - Subida a Cloudinary")
            print("   ⚠️ Modo DRY RUN - No se ejecutará la subida")
            print(f"   Se subiría: {logo_path}")
            print(f"   Destino: Cloudinary CDN (logos/{user_id}/logo)")
            cloudinary_url = f"https://res.cloudinary.com/dffys3mxv/image/upload/v123/logos/{user_id}/logo"
        else:
            print("\n☁️ PASO 3: Subiendo a Cloudinary...")
            
            with open(local_file, 'rb') as f:
                cloudinary_url = upload_logo(user_id, f)
            
            print(f"✅ Logo subido a Cloudinary")
            print(f"   URL: {cloudinary_url}")
        
        # 5. Actualizar BD (si no es dry run)
        if dry_run:
            print("\n🔍 PASO 4: SIMULACIÓN - Actualización de BD")
            print("   ⚠️ Modo DRY RUN - No se actualizará la BD")
            print(f"   Se actualizaría logo_url a: {cloudinary_url}")
        else:
            print("\n💾 PASO 4: Actualizando BD...")
            
            update_response = db.client.table("company_branding_assets")\
                .update({
                    "logo_url": cloudinary_url,
                    "logo_path": cloudinary_url  # También actualizar path
                })\
                .eq("user_id", user_id)\
                .execute()
            
            print(f"✅ BD actualizada con nueva URL")
            
            # Verificar
            verify = db.client.table("company_branding_assets")\
                .select("logo_url")\
                .eq("user_id", user_id)\
                .execute()
            
            if verify.data and verify.data[0].get('logo_url') == cloudinary_url:
                print(f"✅ Verificación exitosa - URL guardada correctamente")
            else:
                print(f"❌ Verificación FALLÓ")
                return False
        
        # 6. Resumen
        print(f"\n{'='*60}")
        print("📋 RESUMEN DE MIGRACIÓN")
        print(f"{'='*60}\n")
        
        if dry_run:
            print("🔍 SIMULACIÓN COMPLETADA")
            print("   Para ejecutar la migración real:")
            print(f"   python scripts/migrate_logos_to_cloudinary.py {user_id} --execute")
        else:
            print("✅ MIGRACIÓN COMPLETADA")
            print(f"   - Logo subido a Cloudinary: ✅")
            print(f"   - BD actualizada: ✅")
            print(f"   - URL pública: {cloudinary_url}")
            print("\n💡 Próximos pasos:")
            print("   1. Generar nuevo presupuesto")
            print("   2. Descargar PDF")
            print("   3. Verificar que el logo sea visible")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR durante migración: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_all_users(dry_run: bool = True):
    """Migra logos de todos los usuarios con branding local"""
    print(f"\n{'='*60}")
    print("🔄 MIGRACIÓN MASIVA - TODOS LOS USUARIOS")
    print(f"   Modo: {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"{'='*60}\n")
    
    db = DatabaseClient()
    
    try:
        # Obtener todos los usuarios con logos locales
        response = db.client.table("company_branding_assets")\
            .select("user_id, logo_url")\
            .eq("is_active", True)\
            .execute()
        
        if not response.data:
            print("ℹ️ No hay usuarios con branding configurado")
            return
        
        # Filtrar usuarios con logos locales (no Cloudinary)
        users_to_migrate = [
            u for u in response.data 
            if u.get('logo_url') and 'cloudinary.com' not in u.get('logo_url', '')
        ]
        
        if not users_to_migrate:
            print("✅ Todos los logos ya están en Cloudinary")
            return
        
        print(f"📋 Usuarios a migrar: {len(users_to_migrate)}")
        print(f"   (De {len(response.data)} usuarios con branding)\n")
        
        # Migrar cada usuario
        success_count = 0
        fail_count = 0
        
        for idx, user in enumerate(users_to_migrate, 1):
            user_id = user['user_id']
            print(f"\n[{idx}/{len(users_to_migrate)}] Migrando usuario: {user_id}")
            
            if migrate_user_logo(user_id, dry_run=dry_run):
                success_count += 1
            else:
                fail_count += 1
        
        # Resumen final
        print(f"\n{'='*60}")
        print("📊 RESUMEN FINAL")
        print(f"{'='*60}\n")
        print(f"Total usuarios procesados: {len(users_to_migrate)}")
        print(f"✅ Exitosos: {success_count}")
        print(f"❌ Fallidos: {fail_count}")
        
        if dry_run:
            print("\n🔍 SIMULACIÓN COMPLETADA")
            print("   Para ejecutar la migración real:")
            print("   python scripts/migrate_logos_to_cloudinary.py --all --execute")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔄 MIGRACIÓN DE LOGOS A CLOUDINARY")
    print("="*60)
    
    # Verificar configuración de Cloudinary
    if not os.getenv('CLOUDINARY_API_SECRET'):
        print("\n❌ ERROR: CLOUDINARY_API_SECRET no configurado en .env")
        print("   Agregar: CLOUDINARY_API_SECRET=your_secret_here")
        sys.exit(1)
    
    # Parsear argumentos
    dry_run = '--execute' not in sys.argv
    migrate_all = '--all' in sys.argv
    
    if dry_run:
        print("\n🔍 MODO: DRY RUN (Simulación)")
        print("   No se realizarán cambios reales")
        print("   Usa --execute para ejecutar la migración real\n")
    else:
        print("\n⚠️ MODO: EJECUCIÓN REAL")
        print("   Se realizarán cambios en Cloudinary y BD")
        print("   Presiona Ctrl+C para cancelar...\n")
        import time
        time.sleep(3)
    
    if migrate_all:
        # Migrar todos los usuarios
        migrate_all_users(dry_run=dry_run)
    elif len(sys.argv) > 1 and sys.argv[1] not in ['--execute', '--all']:
        # Migrar usuario específico
        user_id = sys.argv[1]
        migrate_user_logo(user_id, dry_run=dry_run)
    else:
        # Mostrar ayuda
        print("\n💡 USO:")
        print("   # Simular migración de un usuario:")
        print("   python scripts/migrate_logos_to_cloudinary.py <user_id>")
        print()
        print("   # Ejecutar migración real de un usuario:")
        print("   python scripts/migrate_logos_to_cloudinary.py <user_id> --execute")
        print()
        print("   # Simular migración de todos los usuarios:")
        print("   python scripts/migrate_logos_to_cloudinary.py --all")
        print()
        print("   # Ejecutar migración real de todos los usuarios:")
        print("   python scripts/migrate_logos_to_cloudinary.py --all --execute")
    
    print("\n" + "="*60)
    print("✅ Script completado")
    print("="*60 + "\n")
