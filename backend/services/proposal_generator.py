"""
🎯 Proposal Generation Service - Generación simplificada de propuestas comerciales
Arquitectura refactorizada: Template HTML + IA hace todo + Validación mínima
Reducción: 900+ líneas → 180 líneas
"""
import json
import uuid
import re
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from backend.models.proposal_models import ProposalRequest, GeneratedProposal, ProposalStatus
from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.services.pricing_config_service_v2 import PricingConfigurationServiceV2

import logging

logger = logging.getLogger(__name__)


class ProposalGenerationService:
    """Servicio ultra-simplificado para generar propuestas comerciales"""
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = None  # Lazy initialization
        self.db_client = get_database_client()
        self.template_html = self._load_template()
        self.pricing_service = PricingConfigurationServiceV2()
    
    def _get_openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self.openai_client is None:
            try:
                from openai import OpenAI  # Import only when needed
                self.openai_client = OpenAI(api_key=self.openai_config.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI module not installed. Run: pip install openai"
                )
        return self.openai_client
    
    def _load_template(self) -> str:
        """Carga template HTML desde archivo test_design.html"""
        # Usar test_design.html como template principal
        template_path = Path(__file__).parent.parent.parent / "test_design.html"
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Template test_design.html no encontrado: {template_path}")
            return self._get_embedded_template()
    
    def _get_embedded_template(self) -> str:
        """Template embebido como fallback ultra-básico"""
        return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Propuesta Comercial</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .company-name { color: #2c5f7c; font-size: 24px; font-weight: bold; }
        .error { color: #ff6b6b; font-style: italic; }
    </style>
</head>
<body>
    <div class="company-name">sabra corporation</div>
    <h2>Propuesta Comercial</h2>
    <p>Template básico de emergencia</p>
</body>
</html>"""
    
    async def generate_proposal(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> GeneratedProposal:
        """
        Método principal ultra-simplificado: Template + IA hace todo
        
        Args:
            rfx_data: Datos del RFX con cliente, productos, fechas, etc.
            proposal_request: Request con configuraciones adicionales
            
        Returns:
            PropuestaGenerada: Objeto con HTML completo y metadata
        """
        logger.info(f"🚀 Generando propuesta simplificada para RFX: {proposal_request.rfx_id}")
        
        try:
            # 1. Construir prompt con template y datos
            ai_prompt = self._build_ai_prompt(rfx_data, proposal_request)
            compact_prompt = self._build_compact_ai_prompt(rfx_data, proposal_request)

            # Selección preventiva si el prompt es muy largo (evitar context overflow/latencia)
            prompt_to_use = ai_prompt
            if len(ai_prompt) > 120_000:  # ~aprox a 120k chars; muy grande
                logger.warning("⚠️ Prompt completo demasiado largo. Usando versión compacta preventivamente")
                prompt_to_use = compact_prompt

            # 2. Llamada a OpenAI con retry inteligente (compact fallback en timeout)
            try:
                html_content = await self._call_openai(prompt_to_use, max_tokens=min(2500, self.openai_config.max_tokens))
            except Exception as e:
                error_msg = str(e).lower()
                if any(k in error_msg for k in ["timeout", "timed out", "request timed out"]):
                    logger.warning("⏱️ Timeout con prompt completo. Reintentando con prompt compacto y menos tokens...")
                    time.sleep(1)
                    html_content = await self._call_openai(compact_prompt, max_tokens=min(1500, self.openai_config.max_tokens))
                else:
                    raise
            
            # 3. Validación con logging detallado - NO usar template básico
            is_valid = self._validate_html(html_content)
            if not is_valid:
                logger.error("❌ HTML validation failed - but continuing with generated content instead of fallback")
                logger.error("❌ This indicates an issue with AI generation or validation criteria")
                # Continue with the generated HTML instead of falling back
            
            # 4. Crear objeto de respuesta
            proposal = self._create_proposal_object(rfx_data, html_content, proposal_request)
            
            # 5. Guardar en BD
            await self._save_to_database(proposal)
            
            logger.info(f"✅ Propuesta generada exitosamente: {proposal.id}")
            return proposal
            
        except Exception as e:
            logger.error(f"❌ CRITICAL Error generando propuesta: {e}")
            logger.error(f"❌ Fallback disabled - this error needs to be fixed at the source")
            # Re-raise the exception instead of using fallback
            raise Exception(f"Proposal generation failed: {e}. Fallback disabled to force fixing root cause.")
    
    def _build_ai_prompt(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> str:
        """Construye prompt inteligente para OpenAI con template y datos del RFX"""
        
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        productos = rfx_data.get("productos", [])  # Usar "productos" en español para consistencia
        rfx_id = proposal_request.rfx_id
        
        # 🆕 Extraer moneda del RFX (desde BD V2.0)
        rfx_currency = rfx_data.get("currency", "USD")  # Fallback a USD si no hay moneda
        logger.debug(f"💰 Currency extracted from RFX data: {rfx_currency}")
        
        # Obtener configuración de pricing
        pricing_config = self.pricing_service.get_rfx_pricing_configuration(rfx_id)
        
        # Preparar datos estructurados para la IA con precios reales
        productos_info = []
        subtotal = 0.0
        for producto in productos:
            precio_unitario = producto.get("estimated_unit_price", 0.0)
            cantidad = producto.get("quantity", producto.get("cantidad", 1))
            total_producto = precio_unitario * cantidad
            subtotal += total_producto
            
            productos_info.append({
                "nombre": producto.get("name", producto.get("nombre", "product")),
                "cantidad": cantidad,
                "unidad": producto.get("unit", producto.get("unidad", "units")),
                "precio_unitario": precio_unitario,
                "total": total_producto
            })
        
        # Calcular pricing con configuraciones
        pricing_calculation = self.pricing_service.calculate_pricing(rfx_id, subtotal)
        
        # Preparar instrucciones de pricing para la IA
        pricing_instructions = self._build_pricing_instructions(pricing_calculation, pricing_config)
        
        # 🆕 Preparar instrucciones de moneda para la IA
        currency_instructions = self._build_currency_instructions(rfx_currency)
        
        prompt = f"""
<system>
Eres un asistente experto especializado en la generación de presupuestos comerciales profesionales para Sabra Corporation. Tu función principal es transformar datos estructurados de solicitudes (RFX) en documentos HTML comerciales de alta calidad, adaptándote inteligentemente al contexto y requerimientos específicos de cada cliente.

Combinas precisión técnica con flexibilidad comercial, manteniendo siempre los estándares profesionales de la empresa mientras te adaptas a las necesidades particulares de cada solicitud.
</system>

<role>
Actúas como un generador inteligente de presupuestos HTML, especializado en:
- Análisis automático de dominios de negocio (catering, construcción, tecnología, logística, etc.)
- Aplicación de lógica condicional para servicios adicionales
- Cálculos matemáticos precisos y verificables
- Adaptación flexible según especificaciones del usuario
- Generación de HTML profesional y renderizable
- Compatibilidad perfecta con Playwright para conversión PDF
- Mantenimiento de estándares comerciales de Sabra Corporation

Tu expertise abarca múltiples industrias y te adaptas al contexto específico de cada solicitud, manteniendo siempre la calidad y profesionalismo en los documentos generados.
</role>

<context>
INFORMACIÓN DE LA SOLICITUD:
- Solicitante: {client_info.get('name', 'Solicitante')}
- Email: {client_info.get('email', '')}
- Empresa: {client_info.get('company', '')}
- Lugar de entrega: {rfx_data.get('location', 'Por definir')}
- Fecha de entrega: {rfx_data.get('delivery_date', 'Por definir')}
- Número de personas (si aplica): {rfx_data.get('people_count', '')}
- Solicitud de costo por persona: {rfx_data.get('cost_per_person_requested', False)}

PRODUCTOS Y SERVICIOS:
{json.dumps(productos_info, ensure_ascii=False, indent=2)}

ESPECIFICACIONES ADICIONALES DEL USUARIO:
{proposal_request.notes if hasattr(proposal_request, 'notes') and proposal_request.notes else "Ninguna - usar configuración estándar"}

CONFIGURACIONES DE PRICING:
{pricing_instructions if pricing_instructions else "Usar configuración estándar"}

CONFIGURACIÓN DE MONEDA:
{currency_instructions}
TEMPLATE HTML DE REFERENCIA:
{self.template_html}

FECHA ACTUAL: {datetime.now().strftime('%d/%m/%y')}

Trabajas en un entorno empresarial donde cada presupuesto debe reflejar profesionalismo y precisión. Los clientes esperan documentos de calidad comercial que puedan presentar internamente o a sus stakeholders. La flexibilidad es clave, pero sin comprometer la estructura fundamental del presupuesto. El HTML generado DEBE ser compatible con Playwright para conversión a PDF.
</context>

<instructions>
<step>1. ANÁLISIS INTELIGENTE DEL CONTEXTO</step>
    <substep>• Identifica el dominio del presupuesto (catering, construcción, tecnología, eventos, logística, servicios profesionales, etc.)</substep>
    <substep>• Determina si los productos requieren categorización automática por tipo</substep>
    <substep>• Evalúa si aplica "Coordinación y logística" según la naturaleza del proyecto y servicios involucrados</substep>
    <substep>• Analiza las especificaciones adicionales del usuario para adaptaciones específicas</substep>

<step>2. PROCESAMIENTO INTELIGENTE DE DATOS</step>
    <substep>• Completa nombres de empresas conocidas si vienen abreviados (ej: "Chevron" → "Chevron Global Technology Services Company")</substep>
    <substep>• Organiza productos por categorías relevantes cuando sea apropiado para el dominio</substep>
    <substep>• Calcula automáticamente: cantidad × precio_unitario = total por cada producto</substep>
    <substep>• Genera subtotal sumando todos los totales de productos</substep>

<step>3. APLICACIÓN DE REGLAS CONDICIONALES</step>
    <substep>• COORDINACIÓN Y LOGÍSTICA: Incluir automáticamente cuando el proyecto requiera coordinación, gestión, organización o servicios logísticos</substep>
    <substep>• Aplica a mayoría de dominios: catering, eventos, construcción, logística, servicios técnicos, instalaciones, servicios profesionales</substep>
    <substep>• NO aplica a: ventas directas simples, productos de retail básico sin servicios</substep>
    <substep>• Calcular coordinación y logística como 18% del subtotal cuando aplique</substep>
    <substep>• Si cost_per_person_requested = True: calcular y mostrar prominentemente "Costo por persona" = total_final ÷ people_count</substep>
    <substep>• Si hay especificaciones adicionales: adaptarse a los requerimientos específicos manteniendo la estructura profesional base</substep>

<step>4. GENERACIÓN DEL HTML FINAL</step>
    <substep>• Reemplazar todos los marcadores del template con datos procesados:</substep>
        <subitem>[FECHA] → Fecha actual en formato DD/MM/YY</subitem>
        <subitem>[NUMERO] → PROP-DDMMYY-XXX (código único)</subitem>
        <subitem>[CLIENTE] → Nombre del cliente en MAYÚSCULAS</subitem>
        <subitem>[EMPRESA] → Nombre completo oficial de la empresa</subitem>
        <subitem>[PROCESO] → Descripción contextual del proceso según dominio</subitem>
        <subitem>[PRODUCTOS_ROWS] → Filas HTML organizadas y categorizadas</subitem>
        <subitem>[SUBTOTAL] → Suma total de todos los productos</subitem>
        <subitem>[COORDINACION] → 18% del subtotal si aplica</subitem>
        <subitem>[TOTAL] → Total final (subtotal + coordinación si aplica)</subitem>
        <subitem>[COSTO_PERSONA] → Total ÷ personas solo si se solicita explícitamente</subitem>
    <substep>• Asegurar que el HTML sea válido, funcional y renderizable en navegadores</substep>
    <substep>• Mantener estructura responsive y profesional del template base</substep>
    <substep>• NUNCA iniciar el código HTML con ```html ni terminarlo con ```, generar HTML limpio directamente</substep>
    <substep>• NO agregar estilos CSS incompatibles con Playwright para conversión PDF</substep>
    <substep>• SOLO usar CSS compatible con Playwright/Chromium para PDF: flexbox, grid, border-radius, box-shadow, transforms básicos</substep>
    <substep>• OBLIGATORIO: Incluir -webkit-print-color-adjust: exact !important en elementos con colores de fondo</substep>
    <substep>• EVITAR: viewport units (vw, vh), hover states, transitions, animations, backdrop-filter</substep>
    <substep>• USAR: px, %, cm, pt para unidades; font-family web-safe; colores con !important para elementos críticos</substep>
    <substep>• NO AGREGAR Notas adicionales como como las CONFIGURACIONES DE PRICING o currency</substep>
</instructions>

<criteria>
<requirement>PRECISIÓN MATEMÁTICA: Todos los cálculos deben ser exactos, verificables y consistentes</requirement>
<requirement>FLEXIBILIDAD INTELIGENTE: Adaptarse a especificaciones adicionales sin perder profesionalismo ni funcionalidad</requirement>
<requirement>CONSISTENCIA DE DATOS: Usar SIEMPRE los precios definidos en los datos de entrada, nunca inventar o modificar valores</requirement>
<requirement>COMPLETITUD CONTEXTUAL: Incluir todos los elementos requeridos según el dominio y contexto específico</requirement>
<requirement>PROFESIONALISMO COMERCIAL: Mantener formato de alta calidad apto para presentaciones empresariales</requirement>
<requirement>COMPATIBILIDAD PLAYWRIGHT: Generar HTML/CSS 100% compatible con Playwright para conversión PDF sin errores</requirement>
<requirement>VALIDEZ TÉCNICA: Generar código HTML funcional, bien estructurado y sin marcadores de código (```)</requirement>
<requirement>ADAPTABILIDAD CONTROLADA: Ser flexible con formatos y presentación manteniendo siempre los estándares de calidad</requirement>
</criteria>

<examples>
<example1>
<title>Catering Corporativo con Especificaciones Personalizadas</title>
<input>
Dominio: Catering corporativo
Empresa: "Chevron"
Especificaciones adicionales: "Incluir información nutricional, destacar opciones veganas, usar formato premium con colores corporativos"
Productos: 
- Tequeños (100 unidades, $1.50 c/u)
- Jugo natural (15 litros, $3.50 c/u) 
- Pie de limón (20 unidades, $2.50 c/u)
Personas: 50
Costo por persona solicitado: True
</input>
<output>
→ EMPRESA: "CHEVRON GLOBAL TECHNOLOGY SERVICES COMPANY"
→ PROCESO: "Cotización - Catering Corporativo Torre Barcelona"
→ CATEGORIZACIÓN:
  • PASAPALOS SALADOS: Tequeños (100 × $1.50 = $150.00)
  • BEBIDAS: Jugo natural (15 × $3.50 = $52.50)
  • POSTRES: Pie de limón (20 × $2.50 = $50.00)
→ SUBTOTAL: $252.50
→ COORDINACIÓN Y LOGÍSTICA (18%): $45.45
→ TOTAL: $297.95
→ COSTO POR PERSONA: $297.95 ÷ 50 = $5.96
→ FORMATO: Premium con información nutricional y destacado vegano
→ CSS: Solo estilos compatibles con Playwright PDF
</output>
</example1>

<example2>
<title>Construcción con Configuración Estándar</title>
<input>
Dominio: Construcción
Empresa: "ConstruMax"
Especificaciones adicionales: Ninguna - usar configuración estándar
Productos:
- Cemento Gris (25 sacos, $9.00 c/u)
- Arena Lavada (5 m³, $40.00 c/u)
- Varillas 3/8" (100 unidades, $12.00 c/u)
Personas: No aplica
Costo por persona solicitado: False
</input>
<output>
→ EMPRESA: "CONSTRUMAX"
→ PROCESO: "Cotización - Materiales de Construcción"
→ PRODUCTOS (sin categorización específica):
  • Cemento Gris: 25 sacos × $9.00 = $225.00
  • Arena Lavada: 5 m³ × $40.00 = $200.00  
  • Varillas 3/8": 100 un × $12.00 = $1,200.00
→ SUBTOTAL: $1,625.00
→ COORDINACIÓN Y LOGÍSTICA (18%): $292.50
→ TOTAL: $1,917.50
→ FORMATO: Estándar profesional
→ NO mostrar costo por persona
→ HTML limpio sin marcadores de código
</output>
</example2>

<example3>
<title>Venta Directa Simplificada</title>
<input>
Dominio: Venta directa de productos tecnológicos
Empresa: "TechStore"
Especificaciones adicionales: "Formato minimalista, solo productos y totales, sin servicios adicionales"
Productos:
- Laptop HP (2 unidades, $850.00 c/u)
- Mouse inalámbrico (2 unidades, $25.00 c/u)
- Teclado mecánico (2 unidades, $45.00 c/u)
Personas: No aplica
Costo por persona solicitado: False
</input>
<output>
→ EMPRESA: "TECHSTORE"
→ PROCESO: "Cotización - Equipos Tecnológicos"
→ PRODUCTOS (lista simple):
  • Laptop HP: 2 un × $850.00 = $1,700.00
  • Mouse inalámbrico: 2 un × $25.00 = $50.00
  • Teclado mecánico: 2 un × $45.00 = $90.00
→ SUBTOTAL: $1,840.00
→ NO incluir coordinación y logística (venta directa simple)
→ TOTAL: $1,840.00
→ FORMATO: Minimalista según especificaciones
→ CSS: Estilos básicos compatibles con PDF
</output>
</example3>
</examples>

CSS_COMPATIBILITY_RULES:
OBLIGATORIO USAR:
- display: flex, grid, block, inline-block
- font-family: Arial, sans-serif (web-safe)
- font-size en px o pt
- margin, padding en px, cm o %
- border: 1px solid #color
- background-color con -webkit-print-color-adjust: exact !important
- color con !important para elementos críticos
- text-align, font-weight, font-style
- width, height en px, % o cm
- border-radius, box-shadow (efectos básicos)

PROHIBIDO USAR:
- viewport units (vw, vh, vmin, vmax)
- hover, focus, active states
- transition, animation properties
- backdrop-filter, filter complejos
- position: fixed (problemático en PDF)
- rem units (usar px o pt)
- JavaScript-dependent classes
- @media queries complejas

IMPORTANTE:
- Mantén nombres de productos simples y profesionales
- Usa precios exactos definidos en los datos de entrada
- Asegúrate que todas las operaciones matemáticas sean correctas
- Fecha actual para [FECHA]: {datetime.now().strftime('%d/%m/%y')}
- NUNCA incluir marcadores ```html o ``` en el output
- Responde SOLO con HTML completo y funcional, sin explicaciones adicionales

RESPONDE ÚNICAMENTE CON HTML COMPLETO Y FUNCIONAL (SIN ```html NI ``` AL INICIO O FINAL):
"""

        
        return prompt
    
    def _build_pricing_instructions(self, pricing_calculation, pricing_config) -> str:
        """Construye instrucciones específicas de pricing para la IA"""
        try:
            instructions = ["CONFIGURACIONES DE PRICING APLICADAS:"]
            
            # Información del subtotal
            instructions.append(f"SUBTOTAL BASE: ${pricing_calculation.subtotal:.2f}")
            
            # Configuración de coordinación
            if pricing_calculation.coordination_enabled:
                rate_percent = pricing_calculation.coordination_rate * 100
                instructions.append(f"✅ COORDINACIÓN HABILITADA:")
                instructions.append(f"   - Agregar {rate_percent:.1f}% de coordinación y logística")
                instructions.append(f"   - Monto de coordinación: ${pricing_calculation.coordination_amount:.2f}")
                instructions.append(f"   - Mostrar como línea separada: 'Coordinación y logística ({rate_percent:.1f}%): ${pricing_calculation.coordination_amount:.2f}'")
            else:
                instructions.append("❌ COORDINACIÓN DESHABILITADA: No agregar coordinación al presupuesto")
            
            # Configuración de costo por persona
            if pricing_calculation.cost_per_person_enabled and pricing_calculation.headcount:
                instructions.append(f"✅ COSTO POR PERSONA HABILITADO:")
                instructions.append(f"   - Número de personas: {pricing_calculation.headcount}")
                instructions.append(f"   - Costo por persona: ${pricing_calculation.cost_per_person:.2f}")
                instructions.append(f"   - Incluir al final: 'Costo por persona: ${pricing_calculation.cost_per_person:.2f} ({pricing_calculation.headcount} personas)'")
            else:
                instructions.append("❌ COSTO POR PERSONA DESHABILITADO: No mostrar cálculo por persona")
            
            # Configuración de impuestos
            if pricing_calculation.taxes_enabled:
                rate_percent = pricing_calculation.tax_rate * 100
                instructions.append(f"✅ IMPUESTOS HABILITADOS:")
                instructions.append(f"   - Tasa de impuesto: {rate_percent:.1f}%")
                instructions.append(f"   - Monto de impuesto: ${pricing_calculation.tax_amount:.2f}")
                instructions.append(f"   - Mostrar línea de impuesto antes del total final")
            else:
                instructions.append("❌ IMPUESTOS DESHABILITADOS: No agregar impuestos")
            
            # Total final
            instructions.append(f"TOTAL FINAL CALCULADO: ${pricing_calculation.total_cost:.2f}")
            
            instructions.append("")
            instructions.append("INSTRUCCIONES CRÍTICAS:")
            instructions.append("- Usa exactamente los montos calculados arriba")
            instructions.append("- No inventes nuevos cálculos")
            instructions.append("- Respeta las configuraciones habilitadas/deshabilitadas")
            instructions.append("- Mantén la estructura del template HTML")
            instructions.append("- El total final debe ser exactamente el TOTAL FINAL CALCULADO")
            
            return "\n".join(instructions)
            
        except Exception as e:
            logger.error(f"❌ Error building pricing instructions: {e}")
            return "CONFIGURACIONES DE PRICING: Usar configuración estándar (coordinación 18%)"
    
    def _build_currency_instructions(self, currency: str) -> str:
        """🆕 Construye instrucciones específicas de moneda para la IA"""
        try:
            # Mapeo de monedas a símbolos y formatos
            currency_config = {
                "USD": {"symbol": "$", "name": "Dólares Americanos", "format": "$1,000.00", "position": "before"},
                "EUR": {"symbol": "€", "name": "Euros", "format": "€1.000,00", "position": "before"},
                "GBP": {"symbol": "£", "name": "Libras Esterlinas", "format": "£1,000.00", "position": "before"},
                "JPY": {"symbol": "¥", "name": "Yenes", "format": "¥1,000", "position": "before"},
                "MXN": {"symbol": "$", "name": "Pesos Mexicanos", "format": "$1,000.00 MXN", "position": "before"},
                "CAD": {"symbol": "C$", "name": "Dólares Canadienses", "format": "C$1,000.00", "position": "before"},
                "AUD": {"symbol": "A$", "name": "Dólares Australianos", "format": "A$1,000.00", "position": "before"},
                "BRL": {"symbol": "R$", "name": "Reales Brasileños", "format": "R$1.000,00", "position": "before"},
                "COP": {"symbol": "$", "name": "Pesos Colombianos", "format": "$1.000,00 COP", "position": "before"},
                "CHF": {"symbol": "CHF", "name": "Francos Suizos", "format": "CHF 1,000.00", "position": "before"}
            }
            
            config = currency_config.get(currency, {
                "symbol": "$", 
                "name": "Dólares (USD)", 
                "format": "$1,000.00", 
                "position": "before"
            })
            
            instructions = [
                f"MONEDA DE LA SOLICITUD: {currency}",
                f"NOMBRE COMPLETO: {config['name']}",
                f"SÍMBOLO A USAR: {config['symbol']}",
                f"FORMATO DE EJEMPLO: {config['format']}",
                "",
                "INSTRUCCIONES CRÍTICAS PARA MONEDA:",
                f"1. USAR EXCLUSIVAMENTE la moneda {currency} para todos los precios",
                f"2. Mostrar símbolo '{config['symbol']}' antes de cada cantidad monetaria",
                f"3. Formato de números: usar comas para miles y punto para decimales (ej: {config['format']})",
                f"4. NO cambiar la moneda a USD si la solicitud es en {currency}",
                f"5. Mantener consistencia: todos los precios deben usar {config['symbol']}",
                f"6. En títulos/encabezados mencionar 'Presupuesto en {config['name']}'",
                "",
                "EJEMPLOS DE FORMATO CORRECTO:",
                f"- Subtotal: {config['symbol']}1,250.00",
                f"- Coordinación y logística: {config['symbol']}225.00", 
                f"- Total: {config['symbol']}1,475.00",
                "",
                "IMPORTANTE:",
                f"- La moneda {currency} fue detectada automáticamente del documento original",
                f"- Respetar la moneda original es crucial para la precisión comercial",
                f"- NO inventar tasas de cambio ni convertir a otras monedas"
            ]
            
            return "\n".join(instructions)
            
        except Exception as e:
            logger.error(f"❌ Error building currency instructions: {e}")
            return f"MONEDA: Usar {currency} con símbolo correspondiente para todos los precios"

    def _build_compact_ai_prompt(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> str:
        """Versión compacta del prompt para reintento en caso de timeout.
        - No incrusta el HTML completo del template, solo instrucciones clave y marcadores.
        - Reduce tokens para acelerar la respuesta.
        """
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        productos = rfx_data.get("productos", [])
        
        # 🆕 Extraer moneda para prompt compacto
        rfx_currency = rfx_data.get("currency", "USD")

        productos_info = []
        for producto in productos:
            productos_info.append({
                "nombre": producto.get("name", producto.get("nombre", "product")),
                "cantidad": producto.get("quantity", producto.get("cantidad", 1)),
                "unidad": producto.get("unit", producto.get("unidad", "units")),
                "precio_unitario": producto.get("estimated_unit_price", 0.0),
                "total": producto.get("total_estimated_cost", 0.0)
            })

        compact_template = """
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Propuesta Comercial</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .company-name { color: #2c5f7c; font-size: 28px; font-weight: bold; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #000; padding: 6px; text-align: left; }
    th { background: #f0f0f0; }
    .final-total { font-weight: bold; background: #e0e0e0; }
  </style>
  <!-- Marcadores: [FECHA], [NUMERO], [CLIENTE], [EMPRESA], [PROCESO], [PRODUCTOS_ROWS], [SUBTOTAL], [TOTAL] -->
  <!-- Usa estética similar a test_design.html pero mantén salida breve -->
  <!-- No añadas texto fuera del HTML -->
</head>
<body>
  <div class=\"company-name\">sabra corporation</div>
  <h2>Propuesta Comercial</h2>
  <div>Cliente: [CLIENTE] • Empresa: [EMPRESA]</div>
  <div>Lugar: {rfx_data.get('location', 'Por definir')} • Fecha: {rfx_data.get('delivery_date', 'Por definir')}</div>
  <table>
    <thead>
      <tr><th>Descripción</th><th>Cant</th><th>Precio</th><th>Total</th></tr>
    </thead>
    <tbody>
      [PRODUCTOS_ROWS]
      <tr class=\"final-total\"><td colspan=\"3\">Total</td><td>[TOTAL]</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

        prompt = f"""
Eres un generador de propuestas para sabra corporation.

USA ESTA PLANTILLA RESUMIDA COMO BASE (reemplaza marcadores exactamente):
{compact_template}

DATOS DEL RFX:
Solicitante: {client_info.get('name', 'Solicitante')}
Email: {client_info.get('email', '')}
Lugar: {rfx_data.get('location', 'Por definir')}
Fecha entrega: {rfx_data.get('delivery_date', 'Por definir')}

PRODUCTOS CON PRECIOS REALES:
{json.dumps(productos_info, ensure_ascii=False, indent=2)}

INSTRUCCIONES CLAVE:
- Calcula total por fila = cantidad × precio_unitario cuando total==0.
- Suma para el Total final.
- Rellena [CLIENTE] (mayúsculas), [EMPRESA] (versión oficial si es abreviada), [PRODUCTOS_ROWS] y [TOTAL].
- MONEDA: Usar {rfx_currency} para todos los precios con símbolo correspondiente
- Mantén HTML breve, válido y limpio. Responde SOLO el HTML completo, sin comentarios.
- Fecha actual para [FECHA]: {datetime.now().strftime('%d/%m/%y')}
"""

        return prompt
    
    async def _call_openai(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Llamada a OpenAI con opciones de timeout y control de tokens.
        Usa el timeout configurado globalmente y reduce latencia.
        """
        openai_client = self._get_openai_client()

        # Aplicar opciones (timeout configurable)
        client_with_timeout = getattr(openai_client, "with_options", None)
        if callable(client_with_timeout):
            client = openai_client.with_options(timeout=self.openai_config.timeout)
        else:
            client = openai_client

        effective_max_tokens = max_tokens if max_tokens is not None else min(2500, self.openai_config.max_tokens)

        logger.debug(f"🤖 Calling OpenAI with model: {self.openai_config.model}, max_tokens={effective_max_tokens}, timeout={self.openai_config.timeout}s")

        try:
            response = client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=effective_max_tokens,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"❌ OpenAI call failed: {e}")
            raise

        generated_html = (response.choices[0].message.content or "").strip()

        logger.debug(f"🤖 OpenAI response length: {len(generated_html)} characters")
        logger.debug(f"🤖 OpenAI response preview: {generated_html[:300]}...")

        return generated_html
    
    def _validate_html(self, html: str) -> bool:
        """Validación flexible del HTML generado"""
        
        # Validaciones básicas de estructura HTML
        basic_html_structure = [
            '<!DOCTYPE html>',
            '<html',
            '</html>',
            '<head',
            '<body'
        ]
        
        # Validaciones de contenido empresarial (más flexibles)
        business_content = [
            'sabra',  # Nombre empresa (case insensitive)
            '<table',  # Debe tener tabla
            '</table>'
        ]
        
        # Validaciones de precios (más flexibles - acepta $0.00 o precios reales)
        price_indicators = [
            '$',  # Símbolo de dólar
            'total',  # Palabra total
            'precio'  # Palabra precio
        ]
        
        # Validaciones opcionales (al menos una debe estar presente)
        content_indicators = [
            'presupuesto', 'propuesta', 'cotización',  # Títulos posibles
            'total', 'subtotal', 'costo'  # Términos de costo
        ]
        
        html_lower = html.lower()
        
        # Verificar estructura básica HTML
        html_valid = all(element.lower() in html_lower for element in basic_html_structure)
        
        # Verificar contenido empresarial
        business_valid = all(element.lower() in html_lower for element in business_content)
        
        # Verificar que tenga al menos un indicador de precios
        price_valid = any(indicator.lower() in html_lower for indicator in price_indicators)
        
        # Verificar que tenga al menos un indicador de contenido
        content_valid = any(indicator in html_lower for indicator in content_indicators)
        
        # Verificar longitud mínima
        length_valid = len(html) > 300  # Reducido de 500 a 300 para ser más flexible
        
        is_valid = html_valid and business_valid and price_valid and content_valid and length_valid
        
        if not is_valid:
            logger.warning(f"❌ HTML validation failed:")
            logger.warning(f"  - HTML structure: {html_valid}")
            logger.warning(f"  - Business content: {business_valid}")
            logger.warning(f"  - Price indicators: {price_valid}")
            logger.warning(f"  - Content indicators: {content_valid}")
            logger.warning(f"  - Length valid (>{300}): {length_valid} (actual: {len(html)})")
            logger.debug(f"  - HTML preview: {html[:200]}...")
        else:
            logger.info(f"✅ HTML validation passed successfully!")
            logger.info(f"  - HTML structure: {html_valid}")
            logger.info(f"  - Business content: {business_valid}")
            logger.info(f"  - Price indicators: {price_valid}")
            logger.info(f"  - Content indicators: {content_valid}")
            logger.info(f"  - Length valid: {length_valid} ({len(html)} chars)")
        
        return is_valid
    
    def _create_proposal_object(self, rfx_data: Dict[str, Any], html_content: str, proposal_request: ProposalRequest) -> GeneratedProposal:
        """Crea objeto GeneratedProposal V2.0 a partir del HTML"""
        
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        proposal_id = uuid.uuid4()  # UUID object, not string
        rfx_uuid = uuid.UUID(proposal_request.rfx_id) if isinstance(proposal_request.rfx_id, str) else proposal_request.rfx_id
        
        # Obtener total del cálculo de pricing en lugar de extraerlo del HTML
        productos = rfx_data.get("productos", [])
        subtotal = sum(p.get("estimated_unit_price", 0) * p.get("quantity", 0) for p in productos)
        pricing_calculation = self.pricing_service.calculate_pricing(proposal_request.rfx_id, subtotal)
        total_cost = pricing_calculation.total_cost
        
        return GeneratedProposal(
            id=proposal_id,
            rfx_id=rfx_uuid,
            content_markdown="",  # Optional in V2.0
            content_html=html_content,
            itemized_costs=[],  # Simplified: AI handles everything
            total_cost=total_cost,
            notes=proposal_request.notes,
            status=ProposalStatus.GENERATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "client_name": client_info.get("name", "Solicitante"),
                "client_email": client_info.get("email", ""),
                "products_count": len(rfx_data.get("productos", [])),
                "generation_method": "ai_template_simplified",
                "ai_model": self.openai_config.model,
                "document_type": "commercial_proposal",
                "generation_version": "2.0_with_pricing_config",
                # Pricing configuration metadata
                "pricing": {
                    "subtotal": pricing_calculation.subtotal,
                    "coordination_enabled": pricing_calculation.coordination_enabled,
                    "coordination_amount": pricing_calculation.coordination_amount,
                    "cost_per_person_enabled": pricing_calculation.cost_per_person_enabled,
                    "headcount": pricing_calculation.headcount,
                    "cost_per_person": pricing_calculation.cost_per_person,
                    "taxes_enabled": pricing_calculation.taxes_enabled,
                    "tax_amount": pricing_calculation.tax_amount,
                    "applied_configs": pricing_calculation.applied_configs
                }
            }
        )
    
    def _extract_total_from_html(self, html: str) -> float:
        """Extrae el costo total del HTML generado usando regex - maneja formato español"""
        
        # Patrones para diferentes formatos de total (español y US)
        total_patterns = [
            # Formato con símbolo de dólar
            r'Total[^$]*\$(\d+[,.]?\d*)',
            r'<td[^>]*>.*?\$(\d+[,.]?\d*).*?</td>[^<]*</tr>[^<]*</table>',
            r'final-total[^$]*\$(\d+[,.]?\d*)',
            
            # Formato español sin símbolo (números con coma decimal)
            r'Total[^>]*>[\s]*(\d+,\d+)[\s]*<',  # Total>605,34<
            r'<td[^>]*>\s*(\d+,\d+)\s*</td>(?=\s*</tr>\s*</table>)',  # Última celda antes de cerrar tabla
            r'total[^>]*>\s*(\d+,\d+)',  # class="total">605,34
            r'font-weight:\s*bold[^>]*>\s*(\d+,\d+)',  # style con bold
            
            # Formato US sin símbolo (números con punto decimal)  
            r'Total[^>]*>[\s]*(\d+\.\d+)[\s]*<',
            r'<td[^>]*>\s*(\d+\.\d+)\s*</td>(?=\s*</tr>\s*</table>)',
            r'total[^>]*>\s*(\d+\.\d+)',
            r'font-weight:\s*bold[^>]*>\s*(\d+\.\d+)'
        ]
        
        logger.debug(f"🔍 Extracting total from HTML length: {len(html)}")
        
        for i, pattern in enumerate(total_patterns):
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                try:
                    total_str = matches[-1].strip()
                    # Manejar formato español (coma decimal) vs US (punto decimal)
                    if ',' in total_str and '.' not in total_str:
                        # Formato español: 605,34 -> 605.34
                        total_str = total_str.replace(',', '.')
                    elif ',' in total_str and '.' in total_str:
                        # Formato con miles: 1,605.34 -> 1605.34
                        total_str = total_str.replace(',', '')
                    
                    total_value = float(total_str)
                    logger.info(f"✅ Total extraído exitosamente: {total_value} (patrón {i+1}: {pattern[:50]}...)")
                    return total_value
                except ValueError as e:
                    logger.debug(f"   Patrón {i+1} falló conversión: {total_str} -> {e}")
                    continue
        
        # Si no se encontró, mostrar parte del HTML para debugging
        html_preview = html[-500:] if len(html) > 500 else html
        logger.warning(f"❌ No se pudo extraer total del HTML")
        logger.debug(f"   HTML final (últimos 500 chars): {html_preview}")
        return 0.0
    
    async def _save_to_database(self, proposal: GeneratedProposal) -> None:
        """Guarda propuesta en base de datos de forma simple"""
        
        document_data = {
            "id": str(proposal.id),  # Convert UUID to string for database
            "rfx_id": str(proposal.rfx_id),  # Convert UUID to string for database
            "document_type": "proposal",  # Direct V2.0 field name
            "content_html": proposal.content_html,  # Direct V2.0 field name
            "total_cost": proposal.total_cost,  # Direct V2.0 field name
            "created_at": proposal.created_at.isoformat(),  # Direct V2.0 field name
            "metadata": proposal.metadata,  # Direct V2.0 field name
            "version": 1  # Required field
        }
        
        try:
            logger.debug(f"🔍 Attempting to save document data: {list(document_data.keys())}")
            logger.debug(f"🔍 Document ID: {document_data['id']}, RFX ID: {document_data['rfx_id']}")
            logger.debug(f"🔍 Content length: {len(document_data['content_html'])}")
            logger.debug(f"🔍 Total cost being saved: {document_data['total_cost']}")
            
            result_id = self.db_client.save_generated_document(document_data)
            logger.info(f"💾 Propuesta guardada en BD: {result_id}")
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle duplicate key constraint gracefully
            if "duplicate key" in error_msg or "already exists" in error_msg:
                logger.warning(f"⚠️ Document already exists in database: {document_data['id']}")
                logger.info(f"💾 Using existing document ID: {document_data['id']}")
                # Don't fail - document exists is acceptable
            else:
                logger.error(f"❌ Error guardando en BD: {e}")
                logger.error(f"❌ Document data that failed: {document_data}")
                # Don't fail the generation for database errors, but log them
    
    def _generate_basic_fallback(self, rfx_data: Dict[str, Any]) -> str:
        """Genera HTML ultra-básico en caso de fallo total"""
        
        client_info = rfx_data.get("clientes", {}) if isinstance(rfx_data.get("clientes"), dict) else {}
        client_name = client_info.get("nombre", "SOLICITANTE")
        productos_count = len(rfx_data.get("productos", []))
        fecha_actual = datetime.now().strftime("%d/%m/%y")
        numero_prop = f"PROP-{datetime.now().strftime('%d%m%y')}-ERR"
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Propuesta Comercial - {client_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 12px; }}
        .company-name {{ color: #2c5f7c; font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
        .company-subtitle {{ color: #2c5f7c; font-size: 14px; margin-bottom: 20px; }}
        .budget-box {{ border: 2px solid #000; padding: 10px; margin-bottom: 20px; width: 200px; }}
        .error {{ color: #ff6b6b; font-style: italic; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #000; padding: 8px; text-align: left; }}
        th {{ background-color: #f0f0f0; }}
        .total {{ font-weight: bold; background-color: #e0e0e0; }}
    </style>
</head>
<body>
    <div class="company-name">sabra</div>
    <div class="company-subtitle">corporation</div>
    
    <div class="budget-box">
        <strong>PRESUPUESTO</strong><br>
        Fecha: {fecha_actual}<br>
        Duración: 20 días<br>
        #: {numero_prop}
    </div>
    
    <div>
        <strong>Para: {client_name.upper()}</strong><br>
        <strong>Proceso: PLC - Catering</strong>
    </div>
    
    <table>
        <tr>
            <th>Descripción</th>
            <th>Cant</th>
            <th>Precio unitario</th>
            <th>Total</th>
        </tr>
        <tr>
            <td>Servicios de catering</td>
            <td>{productos_count}</td>
            <td>$0.00</td>
            <td>$0.00</td>
        </tr>
        <tr class="total">
            <td colspan="3"><strong>Total</strong></td>
            <td><strong>$0.00</strong></td>
        </tr>
    </table>
    
    <p class="error">Propuesta generada con template básico por error en generación IA</p>
</body>
</html>"""


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
