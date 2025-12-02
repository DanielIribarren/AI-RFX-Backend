"""
🌥️ Cloudinary Service - Servicio minimalista para upload de logos
KISS: Solo hace lo necesario - subir logos y retornar URLs públicas
"""
import os
import logging
from typing import Optional

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
        
        # Configuración desde variables de entorno
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'dffys3mxv'),
            api_key=os.getenv('CLOUDINARY_API_KEY', '287712473884852'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET')
        )
        
        _cloudinary_configured = True
        logger.info("✅ Cloudinary configured successfully")
        
    except ImportError:
        logger.error("❌ Cloudinary not installed. Run: pip install cloudinary")
        raise ImportError("Cloudinary library not installed")
    except Exception as e:
        logger.error(f"❌ Error configuring Cloudinary: {e}")
        raise


def upload_logo(user_id: str, logo_file) -> str:
    """
    Sube logo a Cloudinary y retorna URL pública
    
    Args:
        user_id: ID del usuario (para organizar en folders)
        logo_file: Archivo del logo (FileStorage o file path)
        
    Returns:
        str: URL pública HTTPS del logo en Cloudinary
        
    Example:
        url = upload_logo("user-123", logo_file)
        # Returns: https://res.cloudinary.com/dffys3mxv/image/upload/v123/logos/user-123/logo.png
    """
    _configure_cloudinary()
    
    try:
        import cloudinary.uploader
        
        logger.info(f"☁️ Uploading logo to Cloudinary for user: {user_id}")
        
        # Upload a Cloudinary con configuración optimizada
        result = cloudinary.uploader.upload(
            logo_file,
            folder=f"logos/{user_id}",      # Organizar por usuario
            public_id="logo",                # Nombre fijo (sobrescribe si existe)
            overwrite=True,                  # Reemplazar logo anterior
            resource_type="image",           # Tipo de recurso
            invalidate=True,                 # Invalidar cache del CDN
            transformation=[                 # Optimizaciones automáticas
                {'width': 500, 'crop': 'limit'},  # Max 500px ancho
                {'quality': 'auto'},              # Calidad automática
                {'fetch_format': 'auto'}          # Formato automático (WebP si soporta)
            ]
        )
        
        # Extraer URL pública segura (HTTPS)
        public_url = result['secure_url']
        
        logger.info(f"✅ Logo uploaded successfully to Cloudinary")
        logger.info(f"📍 Public URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading logo to Cloudinary: {e}")
        raise Exception(f"Failed to upload logo to Cloudinary: {e}")


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


def get_logo_url(user_id: str) -> Optional[str]:
    """
    Obtiene URL pública del logo sin subirlo (útil para verificación)
    
    Args:
        user_id: ID del usuario
        
    Returns:
        str: URL pública del logo o None si no existe
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
        
        return url
        
    except Exception as e:
        logger.error(f"❌ Error getting logo URL: {e}")
        return None
