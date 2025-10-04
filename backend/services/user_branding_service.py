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
        
        # 3. Guardar en BD (sin análisis aún)
        await self._save_to_database(user_id, result, analyze_now)
        
        # 4. Lanzar análisis asíncrono si se requiere
        if analyze_now:
            # Crear tarea asíncrona que no bloquea
            asyncio.create_task(self._analyze_async(user_id, result))
            result["analysis_status"] = "analyzing"
            result["message"] = "Files uploaded successfully. Analysis in progress."
        else:
            result["analysis_status"] = "pending"
            result["message"] = "Files uploaded successfully. Analysis pending."
        
        logger.info(f"✅ Branding uploaded for user: {user_id}")
        return result
    
    async def _save_logo(
        self, 
        user_id: str, 
        logo_file: FileStorage, 
        user_dir: Path
    ) -> Dict:
        """Valida y guarda archivo de logo"""
        # Validar archivo
        self._validate_file(
            logo_file, 
            self.ALLOWED_LOGO_EXTENSIONS, 
            self.MAX_LOGO_SIZE,
            "Logo"
        )
        
        # Generar nombre seguro
        extension = logo_file.filename.rsplit('.', 1)[1].lower()
        filename = f"logo.{extension}"
        file_path = user_dir / filename
        
        # Guardar archivo
        logo_file.save(str(file_path))
        
        logger.info(f"💾 Logo saved: {file_path}")
        
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
        """Valida y guarda archivo de template"""
        # Validar archivo
        self._validate_file(
            template_file,
            self.ALLOWED_TEMPLATE_EXTENSIONS, 
            self.MAX_TEMPLATE_SIZE,
            "Template"
        )
        
        # Generar nombre seguro
        extension = template_file.filename.rsplit('.', 1)[1].lower()
        filename = f"template.{extension}"
        file_path = user_dir / filename
        
        # Guardar archivo
        template_file.save(str(file_path))
        
        logger.info(f"💾 Template saved: {file_path}")
        
        return {
            "template_filename": filename,
            "template_path": str(file_path),
            "template_url": f"/static/branding/{user_id}/{filename}"
        }
    
    def _validate_file(
        self, 
        file: FileStorage, 
        allowed_extensions: set, 
        max_size: int, 
        file_type: str
    ):
        """Valida extensión y tamaño de archivo"""
        if not file or not file.filename:
            raise ValueError(f"{file_type} file is required")
        
        # Validar extensión
        if '.' not in file.filename:
            raise ValueError(f"{file_type} file must have an extension")
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            raise ValueError(
                f"{file_type} must be one of: {', '.join(allowed_extensions)}"
            )
        
        # Validar tamaño (seek to end, get position, seek back to start)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Seek back to start
        
        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f"{file_type} file size exceeds {max_mb:.1f}MB limit")
    
    async def _save_to_database(
        self, 
        user_id: str, 
        file_info: Dict,
        analyze_now: bool
    ):
        """Guarda información de archivos en base de datos usando UPSERT"""
        # Extraer información de archivos
        logo_filename = file_info.get("logo_filename")
        logo_path = file_info.get("logo_path")
        logo_url = file_info.get("logo_url")
        
        template_filename = file_info.get("template_filename")
        template_path = file_info.get("template_path")
        template_url = file_info.get("template_url")
        
        analysis_status = "analyzing" if analyze_now else "pending"
        
        # Usar UPSERT para actualizar si existe
        # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
        query = """
            INSERT INTO company_branding_assets 
                (user_id, logo_filename, logo_path, logo_url, logo_uploaded_at,
                 template_filename, template_path, template_url, template_uploaded_at,
                 analysis_status, analysis_started_at, is_active)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, NOW(), %s, %s, true)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                logo_filename = COALESCE(EXCLUDED.logo_filename, company_branding_assets.logo_filename),
                logo_path = COALESCE(EXCLUDED.logo_path, company_branding_assets.logo_path),
                logo_url = COALESCE(EXCLUDED.logo_url, company_branding_assets.logo_url),
                logo_uploaded_at = CASE 
                    WHEN EXCLUDED.logo_filename IS NOT NULL THEN NOW()
                    ELSE company_branding_assets.logo_uploaded_at 
                END,
                template_filename = COALESCE(EXCLUDED.template_filename, company_branding_assets.template_filename),
                template_path = COALESCE(EXCLUDED.template_path, company_branding_assets.template_path),
                template_url = COALESCE(EXCLUDED.template_url, company_branding_assets.template_url),
                template_uploaded_at = CASE 
                    WHEN EXCLUDED.template_filename IS NOT NULL THEN NOW()
                    ELSE company_branding_assets.template_uploaded_at 
                END,
                analysis_status = EXCLUDED.analysis_status,
                analysis_started_at = EXCLUDED.analysis_started_at,
                is_active = true,
                updated_at = NOW()
        """
        
        self.db.execute(
            query,
            (
                user_id,
                logo_filename, logo_path, logo_url,
                template_filename, template_path, template_url,
                analysis_status,
                "NOW()" if analyze_now else None
            )
        )
        
        logger.info(f"💾 Branding info saved to database for user: {user_id}")
    
    async def _analyze_async(self, user_id: str, file_info: Dict):
        """
        Análisis asíncrono (no bloquea la respuesta)
        Ejecuta análisis de IA y guarda resultados en BD
        """
        try:
            logger.info(f"🔍 Starting async analysis for user: {user_id}")
            
            logo_analysis = None
            template_analysis = None
            
            # Análisis de logo (si existe)
            if file_info.get("logo_path"):
                try:
                    logo_analysis = await self.vision_service.analyze_logo(file_info["logo_path"])
                    logger.info(f"✅ Logo analysis completed for {user_id}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing logo: {e}")
            
            # Análisis de template (si existe)
            if file_info.get("template_path"):
                try:
                    template_analysis = await self.vision_service.analyze_template(file_info["template_path"])
                    logger.info(f"✅ Template analysis completed for {user_id}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing template: {e}")
            
            # Guardar resultados en BD
            # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
            self.db.execute("""
                UPDATE company_branding_assets
                SET 
                    logo_analysis = COALESCE(%s, logo_analysis),
                    template_analysis = COALESCE(%s, template_analysis),
                    analysis_status = 'completed',
                    analysis_completed_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = %s
            """, (
                json.dumps(logo_analysis) if logo_analysis else None,
                json.dumps(template_analysis) if template_analysis else None,
                user_id
            ))
            
            logger.info(f"✅ Analysis completed and saved for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in async analysis for {user_id}: {e}")
            
            # Marcar como fallido en BD
            try:
                self.db.execute("""
                    UPDATE company_branding_assets
                    SET 
                        analysis_status = 'failed',
                        analysis_error = %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                """, (str(e), user_id))
            except:
                pass
    
    # ========================
    # LECTURA Y CONSULTAS
    # ========================
    
    def get_branding_with_analysis(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene configuración de branding con análisis cacheado
        Lectura rápida desde BD - sin llamadas a IA
        
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
        
        # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
        query = """
            SELECT 
                user_id,
                logo_filename, logo_path, logo_url, logo_uploaded_at,
                template_filename, template_path, template_url, template_uploaded_at,
                logo_analysis, template_analysis,
                analysis_status, analysis_error,
                analysis_started_at, analysis_completed_at,
                is_active,
                created_at,
                updated_at
            FROM company_branding_assets
            WHERE user_id = %s AND is_active = true
        """
        
        result = self.db.query_one(query, (user_id,))
        
        if not result:
            return None
        
        # Convertir a dict y parsear JSONB
        result = dict(result)
        
        # Parsear JSON fields
        try:
            result['logo_analysis'] = json.loads(result['logo_analysis']) if result['logo_analysis'] else {}
        except:
            result['logo_analysis'] = {}
        
        try:
            result['template_analysis'] = json.loads(result['template_analysis']) if result['template_analysis'] else {}
        except:
            result['template_analysis'] = {}
        
        logger.debug(f"📖 Retrieved branding for user: {user_id}, status: {result.get('analysis_status')}")
        return result
    
    def get_analysis_status(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene solo el estado del análisis
        Útil para polling desde frontend
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con estado del análisis o None si no existe
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            return None
        
        # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
        query = """
            SELECT 
                analysis_status,
                analysis_error,
                analysis_started_at,
                analysis_completed_at
            FROM company_branding_assets
            WHERE user_id = %s AND is_active = true
        """
        
        result = self.db.query_one(query, (user_id,))
        return dict(result) if result else None
    
    async def reanalyze(self, user_id: str) -> Dict:
        """
        Re-ejecuta el análisis de branding existente
        Útil si el usuario no está satisfecho con el resultado
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con estado de la nueva solicitud de análisis
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            raise ValueError(f"Invalid user_id format: {user_id}")
        
        # Obtener configuración actual
        current_config = self.get_branding_with_analysis(user_id)
        
        if not current_config:
            raise ValueError(f"No branding configuration found for user: {user_id}")
        
        # Marcar como analyzing en BD
        # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
        self.db.execute("""
            UPDATE company_branding_assets
            SET 
                analysis_status = 'analyzing',
                analysis_error = NULL,
                analysis_started_at = NOW(),
                analysis_completed_at = NULL,
                updated_at = NOW()
            WHERE user_id = %s
        """, (user_id,))
        
        # Lanzar análisis asíncrono
        asyncio.create_task(self._analyze_async(user_id, current_config))
        
        logger.info(f"🔄 Re-analysis started for user: {user_id}")
        
        return {
            "user_id": user_id,
            "analysis_status": "analyzing",
            "message": "Re-analysis started successfully"
        }
    
    def delete_branding(self, user_id: str) -> bool:
        """
        Elimina configuración de branding (marca como inactiva)
        
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
            # NOTA: Usa company_branding_assets con user_id (migrado en V3.0 MVP)
            self.db.execute("""
                UPDATE company_branding_assets
                SET 
                    is_active = false,
                    updated_at = NOW()
                WHERE user_id = %s
            """, (user_id,))
            
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
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si tiene branding configurado y analizado
        """
        try:
            UUID(user_id)  # Validar formato
        except ValueError:
            return False
        
        result = self.db.query_one("""
            SELECT has_user_branding_configured(%s) as has_branding
        """, (user_id,))
        
        return result['has_branding'] if result else False
    
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
