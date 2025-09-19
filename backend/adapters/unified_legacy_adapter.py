"""
🔄 Unified Legacy Adapter - Adaptador único para todos los formatos legacy
Consolida la funcionalidad de LegacyRFXAdapter + LegacyProposalAdapter
Mantiene compatibilidad 100% con frontend existente
"""
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UnifiedLegacyAdapter:
    """
    🎯 Adaptador único que maneja TODAS las conversiones de formato legacy
    Reemplaza LegacyRFXAdapter + LegacyProposalAdapter con lógica consolidada
    """
    
    def __init__(self):
        self.rfx_field_mapping = self._get_rfx_field_mapping()
        self.proposal_field_mapping = self._get_proposal_field_mapping()
        self._cache = {}  # Cache para conversiones frecuentes
        logger.info("🔄 Unified Legacy Adapter initialized")
    
    def convert_to_format(self, data: Dict[str, Any], target_format: str) -> Dict[str, Any]:
        """
        🎯 Método principal de conversión con auto-detección de formato
        
        Args:
            data: Datos a convertir (output de BudyAgent o datos unificados)
            target_format: Formato objetivo ('rfx', 'proposal', 'modern')
            
        Returns:
            Dict en formato específico requerido
        """
        try:
            logger.info(f"🔄 Converting data to {target_format} format")
            
            if target_format == 'rfx':
                return self._convert_to_rfx_format(data)
            elif target_format == 'proposal':
                return self._convert_to_proposal_format(data)
            elif target_format == 'modern':
                return data  # Pass through modern format
            else:
                raise ValueError(f"Unsupported target format: {target_format}")
                
        except Exception as e:
            logger.error(f"❌ Conversion failed for {target_format}: {e}")
            raise
    
    def _convert_to_rfx_format(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 Convierte Project/BudyAgent result → RFX legacy format
        Integra la lógica de LegacyRFXAdapter original con mejoras
        """
        try:
            logger.debug("🔄 Converting to RFX legacy format")
            
            # Detectar formato de origen
            source_format = self.detect_source_format(project_data)
            
            if source_format == 'budy_agent_analysis':
                # MOMENTO 1: BudyAgent analysis result
                return self._convert_budy_analysis_to_rfx(project_data)
            elif source_format == 'unified_project':
                # Unified Project model
                return self._convert_project_to_rfx(project_data)
            else:
                # Datos generales - mapeo directo
                return self._convert_generic_to_rfx(project_data)
                
        except Exception as e:
            logger.error(f"❌ Failed to convert to RFX format: {e}")
            raise
    
    def _convert_budy_analysis_to_rfx(self, budy_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte resultado de BudyAgent MOMENTO 1 → RFX legacy format"""
        extracted_data = budy_result.get('extracted_data', {})
        project_details = extracted_data.get('project_details', {})
        client_info = extracted_data.get('client_information', {})
        timeline = extracted_data.get('timeline', {})
        budget_financial = extracted_data.get('budget_financial', {})
        requirements = extracted_data.get('requirements', {})
        location_logistics = extracted_data.get('location_logistics', {})
        requested_products = extracted_data.get('requested_products', [])
        
        # Database IDs if available
        db_ids = budy_result.get('database_ids', {})
        
        return {
            # Identificación básica
            'id': budy_result.get('rfx_id', budy_result.get('project_id', 'UNKNOWN')),
            'status': 'completed',
            'title': project_details.get('title', 'Proyecto Sin Título'),
            'description': project_details.get('description', ''),
            'industry': project_details.get('industry_domain', 'general'),
            'type': project_details.get('rfx_type_detected', 'general'),
            'project_type': project_details.get('industry_domain', 'general'),
            
            # Información del cliente (formato legacy)
            'client_name': client_info.get('name', ''),
            'client_company': client_info.get('company', ''),
            'client_email': client_info.get('requester_email', ''),
            'client_profile': 'standard',
            
            # Fechas (formato legacy compatible)
            'start_date': self._extract_date(timeline, 'start_date'),
            'end_date': self._extract_date(timeline, 'end_date'),
            'deadline': self._extract_date(timeline, 'delivery_date'),
            'delivery_date': self._extract_date(timeline, 'delivery_date'),
            
            # Ubicación
            'location': location_logistics.get('primary_location', ''),
            'service_location': location_logistics.get('primary_location', ''),
            
            # Presupuesto
            'estimated_budget': budget_financial.get('estimated_budget', ''),
            'budget_range': budget_financial.get('budget_range', ''),
            'currency': budget_financial.get('currency', 'USD'),
            
            # Productos/servicios (formato legacy)
            'products': self._map_items_to_products(requested_products),
            
            # Información legacy de compañías y solicitantes
            'companies': self._map_company_info(client_info),
            'requesters': self._map_requester_info(client_info),
            
            # Métricas de calidad
            'overall_confidence': budy_result.get('quality_assessment', {}).get('confidence_level', 0.0),
            'products_confidence': budy_result.get('quality_assessment', {}).get('products_confidence', 0.0),
            'client_confidence': budy_result.get('quality_assessment', {}).get('client_confidence', 0.0),
            
            # Sugerencias y recomendaciones
            'suggestions': budy_result.get('inferred_information', {}).get('additional_considerations', []),
            'processing_notes': budy_result.get('inferred_information', {}).get('notes', ''),
            
            # Contenido original
            'extracted_content': budy_result.get('original_document_text', ''),
            
            # Datos de BD si están disponibles
            'project_id': db_ids.get('project_id', budy_result.get('project_id')),
            'organization_id': db_ids.get('organization_id'),
            'user_id': db_ids.get('user_id'),
            
            # Metadatos
            'processing_time': budy_result.get('metadata', {}).get('generation_time', 0),
            'model_used': budy_result.get('metadata', {}).get('model_used', 'unknown'),
            'complexity_score': extracted_data.get('complexity_score', 5)
        }
    
    def _convert_to_proposal_format(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        💰 Convierte Quote/BudyAgent result → Proposal legacy format
        Integra la lógica de LegacyProposalAdapter original con mejoras
        """
        try:
            logger.debug("💰 Converting to Proposal legacy format")
            
            # Detectar formato de origen
            source_format = self.detect_source_format(quote_data)
            
            if source_format == 'budy_agent_quote':
                # MOMENTO 3: BudyAgent quote result
                return self._convert_budy_quote_to_proposal(quote_data)
            elif source_format == 'unified_quote':
                # Unified Quote model
                return self._convert_quote_to_proposal(quote_data)
            else:
                # Datos generales - mapeo directo
                return self._convert_generic_to_proposal(quote_data)
                
        except Exception as e:
            logger.error(f"❌ Failed to convert to Proposal format: {e}")
            raise
    
    def _convert_budy_quote_to_proposal(self, budy_quote_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte resultado de BudyAgent MOMENTO 3 → Proposal legacy format"""
        quote = budy_quote_result.get('quote', {})
        quote_metadata = quote.get('quote_metadata', {})
        pricing_breakdown = quote.get('pricing_breakdown', {})
        quote_structure = quote.get('quote_structure', {})
        terms_conditions = quote.get('terms_and_conditions', {})
        html_content = quote.get('html_content', '')
        
        return {
            # Identificación básica
            'id': quote_metadata.get('quote_number', str(uuid.uuid4())),
            'quote_id': quote_metadata.get('quote_number', str(uuid.uuid4())),
            'proposal_id': quote_metadata.get('quote_number', str(uuid.uuid4())),  # Alias
            'project_id': budy_quote_result.get('project_id', 'UNKNOWN'),
            'rfx_id': budy_quote_result.get('project_id', 'UNKNOWN'),  # Legacy compatibility
            
            # Información del proyecto y cliente
            'project_title': quote_metadata.get('project_title', 'Propuesta Comercial'),
            'client_name': quote_metadata.get('client_name', ''),
            'company_name': quote_metadata.get('company_name', ''),
            'industry': quote_metadata.get('industry', 'general'),
            'complexity_level': quote_metadata.get('complexity_level', 'medium'),
            
            # Información financiera (estructura legacy)
            'subtotal': pricing_breakdown.get('subtotal', 0.0),
            'coordination_amount': pricing_breakdown.get('coordination_fee', 0.0),
            'coordination_percentage': pricing_breakdown.get('coordination_percentage', 0),
            'tax_amount': pricing_breakdown.get('tax', 0.0),
            'tax_percentage': pricing_breakdown.get('tax_percentage', 0),
            'discount_amount': pricing_breakdown.get('discount', 0.0),
            'total_amount': pricing_breakdown.get('total', quote_metadata.get('total_amount', 0.0)),
            'currency': quote_metadata.get('currency', 'USD'),
            
            # Estructura de secciones (formato legacy)
            'sections': quote_structure.get('sections', []),
            
            # Contenido generado
            'html_content': html_content,
            'generated_content': html_content,  # Alias legacy
            
            # Términos y condiciones
            'payment_terms': terms_conditions.get('payment_terms', ''),
            'delivery_terms': terms_conditions.get('delivery_terms', ''),
            'validity_days': terms_conditions.get('validity_days', 30),
            'valid_until': quote_metadata.get('valid_until'),
            
            # Estado y metadatos
            'status': 'GENERATED',
            'generation_method': 'budy_agent',
            'version': 1,
            'created_at': datetime.utcnow().isoformat(),
            
            # Recomendaciones y notas
            'recommendations': quote.get('recommendations', []),
            'notes': quote.get('notes', ''),
            
            # Metadatos de generación
            'generation_time': budy_quote_result.get('metadata', {}).get('generation_time', 0),
            'model_used': budy_quote_result.get('metadata', {}).get('model_used', 'unknown'),
            'tokens_used': budy_quote_result.get('metadata', {}).get('tokens_used', 0),
            
            # Datos de BD si están disponibles
            'quote_id_db': budy_quote_result.get('quote_id'),
            'project_id_db': budy_quote_result.get('project_id')
        }
    
    def _map_items_to_products(self, items: List[Dict]) -> List[Dict]:
        """Mapea project_items → legacy products format"""
        products = []
        for item in items:
            products.append({
                'name': item.get('product_name', item.get('name', '')),
                'quantity': item.get('quantity', 1),
                'unit': item.get('unit', 'unidades'),
                'specifications': item.get('specifications', item.get('description', '')),
                'category': item.get('category', 'general'),
                'estimated_unit_price': item.get('unit_price', 0.0),
                'estimated_total_price': item.get('total_price', item.get('quantity', 1) * item.get('unit_price', 0.0))
            })
        return products
    
    def _map_company_info(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """Mapea información del cliente → legacy companies format"""
        return {
            'name': client_info.get('company', ''),
            'email': client_info.get('company_email'),
            'phone': client_info.get('company_phone'),
            'address': client_info.get('company_address'),
            'industry': client_info.get('industry', 'general'),
            'notes': ''
        }
    
    def _map_requester_info(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """Mapea información del solicitante → legacy requesters format"""
        return {
            'name': client_info.get('name', ''),
            'email': client_info.get('requester_email', ''),
            'phone': client_info.get('requester_phone', ''),
            'position': client_info.get('requester_position', ''),
            'notes': ''
        }
    
    def _extract_date(self, timeline: Dict[str, Any], date_key: str) -> Optional[str]:
        """Extrae y formatea fechas para compatibilidad legacy"""
        date_value = timeline.get(date_key)
        if date_value:
            try:
                # Si es string, intentar parsear
                if isinstance(date_value, str):
                    return date_value
                # Si es datetime, formatear
                elif hasattr(date_value, 'isoformat'):
                    return date_value.isoformat()
                else:
                    return str(date_value)
            except:
                return None
        return None
    
    def detect_source_format(self, data: Dict[str, Any]) -> str:
        """
        🔍 Auto-detecta el formato de origen de los datos
        
        Returns:
            str: Tipo de formato detectado
        """
        if 'extracted_data' in data and 'quality_assessment' in data:
            return 'budy_agent_analysis'  # MOMENTO 1 result
        elif 'quote' in data and 'quote_metadata' in data.get('quote', {}):
            return 'budy_agent_quote'     # MOMENTO 3 result
        elif 'project_type' in data and 'client_name' in data:
            return 'unified_project'      # Unified Project model
        elif 'quote_number' in data and 'total_amount' in data:
            return 'unified_quote'        # Unified Quote model
        else:
            return 'unknown'
    
    def _get_rfx_field_mapping(self) -> Dict[str, str]:
        """Mapeo de campos para conversión RFX"""
        return {
            'project_title': 'title',
            'project_description': 'description',
            'project_type': 'type',
            'requester_name': 'client_name',
            'requester_email': 'client_email',
            'company_name': 'client_company',
            'delivery_location': 'location',
            'estimated_cost': 'estimated_budget'
        }
    
    def _get_proposal_field_mapping(self) -> Dict[str, str]:
        """Mapeo de campos para conversión Proposal"""
        return {
            'quote_title': 'project_title',
            'quote_description': 'description',
            'quote_total': 'total_amount',
            'quote_currency': 'currency',
            'quote_status': 'status',
            'quote_notes': 'notes'
        }
    
    def _convert_project_to_rfx(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte datos de Project unificado → RFX legacy"""
        return {
            'id': project_data.get('id', 'UNKNOWN'),
            'status': 'completed',
            'title': project_data.get('name', project_data.get('title', '')),
            'description': project_data.get('description', ''),
            'client_name': project_data.get('client_name', ''),
            'client_company': project_data.get('client_company', ''),
            'client_email': project_data.get('client_email', ''),
            'estimated_budget': project_data.get('estimated_budget', ''),
            'currency': project_data.get('currency', 'USD'),
            'location': project_data.get('location', project_data.get('service_location', '')),
            'products': project_data.get('products', []),
            'industry': project_data.get('project_type', 'general'),
            'type': project_data.get('project_type', 'general')
        }
    
    def _convert_quote_to_proposal(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte datos de Quote unificado → Proposal legacy"""
        return {
            'id': quote_data.get('id', quote_data.get('quote_id', 'UNKNOWN')),
            'quote_id': quote_data.get('id', quote_data.get('quote_id', 'UNKNOWN')),
            'project_id': quote_data.get('project_id', ''),
            'project_title': quote_data.get('title', ''),
            'total_amount': quote_data.get('total_amount', 0.0),
            'currency': quote_data.get('currency', 'USD'),
            'html_content': quote_data.get('html_content', ''),
            'status': quote_data.get('status', 'GENERATED')
        }
    
    def _convert_generic_to_rfx(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Conversión genérica para datos no reconocidos → RFX format"""
        return {
            'id': data.get('id', data.get('project_id', 'UNKNOWN')),
            'status': data.get('status', 'completed'),
            'title': data.get('title', data.get('name', 'Proyecto')),
            'description': data.get('description', ''),
            'client_name': data.get('client_name', ''),
            'client_company': data.get('client_company', ''),
            'estimated_budget': data.get('estimated_budget', ''),
            'products': data.get('products', [])
        }
    
    def _convert_generic_to_proposal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Conversión genérica para datos no reconocidos → Proposal format"""
        return {
            'id': data.get('id', data.get('quote_id', 'UNKNOWN')),
            'quote_id': data.get('quote_id', data.get('id', 'UNKNOWN')),
            'project_id': data.get('project_id', ''),
            'total_amount': data.get('total_amount', 0.0),
            'currency': data.get('currency', 'USD'),
            'status': data.get('status', 'GENERATED')
        }
    
    def validate_conversion(self, original_data: Dict[str, Any], converted_data: Dict[str, Any], target_format: str) -> Dict[str, Any]:
        """
        ✅ Valida que la conversión sea correcta y completa
        
        Returns:
            Dict con resultado de validación
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'completeness_score': 0.0
        }
        
        try:
            if target_format == 'rfx':
                required_fields = ['id', 'status', 'title']
                optional_fields = ['client_name', 'client_company', 'products', 'estimated_budget']
            elif target_format == 'proposal':
                required_fields = ['id', 'quote_id', 'project_id', 'total_amount']
                optional_fields = ['html_content', 'currency', 'status']
            else:
                required_fields = ['id']
                optional_fields = []
            
            # Validar campos requeridos
            missing_required = [field for field in required_fields if field not in converted_data]
            if missing_required:
                validation_result['is_valid'] = False
                validation_result['errors'].extend([f"Missing required field: {field}" for field in missing_required])
            
            # Calcular completeness score
            total_fields = len(required_fields) + len(optional_fields)
            present_fields = len([f for f in required_fields + optional_fields if f in converted_data and converted_data[f]])
            validation_result['completeness_score'] = present_fields / total_fields if total_fields > 0 else 1.0
            
            # Warnings para campos opcionales faltantes
            missing_optional = [field for field in optional_fields if field not in converted_data or not converted_data[field]]
            if missing_optional:
                validation_result['warnings'].extend([f"Missing optional field: {field}" for field in missing_optional])
            
            logger.info(f"✅ Validation completed for {target_format}: {validation_result['completeness_score']:.2f} completeness")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"❌ Validation failed: {e}")
        
        return validation_result


# ========================
# HELPER FUNCTIONS
# ========================

def get_unified_adapter() -> UnifiedLegacyAdapter:
    """Factory function para obtener instancia del adaptador"""
    return UnifiedLegacyAdapter()


# ========================
# TESTING FUNCTION
# ========================

def test_unified_adapter():
    """Función de prueba para el adaptador unificado"""
    
    # Mock data para testing
    mock_budy_analysis = {
        'rfx_id': 'RFX-TEST-001',
        'extracted_data': {
            'project_details': {
                'title': 'Catering Evento Corporativo',
                'description': 'Servicio de catering para evento de empresa',
                'industry_domain': 'catering'
            },
            'client_information': {
                'name': 'María González',
                'company': 'PDVSA',
                'requester_email': 'maria@pdvsa.com'
            },
            'requested_products': [
                {'product_name': 'Desayuno continental', 'quantity': 100, 'unit': 'pax'}
            ]
        },
        'quality_assessment': {'confidence_level': 0.92}
    }
    
    mock_budy_quote = {
        'project_id': 'RFX-TEST-001',
        'quote': {
            'quote_metadata': {
                'quote_number': 'Q-001',
                'project_title': 'Catering PDVSA',
                'total_amount': 25000.0,
                'currency': 'USD'
            },
            'pricing_breakdown': {
                'subtotal': 22000.0,
                'coordination_fee': 3000.0,
                'total': 25000.0
            },
            'html_content': '<html><body>Propuesta</body></html>'
        }
    }
    
    # Probar adaptador
    adapter = UnifiedLegacyAdapter()
    
    # Test conversión RFX
    rfx_result = adapter.convert_to_format(mock_budy_analysis, 'rfx')
    
    # Test conversión Proposal
    proposal_result = adapter.convert_to_format(mock_budy_quote, 'proposal')
    
    # Test validación
    rfx_validation = adapter.validate_conversion(mock_budy_analysis, rfx_result, 'rfx')
    proposal_validation = adapter.validate_conversion(mock_budy_quote, proposal_result, 'proposal')
    
    print("🧪 Unified Legacy Adapter Test Results:")
    print(f"  ✅ RFX Conversion: {rfx_result.get('status')} - {rfx_result.get('title')}")
    print(f"  💰 Proposal Conversion: {proposal_result.get('status')} - {proposal_result.get('total_amount')} {proposal_result.get('currency')}")
    print(f"  🔍 RFX Validation: {rfx_validation.get('is_valid')} ({rfx_validation.get('completeness_score', 0):.2f})")
    print(f"  🔍 Proposal Validation: {proposal_validation.get('is_valid')} ({proposal_validation.get('completeness_score', 0):.2f})")
    
    return rfx_result, proposal_result, rfx_validation, proposal_validation


if __name__ == "__main__":
    test_unified_adapter()
