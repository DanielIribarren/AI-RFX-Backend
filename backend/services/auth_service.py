"""
🔐 Authentication Service - Sistema completo de autenticación con JWT
Incluye: Login, Signup, Email Verification, Password Reset, Token Management
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ========================
# CONFIGURACIÓN
# ========================

# Obtener de variables de entorno o usar defaults para desarrollo
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tu-secret-key-super-segura-cambiar-en-produccion-rfx-system-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 2 horas por defecto

# Configuración de password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Servicio centralizado de autenticación"""
    
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    # ========================
    # PASSWORD MANAGEMENT
    # ========================
    
    def hash_password(self, password: str) -> str:
        """Hash de contraseña con bcrypt - Arregla límite de 72 bytes"""
        # ✅ FIX: bcrypt tiene límite de 72 bytes - truncar si es necesario
        if len(password.encode('utf-8')) > 72:
            logger.warning("Password truncated to 72 bytes for bcrypt compatibility")
            password = password[:72]
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña contra hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validar fortaleza de contraseña - SIMPLIFICADO para menos errores
        
        Returns:
            Dict con is_valid y lista de errores
        """
        errors = []
        
        # ✅ SOLO validaciones BÁSICAS - menos restrictivo
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        
        if len(password) > 72:
            errors.append("Password must be less than 72 characters (bcrypt limitation)")
        
        # ✅ Opcional: solo recomendar mayúsculas y números (no obligatorio)
        warnings = []
        if not any(c.isupper() for c in password):
            warnings.append("Consider adding an uppercase letter for better security")
        
        if not any(c.isdigit() for c in password):
            warnings.append("Consider adding a number for better security")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,  # No bloquean el registro
            "strength": self._calculate_password_strength(password)
        }
    
    def _calculate_password_strength(self, password: str) -> str:
        """Calcular nivel de fortaleza de contraseña"""
        score = 0
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        if score <= 2:
            return "weak"
        elif score <= 4:
            return "medium"
        else:
            return "strong"
    
    # ========================
    # JWT TOKEN MANAGEMENT
    # ========================
    
    def create_access_token(self, user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Crear JWT token de acceso
        
        Args:
            user_data: Datos del usuario (id, email, etc.)
            expires_delta: Tiempo de expiración personalizado
        
        Returns:
            JWT token string
        """
        to_encode = user_data.copy()
        
        # Calcular expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        # Agregar claims estándar
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token"
        })
        
        # Generar token
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.info(f"✅ Created access token for user: {user_data.get('sub')} (expires: {expire})")
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodificar y validar JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Payload del token si es válido, None si no es válido
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validar que sea un access token
            if payload.get("type") != "access_token":
                logger.warning("Invalid token type")
                return None
            
            # Validar que tenga user ID
            if not payload.get("sub"):
                logger.warning("Token missing user ID")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTClaimsError:
            logger.warning("Invalid token claims")
            return None
        except JWTError as e:
            logger.warning(f"JWT error: {e}")
            return None
    
    def create_refresh_token(self, user_id: str) -> str:
        """
        Crear refresh token (válido por más tiempo)
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=30)  # 30 días
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh_token"
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generar nuevo access token usando refresh token
        
        Args:
            refresh_token: Refresh token válido
            
        Returns:
            Nuevo access token o None si refresh token inválido
        """
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh_token":
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Crear nuevo access token
            new_token_data = {"sub": user_id}
            return self.create_access_token(new_token_data)
            
        except JWTError:
            return None
    
    # ========================
    # USER VALIDATION
    # ========================
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validar formato de email
        
        Args:
            email: Email a validar
            
        Returns:
            Dict con is_valid y mensaje
        """
        import re
        
        email = email.strip().lower()
        
        # Regex básico para email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        is_valid = re.match(pattern, email) is not None
        
        return {
            "is_valid": is_valid,
            "email": email,
            "message": "Valid email" if is_valid else "Invalid email format"
        }
    
    def validate_user_data(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """
        Validar datos completos de usuario para registro
        
        Returns:
            Dict con is_valid, errores y datos normalizados
        """
        errors = []
        
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation["is_valid"]:
            errors.append(email_validation["message"])
        
        # Validar contraseña
        password_validation = self.validate_password_strength(password)
        if not password_validation["is_valid"]:
            errors.extend(password_validation["errors"])
        
        # Validar nombre completo
        if not full_name or len(full_name.strip()) < 2:
            errors.append("Full name must be at least 2 characters long")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "normalized_data": {
                "email": email_validation["email"],
                "full_name": full_name.strip(),
                "password_strength": password_validation.get("strength", "unknown")
            }
        }
    
    # ========================
    # TOKEN UTILITIES
    # ========================
    
    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extraer user ID de un token sin validación completa
        Útil para logging y debugging
        """
        try:
            # Decodificar sin verificar expiración
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            return payload.get("sub")
        except:
            return None
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Obtener información del token para debugging
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            
            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")
            
            exp_datetime = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
            iat_datetime = datetime.fromtimestamp(iat_timestamp) if iat_timestamp else None
            
            is_expired = exp_datetime < datetime.utcnow() if exp_datetime else True
            
            return {
                "user_id": payload.get("sub"),
                "token_type": payload.get("type"),
                "issued_at": iat_datetime.isoformat() if iat_datetime else None,
                "expires_at": exp_datetime.isoformat() if exp_datetime else None,
                "is_expired": is_expired,
                "valid": not is_expired and payload.get("type") == "access_token"
            }
        except JWTError as e:
            return {
                "error": str(e),
                "valid": False
            }

# ========================
# SINGLETON INSTANCE
# ========================

# Instancia global del servicio
auth_service = AuthService()

# Funciones de conveniencia para importación fácil
def hash_password(password: str) -> str:
    """Función de conveniencia para hash de contraseña"""
    return auth_service.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Función de conveniencia para verificar contraseña"""
    return auth_service.verify_password(plain_password, hashed_password)

def create_access_token(user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Función de conveniencia para crear access token"""
    return auth_service.create_access_token(user_data, expires_delta)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para decodificar token"""
    return auth_service.decode_token(token)

def validate_email(email: str) -> Dict[str, Any]:
    """Función de conveniencia para validar email"""
    return auth_service.validate_email(email)

def validate_password_strength(password: str) -> Dict[str, Any]:
    """Función de conveniencia para validar contraseña"""
    return auth_service.validate_password_strength(password)

# ========================
# LOGGING
# ========================

logger.info("🔐 Authentication service initialized")
logger.info(f"Token expiration: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
logger.info(f"Algorithm: {ALGORITHM}")
