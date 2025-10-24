"""
🎯 Proposal Generation Service - REFACTORIZADO V5.0
Arquitectura mejorada: Prompts separados + Validación por scoring + Retry automático
"""
import json
import uuid
import re
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from backend.models.proposal_models import ProposalRequest, GeneratedProposal, ProposalStatus
from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.services.unified_budget_configuration_service import unified_budget_service
from backend.services.prompts.proposal_prompts import ProposalPrompts
from backend.utils.html_validator import HTMLValidator

import logging

logger = logging.getLogger(__name__)


class ProposalGenerationService:
    """Servicio refactorizado para generar propuestas comerciales con validación robusta"""
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = None  # Lazy initialization
        self.db_client = get_database_client()
    
    def _get_openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self.openai_client is None:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_config.api_key)
            except ImportError:
                raise ImportError("OpenAI module not installed. Run: pip install openai")
        return self.openai_client
    
    async def generate_proposal(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> GeneratedProposal:
        """
        🚀 Método principal REFACTORIZADO con validación por scoring
        
        Args:
            rfx_data: Datos del RFX con cliente, productos, fechas, etc.
            proposal_request: Request con configuraciones adicionales
            
        Returns:
            GeneratedProposal: Objeto con HTML completo y metadata
        """
        logger.info(f"🚀 Starting proposal generation - RFX: {proposal_request.rfx_id}, User: {rfx_data.get('user_id', 'N/A')}")
        
        try:
            # 1. Obtener user_id con fallbacks múltiples
            user_id = self._get_user_id(rfx_data, proposal_request.rfx_id)
            logger.info(f"✅ Generating proposal for user: {user_id}")
            
            # 2. Preparar datos de productos
            products_info = self._prepare_products_data(rfx_data)
            
            # 3. Calcular pricing
            subtotal = sum(p['total'] for p in products_info)
            pricing_calculation = unified_budget_service.calculate_with_unified_config(
                proposal_request.rfx_id, subtotal
            )
            
            # 4. Obtener configuración y moneda
            unified_config = unified_budget_service.get_user_unified_config(user_id)
            currency = self._get_currency(rfx_data, unified_config)
            
            # 5. Detectar si tiene branding completo
            has_branding = self._has_complete_branding(user_id)
            
            # 6. Generar HTML usando el prompt apropiado
            if has_branding:
                logger.info(f"🎨 Branding check - Logo: True, Active: True, Completed: True → {has_branding}")
                logger.info(f"✅ Using BRANDING PROMPT (with logo)")
                branding_config = self._get_branding_config(user_id)
                html_content = await self._generate_with_branding(
                    rfx_data, products_info, pricing_calculation, currency, user_id, branding_config
                )
            else:
                logger.info(f"📄 No branding found for user {user_id}")
                logger.info(f"📄 Using DEFAULT PROMPT (no branding)")
                html_content = await self._generate_default(
                    rfx_data, products_info, pricing_calculation, currency
                )
            
            # 7. Validar HTML con sistema de scoring
            validation_result = self._validate_html(html_content, products_info)
            
            # 8. Retry si la validación falla
            if not validation_result['is_valid']:
                logger.warning(f"⚠️ Validation failed, attempting retry with corrections...")
                html_content = await self._retry_generation(
                    html_content, validation_result['issues'], rfx_data, 
                    products_info, pricing_calculation, currency
                )
                
                # Validar nuevamente
                validation_result = self._validate_html(html_content, products_info)
                if validation_result['is_valid']:
                    logger.info(f"✅ Retry successful - validation passed")
                else:
                    logger.error(f"❌ Retry failed - validation still failing")
            
            # 9. Crear objeto de propuesta
            proposal = self._create_proposal_object(
                rfx_data, html_content, proposal_request, pricing_calculation
            )
            
            # 10. Guardar en BD
            await self._save_to_database(proposal)
            
            logger.info(f"✅ Proposal generated successfully - Document ID: {proposal.id}")
            logger.info(f"📊 Validation score: {validation_result['score']}/10 ({validation_result['score']*10:.0f}%)")
            
            return proposal
            
        except Exception as e:
            logger.error(f"❌ Error generating proposal: {e}", exc_info=True)
            raise Exception(f"Proposal generation failed: {e}")
    
    def _get_user_id(self, rfx_data: Dict[str, Any], rfx_id: str) -> str:
        """Obtiene user_id con múltiples fallbacks"""
        # PASO 1: Desde rfx_data
        user_id = rfx_data.get("user_id")
        if user_id:
            logger.info(f"🔍 user_id from rfx_data: {user_id}")
            return user_id
        
        # PASO 2: Desde base de datos
        logger.warning("⚠️ user_id not in rfx_data, attempting database lookup")
        try:
            rfx_result = self.db_client.client.table("rfx_v2").select("user_id").eq("id", rfx_id).single().execute()
            if rfx_result.data:
                user_id = rfx_result.data.get("user_id")
                if user_id:
                    logger.info(f"✅ Retrieved user_id from RFX database: {user_id}")
                    return user_id
        except Exception as e:
            logger.error(f"❌ Could not retrieve user_id from database: {e}")
        
        # PASO 3: Fallback final (de memorias - usuario conocido)
        user_id = "186ea35f-3cf8-480f-a7d3-0af178c09498"
        logger.warning(f"⚠️ Using fallback user_id: {user_id}")
        return user_id
    
    def _prepare_products_data(self, rfx_data: Dict[str, Any]) -> List[Dict]:
        """Prepara datos de productos para el prompt"""
        productos = rfx_data.get('productos', [])
        products_info = []
        
        for producto in productos:
            precio_unitario = producto.get("estimated_unit_price", 0.0)
            cantidad = producto.get("quantity", producto.get("cantidad", 1))
            total_producto = precio_unitario * cantidad
            
            products_info.append({
                "nombre": producto.get("name", producto.get("nombre", "product")),
                "cantidad": cantidad,
                "unidad": producto.get("unit", producto.get("unidad", "units")),
                "precio_unitario": precio_unitario,
                "total": total_producto
            })
        
        return products_info
    
    def _get_currency(self, rfx_data: Dict[str, Any], unified_config: Optional[Dict]) -> str:
        """Obtiene moneda con prioridades"""
        if unified_config:
            currency = unified_config.get('document', {}).get('currency')
            if currency:
                return currency
        
        return rfx_data.get("currency", "USD")
    
    def _map_rfx_data_for_prompt(self, rfx_data: Dict, products_info: List[Dict]) -> Dict:
        """
        🔧 Mapea rfx_data al formato que espera el prompt
        
        Convierte:
        - 'companies' → 'client_name'
        - 'title' → 'solicitud'
        - 'productos' + products_info → 'products'
        - Agrega fecha actual automáticamente
        """
        from datetime import datetime, timedelta
        
        # Extraer información del cliente
        companies = rfx_data.get('companies', {})
        if isinstance(companies, dict):
            client_name = companies.get('name', 'N/A')
        else:
            client_name = 'N/A'
        
        # Usar products_info que ya viene preparado
        products = products_info if products_info else []
        
        # Calcular fecha actual
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calcular fecha de vigencia (30 días desde hoy)
        validity_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Mapear datos
        mapped_data = {
            'client_name': client_name,
            'solicitud': rfx_data.get('title', 'N/A'),
            'products': products,
            'user_id': rfx_data.get('user_id'),
            'current_date': current_date,
            'validity_date': validity_date
        }
        
        logger.info(f"✅ Mapped data - client: {client_name}, solicitud: {rfx_data.get('title', 'N/A')}, products: {len(products)}, date: {current_date}")
        
        return mapped_data
    
    def _get_company_info(self, user_id: str) -> Dict[str, str]:
        """Obtiene información de la empresa del usuario"""
        try:
            # Aquí deberías obtener la info real de la BD
            # Por ahora retornamos un placeholder
            return {
                'name': 'Sabra Corporation',
                'address': 'Dirección de la empresa',
                'phone': '+1 (555) 123-4567',
                'email': 'contacto@sabracorp.com'
            }
        except Exception as e:
            logger.error(f"Error getting company info: {e}")
            return {
                'name': 'Empresa',
                'address': 'N/A',
                'phone': 'N/A',
                'email': 'N/A'
            }
    
    def _format_pricing_data(self, pricing_calculation: Any, currency: str, rfx_id: str = None) -> Dict[str, str]:
        """Formatea datos de pricing para los prompts CON flags de configuración activa"""
        try:
            # Obtener símbolo de moneda
            symbols = {
                'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
                'MXN': '$', 'CAD': 'C$', 'AUD': 'A$', 'BRL': 'R$',
                'COP': '$', 'CHF': 'CHF', 'CNY': '¥', 'INR': '₹'
            }
            symbol = symbols.get(currency, '$')
            
            # Extraer valores con manejo seguro de None
            if isinstance(pricing_calculation, dict):
                subtotal = pricing_calculation.get('subtotal', 0) or 0
                coordination = pricing_calculation.get('coordination_amount', 0) or 0
                coordination_rate = (pricing_calculation.get('coordination_rate') or 0) * 100
                coordination_enabled = pricing_calculation.get('coordination_enabled', False)
                tax = pricing_calculation.get('tax_amount', 0) or 0
                tax_rate = (pricing_calculation.get('tax_rate') or 0) * 100
                taxes_enabled = pricing_calculation.get('taxes_enabled', False)
                total = pricing_calculation.get('total', 0) or 0
                cost_per_person = pricing_calculation.get('cost_per_person', 0) or 0
                cost_per_person_enabled = pricing_calculation.get('cost_per_person_enabled', False)
            else:
                subtotal = getattr(pricing_calculation, 'subtotal', 0) or 0
                coordination = getattr(pricing_calculation, 'coordination_amount', 0) or 0
                coordination_rate = (getattr(pricing_calculation, 'coordination_rate', 0) or 0) * 100
                coordination_enabled = getattr(pricing_calculation, 'coordination_enabled', False)
                tax = getattr(pricing_calculation, 'tax_amount', 0) or 0
                tax_rate = (getattr(pricing_calculation, 'tax_rate', 0) or 0) * 100
                taxes_enabled = getattr(pricing_calculation, 'taxes_enabled', False)
                total = getattr(pricing_calculation, 'total_cost', 0) or 0
                cost_per_person = getattr(pricing_calculation, 'cost_per_person', 0) or 0
                cost_per_person_enabled = getattr(pricing_calculation, 'cost_per_person_enabled', False)
            
            # ✅ LÓGICA INTELIGENTE: Solo mostrar si está ACTIVO Y tiene valor > 0
            show_coordination = coordination_enabled and coordination > 0
            show_tax = taxes_enabled and tax > 0
            show_cost_per_person = cost_per_person_enabled and cost_per_person > 0
            
            logger.info(f"💰 Pricing flags - Coordination: {show_coordination} (enabled={coordination_enabled}, amount={coordination})")
            logger.info(f"💰 Pricing flags - Tax: {show_tax} (enabled={taxes_enabled}, amount={tax})")
            logger.info(f"💰 Pricing flags - Cost per person: {show_cost_per_person} (enabled={cost_per_person_enabled}, amount={cost_per_person})")
            
            return {
                'subtotal_formatted': f"{symbol}{subtotal:.2f}",
                'coordination_formatted': f"{symbol}{coordination:.2f}",
                'coordination_percentage': f"{coordination_rate:.1f}",
                'coordination_enabled': coordination_enabled,
                'show_coordination': show_coordination,  # ✅ Flag inteligente
                'tax_formatted': f"{symbol}{tax:.2f}",
                'tax_percentage': f"{tax_rate:.1f}",
                'taxes_enabled': taxes_enabled,
                'show_tax': show_tax,  # ✅ Flag inteligente
                'total_formatted': f"{symbol}{total:.2f}",
                'cost_per_person_formatted': f"{symbol}{cost_per_person:.2f}",
                'cost_per_person_enabled': cost_per_person_enabled,
                'show_cost_per_person': show_cost_per_person  # ✅ Flag inteligente
            }
        except Exception as e:
            logger.error(f"Error formatting pricing data: {e}")
            return {
                'subtotal_formatted': '$0.00',
                'coordination_formatted': '$0.00',
                'coordination_percentage': '0',
                'coordination_enabled': False,
                'show_coordination': False,
                'tax_formatted': '$0.00',
                'tax_percentage': '0',
                'taxes_enabled': False,
                'show_tax': False,
                'total_formatted': '$0.00',
                'cost_per_person_formatted': '$0.00',
                'cost_per_person_enabled': False,
                'show_cost_per_person': False
            }
    
    def _has_complete_branding(self, user_id: str) -> bool:
        """
        🆕 Detecta si el usuario tiene branding completo (logo + análisis completado)
        
        Returns:
            True si tiene logo Y análisis completado
        """
        try:
            from backend.services.user_branding_service import user_branding_service
            
            branding = user_branding_service.get_branding_with_analysis(user_id)
            
            if not branding:
                return False
            
            # Verificar que tenga logo
            has_logo = bool(branding.get('logo_url'))
            
            # Verificar que esté activo
            is_active = branding.get('is_active', False)
            
            # Verificar que el análisis esté completado
            analysis_completed = branding.get('analysis_status') == 'completed'
            
            return has_logo and is_active and analysis_completed
            
        except Exception as e:
            logger.error(f"Error checking branding: {e}")
            return False
    
    def _get_branding_config(self, user_id: str) -> Dict[str, Any]:
        """Obtiene configuración de branding completa con colores reales del template"""
        try:
            from backend.services.user_branding_service import user_branding_service
            
            branding = user_branding_service.get_branding_with_analysis(user_id)
            
            if not branding:
                return {}
            
            template_analysis = branding.get('template_analysis', {})
            logo_analysis = branding.get('logo_analysis', {})
            
            # ✅ EXTRAER COLORES REALES DEL TEMPLATE ANALYSIS
            color_scheme = template_analysis.get('color_scheme', {})
            table_style = template_analysis.get('table_style', {})
            
            # Colores principales
            primary_color = color_scheme.get('primary', '#2c5f7c')
            secondary_color = color_scheme.get('secondary', '#ffffff')
            
            # Colores específicos de tabla
            table_header_bg = table_style.get('header_background', '#f0f0f0')
            table_header_text = color_scheme.get('text', '#000000')
            table_border = color_scheme.get('borders', '#000000')
            
            logger.info(f"🎨 Branding colors - Primary: {primary_color}, Secondary: {secondary_color}")
            logger.info(f"🎨 Table colors - Header BG: {table_header_bg}, Header Text: {table_header_text}")
            
            return {
                'logo_url': branding.get('logo_url'),
                'logo_analysis': logo_analysis,
                'template_analysis': template_analysis,
                'primary_color': primary_color,
                'secondary_color': secondary_color,
                'table_header_bg': table_header_bg,
                'table_header_text': table_header_text,
                'table_border': table_border,
                'typography': template_analysis.get('typography', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting branding config: {e}")
            return {}
    
    async def _generate_with_branding(
        self, rfx_data: Dict, products_info: List[Dict], 
        pricing_calculation: Dict, currency: str, user_id: str, branding_config: Dict
    ) -> str:
        """🎨 Genera propuesta CON branding usando ProposalPrompts"""
        logger.info(f"🎨 Building prompt with branding for user {user_id}")
        
        # Construir URL del logo - Usar ruta relativa para compatibilidad con servidor
        logo_endpoint = f"/api/branding/files/{user_id}/logo"
        logger.info(f"🎨 Logo endpoint (relative): {logo_endpoint}")
        
        # Preparar datos para el prompt
        company_info = self._get_company_info(user_id)
        pricing_data = self._format_pricing_data(pricing_calculation, currency)
        
        # DEBUG: Log de datos originales
        logger.info(f"🔍 DEBUG rfx_data keys: {list(rfx_data.keys())}")
        logger.info(f"🔍 DEBUG products_info count: {len(products_info)}")
        logger.info(f"🔍 DEBUG productos count: {len(rfx_data.get('productos', []))}")
        
        # 🔧 MAPEAR datos al formato que espera el prompt
        mapped_rfx_data = self._map_rfx_data_for_prompt(rfx_data, products_info)
        
        logger.info(f"✅ Mapped data - client: {mapped_rfx_data.get('client_name')}, products: {len(mapped_rfx_data.get('products', []))}")
        
        # Llamar al prompt con los parámetros correctos
        prompt = ProposalPrompts.get_prompt_with_branding(
            user_id=user_id,
            logo_endpoint=logo_endpoint,
            company_info=company_info,
            rfx_data=mapped_rfx_data,
            pricing_data=pricing_data,
            branding_config=branding_config  # ✅ Pasar colores del branding
        )
        
        return await self._call_ai(prompt)
    
    async def _generate_default(
        self, rfx_data: Dict, products_info: List[Dict], 
        pricing_calculation: Dict, currency: str
    ) -> str:
        """📋 Genera propuesta CON logo por defecto de Sabra usando ProposalPrompts"""
        logger.info(f"📋 Building default prompt (with Sabra default logo)")
        
        # Preparar datos para el prompt
        user_id = rfx_data.get('user_id', 'unknown')
        company_info = self._get_company_info(user_id)
        pricing_data = self._format_pricing_data(pricing_calculation, currency)
        
        # 🔧 MAPEAR datos al formato que espera el prompt
        mapped_rfx_data = self._map_rfx_data_for_prompt(rfx_data, products_info)
        
        # Usar ruta relativa para el logo por defecto - compatibilidad con servidor
        base_url = ""  # Ruta relativa, no necesita dominio completo
        
        # Llamar al prompt con los parámetros correctos
        prompt = ProposalPrompts.get_prompt_default(
            company_info=company_info,
            rfx_data=mapped_rfx_data,
            pricing_data=pricing_data,
            base_url=base_url
        )
        
        return await self._call_ai(prompt)
    
    async def _retry_generation(
        self, original_html: str, issues: List[str], rfx_data: Dict,
        products_info: List[Dict], pricing_calculation: Dict, currency: str
    ) -> str:
        """🔄 Reintenta generación con correcciones específicas"""
        logger.info(f"🔄 Attempting retry with explicit corrections...")
        logger.info(f"🔄 Issues to fix: {issues}")
        
        # Obtener user_id para reconstruir el prompt
        user_id = self._get_user_id(rfx_data, rfx_data.get('id', ''))
        has_branding = self._has_complete_branding(user_id)
        
        # Reconstruir el prompt original (sin llamar a AI)
        if has_branding:
            branding_config = self._get_branding_config(user_id)
            # Usar ruta relativa para compatibilidad con servidor
            logo_endpoint = f"/api/branding/files/{user_id}/logo"
            
            # Preparar datos para el prompt
            company_info = self._get_company_info(user_id)
            pricing_data = self._format_pricing_data(pricing_calculation, rfx_data.get('currency', 'USD'))
            
            original_prompt = ProposalPrompts.get_prompt_with_branding(
                user_id=user_id,
                logo_endpoint=logo_endpoint,
                company_info=company_info,
                rfx_data=rfx_data,
                pricing_data=pricing_data,
                branding_config=branding_config  # ✅ Pasar colores del branding
            )
        else:
            company_info = self._get_company_info(user_id)
            pricing_data = self._format_pricing_data(pricing_calculation, rfx_data.get('currency', 'USD'))
            
            base_url = os.getenv('BASE_URL', 'http://localhost:5001')
            original_prompt = ProposalPrompts.get_prompt_default(
                company_info=company_info,
                rfx_data=rfx_data,
                pricing_data=pricing_data,
                base_url=base_url
            )
        
        # Construir prompt de retry con correcciones
        retry_prompt = ProposalPrompts.get_retry_prompt(
            original_prompt=original_prompt,
            validation_errors=issues
        )
        
        return await self._call_ai(retry_prompt)
    
    async def _call_ai(self, prompt: str) -> str:
        """🤖 Llama a OpenAI con el prompt"""
        logger.info(f"🤖 Calling OpenAI API...")
        
        openai_client = self._get_openai_client()
        
        try:
            response = openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(4000, self.openai_config.max_tokens),
                temperature=0.7
            )
            
            html_content = (response.choices[0].message.content or "").strip()
            
            # Limpiar marcadores de código si existen
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            
            html_content = html_content.strip()
            
            logger.info(f"✅ OpenAI response received - Length: {len(html_content)} chars")
            
            return html_content
            
        except Exception as e:
            logger.error(f"❌ OpenAI call failed: {e}")
            raise
    
    def _validate_html(self, html: str, products_info: List[Dict]) -> Dict[str, Any]:
        """
        🔍 Valida HTML usando HTMLValidator con sistema de scoring (0-10 puntos)
        
        Returns:
            Dict con: is_valid, score, max_score, errors, warnings, details, percentage
        """
        logger.info(f"🔍 Validating HTML content...")
        
        # Usar el validador robusto
        validation = HTMLValidator.validate_proposal_html(html)
        
        # Logging detallado
        logger.info(f"📊 Validation result: {validation['score']}/{validation['max_score']} ({validation['percentage']:.0f}%) - {'✅ VALID' if validation['is_valid'] else '❌ INVALID'}")
        
        if not validation['is_valid']:
            logger.warning(f"⚠️ Validation errors found:")
            for error in validation['errors']:
                logger.warning(f"   - {error}")
        
        if validation['warnings']:
            logger.info(f"ℹ️ Validation warnings:")
            for warning in validation['warnings']:
                logger.info(f"   - {warning}")
        
        # Log de detalles
        logger.debug(f"📋 Validation details: {validation['details']}")
        
        # Convertir a formato compatible con el resto del código
        return {
            'is_valid': validation['is_valid'],
            'score': validation['score'],
            'max_score': validation['max_score'],
            'issues': validation['errors'] + validation['warnings'],
            'details': validation['details'],
            'percentage': validation['percentage']
        }
    
    def _create_proposal_object(
        self, rfx_data: Dict[str, Any], html_content: str, 
        proposal_request: ProposalRequest, pricing_calculation: Any
    ) -> GeneratedProposal:
        """Crea objeto GeneratedProposal"""
        
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        proposal_id = uuid.uuid4()
        rfx_uuid = uuid.UUID(proposal_request.rfx_id) if isinstance(proposal_request.rfx_id, str) else proposal_request.rfx_id
        
        # Obtener total del pricing calculation
        total_cost = pricing_calculation.get('total', 0) if isinstance(pricing_calculation, dict) else getattr(pricing_calculation, 'total_cost', 0)
        
        return GeneratedProposal(
            id=proposal_id,
            rfx_id=rfx_uuid,
            content_markdown="",
            content_html=html_content,
            itemized_costs=[],
            total_cost=total_cost,
            notes=proposal_request.notes,
            status=ProposalStatus.GENERATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "client_name": client_info.get("name", "Cliente"),
                "client_email": client_info.get("email", ""),
                "products_count": len(rfx_data.get("productos", [])),
                "generation_method": "refactored_v5_with_scoring",
                "ai_model": self.openai_config.model,
                "document_type": "commercial_proposal",
                "generation_version": "5.0_refactored"
            }
        )
    
    async def _save_to_database(self, proposal: GeneratedProposal) -> None:
        """Guarda propuesta en base de datos"""
        logger.info(f"💾 Saving proposal to database...")
        
        document_data = {
            "id": str(proposal.id),
            "rfx_id": str(proposal.rfx_id),
            "document_type": "proposal",
            "content_html": proposal.content_html,
            "total_cost": proposal.total_cost,
            "created_at": proposal.created_at.isoformat(),
            "metadata": proposal.metadata,
            "version": 1
        }
        
        try:
            result_id = self.db_client.save_generated_document(document_data)
            logger.info(f"✅ Proposal saved - ID: {result_id}")
        except Exception as e:
            error_msg = str(e).lower()
            
            if "duplicate key" in error_msg or "already exists" in error_msg:
                logger.warning(f"⚠️ Document already exists: {document_data['id']}")
            else:
                logger.error(f"❌ Error saving to database: {e}")


# Función de conveniencia para uso externo
async def generate_commercial_proposal(rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> GeneratedProposal:
    """
    Función utilitaria simplificada para generar propuestas comerciales
    
    Args:
        rfx_data: Datos del RFX
        proposal_request: Configuraciones de la propuesta
        
    Returns:
        GeneratedProposal: Propuesta lista para mostrar en frontend
    """
    service = ProposalGenerationService()
    return await service.generate_proposal(rfx_data, proposal_request)
