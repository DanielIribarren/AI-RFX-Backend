"""
📋 Proposal Prompts - Versión simplificada y funcional
Compatible con proposal_generator.py
"""

from typing import Dict, Any


class ProposalPrompts:
    """Clase que centraliza prompts para generación de propuestas"""
    
    @staticmethod
    def get_prompt_with_branding(
        user_id: str,
        logo_endpoint: str,
        company_info: Dict[str, Any],
        rfx_data: Dict[str, Any],
        pricing_data: Dict,
        branding_config: Dict[str, Any] = None
    ) -> str:
        """Prompt con branding personalizado"""
        
        # Extraer datos
        client_name = rfx_data.get('client_name', 'Cliente')
        solicitud = rfx_data.get('solicitud', 'Solicitud de presupuesto')
        products = rfx_data.get('products', [])
        
        # Formatear productos
        products_text = "\n".join([
            f"{i+1}. {p.get('nombre', 'N/A')} - Qty: {p.get('cantidad', 0)} - ${p.get('precio_unitario', 0):.2f}"
            for i, p in enumerate(products)
        ])
        
        # Extraer pricing
        subtotal = pricing_data.get('subtotal_formatted', '$0.00')
        coordination = pricing_data.get('coordination_formatted', '$0.00')
        show_coordination = pricing_data.get('show_coordination', False)
        tax = pricing_data.get('tax_formatted', '$0.00')
        show_tax = pricing_data.get('show_tax', False)
        total = pricing_data.get('total_formatted', '$0.00')
        
        # Extraer colores
        primary_color = branding_config.get('primary_color', '#0e2541') if branding_config else '#0e2541'
        table_header_bg = branding_config.get('table_header_bg', '#0e2541') if branding_config else '#0e2541'
        table_header_text = branding_config.get('table_header_text', '#ffffff') if branding_config else '#ffffff'
        
        prompt = f"""Genera un presupuesto HTML profesional con el siguiente contenido:

EMPRESA:
- Nombre: {company_info.get('name', 'Sabra Corporation')}
- Dirección: {company_info.get('address', '')}
- Teléfono: {company_info.get('phone', '')}
- Email: {company_info.get('email', '')}

CLIENTE:
- Nombre: {client_name}
- Solicitud: {solicitud}

PRODUCTOS:
{products_text}

PRICING:
- Subtotal: {subtotal}
{'- Coordinación: ' + coordination if show_coordination else ''}
{'- Impuestos: ' + tax if show_tax else ''}
- TOTAL: {total}

BRANDING:
- Logo: {logo_endpoint}
- Color primario: {primary_color}
- Header tabla: {table_header_bg}
- Texto header: {table_header_text}

INSTRUCCIONES:
1. HTML completo con DOCTYPE, head, style y body
2. Logo con altura 80-120px (NO duplicar nombre empresa)
3. Usar colores del branding consistentemente
4. Tabla profesional con todos los productos
5. Espaciado profesional (30px entre secciones)
6. Diseño limpio y proporcional
7. Solo mostrar coordinación/impuestos si están activos

IMPORTANTE: Responde SOLO con HTML, sin ```html``` al inicio o final."""

        return prompt
    
    @staticmethod
    def get_prompt_default(
        company_info: Dict[str, Any],
        rfx_data: Dict[str, Any],
        pricing_data: Dict
    ) -> str:
        """Prompt sin branding personalizado"""
        
        # Extraer datos
        client_name = rfx_data.get('client_name', 'Cliente')
        solicitud = rfx_data.get('solicitud', 'Solicitud de presupuesto')
        products = rfx_data.get('products', [])
        
        # Formatear productos
        products_text = "\n".join([
            f"{i+1}. {p.get('nombre', 'N/A')} - Qty: {p.get('cantidad', 0)} - ${p.get('precio_unitario', 0):.2f}"
            for i, p in enumerate(products)
        ])
        
        # Extraer pricing
        subtotal = pricing_data.get('subtotal_formatted', '$0.00')
        coordination = pricing_data.get('coordination_formatted', '$0.00')
        show_coordination = pricing_data.get('show_coordination', False)
        tax = pricing_data.get('tax_formatted', '$0.00')
        show_tax = pricing_data.get('show_tax', False)
        total = pricing_data.get('total_formatted', '$0.00')
        
        prompt = f"""Genera un presupuesto HTML profesional con el siguiente contenido:

EMPRESA:
- Nombre: {company_info.get('name', 'Sabra Corporation')}
- Dirección: {company_info.get('address', '')}
- Teléfono: {company_info.get('phone', '')}
- Email: {company_info.get('email', '')}

CLIENTE:
- Nombre: {client_name}
- Solicitud: {solicitud}

PRODUCTOS:
{products_text}

PRICING:
- Subtotal: {subtotal}
{'- Coordinación: ' + coordination if show_coordination else ''}
{'- Impuestos: ' + tax if show_tax else ''}
- TOTAL: {total}

DISEÑO:
- Color primario: #2c5f7c
- Diseño profesional estándar
- Logo por defecto de Sabra

INSTRUCCIONES:
1. HTML completo con DOCTYPE, head, style y body
2. Diseño limpio y profesional
3. Tabla con todos los productos
4. Espaciado profesional (30px entre secciones)
5. Solo mostrar coordinación/impuestos si están activos

IMPORTANTE: Responde SOLO con HTML, sin ```html``` al inicio o final."""

        return prompt
    
    @staticmethod
    def get_retry_prompt(
        original_html: str,
        validation_issues: list,
        rfx_data: Dict[str, Any],
        pricing_data: Dict,
        branding_config: Dict[str, Any] = None
    ) -> str:
        """Prompt para retry con correcciones"""
        
        issues_text = "\n".join([f"- {issue}" for issue in validation_issues])
        
        prompt = f"""El HTML generado tiene los siguientes problemas:

{issues_text}

Por favor, corrige el HTML manteniendo:
1. Toda la información de productos y pricing
2. El branding y colores especificados
3. Diseño profesional

HTML ORIGINAL:
{original_html[:2000]}...

Genera el HTML CORREGIDO completo, sin ```html``` al inicio o final."""

        return prompt
