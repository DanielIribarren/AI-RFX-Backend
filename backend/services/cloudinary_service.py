"""
🌥️ Cloudinary Service - Servicio minimalista para upload de logos
KISS: Solo hace lo necesario - subir logos y retornar URLs públicas
"""
import os
import logging
import time
import requests
from typing import Optional

from backend.utils.retry_decorator import retry_on_failure

logger = logging.getLogger(__name__)

# Lazy import de cloudinary para no romper si no está instalado
_cloudinary_configured = False


def _configure_cloudinary():
    """Configura Cloudinary una sola vez (lazy initialization)"""
    global _cloudinary_configured
    
    if _cloudinary_configured:
        return
    
    try:
        import cloudinary

        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')

        missing = [
            key for key, value in [
                ("CLOUDINARY_CLOUD_NAME", cloud_name),
                ("CLOUDINARY_API_KEY", api_key),
                ("CLOUDINARY_API_SECRET", api_secret),
            ] if not value
        ]
        if missing:
            raise ValueError(
                f"Missing required Cloudinary env vars: {', '.join(missing)}"
            )
        
        # Configuración desde variables de entorno
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )
        
        _cloudinary_configured = True
        logger.info("✅ Cloudinary configured successfully")
        
    except ImportError:
        logger.error("❌ Cloudinary not installed. Run: pip install cloudinary")
        raise ImportError("Cloudinary library not installed")
    except Exception as e:
        logger.error(f"❌ Error configuring Cloudinary: {e}")
        raise


@retry_on_failure(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
def _upload_to_cloudinary(user_id: str, logo_file):
    """Helper function para upload con retry automático"""
    import cloudinary.uploader
    
    logger.info(f"☁️ Uploading logo to Cloudinary for user: {user_id}")
    
    # Upload a Cloudinary con configuración optimizada y timeout
    result = cloudinary.uploader.upload(
        logo_file,
        folder=f"logos/{user_id}",      # Organizar por usuario
        public_id="logo",                # Nombre fijo (sobrescribe si existe)
        overwrite=True,                  # Reemplazar logo anterior
        resource_type="image",           # Tipo de recurso
        invalidate=True,                 # Invalidar cache del CDN
        timeout=30,                      # Timeout de 30 segundos
        transformation=[                 # Optimizaciones automáticas
            {'width': 500, 'crop': 'limit'},  # Max 500px ancho
            {'quality': 'auto'},              # Calidad automática
            {'fetch_format': 'auto'}          # Formato automático (WebP si soporta)
        ]
    )
    
    # Extraer URL pública segura (HTTPS)
    public_url = result.get('secure_url')
    
    if not public_url:
        raise ValueError("Cloudinary did not return a secure_url")
    
    # Validar que la URL sea accesible
    if not _validate_cloudinary_url(public_url):
        raise ValueError(f"Cloudinary URL is not accessible: {public_url}")
    
    logger.info(f"✅ Logo uploaded successfully to Cloudinary")
    logger.info(f"📍 Public URL: {public_url}")
    logger.info(f"🔍 Cloudinary response: asset_id={result.get('asset_id')}, version={result.get('version')}")
    
    return public_url


def upload_logo(user_id: str, logo_file) -> str:
    """
    Sube logo a Cloudinary y retorna URL pública con retry automático
    
    Args:
        user_id: ID del usuario (para organizar en folders)
        logo_file: Archivo del logo (FileStorage o file path)
        
    Returns:
        str: URL pública HTTPS del logo en Cloudinary
        
    Example:
        url = upload_logo("user-123", logo_file)
        # Returns: https://res.cloudinary.com/<cloud-name>/image/upload/v123/logos/user-123/logo.png
    """
    _configure_cloudinary()
    return _upload_to_cloudinary(user_id, logo_file)


def delete_logo(user_id: str) -> bool:
    """
    Elimina logo de Cloudinary (opcional - para cleanup)
    
    Args:
        user_id: ID del usuario
        
    Returns:
        bool: True si se eliminó correctamente
    """
    _configure_cloudinary()
    
    try:
        import cloudinary.uploader
        
        public_id = f"logos/{user_id}/logo"
        
        logger.info(f"🗑️ Deleting logo from Cloudinary: {public_id}")
        
        result = cloudinary.uploader.destroy(public_id)
        
        if result.get('result') == 'ok':
            logger.info(f"✅ Logo deleted successfully from Cloudinary")
            return True
        else:
            logger.warning(f"⚠️ Logo not found in Cloudinary: {public_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error deleting logo from Cloudinary: {e}")
        return False


def get_logo_url(user_id: str, validate: bool = True) -> Optional[str]:
    """
    Obtiene URL pública del logo sin subirlo (útil para verificación)
    
    Args:
        user_id: ID del usuario
        validate: Si True, valida que la URL sea accesible
        
    Returns:
        str: URL pública del logo o None si no existe o no es accesible
    """
    _configure_cloudinary()
    
    try:
        import cloudinary
        
        # Construir URL pública del logo
        public_id = f"logos/{user_id}/logo"
        
        url = cloudinary.CloudinaryImage(public_id).build_url(
            secure=True,
            transformation=[
                {'width': 500, 'crop': 'limit'},
                {'quality': 'auto'},
                {'fetch_format': 'auto'}
            ]
        )
        
        logger.info(f"🔗 Generated Cloudinary URL for user {user_id}: {url}")
        
        # Validar que la URL sea accesible si se solicita
        if validate and not _validate_cloudinary_url(url):
            logger.warning(f"⚠️ Cloudinary URL exists but is not accessible: {url}")
            return None
        
        return url
        
    except Exception as e:
        logger.error(f"❌ Error getting logo URL: {e}")
        return None


def _validate_cloudinary_url(url: str, timeout: int = 10) -> bool:
    """
    Valida que una URL de Cloudinary sea accesible
    
    Args:
        url: URL de Cloudinary a validar
        timeout: Timeout en segundos para la validación
        
    Returns:
        bool: True si la URL es accesible, False en caso contrario
    """
    try:
        logger.debug(f"🔍 Validating Cloudinary URL: {url}")
        
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        if response.status_code == 200:
            logger.debug(f"✅ Cloudinary URL is accessible (status: {response.status_code})")
            return True
        else:
            logger.warning(f"⚠️ Cloudinary URL returned status {response.status_code}: {url}")
            return False
            
    except requests.Timeout:
        logger.error(f"⏱️ Timeout validating Cloudinary URL: {url}")
        return False
    except requests.RequestException as e:
        logger.error(f"❌ Error validating Cloudinary URL: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error validating Cloudinary URL: {e}")
        return False
