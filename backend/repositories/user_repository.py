"""
👥 User Repository - Gestión de datos de usuarios en la base de datos
Incluye: CRUD usuarios, verificación email, reset contraseña, branding
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
import json
from datetime import datetime

from backend.core.database import get_database_client
from backend.services.auth_service_fixed import auth_service_fixed

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository para gestión de usuarios en PostgreSQL/Supabase"""
    
    def __init__(self):
        self.db = get_database_client()
    
    # ========================
    # USER CRUD OPERATIONS
    # ========================
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: str, 
        company_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crear nuevo usuario con contraseña hasheada
        
        Args:
            email: Email del usuario (será normalizado a lowercase)
            password: Contraseña en texto plano (será hasheada)
            full_name: Nombre completo
            company_name: Nombre de la empresa (opcional)
            
        Returns:
            Dict con datos del usuario creado o None si falló
        """
        try:
            logger.info(f"Creating user: {email}")
            
            # Hash de la contraseña usando el servicio FIXED (sin conflictos bcrypt/passlib)
            password_hash = auth_service_fixed.hash_password(password)
            
            # Insertar usuario
            result = self.db.query_one("""
                INSERT INTO users (email, password_hash, full_name, company_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, full_name, company_name, status, 
                         email_verified, created_at, updated_at
            """, (email.lower(), password_hash, full_name.strip(), company_name))
            
            if result:
                logger.info(f"✅ User created successfully: {email} (ID: {result['id']})")
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creating user {email}: {e}")
            raise
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Obtener usuario por email
        
        Args:
            email: Email del usuario
            
        Returns:
            Dict con datos del usuario o None si no existe
        """
        try:
            result = self.db.query_one("""
                SELECT 
                    id, email, password_hash, full_name, company_name,
                    status, email_verified, email_verified_at,
                    phone, timezone, language, last_login_at,
                    created_at, updated_at
                FROM users 
                WHERE email = %s AND status != 'inactive'
            """, (email.lower(),))
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by email {email}: {e}")
            return None
    
    def get_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Obtener usuario por ID
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict con datos del usuario o None si no existe
        """
        try:
            result = self.db.query_one("""
                SELECT 
                    id, email, password_hash, full_name, company_name,
                    status, email_verified, email_verified_at,
                    phone, timezone, language, last_login_at,
                    created_at, updated_at
                FROM users 
                WHERE id = %s AND status != 'inactive'
            """, (str(user_id),))
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by ID {user_id}: {e}")
            return None
    
    def update_user(
        self, 
        user_id: UUID, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Actualizar datos del usuario
        
        Args:
            user_id: UUID del usuario
            updates: Diccionario con campos a actualizar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            # Campos permitidos para actualizar
            allowed_fields = {
                'full_name', 'company_name', 'phone', 'timezone', 'language'
            }
            
            # Filtrar solo campos permitidos
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                logger.warning(f"No valid fields to update for user {user_id}")
                return False
            
            # Construir query dinámicamente
            set_clauses = []
            values = []
            
            for field, value in filtered_updates.items():
                set_clauses.append(f"{field} = %s")
                values.append(value)
            
            # Agregar updated_at
            set_clauses.append("updated_at = NOW()")
            values.append(str(user_id))
            
            query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            
            self.db.execute(query, tuple(values))
            
            logger.info(f"✅ User updated: {user_id} - Fields: {list(filtered_updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating user {user_id}: {e}")
            return False
    
    def update_last_login(self, user_id: UUID) -> bool:
        """
        Actualizar timestamp de último login
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            self.db.execute("""
                UPDATE users 
                SET last_login_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (str(user_id),))
            
            logger.info(f"✅ Last login updated for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating last login for user {user_id}: {e}")
            return False
    
    def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Cambiar contraseña del usuario
        
        Args:
            user_id: UUID del usuario
            new_password: Nueva contraseña en texto plano
            
        Returns:
            True si se cambió correctamente
        """
        try:
            password_hash = hash_password(new_password)
            
            self.db.execute("""
                UPDATE users 
                SET password_hash = %s, updated_at = NOW()
                WHERE id = %s
            """, (password_hash, str(user_id)))
            
            logger.info(f"✅ Password changed for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error changing password for user {user_id}: {e}")
            return False
    
    # ========================
    # EMAIL VERIFICATION
    # ========================
    
    async def create_verification_token(self, user_id: UUID) -> Optional[str]:
        """
        Crear token de verificación de email
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Token de verificación o None si falló
        """
        try:
            result = self.db.query_one("""
                INSERT INTO email_verifications (user_id)
                VALUES (%s)
                RETURNING token
            """, (str(user_id),))
            
            if result:
                token = result['token']
                logger.info(f"✅ Verification token created for user: {user_id}")
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creating verification token for user {user_id}: {e}")
            return None
    
    async def verify_email(self, token: str) -> bool:
        """
        Verificar email usando token
        
        Args:
            token: Token de verificación
            
        Returns:
            True si se verificó correctamente
        """
        try:
            # Usar función de BD que maneja toda la lógica
            result = self.db.query_one("""
                SELECT verify_user_email(%s) as success
            """, (token,))
            
            success = result['success'] if result else False
            
            if success:
                logger.info(f"✅ Email verified successfully with token: {token[:8]}...")
            else:
                logger.warning(f"⚠️ Failed to verify email with token: {token[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error verifying email with token {token[:8]}...: {e}")
            return False
    
    # ========================
    # PASSWORD RESET
    # ========================
    
    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Crear token de reset de contraseña
        
        Args:
            email: Email del usuario
            
        Returns:
            Token de reset o None si usuario no existe
        """
        try:
            result = self.db.query_one("""
                SELECT create_password_reset(%s) as token
            """, (email.lower(),))
            
            token = result['token'] if result else None
            
            if token:
                logger.info(f"✅ Password reset token created for: {email}")
            else:
                logger.warning(f"⚠️ No user found for password reset: {email}")
            
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creating password reset token for {email}: {e}")
            return None
    
    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Resetear contraseña usando token
        
        Args:
            token: Token de reset
            new_password: Nueva contraseña en texto plano
            
        Returns:
            True si se reseteo correctamente
        """
        try:
            password_hash = hash_password(new_password)
            
            result = self.db.query_one("""
                SELECT reset_password_with_token(%s, %s) as success
            """, (token, password_hash))
            
            success = result['success'] if result else False
            
            if success:
                logger.info(f"✅ Password reset successfully with token: {token[:8]}...")
            else:
                logger.warning(f"⚠️ Failed to reset password with token: {token[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error resetting password with token {token[:8]}...: {e}")
            return False
    
    # ========================
    # USER BRANDING
    # ========================
    
    def get_user_branding(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Obtener configuración de branding del usuario
        Usa la tabla company_branding_assets con user_id (migrada en V3.0)
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict con configuración de branding o None si no existe
        """
        try:
            result = self.db.query_one("""
                SELECT * FROM get_user_branding(%s)
            """, (str(user_id),))
            
            if result:
                # Convertir JSONB a dict Python
                branding = dict(result)
                
                # Parsear campos JSONB
                if branding.get('logo_analysis'):
                    try:
                        branding['logo_analysis'] = json.loads(branding['logo_analysis']) if isinstance(branding['logo_analysis'], str) else branding['logo_analysis']
                    except:
                        branding['logo_analysis'] = {}
                
                if branding.get('template_analysis'):
                    try:
                        branding['template_analysis'] = json.loads(branding['template_analysis']) if isinstance(branding['template_analysis'], str) else branding['template_analysis']
                    except:
                        branding['template_analysis'] = {}
                
                return branding
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting branding for user {user_id}: {e}")
            return None
    
    def has_branding_configured(self, user_id: UUID) -> bool:
        """
        Verificar si usuario tiene branding completamente configurado
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            True si tiene branding configurado y analizado
        """
        try:
            result = self.db.query_one("""
                SELECT has_user_branding_configured(%s) as has_branding
            """, (str(user_id),))
            
            return result['has_branding'] if result else False
            
        except Exception as e:
            logger.error(f"❌ Error checking branding for user {user_id}: {e}")
            return False
    
    # ========================
    # USER STATISTICS
    # ========================
    
    def get_user_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Obtener estadísticas del usuario
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict con estadísticas del usuario
        """
        try:
            # RFX count
            rfx_result = self.db.query_one("""
                SELECT COUNT(*) as rfx_count
                FROM rfx
                WHERE user_id = %s
            """, (str(user_id),))
            
            # Documents generated count
            docs_result = self.db.query_one("""
                SELECT COUNT(*) as documents_count
                FROM generated_documents
                WHERE user_id = %s
            """, (str(user_id),))
            
            # Branding status
            has_branding = self.has_branding_configured(user_id)
            
            return {
                "rfx_count": rfx_result['rfx_count'] if rfx_result else 0,
                "documents_count": docs_result['documents_count'] if docs_result else 0,
                "has_branding": has_branding,
                "account_age_days": 0  # TODO: calcular desde created_at
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting stats for user {user_id}: {e}")
            return {
                "rfx_count": 0,
                "documents_count": 0,
                "has_branding": False,
                "account_age_days": 0
            }
    
    # ========================
    # ADMIN OPERATIONS
    # ========================
    
    def list_users(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Listar usuarios (para admin)
        
        Args:
            limit: Límite de usuarios a retornar
            offset: Offset para paginación
            
        Returns:
            Lista de usuarios
        """
        try:
            results = self.db.query_all("""
                SELECT 
                    id, email, full_name, company_name, status,
                    email_verified, last_login_at, created_at
                FROM users
                WHERE status != 'inactive'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            return [dict(result) for result in results] if results else []
            
        except Exception as e:
            logger.error(f"❌ Error listing users: {e}")
            return []
    
    def get_users_count(self) -> int:
        """
        Obtener total de usuarios activos
        
        Returns:
            Número total de usuarios
        """
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as total
                FROM users
                WHERE status != 'inactive'
            """)
            
            return result['total'] if result else 0
            
        except Exception as e:
            logger.error(f"❌ Error getting users count: {e}")
            return 0

# ========================
# SINGLETON INSTANCE
# ========================

# Instancia global del repositorio
user_repository = UserRepository()

logger.info("👥 User repository initialized")
