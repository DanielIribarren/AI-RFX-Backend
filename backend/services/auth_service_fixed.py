"""
🔐 Authentication Service FIXED - Solución directa sin conflictos bcrypt/passlib
Implementación que evita completamente el problema de compatibilidad
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
import bcrypt  # Usar bcrypt directamente sin passlib

logger = logging.getLogger(__name__)

# ========================
# CONFIGURACIÓN
# ========================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tu-secret-key-super-segura-cambiar-en-produccion-rfx-system-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 2 horas por defecto

class AuthServiceFixed:
    """Servicio de autenticación con implementación DIRECTA de bcrypt (sin passlib)"""
    
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    # ========================
    # PASSWORD MANAGEMENT - DIRECT BCRYPT
    # ========================
    
    def hash_password(self, password: str) -> str:
        """
        Hash de contraseña usando bcrypt DIRECTAMENTE (sin passlib)
        ✅ SOLUCIÓN DEFINITIVA que evita conflictos de versiones
        """
        try:
            # Convertir a bytes y truncar si es necesario (límite de bcrypt)
            password_bytes = password.encode('utf-8')
            if len(password_bytes) > 72:
                logger.warning("Password truncated to 72 bytes for bcrypt compatibility")
                password_bytes = password_bytes[:72]
            
            # Usar bcrypt directamente (sin passlib)
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            # Retornar como string para almacenamiento en DB
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Error hashing password: {e}")
            raise Exception(f"Password hashing failed: {e}")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verificar contraseña usando bcrypt DIRECTAMENTE (sin passlib)
        ✅ SOLUCIÓN que evita conflictos de versiones
        """
        try:
            # Convertir inputs a bytes
            password_bytes = plain_password.encode('utf-8')
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
                
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verificar usando bcrypt directamente
            return bcrypt.checkpw(password_bytes, hashed_bytes)
            
        except Exception as e:
            logger.error(f"❌ Error verifying password: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validar fortaleza de contraseña - SIMPLIFICADO"""
        errors = []
        
        # ✅ Validaciones básicas y prácticas
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        
        if len(password) > 72:
            errors.append("Password must be less than 72 characters")
        
        # Warnings opcionales
        warnings = []
        if len(password) < 8:
            warnings.append("Consider using at least 8 characters for better security")
        
        if not any(c.isupper() for c in password):
            warnings.append("Consider adding an uppercase letter")
        
        if not any(c.isdigit() for c in password):
            warnings.append("Consider adding a number")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "strength": "basic" if len(password) < 8 else "good"
        }
    
    # ========================
    # JWT TOKEN MANAGEMENT
    # ========================
    
    def create_access_token(self, user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Crear JWT access token"""
        try:
            to_encode = user_data.copy()
            
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
            
            to_encode.update({"exp": expire, "iat": datetime.utcnow()})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ Error creating access token: {e}")
            raise
    
    def create_refresh_token(self, user_id: str) -> str:
        """Crear JWT refresh token (válido por más tiempo)"""
        try:
            refresh_data = {
                "sub": user_id,
                "type": "refresh",
                "exp": datetime.utcnow() + timedelta(days=30),  # 30 días
                "iat": datetime.utcnow()
            }
            
            encoded_jwt = jwt.encode(refresh_data, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ Error creating refresh token: {e}")
            raise
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decodificar y validar JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"❌ Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error decoding token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generar nuevo access token usando refresh token válido"""
        try:
            payload = self.decode_token(refresh_token)
            
            if not payload or payload.get("type") != "refresh":
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Crear nuevo access token
            new_token_data = {"sub": user_id}
            return self.create_access_token(new_token_data)
            
        except Exception as e:
            logger.error(f"❌ Error refreshing token: {e}")
            return None
    
    # ========================
    # EMAIL VALIDATION
    # ========================
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """Validar formato de email"""
        import re
        
        errors = []
        
        if not email:
            errors.append("Email is required")
        elif len(email) > 254:  # RFC limite
            errors.append("Email too long")
        elif not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
            errors.append("Invalid email format")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "normalized_email": email.lower().strip() if email else None
        }
    
    def validate_user_data(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Validar datos completos de usuario"""
        errors = []
        
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['is_valid']:
            errors.extend(email_validation['errors'])
        
        # Validar password
        password_validation = self.validate_password_strength(password)
        if not password_validation['is_valid']:
            errors.extend(password_validation['errors'])
        
        # Validar nombre
        if not full_name or len(full_name.strip()) < 2:
            errors.append("Full name must be at least 2 characters")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

# ========================
# SINGLETON INSTANCE
# ========================

# Instancia global del servicio FIXED
auth_service_fixed = AuthServiceFixed()

# Funciones de conveniencia
def hash_password_fixed(password: str) -> str:
    """Función de conveniencia para hash password (FIXED)"""
    return auth_service_fixed.hash_password(password)

def verify_password_fixed(plain_password: str, hashed_password: str) -> bool:
    """Función de conveniencia para verificar password (FIXED)"""
    return auth_service_fixed.verify_password(plain_password, hashed_password)

def create_access_token_fixed(user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Función de conveniencia para crear access token (FIXED)"""
    return auth_service_fixed.create_access_token(user_data, expires_delta)

def decode_token_fixed(token: str) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para decodificar token (FIXED)"""
    return auth_service_fixed.decode_token(token)

# ========================
# LOGGING
# ========================

logger.info("🔐 FIXED Authentication service initialized (direct bcrypt, no passlib conflicts)")
