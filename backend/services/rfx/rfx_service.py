"""
🎯 RFX Service - Orquestador simple de procesamiento RFX
Coordina extracción de texto, análisis con AI y guardado en BD
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from backend.core.database import get_database_client
from backend.services.rfx.text_extractor import text_extractor
from backend.services.rfx.ai_extractor import ai_extractor
from backend.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class RFXService:
    """
    Servicio principal de procesamiento RFX.
    
    Flujo simple (AI-FIRST):
    1. Extraer texto de archivos → text_extractor
    2. Extraer datos estructurados → ai_extractor (GPT-4o hace TODO)
    3. Guardar en base de datos
    4. (Opcional) Ejecutar evaluaciones si feature flag activo
    
    Principio KISS: El servicio solo ORQUESTA, no hace trabajo pesado.
    """
    
    def __init__(self):
        self.db = get_database_client()
        logger.info("🎯 RFXService initialized")
    
    def process(self, files: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
        """
        Procesa archivos RFX y retorna datos estructurados.
        
        Args:
            files: Lista de archivos con 'content' (bytes) y 'filename' (str)
            user_id: ID del usuario que procesa el RFX
            
        Returns:
            Dict con RFX procesado y productos
            
        Raises:
            Exception: Si el procesamiento falla
        """
        logger.info(f"📦 Processing {len(files)} file(s) for user {user_id}")
        start_time = datetime.now()
        
        try:
            # PASO 1: Extraer texto de archivos
            logger.info("📄 Step 1: Extracting text from files")
            text = text_extractor.extract_from_files(files)
            
            if not text or len(text.strip()) < 10:
                raise ValueError("No text could be extracted from files")
            
            logger.info(f"✅ Extracted {len(text)} characters")
            
            # PASO 2: Extraer datos estructurados con AI
            logger.info("🤖 Step 2: Extracting structured data with AI")
            extracted_data = ai_extractor.extract(text)
            
            # PASO 3: Guardar en base de datos
            logger.info("💾 Step 3: Saving to database")
            rfx_result = self._save_to_database(extracted_data, user_id)
            
            # PASO 4 (Opcional): Ejecutar evaluaciones
            if FeatureFlags.evals_enabled():
                logger.info("🔍 Step 4: Running evaluations (feature flag enabled)")
                rfx_result = self._run_evaluations(rfx_result)
            
            # Calcular tiempo de procesamiento
            processing_time = (datetime.now() - start_time).total_seconds()
            rfx_result['processing_time_seconds'] = processing_time
            
            logger.info(f"✅ RFX processed successfully in {processing_time:.2f}s - ID: {rfx_result['id']}")
            
            return rfx_result
            
        except Exception as e:
            logger.error(f"❌ RFX processing failed: {e}")
            raise
    
    def _save_to_database(self, extracted_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Guarda RFX y productos en base de datos.
        
        Args:
            extracted_data: Datos extraídos por AI
            user_id: ID del usuario
            
        Returns:
            Dict con RFX guardado incluyendo productos
        """
        try:
            # Preparar datos del RFX principal
            rfx_data = {
                'user_id': user_id,
                'title': extracted_data.get('title', 'Sin título'),
                'description': extracted_data.get('description'),
                'rfx_type': extracted_data.get('rfx_type', 'rfq'),
                'priority': extracted_data.get('priority', 'medium'),
                'status': 'pending',
                
                # Información del solicitante
                'email': extracted_data.get('requester_info', {}).get('email'),
                'nombre_solicitante': extracted_data.get('requester_info', {}).get('name'),
                'telefono_solicitante': extracted_data.get('requester_info', {}).get('phone'),
                'cargo_solicitante': extracted_data.get('requester_info', {}).get('position'),
                
                # Información de la empresa
                'nombre_empresa': extracted_data.get('requester_info', {}).get('company_name'),
                'email_empresa': extracted_data.get('requester_info', {}).get('company_email'),
                'telefono_empresa': extracted_data.get('requester_info', {}).get('company_phone'),
                
                # Información de entrega
                'fecha': extracted_data.get('delivery_info', {}).get('delivery_date'),
                'hora_entrega': extracted_data.get('delivery_info', {}).get('delivery_time'),
                'lugar': extracted_data.get('delivery_info', {}).get('location'),
                
                # Metadata
                'extraction_confidence': extracted_data.get('extraction_confidence', 0.0),
                'detected_domain': extracted_data.get('detected_domain'),
                'special_requirements': extracted_data.get('special_requirements', [])
            }
            
            # Insertar RFX principal
            logger.info("💾 Inserting RFX into database")
            result = self.db.client.table('rfx_v2').insert(rfx_data).execute()
            
            if not result.data:
                raise Exception("Failed to insert RFX - no data returned")
            
            rfx_id = result.data[0]['id']
            logger.info(f"✅ RFX created with ID: {rfx_id}")
            
            # Insertar productos
            products = extracted_data.get('requested_products', [])
            if products:
                logger.info(f"💾 Inserting {len(products)} products")
                self._save_products(rfx_id, products)
            else:
                logger.warning("⚠️ No products to save")
            
            # Retornar RFX completo con productos
            return {
                'id': rfx_id,
                **rfx_data,
                'productos': products
            }
            
        except Exception as e:
            logger.error(f"❌ Database save error: {e}")
            raise
    
    def _save_products(self, rfx_id: str, products: List[Dict[str, Any]]) -> None:
        """
        Guarda productos en la tabla rfx_products.
        
        Args:
            rfx_id: ID del RFX
            products: Lista de productos extraídos
        """
        try:
            products_data = []
            
            for product in products:
                product_data = {
                    'rfx_id': rfx_id,
                    'nombre': product.get('product_name'),
                    'cantidad': product.get('quantity', 0),
                    'unidad': product.get('unit', 'unidades'),
                    'categoria': product.get('category'),
                    'descripcion': product.get('description'),
                    'costo_unitario': product.get('unit_cost', 0.0),
                    'notas': product.get('notes')
                }
                products_data.append(product_data)
            
            # Insertar todos los productos en batch
            if products_data:
                self.db.client.table('rfx_products').insert(products_data).execute()
                logger.info(f"✅ Saved {len(products_data)} products")
            
        except Exception as e:
            logger.error(f"❌ Error saving products: {e}")
            raise
    
    def _run_evaluations(self, rfx_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta evaluaciones inteligentes si el feature flag está activo.
        
        Args:
            rfx_result: Resultado del procesamiento RFX
            
        Returns:
            RFX result con evaluaciones agregadas
        """
        try:
            # Import lazy para evitar circular imports
            from backend.services.evaluation_orchestrator import evaluate_rfx_intelligently
            
            logger.info(f"🔍 Running intelligent evaluation for RFX: {rfx_result['id']}")
            
            # Ejecutar evaluación
            eval_result = evaluate_rfx_intelligently(rfx_result)
            
            # Agregar resultados de evaluación al RFX
            rfx_result['evaluation'] = {
                'domain': eval_result.get('domain_detection', {}).get('primary_domain'),
                'confidence': eval_result.get('domain_detection', {}).get('confidence'),
                'score': eval_result.get('consolidated_score'),
                'quality': eval_result.get('execution_summary', {}).get('overall_quality'),
                'recommendations': eval_result.get('recommendations', [])[:5]  # Top 5
            }
            
            logger.info(f"✅ Evaluation complete - Score: {rfx_result['evaluation']['score']:.2f}")
            
            return rfx_result
            
        except Exception as e:
            logger.error(f"❌ Evaluation error: {e}")
            # No fallar el procesamiento si la evaluación falla
            rfx_result['evaluation'] = {'error': str(e)}
            return rfx_result
    
    def get_by_id(self, rfx_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un RFX por ID con sus productos.
        
        Args:
            rfx_id: ID del RFX
            
        Returns:
            Dict con RFX y productos o None si no existe
        """
        try:
            # Obtener RFX
            rfx_result = self.db.client.table('rfx_v2')\
                .select('*')\
                .eq('id', rfx_id)\
                .single()\
                .execute()
            
            if not rfx_result.data:
                return None
            
            rfx = rfx_result.data
            
            # Obtener productos
            products_result = self.db.client.table('rfx_products')\
                .select('*')\
                .eq('rfx_id', rfx_id)\
                .execute()
            
            rfx['productos'] = products_result.data or []
            
            return rfx
            
        except Exception as e:
            logger.error(f"❌ Error getting RFX {rfx_id}: {e}")
            return None


# Singleton para reutilización
rfx_service = RFXService()
