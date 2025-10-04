"""
🔐 Authentication API Endpoints - Sistema completo de autenticación
Incluye: Signup, Login, Logout, Refresh Token, Email Verification, Password Reset
"""
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
import logging
import asyncio
from datetime import timedelta

from backend.services.auth_service_fixed import auth_service_fixed as auth_service, decode_token_fixed as decode_token
from backend.repositories.user_repository import user_repository

logger = logging.getLogger(__name__)

# ========================
# FASTAPI APP SETUP
# ========================

auth_app = FastAPI(
    title="RFX Authentication API",
    description="Sistema de autenticación completo con JWT",
    version="1.0.0"
)

# CORS configuration
auth_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# ========================
# PYDANTIC MODELS
# ========================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v.strip()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: Optional[str]
    status: str
    email_verified: bool
    has_branding: bool
    last_login_at: Optional[str]
    created_at: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        validation = auth_service.validate_password_strength(v)
        if not validation['is_valid']:
            raise ValueError(f"Password requirements: {', '.join(validation['errors'])}")
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ========================
# DEPENDENCY: GET CURRENT USER
# ========================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency para obtener usuario actual del JWT token
    
    Raises:
        HTTPException: Si el token es inválido o usuario no existe
        
    Returns:
        Dict con datos del usuario actual
    """
    token = credentials.credentials
    
    # Decodificar token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener user_id del payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener usuario de la base de datos
    try:
        from uuid import UUID
        user = user_repository.get_by_id(UUID(user_id))
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user['status'] not in ['active', 'pending_verification']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ========================
# BACKGROUND TASKS
# ========================

async def send_verification_email(user_email: str, token: str):
    """
    Tarea en background para enviar email de verificación
    TODO: Implementar envío real de email
    """
    logger.info(f"📧 Would send verification email to {user_email}")
    logger.info(f"Verification link: https://rfxsystem.com/verify?token={token}")
    
    # TODO: Integrar con servicio de email (SendGrid, AWS SES, etc.)
    await asyncio.sleep(0.1)  # Simular envío

async def send_password_reset_email(user_email: str, token: str):
    """
    Tarea en background para enviar email de reset de contraseña
    TODO: Implementar envío real de email
    """
    logger.info(f"📧 Would send password reset email to {user_email}")
    logger.info(f"Reset link: https://rfxsystem.com/reset-password?token={token}")
    
    # TODO: Integrar con servicio de email
    await asyncio.sleep(0.1)  # Simular envío

# ========================
# AUTH ENDPOINTS
# ========================

@auth_app.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest,
    background_tasks: BackgroundTasks
):
    """
    Registrar nuevo usuario
    
    - Valida datos de entrada
    - Crea usuario con status 'pending_verification'
    - Genera token de verificación
    - Envía email de verificación en background
    - Retorna JWT token de acceso
    """
    try:
        # Validar datos
        validation = auth_service.validate_user_data(
            data.email, data.password, data.full_name
        )
        
        if not validation['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Validation failed",
                    "errors": validation['errors']
                }
            )
        
        # Verificar si usuario ya existe
        existing_user = user_repository.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Crear usuario
        user = await user_repository.create_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            company_name=data.company_name
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Generar token de verificación
        from uuid import UUID
        verification_token = await user_repository.create_verification_token(
            UUID(user['id'])
        )
        
        if verification_token:
            # Enviar email de verificación en background
            background_tasks.add_task(
                send_verification_email, 
                user['email'], 
                verification_token
            )
        
        # Crear JWT token
        token_data = {"sub": str(user['id'])}
        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(str(user['id']))
        
        logger.info(f"✅ User registered successfully: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.token_expire_minutes * 60,
            user={
                "id": str(user['id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "company_name": user.get('company_name'),
                "status": user['status'],
                "email_verified": user['email_verified']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@auth_app.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """
    Iniciar sesión
    
    - Valida credenciales
    - Actualiza last_login_at
    - Retorna JWT token de acceso
    """
    try:
        # Obtener usuario por email
        user = user_repository.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verificar contraseña
        if not auth_service.verify_password(data.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verificar que la cuenta no esté suspendida
        if user['status'] == 'suspended':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account suspended"
            )
        
        # Actualizar last login
        from uuid import UUID
        user_repository.update_last_login(UUID(user['id']))
        
        # Verificar si tiene branding configurado
        has_branding = user_repository.has_branding_configured(UUID(user['id']))
        
        # Crear JWT token
        token_data = {"sub": str(user['id'])}
        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(str(user['id']))
        
        logger.info(f"✅ User logged in successfully: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.token_expire_minutes * 60,
            user={
                "id": str(user['id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "company_name": user.get('company_name'),
                "status": user['status'],
                "email_verified": user['email_verified'],
                "has_branding": has_branding
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@auth_app.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """
    Obtener información del usuario actual
    """
    try:
        # Verificar si tiene branding configurado
        from uuid import UUID
        has_branding = user_repository.has_branding_configured(UUID(current_user['id']))
        
        return UserResponse(
            id=str(current_user['id']),
            email=current_user['email'],
            full_name=current_user['full_name'],
            company_name=current_user.get('company_name'),
            status=current_user['status'],
            email_verified=current_user['email_verified'],
            has_branding=has_branding,
            last_login_at=current_user['last_login_at'].isoformat() if current_user.get('last_login_at') else None,
            created_at=current_user['created_at'].isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@auth_app.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest):
    """
    Renovar access token usando refresh token
    """
    try:
        new_access_token = auth_service.refresh_access_token(data.refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Obtener user ID del refresh token para respuesta
        payload = decode_token(data.refresh_token)
        user_id = payload.get("sub") if payload else None
        
        user_info = {"id": user_id} if user_id else {}
        
        return TokenResponse(
            access_token=new_access_token,
            expires_in=auth_service.token_expire_minutes * 60,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ========================
# EMAIL VERIFICATION
# ========================

@auth_app.post("/verify-email")
async def verify_email(token: str):
    """
    Verificar email usando token enviado por email
    """
    try:
        success = await user_repository.verify_email(token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@auth_app.post("/resend-verification")
async def resend_verification_email(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Reenviar email de verificación
    """
    try:
        if current_user['email_verified']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Generar nuevo token
        from uuid import UUID
        verification_token = await user_repository.create_verification_token(
            UUID(current_user['id'])
        )
        
        if verification_token:
            background_tasks.add_task(
                send_verification_email,
                current_user['email'],
                verification_token
            )
        
        return {"message": "Verification email sent"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resending verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ========================
# PASSWORD RESET
# ========================

@auth_app.post("/forgot-password")
async def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks
):
    """
    Solicitar reset de contraseña
    """
    try:
        # Generar token de reset
        reset_token = await user_repository.create_password_reset_token(data.email)
        
        if reset_token:
            # Enviar email en background
            background_tasks.add_task(
                send_password_reset_email,
                data.email,
                reset_token
            )
        
        # Siempre retornar éxito para evitar enumeración de usuarios
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        logger.error(f"❌ Error in forgot password: {e}")
        # No revelar errores internos
        return {"message": "If the email exists, a reset link has been sent"}

@auth_app.post("/reset-password")
async def reset_password(data: PasswordResetConfirm):
    """
    Confirmar reset de contraseña con token
    """
    try:
        success = await user_repository.reset_password_with_token(
            data.token, 
            data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ========================
# HEALTH CHECK
# ========================

@auth_app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }

# ========================
# LOGGING
# ========================

logger.info("🔐 Authentication API endpoints initialized")
logger.info("Available endpoints: /signup, /login, /me, /refresh, /verify-email, /forgot-password, /reset-password")
