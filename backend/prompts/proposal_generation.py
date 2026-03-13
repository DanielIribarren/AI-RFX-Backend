"""
📋 Proposal Prompts V2 - Estilo Sabra Corporation
Basado en imagen de referencia del usuario
Incluye: Cajas azules, tabla con header azul, pricing condicional
"""

from typing import Dict, Any, List
from backend.prompts.template_config import (
    build_template_style_instructions,
    get_template_config,
    get_template_html_reference,
    TemplateType,
)


class ProposalPrompts:
    """Gestiona los diferentes prompts para generación de presupuestos"""
    
    @staticmethod
    def get_prompt_with_branding(
        user_id: str,
        logo_endpoint: str,
        company_info: dict,
        rfx_data: dict,
        pricing_data: dict,
        branding_config: dict = None,
        template_type: str = "custom"
    ) -> str:
        """
        Prompt cuando el usuario TIENE branding configurado
        Genera presupuesto con estilo Sabra Corporation según imagen de referencia
        """
        
        # Usar productos preparados directamente (ya formateados desde el servicio)
        products_formatted = rfx_data.get('products', [])
        
        # ✅ Usar flags inteligentes de pricing (activo Y valor > 0)
        coord_val = pricing_data.get('coordination_formatted', '$0.00')
        tax_val = pricing_data.get('tax_formatted', '$0.00')
        cpp_val = pricing_data.get('cost_per_person_formatted', '$0.00')
        
        show_coordination = pricing_data.get('show_coordination', False)
        show_tax = pricing_data.get('show_tax', False)
        show_cost_per_person = pricing_data.get('show_cost_per_person', False)
        
        # ✅ Determinar colores según template_type o branding del usuario
        use_template = template_type and template_type != "custom"
        
        if use_template:
            # Usar colores del template predefinido
            tpl_config = get_template_config(template_type)
            tpl_colors = tpl_config.get('colors', {})
            primary_color = tpl_colors.get('primary', '#0e2541')
            table_header_bg = tpl_colors.get('table_header_bg', '#0e2541')
            table_header_text = tpl_colors.get('table_header_text', '#ffffff')
            table_border = tpl_colors.get('table_border', '#000000')
        else:
            # Usar colores del branding del usuario (flujo actual)
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
        
        # Construir contexto de template si aplica
        template_style_block = ""
        template_reference_block = ""
        role_context = "Eres un experto en generación de presupuestos profesionales en HTML con el estilo corporativo de Sabra Corporation."
        
        if use_template:
            tpl_name = tpl_config.get('name', template_type)
            role_context = f"Eres un experto en generación de presupuestos profesionales en HTML. Debes generar un presupuesto con estilo '{tpl_name}' ({tpl_config.get('tone', '')})."
            template_style_block = build_template_style_instructions(template_type)
            
            # Incluir HTML de referencia como few-shot si existe
            ref_html = get_template_html_reference(template_type)
            if ref_html:
                template_reference_block = f"""

---

# 📚 HTML DE REFERENCIA DEL TEMPLATE "{tpl_name.upper()}"

**IMPORTANTE:** Este HTML es un EJEMPLO VISUAL de cómo debe verse el documento.
Usa la MISMA estructura, colores y layout. Reemplaza los datos de ejemplo con los datos REALES del presupuesto.

```html
{ref_html}
```

**INSTRUCCIONES SOBRE ESTE EJEMPLO:**
- ✅ COPIA la estructura visual (layout, secciones, orden)
- ✅ COPIA los colores y estilos CSS exactos
- ✅ REEMPLAZA todos los datos de ejemplo con los datos reales de abajo
- ❌ NO copies los datos de ejemplo literalmente
- ❌ NO cambies los colores ni el estilo visual
"""
        
        return f"""# ROL Y CONTEXTO
{role_context}
{template_style_block}

---

# 🚨 INSTRUCCIONES CRÍTICAS DE CONSISTENCIA - MEJORA #3

**PRIORIDAD MÁXIMA: FIDELIDAD AL BRANDING (ESTILOS)**

1. **USA EXCLUSIVAMENTE los colores del branding:**
   - Color primario: {primary_color}
   - Header tabla fondo: {table_header_bg}
   - Header tabla texto: {table_header_text}
   - Bordes: {table_border}
   - ❌ NO uses colores por defecto si hay branding diferente
   - ❌ NO inventes colores nuevos

2. **ESTRUCTURA DEL LAYOUT:**
   - Sigue EXACTAMENTE la estructura mostrada abajo
   - ❌ NO agregues ni quites secciones
   - ❌ NO reordenes elementos

3. **TABLA DE PRODUCTOS:**
   - Estilo de bordes: 1pt solid {table_border}
   - Fondo del header: {table_header_bg}
   - Texto del header: {table_header_text}
   - ❌ NO uses estilos alternativos

4. **LOGO:**
   - URL exacta: {logo_endpoint}
   - Altura: 15mm (NO cambiar)
   - Posición: Según plantilla
   - ❌ NO reposiciones ni redimensiones

5. **PRICING CONDICIONAL:**
   - Coordinación: {'MOSTRAR' if show_coordination else 'NO MOSTRAR (omitir completamente)'}
   - Impuestos: {'MOSTRAR' if show_tax else 'NO MOSTRAR (omitir completamente)'}
   - Costo por persona: {'MOSTRAR' if show_cost_per_person else 'NO MOSTRAR (omitir completamente)'}
   - ❌ NO muestres filas si el flag es False

⚠️ **CHECKLIST DE VALIDACIÓN ANTES DE GENERAR:**
- [ ] ¿Usé SOLO los colores del branding especificados arriba?
- [ ] ¿Seguí EXACTAMENTE el layout sin modificaciones?
- [ ] ¿Los estilos son consistentes en todo el documento?
- [ ] ¿NO improvisé ningún elemento visual?
- [ ] ¿Respeté los flags de pricing condicional?

---

# 📚 EJEMPLO DE OUTPUT CORRECTO - MEJORA #4 (FEW-SHOT LEARNING)

**ESTE ES UN EJEMPLO DE CÓMO DEBE VERSE EL HTML GENERADO:**

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  /* 🎨 COLORES DEL BRANDING - NO CAMBIAR */
  @page {{ size: A4; margin: 20mm; }}
  body {{ 
    font-family: Arial, sans-serif; 
    color: #333; 
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  
  /* Header con color primario del branding */
  .header {{ border-bottom: 3pt solid {primary_color}; }}
  .logo {{ height: 15mm; }}
  
  /* Tabla con colores exactos del branding.
     IMPORTANTE: usar width:100% (NO calc) para que el borde derecho
     siempre se renderice dentro del área imprimible. El margen de la
     página lo controla @page, no la tabla. */
  table {{ 
    width: 100%; 
    margin: 0;
    border-collapse: collapse;
    box-sizing: border-box;
    page-break-inside: auto;  /* Permitir saltos de página dentro de la tabla */
  }}
  
  /* Evitar que el header de la tabla se corte */
  thead {{
    display: table-header-group;  /* Repetir header en cada página */
  }}
  
  /* Evitar que las filas se corten entre páginas */
  tr {{
    page-break-inside: avoid;  /* Evitar cortar filas */
    page-break-after: auto;
  }}
  
  th {{ 
    background-color: {table_header_bg};  /* Color EXACTO del branding */
    color: {table_header_text};  /* Color EXACTO del branding */
    padding: 2mm; 
    border: 1pt solid {table_border}; 
    font-weight: bold;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  td {{ 
    padding: 2mm; 
    border: 1pt solid {table_border}; 
  }}
  
  /* Cajas de información con color primario */
  .info-label {{ 
    background: {primary_color}; 
    color: white; 
    padding: 2mm 3mm; 
    font-weight: bold; 
  }}
  .info-value {{ 
    border: 1pt solid {primary_color}; 
    padding: 2mm 3mm; 
  }}
  
  /* NO agregar más estilos - mantener minimalista */
</style>
</head>
<body>
  <!-- HEADER -->
  <div class="header" style="display: flex; justify-content: space-between; align-items: center; padding: 5mm 0;">
    <img src="{logo_endpoint}" alt="Logo" class="logo">
    <h1 style="font-size: 24pt; color: {primary_color}; margin: 0;">PRESUPUESTO</h1>
  </div>
  
  <!-- INFORMACIÓN DEL CLIENTE -->
  <div style="margin: 3mm 0;">
    <span class="info-label">Cliente:</span>
    <span class="info-value">[NOMBRE CLIENTE]</span>
  </div>
  
  <!-- TABLA DE PRODUCTOS -->
  <table>
    <thead>
      <tr>
        <th>Item</th>
        <th>Descripción</th>
        <th>Cant</th>
        <th>Precio unitario</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="text-align: center;">1</td>
        <td>[PRODUCTO] - [DESCRIPCIÓN]</td>
        <td style="text-align: center;">[CANTIDAD]</td>
        <td style="text-align: right;">[PRECIO]</td>
        <td style="text-align: right;">[TOTAL]</td>
      </tr>
      <!-- MÁS PRODUCTOS... -->
      
      <!-- TOTAL -->
      <tr>
        <td colspan="3"></td>
        <td style="font-weight: bold;">TOTAL</td>
        <td style="font-weight: bold; text-align: right;">[TOTAL]</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
```

**IMPORTANTE SOBRE ESTE EJEMPLO:**
- ✅ Usa colores consistentes del branding ({primary_color}, {table_header_bg}, {table_header_text})
- ✅ Estructura limpia y minimalista
- ✅ Estilos específicos, NO genéricos
- ✅ NO mezcla estilos diferentes
- ✅ Unidades en mm/pt para PDF
- ✅ Comentarios HTML para claridad

🚨 **INSTRUCCIÓN CRÍTICA - NO COPIES EJEMPLOS LITERALMENTE:**

El ejemplo de arriba es una PLANTILLA que muestra la ESTRUCTURA.
Cuando generes el HTML final, debes:

1. ✅ **USAR LA ESTRUCTURA** del ejemplo (layout, orden de secciones)
2. ✅ **REEMPLAZAR TODOS LOS PLACEHOLDERS** con los datos reales de abajo
3. ❌ **NO COPIES** literalmente `[NOMBRE CLIENTE]`, `[PRODUCTO]`, `[CANTIDAD]`, etc.
4. ❌ **NO DEJES** placeholders sin reemplazar en el HTML final

{template_reference_block}

---

# 📊 DATOS REALES DEL PRESUPUESTO (USA ESTOS DATOS PARA GENERAR EL PRESUPUESTO CON LOS ESTILOS DEL BRANDING)

## Información de la Empresa
{company_info}

## Logo de la Empresa
**URL EXACTA DEL LOGO:** {logo_endpoint}
⚠️ Usa ESTA URL exacta en el tag <img src="...">

---

## 👤 INFORMACIÓN DEL CLIENTE - DATOS REALES DEL RFX

🚨 **INSTRUCCIÓN CRÍTICA:** NO escribas "N/A" - USA los datos específicos de abajo:

**Cliente (USAR ESTE NOMBRE EXACTO):**
{rfx_data.get('client_name', 'N/A')}

**Solicitud (USAR ESTE TEXTO EXACTO):**
{rfx_data.get('solicitud', 'N/A')}

---

## 📅 FECHAS DEL PRESUPUESTO - DATOS REALES DEL RFX

**Fecha actual (USAR ESTA FECHA EXACTA):**
{rfx_data.get('current_date', '2025-10-20')}

**Vigencia:**
30 días desde la fecha actual (calcular: fecha_actual + 30 días)

---

## 📦 PRODUCTOS/SERVICIOS - DATOS REALES DEL RFX

🚨 **INSTRUCCIÓN CRÍTICA:** La tabla de productos NO debe estar vacía.
Debes incluir TODOS Y CADA UNO de los productos listados abajo.

**PRODUCTOS COMPLETOS DEL RFX:**

{products_formatted}

⚠️ **VERIFICACIÓN OBLIGATORIA:**
- ¿Incluiste TODOS los productos de arriba en la tabla HTML?
- ¿La tabla tiene filas con datos reales (NO está vacía)?
- ¿Cada producto tiene: nombre, descripción, cantidad, precio de venta, total?

---

## 💰 TOTALES DE PRICING - DATOS REALES DEL RFX

🚨 **INSTRUCCIÓN CRÍTICA:** Usa estos valores EXACTOS en la tabla:

{pricing_lines}

⚠️ **VERIFICACIÓN OBLIGATORIA:**
- ¿El TOTAL en el HTML coincide con el total de arriba?
- ¿Incluiste la fila de Coordinación si está activa?

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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5mm;">
    <img src="{logo_endpoint}" alt="Logo" style="height: 15mm;">
    <h1 style="font-size: 24pt; color: {primary_color}; margin: 0;">PRESUPUESTO</h1>
</div>

<!-- Información de la empresa (dirección, teléfono, etc.) -->
<div style="font-size: 9pt; margin-bottom: 5mm;">
    <p style="margin: 0;">Av. Principal, C.C Mini Centro Principal</p>
    <p style="margin: 0;">Nivel 1, Local 10, Sector el Pedronal</p>
    <p style="margin: 0;">Lechería, Anzoátegui, Zona Postal 6016</p>
</div>

<!-- Fecha, Vigencia, Código alineados a la derecha -->
<div style="text-align: right; font-size: 9pt; margin-bottom: 5mm;">
    <p style="margin: 0;"><strong>Fecha:</strong> {rfx_data.get('current_date', '2025-10-20')}</p>
    <p style="margin: 0;"><strong>Vigencia:</strong> {rfx_data.get('validity_date', '30 días')}</p>
    <p style="margin: 0;"><strong>Código:</strong> {{PROPOSAL_CODE}}</p>
</div>

IMPORTANTE sobre las fechas:
- Fecha: Usa la fecha actual proporcionada (formato: YYYY-MM-DD)
- Vigencia: Calcula 30 días desde la fecha actual y muestra la fecha resultante
- Código: Mantén el placeholder {{PROPOSAL_CODE}}; el backend inyecta el código oficial.

### 2. INFORMACIÓN DEL CLIENTE (Cajas con colores del branding)
<!-- Solo incluir: Cliente y Solicitud -->

<div style="margin-bottom: 3mm;">
    <div style="background: {primary_color}; color: white; padding: 2mm 3mm; font-weight: bold; display: inline-block; min-width: 30mm;">Cliente:</div>
    <div style="border: 1pt solid {primary_color}; padding: 2mm 3mm; display: inline-block; min-width: 120mm;">{rfx_data.get('client_name', 'N/A')}</div>
</div>

<div style="margin-bottom: 3mm;">
    <div style="background: {primary_color}; color: white; padding: 2mm 3mm; font-weight: bold; display: inline-block; min-width: 30mm;">Solicitud:</div>
    <div style="border: 1pt solid {primary_color}; padding: 2mm 3mm; display: inline-block; min-width: 120mm;">{rfx_data.get('solicitud', 'N/A')}</div>
</div>

### 3. TABLA DE PRODUCTOS (Header con colores del branding)
<table style="width: 100%; margin: 0; border-collapse: collapse; box-sizing: border-box;">
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
<div style="margin: 3mm 0;">
    <strong>Comentarios:</strong>
    <div style="border: 1pt solid #000; padding: 3mm; min-height: 15mm; margin-top: 2mm;">
        <!-- Espacio para comentarios adicionales -->
    </div>
</div>

---

# REGLAS TÉCNICAS HTML-TO-PDF

✅ **Página:** @page {{ size: A4; margin: 20mm; }} (el margen de página controla el espacio, NO el body)
✅ **Body:** margin: 0; padding: 0; (NO usar width ni height fijos en mm/px en body)
✅ **Tabla:** width: 100%; margin: 0; border-collapse: collapse; box-sizing: border-box;
❌ **PROHIBIDO en tabla:** width: calc(100% - 20mm), margin: 5mm 10mm, max-width en mm
✅ **Colores:** -webkit-print-color-adjust: exact; print-color-adjust: exact;
✅ **Bordes tabla:** 1pt solid (border en th y td)
✅ **Unidades en tabla:** Solo pt para bordes, mm para padding de celdas
✅ **Comentarios HTML:** Incluir comentarios explicando cada sección

🚨 **REGLAS CRÍTICAS DE PAGINACIÓN (EVITAR TABLAS CORTADAS):**
✅ **Tabla:** page-break-inside: auto; (permitir saltos de página)
✅ **Header tabla:** display: table-header-group; (repetir header en cada página)
✅ **Filas:** page-break-inside: avoid; (NO cortar filas entre páginas)
✅ **Header colores:** -webkit-print-color-adjust: exact; (mantener colores en todas las páginas)

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

# 🔒 STRICT MODE ACTIVADO - MEJORA #7

Este presupuesto será validado automáticamente. Si no cumple EXACTAMENTE con el branding:

✅ DEBE CUMPLIR:
- Colores SOLO del branding: {primary_color}, {table_header_bg}, {table_header_text}
- Estructura EXACTA según las plantillas de arriba
- Tipografía consistente en todo el documento
- Logo en la posición especificada: {logo_endpoint}
- Pricing condicional según flags: coordination={show_coordination}, tax={show_tax}

❌ SERÁ RECHAZADO si:
- Usas colores no especificados (ej: colores hardcodeados diferentes)
- Cambias la estructura del layout
- Improvisas estilos o elementos no solicitados
- No sigues las reglas de contraste de colores
- Incluyes Términos y Condiciones (NO INCLUIR)

⚠️ GENERA EL HTML CON MÁXIMA PRECISIÓN. NO hay margen para creatividad.
⚠️ PRIORIZA CONSISTENCIA sobre estética.
⚠️ SIGUE LAS PLANTILLAS EXACTAMENTE como se muestran arriba.

---

# 🎯 INSTRUCCIÓN FINAL - GENERA EL HTML AHORA

🚨 **VERIFICACIÓN FINAL ANTES DE GENERAR:**

**1. DATOS DEL CLIENTE (NO ESCRIBAS "N/A"):**
   - ✅ Cliente: {rfx_data.get('client_name', 'N/A')}
   - ✅ Solicitud: {rfx_data.get('solicitud', 'N/A')}
   - ❌ NO escribas "N/A" en el HTML
   - ❌ NO dejes las cajas vacías

**2. TABLA DE PRODUCTOS (NO DEBE ESTAR VACÍA):**
   - ✅ Incluir los {len(rfx_data.get('products', []))} productos listados arriba
   - ✅ Cada producto debe tener: nombre, descripción, cantidad, precio, total
   - ❌ NO generes una tabla vacía
   - ❌ NO uses productos de ejemplo

**3. TOTALES (USAR VALORES REALES):**
   - ✅ Subtotal: {pricing_data.get('subtotal_formatted', '$0.00')}
   - ✅ Coordinación: {pricing_data.get('coordination_formatted', '$0.00')} {'(INCLUIR)' if show_coordination else '(OMITIR)'}
   - ✅ TOTAL: {pricing_data.get('total_formatted', '$0.00')}
   - ❌ NO inventes valores

**4. COLORES DEL BRANDING:**
   - ✅ Primario: {primary_color}
   - ✅ Header tabla: {table_header_bg} / {table_header_text}

**AHORA GENERA EL HTML COMPLETO CON TODOS LOS DATOS REALES DE ARRIBA.**

---

# OUTPUT

Genera ÚNICAMENTE el código HTML completo.
NO incluyas markdown, NO incluyas explicaciones.
SOLO el código HTML puro con comentarios internos.

RESPONDE SOLO CON EL HTML COMPLETO (sin ```html, sin markdown, sin texto adicional).
"""
    
    @staticmethod
    def get_prompt_default(
        company_info: dict,
        rfx_data: dict,
        pricing_data: dict,
        base_url: str = "http://localhost:5001",
        template_type: str = "custom"
    ) -> str:
        """
        Prompt cuando el usuario NO tiene branding configurado.
        Si template_type es un template predefinido, usa ese estilo.
        Si template_type es "custom", usa estilo default Sabra Corporation.
        """
        
        # Usar productos preparados directamente (ya formateados desde el servicio)
        products_formatted = rfx_data.get('products', [])
        
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
        
        # Determinar si usar template predefinido o default Sabra
        use_template = template_type and template_type != "custom"
        
        template_style_block = ""
        template_reference_block = ""
        role_context = "Eres un generador de presupuestos profesionales en HTML con estilo corporativo de Sabra Corporation."
        design_instructions = f"""# INSTRUCCIONES DE DISEÑO - ESTILO SABRA CORPORATION

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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5mm;">
    <img src="{default_logo_endpoint}" alt="Logo Sabra" style="height: 15mm;">
    <h1 style="font-size: 24pt; color: #0e2541; margin: 0;">PRESUPUESTO</h1>
</div>"""
        
        if use_template:
            tpl_config = get_template_config(template_type)
            tpl_name = tpl_config.get('name', template_type)
            role_context = f"Eres un experto en generación de presupuestos profesionales en HTML. Debes generar un presupuesto con estilo '{tpl_name}' ({tpl_config.get('tone', '')})."
            template_style_block = build_template_style_instructions(template_type)
            
            ref_html = get_template_html_reference(template_type)
            if ref_html:
                template_reference_block = f"""
---

# 📚 HTML DE REFERENCIA DEL TEMPLATE "{tpl_name.upper()}"

**IMPORTANTE:** Este HTML es un EJEMPLO VISUAL de cómo debe verse el documento.
Usa la MISMA estructura, colores y layout. Reemplaza los datos de ejemplo con los datos REALES del presupuesto.

```html
{ref_html}
```

**INSTRUCCIONES SOBRE ESTE EJEMPLO:**
- ✅ COPIA la estructura visual (layout, secciones, orden)
- ✅ COPIA los colores y estilos CSS exactos
- ✅ REEMPLAZA todos los datos de ejemplo con los datos reales de abajo
- ❌ NO copies los datos de ejemplo literalmente
- ❌ NO cambies los colores ni el estilo visual
"""
            
            # Reemplazar instrucciones de diseño con las del template
            design_instructions = f"""# INSTRUCCIONES DE DISEÑO - ESTILO {tpl_name.upper()}

Genera el HTML siguiendo EXACTAMENTE el estilo del template "{tpl_name}" descrito arriba.
Usa el logo por defecto de Sabra Corporation: {default_logo_endpoint}"""
        
        return f"""# ROL Y CONTEXTO
{role_context}
{template_style_block}

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

{template_reference_block}

---

{design_instructions}

## REGLAS

✅ Unidades en mm/pt (NO px)
✅ Comentarios HTML en cada sección
✅ Solo mostrar Coordinación si > $0: {'Sí' if show_coordination else 'No'}
✅ Solo mostrar Impuestos si > $0: {'Sí' if show_tax else 'No'}
✅ Solo mostrar Costo/persona si > $0: {'Sí' if show_cost_per_person else 'No'}
🚫 NO incluir Términos y Condiciones

🚨 **REGLAS DE PAGINACIÓN (EVITAR TABLAS CORTADAS):**
✅ **Tabla:** page-break-inside: auto; (permitir saltos de página)
✅ **Header tabla:** display: table-header-group; (repetir header en cada página)
✅ **Filas:** page-break-inside: avoid; (NO cortar filas entre páginas)
✅ Aplicar estos estilos en el CSS del <style> tag

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
