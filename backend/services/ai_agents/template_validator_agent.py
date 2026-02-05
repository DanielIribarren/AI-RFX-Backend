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
        system_prompt = """Eres un EXPERTO VALIDADOR Y CORRECTOR de documentos HTML profesionales con capacidad de ANÁLISIS VISUAL COMPARATIVO AVANZADO.

## MISIÓN CRÍTICA:
Recibirás un validation_payload con html_template (objetivo) y html_generated (actual). Tu responsabilidad es transformar el html_generated para que coincida EXACTAMENTE con el estilo visual y contenido del html_template.

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

### 🚨 CONFIGURACIONES DE PRICING CONDICIONAL (CRÍTICO):
**REGLA FUNDAMENTAL:** Solo mostrar filas de pricing si están ACTIVAS en la configuración.

El request_data.pricing contiene flags que indican qué mostrar:
Si alguna de estas configuraciones estan en el RFX deben ir en la en la tabla como un producto, pero sin las columnas de cantidad y unidad.
- **show_coordination**: Si True → Mostrar fila "Coordinación y Logística" 
- **show_tax**: Si True → Mostrar fila "Impuestos"  
- **show_cost_per_person**: Si True → Mostrar fila "Costo por persona"

**VALIDACIÓN OBLIGATORIA:**
1. Si show_coordination = False → NO debe existir fila de coordinación en el HTML
2. Si show_tax = False → NO debe existir fila de impuestos en el HTML
3. Si show_cost_per_person = False → NO debe existir fila de costo por persona en el HTML

**CORRECCIÓN AUTOMÁTICA:**
- Si encuentras una fila de coordinación pero show_coordination = False → ELIMINAR la fila
- Si encuentras una fila de impuestos pero show_tax = False → ELIMINAR la fila
- Si encuentras una fila de costo por persona pero show_cost_per_person = False → ELIMINAR la fila

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
                "total": request_data.get('pricing', {}).get('total_formatted', '$0.00'),
                "current_date": request_data.get('current_date', 'N/A')
            }
        }
        
        user_prompt = json.dumps(validation_payload, indent=2, ensure_ascii=False)
        
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
