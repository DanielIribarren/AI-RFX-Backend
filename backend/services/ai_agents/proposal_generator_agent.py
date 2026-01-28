"""
🤖 Proposal Generator Agent (NO AI - Python Puro)
Responsabilidad: Insertar datos del RFX en el template HTML del usuario
Enfoque: ULTRA SIMPLE - Template + Datos → .replace() → HTML con datos
Sin llamadas a OpenAI - 100% determinístico y rápido
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProposalGeneratorAgent:
    """
    Agente especializado en insertar datos en templates HTML usando Python puro
    NO usa AI - 100% determinístico, rápido y confiable
    Arquitectura ULTRA SIMPLE: Template + Datos → .replace() → HTML completo
    """
    
    def __init__(self):
        """No requiere configuración - solo lógica Python pura"""
        pass
    
    async def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera HTML insertando datos del RFX en el template
        
        Args:
            request: {
                "html_template": "<html>...template...</html>",
                "user_id": "uuid",
                "logo_url": "/api/branding/files/{user_id}/logo",
                "data": {
                    "client_name": "Empresa XYZ",
                    "solicitud": "Descripción",
                    "products": [...],
                    "pricing": {...}
                }
            }
        """
        try:
            logger.info("🤖 Proposal Generator Agent - Starting generation")
            
            html_template = request.get("html_template")
            data = request.get("data", {})
            branding_config = request.get("branding_config", {})
            
            if not html_template:
                return {"status": "error", "error": "html_template required", "html_generated": None}
            
            # Mapear datos
            mapped_data = self._map_data(data)
            
            # Insertar datos en template usando Python puro (SIN AI)
            html_generated = self._insert_data_in_template(html_template, mapped_data, branding_config)
            
            logger.info(f"✅ HTML generated - Length: {len(html_generated)} chars")
            
            return {
                "status": "success",
                "html_generated": html_generated,
                "metadata": mapped_data  # Pasar todos los datos mapeados para validación
            }
            
        except Exception as e:
            logger.error(f"❌ Error in Proposal Generator Agent: {e}")
            return {"status": "error", "error": str(e), "html_generated": None}
    
    def _map_data(self, data: Dict) -> Dict:
        """Mapea datos del RFX al formato esperado (reutiliza lógica del service)"""
        
        # Fechas
        current_date = datetime.now().strftime('%Y-%m-%d')
        validity_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Extraer datos
        client_name = data.get('client_name', 'N/A')
        solicitud = data.get('solicitud', 'N/A')
        products = data.get('products', [])
        pricing = data.get('pricing', {})
        pricing_config = data.get('pricing_config', {})  # ✅ NUEVO: Configuraciones detalladas
        
        mapped = {
            'client_name': client_name,
            'solicitud': solicitud,
            'products': products,
            'pricing': pricing,
            'pricing_config': pricing_config,  # ✅ NUEVO: Pasar configuraciones
            'current_date': current_date,
            'validity_date': validity_date
        }
        
        logger.info(f"📋 Data mapped - Client: {client_name}, Products: {len(products)}, Total: {pricing.get('total_formatted', '$0.00')}")
        if pricing_config:
            logger.info(f"⚙️ Pricing config - Coordination: {pricing_config.get('coordination_enabled', False)}, Taxes: {pricing_config.get('taxes_enabled', False)}, Cost per person: {pricing_config.get('cost_per_person_enabled', False)}")
        
        return mapped
    
    def _insert_data_in_template(self, html_template: str, mapped_data: Dict, branding_config: Dict = None) -> str:
        """
        Inserta datos en template usando replace (SIN AI - Python puro)
        100% determinístico, rápido y confiable
        """
        html = html_template
        
        # Aplicar colores del branding si están disponibles
        if branding_config:
            primary_color = branding_config.get('primary_color', '')
            table_header_bg = branding_config.get('table_header_bg', '')
            table_header_text = branding_config.get('table_header_text', '')
            
            # Reemplazar colores hardcodeados del template con colores del branding
            if primary_color:
                # Reemplazar variaciones comunes de colores hardcodeados
                html = html.replace('#1F2A44', primary_color)
                html = html.replace('#1f2a44', primary_color)
                html = html.replace('color: #1F2A44', f'color: {primary_color}')
                html = html.replace('background-color: #1F2A44', f'background-color: {primary_color}')
                
                logger.info(f"🎨 Applied primary color: {primary_color}")
        
        # Reemplazos simples de variables (múltiples variaciones para compatibilidad)
        client_name = mapped_data.get('client_name', 'N/A')
        solicitud = mapped_data.get('solicitud', 'N/A')
        current_date = mapped_data.get('current_date', 'N/A')
        validity_date = mapped_data.get('validity_date', 'N/A')
        
        # Cliente (variaciones posibles)
        html = html.replace("{{CLIENT_NAME}}", client_name)
        html = html.replace("{{CLIENTE}}", client_name)
        
        # Solicitud/Request (variaciones posibles)
        html = html.replace("{{SOLICITUD}}", solicitud)
        html = html.replace("{{REQUEST_DESCRIPTION}}", solicitud)
        html = html.replace("{{REQUEST}}", solicitud)
        html = html.replace("{{DESCRIPCION}}", solicitud)
        
        # Fechas (variaciones posibles)
        html = html.replace("{{CURRENT_DATE}}", current_date)
        html = html.replace("{{DATE}}", current_date)
        html = html.replace("{{FECHA}}", current_date)
        
        html = html.replace("{{VALIDITY_DATE}}", validity_date)
        html = html.replace("{{VIGENCIA}}", validity_date)
        html = html.replace("{{VALIDITY}}", validity_date)
        
        # Totales y pricing con flags condicionales
        pricing = mapped_data.get('pricing', {})
        pricing_config = mapped_data.get('pricing_config', {})  # ✅ NUEVO: Configuraciones detalladas
        
        # ✅ PRICING CONDICIONAL: Usar flags de configuración detallada si están disponibles
        # Prioridad 1: Usar pricing_config (configuraciones de BD)
        # Prioridad 2: Fallback a show_* flags del pricing calculation
        if pricing_config:
            show_coordination = pricing_config.get('coordination_enabled', False)
            show_tax = pricing_config.get('taxes_enabled', False)
            show_cost_per_person = pricing_config.get('cost_per_person_enabled', False)
            logger.info(f"✅ Using pricing_config flags - Coordination: {show_coordination}, Tax: {show_tax}, Cost per person: {show_cost_per_person}")
        else:
            # Fallback a flags del pricing calculation
            show_coordination = pricing.get('show_coordination', False)
            show_tax = pricing.get('show_tax', False)
            show_cost_per_person = pricing.get('show_cost_per_person', False)
            logger.info(f"⚠️ Using fallback pricing flags - Coordination: {show_coordination}, Tax: {show_tax}, Cost per person: {show_cost_per_person}")
        
        # Reemplazos básicos (siempre)
        html = html.replace("{{TOTAL}}", pricing.get('total_formatted', '$0.00'))
        html = html.replace("{{TOTAL_AMOUNT}}", pricing.get('total_formatted', '$0.00'))
        html = html.replace("{{SUBTOTAL}}", pricing.get('subtotal_formatted', '$0.00'))
        
        # Reemplazos condicionales (solo si están activos)
        if show_coordination:
            html = html.replace("{{COORDINATION}}", pricing.get('coordination_formatted', '$0.00'))
            logger.info(f"✅ Coordination enabled: {pricing.get('coordination_formatted', '$0.00')}")
        else:
            html = html.replace("{{COORDINATION}}", "")
            logger.info("⚠️ Coordination disabled - omitting from template")
        
        if show_tax:
            html = html.replace("{{TAX}}", pricing.get('tax_formatted', '$0.00'))
            logger.info(f"✅ Tax enabled: {pricing.get('tax_formatted', '$0.00')}")
        else:
            html = html.replace("{{TAX}}", "")
            logger.info("⚠️ Tax disabled - omitting from template")
        
        if show_cost_per_person:
            html = html.replace("{{COST_PER_PERSON}}", pricing.get('cost_per_person_formatted', '$0.00'))
            logger.info(f"✅ Cost per person enabled: {pricing.get('cost_per_person_formatted', '$0.00')}")
        else:
            html = html.replace("{{COST_PER_PERSON}}", "")
            logger.info("⚠️ Cost per person disabled - omitting from template")
        
        # Generar filas de productos
        products = mapped_data.get('products', [])
        products_html = self._generate_product_rows(products)
        html = html.replace("{{PRODUCT_ROWS}}", products_html)
        
        logger.info(f"✅ Data inserted - {len(products)} products, {html.count('{{')//2} remaining placeholders")
        
        return html
    
    def _generate_product_rows(self, products: List[Dict]) -> str:
        """
        Genera filas HTML de productos (Python puro - SIN AI)
        Formato consistente y predecible
        """
        if not products:
            return '<tr><td colspan="5" style="text-align: center;">No hay productos</td></tr>'
        
        rows = []
        for i, product in enumerate(products, 1):
            nombre = product.get('nombre', 'N/A')
            cantidad = product.get('cantidad', 0)
            unidad = product.get('unidad', 'unidad')
            precio_unitario = product.get('precio_unitario', 0.0)
            total = product.get('total', 0.0)
            
            row = f"""        <tr>
            <td>{i}</td>
            <td>{nombre}</td>
            <td>{cantidad} {unidad}</td>
            <td>${precio_unitario:.2f}</td>
            <td>${total:.2f}</td>
        </tr>"""
            rows.append(row)
        
        logger.info(f"📦 Generated {len(rows)} product rows")
        return "\n".join(rows)
    
    async def regenerate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Regenera HTML (con Python puro siempre genera igual - determinístico)
        Solo vuelve a llamar generate() ya que no hay errores de AI
        
        Args:
            request: {
                "html_template": "...",
                "issues": ["error1", "error2"],  # Se ignoran con Python puro
                "data": {...}
            }
        """
        logger.info(f"🔄 Regenerating (Python puro - issues ignorados, siempre determinístico)")
        
        # Con Python puro, simplemente regeneramos desde cero
        # No hay "errores de interpretación de AI" que corregir
        return await self.generate(request)


# Singleton instance
proposal_generator_agent = ProposalGeneratorAgent()
