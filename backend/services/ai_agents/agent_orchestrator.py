"""
🎭 Agent Orchestrator
Responsabilidad: Coordinar el flujo completo entre los 3 agentes
Flujo: Generator → Validator → (Retry si falla) → PDF Optimizer → HTML Final
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.services.ai_agents.proposal_generator_agent import proposal_generator_agent
from backend.services.ai_agents.template_validator_agent import template_validator_agent
from backend.services.ai_agents.pdf_optimizer_agent import pdf_optimizer_agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orquestador que coordina los 3 agentes especializados
    Maneja el flujo completo de generación de propuestas
    """
    
    def __init__(self):
        self.max_retries = 2  # Máximo de intentos de corrección
    
    async def generate_professional_proposal(
        self,
        html_template: str,
        rfx_data: Dict[str, Any],
        branding_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Flujo completo de generación de propuesta profesional
        
        Args:
            html_template: Template HTML del branding del usuario
            rfx_data: Datos del RFX (cliente, productos, etc.)
            branding_config: Configuración de branding (colores, estilos)
            user_id: ID del usuario
        
        Returns:
            {
                "status": "success" | "error",
                "html_final": "<html>...</html>",
                "metadata": {
                    "generation": {...},
                    "validation": {...},
                    "optimization": {...},
                    "total_time_ms": 1234
                }
            }
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"🎭 Orchestrator - Starting proposal generation for user {user_id}")
            
            # ========================================
            # PASO 1: GENERAR HTML CON AGENTE 1
            # ========================================
            logger.info("📝 Step 1/4: Generating HTML with Proposal Generator Agent")
            
            generator_request = {
                "html_template": html_template,
                "user_id": user_id,
                "logo_url": f"/api/branding/files/{user_id}/logo",
                "data": rfx_data,
                "branding_config": branding_config  # Pasar branding para aplicar colores correctos
            }
            
            generator_response = await proposal_generator_agent.generate(generator_request)
            
            if generator_response["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Generation failed: {generator_response.get('error')}",
                    "html_final": None
                }
            
            html_generated = generator_response["html_generated"]
            request_data = generator_response.get("metadata", {})
            
            # ========================================
            # PASO 2: VALIDAR + AUTO-CORREGIR CON AGENTE 2
            # ========================================
            logger.info("✅ Step 2/4: Validating + Auto-fixing with Validator Agent")
            
            validator_request = {
                "html_generated": html_generated,
                "html_template": html_template,
                "branding_config": branding_config,
                "request_data": request_data  # Datos que deberían estar en el HTML
            }
            
            validator_response = await template_validator_agent.validate(validator_request)
            
            # El validador ahora retorna HTML corregido automáticamente
            html_corrected = validator_response.get("html_corrected", html_generated)
            corrections_made = validator_response.get("corrections_made", [])
            
            if corrections_made:
                logger.info(f"🔧 Validator applied {len(corrections_made)} auto-corrections")
                html_generated = html_corrected  # Usar HTML corregido
            else:
                logger.info("✅ No corrections needed - HTML was perfect")
            
            # ========================================
            # PASO 4: OPTIMIZAR PARA PDF CON AGENTE 3
            # ========================================
            logger.info("🎨 Step 4/4: Optimizing for PDF with PDF Optimizer Agent")
            
            optimizer_request = {
                "html_content": html_generated,
                "validation_results": {
                    "is_valid": validator_response["is_valid"],
                    "corrections_made": corrections_made,
                    "similarity_score": validator_response.get("similarity_score", 0.0),
                    "quality_score": validator_response.get("quality_score", 0.0)
                },
                "branding_config": branding_config,  # Para optimizaciones específicas del branding
                "page_config": {
                    "size": "letter",
                    "orientation": "portrait"
                },
                "quality_requirements": {
                    "professional_spacing": True,
                    "table_centering": True,
                    "min_margin": "15mm",
                    "max_table_width": "190mm"
                }
            }
            
            optimizer_response = await pdf_optimizer_agent.optimize(optimizer_request)
            
            if optimizer_response["status"] != "success":
                logger.warning(f"⚠️ PDF optimization failed - using non-optimized HTML")
                html_final = html_generated
            else:
                html_final = optimizer_response["html_optimized"]
            
            # ========================================
            # PASO 5: INSERTAR LOGO (POST-PROCESSING)
            # ========================================
            logger.info("🖼️ Step 5/5: Inserting logo (post-processing)")
            
            html_final = await self._insert_logo(html_final, user_id)
            
            # ========================================
            # RESULTADO FINAL
            # ========================================
            end_time = datetime.now()
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(f"✅ Orchestrator - Proposal generation complete in {total_time_ms}ms")
            
            return {
                "status": "success",
                "html_final": html_final,
                "metadata": {
                    "generation": generator_response.get("metadata", {}),
                    "validation": {
                        "is_valid": validator_response["is_valid"],
                        "corrections_count": len(corrections_made),
                        "corrections_made": corrections_made[:5],  # Primeras 5 correcciones
                        "similarity_score": validator_response.get("similarity_score", 0.0),
                        "quality_score": validator_response.get("quality_score", 0.0)
                    },
                    "optimization": optimizer_response.get("analysis", {}),
                    "total_time_ms": total_time_ms,
                    "agents_used": ["ProposalGenerator", "ValidatorAutoFix", "PDFOptimizer"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Orchestrator error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "html_final": None
            }
    
    async def generate_default_proposal(
        self,
        rfx_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera propuesta con template por defecto (sin branding personalizado)
        
        Args:
            rfx_data: Datos del RFX
        
        Returns:
            Mismo formato que generate_professional_proposal
        """
        logger.info("📋 Orchestrator - Generating default proposal (no custom branding)")
        
        # Template por defecto de Sabra Corporation
        default_template = self._get_default_template()
        
        default_branding = {
            "primary_color": "#0e2541",
            "secondary_color": "#ffffff",
            "table_header_bg": "#0e2541",
            "table_header_text": "#ffffff",
            "table_border": "#000000"
        }
        
        return await self.generate_professional_proposal(
            html_template=default_template,
            rfx_data=rfx_data,
            branding_config=default_branding,
            user_id="default"
        )
    
    def _get_default_template(self) -> str:
        """Template HTML por defecto de Sabra Corporation"""
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>PRESUPUESTO</title>
<style>
  @page { size: letter; margin: 0; }
  body { font-family: Arial, sans-serif; color: #333; width: 216mm; height: 279mm; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .header { border-bottom: 3pt solid #0e2541; padding: 5mm 10mm; }
  .logo { height: 15mm; }
  .company-info { font-size: 9pt; margin: 3mm 10mm; }
  .dates { text-align: right; font-size: 9pt; margin: 3mm 10mm; }
  .info-label { background: #0e2541; color: white; padding: 2mm 3mm; font-weight: bold; display: inline-block; min-width: 30mm; }
  .info-value { border: 1pt solid #0e2541; padding: 2mm 3mm; display: inline-block; min-width: 120mm; }
  table { width: calc(100% - 20mm); margin: 5mm 10mm; border-collapse: collapse; page-break-inside: auto; }
  thead { display: table-header-group; }
  tr { page-break-inside: avoid; page-break-after: auto; }
  th { background-color: #0e2541; color: #ffffff; padding: 2mm; border: 1pt solid #000; font-weight: bold; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  td { padding: 2mm; border: 1pt solid #000; }
  .comments { padding: 0 10mm; margin: 3mm 0; }
</style>
</head>
<body>
  <div class="header" style="display: flex; justify-content: space-between; align-items: center;">
    <img src="{{LOGO_URL}}" alt="Logo" class="logo">
    <h1 style="font-size: 24pt; color: #0e2541; margin: 0;">PRESUPUESTO</h1>
  </div>
  <div class="company-info">
    <p style="margin: 0;">Av. Principal, C.C Mini Centro Principal</p>
    <p style="margin: 0;">Nivel 1, Local 10, Sector el Pedronal</p>
    <p style="margin: 0;">Lechería, Anzoátegui, Zona Postal 6016</p>
  </div>
  <div class="dates">
    <p style="margin: 0;"><strong>Fecha:</strong> {{CURRENT_DATE}}</p>
    <p style="margin: 0;"><strong>Vigencia:</strong> {{VALIDITY_DATE}}</p>
    <p style="margin: 0;"><strong>Código:</strong> SABRA-PO-2025-XXX</p>
  </div>
  <div style="padding: 0 10mm; margin: 3mm 0;">
    <span class="info-label">Cliente:</span>
    <span class="info-value">{{CLIENT_NAME}}</span>
  </div>
  <div style="padding: 0 10mm; margin: 3mm 0;">
    <span class="info-label">Solicitud:</span>
    <span class="info-value">{{SOLICITUD}}</span>
  </div>
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
{{PRODUCT_ROWS}}
      <tr>
        <td colspan="3"></td>
        <td style="font-weight: bold;">TOTAL</td>
        <td style="font-weight: bold; text-align: right; font-size: 12pt;">{{TOTAL_AMOUNT}}</td>
      </tr>
    </tbody>
  </table>
  <div class="comments">
    <strong>Comentarios:</strong>
    <div style="border: 1pt solid #000; padding: 3mm; min-height: 15mm; margin-top: 2mm;"></div>
  </div>
</body>
</html>
"""
    
    async def _insert_logo(self, html: str, user_id: str) -> str:
        """
        Inserta logo usando URL de Cloudinary (post-processing)
        Reemplaza {{LOGO_PLACEHOLDER}} con URL pública de Cloudinary
        ✅ MIGRADO A CLOUDINARY: Ya no usa rutas locales
        """
        try:
            # Obtener URL de Cloudinary desde BD
            logo_url = await self._get_user_logo_url(user_id)
            
            if not logo_url:
                logger.warning(f"⚠️ No Cloudinary logo URL found for user {user_id}, keeping placeholder")
                return html
            
            # Reemplazar placeholder con URL de Cloudinary
            html_with_logo = html.replace("{{LOGO_PLACEHOLDER}}", logo_url)
            
            # Contar cuántos reemplazos se hicieron
            replacements = html.count("{{LOGO_PLACEHOLDER}}")
            
            logger.info(f"☁️ Logo inserted - {replacements} placeholder(s) replaced with Cloudinary URL: {logo_url}")
            
            return html_with_logo
            
        except Exception as e:
            logger.error(f"❌ Error inserting logo: {e}")
            return html  # Retornar HTML sin logo en caso de error
    
    async def _get_user_logo_url(self, user_id: str) -> Optional[str]:
        """
        Obtiene la URL pública del logo desde Cloudinary (BD)
        ✅ MIGRADO A CLOUDINARY: Ya no busca en filesystem local
        """
        try:
            from backend.core.database import get_database_client
            
            # Obtener URL de Cloudinary desde BD
            db = get_database_client()
            response = db.client.table("company_branding_assets")\
                .select("logo_url")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            
            if not response.data or not response.data[0].get('logo_url'):
                logger.warning(f"⚠️ No Cloudinary logo URL found for user: {user_id}")
                return None
            
            logo_url = response.data[0]['logo_url']
            
            # Verificar que sea URL pública de Cloudinary
            if logo_url and logo_url.startswith('http'):
                logger.info(f"☁️ Cloudinary logo URL retrieved: {logo_url}")
                return logo_url
            else:
                logger.warning(f"⚠️ Invalid logo URL format: {logo_url}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error getting Cloudinary logo URL: {e}")
            return None


# Singleton instance
agent_orchestrator = AgentOrchestrator()
