"""
🔍 Debug: Verificar usuarios faltantes en tabla users
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# User IDs de los logs
MISSING_USER_IDS = [
    "186ea35f-3cf8-480f-a7d3-0af178c09498",
    "c17f0d49-501c-40e4-8a63-c02c4f09ed90"
]

def check_users():
    """Verificar si usuarios existen en ambas tablas"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
    
    client: Client = create_client(supabase_url, supabase_key)
    
    print("=" * 80)
    print("🔍 VERIFICANDO USUARIOS FALTANTES")
    print("=" * 80)
    
    for user_id in MISSING_USER_IDS:
        print(f"\n📋 User ID: {user_id}")
        print("-" * 80)
        
        # 1. Verificar en tabla users (custom)
        try:
            response = client.table("users").select("*").eq("id", user_id).execute()
            if response.data:
                user = response.data[0]
                print(f"✅ EXISTE en tabla 'users':")
                print(f"   - Email: {user.get('email')}")
                print(f"   - Full Name: {user.get('full_name')}")
                print(f"   - Status: {user.get('status')}")
                print(f"   - Organization ID: {user.get('organization_id')}")
            else:
                print(f"❌ NO EXISTE en tabla 'users'")
        except Exception as e:
            print(f"❌ Error consultando tabla 'users': {e}")
        
        # 2. Verificar en auth.users (Supabase Auth)
        try:
            # Usar admin API para consultar auth.users
            response = client.auth.admin.get_user_by_id(user_id)
            if response:
                print(f"✅ EXISTE en 'auth.users' (Supabase Auth):")
                print(f"   - Email: {response.user.email}")
                print(f"   - Created At: {response.user.created_at}")
                print(f"   - Last Sign In: {response.user.last_sign_in_at}")
        except Exception as e:
            print(f"❌ NO EXISTE en 'auth.users': {e}")
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print("\n🔧 SOLUCIONES POSIBLES:")
    print("1. Si usuarios existen en auth.users pero NO en tabla users:")
    print("   → Ejecutar script de sincronización/migración")
    print("\n2. Si usuarios NO existen en ninguna tabla:")
    print("   → Tokens JWT inválidos o de ambiente diferente")
    print("\n3. Si usuarios existen en ambas pero status != 'active':")
    print("   → Actualizar status a 'active'")

if __name__ == "__main__":
    check_users()
