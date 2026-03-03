"""
📋 Proposal Prompts - Versión simplificada y funcional
Compatible con proposal_generator.py
"""

import json
from typing import Dict, Any, Optional
from backend.prompts.template_config import (
    build_template_style_instructions,
    get_template_config,
    get_template_html_reference,
)


class ProposalPrompts:
    """Clase que centraliza prompts para generación de propuestas"""

    @staticmethod
    def _format_decision_context(decision_context: Optional[Dict[str, Any]]) -> str:
        if not decision_context:
            return "Sin contexto adicional explícito del usuario."

        must_include = decision_context.get("must_include") or []
        must_avoid = decision_context.get("must_avoid") or []
        open_questions = decision_context.get("open_questions") or []

        summary = {
            "user_goal": decision_context.get("user_goal", ""),
            "tone_preference": decision_context.get("tone_preference", ""),
            "must_include": must_include,
            "must_avoid": must_avoid,
            "commercial_constraints": decision_context.get("commercial_constraints") or [],
            "open_questions": open_questions,
            "history_excerpt": decision_context.get("history_excerpt", ""),
            "recent_user_messages": decision_context.get("recent_user_messages") or [],
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)
    
    @staticmethod
    def get_prompt_with_branding(
        user_id: str,
        logo_endpoint: str,
        company_info: Dict[str, Any],
        rfx_data: Dict[str, Any],
        pricing_data: Dict,
        branding_config: Dict[str, Any] = None,
        template_type: str = "custom",
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Prompt con branding personalizado. Si template_type != 'custom', usa estilo del template."""
        
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
        
        # Determinar colores según template_type o branding del usuario
        use_template = template_type and template_type != "custom"
        
        if use_template:
            tpl_config = get_template_config(template_type)
            tpl_colors = tpl_config.get('colors', {})
            primary_color = tpl_colors.get('primary', '#0e2541')
            table_header_bg = tpl_colors.get('table_header_bg', '#0e2541')
            table_header_text = tpl_colors.get('table_header_text', '#ffffff')
        else:
            primary_color = branding_config.get('primary_color', '#0e2541') if branding_config else '#0e2541'
            table_header_bg = branding_config.get('table_header_bg', '#0e2541') if branding_config else '#0e2541'
            table_header_text = branding_config.get('table_header_text', '#ffffff') if branding_config else '#ffffff'
        
        # Construir bloque de estilo del template
        template_style_block = ""
        template_reference_block = ""
        
        if use_template:
            tpl_name = tpl_config.get('name', template_type)
            template_style_block = build_template_style_instructions(template_type)
            
            ref_html = get_template_html_reference(template_type)
            if ref_html:
                template_reference_block = f"""

HTML DE REFERENCIA DEL TEMPLATE "{tpl_name.upper()}":
Usa la MISMA estructura, colores y layout. Reemplaza datos de ejemplo con los datos REALES.

```html
{ref_html}
```

INSTRUCCIONES SOBRE EL EJEMPLO:
- COPIA la estructura visual (layout, secciones, orden)
- COPIA los colores y estilos CSS exactos
- REEMPLAZA todos los datos de ejemplo con los datos reales de abajo
- NO copies los datos de ejemplo literalmente
- NO cambies los colores ni el estilo visual"""
        
        # Construir bloque de empresa solo si hay nombre configurado
        company_name = company_info.get('name', '')
        if company_name:
            empresa_block = f"""EMPRESA:
- Nombre: {company_name}
- Dirección: {company_info.get('address', '')}
- Teléfono: {company_info.get('phone', '')}
- Email: {company_info.get('email', '')}"""
        else:
            empresa_block = "EMPRESA: No configurada (NO incluir nombre de empresa en el header, solo mostrar datos del cliente)"

        decision_context_block = ProposalPrompts._format_decision_context(decision_context)
        requirements = rfx_data.get("requirements", "")
        location = rfx_data.get("location", "")
        delivery_date = rfx_data.get("delivery_date", "")
        
        prompt = f"""Genera un presupuesto HTML profesional con el siguiente contenido:
{template_style_block}
{empresa_block}

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

CONTEXTO OPERATIVO DEL RFX:
- Requerimientos detectados: {requirements}
- Ubicación de entrega/evento: {location}
- Fecha de entrega/evento: {delivery_date}

CONTEXTO DE DECISIÓN (USUARIO + CHAT):
{decision_context_block}

BRANDING:
{'- Logo: ' + logo_endpoint if logo_endpoint else '- Sin logo configurado (NO incluir ningún logo)'}
- Color primario: {primary_color}
- Header tabla: {table_header_bg}
- Texto header: {table_header_text}
{template_reference_block}

INSTRUCCIONES:
PRIORIDAD DE DECISIÓN (OBLIGATORIA):
1. Cumplir intención, restricciones y mensajes adicionales del usuario.
2. Mantener coherencia comercial y operativa (no inventar condiciones no solicitadas).
3. Aplicar estilo visual/branding.

SECUENCIA DE RAZONAMIENTO (INTERNA):
A) Identifica objetivo de propuesta y restricciones obligatorias.
B) Decide qué destacar, qué omitir y qué supuestos mínimos usar.
C) Genera HTML final alineado al punto A/B.

REGLAS:
1. HTML completo con DOCTYPE, head, style y body.
2. {'Logo con altura 80-120px (NO duplicar nombre empresa).' if logo_endpoint else 'NO incluir ningún logo ni imagen de empresa.'}
3. Usar colores del branding/template consistentemente.
4. Tabla profesional con todos los productos.
5. Espaciado profesional (30px entre secciones).
6. Diseño limpio y proporcional.
7. Solo mostrar coordinación/impuestos si están activos.
8. Si falta un dato crítico, NO inventar; dejar comentario HTML: <!-- DATO_PENDIENTE: ... -->
{'9. Seguir EXACTAMENTE el estilo del template ' + tpl_config.get('name', '') + ' descrito arriba.' if use_template else ''}

IMPORTANTE: Responde SOLO con HTML, sin ```html``` al inicio o final."""

        return prompt
    
    @staticmethod
    def get_prompt_default(
        company_info: Dict[str, Any],
        rfx_data: Dict[str, Any],
        pricing_data: Dict,
        template_type: str = "custom",
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Prompt sin branding personalizado. Si template_type != 'custom', usa estilo del template."""
        
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
        
        # Determinar si usar template predefinido o estilo genérico
        use_template = template_type and template_type != "custom"
        
        template_style_block = ""
        template_reference_block = ""
        company_name = company_info.get('name', '')
        design_block = f"""DISEÑO:
- Color primario: #2c5f7c
- Diseño profesional estándar
- Sin logo (no hay logo configurado, NO incluir ningún logo ni imagen)"""
        extra_instruction = ""
        
        if use_template:
            tpl_config = get_template_config(template_type)
            tpl_name = tpl_config.get('name', template_type)
            tpl_colors = tpl_config.get('colors', {})
            template_style_block = build_template_style_instructions(template_type)
            
            design_block = f"""DISEÑO:
- Color primario: {tpl_colors.get('primary', '#2c5f7c')}
- Estilo: {tpl_name} ({tpl_config.get('tone', '')})
- Sin logo (no hay logo configurado, NO incluir ningún logo ni imagen)"""
            extra_instruction = f"\n8. Seguir EXACTAMENTE el estilo del template {tpl_name} descrito arriba"
            
            ref_html = get_template_html_reference(template_type)
            if ref_html:
                template_reference_block = f"""

HTML DE REFERENCIA DEL TEMPLATE "{tpl_name.upper()}":
Usa la MISMA estructura, colores y layout. Reemplaza datos de ejemplo con los datos REALES.

```html
{ref_html}
```

INSTRUCCIONES SOBRE EL EJEMPLO:
- COPIA la estructura visual (layout, secciones, orden)
- COPIA los colores y estilos CSS exactos
- REEMPLAZA todos los datos de ejemplo con los datos reales
- NO copies los datos de ejemplo literalmente
- NO cambies los colores ni el estilo visual"""
        
        # Construir bloque de empresa solo si hay nombre configurado
        company_name_val = company_info.get('name', '')
        if company_name_val:
            empresa_block = f"""EMPRESA:
- Nombre: {company_name_val}
- Dirección: {company_info.get('address', '')}
- Teléfono: {company_info.get('phone', '')}
- Email: {company_info.get('email', '')}"""
        else:
            empresa_block = "EMPRESA: No configurada (NO incluir nombre de empresa en el header, solo mostrar datos del cliente)"

        decision_context_block = ProposalPrompts._format_decision_context(decision_context)
        requirements = rfx_data.get("requirements", "")
        location = rfx_data.get("location", "")
        delivery_date = rfx_data.get("delivery_date", "")
        
        prompt = f"""Genera un presupuesto HTML profesional con el siguiente contenido:
{template_style_block}
{empresa_block}

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

CONTEXTO OPERATIVO DEL RFX:
- Requerimientos detectados: {requirements}
- Ubicación de entrega/evento: {location}
- Fecha de entrega/evento: {delivery_date}

CONTEXTO DE DECISIÓN (USUARIO + CHAT):
{decision_context_block}

{design_block}
{template_reference_block}

INSTRUCCIONES:
PRIORIDAD DE DECISIÓN (OBLIGATORIA):
1. Cumplir intención, restricciones y mensajes adicionales del usuario.
2. Mantener coherencia comercial y operativa.
3. Aplicar diseño visual.

SECUENCIA DE RAZONAMIENTO (INTERNA):
A) Identifica objetivo y restricciones.
B) Define decisiones de contenido (qué enfatizar/omitir).
C) Genera HTML.

REGLAS:
1. HTML completo con DOCTYPE, head, style y body.
2. Diseño limpio y profesional.
3. Tabla con todos los productos.
4. Espaciado profesional (30px entre secciones).
5. Solo mostrar coordinación/impuestos si están activos.
6. NO incluir ningún logo ni imagen de empresa (no hay logo configurado).
7. Usar colores del template/branding consistentemente.
8. Si falta un dato crítico, NO inventar; dejar comentario HTML: <!-- DATO_PENDIENTE: ... -->{extra_instruction}

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
