"""
📄 Proposal Service - Generación simplificada de propuestas comerciales
Servicio AI-FIRST que coordina generación de HTML profesional
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from openai import OpenAI

from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.services.user_branding_service import user_branding_service
from backend.prompts.proposal_generation import ProposalPrompts
from backend.utils.html_validator import HTMLValidator

logger = logging.getLogger(__name__)


class ProposalService:
    """
    Servicio simplificado de generación de propuestas.
    
    Principio AI-FIRST: El LLM genera HTML profesional completo.
    El código solo orquesta y valida.
    """
    
    def __init__(self):
        config = get_openai_config()
        self.client = OpenAI(api_key=config.api_key)
        self.db = get_database_client()
        self.model = config.model
        self.validator = HTMLValidator()
        logger.info("📄 ProposalService initialized")
    
    async def generate(
        self, 
        rfx_id: str, 
        user_id: str,
        products_with_costs: List[Dict[str, Any]],
        pricing_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera propuesta HTML profesional.
        
        Args:
            rfx_id: ID del RFX
            user_id: ID del usuario
            products_with_costs: Lista de productos con costos asignados
            pricing_config: Configuración de pricing (coordinación, impuestos, etc.)
            
        Returns:
            Dict con HTML generado y metadata
        """
        logger.info(f"📄 Generating proposal for RFX {rfx_id}, user {user_id}")
        start_time = datetime.now()
        
        try:
            # PASO 1: Obtener datos del RFX
            rfx_data = self._get_rfx_data(rfx_id)
            if not rfx_data:
                raise ValueError(f"RFX {rfx_id} not found")
            
            # PASO 2: Preparar datos de productos
            products_formatted = self._format_products(products_with_costs)
            
            # PASO 3: Calcular pricing
            pricing_data = self._calculate_pricing(products_with_costs, pricing_config)
            
            # PASO 4: Obtener branding del usuario
            branding = user_branding_service.get_branding_with_analysis(user_id)
            
            # PASO 5: Construir prompt según branding
            if branding:
                logger.info("🎨 Using custom branding")
                prompt = self._build_prompt_with_branding(
                    rfx_data, products_formatted, pricing_data, branding, user_id
                )
            else:
                logger.info("🎨 Using default branding")
                prompt = self._build_prompt_default(
                    rfx_data, products_formatted, pricing_data
                )
            
            # PASO 6: Generar HTML con AI (con retry automático)
            html = await self._generate_html_with_retry(prompt, max_retries=2)
            
            # PASO 7: Validar HTML
            validation = self.validator.validate(html)
            if not validation['is_valid']:
                logger.warning(f"⚠️ HTML validation warnings: {validation['errors']}")
            
            # PASO 8: Guardar propuesta
            proposal_id = self._save_proposal(rfx_id, user_id, html)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Proposal generated successfully in {processing_time:.2f}s - ID: {proposal_id}")
            
            return {
                'proposal_id': proposal_id,
                'html_content': html,
                'validation': validation,
                'processing_time_seconds': processing_time,
                'has_branding': bool(branding)
            }
            
        except Exception as e:
            logger.error(f"❌ Proposal generation failed: {e}")
            raise
    
    def _get_rfx_data(self, rfx_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos del RFX desde la base de datos."""
        try:
            result = self.db.client.table('rfx_v2')\
                .select('*')\
                .eq('id', rfx_id)\
                .single()\
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"❌ Error getting RFX data: {e}")
            return None
    
    def _format_products(self, products: List[Dict[str, Any]]) -> str:
        """
        Formatea productos para el prompt.
        
        Args:
            products: Lista de productos con costos
            
        Returns:
            String formateado para el prompt
        """
        if not products:
            return "No hay productos"
        
        formatted = []
        for i, product in enumerate(products, 1):
            name = product.get('nombre', product.get('name', 'Sin nombre'))
            quantity = product.get('cantidad', product.get('quantity', 0))
            unit = product.get('unidad', product.get('unit', 'unidades'))
            unit_cost = product.get('costo_unitario', product.get('unit_cost', 0))
            total = quantity * unit_cost
            
            formatted.append(
                f"{i}. {name}\n"
                f"   - Cantidad: {quantity} {unit}\n"
                f"   - Precio unitario: ${unit_cost:.2f}\n"
                f"   - Total: ${total:.2f}"
            )
        
        return "\n\n".join(formatted)
    
    def _calculate_pricing(
        self, 
        products: List[Dict[str, Any]], 
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcula totales de pricing.
        
        Args:
            products: Lista de productos con costos
            config: Configuración de pricing (opcional)
            
        Returns:
            Dict con totales formateados
        """
        # Calcular subtotal
        subtotal = sum(
            p.get('cantidad', p.get('quantity', 0)) * 
            p.get('costo_unitario', p.get('unit_cost', 0))
            for p in products
        )
        
        # Configuración por defecto
        config = config or {}
        
        # Coordinación
        coordination_enabled = config.get('coordination_enabled', False)
        coordination_rate = config.get('coordination_rate', 0.18)
        coordination = subtotal * coordination_rate if coordination_enabled else 0
        
        # Impuestos
        taxes_enabled = config.get('taxes_enabled', False)
        tax_rate = config.get('tax_rate', 0.16)
        tax = subtotal * tax_rate if taxes_enabled else 0
        
        # Costo por persona
        cost_per_person_enabled = config.get('cost_per_person_enabled', False)
        headcount = config.get('headcount', 120)
        cost_per_person = (subtotal + coordination + tax) / headcount if cost_per_person_enabled and headcount > 0 else 0
        
        # Total
        total = subtotal + coordination + tax
        
        # Flags inteligentes (mostrar solo si activo Y > 0)
        show_coordination = coordination_enabled and coordination > 0
        show_tax = taxes_enabled and tax > 0
        show_cost_per_person = cost_per_person_enabled and cost_per_person > 0
        
        return {
            'subtotal': subtotal,
            'subtotal_formatted': f"${subtotal:.2f}",
            'coordination': coordination,
            'coordination_formatted': f"${coordination:.2f}",
            'coordination_percentage': f"{coordination_rate * 100:.1f}",
            'coordination_enabled': coordination_enabled,
            'show_coordination': show_coordination,
            'tax': tax,
            'tax_formatted': f"${tax:.2f}",
            'tax_percentage': f"{tax_rate * 100:.1f}",
            'taxes_enabled': taxes_enabled,
            'show_tax': show_tax,
            'total': total,
            'total_formatted': f"${total:.2f}",
            'cost_per_person': cost_per_person,
            'cost_per_person_formatted': f"${cost_per_person:.2f}",
            'cost_per_person_enabled': cost_per_person_enabled,
            'show_cost_per_person': show_cost_per_person
        }
    
    def _build_prompt_with_branding(
        self,
        rfx_data: Dict[str, Any],
        products_formatted: str,
        pricing_data: Dict[str, Any],
        branding: Dict[str, Any],
        user_id: str
    ) -> str:
        """Construye prompt con branding personalizado."""
        
        # Preparar datos del RFX para el prompt
        rfx_prompt_data = {
            'client_name': rfx_data.get('nombre_solicitante', 'Cliente'),
            'solicitud': rfx_data.get('description', rfx_data.get('title', 'Solicitud de presupuesto')),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'products': products_formatted
        }
        
        # Logo endpoint
        logo_endpoint = f"/api/branding/files/{user_id}/logo"
        
        # Información de la empresa
        company_info = {
            'name': 'Sabra Corporation',
            'address': 'Dirección de la empresa',
            'phone': '+1 (555) 123-4567',
            'email': 'contacto@sabracorp.com'
        }
        
        # Extraer configuración de branding
        branding_config = {
            'primary_color': branding.get('logo_analysis', {}).get('dominant_colors', [{}])[0].get('hex', '#0e2541'),
            'table_header_bg': branding.get('template_analysis', {}).get('table_style', {}).get('header_bg', '#0e2541'),
            'table_header_text': branding.get('template_analysis', {}).get('table_style', {}).get('header_text', '#ffffff'),
            'table_border': branding.get('template_analysis', {}).get('table_style', {}).get('border_color', '#000000')
        }
        
        return ProposalPrompts.get_prompt_with_branding(
            user_id=user_id,
            logo_endpoint=logo_endpoint,
            company_info=company_info,
            rfx_data=rfx_prompt_data,
            pricing_data=pricing_data,
            branding_config=branding_config
        )
    
    def _build_prompt_default(
        self,
        rfx_data: Dict[str, Any],
        products_formatted: str,
        pricing_data: Dict[str, Any]
    ) -> str:
        """Construye prompt con branding por defecto."""
        
        # Preparar datos del RFX
        rfx_prompt_data = {
            'client_name': rfx_data.get('nombre_solicitante', 'Cliente'),
            'solicitud': rfx_data.get('description', rfx_data.get('title', 'Solicitud de presupuesto')),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'products': products_formatted
        }
        
        # Información de la empresa
        company_info = {
            'name': 'Sabra Corporation',
            'address': 'Dirección de la empresa',
            'phone': '+1 (555) 123-4567',
            'email': 'contacto@sabracorp.com'
        }
        
        return ProposalPrompts.get_prompt_default(
            company_info=company_info,
            rfx_data=rfx_prompt_data,
            pricing_data=pricing_data
        )
    
    async def _generate_html_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """
        Genera HTML con retry automático si falla.
        
        Args:
            prompt: Prompt para el LLM
            max_retries: Número máximo de reintentos
            
        Returns:
            HTML generado
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"🤖 Generating HTML (attempt {attempt + 1}/{max_retries + 1})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un experto en generación de presupuestos HTML profesionales."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096
                )
                
                html = response.choices[0].message.content
                
                # Limpiar markdown si existe
                html = html.replace('```html', '').replace('```', '').strip()
                
                # Validar que sea HTML válido
                if '<html' in html.lower() and '</html>' in html.lower():
                    logger.info(f"✅ HTML generated successfully ({len(html)} chars)")
                    return html
                else:
                    raise ValueError("Generated content is not valid HTML")
                    
            except Exception as e:
                logger.error(f"❌ HTML generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    raise Exception(f"Failed to generate HTML after {max_retries + 1} attempts")
                
                # Esperar antes de reintentar
                import asyncio
                await asyncio.sleep(2)
        
        raise Exception("Failed to generate HTML")
    
    def _save_proposal(self, rfx_id: str, user_id: str, html: str) -> str:
        """
        Guarda propuesta en la base de datos.
        
        Args:
            rfx_id: ID del RFX
            user_id: ID del usuario
            html: Contenido HTML
            
        Returns:
            ID de la propuesta guardada
        """
        try:
            proposal_data = {
                'rfx_id': rfx_id,
                'user_id': user_id,
                'html_content': html,
                'status': 'generated',
                'generated_at': datetime.now().isoformat()
            }
            
            result = self.db.client.table('proposals').insert(proposal_data).execute()
            
            if result.data:
                proposal_id = result.data[0]['id']
                logger.info(f"✅ Proposal saved with ID: {proposal_id}")
                return proposal_id
            else:
                raise Exception("Failed to save proposal - no data returned")
                
        except Exception as e:
            logger.error(f"❌ Error saving proposal: {e}")
            raise


# Singleton para reutilización
proposal_service = ProposalService()
