"""
📋 Proposal Prompts - VERSIÓN COMPLETA según especificación del usuario
Incluye: HTML-to-PDF optimization, validación robusta, prompts explícitos
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
        pricing_data: dict
    ) -> str:
        """
        Prompt cuando el usuario TIENE branding configurado
        El AI debe analizar el template y replicarlo
        """
        
        products_formatted = ProposalPrompts._format_products(rfx_data.get('products', []))
        
        return f"""# ROL Y CONTEXTO
Eres un experto en análisis de documentos corporativos y generación de presupuestos profesionales en HTML.

El usuario tiene un template de presupuesto personalizado que debes REPLICAR EXACTAMENTE.

---

# INFORMACIÓN DEL CLIENTE

## Datos de la Empresa
{company_info}

## Logo de la Empresa
URL del logo: {logo_endpoint}

IMPORTANTE sobre el logo:
- Debes incluir el logo usando esta URL exacta
- Posiciónalo en la esquina superior izquierda
- Dimensiones: 40mm de ancho x 15mm de alto
- Código correcto:
```html
<img src="{logo_endpoint}" 
     alt="Logo" 
     width="151" 
     height="57"
     style="width: 40mm; height: 15mm; display: block; object-fit: contain;"
     loading="eager"
     decoding="sync"
     crossorigin="anonymous">
```

---

# DATOS DEL PRESUPUESTO

## Información del Cliente Final
- Cliente: {rfx_data.get('client_name', 'N/A')}
- Empresa: {rfx_data.get('company_name', 'N/A')}
- Solicitante: {rfx_data.get('requester_name', 'N/A')}
- Email: {rfx_data.get('requester_email', 'N/A')}
- Fecha de evento: {rfx_data.get('event_date', 'N/A')}
- Lugar: {rfx_data.get('event_location', 'N/A')}
- Número de personas: {rfx_data.get('num_people', 'N/A')}

## Productos/Servicios Solicitados
{products_formatted}

## Pricing Breakdown
- Subtotal: {pricing_data.get('subtotal_formatted')}
- Coordinación ({pricing_data.get('coordination_percentage')}%): {pricing_data.get('coordination_formatted')}
- Impuestos ({pricing_data.get('tax_percentage')}%): {pricing_data.get('tax_formatted')}
- TOTAL FINAL: {pricing_data.get('total_formatted')}
- Costo por persona: {pricing_data.get('cost_per_person_formatted')}

---

# INSTRUCCIONES CRÍTICAS PARA GENERAR EL HTML

## 1. ESTRUCTURA EXACTA DEL DOCUMENTO

Debes generar un HTML COMPLETO con esta estructura:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Presupuesto - {{{{company_name}}}}</title>
    <style>
        /* CSS AQUÍ - OPTIMIZADO PARA PDF */
        @page {{{{
            size: letter;
            margin: 0;
        }}}}
        
        * {{{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}}}
        
        body {{{{
            width: 216mm;
            height: 279mm;
            font-family: Arial, sans-serif;
            font-size: 11pt;
            color: #000;
        }}}}
        
        /* MÁS CSS AQUÍ */
    </style>
</head>
<body>
    <!-- CONTENIDO DEL PRESUPUESTO -->
</body>
</html>
```

## 2. SECCIONES OBLIGATORIAS

Tu HTML DEBE incluir TODAS estas secciones:

✅ Header con Logo y Título
✅ Información de tu Empresa (dirección, teléfono, email)
✅ Información del Cliente (nombre, empresa)
✅ Detalles de la Solicitud (fecha, lugar, descripción)
✅ Tabla de Productos/Servicios (con todas las columnas)
✅ Breakdown de Precios (subtotal, coordinación, impuestos, total)
✅ Términos y Condiciones (al menos 3 puntos)
✅ Información de Contacto (footer)

## 3. REGLAS PARA HTML-TO-PDF

IMPORTANTE: Este HTML se convertirá a PDF con Playwright, por lo tanto:

✅ Usa SOLO unidades absolutas: mm, pt, in
✅ NO uses: px, %, em, rem, vw, vh
✅ Define width Y height explícitos para TODAS las imágenes
✅ Usa colores con -webkit-print-color-adjust: exact
✅ Define @page {{{{ size: letter; margin: 0; }}}}
✅ Body debe ser: width: 216mm; height: 279mm;

## 4. FORMATO DE LA TABLA DE PRODUCTOS

```html
<table class="products-table">
    <thead>
        <tr>
            <th>Ítem</th>
            <th>Descripción</th>
            <th>Cantidad</th>
            <th>Precio Unit.</th>
            <th>Total</th>
        </tr>
    </thead>
    <tbody>
        <!-- Una fila por cada producto -->
        <tr>
            <td>1</td>
            <td>Nombre del producto - Descripción detallada</td>
            <td>X unidades</td>
            <td>$X.XX</td>
            <td>$X.XX</td>
        </tr>
        <!-- Más filas... -->
    </tbody>
</table>
```

## 5. SECCIÓN DE TÉRMINOS Y CONDICIONES

DEBES incluir una sección de términos. Ejemplo:

```html
<div class="terms-section">
    <h3>Términos y Condiciones</h3>
    <ul>
        <li>Validez de la propuesta: 30 días</li>
        <li>Forma de pago: 50% anticipo, 50% contra entrega</li>
        <li>Tiempo de entrega: según fecha del evento</li>
        <li>Los precios incluyen coordinación logística</li>
    </ul>
</div>
```

---

# VALIDACIÓN ANTES DE ENTREGAR

Antes de generar el HTML final, verifica que incluya:

[ ] Estructura HTML completa (<!DOCTYPE>, <html>, <head>, <body>)
[ ] Logo con la URL correcta y dimensiones explícitas
[ ] Información de la empresa (dirección, teléfono, email)
[ ] Información del cliente
[ ] Tabla con TODOS los productos
[ ] Breakdown de precios completo
[ ] Sección de términos y condiciones
[ ] Footer con información de contacto
[ ] CSS optimizado para PDF (unidades en mm/pt)
[ ] Longitud > 500 caracteres

---

# OUTPUT ESPERADO

Genera ÚNICAMENTE el código HTML completo, sin explicaciones adicionales.
El HTML debe ser válido, completo y listo para convertirse a PDF.

NO incluyas markdown, NO incluyas comentarios fuera del HTML. Solo el código HTML puro.
"""
    
    @staticmethod
    def get_prompt_default(
        company_info: dict,
        rfx_data: dict,
        pricing_data: dict
    ) -> str:
        """
        Prompt cuando el usuario NO tiene branding configurado
        Usa un template HTML predeterminado profesional
        """
        
        products_formatted = ProposalPrompts._format_products(rfx_data.get('products', []))
        
        return f"""# ROL Y CONTEXTO
Eres un generador de presupuestos profesionales. Debes crear un presupuesto en HTML usando un formato predeterminado profesional.

---

# DATOS DEL PRESUPUESTO

## Información de tu Empresa
{company_info}

## Información del Cliente Final
- Cliente: {rfx_data.get('client_name', 'N/A')}
- Empresa: {rfx_data.get('company_name', 'N/A')}
- Solicitante: {rfx_data.get('requester_name', 'N/A')}
- Email: {rfx_data.get('requester_email', 'N/A')}
- Fecha de evento: {rfx_data.get('event_date', 'N/A')}
- Lugar: {rfx_data.get('event_location', 'N/A')}
- Número de personas: {rfx_data.get('num_people', 'N/A')}

## Productos/Servicios
{products_formatted}

## Pricing
- Subtotal: {pricing_data.get('subtotal_formatted')}
- Coordinación: {pricing_data.get('coordination_formatted')}
- Impuestos: {pricing_data.get('tax_formatted')}
- TOTAL: {pricing_data.get('total_formatted')}

---

# INSTRUCCIONES

Genera un HTML completo con este TEMPLATE PREDETERMINADO:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta Comercial</title>
    <style>
        @page {{{{
            size: letter;
            margin: 0;
        }}}}
        
        * {{{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}}}
        
        body {{{{
            width: 216mm;
            height: 279mm;
            font-family: Arial, sans-serif;
            font-size: 11pt;
            color: #333;
            background: white;
        }}}}
        
        .container {{{{
            padding: 10mm;
        }}}}
        
        .header {{{{
            text-align: center;
            border-bottom: 2pt solid #2c5f7c;
            padding-bottom: 5mm;
            margin-bottom: 5mm;
        }}}}
        
        .header h1 {{{{
            font-size: 24pt;
            color: #2c5f7c;
            margin-bottom: 2mm;
        }}}}
        
        .section {{{{
            margin-bottom: 5mm;
        }}}}
        
        .section-title {{{{
            background-color: #2c5f7c;
            color: white;
            padding: 2mm 3mm;
            font-size: 12pt;
            font-weight: bold;
            margin-bottom: 2mm;
        }}}}
        
        .section-content {{{{
            padding: 3mm;
            background-color: #f9f9f9;
            border: 1pt solid #ddd;
        }}}}
        
        table {{{{
            width: 100%;
            border-collapse: collapse;
            margin: 3mm 0;
        }}}}
        
        th {{{{
            background-color: #2c5f7c;
            color: white;
            padding: 2mm;
            text-align: left;
            border: 1pt solid #ddd;
        }}}}
        
        td {{{{
            padding: 2mm;
            border: 1pt solid #ddd;
        }}}}
        
        .pricing-summary {{{{
            margin-top: 5mm;
            text-align: right;
        }}}}
        
        .total-line {{{{
            font-size: 14pt;
            font-weight: bold;
            color: #2c5f7c;
            margin-top: 2mm;
            padding-top: 2mm;
            border-top: 2pt solid #2c5f7c;
        }}}}
        
        .footer {{{{
            position: absolute;
            bottom: 5mm;
            left: 10mm;
            right: 10mm;
            text-align: center;
            font-size: 9pt;
            color: #666;
            border-top: 1pt solid #ddd;
            padding-top: 3mm;
        }}}}
        
        ul {{{{
            padding-left: 5mm;
        }}}}
        
        li {{{{
            margin-bottom: 1mm;
        }}}}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>PROPUESTA COMERCIAL</h1>
            <p>Presupuesto Profesional</p>
        </div>
        
        <!-- INFO EMPRESA -->
        <div class="section">
            <div class="section-title">Información del Proveedor</div>
            <div class="section-content">
                <p><strong>Empresa:</strong> [NOMBRE DE TU EMPRESA]</p>
                <p><strong>Contacto:</strong> [TELÉFONO] | [EMAIL]</p>
                <p><strong>Dirección:</strong> [DIRECCIÓN]</p>
            </div>
        </div>
        
        <!-- INFO CLIENTE -->
        <div class="section">
            <div class="section-title">Información del Cliente</div>
            <div class="section-content">
                <p><strong>Cliente:</strong> [CLIENTE]</p>
                <p><strong>Empresa:</strong> [EMPRESA]</p>
                <p><strong>Fecha:</strong> [FECHA]</p>
                <p><strong>Lugar:</strong> [LUGAR]</p>
            </div>
        </div>
        
        <!-- PRODUCTOS -->
        <div class="section">
            <div class="section-title">Productos y Servicios</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 5%;">#</th>
                        <th style="width: 50%;">Descripción</th>
                        <th style="width: 15%;">Cantidad</th>
                        <th style="width: 15%;">Precio Unit.</th>
                        <th style="width: 15%;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Filas de productos aquí -->
                </tbody>
            </table>
        </div>
        
        <!-- PRICING -->
        <div class="pricing-summary">
            <p>Subtotal: [SUBTOTAL]</p>
            <p>Coordinación: [COORDINACION]</p>
            <p>Impuestos: [IMPUESTOS]</p>
            <p class="total-line">TOTAL: [TOTAL]</p>
        </div>
        
        <!-- TÉRMINOS -->
        <div class="section">
            <div class="section-title">Términos y Condiciones</div>
            <div class="section-content">
                <ul>
                    <li>Validez de la propuesta: 30 días calendario</li>
                    <li>Forma de pago: 50% anticipo, 50% contra entrega</li>
                    <li>Los precios incluyen coordinación y logística</li>
                    <li>Tiempo de entrega según fecha del evento</li>
                </ul>
            </div>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <p>Gracias por su preferencia | Para más información, contáctenos</p>
        </div>
    </div>
</body>
</html>
```

Completa este template con los datos proporcionados arriba.
Genera SOLO el HTML completo, sin explicaciones.
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
- Incluir TODA la información del cliente y empresa
- Incluir una tabla completa con productos
- Incluir sección de "Términos y Condiciones"
- Incluir breakdown completo de precios
- El HTML debe tener al menos 500 caracteres
- Usar unidades en mm/pt (NO px)
- Incluir CSS optimizado para PDF

Genera un HTML COMPLETO que cumpla todos estos requisitos.
"""
