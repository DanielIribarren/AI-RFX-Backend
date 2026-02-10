"""
✅ Template Validator + Auto-Fix AI Agent
Responsabilidad: Validar HTML Y corregir automáticamente cualquier problema encontrado
Enfoque: Validar → Si falla → Corregir → Retornar HTML corregido
Elimina la necesidad de retries externos - el agente se auto-corrige
"""

import logging
import asyncio
import json
from typing import Dict, Any
from openai import OpenAI

from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class TemplateValidatorAgent:
    """
    Agente simple: Valida que el HTML tenga los datos del request_data
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.client = OpenAI(api_key=self.openai_config.api_key)
    
    async def validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida HTML Y corrige automáticamente si encuentra problemas
        
        Args:
            request: {
                "html_generated": "<html>...</html>",
                "html_template": "<html>...</html>",
                "branding_config": {...},
                "request_data": {...}  # Datos que deberían estar en el HTML
            }
        
        Returns:
            {
                "is_valid": True (siempre True después de auto-corrección),
                "html_corrected": "<html>...corregido...</html>",
                "corrections_made": ["Lista de correcciones aplicadas"],
                "similarity_score": 0.95
            }
        """
        try:
            html_generated = request.get("html_generated", "")
            html_template = request.get("html_template", "")
            branding_config = request.get("branding_config", {})
            request_data = request.get("request_data", {})
            
            if not html_generated:
                return {
                    "is_valid": False,
                    "html_corrected": html_generated,
                    "corrections_made": ["HTML vacío - no se puede corregir"],
                    "similarity_score": 0.0
                }
            
            # Validación + Auto-corrección con AI
            result = await self._validate_and_fix_with_ai(
                html_generated, 
                html_template, 
                branding_config, 
                request_data
            )
            
            # Log de resultados
            corrections = result.get("corrections_made", [])
            if corrections:
                logger.info(f"🔧 Auto-corrections applied: {len(corrections)} fixes")
                for correction in corrections[:3]:  # Log primeras 3
                    logger.info(f"  ✓ {correction}")
            else:
                logger.info(f"✅ Validation PASSED - No corrections needed")
            
            logger.info(f"📊 Final Score: {result.get('similarity_score', 0.0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Validator error: {e}")
            return {
                "is_valid": False,
                "html_corrected": html_generated,
                "corrections_made": [f"Error en validación: {str(e)}"],
                "similarity_score": 0.0
            }
    
    
    async def _validate_and_fix_with_ai(
        self, 
        html_generated: str, 
        html_template: str,
        branding_config: Dict,
        request_data: Dict
    ) -> Dict[str, Any]:
        """Validación + Auto-corrección con AI - Valida Y corrige automáticamente"""
        
        # System prompt: Validador ESTRICTO que CORRIGE automáticamente
        system_prompt = """Eres un EXPERTO en DISEÑO DE PROPUESTAS COMERCIALES PROFESIONALES con capacidad de crear documentos que CONVENZAN al cliente final.

## 🎯 OBJETIVO PRINCIPAL:
Crear una propuesta comercial VISUALMENTE EXCELENTE, PROFESIONAL y PERSUASIVA que el cliente final quiera ACEPTAR inmediatamente.

## 📋 PRINCIPIOS DE DISEÑO PROFESIONAL:

### 1. ESTRUCTURA DE FACTURA PROFESIONAL:
Una propuesta comercial es como una FACTURA PROFESIONAL. Debe tener:
- **Header:** Logo + Información de la empresa + Fecha
- **Cliente:** Nombre del cliente + Descripción de la solicitud
- **Tabla de productos:** TODOS los productos con sus precios
- **Sección de totales:** DENTRO DE LA MISMA TABLA (no fuera)
  * Subtotal
  * Coordinación y Logística (si aplica)
  * Impuestos (si aplica)
  * Costo por persona (si aplica)
  * **TOTAL FINAL** (destacado)
- **Footer:** Términos y condiciones + Información de contacto

### 2. REGLA CRÍTICA - PRICING DENTRO DE LA TABLA:
⚠️ **NUNCA coloques Subtotal, Coordinación, Impuestos o TOTAL fuera de la tabla de productos.**

❌ **INCORRECTO** (pricing fuera de la tabla):
```html
</table>
<div>Subtotal: $688.70</div>
<div>Coordinación: $123.97</div>
<div>TOTAL: $812.67</div>
```

✅ **CORRECTO** (pricing dentro de la tabla):
```html
        <tr><td>10</td><td>Agua Clásico 24pz</td><td>30 unidades</td><td>$4.12</td><td>$123.60</td></tr>
        <tr><td colspan="4" style="text-align: right; font-weight: bold; padding-top: 20px;">Subtotal:</td><td style="padding-top: 20px;">$688.71</td></tr>
        <tr><td colspan="4" style="text-align: right;">Coordinación y Logística:</td><td>$123.97</td></tr>
        <tr><td colspan="4" style="text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px;">TOTAL:</td><td style="font-weight: bold; font-size: 16px; padding-top: 10px;">$812.67</td></tr>
    </table>
```

### 3. DISEÑO VISUAL PROFESIONAL:
- **Espaciado:** Padding generoso (20px arriba del subtotal, 10px arriba del total)
- **Jerarquía visual:** Subtotal y TOTAL en negrita, TOTAL más grande (16px)
- **Alineación:** Descripciones a la derecha, montos a la derecha
- **Colspan:** Usar `colspan="4"` para que las filas de pricing ocupen el ancho correcto
- **Separación visual:** Padding-top para separar productos de totales

## MISIÓN CRÍTICA:
Transformar el html_generated en una propuesta comercial PROFESIONAL que:
1. Tenga TODO el pricing DENTRO de la tabla de productos
2. Sea visualmente atractiva y fácil de leer
3. Convenza al cliente final de aceptar la propuesta
4. Siga el formato de factura profesional

## PROCESO DE TRANSFORMACIÓN INTELIGENTE (Chain-of-Thought):

### PASO 1: ANÁLISIS PROFUNDO DEL TEMPLATE OBJETIVO
Examina minuciosamente el `html_template` e identifica:
- **Estructura visual**: Layout, jerarquía, secciones, disposición de elementos
- **Esquema de colores**: Colores de fondo, texto, borders, highlights
- **Branding aplicado**: Uso de primary_color, table_header_bg, table_header_text
- **Tipografía y espaciado**: Tamaños de fuente, weights, margins, padding
- **Tabla de productos**: Formato, columnas, estilos de headers y celdas
- **Elementos únicos**: Footer, header, logo placement, contact info

### PASO 2: DISECCIÓN DEL HTML GENERADO ACTUAL  
Analiza el `html_generated` comparándolo contra el template:
- **Discrepancias visuales**: ¿Qué no coincide exactamente?
- **Contenido faltante**: ¿Faltan productos, datos del cliente, fechas?
- **Estilos incorrectos**: ¿Colores, espaciado, tipografía diferentes?
- **Estructura deficiente**: ¿Layout, jerarquía, organización inadecuada?

### PASO 3: MAPEO ESTRATÉGICO DE CORRECCIONES
Antes de modificar, planifica sistemáticamente:
1. **Prioridad 1**: Corregir contenido faltante (productos, totales, fechas)
2. **Prioridad 2**: Aplicar branding consistente (colores del branding_config)  
3. **Prioridad 3**: Replicar estructura y layout del template
4. **Prioridad 4**: Ajustar tipografía y espaciado para coherencia perfecta

### PASO 4: TRANSFORMACIÓN PRECISA Y COMPLETA
Modifica el html_generated aplicando TODAS las correcciones necesarias:
- **COLORES**: Si branding_config tiene colores, úsalos. Si NO tiene colores (N/A), extrae los colores del html_template y úsalos. Si el html_template tampoco tiene colores, elige colores profesionales y coherentes para un presupuesto comercial.
- Replicar el espaciado y layout del html_template
- Incluir TODOS los productos del request_data
- Asegurar cálculos matemáticos correctos
- Mantener la estructura semántica del template objetivo

## CRITERIOS DE VALIDACIÓN ESTRICTOS:

### ✅ COHERENCIA VISUAL ABSOLUTA:
- **COLORES**: 
  * Los colores de html_generated tienen que ser identicos al del html_template. (si son distintos o vez discrepancias tu objetivo es adaptar los colores al html_template)
  * Si html_template es vacio entonces utiliza colores elegantes que se ajusten al contexto y estilo del presupuesto (ej: azul corporativo #2c5f7c, verde #009688, gris oscuro #333333)

- Espaciado que replique exactamente la respiración visual del template  
- Tipografía consistente (tamaños, weights, families)
- Layout y estructura que coincidan píxel a píxel

### ✅ CONTENIDO COMPLETO Y PRECISO:
- Todos los productos del request_data presentes y correctos
- Información del cliente (client_name) visible y bien posicionada  
- Descripción de solicitud completa y clara
- Fechas actuales y de validez correctas
- Cálculos matemáticos exactos (subtotales, impuestos, total)

### 🎯 VALIDACIÓN CRÍTICA PARA CLIENTE FINAL (OBLIGATORIO):

**1. NOMBRE DEL CLIENTE (CRÍTICO - NO NEGOCIABLE):**
- ✅ **SIEMPRE debe haber un nombre de cliente visible**
- Buscar en request_data.client_name (prioridad 1)
- Si está vacío, buscar en request_data.solicitud o descripción
- Si encuentras placeholders como {{CLIENT_NAME}}, {{CLIENTE}}, [Cliente], "N/A", "Cliente" → **REEMPLAZAR con el nombre real del cliente**
- Si no hay nombre disponible en ningún lado → Usar "Cliente Estimado" como último recurso
- **NUNCA dejar placeholders vacíos o genéricos en el documento final**

**2. VERIFICACIÓN DE CAMPOS COMPLETOS:**
- ❌ **PROHIBIDO:** Dejar campos con {{VARIABLE}}, [PLACEHOLDER], "N/A", "Por definir"
- ✅ **OBLIGATORIO:** Todos los campos deben tener información real y coherente
- Si falta información del cliente → Usar datos genéricos profesionales
- Si falta fecha → Usar fecha actual
- Si falta descripción → Usar "Solicitud de presupuesto" o similar

**3. CONTENIDO APTO PARA ENVÍO DIRECTO:**
- El documento debe estar 100% listo para enviar al cliente
- Sin errores de formato, sin placeholders, sin datos faltantes
- Información coherente y profesional en todos los campos
- Nombres, fechas, montos y descripciones completos

### 🚨 INSERCIÓN DE FILAS DE PRICING (CRÍTICO):

**DATOS DISPONIBLES EN request_data.pricing:**
- `subtotal_formatted`: Subtotal de productos (ej: "$688.71")
- `coordination_formatted`: Coordinación y logística (ej: "$123.97")
- `tax_formatted`: Impuestos (ej: "$50.00")
- `cost_per_person_formatted`: Costo por persona (ej: "$6.77")
- `total_formatted`: Total final (ej: "$812.67")
- `show_coordination`: Boolean - Si True, insertar fila de coordinación
- `show_tax`: Boolean - Si True, insertar fila de impuestos
- `show_cost_per_person`: Boolean - Si True, insertar fila de costo por persona

**PROCESO DE INSERCIÓN (PASO A PASO):**

1. **Localizar la última fila de productos** en la tabla (antes de `</table>`)
2. **DESPUÉS de la última fila de productos**, insertar las siguientes filas **DENTRO de la tabla**:
   - **Subtotal** (siempre) con `padding-top: 20px` para separación visual
   - **Coordinación** (solo si `show_coordination = True`)
   - **Impuestos** (solo si `show_tax = True`)
   - **Costo por persona** (solo si `show_cost_per_person = True`)
   - **TOTAL** (siempre) con `font-weight: bold; font-size: 16px; padding-top: 10px`
3. **DESPUÉS de insertar todas las filas**, cerrar la tabla con `</table>`

**FORMATO EXACTO DE CADA FILA:**
```html
<!-- Subtotal (siempre) -->
<tr>
    <td colspan="4" style="text-align: right; font-weight: bold; padding-top: 20px; border-top: 2px solid #ddd;">Subtotal:</td>
    <td style="text-align: right; padding-top: 20px; border-top: 2px solid #ddd;">{subtotal_formatted}</td>
</tr>

<!-- Coordinación (solo si show_coordination = True) -->
<tr>
    <td colspan="4" style="text-align: right;">Coordinación y Logística:</td>
    <td style="text-align: right;">{coordination_formatted}</td>
</tr>

<!-- Impuestos (solo si show_tax = True) -->
<tr>
    <td colspan="4" style="text-align: right;">Impuestos:</td>
    <td style="text-align: right;">{tax_formatted}</td>
</tr>

<!-- TOTAL (siempre) -->
<tr>
    <td colspan="4" style="text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px; border-top: 2px solid #333;">TOTAL:</td>
    <td style="text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px; border-top: 2px solid #333;">{total_formatted}</td>
</tr>
```

**EJEMPLO COMPLETO:**
```html
<!-- Última fila de productos -->
<tr><td>10</td><td>Agua Clásico 24pz</td><td>30 unidades</td><td>$4.12</td><td>$123.60</td></tr>

<!-- Filas de pricing DENTRO de la tabla -->
<tr><td colspan="4" style="text-align: right; font-weight: bold; padding-top: 20px; border-top: 2px solid #ddd;">Subtotal:</td><td style="text-align: right; padding-top: 20px; border-top: 2px solid #ddd;">$688.71</td></tr>
<tr><td colspan="4" style="text-align: right;">Coordinación y Logística:</td><td style="text-align: right;">$123.97</td></tr>
<tr><td colspan="4" style="text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px; border-top: 2px solid #333;">TOTAL:</td><td style="text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px; border-top: 2px solid #333;">$812.67</td></tr>

<!-- Cerrar tabla -->
</table>
```

**⚠️ REGLAS CRÍTICAS:**
- ✅ Filas de pricing SIEMPRE dentro de `<table>...</table>`
- ✅ Usar `colspan="4"` para que ocupen el ancho correcto
- ✅ Subtotal con borde superior para separación visual
- ✅ TOTAL destacado (negrita, más grande, borde superior)
- ❌ NUNCA colocar pricing fuera de la tabla
- ❌ NUNCA usar `<div>` para pricing
- ❌ **ELIMINAR cualquier TOTAL duplicado fuera de la tabla** (solo debe existir dentro de la tabla)

**🚨 REGLA ANTI-DUPLICACIÓN:**
Si encuentras un TOTAL fuera de la tabla (después de `</table>`), **ELIMÍNALO COMPLETAMENTE**.
Solo debe existir UN TOTAL y debe estar DENTRO de la tabla de productos.

Ejemplo de lo que debes ELIMINAR:
```html
</table>
<!-- ❌ ELIMINAR ESTO -->
<div>TOTAL: $812.67</div>
<!-- ❌ ELIMINAR ESTO -->
```

**VALIDACIÓN OBLIGATORIA:**
1. Si show_coordination = False → NO debe existir fila de coordinación en el HTML
2. Si show_tax = False → NO debe existir fila de impuestos en el HTML
3. Si show_cost_per_person = False → NO debe existir fila de costo por persona en el HTML

**CORRECCIÓN AUTOMÁTICA:**
- Si encuentras una fila de coordinación pero show_coordination = False → ELIMINAR la fila
- Si encuentras una fila de impuestos pero show_tax = False → ELIMINAR la fila
- Si encuentras una fila de costo por persona pero show_cost_per_person = False → ELIMINAR la fila

**⚠️ EJEMPLOS CRÍTICOS - LO QUE NO DEBES HACER:**

❌ INCORRECTO - Eliminar fila de coordinación que existe en html_generated:
```html
<!-- HTML_GENERATED (entrada) -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>

<!-- HTML_CORRECTED (salida INCORRECTA) -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>  ❌ ELIMINASTE LA COORDINACIÓN
```

✅ CORRECTO - Preservar fila de coordinación que existe en html_generated:
```html
<!-- HTML_GENERATED (entrada) -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>

<!-- HTML_CORRECTED (salida CORRECTA) -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>  ✅ PRESERVADA
<tr><td>TOTAL</td><td>$812.67</td></tr>
```

**RECUERDA:** Tu trabajo es corregir ESTILOS y CONTENIDO VACÍO, NO eliminar filas de pricing.

**EJEMPLO DE CORRECCIÓN:**
```html
<!-- ANTES (INCORRECTO - show_coordination = False pero la fila existe) -->
<tr>
  <td>Coordinación y Logística</td>
  <td>$150.00</td>
</tr>

<!-- DESPUÉS (CORRECTO - fila eliminada porque show_coordination = False) -->
<!-- Coordinación omitida (no activa en configuración) -->
```

**⚠️ NUNCA AGREGUES FILAS DE PRICING QUE NO ESTÉN ACTIVAS**
- NO inventes valores de coordinación si show_coordination = False
- NO agregues impuestos si show_tax = False
- NO incluyas costo por persona si show_cost_per_person = False

### ✅ ESTRUCTURA HTML PROFESIONAL:
- HTML válido y bien formado
- CSS inline optimizado para conversión PDF
- Elementos semánticamente correctos
- Contraste adecuado para legibilidad profesional

## EJEMPLOS DE TRANSFORMACIONES TÍPICAS:

**Transformación de Branding:**
```html
<!-- ANTES (html_generated) -->
<th style="background-color: #cccccc; color: black;">

<!-- DESPUÉS (corregido) -->  
<th style="background-color: {{branding_config.table_header_bg}}; color: {{branding_config.table_header_text}};">
Transformación de Contenido:

html
Copy code
<!-- ANTES: Falta producto -->
<!-- Producto "Servicio Premium" ausente -->

<!-- DESPUÉS: Producto agregado -->
<tr>
  <td>Servicio Premium</td>
  <td>2</td>
  <td>Horas</td>
  <td>$150.00</td>
  <td>$300.00</td>
</tr>
Transformación de Layout:

html
Copy code
<!-- ANTES: Espaciado inconsistente -->
<div style="margin: 10px;">

<!-- DESPUÉS: Espaciado del template -->
<div style="margin: 24px 0; padding: 16px; border-radius: 8px;">
```

## FORMATO DE RESPUESTA JSON OBLIGATORIO:

{
  "is_valid": true,
  "html_corrected": "HTML COMPLETO corregido (sin truncar)",
  "corrections_made": [
    "Lista de correcciones en lenguaje claro y específico"
  ],
  "similarity_score": 0.95,
  "quality_score": 0.98
}

## EJEMPLOS DE CORRECCIONES BIEN REDACTADAS:

✅ CORRECTO - Específico y claro:
- "Ajusté los colores de la tabla - el header tenía #cccccc, ahora usa #2c5f7c del branding"
- "Corregí la orientación de la tabla - estaba con headers verticales, ahora es horizontal como el template"
- "Agregué el producto 'Servicio Premium' que faltaba en la tabla (fila 3)"
- "Cambié el espaciado del header de 10px a 24px para coincidir con el template"
- "Corregí el total de $1,500.00 a $1,690.94 según los cálculos correctos"

❌ INCORRECTO - Vago y poco útil:
- "Arreglé los colores"
- "Corregí la tabla"
- "Agregué productos faltantes"
- "Ajusté el espaciado"
- "Corregí cálculos"

## REGLAS CRÍTICAS PARA REDACCIÓN:

1. **Sé específico**: Menciona QUÉ cambió (de X a Y)
2. **Sé claro**: Explica POR QUÉ se hizo el cambio
3. **Sé útil**: Ayuda a identificar el problema original
4. **Sé completo**: Lista TODAS las correcciones, no resumas

⚠️ IMPORTANTE: Tus correcciones serán leídas por humanos para debugging. Hazlas útiles y específicas. Tratar de Hacer correcciones lo mas rapido posible"""
        
        # User prompt: Datos estructurados para validación (SIN truncar HTML)
        validation_payload = {
            "html_template": html_template,  # HTML COMPLETO - calidad > costo
            "html_generated": html_generated,  # HTML COMPLETO - no truncar
            "branding_config": {
                "primary_color": branding_config.get('primary_color', 'N/A') if branding_config else 'N/A',
                "table_header_bg": branding_config.get('table_header_bg', 'N/A') if branding_config else 'N/A',
                "table_header_text": branding_config.get('table_header_text', 'N/A') if branding_config else 'N/A'
            },
            "request_data": {
                "client_name": request_data.get('client_name', 'N/A'),
                "solicitud": request_data.get('solicitud', 'N/A'),
                "products_count": len(request_data.get('products', [])),
                "current_date": request_data.get('current_date', 'N/A'),
                "pricing": request_data.get('pricing', {})  # ✅ NUEVO: Información completa de pricing con flags
            }
        }
        
        user_prompt = json.dumps(validation_payload, indent=2, ensure_ascii=False)
        
        # ========================================
        # 🔍 DEBUG: VERIFICAR CONTENIDO DE ENTRADA
        # ========================================
        logger.info("=" * 80)
        logger.info("🔍 TEMPLATE VALIDATOR - ANÁLISIS DE HTML DE ENTRADA")
        logger.info("=" * 80)
        logger.info(f"📤 HTML Generated Size: {len(html_generated)} chars")
        
        # Verificar si contiene filas de pricing
        import re
        has_coordination_input = "Coordinación" in html_generated or "coordinación" in html_generated.lower()
        has_tax_input = "Impuesto" in html_generated or "impuesto" in html_generated.lower()
        has_cost_per_person_input = "Costo por persona" in html_generated or "costo por persona" in html_generated.lower()
        
        logger.info(f"🔍 Pricing rows detected in INPUT HTML (from Proposal Generator):")
        logger.info(f"   - Coordinación: {'✅ PRESENTE' if has_coordination_input else '❌ AUSENTE'}")
        logger.info(f"   - Impuestos: {'✅ PRESENTE' if has_tax_input else '❌ AUSENTE'}")
        logger.info(f"   - Costo por persona: {'✅ PRESENTE' if has_cost_per_person_input else '❌ AUSENTE'}")
        
        # Buscar el total para confirmar estructura
        total_match_input = re.search(r'TOTAL[:\s]*\$?([\d,]+\.?\d*)', html_generated, re.IGNORECASE)
        if total_match_input:
            logger.info(f"💰 Total found in INPUT HTML: ${total_match_input.group(1)}")
        
        logger.info("=" * 80)
        
        try:
            # Ejecutar llamada síncrona en thread separado para no bloquear
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Baja para validación consistente
                # SIN max_tokens - dejar que el modelo use lo necesario (calidad > costo)
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # ========================================
            # 📊 LOG DETALLADO DE RESULTADOS DEL VALIDATOR
            # ========================================
            html_corrected = result.get("html_corrected", html_generated)
            corrections_made = result.get("corrections_made", [])
            
            logger.info("=" * 80)
            logger.info("📋 TEMPLATE VALIDATOR AGENT - RESULTADO COMPLETO")
            logger.info("=" * 80)
            
            # Log del HTML corregido (truncado para legibilidad)
            html_preview = html_corrected[:500] + "..." if len(html_corrected) > 500 else html_corrected
            logger.info(f"✅ HTML CORRECTED (preview):\n{html_preview}")
            logger.info(f"📏 HTML Length: {len(html_corrected)} chars")
            
            # ========================================
            # 🔍 DEBUG: VERIFICAR CONTENIDO DE SALIDA
            # ========================================
            has_coordination_output = "Coordinación" in html_corrected or "coordinación" in html_corrected.lower()
            has_tax_output = "Impuesto" in html_corrected or "impuesto" in html_corrected.lower()
            has_cost_per_person_output = "Costo por persona" in html_corrected or "costo por persona" in html_corrected.lower()
            
            logger.info(f"\n🔍 Pricing rows detected in OUTPUT HTML (after validation):")
            logger.info(f"   - Coordinación: {'✅ PRESENTE' if has_coordination_output else '❌ ELIMINADA'}")
            logger.info(f"   - Impuestos: {'✅ PRESENTE' if has_tax_output else '❌ ELIMINADA'}")
            logger.info(f"   - Costo por persona: {'✅ PRESENTE' if has_cost_per_person_output else '❌ ELIMINADA'}")
            
            # Comparar entrada vs salida
            if has_coordination_input and not has_coordination_output:
                logger.error("🚨 CRÍTICO: Template Validator ELIMINÓ la fila de Coordinación que estaba en el HTML de entrada!")
            if has_tax_input and not has_tax_output:
                logger.error("🚨 CRÍTICO: Template Validator ELIMINÓ la fila de Impuestos que estaba en el HTML de entrada!")
            if has_cost_per_person_input and not has_cost_per_person_output:
                logger.error("🚨 CRÍTICO: Template Validator ELIMINÓ la fila de Costo por persona que estaba en el HTML de entrada!")
            
            # Buscar el total en el HTML corregido
            total_match_output = re.search(r'TOTAL[:\s]*\$?([\d,]+\.?\d*)', html_corrected, re.IGNORECASE)
            if total_match_output:
                logger.info(f"💰 Total found in OUTPUT HTML: ${total_match_output.group(1)}")
            
            # Log de todas las correcciones aplicadas
            logger.info(f"\n🔧 CORRECTIONS MADE ({len(corrections_made)} total):")
            if corrections_made:
                for i, correction in enumerate(corrections_made, 1):
                    logger.info(f"  {i}. {correction}")
            else:
                logger.info("  ✅ No corrections needed - HTML was perfect")
            
            # Scores
            logger.info(f"\n📊 SCORES:")
            logger.info(f"  - Similarity Score: {result.get('similarity_score', 0.0)}")
            logger.info(f"  - Quality Score: {result.get('quality_score', 0.0)}")
            logger.info(f"  - Is Valid: {result.get('is_valid', True)}")
            logger.info("=" * 80)
            
            # Retornar HTML corregido + metadata
            return {
                "is_valid": result.get("is_valid", True),  # True después de correcciones
                "html_corrected": html_corrected,
                "corrections_made": corrections_made,
                "similarity_score": result.get("similarity_score", 0.0),
                "quality_score": result.get("quality_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ AI validation+fix failed: {e}")
            # Fallback: retornar HTML original sin correcciones
            return {
                "is_valid": False,
                "html_corrected": html_generated,
                "corrections_made": [f"Error en auto-corrección: {str(e)}"],
                "similarity_score": 0.0,
                "quality_score": 0.0
            }


# Singleton instance
template_validator_agent = TemplateValidatorAgent()
