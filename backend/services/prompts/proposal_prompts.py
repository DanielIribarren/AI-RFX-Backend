"""
📋 Proposal Prompts V2 - Estilo Sabra Corporation
Basado en imagen de referencia del usuario
Incluye: Cajas azules, tabla con header azul, pricing condicional
"""

from typing import Dict, Any, List


class ProposalPrompts:
    """Gestiona los diferentes prompts para generación de presupuestos"""
    
    @staticmethod
    def _format_products(products: List[Dict]) -> str:
        """Helper para formatear productos en texto"""
        if not products:
            return "No hay productos especificados"
        
        formatted = []
        for i, product in enumerate(products, 1):
            name = product.get('nombre', product.get('name', 'N/A'))
            desc = product.get('description', '')
            qty = product.get('cantidad', product.get('quantity', 0))
            price = product.get('precio_unitario', product.get('unit_price', 0))
            total = product.get('total', 0)
            
            formatted.append(
                f"{i}. {name} - {desc} | "
                f"Qty: {qty} | Precio: ${price:.2f} | Total: ${total:.2f}"
            )
        return "\n".join(formatted)
    
    @staticmethod
    def get_prompt_with_branding(
        user_id: str,
        logo_endpoint: str,
        company_info: dict,
        rfx_data: dict,
        pricing_data: dict,
        branding_config: dict = None
    ) -> str:
        """
        Prompt cuando el usuario TIENE branding configurado
        Genera presupuesto con estilo Sabra Corporation según imagen de referencia
        """
        
        products_formatted = ProposalPrompts._format_products(rfx_data.get('products', []))
        
        # ✅ Usar flags inteligentes de pricing (activo Y valor > 0)
        coord_val = pricing_data.get('coordination_formatted', '$0.00')
        tax_val = pricing_data.get('tax_formatted', '$0.00')
        cpp_val = pricing_data.get('cost_per_person_formatted', '$0.00')
        
        show_coordination = pricing_data.get('show_coordination', False)
        show_tax = pricing_data.get('show_tax', False)
        show_cost_per_person = pricing_data.get('show_cost_per_person', False)
        
        # ✅ Extraer colores reales del branding (con fallbacks)
        branding_config = branding_config or {}
        primary_color = branding_config.get('primary_color', '#0e2541')
        table_header_bg = branding_config.get('table_header_bg', '#0e2541')
        table_header_text = branding_config.get('table_header_text', '#ffffff')
        table_border = branding_config.get('table_border', '#000000')
        
        pricing_lines = f"- Subtotal: {pricing_data.get('subtotal_formatted')}"
        if show_coordination:
            pricing_lines += f"\n- Coordinación: {coord_val}"
        if show_tax:
            pricing_lines += f"\n- Impuestos: {tax_val}"
        pricing_lines += f"\n- TOTAL: {pricing_data.get('total_formatted')}"
        if show_cost_per_person:
            pricing_lines += f"\n- Costo por persona: {cpp_val}"
        
        return f"""# ROL Y CONTEXTO
Eres un experto en generación de presupuestos profesionales en HTML con el estilo corporativo de Sabra Corporation.

---

# INFORMACIÓN DE LA EMPRESA

{company_info}

## Logo de la Empresa
URL del logo: {logo_endpoint}

---

# DATOS DEL PRESUPUESTO

## Información del Cliente
- Cliente: {rfx_data.get('client_name', 'N/A')}
- Solicitud: {rfx_data.get('solicitud', 'N/A')}

## Fechas del Presupuesto
- Fecha actual: {rfx_data.get('current_date', '2025-10-20')}
- Vigencia: 30 días desde la fecha actual (calcular: fecha_actual + 30 días)

## Productos/Servicios
{products_formatted}

## Pricing
{pricing_lines}

---

# INSTRUCCIONES DE DISEÑO - ESTILO SABRA CORPORATION

## COLORES CORPORATIVOS (EXTRAÍDOS DEL BRANDING)
- **Color primario:** {primary_color} (usar en headers de tabla y cajas de información)
- **Header de tabla - Fondo:** {table_header_bg}
- **Header de tabla - Texto:** {table_header_text}
- **Bordes:** {table_border}

🚨 **CRÍTICO - USAR ESTOS COLORES EXACTOS:**
Los ejemplos de código abajo son PLANTILLAS. Cuando generes el HTML final:
- Reemplaza TODOS los colores con los valores REALES de arriba
- NO copies los ejemplos literalmente con colores hardcodeados
- Usa {primary_color}, {table_header_bg}, {table_header_text}, {table_border}

⚠️ **IMPORTANTE SOBRE COLORES:**
1. Usa EXACTAMENTE estos colores del branding como base
2. **SÉ INTELIGENTE CON EL CONTRASTE:** Si el color de fondo es claro (ej: #ffffff, #f0f0f0), usa texto OSCURO (#000000). Si el fondo es oscuro (ej: #0e2541, #2c5f7c), usa texto CLARO (#ffffff)
3. **NUNCA uses blanco sobre blanco o negro sobre negro** - esto es ilegible
4. Valida mentalmente el contraste antes de aplicar: ¿El texto será legible sobre ese fondo?
5. Si tienes duda, aplica la regla: fondos claros → texto oscuro, fondos oscuros → texto claro

## ESTRUCTURA DEL DOCUMENTO

### 1. HEADER (Superior)
<!-- Logo a la izquierda, título PRESUPUESTO a la derecha -->
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5mm; padding: 5mm 10mm 0 10mm;">
    <img src="{logo_endpoint}" alt="Logo" style="height: 15mm;">
    <h1 style="font-size: 24pt; color: {primary_color}; margin: 0;">PRESUPUESTO</h1>
</div>

<!-- Información de la empresa (dirección, teléfono, etc.) -->
<div style="font-size: 9pt; margin-bottom: 5mm; padding: 0 10mm;">
    <p style="margin: 0;">Av. Principal, C.C Mini Centro Principal</p>
    <p style="margin: 0;">Nivel 1, Local 10, Sector el Pedronal</p>
    <p style="margin: 0;">Lechería, Anzoátegui, Zona Postal 6016</p>
</div>

<!-- Fecha, Vigencia, Código alineados a la derecha -->
<div style="text-align: right; font-size: 9pt; margin-bottom: 5mm; padding: 0 10mm;">
    <p style="margin: 0;"><strong>Fecha:</strong> {rfx_data.get('current_date', '2025-10-20')}</p>
    <p style="margin: 0;"><strong>Vigencia:</strong> {rfx_data.get('validity_date', '30 días')}</p>
    <p style="margin: 0;"><strong>Código:</strong> SABRA-PO-2025-XXX</p>
</div>

IMPORTANTE sobre las fechas:
- Fecha: Usa la fecha actual proporcionada (formato: YYYY-MM-DD)
- Vigencia: Calcula 30 días desde la fecha actual y muestra la fecha resultante
- Código: Genera un código único basado en el año actual (ej: SABRA-PO-2025-001)

### 2. INFORMACIÓN DEL CLIENTE (Cajas con colores del branding)
<!-- Solo incluir: Cliente y Solicitud -->

<div style="padding: 0 10mm; margin-bottom: 3mm;">
    <div style="background: {primary_color}; color: white; padding: 2mm 3mm; font-weight: bold; display: inline-block; min-width: 30mm;">Cliente:</div>
    <div style="border: 1pt solid {primary_color}; padding: 2mm 3mm; display: inline-block; min-width: 120mm;">{rfx_data.get('client_name', 'N/A')}</div>
</div>

<div style="padding: 0 10mm; margin-bottom: 3mm;">
    <div style="background: {primary_color}; color: white; padding: 2mm 3mm; font-weight: bold; display: inline-block; min-width: 30mm;">Solicitud:</div>
    <div style="border: 1pt solid {primary_color}; padding: 2mm 3mm; display: inline-block; min-width: 120mm;">{rfx_data.get('solicitud', 'N/A')}</div>
</div>

### 3. TABLA DE PRODUCTOS (Header con colores del branding)
<table style="width: calc(100% - 20mm); margin: 5mm 10mm; border-collapse: collapse;">
    <thead>
        <tr style="background: {table_header_bg}; color: {table_header_text};">
            <th style="padding: 2mm; border: 1pt solid {table_border}; text-align: center; font-weight: bold;">Item</th>
            <th style="padding: 2mm; border: 1pt solid {table_border}; text-align: left; font-weight: bold;">Descripción</th>
            <th style="padding: 2mm; border: 1pt solid {table_border}; text-align: center; font-weight: bold;">Cant</th>
            <th style="padding: 2mm; border: 1pt solid {table_border}; text-align: right; font-weight: bold;">Precio unitario</th>
            <th style="padding: 2mm; border: 1pt solid {table_border}; text-align: right; font-weight: bold;">Total</th>
        </tr>
    </thead>
    <tbody>
        <!-- Filas de productos con fondo blanco -->
        <tr>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: center;">1</td>
            <td style="padding: 2mm; border: 1pt solid {table_border};">[NOMBRE] - [DESCRIPCIÓN]</td>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: center;">[CANTIDAD]</td>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: right;">[PRECIO]</td>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: right;">[TOTAL]</td>
        </tr>
        
        <!-- ✅ IMPORTANTE: Fila de Coordinación SOLO SI está ACTIVA en configuración -->
        {f'<tr><td colspan="3" style="padding: 2mm; border: 1pt solid {table_border};">Coordinación y Logística</td><td colspan="2" style="padding: 2mm; border: 1pt solid {table_border}; text-align: right;">{coord_val}</td></tr>' if show_coordination else '<!-- Coordinación omitida (no activa o valor = $0) -->'}
        
        <!-- ✅ IMPORTANTE: Fila de Impuestos SOLO SI está ACTIVA en configuración -->
        {f'<tr><td colspan="3" style="padding: 2mm; border: 1pt solid {table_border};">Impuestos</td><td colspan="2" style="padding: 2mm; border: 1pt solid {table_border}; text-align: right;">{tax_val}</td></tr>' if show_tax else '<!-- Impuestos omitidos (no activos o valor = $0) -->'}
        
        <!-- Fila de TOTAL (última fila de la tabla) -->
        <tr>
            <td colspan="3" style="padding: 2mm; border: 1pt solid {table_border};"></td>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: right; font-weight: bold;">TOTAL</td>
            <td style="padding: 2mm; border: 1pt solid {table_border}; text-align: right; font-weight: bold; font-size: 12pt;">{pricing_data.get('total_formatted')}</td>
        </tr>
    </tbody>
</table>

### 4. COMENTARIOS (Opcional)
<div style="padding: 0 10mm; margin: 3mm 0;">
    <strong>Comentarios:</strong>
    <div style="border: 1pt solid #000; padding: 3mm; min-height: 15mm; margin-top: 2mm;">
        <!-- Espacio para comentarios adicionales -->
    </div>
</div>

---

# REGLAS TÉCNICAS HTML-TO-PDF

✅ **Unidades:** Solo mm, pt, in (NO px, %, em, rem)
✅ **Página:** @page {{ size: letter; margin: 0; }}
✅ **Body:** width: 216mm; height: 279mm;
✅ **Colores:** -webkit-print-color-adjust: exact; print-color-adjust: exact;
✅ **Imágenes:** Especificar width y height explícitos
✅ **Bordes tabla:** 1pt solid #000
✅ **Comentarios HTML:** Incluir comentarios explicando cada sección

---

# REGLAS DE CONTENIDO

🚫 **NO incluir Términos y Condiciones**
✅ **Incluir comentarios HTML** explicando cada sección (ej: <!-- HEADER -->, <!-- TABLA DE PRODUCTOS -->)
✅ **Solo mostrar campos de pricing si > $0.00:**
   - Coordinación: {'Mostrar' if show_coordination else 'NO mostrar (omitir fila)'}
   - Impuestos: {'Mostrar' if show_tax else 'NO mostrar'}
   - Costo por persona: {'Mostrar' if show_cost_per_person else 'NO mostrar'}
✅ **Pricing dentro de la tabla** (última fila con TOTAL)
✅ **Cajas con color primario** ({primary_color}) para Cliente, Solicitud
✅ **Header de tabla** con colores del branding: fondo {table_header_bg}, texto {table_header_text}

---

# VALIDACIÓN ANTES DE ENTREGAR

Antes de generar el HTML final, verifica que incluya:

[ ] Estructura HTML completa (<!DOCTYPE>, <html>, <head>, <body>)
[ ] Logo con la URL correcta: {logo_endpoint}
[ ] Información de la empresa en el header
[ ] Cajas con colores del branding para información del cliente
[ ] Tabla con header usando colores del branding ({table_header_bg} / {table_header_text})
[ ] TODOS los productos en la tabla
[ ] Fila de Coordinación SOLO si está ACTIVA (show_coordination = {show_coordination})
[ ] Fila de Impuestos SOLO si está ACTIVA (show_tax = {show_tax})
[ ] Fila de TOTAL al final de la tabla
[ ] Comentarios HTML en cada sección
[ ] CSS optimizado para PDF (unidades en mm/pt)
[ ] NO incluir Términos y Condiciones

---

# OUTPUT

Genera ÚNICAMENTE el código HTML completo.
NO incluyas markdown, NO incluyas explicaciones.
SOLO el código HTML puro con comentarios internos.
"""
    
    @staticmethod
    def get_prompt_default(
        company_info: dict,
        rfx_data: dict,
        pricing_data: dict,
        base_url: str = "http://localhost:5001"
    ) -> str:
        """
        Prompt cuando el usuario NO tiene branding configurado
        Usa logo por defecto de Sabra Corporation
        """
        
        products_formatted = ProposalPrompts._format_products(rfx_data.get('products', []))
        
        # Logo por defecto de Sabra Corporation - usar ruta relativa
        default_logo_endpoint = "/api/branding/default/logo"
        
        # Determinar qué campos de pricing mostrar (solo si > 0)
        coord_val = pricing_data.get('coordination_formatted', '$0.00')
        tax_val = pricing_data.get('tax_formatted', '$0.00')
        cpp_val = pricing_data.get('cost_per_person_formatted', '$0.00')
        
        show_coordination = coord_val not in ['$0.00', '$0', '0']
        show_tax = tax_val not in ['$0.00', '$0', '0']
        show_cost_per_person = cpp_val not in ['$0.00', '$0', '0']
        
        pricing_lines = f"- Subtotal: {pricing_data.get('subtotal_formatted')}"
        if show_coordination:
            pricing_lines += f"\n- Coordinación: {coord_val}"
        if show_tax:
            pricing_lines += f"\n- Impuestos: {tax_val}"
        pricing_lines += f"\n- TOTAL: {pricing_data.get('total_formatted')}"
        if show_cost_per_person:
            pricing_lines += f"\n- Costo por persona: {cpp_val}"
        
        return f"""# ROL Y CONTEXTO
Eres un generador de presupuestos profesionales en HTML con estilo corporativo de Sabra Corporation.

---

# INFORMACIÓN DE LA EMPRESA

{company_info}

## Logo de la Empresa (Por Defecto)
URL del logo: {default_logo_endpoint}

---

# DATOS DEL PRESUPUESTO

## Información del Cliente
- Cliente: {rfx_data.get('client_name', 'N/A')}
- Solicitud: {rfx_data.get('solicitud', 'N/A')}

## Fechas del Presupuesto
- Fecha actual: {rfx_data.get('current_date', '2025-10-20')}
- Vigencia: 30 días desde la fecha actual (calcular: fecha_actual + 30 días)

## Productos/Servicios
{products_formatted}

## Pricing
{pricing_lines}

---

# INSTRUCCIONES DE DISEÑO - ESTILO SABRA CORPORATION

Usa el mismo estilo que el prompt con branding personalizado, CON el logo por defecto de Sabra.

## COLOR CORPORATIVO
- **Azul:** #0e2541 (headers de tabla y cajas de información)
- **Texto blanco:** #ffffff (sobre fondo azul)

## ESTRUCTURA

1. **HEADER:** Logo de Sabra a la izquierda, "PRESUPUESTO" a la derecha
2. **INFO EMPRESA:** Dirección, teléfono, email
3. **FECHAS:** Fecha actual y vigencia (30 días) alineadas a la derecha
4. **CAJAS AZULES:** Solo Cliente y Solicitud
5. **TABLA:** Header azul con texto blanco, productos, coordinación (si > $0), TOTAL
6. **COMENTARIOS:** Sección opcional para notas

### HEADER - Ejemplo con Logo:
<!-- Logo a la izquierda, título PRESUPUESTO a la derecha -->
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5mm; padding: 5mm 10mm 0 10mm;">
    <img src="{default_logo_endpoint}" alt="Logo Sabra" style="height: 15mm;">
    <h1 style="font-size: 24pt; color: #0e2541; margin: 0;">PRESUPUESTO</h1>
</div>

## REGLAS

✅ Unidades en mm/pt (NO px)
✅ Comentarios HTML en cada sección
✅ Solo mostrar Coordinación si > $0: {'Sí' if show_coordination else 'No'}
✅ Solo mostrar Impuestos si > $0: {'Sí' if show_tax else 'No'}
✅ Solo mostrar Costo/persona si > $0: {'Sí' if show_cost_per_person else 'No'}
🚫 NO incluir Términos y Condiciones

---

# OUTPUT

Genera ÚNICAMENTE el código HTML completo.
NO incluyas markdown, NO incluyas explicaciones.
SOLO el código HTML puro con comentarios internos.
"""
    
    @staticmethod
    def get_retry_prompt(
        original_prompt: str,
        validation_errors: List[str]
    ) -> str:
        """
        Prompt para retry con correcciones específicas
        """
        errors_formatted = "\n".join([f"- {error}" for error in validation_errors])
        
        return f"""{original_prompt}

---

# ⚠️ CORRECCIÓN REQUERIDA

El intento anterior falló por las siguientes razones:

{errors_formatted}

DEBES CORREGIR:
- Incluir TODA la información del cliente en cajas azules
- Incluir una tabla completa con productos
- Header de tabla azul (#0e2541) con texto blanco
- NO incluir Términos y Condiciones
- Incluir breakdown completo de precios dentro de la tabla
- El HTML debe tener al menos 500 caracteres
- Usar unidades en mm/pt (NO px)
- Incluir CSS optimizado para PDF
- Incluir comentarios HTML explicativos

Genera un HTML COMPLETO que cumpla todos estos requisitos.
"""
