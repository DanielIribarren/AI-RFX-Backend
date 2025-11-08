"""
🤖 Proposal Generator AI Agent
Responsabilidad: Insertar datos del RFX en el template HTML del usuario
Enfoque: Simple - Template + Datos → OpenAI → HTML con datos
"""

import logging
import json
from typing import Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI

from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class ProposalGeneratorAgent:
    """
    Agente especializado en insertar datos en templates HTML
    Arquitectura simple: Template + Datos → LLM → HTML generado
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.client = OpenAI(api_key=self.openai_config.api_key)
    
    async def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera HTML insertando datos del RFX en el template
        
        Args:
            request: {
                "html_template": "<html>...template...</html>",
                "user_id": "uuid",
                "logo_url": "/api/branding/files/{user_id}/logo",
                "data": {
                    "client_name": "Empresa XYZ",
                    "solicitud": "Descripción",
                    "products": [...],
                    "pricing": {...}
                }
            }
        """
        try:
            logger.info("🤖 Proposal Generator Agent - Starting generation")
            
            html_template = request.get("html_template")
            data = request.get("data", {})
            
            if not html_template:
                return {"status": "error", "error": "html_template required", "html_generated": None}
            
            # Mapear datos usando función del service
            mapped_data = self._map_data(data)
            
            # System prompt
            system_prompt = """Eres un sistema de generación de presupuestos HTML.

Tu tarea:
1. Tomar el template HTML proporcionado
2. Insertar los datos del cliente, productos y totales en el template
3. Mantener EXACTAMENTE la estructura, colores y estilos del template original
4. NO inventar datos - usar SOLO los datos proporcionados

Reglas críticas:
- NO cambies colores ni estilos CSS del template
- NO agregues elementos nuevos no solicitados
- Mantén la estructura HTML exacta del template
- Si una variable no tiene valor, usa texto apropiado como "N/A" o deja vacío

⚠️ **CRÍTICO - ESTRUCTURA Y POSICIONAMIENTO:**
- NO modifiques el layout del template (flex, grid, position, etc.)
- NO cambies el orden de los elementos HTML
- NO muevas elementos de su posición original
- Si el template tiene "PRESUPUESTO" en la esquina derecha, DEBE quedar en la esquina derecha
- Si el template usa clases específicas, MANTENLAS exactamente igual
- COPIA la estructura HTML del template, NO la recrees desde cero"""
            
            # User prompt
            user_prompt = f"""# TEMPLATE HTML:

{html_template}

# DATOS DEL PRESUPUESTO:

{json.dumps(mapped_data, indent=2, ensure_ascii=False)}

# INSTRUCCIONES:

Genera el HTML completo del presupuesto insertando los datos en el template.
- Cliente: {mapped_data.get('client_name', 'N/A')}
- Solicitud: {mapped_data.get('solicitud', 'N/A')}
- Productos: {len(mapped_data.get('products', []))} items
- Total: {mapped_data.get('pricing', {}).get('total_formatted', '$0.00')}
- Fecha: {mapped_data.get('current_date', 'N/A')}

⚠️ **CRÍTICO - LOGO PLACEHOLDER:**
El logo se insertará después. DEBES usar este placeholder EXACTO:
<img src="{{{{LOGO_PLACEHOLDER}}}}" alt="Logo" class="logo">

NO modifiques este placeholder. NO uses URLs. NO uses base64.
USA EXACTAMENTE: {{{{LOGO_PLACEHOLDER}}}}

Genera SOLO el HTML completo. NO incluyas markdown (```html)."""
            
            # Llamar OpenAI
            response = self.client.chat.completions.create(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=8000
            )
            
            html_generated = (response.choices[0].message.content or "").strip()
            
            # Limpiar markdown si existe
            if html_generated.startswith("```html"):
                html_generated = html_generated[7:]
            if html_generated.startswith("```"):
                html_generated = html_generated[3:]
            if html_generated.endswith("```"):
                html_generated = html_generated[:-3]
            html_generated = html_generated.strip()
            
            logger.info(f"✅ HTML generated - Length: {len(html_generated)} chars")
            
            return {
                "status": "success",
                "html_generated": html_generated,
                "metadata": mapped_data  # Pasar todos los datos mapeados para validación
            }
            
        except Exception as e:
            logger.error(f"❌ Error in Proposal Generator Agent: {e}")
            return {"status": "error", "error": str(e), "html_generated": None}
    
    def _map_data(self, data: Dict) -> Dict:
        """Mapea datos del RFX al formato esperado (reutiliza lógica del service)"""
        
        # Fechas
        current_date = datetime.now().strftime('%Y-%m-%d')
        validity_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Extraer datos
        client_name = data.get('client_name', 'N/A')
        solicitud = data.get('solicitud', 'N/A')
        products = data.get('products', [])
        pricing = data.get('pricing', {})
        
        mapped = {
            'client_name': client_name,
            'solicitud': solicitud,
            'products': products,
            'pricing': pricing,
            'current_date': current_date,
            'validity_date': validity_date
        }
        
        logger.info(f"📋 Data mapped - Client: {client_name}, Products: {len(products)}, Total: {pricing.get('total_formatted', '$0.00')}")
        
        return mapped
    
    async def regenerate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Regenera HTML corrigiendo issues específicos
        
        Args:
            request: {
                "html_template": "...",
                "previous_html": "...",
                "issues": ["error1", "error2"],
                "data": {...}
            }
        """
        try:
            logger.info(f"🔄 Regenerating with {len(request.get('issues', []))} corrections")
            
            html_template = request.get("html_template")
            issues = request.get("issues", [])
            data = request.get("data", {})
            
            # Mapear datos
            mapped_data = self._map_data(data)
            
            issues_text = "\n".join([f"- {issue}" for issue in issues])
            
            # System prompt
            system_prompt = """Eres un sistema de corrección de presupuestos HTML.

Tu tarea:
1. Corregir los problemas específicos listados
2. Mantener la estructura y estilos del template original
3. Insertar correctamente los datos del presupuesto"""
            
            # User prompt
            user_prompt = f"""# PROBLEMAS A CORREGIR:

{issues_text}

# TEMPLATE ORIGINAL:

{html_template}

# DATOS DEL PRESUPUESTO:

{json.dumps(mapped_data, indent=2, ensure_ascii=False)}

# INSTRUCCIONES:

Genera el HTML corregido:
1. Corrige SOLO los problemas listados arriba
2. Inserta correctamente los datos del presupuesto
3. Mantén la estructura y estilos del template

Genera SOLO el HTML completo. NO incluyas markdown."""
            
            # Llamar OpenAI
            response = self.client.chat.completions.create(
                model=self.openai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            html_corrected = (response.choices[0].message.content or "").strip()
            
            # Limpiar markdown
            if html_corrected.startswith("```html"):
                html_corrected = html_corrected[7:]
            if html_corrected.startswith("```"):
                html_corrected = html_corrected[3:]
            if html_corrected.endswith("```"):
                html_corrected = html_corrected[:-3]
            html_corrected = html_corrected.strip()
            
            return {
                "status": "success",
                "html_generated": html_corrected,
                "metadata": {"corrections_applied": len(issues), "regeneration": True},
                "request_data": mapped_data,
            }
            
        except Exception as e:
            logger.error(f"❌ Error in regeneration: {e}")
            return {"status": "error", "error": str(e), "html_generated": None}


# Singleton instance
proposal_generator_agent = ProposalGeneratorAgent()
