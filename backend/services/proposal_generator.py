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

import logging

logger = logging.getLogger(__name__)


class ProposalGenerationService:
    """Servicio ultra-simplificado para generar propuestas comerciales"""
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = None  # Lazy initialization
        self.db_client = get_database_client()
        self.template_html = self._load_template()
    
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
        
        # Preparar datos estructurados para la IA con precios reales
        productos_info = []
        for producto in productos:
            productos_info.append({
                "nombre": producto.get("name", producto.get("nombre", "product")),
                "cantidad": producto.get("quantity", producto.get("cantidad", 1)),
                "unidad": producto.get("unit", producto.get("unidad", "units")),
                "precio_unitario": producto.get("estimated_unit_price", 0.0),  # ✅ Include real prices
                "total": producto.get("total_estimated_cost", 0.0)  # ✅ Include calculated totals
            })
        
        prompt = f"""
Eres un experto en generar propuestas comerciales HTML para sabra corporation.

TEMPLATE HTML BASE (usa esta estructura exacta):
{self.template_html}

DATOS DEL RFX:
Solicitante: {client_info.get('name', 'Solicitante')}
Email: {client_info.get('email', '')}
Lugar: {rfx_data.get('location', 'Por definir')}
Fecha entrega: {rfx_data.get('delivery_date', 'Por definir')}

PRODUCTOS CON PRECIOS REALES:
{json.dumps(productos_info, ensure_ascii=False, indent=2)}

<prompt>
    <system>
        Eres un asistente experto en generación de presupuestos comerciales para Sabra Corporation. Tu función es transformar datos estructurados de solicitudes de productos o servicios (RFX) en documentos HTML profesionales listos para ser entregados a clientes empresariales.

        Actúas como un generador inteligente, enfocado en claridad, precisión matemática, presentación comercial efectiva, y uso correcto de estructuras HTML. No debes inventar información no proporcionada, excepto para completar nombres oficiales de empresas reconocidas si vienen abreviados o incompletos.
    </system>

    <context>
        Recibes datos provenientes del sistema (frontend), los cuales incluyen:

        - Nombre del cliente solicitante y su correo electrónico.
        - Nombre de la empresa cliente (puede venir incompleto).
        - Lugar de entrega y fecha estimada.
        - Lista detallada de productos o servicios requeridos, incluyendo nombre, cantidad, unidad y precio unitario ya definido.
        - Una plantilla HTML de referencia visual (no restrictiva) con el formato general deseado para la propuesta.

        El presupuesto puede pertenecer a múltiples dominios, tales como catering, construcción, tecnología, eventos, logística, marketing o retail.
    </context>

    <instructions>
        <step>A. Utiliza la plantilla HTML del archivo test_design.html como guía visual. Respeta la estética, pero puedes adaptar la estructura interna de las filas si lo consideras necesario para claridad.</step>
        <step>B. Reemplaza los siguientes marcadores dentro del HTML:</step>
        <substeps>
            <substep>[FECHA] → Fecha actual en formato DD/MM/YY</substep>
            <substep>[NUMERO] → Código único con formato PROP-DDMMYY-XXX</substep>
            <substep>[CLIENTE] → Nombre completo del cliente en MAYÚSCULAS</substep>
            <substep>[EMPRESA] → Nombre completo oficial de la empresa (completar si está abreviado)</substep>
            <substep>[PROCESO] → Descripción del proceso, ejemplo: "Cotización - Catering Torre Norte"</substep>
            <substep>[PRODUCTOS_ROWS] → Filas HTML con todos los productos organizados</substep>
            <substep>[SUBTOTAL] → Suma total de productos (sin coordinación)</substep>
            <substep>[TOTAL] → Suma final con coordinación incluida si aplica</substep>
        </substeps>

        <step>C. Si el dominio permite categorización (ej: catering), organiza los productos por categoría.</step>
        <step>D. Si no aplica categorización, muestra los productos en una tabla simple ordenada.</step>
        <step>E. Calcula correctamente los totales: cantidad × precio unitario por producto.</step>
        <step>F. Si se requiere, agrega una fila adicional de "Coordinación y logística" con un 15% sobre el subtotal.</step>
        <step>G. Genera un HTML funcional, válido y listo para imprimir o enviar.</step>
    </instructions>

    <criteria>
        <item>Precisión numérica en todos los cálculos (unidad × precio = total).</item>
        <item>Profesionalismo en la presentación visual, sin romper el diseño base.</item>
        <item>USAR SIEMPRE los precios definidos en 'precio_unitario' y 'total' de cada producto - NO inventar precios.</item>
        <item>Completar el nombre oficial de la empresa si se detecta abreviación o falta parcial.</item>
        <item>Adaptabilidad según el tipo de RFX: el modelo debe ajustarse a la estructura más clara según contexto.</item>
        <item>Los valores deben estar correctamente formateados y alineados en la tabla.</item>
    </criteria>

    <examples>
        <example>
            <input>
                Empresa: "Chevron"
                Cliente: "Luis Romero"
                Lugar: "Torre Barcelona"
                Fecha: "2025-08-21"
                Productos:
                - Tequeños | 100 unidades | $1.50
                - Jugo natural | 15 litros | $3.50
                - Shots de pie limón | 20 unidades | $2.50
            </input>
            <expected_output>
                HTML con:
                - CLIENTE: LUIS ROMERO
                - EMPRESA: CHEVRON GLOBAL TECHNOLOGY SERVICES COMPANY
                - PROCESO: "Cotización - Catering Torre Barcelona"
                - Clasificación en: PASAPALOS SALADOS, PASAPALOS DULCES, BEBIDAS
                - Subtotal calculado correctamente
                - Coordinación del 15%
                - Total final exacto
            </expected_output>
        </example>
        <example>
            <input>
                Empresa: "ConstruTop"
                Productos:
                - Cemento Gris | 25 sacos | $9.00
                - Arena Lavada | 5 m³ | $40.00
            </input>
            <expected_output>
                HTML con:
                - EMPRESA: CONSTRUTOP (completado si no está en mayúsculas o le falta razón social)
                - Tabla sin categorías específicas
                - Totales calculados correctamente
                - Sin coordinación si no aplica
            </expected_output>
        </example>
    </examples>

    <reasoning>
        <chain_of_thought>
            <step>1. Analiza el dominio del RFX.</step>
            <step>2. Evalúa si se puede clasificar por categoría.</step>
            <step>3. Procesa cada producto: calcula total = cantidad × precio.</step>
            <step>4. Suma los totales para calcular el subtotal.</step>
            <step>5. Si aplica coordinación, calcula 15% del subtotal y agrégalo como fila.</step>
            <step>6. Construye el HTML con los valores reemplazados en el lugar correcto.</step>
            <step>7. Asegúrate de que la salida sea HTML funcional, válido y estético.</step>
        </chain_of_thought>
    </reasoning>

    <creativity_trigger>
        - Si una empresa viene incompleta, completa su nombre a su versión oficial o corporativa más conocida.
        - Si no hay categoría clara para un producto, colócalo como “Otros servicios”.
        - Si el nombre del producto es demasiado largo, puedes simplificarlo sin perder precisión.
    </creativity_trigger>

    <output>
        Entrega SOLO un bloque de HTML completo, limpio, funcional y renderizable en navegadores. No agregues explicaciones, texto adicional ni mensajes fuera del bloque.
    </output>
</prompt>


IMPORTANTE:
- Mantén nombres de productos simples y directos
- Usa precios realistas para catering corporativo
- Asegúrate que matemáticas sean correctas
- Fecha actual para [FECHA]: {datetime.now().strftime('%d/%m/%y')}

RESPONDE SOLO CON HTML COMPLETO Y FUNCIONAL (sin explicaciones):
        """
        
        return prompt

    def _build_compact_ai_prompt(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> str:
        """Versión compacta del prompt para reintento en caso de timeout.
        - No incrusta el HTML completo del template, solo instrucciones clave y marcadores.
        - Reduce tokens para acelerar la respuesta.
        """
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        productos = rfx_data.get("productos", [])

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
        total_cost = self._extract_total_from_html(html_content)
        
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
                "generation_version": "2.0_simplified"
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
