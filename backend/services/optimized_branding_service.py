"""
🎨 Optimized Branding Service - Gestión de branding con análisis cacheado
Upload de archivos + análisis asíncrono con IA + cache en BD
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)


class OptimizedUserBrandingService:
    """
    Servicio de branding personalizado por usuario con análisis de IA cacheado
    - Upload de logo y template por usuario
    - Análisis asíncrono con GPT-4 Vision
    - Cache de resultados en BD (JSONB)
    - Lectura rápida para generación
    """
    
    ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    ALLOWED_TEMPLATE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_TEMPLATE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.base_path = Path("backend/static/branding")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Lazy import de VisionAnalysisService
        self._vision_service = None
    
    @property
    def vision_service(self):
        """Lazy initialization de VisionAnalysisService"""
        if self._vision_service is None:
            from backend.services.vision_analysis_service import VisionAnalysisService
            self._vision_service = VisionAnalysisService()
        return self._vision_service
    
    async def upload_and_analyze(
        self, 
        company_id: str, 
        logo_file: Optional[FileStorage] = None, 
        template_file: Optional[FileStorage] = None,
        analyze_now: bool = True
    ) -> Dict:
        """
        Sube archivos y opcionalmente lanza análisis asíncrono
        
        Args:
            company_id: ID de la empresa
            logo_file: Archivo del logo (opcional)
            template_file: Archivo del template (opcional)
            analyze_now: Si True, lanza análisis inmediatamente
            
        Returns:
            Dict con URLs de archivos y estado de análisis
        """
        logger.info(f"📤 Uploading branding for company: {company_id}")
        
        if not logo_file and not template_file:
            raise ValueError("At least one file (logo or template) is required")
        
        # Crear directorio de empresa
        company_dir = self.base_path / company_id
        company_dir.mkdir(exist_ok=True)
        
        result = {"company_id": company_id}
        
        # 1. Procesar y guardar logo
        if logo_file and logo_file.filename:
            logo_info = await self._save_logo(company_id, logo_file, company_dir)
            result.update(logo_info)
        
        # 2. Procesar y guardar template
        if template_file and template_file.filename:
            template_info = await self._save_template(company_id, template_file, company_dir)
            result.update(template_info)
        
        # 3. Guardar en BD (sin análisis aún)
        await self._save_to_database(company_id, result, analyze_now)
        
        # 4. Lanzar análisis asíncrono si se requiere
        if analyze_now:
            # Crear tarea asíncrona que no bloquea
            asyncio.create_task(self._analyze_async(company_id, result))
            result["analysis_status"] = "analyzing"
            result["message"] = "Files uploaded successfully. Analysis in progress."
        else:
            result["analysis_status"] = "pending"
            result["message"] = "Files uploaded successfully. Analysis pending."
        
        logger.info(f"✅ Branding uploaded for company: {company_id}")
        return result
    
    async def _save_logo(
        self, 
        company_id: str, 
        logo_file: FileStorage, 
        company_dir: Path
    ) -> Dict:
        """Valida y guarda archivo de logo"""
        # Validar archivo
        self._validate_file(
            logo_file, 
            self.ALLOWED_LOGO_EXTENSIONS, 
            self.MAX_LOGO_SIZE,
            "logo"
        )
        
        # Determinar extensión
        ext = logo_file.filename.rsplit('.', 1)[1].lower()
        filename = f"logo.{ext}"
        file_path = company_dir / filename
        
        # Guardar archivo
        logo_file.save(str(file_path))
        
        logger.info(f"💾 Logo saved: {file_path}")
        
        return {
            "logo_filename": filename,
            "logo_path": str(file_path),
            "logo_url": f"/static/branding/{company_id}/{filename}"
        }
    
    async def _save_template(
        self, 
        company_id: str, 
        template_file: FileStorage, 
        company_dir: Path
    ) -> Dict:
        """Valida y guarda archivo de template"""
        # Validar archivo
        self._validate_file(
            template_file, 
            self.ALLOWED_TEMPLATE_EXTENSIONS, 
            self.MAX_TEMPLATE_SIZE,
            "template"
        )
        
        # Determinar extensión
        ext = template_file.filename.rsplit('.', 1)[1].lower()
        filename = f"template.{ext}"
        file_path = company_dir / filename
        
        # Guardar archivo
        template_file.save(str(file_path))
        
        logger.info(f"💾 Template saved: {file_path}")
        
        return {
            "template_filename": filename,
            "template_path": str(file_path),
            "template_url": f"/static/branding/{company_id}/{filename}"
        }
    
    def _validate_file(
        self, 
        file: FileStorage, 
        allowed_extensions: set, 
        max_size: int,
        file_type: str
    ):
        """Valida archivo antes de guardar"""
        # Verificar que tiene nombre
        if not file.filename:
            raise ValueError(f"{file_type} file has no filename")
        
        # Verificar extensión
        if '.' not in file.filename:
            raise ValueError(f"{file_type} file has no extension")
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(
                f"Invalid {file_type} extension: {ext}. "
                f"Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Verificar tamaño
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(
                f"{file_type} file too large: {size} bytes. "
                f"Maximum: {max_mb}MB"
            )
        
        logger.debug(f"✅ File validated: {file.filename} ({size} bytes)")
    
    async def _save_to_database(
        self, 
        company_id: str, 
        file_info: Dict,
        analyze_now: bool
    ):
        """Guarda información en base de datos"""
        from backend.core.database import get_database_client
        
        db = get_database_client()
        
        # Preparar valores
        logo_filename = file_info.get("logo_filename")
        logo_path = file_info.get("logo_path")
        logo_url = file_info.get("logo_url")
        
        template_filename = file_info.get("template_filename")
        template_path = file_info.get("template_path")
        template_url = file_info.get("template_url")
        
        analysis_status = 'analyzing' if analyze_now else 'pending'
        
        # Usar UPSERT para actualizar si existe
        query = """
            INSERT INTO company_branding_assets 
                (company_id, logo_filename, logo_path, logo_url, logo_uploaded_at,
                 template_filename, template_path, template_url, template_uploaded_at,
                 analysis_status, analysis_started_at, is_active)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, NOW(), %s, %s, true)
            ON CONFLICT (company_id) 
            DO UPDATE SET 
                logo_filename = COALESCE(EXCLUDED.logo_filename, company_branding_assets.logo_filename),
                logo_path = COALESCE(EXCLUDED.logo_path, company_branding_assets.logo_path),
                logo_url = COALESCE(EXCLUDED.logo_url, company_branding_assets.logo_url),
                logo_uploaded_at = CASE WHEN EXCLUDED.logo_filename IS NOT NULL THEN NOW() ELSE company_branding_assets.logo_uploaded_at END,
                template_filename = COALESCE(EXCLUDED.template_filename, company_branding_assets.template_filename),
                template_path = COALESCE(EXCLUDED.template_path, company_branding_assets.template_path),
                template_url = COALESCE(EXCLUDED.template_url, company_branding_assets.template_url),
                template_uploaded_at = CASE WHEN EXCLUDED.template_filename IS NOT NULL THEN NOW() ELSE company_branding_assets.template_uploaded_at END,
                analysis_status = EXCLUDED.analysis_status,
                analysis_started_at = EXCLUDED.analysis_started_at,
                updated_at = NOW()
            RETURNING id
        """
        
        result = db.execute(
            query,
            (
                company_id,
                logo_filename, logo_path, logo_url,
                template_filename, template_path, template_url,
                analysis_status,
                datetime.now() if analyze_now else None
            )
        )
        
        logger.info(f"💾 Branding info saved to database for company: {company_id}")
    
    async def _analyze_async(self, company_id: str, file_info: Dict):
        """
        Análisis asíncrono (no bloquea la respuesta)
        Ejecuta análisis de IA y guarda resultados en BD
        """
        try:
            logger.info(f"🔍 Starting async analysis for company: {company_id}")
            
            logo_analysis = None
            template_analysis = None
            
            # Analizar logo si existe
            if file_info.get("logo_path"):
                try:
                    logo_analysis = await self.vision_service.analyze_logo(file_info["logo_path"])
                    logger.info(f"✅ Logo analysis completed for {company_id}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing logo: {e}")
            
            # Analizar template si existe
            if file_info.get("template_path"):
                try:
                    template_analysis = await self.vision_service.analyze_template(file_info["template_path"])
                    logger.info(f"✅ Template analysis completed for {company_id}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing template: {e}")
            
            # Guardar análisis en BD
            from backend.core.database import get_database_client
            from datetime import datetime
            
            db = get_database_client()
            
            query = """
                UPDATE company_branding_assets
                SET 
                    logo_analysis = COALESCE(%s, logo_analysis),
                    template_analysis = COALESCE(%s, template_analysis),
                    analysis_status = 'completed',
                    analysis_completed_at = NOW(),
                    updated_at = NOW()
                WHERE company_id = %s
            """
            
            db.execute(
                query,
                (
                    json.dumps(logo_analysis) if logo_analysis else None,
                    json.dumps(template_analysis) if template_analysis else None,
                    company_id
                )
            )
            
            logger.info(f"✅ Analysis completed and saved for company: {company_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in async analysis for {company_id}: {e}")
            
            # Marcar como fallido en BD
            try:
                from backend.core.database import get_database_client
                db = get_database_client()
                
                db.execute("""
                    UPDATE company_branding_assets
                    SET 
                        analysis_status = 'failed',
                        analysis_error = %s,
                        updated_at = NOW()
                    WHERE company_id = %s
                """, (str(e), company_id))
            except:
                pass
    
    def get_branding_with_analysis(self, company_id: str) -> Optional[Dict]:
        """
        Obtiene configuración de branding con análisis cacheado
        Lectura rápida desde BD - sin llamadas a IA
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            Dict con URLs y análisis cacheado, o None si no existe
        """
        from backend.core.database import get_database_client
        
        db = get_database_client()
        
        query = """
            SELECT 
                id,
                logo_url, 
                template_url,
                logo_analysis,
                template_analysis,
                analysis_status,
                analysis_error,
                created_at,
                updated_at
            FROM company_branding_assets
            WHERE company_id = %s AND is_active = true
        """
        
        result = db.query_one(query, (company_id,))
        
        if not result:
            return None
        
        # Parsear JSONB a dict
        if result.get('logo_analysis'):
            try:
                result['logo_analysis'] = json.loads(result['logo_analysis']) if isinstance(result['logo_analysis'], str) else result['logo_analysis']
            except:
                result['logo_analysis'] = {}
        
        if result.get('template_analysis'):
            try:
                result['template_analysis'] = json.loads(result['template_analysis']) if isinstance(result['template_analysis'], str) else result['template_analysis']
            except:
                result['template_analysis'] = {}
        
        logger.debug(f"📖 Retrieved branding for company: {company_id}, status: {result.get('analysis_status')}")
        return result
    
    def get_analysis_status(self, company_id: str) -> Optional[Dict]:
        """
        Obtiene solo el estado del análisis
        Útil para polling desde frontend
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            Dict con estado del análisis
        """
        from backend.core.database import get_database_client
        
        db = get_database_client()
        
        result = db.query_one("""
            SELECT 
                analysis_status,
                analysis_error,
                analysis_started_at,
                analysis_completed_at
            FROM company_branding_assets
            WHERE company_id = %s AND is_active = true
        """, (company_id,))
        
        return result
    
    async def reanalyze(self, company_id: str) -> Dict:
        """
        Re-analiza branding existente
        Útil si el usuario no está satisfecho o si mejoró el modelo
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            Dict con estado de re-análisis
        """
        logger.info(f"🔄 Re-analyzing branding for company: {company_id}")
        
        # Obtener info actual
        branding = self.get_branding_with_analysis(company_id)
        
        if not branding:
            raise ValueError(f"No branding found for company: {company_id}")
        
        # Marcar como analyzing
        from backend.core.database import get_database_client
        from datetime import datetime
        
        db = get_database_client()
        
        db.execute("""
            UPDATE company_branding_assets
            SET 
                analysis_status = 'analyzing',
                analysis_started_at = NOW(),
                analysis_error = NULL,
                updated_at = NOW()
            WHERE company_id = %s
        """, (company_id,))
        
        # Preparar info para análisis
        file_info = {
            "logo_path": branding.get("logo_path"),
            "template_path": branding.get("template_path")
        }
        
        # Lanzar análisis asíncrono
        asyncio.create_task(self._analyze_async(company_id, file_info))
        
        return {
            "company_id": company_id,
            "analysis_status": "analyzing",
            "message": "Re-analysis started"
        }
    
    def delete_branding(self, company_id: str) -> bool:
        """
        Desactiva branding de una empresa
        No elimina archivos físicos por seguridad
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            True si se desactivó correctamente
        """
        from backend.core.database import get_database_client
        
        db = get_database_client()
        
        db.execute("""
            UPDATE company_branding_assets
            SET 
                is_active = false,
                updated_at = NOW()
            WHERE company_id = %s
        """, (company_id,))
        
        logger.info(f"🗑️ Branding deactivated for company: {company_id}")
        return True
