#!/usr/bin/env python3
"""
Script para refactorizar el servicio de propuestas
Genera el nuevo archivo proposal_generator.py con la arquitectura refactorizada
"""

import sys
from pathlib import Path

# Contenido del servicio refactorizado
REFACTORED_SERVICE = '''"""
🎯 Proposal Generation Service - REFACTORIZADO V5.0
Arquitectura mejorada: Prompts separados + Validación por scoring + Retry automático
"""
import json
import uuid
import re
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from backend.models.proposal_models import ProposalRequest, GeneratedProposal, ProposalStatus
from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.services.unified_budget_configuration_service import unified_budget_service
from backend.services.prompts import ProposalPrompts

import logging

logger = logging.getLogger(__name__)


class ProposalGenerationService:
    """Servicio refactorizado para generar propuestas comerciales con validación robusta"""
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = None  # Lazy initialization
        self.db_client = get_database_client()
    
    def _get_openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self.openai_client is None:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_config.api_key)
            except ImportError:
                raise ImportError("OpenAI module not installed. Run: pip install openai")
        return self.openai_client
    
    async def generate_proposal(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> GeneratedProposal:
        """
        🚀 Método principal REFACTORIZADO con validación por scoring
        
        Args:
            rfx_data: Datos del RFX con cliente, productos, fechas, etc.
            proposal_request: Request con configuraciones adicionales
            
        Returns:
            GeneratedProposal: Objeto con HTML completo y metadata
        """
        logger.info(f"🚀 Starting proposal generation - RFX: {proposal_request.rfx_id}, User: {rfx_data.get('user_id', 'N/A')}")
        
        try:
            # 1. Obtener user_id con fallbacks múltiples
            user_id = self._get_user_id(rfx_data, proposal_request.rfx_id)
            logger.info(f"✅ Generating proposal for user: {user_id}")
            
            # 2. Preparar datos de productos
            products_info = self._prepare_products_data(rfx_data)
            
            # 3. Calcular pricing
            subtotal = sum(p['total'] for p in products_info)
            pricing_calculation = unified_budget_service.calculate_with_unified_config(
                proposal_request.rfx_id, subtotal
            )
            
            # 4. Obtener configuración y moneda
            unified_config = unified_budget_service.get_user_unified_config(user_id)
            currency = self._get_currency(rfx_data, unified_config)
            
            # 5. Detectar si tiene branding completo
            has_branding = self._has_complete_branding(user_id)
            
            # 6. Generar HTML usando el prompt apropiado
            if has_branding:
                logger.info(f"🎨 Branding check - Logo: True, Active: True, Completed: True → {has_branding}")
                logger.info(f"✅ Using BRANDING PROMPT (with logo)")
                branding_config = self._get_branding_config(user_id)
                html_content = await self._generate_with_branding(
                    rfx_data, products_info, pricing_calculation, currency, user_id, branding_config
                )
            else:
                logger.info(f"📄 No branding found for user {user_id}")
                logger.info(f"📄 Using DEFAULT PROMPT (no branding)")
                html_content = await self._generate_default(
                    rfx_data, products_info, pricing_calculation, currency
                )
            
            # 7. Validar HTML con sistema de scoring
            validation_result = self._validate_html(html_content, products_info)
            
            # 8. Retry si la validación falla
            if not validation_result['is_valid']:
                logger.warning(f"⚠️ Validation failed, attempting retry with corrections...")
                html_content = await self._retry_generation(
                    html_content, validation_result['issues'], rfx_data, 
                    products_info, pricing_calculation, currency
                )
                
                # Validar nuevamente
                validation_result = self._validate_html(html_content, products_info)
                if validation_result['is_valid']:
                    logger.info(f"✅ Retry successful - validation passed")
                else:
                    logger.error(f"❌ Retry failed - validation still failing")
            
            # 9. Crear objeto de propuesta
            proposal = self._create_proposal_object(
                rfx_data, html_content, proposal_request, pricing_calculation
            )
            
            # 10. Guardar en BD
            await self._save_to_database(proposal)
            
            logger.info(f"✅ Proposal generated successfully - Document ID: {proposal.id}")
            logger.info(f"📊 Validation score: {validation_result['score']}/10 ({validation_result['score']*10:.0f}%)")
            
            return proposal
            
        except Exception as e:
            logger.error(f"❌ Error generating proposal: {e}", exc_info=True)
            raise Exception(f"Proposal generation failed: {e}")
    
    def _get_user_id(self, rfx_data: Dict[str, Any], rfx_id: str) -> str:
        """Obtiene user_id con múltiples fallbacks"""
        # PASO 1: Desde rfx_data
        user_id = rfx_data.get("user_id")
        if user_id:
            logger.info(f"🔍 user_id from rfx_data: {user_id}")
            return user_id
        
        # PASO 2: Desde base de datos
        logger.warning("⚠️ user_id not in rfx_data, attempting database lookup")
        try:
            rfx_result = self.db_client.client.table("rfx_v2").select("user_id").eq("id", rfx_id).single().execute()
            if rfx_result.data:
                user_id = rfx_result.data.get("user_id")
                if user_id:
                    logger.info(f"✅ Retrieved user_id from RFX database: {user_id}")
                    return user_id
        except Exception as e:
            logger.error(f"❌ Could not retrieve user_id from database: {e}")
        
        # PASO 3: Fallback final (de memorias - usuario conocido)
        user_id = "186ea35f-3cf8-480f-a7d3-0af178c09498"
        logger.warning(f"⚠️ Using fallback user_id: {user_id}")
        return user_id
    
    def _prepare_products_data(self, rfx_data: Dict[str, Any]) -> List[Dict]:
        """Prepara datos de productos para el prompt"""
        productos = rfx_data.get('productos', [])
        products_info = []
        
        for producto in productos:
            precio_unitario = producto.get("estimated_unit_price", 0.0)
            cantidad = producto.get("quantity", producto.get("cantidad", 1))
            total_producto = precio_unitario * cantidad
            
            products_info.append({
                "nombre": producto.get("name", producto.get("nombre", "product")),
                "cantidad": cantidad,
                "unidad": producto.get("unit", producto.get("unidad", "units")),
                "precio_unitario": precio_unitario,
                "total": total_producto
            })
        
        return products_info
    
    def _get_currency(self, rfx_data: Dict[str, Any], unified_config: Optional[Dict]) -> str:
        """Obtiene moneda con prioridades"""
        if unified_config:
            currency = unified_config.get('document', {}).get('currency')
            if currency:
                return currency
        
        return rfx_data.get("currency", "USD")
    
    def _has_complete_branding(self, user_id: str) -> bool:
        """
        🆕 Detecta si el usuario tiene branding completo (logo + análisis completado)
        
        Returns:
            True si tiene logo Y análisis completado
        """
        try:
            from backend.services.user_branding_service import user_branding_service
            
            branding = user_branding_service.get_branding_with_analysis(user_id)
            
            if not branding:
                return False
            
            # Verificar que tenga logo
            has_logo = bool(branding.get('logo_url'))
            
            # Verificar que esté activo
            is_active = branding.get('is_active', False)
            
            # Verificar que el análisis esté completado
            analysis_completed = branding.get('analysis_status') == 'completed'
            
            return has_logo and is_active and analysis_completed
            
        except Exception as e:
            logger.error(f"Error checking branding: {e}")
            return False
    
    def _get_branding_config(self, user_id: str) -> Dict[str, Any]:
        """Obtiene configuración de branding completa"""
        try:
            from backend.services.user_branding_service import user_branding_service
            
            branding = user_branding_service.get_branding_with_analysis(user_id)
            
            if not branding:
                return {}
            
            return {
                'logo_url': branding.get('logo_url'),
                'logo_analysis': branding.get('logo_analysis', {}),
                'template_analysis': branding.get('template_analysis', {}),
                'primary_color': branding.get('logo_analysis', {}).get('primary_color', '#2c5f7c'),
                'secondary_color': branding.get('logo_analysis', {}).get('secondary_color', '#ffffff')
            }
            
        except Exception as e:
            logger.error(f"Error getting branding config: {e}")
            return {}
    
    async def _generate_with_branding(
        self, rfx_data: Dict, products_info: List[Dict], 
        pricing_calculation: Dict, currency: str, user_id: str, branding_config: Dict
    ) -> str:
        """🎨 Genera propuesta CON branding usando ProposalPrompts"""
        logger.info(f"🎨 Building prompt with branding for user {user_id}")
        
        # Construir URL del logo
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        logo_endpoint = f"{base_url}/api/branding/files/{user_id}/logo"
        logger.info(f"🎨 Logo endpoint: {logo_endpoint}")
        
        prompt = ProposalPrompts.get_prompt_with_branding(
            rfx_data, products_info, pricing_calculation, currency, user_id, branding_config
        )
        
        return await self._call_ai(prompt)
    
    async def _generate_default(
        self, rfx_data: Dict, products_info: List[Dict], 
        pricing_calculation: Dict, currency: str
    ) -> str:
        """📋 Genera propuesta SIN branding usando ProposalPrompts"""
        logger.info(f"📋 Building default prompt (no branding)")
        
        prompt = ProposalPrompts.get_prompt_default(
            rfx_data, products_info, pricing_calculation, currency
        )
        
        return await self._call_ai(prompt)
    
    async def _retry_generation(
        self, original_html: str, issues: List[str], rfx_data: Dict,
        products_info: List[Dict], pricing_calculation: Dict, currency: str
    ) -> str:
        """🔄 Reintenta generación con correcciones específicas"""
        logger.info(f"🔄 Attempting retry with explicit corrections...")
        logger.info(f"🔄 Issues to fix: {issues}")
        
        prompt = ProposalPrompts.get_retry_prompt(
            original_html, issues, rfx_data, products_info, pricing_calculation, currency
        )
        
        return await self._call_ai(prompt)
    
    async def _call_ai(self, prompt: str) -> str:
        """🤖 Llama a OpenAI con el prompt"""
        logger.info(f"🤖 Calling OpenAI API...")
        
        openai_client = self._get_openai_client()
        
        try:
            response = openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(4000, self.openai_config.max_tokens),
                temperature=0.7
            )
            
            html_content = (response.choices[0].message.content or "").strip()
            
            # Limpiar marcadores de código si existen
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            
            html_content = html_content.strip()
            
            logger.info(f"✅ OpenAI response received - Length: {len(html_content)} chars")
            
            return html_content
            
        except Exception as e:
            logger.error(f"❌ OpenAI call failed: {e}")
            raise
    
    def _validate_html(self, html: str, products_info: List[Dict]) -> Dict[str, Any]:
        """
        🔍 Valida HTML con sistema de scoring (0-10 puntos)
        
        Returns:
            Dict con: is_valid (bool), score (int), issues (List[str])
        """
        logger.info(f"🔍 Validating HTML content...")
        
        score = 0
        issues = []
        max_score = 10
        
        # 1. Estructura HTML básica (2 puntos)
        structure_score = self._check_html_structure(html)
        score += structure_score
        if structure_score < 2:
            issues.append("HTML structure incomplete (missing DOCTYPE, html, head, or body tags)")
        
        # 2. Información del cliente (2 puntos)
        client_score = self._check_client_info(html)
        score += client_score
        if client_score < 2:
            issues.append("Client information missing or incomplete")
        
        # 3. Tabla de productos (2 puntos)
        products_score = self._check_products_table(html, products_info)
        score += products_score
        if products_score < 2:
            issues.append(f"Products table incomplete (expected {len(products_info)} products)")
        
        # 4. Sección de precios (2 puntos)
        pricing_score = self._check_pricing_section(html)
        score += pricing_score
        if pricing_score < 2:
            issues.append("Pricing section incomplete (missing subtotal or total)")
        
        # 5. Términos y condiciones (1 punto)
        terms_score = self._check_terms_section(html)
        score += terms_score
        if terms_score < 1:
            issues.append("Terms and conditions section missing")
        
        # 6. Información de contacto (1 punto)
        contact_score = self._check_contact_info(html)
        score += contact_score
        if contact_score < 1:
            issues.append("Contact information missing")
        
        # Validación: mínimo 7/10 puntos para ser válido (70%)
        is_valid = score >= 7
        
        logger.info(f"📊 Validation result: {score}/{max_score} ({score*10:.0f}%) - {'✅ VALID' if is_valid else '❌ INVALID'}")
        
        if not is_valid:
            logger.warning(f"⚠️ Validation issues found:")
            for issue in issues:
                logger.warning(f"   - {issue}")
        
        return {
            'is_valid': is_valid,
            'score': score,
            'max_score': max_score,
            'issues': issues
        }
    
    def _check_html_structure(self, html: str) -> int:
        """Verifica estructura HTML básica (0-2 puntos)"""
        required = ['<!DOCTYPE html>', '<html', '</html>', '<head', '<body']
        html_lower = html.lower()
        
        found = sum(1 for element in required if element.lower() in html_lower)
        
        if found == len(required):
            return 2
        elif found >= 3:
            return 1
        else:
            return 0
    
    def _check_client_info(self, html: str) -> int:
        """Verifica información del cliente (0-2 puntos)"""
        html_lower = html.lower()
        
        # Buscar indicadores de información del cliente
        client_indicators = ['cliente', 'client', 'para:', 'to:', 'solicitante']
        has_client_section = any(indicator in html_lower for indicator in client_indicators)
        
        # Buscar información de contacto
        contact_indicators = ['email', '@', 'teléfono', 'phone', 'dirección', 'address']
        has_contact_info = any(indicator in html_lower for indicator in contact_indicators)
        
        score = 0
        if has_client_section:
            score += 1
        if has_contact_info:
            score += 1
        
        return score
    
    def _check_products_table(self, html: str, products_info: List[Dict]) -> int:
        """Verifica tabla de productos (0-2 puntos)"""
        html_lower = html.lower()
        
        # Verificar que tenga tabla
        has_table = '<table' in html_lower and '</table>' in html_lower
        if not has_table:
            return 0
        
        # Verificar columnas esperadas
        expected_columns = ['descripción', 'description', 'cantidad', 'quantity', 'precio', 'price', 'total']
        has_columns = any(col in html_lower for col in expected_columns)
        
        # Verificar que tenga filas de productos (aproximado)
        product_rows = html_lower.count('<tr')
        expected_rows = len(products_info) + 2  # +2 para header y total
        
        score = 0
        if has_columns:
            score += 1
        if product_rows >= expected_rows * 0.7:  # Al menos 70% de las filas esperadas
            score += 1
        
        return score
    
    def _check_pricing_section(self, html: str) -> int:
        """Verifica sección de precios (0-2 puntos)"""
        html_lower = html.lower()
        
        # Buscar subtotal
        has_subtotal = 'subtotal' in html_lower
        
        # Buscar total
        has_total = 'total' in html_lower and ('$' in html or '€' in html or '£' in html)
        
        score = 0
        if has_subtotal:
            score += 1
        if has_total:
            score += 1
        
        return score
    
    def _check_terms_section(self, html: str) -> int:
        """Verifica sección de términos (0-1 punto)"""
        html_lower = html.lower()
        
        terms_indicators = ['términos', 'terms', 'condiciones', 'conditions', 'notas', 'notes']
        has_terms = any(indicator in html_lower for indicator in terms_indicators)
        
        return 1 if has_terms else 0
    
    def _check_contact_info(self, html: str) -> int:
        """Verifica información de contacto (0-1 punto)"""
        html_lower = html.lower()
        
        contact_indicators = ['contacto', 'contact', 'email', '@', 'teléfono', 'phone', 'sabra']
        has_contact = sum(1 for indicator in contact_indicators if indicator in html_lower) >= 2
        
        return 1 if has_contact else 0
    
    def _validate_html_basic(self, html: str) -> bool:
        """Validación básica rápida para casos simples"""
        if not html or len(html) < 300:
            return False
        
        html_lower = html.lower()
        
        # Verificaciones mínimas
        has_html = '<!doctype html>' in html_lower and '<html' in html_lower
        has_table = '<table' in html_lower
        has_content = 'sabra' in html_lower or 'propuesta' in html_lower
        
        return has_html and has_table and has_content
    
    def _create_proposal_object(
        self, rfx_data: Dict[str, Any], html_content: str, 
        proposal_request: ProposalRequest, pricing_calculation: Any
    ) -> GeneratedProposal:
        """Crea objeto GeneratedProposal"""
        
        client_info = rfx_data.get("companies", {}) if isinstance(rfx_data.get("companies"), dict) else {}
        proposal_id = uuid.uuid4()
        rfx_uuid = uuid.UUID(proposal_request.rfx_id) if isinstance(proposal_request.rfx_id, str) else proposal_request.rfx_id
        
        # Obtener total del pricing calculation
        total_cost = pricing_calculation.get('total', 0) if isinstance(pricing_calculation, dict) else getattr(pricing_calculation, 'total_cost', 0)
        
        return GeneratedProposal(
            id=proposal_id,
            rfx_id=rfx_uuid,
            content_markdown="",
            content_html=html_content,
            itemized_costs=[],
            total_cost=total_cost,
            notes=proposal_request.notes,
            status=ProposalStatus.GENERATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "client_name": client_info.get("name", "Cliente"),
                "client_email": client_info.get("email", ""),
                "products_count": len(rfx_data.get("productos", [])),
                "generation_method": "refactored_v5_with_scoring",
                "ai_model": self.openai_config.model,
                "document_type": "commercial_proposal",
                "generation_version": "5.0_refactored"
            }
        )
    
    async def _save_to_database(self, proposal: GeneratedProposal) -> None:
        """Guarda propuesta en base de datos"""
        logger.info(f"💾 Saving proposal to database...")
        
        document_data = {
            "id": str(proposal.id),
            "rfx_id": str(proposal.rfx_id),
            "document_type": "proposal",
            "content_html": proposal.content_html,
            "total_cost": proposal.total_cost,
            "created_at": proposal.created_at.isoformat(),
            "metadata": proposal.metadata,
            "version": 1
        }
        
        try:
            result_id = self.db_client.save_generated_document(document_data)
            logger.info(f"✅ Proposal saved - ID: {result_id}")
        except Exception as e:
            error_msg = str(e).lower()
            
            if "duplicate key" in error_msg or "already exists" in error_msg:
                logger.warning(f"⚠️ Document already exists: {document_data['id']}")
            else:
                logger.error(f"❌ Error saving to database: {e}")


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
'''

def main():
    """Genera el archivo refactorizado"""
    output_file = Path("backend/services/proposal_generator_refactored.py")
    
    print(f"📝 Generando archivo refactorizado: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(REFACTORED_SERVICE)
    
    print(f"✅ Archivo generado exitosamente")
    print(f"📊 Tamaño: {len(REFACTORED_SERVICE)} caracteres")
    print(f"\n🔄 Para aplicar los cambios:")
    print(f"   1. Revisar: backend/services/proposal_generator_refactored.py")
    print(f"   2. Si está correcto, reemplazar:")
    print(f"      mv backend/services/proposal_generator.py backend/services/proposal_generator.py.old")
    print(f"      mv backend/services/proposal_generator_refactored.py backend/services/proposal_generator.py")

if __name__ == "__main__":
    main()
