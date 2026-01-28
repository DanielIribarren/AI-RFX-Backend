"""
🔄 Sincronizar usuarios de auth.users a tabla users
Soluciona el problema: "User not found" cuando JWT es válido
"""
import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.database import DatabaseClient
from backend.core.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User IDs problemáticos de los logs
MISSING_USER_IDS = [
    "186ea35f-3cf8-480f-a7d3-0af178c09498",
    "c17f0d49-501c-40e4-8a63-c02c4f09ed90"
]

def sync_users():
    """Sincronizar usuarios de auth.users a tabla users"""
    
    config = Config()
    db = DatabaseClient(config)
    
    logger.info("=" * 80)
    logger.info("🔄 INICIANDO SINCRONIZACIÓN DE USUARIOS")
    logger.info("=" * 80)
    
    # 1. Obtener organización por defecto
    try:
        org_response = db.client.table("organizations")\
            .select("id")\
            .eq("name", "Default Organization")\
            .limit(1)\
            .execute()
        
        default_org_id = org_response.data[0]["id"] if org_response.data else None
        logger.info(f"📋 Organización por defecto: {default_org_id}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener organización por defecto: {e}")
        default_org_id = None
    
    # 2. Sincronizar cada usuario faltante
    synced_count = 0
    for user_id in MISSING_USER_IDS:
        logger.info(f"\n🔍 Procesando usuario: {user_id}")
        
        try:
            # Verificar si ya existe en tabla users
            check = db.client.table("users")\
                .select("id, email, status")\
                .eq("id", user_id)\
                .execute()
            
            if check.data:
                user = check.data[0]
                logger.info(f"✅ Usuario YA EXISTE en tabla users:")
                logger.info(f"   - Email: {user['email']}")
                logger.info(f"   - Status: {user['status']}")
                continue
            
            # Obtener datos de auth.users usando Admin API
            logger.info(f"📡 Obteniendo datos de auth.users...")
            auth_user = db.client.auth.admin.get_user_by_id(user_id)
            
            if not auth_user or not auth_user.user:
                logger.error(f"❌ Usuario NO existe en auth.users")
                continue
            
            user_data = auth_user.user
            logger.info(f"✅ Usuario encontrado en auth.users:")
            logger.info(f"   - Email: {user_data.email}")
            logger.info(f"   - Created: {user_data.created_at}")
            
            # Extraer metadata
            metadata = user_data.user_metadata or {}
            full_name = (
                metadata.get('full_name') or 
                metadata.get('name') or 
                user_data.email.split('@')[0].title()
            )
            username = (
                metadata.get('username') or 
                user_data.email.split('@')[0]
            )
            avatar_url = metadata.get('avatar_url')
            
            # Determinar status
            status = 'active' if user_data.email_confirmed_at else 'pending_verification'
            
            # Insertar en tabla users
            insert_data = {
                "id": user_id,
                "email": user_data.email,
                "full_name": full_name,
                "username": username,
                "avatar_url": avatar_url,
                "status": status,
                "organization_id": default_org_id,
                "role": "admin",
                "created_at": user_data.created_at
            }
            
            logger.info(f"💾 Insertando en tabla users...")
            result = db.client.table("users").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"✅ Usuario sincronizado exitosamente:")
                logger.info(f"   - Full Name: {full_name}")
                logger.info(f"   - Username: {username}")
                logger.info(f"   - Status: {status}")
                logger.info(f"   - Organization: {default_org_id}")
                synced_count += 1
            else:
                logger.error(f"❌ Error al insertar usuario")
                
        except Exception as e:
            logger.error(f"❌ Error procesando usuario {user_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # 3. Resumen final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMEN DE SINCRONIZACIÓN")
    logger.info("=" * 80)
    logger.info(f"✅ Usuarios sincronizados: {synced_count}/{len(MISSING_USER_IDS)}")
    
    # 4. Verificar usuarios en tabla users
    logger.info("\n🔍 Verificación final:")
    for user_id in MISSING_USER_IDS:
        try:
            check = db.client.table("users")\
                .select("id, email, full_name, status")\
                .eq("id", user_id)\
                .execute()
            
            if check.data:
                user = check.data[0]
                logger.info(f"✅ {user_id}")
                logger.info(f"   Email: {user['email']}, Status: {user['status']}")
            else:
                logger.error(f"❌ {user_id} - AÚN NO EXISTE")
        except Exception as e:
            logger.error(f"❌ Error verificando {user_id}: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("🎯 PRÓXIMOS PASOS:")
    logger.info("=" * 80)
    logger.info("1. Si sincronización exitosa → Reiniciar PM2: pm2 restart all")
    logger.info("2. Si usuarios aún no existen → Verificar que existan en auth.users")
    logger.info("3. Probar login desde frontend")
    logger.info("=" * 80)

if __name__ == "__main__":
    try:
        sync_users()
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
