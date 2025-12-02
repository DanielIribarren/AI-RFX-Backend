"""
🎨 User Branding Service V3.0 - Gestión de branding personalizado por usuario
Funcionalidades:
- Upload de logo y template por USUARIO (no por company)
- Análisis asíncrono con IA (GPT-4 Vision) 
- Cache de resultados en base de datos
- Lectura rápida para generación de propuestas

Cambios V3.0:
- Branding asociado a user_id en lugar de company_id
- Integración con sistema de autenticación JWT
- Nuevas validaciones de permisos por usuario
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from uuid import UUID
import logging

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

class UserBrandingService:
    """
    Servicio de branding personalizado por usuario con análisis de IA cacheado
    """
    
    # Configuración de archivos permitidos
    ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    ALLOWED_TEMPLATE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_TEMPLATE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.base_path = Path("backend/static/branding")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.db = get_database_client()
        
        # Lazy import de VisionAnalysisService
        self._vision_service = None
    
    @property
    def vision_service(self):
        """Lazy initialization de VisionAnalysisService"""
        if self._vision_service is None:
            from backend.services.vision_analysis_service import VisionAnalysisService
            self._vision_service = VisionAnalysisService()
        return self._vision_service
    
    # ========================
    # UPLOAD Y ANÁLISIS PRINCIPAL
    # ========================
    
    async def upload_and_analyze(
        self, 
        user_id: str, 
        logo_file: Optional[FileStorage] = None, 
        template_file: Optional[FileStorage] = None,
        analyze_now: bool = True
    ) -> Dict:
        """
        Sube archivos de branding para un usuario y opcionalmente lanza análisis asíncrono
        
        Args:
            user_id: ID del usuario (UUID string)
            logo_file: Archivo del logo (opcional)
            template_file: Archivo del template (opcional)
            analyze_now: Si True, lanza análisis inmediatamente
            
        Returns:
            Dict con URLs de archivos y estado de análisis
        """
        logger.info(f"📤 Uploading branding for user: {user_id}")
        
        if not logo_file and not template_file:
            raise ValueError("At least one file (logo or template) is required")
        
        # Validar que user_id sea UUID válido
        try:
            UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id format: {user_id}")
        
        # Crear directorio de usuario
        user_dir = self.base_path / user_id
        user_dir.mkdir(exist_ok=True)
        
        result = {"user_id": user_id}
        
        # 1. Procesar y guardar logo
        if logo_file and logo_file.filename:
            logo_info = await self._save_logo(user_id, logo_file, user_dir)
            result.update(logo_info)
        
        # 2. Procesar y guardar template
        if template_file and template_file.filename:
            template_info = await self._save_template(user_id, template_file, user_dir)
            result.update(template_info)
        
        # 3. Guardar archivos en BD
        await self._save_in_database(user_id, result, analyze_now)
        
        # 4. Llamar a analyze_template que genera HTML y guarda en BD
        if analyze_now and result.get("template_path"):
            asyncio.create_task(
                self.vision_service.analyze_template(
                    result["template_path"],
                    user_id
                )
            )
            result["analysis_status"] = "analyzing"
            result["message"] = "Files uploaded. Analysis in progress."
        else:
            result["analysis_status"] = "pending"
            result["message"] = "Files uploaded successfully."
        
        logger.info(f"✅ Branding uploaded for user: {user_id}")
        return result
    
    async def update_branding(
        self,
        user_id: str,
        logo_file: Optional[FileStorage] = None,
        template_file: Optional[FileStorage] = None,
        reanalyze: bool = False
    ) -> Dict:
        """
        Actualiza branding existente
        
        Args:
            user_id: ID del usuario
            logo_file: Nuevo archivo de logo (opcional)
            template_file: Nuevo archivo de template (opcional)
            reanalyze: Si debe re-analizar el template
            
        Returns:
            Dict con resultado de actualización
        """
        logger.info(f"🔄 Updating branding for user: {user_id}")
        
        # Verificar que existe branding
        existing = self.get_branding(user_id)
        if not existing or not existing.get('user_id'):
            raise ValueError(f"No branding found for user: {user_id}")
        
        # Crear directorio si no existe
        user_dir = Path("backend/static/branding") / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        result = {}
        
        # Actualizar logo si se proporciona
        if logo_file:
            logo_data = await self._save_logo(user_id, logo_file, user_dir)
            result.update(logo_data)
        
        # Actualizar template si se proporciona
        if template_file:
            template_data = await self._save_template(user_id, template_file, user_dir)
            result.update(template_data)
        
        # Actualizar en BD
        await self._update_in_database(user_id, result)
        
        # Re-analizar si se solicita y hay template
        if reanalyze and (template_file or existing.get('template_path')):
            template_path = result.get('template_path') or existing.get('template_path')
            if template_path:
                asyncio.create_task(
                    self.vision_service.analyze_template(
                        template_path,
                        user_id
                    )
                )
                result["analysis_status"] = "analyzing"
                result["message"] = "Branding updated. Re-analysis in progress."
            else:
                result["analysis_status"] = "pending"
                result["message"] = "Branding updated successfully."
        else:
            result["analysis_status"] = existing.get('analysis_status', 'pending')
            result["message"] = "Branding updated successfully."
        
        logger.info(f"✅ Branding updated for user: {user_id}")
        return result
    
    async def _save_logo(
        self, 
        user_id: str, 
        logo_file: FileStorage, 
        user_dir: Path
    ) -> Dict:
        """
        Guarda archivo de logo en Cloudinary
        ✅ MIGRADO A CLOUDINARY: Ahora usa CDN público en lugar de filesystem local
        """
        try:
            from backend.services.cloudinary_service import upload_logo
            
            # Subir a Cloudinary y obtener URL pública
            cloudinary_url = upload_logo(user_id, logo_file)
            
            logger.info(f"☁️ Logo uploaded to Cloudinary: {cloudinary_url}")
            
            return {
                "logo_filename": "logo",
                "logo_path": cloudinary_url,      # URL pública de Cloudinary
                "logo_url": cloudinary_url        # URL pública de Cloudinary
            }
            
        except Exception as e:
            logger.error(f"❌ Error uploading logo to Cloudinary: {e}")
            logger.warning("⚠️ Falling back to local filesystem storage")
            
            # Fallback: Guardar localmente si Cloudinary falla
            extension = logo_file.filename.rsplit('.', 1)[1].lower()
            filename = f"logo.{extension}"
            file_path = user_dir / filename
            
            logo_file.save(str(file_path))
            
            logger.info(f"💾 Logo saved locally (fallback): {file_path}")
            
            return {
                "logo_filename": filename,
                "logo_path": str(file_path),
                "logo_url": f"/static/branding/{user_id}/{filename}"
            }
    
    async def _save_template(
        self, 
        user_id: str, 
        template_file: FileStorage, 
        user_dir: Path
    ) -> Dict:
        """Guarda archivo de template"""
        extension = template_file.filename.rsplit('.', 1)[1].lower()
        filename = f"template.{extension}"
        file_path = user_dir / filename
        
        template_file.save(str(file_path))
        
        logger.info(f"💾 Template saved: {file_path}")
        
        return {
            "template_filename": filename,
            "template_path": str(file_path),
            "template_url": f"/static/branding/{user_id}/{filename}"
        }
    
    async def _update_in_database(self, user_id: str, update_data: Dict):
        """Actualiza branding existente en BD usando Supabase client"""
        try:
            # Preparar datos para actualización
            db_update = {}
            
            if 'logo_filename' in update_data:
                db_update['logo_filename'] = update_data['logo_filename']
                db_update['logo_path'] = update_data['logo_path']
                db_update['logo_url'] = update_data['logo_url']
                db_update['logo_uploaded_at'] = datetime.now().isoformat()
            
            if 'template_filename' in update_data:
                db_update['template_filename'] = update_data['template_filename']
                db_update['template_path'] = update_data['template_path']
                db_update['template_url'] = update_data['template_url']
                db_update['template_uploaded_at'] = datetime.now().isoformat()
            
            db_update['updated_at'] = datetime.now().isoformat()
            
            # Usar Supabase client directamente (como guardas productos)
            result = self.db.client.table("company_branding_assets")\
                .update(db_update)\
                .eq("user_id", user_id)\
                .execute()
            
            logger.info(f"💾 Branding updated in database for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating branding in database: {e}")
            raise
    
    async def _save_in_database(
        self, 
        user_id: str, 
        file_info: Dict,
        analyze_now: bool
    ):
        """
        Guarda información de archivos en base de datos usando Supabase client
        ✅ MIGRADO A SUPABASE: Usa self.db.client (Supabase) para consistencia
        """
        from datetime import datetime
        
        # Extraer información de archivos
        logo_filename = file_info.get("logo_filename")
        logo_path = file_info.get("logo_path")
        logo_url = file_info.get("logo_url")
        
        template_filename = file_info.get("template_filename")
        template_path = file_info.get("template_path")
        template_url = file_info.get("template_url")
        
        analysis_status = "analyzing" if analyze_now else "pending"
        
        try:
            # 1. Verificar si ya existe registro para este usuario
            existing = self.db.client.table("company_branding_assets")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            
            # 2. Preparar datos para insert/update
            data = {
                "user_id": user_id,
                "is_active": True,
                "analysis_status": analysis_status
            }
            
            # Solo actualizar campos que se proporcionaron
            if logo_filename:
                data["logo_filename"] = logo_filename
                data["logo_path"] = logo_path
                data["logo_url"] = logo_url
                data["logo_uploaded_at"] = datetime.now().isoformat()
                logger.info(f"📝 Updating logo URL in BD: {logo_url}")
            
            if template_filename:
                data["template_filename"] = template_filename
                data["template_path"] = template_path
                data["template_url"] = template_url
                data["template_uploaded_at"] = datetime.now().isoformat()
            
            if analyze_now:
                data["analysis_started_at"] = datetime.now().isoformat()
            
            # 3. Insert o Update según si existe
            if existing.data:
                # UPDATE
                response = self.db.client.table("company_branding_assets")\
                    .update(data)\
                    .eq("user_id", user_id)\
                    .execute()
                logger.info(f"✅ Branding UPDATED in BD for user: {user_id}")
            else:
                # INSERT
                response = self.db.client.table("company_branding_assets")\
                    .insert(data)\
                    .execute()
                logger.info(f"✅ Branding INSERTED in BD for user: {user_id}")
            
            # 4. Verificar que se guardó correctamente
            if logo_url:
                verify = self.db.client.table("company_branding_assets")\
                    .select("logo_url")\
                    .eq("user_id", user_id)\
                    .execute()
                
                if verify.data and verify.data[0].get('logo_url') == logo_url:
                    logger.info(f"✅ Logo URL verified in BD: {logo_url}")
                else:
                    logger.error(f"❌ Logo URL verification FAILED - Expected: {logo_url}, Got: {verify.data[0].get('logo_url') if verify.data else 'None'}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to database: {e}")
            raise
    
    # ========================
    # LECTURA Y CONSULTAS
    # ========================
    
    def get_branding_with_analysis(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene configuración de branding con análisis cacheado
        Lectura rápida desde BD - sin llamadas a IA
        ✅ MIGRADO A SUPABASE: Usa self.db.client para consistencia
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con URLs y análisis cacheado, o None si no existe
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            logger.error(f"Invalid user_id format: {user_id}")
            return None
        
        try:
            # Usar Supabase client
            response = self.db.client.table("company_branding_assets")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            
            if not response.data:
                return None
            
            result = response.data[0]
            
            # Parsear JSON fields (Supabase ya los retorna como dict si son JSONB)
            if isinstance(result.get('logo_analysis'), str):
                try:
                    result['logo_analysis'] = json.loads(result['logo_analysis'])
                except:
                    result['logo_analysis'] = {}
            elif not result.get('logo_analysis'):
                result['logo_analysis'] = {}
            
            if isinstance(result.get('template_analysis'), str):
                try:
                    result['template_analysis'] = json.loads(result['template_analysis'])
                except:
                    result['template_analysis'] = {}
            elif not result.get('template_analysis'):
                result['template_analysis'] = {}
            
            logger.debug(f"📖 Retrieved branding for user: {user_id}, status: {result.get('analysis_status')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving branding: {e}")
            return None
    
    def get_analysis_status(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene solo el estado del análisis
        Útil para polling desde frontend
        ✅ MIGRADO A SUPABASE: Usa self.db.client para consistencia
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con estado del análisis o None si no existe
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            return None
        
        try:
            response = self.db.client.table("company_branding_assets")\
                .select("analysis_status, analysis_error, analysis_started_at")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"❌ Error getting analysis status: {e}")
            return None
    
    def delete_branding(self, user_id: str) -> bool:
        """
        Elimina configuración de branding (marca como inactiva)
        ✅ MIGRADO A SUPABASE: Usa self.db.client para consistencia
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            return False
        
        try:
            from datetime import datetime
            
            response = self.db.client.table("company_branding_assets")\
                .update({
                    "is_active": False,
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("user_id", user_id)\
                .execute()
            
            logger.info(f"🗑️ Branding deactivated for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting branding for user {user_id}: {e}")
            return False
    
    # ========================
    # UTILIDADES
    # ========================
    
    def has_branding_configured(self, user_id: str) -> bool:
        """
        Verificar si usuario tiene branding completamente configurado
        ✅ MIGRADO A SUPABASE: Usa self.db.client para consistencia
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si tiene branding configurado y analizado
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            return False
        
        try:
            response = self.db.client.table("company_branding_assets")\
                .select("logo_filename, template_filename, analysis_status")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            
            if not response.data:
                return False
            
            branding = response.data[0]
            # Tiene branding si tiene logo, template y análisis completado
            return bool(
                branding.get('logo_filename') and 
                branding.get('template_filename') and 
                branding.get('analysis_status') == 'completed'
            )
            
        except Exception as e:
            logger.error(f"❌ Error checking branding configured: {e}")
            return False
    
    def get_branding_summary(self, user_id: str) -> Dict:
        """
        Obtener resumen de configuración de branding
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con resumen de configuración
        """
        config = self.get_branding_with_analysis(user_id)
        
        if not config:
            return {
                "has_branding": False,
                "has_logo": False,
                "has_template": False,
                "analysis_status": None
            }
        
        return {
            "has_branding": True,
            "has_logo": bool(config.get('logo_url')),
            "has_template": bool(config.get('template_url')),
            "analysis_status": config.get('analysis_status'),
            "logo_url": config.get('logo_url'),
            "template_url": config.get('template_url'),
            "primary_color": config.get('logo_analysis', {}).get('primary_color'),
            "design_style": config.get('template_analysis', {}).get('design_style'),
            "last_updated": config.get('updated_at')
        }

# ========================
# SINGLETON INSTANCE
# ========================

# Instancia global del servicio
user_branding_service = UserBrandingService()

logger.info("🎨 User Branding Service V3.0 initialized")
