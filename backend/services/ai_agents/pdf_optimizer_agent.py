"""
🎨 PDF Optimizer AI Agent
Responsabilidad: Optimizar HTML para conversión PDF profesional
Enfoque: Analizar críticamente y tomar decisiones inteligentes sobre:
- Paginación (page-breaks)
- Anchos de tabla
- Espaciado profesional
- Centrado de contenido
- Estructura header/content/footer
"""

import logging
import asyncio
from typing import Dict, Any
from openai import OpenAI

from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class PDFOptimizerAgent:
    """
    Agente especializado en optimizar HTML para conversión PDF profesional
    Este es el agente MÁS INTELIGENTE - toma decisiones críticas sobre layout
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.client = OpenAI(
            api_key=self.openai_config.api_key,
            max_retries=0  # Desactivar reintentos automáticos del SDK
        )
    
    async def optimize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimiza HTML para conversión PDF profesional multipágina
        Enfoque: Paginación inteligente, espaciado profesional, layout optimizado
        """
        try:
            logger.info("🎨 PDF Optimizer Agent - Starting optimization")
            
            html_content = request.get("html_content", "")
            validation_results = request.get("validation_results", {}) or {}
            page_config = request.get("page_config", {}) or {}
            quality_req = request.get("quality_requirements", {}) or {}
            branding_config = request.get("branding_config", {}) or {}
            
            logger.info(f"🔍 DEBUG - branding_config type: {type(branding_config)}, value: {branding_config}")
            
            if not html_content:
                return {
                    "status": "error",
                    "error": "html_content is required",
                    "html_optimized": None
                }
            
            # Optimización completa con AI para paginación multipágina
            optimization_result = await self._optimize_with_ai(
                html_content, 
                validation_results,
                branding_config,
                page_config, 
                quality_req
            )
            
            logger.info(f"✅ PDF optimization complete - {len(optimization_result.get('adjustments_made', []))} adjustments")
            
            return {
                "status": "success",
                "html_optimized": optimization_result.get("html_optimized"),
                "analysis": {
                    "table_width": optimization_result.get("table_width"),
                    "estimated_pages": optimization_result.get("estimated_pages"),
                    "adjustments_made": optimization_result.get("adjustments_made", []),
                    "warnings": optimization_result.get("warnings", [])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in PDF Optimizer Agent: {e}")
            return {
                "status": "error",
                "error": str(e),
                "html_optimized": html_content  # Fallback: devolver HTML sin optimizar
            }
    
    async def _optimize_with_ai(
        self, 
        html_content: str, 
        validation_results: Dict,
        branding_config: Dict,
        page_config: Dict,
        quality_req: Dict
    ) -> Dict[str, Any]:
        """Optimización inteligente con AI"""
        
        # Protección defensiva: asegurar que todos los dicts no sean None
        validation_results = validation_results or {}
        branding_config = branding_config or {}
        page_config = page_config or {}
        quality_req = quality_req or {}
        
        page_size = page_config.get("size", "letter")
        max_width = "216mm" if page_size == "letter" else "210mm"  # Letter vs A4
        
        # System prompt SIMPLIFICADO para respuestas más rápidas
        system_prompt = """Eres un EXPERTO en OPTIMIZACIÓN DE PROPUESTAS COMERCIALES para conversión a PDF PROFESIONAL.

## 🎯 OBJETIVO PRINCIPAL:
Optimizar el HTML para que se convierta en un PDF VISUALMENTE EXCELENTE que el cliente final quiera IMPRIMIR y FIRMAR inmediatamente.

## ⚠️ REGLAS CRÍTICAS DE CONTENIDO:

### 1. PRESERVAR ESTRUCTURA DE FACTURA PROFESIONAL:
El HTML que recibes tiene una estructura de FACTURA PROFESIONAL con:
- Tabla de productos
- **Filas de pricing DENTRO de la tabla** (Subtotal, Coordinación, Impuestos, TOTAL)
- Footer con términos

### 2. NUNCA MODIFICAR CONTENIDO:
- ❌ NO eliminar filas de la tabla (productos NI pricing)
- ❌ NO modificar valores monetarios
- ❌ NO cambiar texto o estructura
- ❌ NO mover pricing fuera de la tabla
- ✅ SOLO agregar/optimizar CSS para PDF

### 3. PRESERVAR PRICING DENTRO DE LA TABLA:
Las filas de Subtotal, Coordinación, Impuestos y TOTAL están **DENTRO de la tabla de productos**.
**NUNCA las muevas fuera de la tabla.**

### 4. ELIMINAR TOTAL DUPLICADO:
⚠️ **CRÍTICO:** Si encuentras un TOTAL fuera de la tabla (después de `</table>`), **ELIMÍNALO COMPLETAMENTE**.
Solo debe existir UN TOTAL y debe estar DENTRO de la tabla de productos.

Ejemplo de lo que debes ELIMINAR:
```html
</table>
<!-- ❌ ELIMINAR ESTO -->
<div style="text-align: right;">TOTAL: $812.67</div>
<!-- ❌ ELIMINAR ESTO -->
```

## TU TRABAJO:
1. Agregar CSS para que el PDF se vea PROFESIONAL y se imprima correctamente
2. **ELIMINAR cualquier TOTAL duplicado fuera de la tabla**

## OPTIMIZACIONES CRÍTICAS:

### 1. PAGINACIÓN MULTIPÁGINA:
- Si >12 productos: agregar `page-break-after: auto;` cada 12 filas
- Header de tabla: `display: table-header-group;` (repetir en cada página)
- Filas: `page-break-inside: avoid;` (no partir filas entre páginas)

### 2. CSS OBLIGATORIO:
```css
@page { size: letter; margin: 15mm; }
body { -webkit-print-color-adjust: exact; }
table { page-break-inside: auto; max-width: 190mm; margin: 0 auto; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
img { max-width: 100%; page-break-inside: avoid; }
```

### 3. PRESERVAR:
- Placeholder {{LOGO_PLACEHOLDER}} sin modificar
- Todos los productos y precios
- Colores del branding
- Contenido completo

### 4. 🚨 CONFIGURACIONES DE PRICING CONDICIONAL (CRÍTICO - NO MODIFICAR):
**REGLA FUNDAMENTAL:** NO agregar ni eliminar filas de pricing. Solo optimizar las que YA existen.

⚠️ **ADVERTENCIA CRÍTICA:** El HTML que recibes ya fue validado por otro agente. Las filas de pricing que contiene son CORRECTAS y OBLIGATORIAS. NO las elimines bajo NINGUNA circunstancia.

**FILAS DE PRICING QUE DEBES PRESERVAR:**
- Si hay fila de "Coordinación y Logística" → **PRESERVAR OBLIGATORIAMENTE** (está activa en configuración)
- Si hay fila de "Impuestos" → **PRESERVAR OBLIGATORIAMENTE** (está activa en configuración)
- Si hay fila de "Costo por persona" → **PRESERVAR OBLIGATORIAMENTE** (está activa en configuración)
- Si NO hay alguna de estas filas → **NO AGREGAR** (no está activa en configuración)

**EJEMPLOS DE LO QUE NO DEBES HACER:**
❌ INCORRECTO - Eliminar fila de coordinación:
```html
<!-- HTML de entrada -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>

<!-- HTML de salida INCORRECTO -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>  ❌ ELIMINÓ COORDINACIÓN
```

✅ CORRECTO - Preservar fila de coordinación:
```html
<!-- HTML de entrada -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>
<tr><td>TOTAL</td><td>$812.67</td></tr>

<!-- HTML de salida CORRECTO -->
<tr><td>Subtotal</td><td>$688.71</td></tr>
<tr><td>Coordinación y Logística</td><td>$123.97</td></tr>  ✅ PRESERVADA
<tr><td>TOTAL</td><td>$812.67</td></tr>
```

**TU RESPONSABILIDAD:**

**A. VALIDACIÓN DE CONTENIDO PARA CLIENTE FINAL (CRÍTICO):**
1. **Nombre del Cliente (OBLIGATORIO):**
   - ✅ Verificar que haya un nombre de cliente visible
   - Si encuentras {{CLIENT_NAME}}, {{CLIENTE}}, [Cliente], "N/A" → Reemplazar con nombre real
   - Si no hay nombre disponible → Usar "Cliente Estimado"
   - **NUNCA dejar placeholders vacíos en el documento final**

2. **Campos Completos:**
   - ❌ PROHIBIDO: Dejar {{VARIABLE}}, [PLACEHOLDER], "N/A", "Por definir"
   - ✅ OBLIGATORIO: Todos los campos con información real y coherente
   - Si falta fecha → Usar fecha actual
   - Si falta descripción → Usar texto genérico profesional

3. **Documento Listo para Envío:**
   - 100% apto para enviar al cliente sin ediciones
   - Sin errores de formato, sin placeholders, sin datos faltantes
   - Información profesional y coherente en todos los campos

**B. OPTIMIZACIÓN DE PRICING (NO MODIFICAR CONTENIDO):**
- Solo optimizar el CSS y paginación de las filas existentes
- NO agregar filas de pricing que no existen
- NO eliminar filas de pricing que existen
- NO modificar valores de pricing
- NO inventar configuraciones

**EJEMPLO:**
```html
<!-- Si el HTML tiene esto: -->
<tr><td>Subtotal</td><td>$1,000.00</td></tr>
<tr><td>TOTAL</td><td>$1,000.00</td></tr>

<!-- NO agregues coordinación ni impuestos -->
<!-- Solo optimiza el CSS de las filas existentes -->
```

## FORMATO DE RESPUESTA JSON OBLIGATORIO:

{
  "html_optimized": "HTML completo optimizado (sin truncar)",
  "table_width": "190mm",
  "estimated_pages": 2,
  "adjustments_made": [
    "Lista de ajustes en lenguaje claro y específico"
  ],
  "warnings": [],
  "quality_score": 1.0
}

## EJEMPLOS DE AJUSTES BIEN REDACTADOS:

✅ CORRECTO - Específico y claro:
- "Agregado CSS @page { size: letter; margin: 15mm; } para configuración de página"
- "Aplicado page-break-after: auto; cada 12 productos para paginación multipágina"
- "Ajustado ancho de tabla de 100% a 190mm para centrado perfecto en página letter"
- "Agregado display: table-header-group; al <thead> para repetir headers en cada página"
- "Aplicado page-break-inside: avoid; a todas las filas <tr> para evitar cortes"
- "Cambiado margin del body de 20px a 0 para aprovechar márgenes de @page"

❌ INCORRECTO - Vago y poco útil:
- "Agregado CSS para PDF"
- "Aplicado page-breaks"
- "Ajustado ancho de tabla"
- "Optimizado headers"
- "Corregido márgenes"

## REGLAS CRÍTICAS PARA REDACCIÓN:

1. **Sé específico**: Menciona QUÉ CSS/propiedad agregaste o modificaste
2. **Sé técnico**: Usa nombres exactos de propiedades CSS (page-break-after, display, etc.)
3. **Sé útil**: Explica PARA QUÉ sirve el ajuste (ej: "para paginación multipágina")
4. **Sé completo**: Lista TODOS los ajustes, no resumas

⚠️ IMPORTANTE: Tus ajustes serán leídos por humanos para debugging. Hazlos técnicos, específicos y útiles.
⚠️ NO truncar HTML. Retornar contenido completo. ASEGURATE DE HACERLO LO MAS RAPIDO POSIBLE Y DIRECTO Y SIMPLE SIN PERDER CALIDAD"""
        
        # User prompt: HTML COMPLETO sin truncar (calidad > costo)
        optimization_payload = {
            "html_content": html_content,  # HTML COMPLETO - NO truncar
            "validation_results": {
                "is_valid": validation_results.get("is_valid", False),
                "issues_count": len(validation_results.get("issues", [])),
                "similarity_score": validation_results.get("similarity_score", 0.0)
            },
            "branding_config": {
                "primary_color": branding_config.get('primary_color', '#000000'),
                "secondary_color": branding_config.get('secondary_color', '#ffffff')
            },
            "page_config": {
                "size": page_size,
                "max_width": max_width,
                "orientation": page_config.get('orientation', 'portrait')
            },
            "quality_requirements": {
                "min_margin": quality_req.get('min_margin', '15mm'),
                "max_table_width": quality_req.get('max_table_width', '190mm'),
                "professional_spacing": quality_req.get('professional_spacing', True),
                "table_centering": quality_req.get('table_centering', True)
            }
        }
        
        import json
        user_prompt = json.dumps(optimization_payload, indent=2, ensure_ascii=False)
        
        # ========================================
        # 🔍 DEBUG: VERIFICAR CONTENIDO DE ENTRADA
        # ========================================
        logger.info("=" * 80)
        logger.info("🔍 PDF OPTIMIZER - ANÁLISIS DE HTML DE ENTRADA")
        logger.info("=" * 80)
        logger.info(f"📤 HTML Size: {len(html_content)} chars")
        
        # Verificar si contiene filas de pricing
        has_coordination = "Coordinación" in html_content or "coordinación" in html_content.lower()
        has_tax = "Impuesto" in html_content or "impuesto" in html_content.lower()
        has_cost_per_person = "Costo por persona" in html_content or "costo por persona" in html_content.lower()
        
        logger.info(f"🔍 Pricing rows detected in INPUT HTML:")
        logger.info(f"   - Coordinación: {'✅ PRESENTE' if has_coordination else '❌ AUSENTE'}")
        logger.info(f"   - Impuestos: {'✅ PRESENTE' if has_tax else '❌ AUSENTE'}")
        logger.info(f"   - Costo por persona: {'✅ PRESENTE' if has_cost_per_person else '❌ AUSENTE'}")
        
        # Buscar el total para confirmar estructura
        import re
        total_match = re.search(r'TOTAL[:\s]*\$?([\d,]+\.?\d*)', html_content, re.IGNORECASE)
        if total_match:
            logger.info(f"💰 Total found in HTML: ${total_match.group(1)}")
        
        logger.info("=" * 80)
        logger.info(f"🤖 Model: {self.openai_config.model}, Temperature: 0.2")
        
        try:
            import time
            start_time = time.time()
            
            logger.info("⏳ Calling OpenAI API...")
            
            # Ejecutar llamada síncrona en thread separado para no bloquear
            # ✅ OPTIMIZACIÓN: GPT-4o-mini (60% más rápido, 60% más barato)
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",  # Modelo optimizado para PDF optimization
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=12000,  # Suficiente para HTML optimizado
                timeout=60,  # Timeout optimizado (1 minuto)
                response_format={"type": "json_object"}
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ OpenAI API responded in {elapsed:.2f}s")
            
            result = json.loads(response.choices[0].message.content)
            
            # ========================================
            # 📊 LOG DETALLADO DE RESULTADOS DEL PDF OPTIMIZER
            # ========================================
            html_optimized = result.get("html_optimized", html_content)
            adjustments_made = result.get("adjustments_made", [])
            
            logger.info("=" * 80)
            logger.info("🎨 PDF OPTIMIZER AGENT - RESULTADO COMPLETO")
            logger.info("=" * 80)
            
            # Log del HTML optimizado (truncado para legibilidad)
            html_preview = html_optimized[:500] + "..." if len(html_optimized) > 500 else html_optimized
            logger.info(f"✅ HTML OPTIMIZED (preview):\n{html_preview}")
            logger.info(f"📏 HTML Length: {len(html_optimized)} chars")
            
            # ========================================
            # 🔍 DEBUG: VERIFICAR CONTENIDO DE SALIDA
            # ========================================
            has_coordination_output = "Coordinación" in html_optimized or "coordinación" in html_optimized.lower()
            has_tax_output = "Impuesto" in html_optimized or "impuesto" in html_optimized.lower()
            has_cost_per_person_output = "Costo por persona" in html_optimized or "costo por persona" in html_optimized.lower()
            
            logger.info(f"\n🔍 Pricing rows detected in OUTPUT HTML:")
            logger.info(f"   - Coordinación: {'✅ PRESENTE' if has_coordination_output else '❌ ELIMINADA'}")
            logger.info(f"   - Impuestos: {'✅ PRESENTE' if has_tax_output else '❌ ELIMINADA'}")
            logger.info(f"   - Costo por persona: {'✅ PRESENTE' if has_cost_per_person_output else '❌ ELIMINADA'}")
            
            # Comparar entrada vs salida
            if has_coordination and not has_coordination_output:
                logger.error("🚨 CRÍTICO: PDF Optimizer ELIMINÓ la fila de Coordinación que estaba en el HTML de entrada!")
            if has_tax and not has_tax_output:
                logger.error("🚨 CRÍTICO: PDF Optimizer ELIMINÓ la fila de Impuestos que estaba en el HTML de entrada!")
            if has_cost_per_person and not has_cost_per_person_output:
                logger.error("🚨 CRÍTICO: PDF Optimizer ELIMINÓ la fila de Costo por persona que estaba en el HTML de entrada!")
            
            # Buscar el total en el HTML optimizado
            total_match_output = re.search(r'TOTAL[:\s]*\$?([\d,]+\.?\d*)', html_optimized, re.IGNORECASE)
            if total_match_output:
                logger.info(f"💰 Total found in OPTIMIZED HTML: ${total_match_output.group(1)}")
            logger.info("=" * 80)
            
            # Log de todos los ajustes aplicados
            logger.info(f"\n🔧 ADJUSTMENTS MADE ({len(adjustments_made)} total):")
            if adjustments_made:
                for i, adjustment in enumerate(adjustments_made, 1):
                    logger.info(f"  {i}. {adjustment}")
            else:
                logger.info("  ✅ No adjustments needed - HTML was already optimized")
            
            # Metadata adicional
            logger.info(f"\n📊 OPTIMIZATION METADATA:")
            logger.info(f"  - Table Width: {result.get('table_width', 'N/A')}")
            logger.info(f"  - Estimated Pages: {result.get('estimated_pages', 'N/A')}")
            logger.info(f"  - Quality Score: {result.get('quality_score', 0.0)}")
            
            # Warnings si existen
            warnings = result.get("warnings", [])
            if warnings:
                logger.warning(f"\n⚠️ WARNINGS ({len(warnings)} total):")
                for i, warning in enumerate(warnings, 1):
                    logger.warning(f"  {i}. {warning}")
            
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AI optimization failed: {e}")
            # Fallback: devolver HTML sin optimizar
            return {
                "html_optimized": html_content,
                "table_width": "unknown",
                "estimated_pages": 1,
                "adjustments_made": [],
                "warnings": [f"Optimization failed: {str(e)}"],
                "quality_score": 0.5
            }


# Singleton instance
pdf_optimizer_agent = PDFOptimizerAgent()
