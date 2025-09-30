"""
🤖 BUDY Agent - Agente inteligente único con roles dinámicos
Reemplaza la arquitectura fragmentada con un agente unificado que mantiene contexto continuo
Versión: 1.0 - Workflow Agéntico Unificado
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import openai
from openai import AsyncOpenAI

from backend.prompts.budy_prompts import (
    build_role_prompt, get_role_config, get_available_roles,
    format_context_for_prompt, get_validation_prompt
)
from backend.core.config import get_openai_config
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class BudyAgent:
    """
    🤖 Agente inteligente único que adopta roles dinámicos
    
    Principios fundamentales:
    - Un solo agente, múltiples roles especializados
    - Contexto continuo mantenido durante todo el flujo
    - Inteligencia contextual real vs reglas hardcodeadas
    - Compatibilidad total con endpoints existentes
    """
    
    def __init__(self):
        """Inicializar BudyAgent con configuración y memoria contextual"""
        self.openai_config = get_openai_config()
        self.client = AsyncOpenAI(api_key=self.openai_config.api_key)
        self.db_client = get_database_client()
        
        # Memoria contextual del proyecto actual
        self.project_context = {}
        
        # Historial de interacciones para aprendizaje
        self.interaction_history = []
        
        # Configuración del agente
        self.config = {
            'model': 'gpt-4o',
            'temperature': 0.1,  # Baja para consistencia
            'max_tokens': 4000,
            'timeout': 90  # Aumentado para prompts XML complejos
        }
        
        logger.info("🤖 BudyAgent initialized successfully")
    
    async def analyze_and_extract(self, document: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        🎯 MOMENTO 1: Análisis completo automático
        
        Ejecuta secuencialmente:
        1. ORQUESTRADOR: Analiza contexto y crea estrategia
        2. ANALISTA: Extrae datos usando estrategia del orquestador
        
        Args:
            document: Documento o solicitud del usuario
            metadata: Metadatos adicionales del proyecto
            
        Returns:
            Resultado completo del análisis y extracción
        """
        start_time = datetime.utcnow()
        logger.info(f"🎯 Starting MOMENTO 1: Analyze and Extract")
        
        try:
            # PASO 1A: BUDY-ORQUESTRADOR
            logger.info("🎯 Executing ORCHESTRATOR role")
            orchestration_context = {
                'document': document,
                'metadata': metadata or {},
                'timestamp': start_time.isoformat()
            }
            
            orchestration_result = await self._execute_role('orchestrator', orchestration_context)
            
            # PASO 1B: BUDY-ANALISTA
            logger.info("🔍 Executing ANALYST role")
            analysis_context = {
                'document': document,
                'orchestrator_strategy': orchestration_result,
                'metadata': metadata or {}
            }
            
            analysis_result = await self._execute_role('analyst', analysis_context)
            
            # Almacenar contexto completo para uso futuro
            self.project_context = {
                'document': document,
                'metadata': metadata or {},
                'orchestration': orchestration_result,
                'analysis': analysis_result,
                'momento_1_completed_at': datetime.utcnow().isoformat(),
                'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
            }
            
            # Formatear resultado para compatibilidad con endpoints existentes
            formatted_result = self._format_analysis_for_compatibility(orchestration_result, analysis_result)
            
            logger.info(f"✅ MOMENTO 1 completed successfully in {self.project_context['processing_time_seconds']:.2f}s")
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"❌ MOMENTO 1 failed: {e}")
            # En caso de error, devolver estructura compatible pero con error
            return {
                'status': 'error',
                'message': f'Analysis failed: {str(e)}',
                'extracted_data': {},
                'suggestions': [],
                'ready_for_review': False,
                'error_details': str(e)
            }
    
    async def generate_quote(self, confirmed_data: Dict[str, Any], pricing_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        📝 MOMENTO 3: Generación bajo demanda
        
        Usa TODO el contexto acumulado para generar presupuesto profesional
        
        Args:
            confirmed_data: Datos confirmados/editados por el usuario
            pricing_config: Configuración de pricing personalizada
            
        Returns:
            Presupuesto completo generado
        """
        start_time = datetime.utcnow()
        logger.info(f"📝 Starting MOMENTO 3: Generate Quote")
        
        try:
            # Verificar que tenemos contexto del MOMENTO 1
            if not self.project_context:
                raise ValueError("No context available. Must run analyze_and_extract first.")
            
            # PASO 3: BUDY-GENERADOR
            logger.info("📝 Executing GENERATOR role")
            generation_context = {
                'full_context': self.project_context,
                'confirmed_data': confirmed_data,
                'pricing_config': pricing_config,
                'generation_timestamp': start_time.isoformat()
            }
            
            quote_result = await self._execute_role('generator', generation_context)
            
            # Actualizar contexto con resultado de generación
            self.project_context['quote_generation'] = {
                'result': quote_result,
                'confirmed_data': confirmed_data,
                'pricing_config': pricing_config,
                'generated_at': datetime.utcnow().isoformat(),
                'generation_time_seconds': (datetime.utcnow() - start_time).total_seconds()
            }
            
            # Formatear resultado para compatibilidad
            formatted_quote = self._format_quote_for_compatibility(quote_result)
            
            logger.info(f"✅ MOMENTO 3 completed successfully in {self.project_context['quote_generation']['generation_time_seconds']:.2f}s")
            
            return formatted_quote
            
        except Exception as e:
            logger.error(f"❌ MOMENTO 3 failed: {e}")
            return {
                'status': 'error',
                'message': f'Quote generation failed: {str(e)}',
                'quote': {},
                'metadata': {},
                'error_details': str(e)
            }
    
    async def _execute_role(self, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎭 Ejecuta rol específico manteniendo identidad base
        Ahora con soporte para Function Calling cuando sea apropiado
        
        Args:
            role: Rol a ejecutar ('orchestrator', 'analyst', 'generator')
            context: Contexto específico para el rol
            
        Returns:
            Resultado del rol ejecutado
        """
        logger.info(f"🎭 Executing role: {role}")
        
        try:
            # Obtener configuración del rol
            role_config = get_role_config(role)
            
            # Decidir si usar Function Calling o prompt estándar
            if self._should_use_function_calling(role, context):
                logger.info(f"🛠️ Using Function Calling for {role} role")
                response = await self._execute_with_function_calling(role, context)
            else:
                logger.info(f"💬 Using standard prompt for {role} role")
                response = await self._execute_with_standard_prompt(role, context)
            
            # Registrar interacción para aprendizaje
            self._log_interaction(role, context, response)
            
            logger.info(f"✅ Role {role} executed successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Role {role} execution failed: {e}")
            raise
    
    def _should_use_function_calling(self, role: str, context: Dict[str, Any]) -> bool:
        """
        🤔 Determina si usar Function Calling basado en rol y contexto
        
        Args:
            role: Rol a ejecutar
            context: Contexto del rol
            
        Returns:
            True si debe usar Function Calling
        """
        # Function Calling es especialmente útil para extracción estructurada
        if role == 'analyst':
            # Usar Function Calling si tenemos un documento para analizar
            # y es lo suficientemente largo para beneficiarse de estructura
            document = context.get('document', '')
            if document and len(document) > 1000:  # Documento sustancial
                logger.info(f"📊 Document length: {len(document)} chars - Function Calling recommended")
                return True
        
        # Para otros roles o documentos cortos, usar prompts estándar
        return False
    
    async def _execute_with_function_calling(self, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🛠️ Ejecuta rol usando Function Calling de OpenAI
        
        Args:
            role: Rol a ejecutar
            context: Contexto del rol
            
        Returns:
            Resultado estructurado del Function Calling
        """
        try:
            # Para el rol analyst, usar función de extracción RFX
            if role == 'analyst':
                return await self._execute_analyst_function_calling(context)
            else:
                # Fallback a prompt estándar para otros roles
                return await self._execute_with_standard_prompt(role, context)
                
        except Exception as e:
            logger.warning(f"⚠️ Function Calling failed for {role}, falling back to standard prompt: {e}")
            return await self._execute_with_standard_prompt(role, context)
    
    async def _execute_analyst_function_calling(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔍 Ejecuta análisis usando Function Calling específico para extracción RFX
        
        Args:
            context: Contexto con documento a analizar
            
        Returns:
            Resultado estructurado de la extracción
        """
        document = context.get('document', '')
        orchestrator_strategy = context.get('orchestrator_strategy', {})
        
        # Construir system prompt para Function Calling
        system_prompt = self._build_function_calling_system_prompt(orchestrator_strategy)
        
        # Construir user prompt
        user_prompt = f"""Analiza el siguiente documento RFX y extrae toda la información utilizando la función extract_rfx_data.

DOCUMENTO A ANALIZAR:
{document}

ESTRATEGIA DEL ORQUESTADOR:
{json.dumps(orchestrator_strategy, ensure_ascii=False, indent=2)}

Usa la función extract_rfx_data para proporcionar la respuesta estructurada."""

        # Definir función de extracción
        extraction_function = {
            "type": "function",
            "function": {
                "name": "extract_rfx_data",
                "description": "Extrae información estructurada de documentos RFX/RFP/RFQ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "extracted_data": {
                            "type": "object",
                            "properties": {
                                "project_details": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "scope": {"type": "string"},
                                        "deliverables": {"type": "array", "items": {"type": "string"}},
                                        "industry_domain": {"type": "string"},
                                        "rfx_type_detected": {"type": "string"}
                                    }
                                },
                                "client_information": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "company": {"type": "string"},
                                        "contact": {"type": "string"},
                                        "profile": {"type": "string"}
                                    }
                                },
                                "requested_products": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "product_name": {"type": "string"},
                                            "quantity": {"type": "number"},
                                            "unit": {"type": "string"},
                                            "specifications": {"type": "string"},
                                            "category": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "quality_assessment": {
                            "type": "object",
                            "properties": {
                                "completeness_score": {"type": "number"},
                                "confidence_level": {"type": "number"},
                                "products_confidence": {"type": "number"}
                            }
                        },
                        "reasoning": {"type": "string"}
                    },
                    "required": ["extracted_data", "quality_assessment", "reasoning"]
                }
            }
        }

        # Ejecutar Function Calling
        response = await self.client.chat.completions.create(
            model=self.config['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=[extraction_function],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_rfx_data"}
            },
            temperature=0.1,
            timeout=60
        )

        # Extraer resultado del function call
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_args = tool_call.function.arguments
            
            logger.info(f"✅ Function Calling successful")
            logger.info(f"📊 Function arguments length: {len(function_args)} characters")
            
            # Parsear argumentos JSON
            try:
                result = json.loads(function_args)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse function arguments as JSON: {e}")
                raise
        else:
            raise ValueError("No function call found in OpenAI response")
    
    def _build_function_calling_system_prompt(self, orchestrator_strategy: Dict[str, Any]) -> str:
        """
        🏗️ Construye system prompt optimizado para Function Calling
        Incluye identidad BUDY + estrategia del Orchestrator
        """
        from backend.prompts.budy_prompts import BUDY_SYSTEM_PROMPT
        
        # Extraer información clave de la estrategia
        extraction_strategy = orchestrator_strategy.get('extraction_strategy', {})
        focus_areas = extraction_strategy.get('focus_areas', [])
        data_patterns = extraction_strategy.get('data_patterns_to_look_for', [])
        validation_points = extraction_strategy.get('validation_points', [])
        
        strategy_summary = f"""
ESTRATEGIA DEL ORCHESTRATOR:
- Áreas de enfoque: {', '.join(focus_areas[:3]) if focus_areas else 'General'}
- Patrones a buscar: {', '.join(data_patterns[:3]) if data_patterns else 'Todos'}
- Puntos de validación: {', '.join(validation_points[:3]) if validation_points else 'Estándar'}
"""
        
        return f"""{BUDY_SYSTEM_PROMPT}

🔍 AHORA ACTÚAS COMO ANALISTA EXTRACTOR ESPECIALIZADO

{strategy_summary}

Tu expertise incluye:
- Análisis avanzado de documentos RFX de múltiples industrias
- Extracción de datos estructurados con precisión del 95%+
- Clasificación automática de tipos RFX y dominios industriales
- Manejo robusto de fechas en español
- Diferenciación crítica entre información empresarial vs. personal

Usa la función extract_rfx_data para proporcionar respuestas estructuradas y precisas.
Sigue la estrategia del Orchestrator para enfocar tu extracción."""
    
    async def _execute_with_standard_prompt(self, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        💬 Ejecuta rol usando prompt estándar (método original)
        
        Args:
            role: Rol a ejecutar
            context: Contexto del rol
            
        Returns:
            Resultado parseado del prompt estándar
        """
        # Obtener configuración del rol
        role_config = get_role_config(role)
        
        # Construir prompt completo
        full_prompt = build_role_prompt(role, context)
        
        # Ejecutar llamada a OpenAI
        response = await self._openai_call(full_prompt, role_config)
        
        # Validar y parsear respuesta JSON
        parsed_response = self._parse_and_validate_response(response, role)
        
        return parsed_response
    
    async def _openai_call(self, prompt: str, role_config: Dict[str, Any]) -> str:
        """
        🔌 Ejecuta llamada a OpenAI con configuración optimizada
        
        Args:
            prompt: Prompt completo a enviar
            role_config: Configuración específica del rol
            
        Returns:
            Respuesta de OpenAI
        """
        try:
            # Configuración específica para el rol
            max_tokens = min(role_config.get('estimated_tokens', 2000) * 2, self.config['max_tokens'])
            timeout = role_config.get('timeout_seconds', self.config['timeout'])
            
            # Llamada a OpenAI con timeout
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config['model'],
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    temperature=self.config['temperature'],
                    max_tokens=max_tokens
                ),
                timeout=timeout
            )
            
            content = response.choices[0].message.content
            
            # Log de uso de tokens para optimización
            usage = response.usage
            logger.info(f"📊 OpenAI usage - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")
            
            return content
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ OpenAI call timed out after {timeout}s")
            raise Exception(f"OpenAI call timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"❌ OpenAI call failed: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _parse_and_validate_response(self, response: str, role: str) -> Dict[str, Any]:
        """
        ✅ Parsea y valida respuesta JSON del rol
        
        Args:
            response: Respuesta cruda de OpenAI
            role: Rol que generó la respuesta
            
        Returns:
            Respuesta parseada y validada
        """
        try:
            # Limpiar respuesta de markdown y espacios
            cleaned_response = response.strip()
            
            # Remover markdown JSON wrapper si existe
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            
            # Si aún no es válido, intentar extraer JSON entre llaves
            if not cleaned_response.startswith('{'):
                start = cleaned_response.find('{')
                if start != -1:
                    end = cleaned_response.rfind('}') + 1
                    if end > start:
                        cleaned_response = cleaned_response[start:end]
            
            # Intentar parsear JSON limpio
            parsed = json.loads(cleaned_response)
            
            # Validaciones básicas por rol
            if role == 'orchestrator':
                required_keys = ['analysis', 'context', 'extraction_strategy', 'reasoning']
            elif role == 'analyst':
                required_keys = ['extracted_data', 'inferred_information', 'quality_assessment', 'reasoning']
            elif role == 'generator':
                required_keys = ['quote_metadata', 'quote_structure', 'pricing_breakdown', 'html_content', 'reasoning']
            else:
                required_keys = []
            
            # Verificar claves requeridas
            missing_keys = [key for key in required_keys if key not in parsed]
            if missing_keys:
                logger.warning(f"⚠️ Missing keys in {role} response: {missing_keys}")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON response from {role}: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            
            # Intentar extraer JSON de respuesta parcial
            try:
                # Buscar JSON entre llaves
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != 0:
                    json_part = response[start:end]
                    return json.loads(json_part)
            except:
                pass
            
            # Si no se puede parsear, devolver estructura de error
            return {
                'error': f'Invalid JSON response from {role}',
                'raw_response': response[:1000],
                'reasoning': f'Failed to parse response from {role} role'
            }
    
    def _format_analysis_for_compatibility(self, orchestration: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 Formatea resultado del análisis para compatibilidad con endpoints existentes
        
        Args:
            orchestration: Resultado del orquestrador
            analysis: Resultado del analista
            
        Returns:
            Formato compatible con endpoints legacy
        """
        try:
            # Extraer datos principales
            orchestration_analysis = orchestration.get('analysis', {})
            extracted_data = analysis.get('extracted_data', {})
            quality_assessment = analysis.get('quality_assessment', {})
            
            # Formatear para compatibilidad con /api/rfx/process
            compatible_format = {
                'status': 'success',
                'extracted_data': {
                    # Información básica del proyecto
                    'project_title': extracted_data.get('project_details', {}).get('title', ''),
                    'project_description': extracted_data.get('project_details', {}).get('description', ''),
                    'project_type': orchestration_analysis.get('primary_industry', 'general'),
                    'complexity_score': orchestration_analysis.get('complexity_score', 5),
                    
                    # Información del cliente
                    'client_name': extracted_data.get('client_information', {}).get('name', ''),
                    'client_company': extracted_data.get('client_information', {}).get('company', ''),
                    'client_email': extracted_data.get('client_information', {}).get('contact', ''),
                    
                    # Timeline
                    'start_date': extracted_data.get('timeline', {}).get('start_date', ''),
                    'end_date': extracted_data.get('timeline', {}).get('end_date', ''),
                    'deadline': extracted_data.get('timeline', {}).get('end_date', ''),
                    
                    # Requerimientos
                    'requirements': extracted_data.get('requirements', {}),
                    'scope': extracted_data.get('project_details', {}).get('scope', ''),
                    'deliverables': extracted_data.get('project_details', {}).get('deliverables', []),
                    
                    # Ubicación y logística
                    'location': extracted_data.get('location_logistics', {}).get('primary_location', ''),
                    'service_location': extracted_data.get('location_logistics', {}).get('primary_location', ''),
                    
                    # Presupuesto
                    'estimated_budget': extracted_data.get('budget_financial', {}).get('estimated_budget', ''),
                    'budget_range': orchestration_analysis.get('estimated_budget_range', ''),
                    
                    # Metadatos
                    'industry': orchestration_analysis.get('primary_industry', 'general'),
                    'urgency_level': orchestration_analysis.get('urgency_level', 'medium'),
                    'client_profile': orchestration_analysis.get('client_profile', 'standard'),
                    
                    # Items/productos extraídos
                    'items': extracted_data.get('requested_products', [])
                },
                'suggestions': [
                    f"Proyecto identificado como: {orchestration_analysis.get('primary_industry', 'general')}",
                    f"Nivel de complejidad: {orchestration_analysis.get('complexity_score', 5)}/10",
                    f"Perfil del cliente: {orchestration_analysis.get('client_profile', 'standard')}",
                    f"Urgencia: {orchestration_analysis.get('urgency_level', 'medium')}"
                ] + quality_assessment.get('recommended_questions', []),
                'ready_for_review': True,
                'confidence_score': quality_assessment.get('confidence_level', 8.0),
                'quality_score': quality_assessment.get('completeness_score', 8.0),
                
                # Información adicional para el frontend
                'analysis_metadata': {
                    'primary_industry': orchestration_analysis.get('primary_industry'),
                    'secondary_industries': orchestration_analysis.get('secondary_industries', []),
                    'complexity_score': orchestration_analysis.get('complexity_score'),
                    'implicit_needs': analysis.get('inferred_information', {}).get('implicit_requirements', []),
                    'critical_factors': orchestration.get('context', {}).get('critical_factors', []),
                    'potential_risks': orchestration.get('context', {}).get('potential_risks', [])
                }
            }
            
            return compatible_format
            
        except Exception as e:
            logger.error(f"❌ Error formatting analysis for compatibility: {e}")
            return {
                'status': 'error',
                'message': 'Failed to format analysis results',
                'extracted_data': {},
                'suggestions': [],
                'ready_for_review': False,
                'error_details': str(e)
            }
    
    def _format_quote_for_compatibility(self, quote_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 Formatea resultado del presupuesto para compatibilidad con endpoints existentes
        
        Args:
            quote_result: Resultado del generador
            
        Returns:
            Formato compatible con endpoints legacy
        """
        try:
            quote_metadata = quote_result.get('quote_metadata', {})
            quote_structure = quote_result.get('quote_structure', {})
            pricing_breakdown = quote_result.get('pricing_breakdown', {})
            
            # Formatear para compatibilidad con /api/proposals/generate
            compatible_format = {
                'status': 'success',
                'quote': {
                    # Metadatos del presupuesto
                    'id': str(uuid4()),
                    'quote_number': quote_metadata.get('quote_number', f"QUOTE-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"),
                    'project_title': quote_metadata.get('project_title', ''),
                    'client_name': quote_metadata.get('client_name', ''),
                    'industry': quote_metadata.get('industry', 'general'),
                    
                    # Información financiera
                    'subtotal': pricing_breakdown.get('subtotal', 0),
                    'coordination_amount': pricing_breakdown.get('coordination_fee', 0),
                    'tax_amount': pricing_breakdown.get('tax', 0),
                    'total_amount': pricing_breakdown.get('total', quote_metadata.get('total_amount', 0)),
                    'currency': quote_metadata.get('currency', 'USD'),
                    
                    # Contenido
                    'html_content': quote_result.get('html_content', ''),
                    'sections': quote_structure.get('sections', []),
                    
                    # Términos
                    'valid_until': quote_metadata.get('valid_until', ''),
                    'payment_terms': quote_result.get('terms_and_conditions', {}).get('payment_terms', ''),
                    'delivery_terms': quote_result.get('terms_and_conditions', {}).get('delivery_terms', ''),
                    
                    # Metadatos adicionales
                    'complexity_level': quote_metadata.get('complexity_level', 'medium'),
                    'estimated_duration': quote_metadata.get('estimated_duration', ''),
                    'recommendations': quote_result.get('recommendations', [])
                },
                'metadata': {
                    'generation_method': 'budy_agent',
                    'model_used': self.config['model'],
                    'generation_time': self.project_context.get('quote_generation', {}).get('generation_time_seconds', 0),
                    'reasoning': quote_result.get('reasoning', ''),
                    'quality_indicators': {
                        'context_used': bool(self.project_context),
                        'sections_count': len(quote_structure.get('sections', [])),
                        'total_items': sum(len(section.get('items', [])) for section in quote_structure.get('sections', []))
                    }
                }
            }
            
            return compatible_format
            
        except Exception as e:
            logger.error(f"❌ Error formatting quote for compatibility: {e}")
            return {
                'status': 'error',
                'message': 'Failed to format quote results',
                'quote': {},
                'metadata': {},
                'error_details': str(e)
            }
    
    def _log_interaction(self, role: str, context: Dict[str, Any], response: Dict[str, Any]) -> None:
        """
        📝 Registra interacción para aprendizaje y debugging
        
        Args:
            role: Rol ejecutado
            context: Contexto enviado
            response: Respuesta recibida
        """
        interaction = {
            'timestamp': datetime.utcnow().isoformat(),
            'role': role,
            'context_keys': list(context.keys()),
            'response_keys': list(response.keys()) if isinstance(response, dict) else ['raw_response'],
            'success': 'error' not in response,
            'context_size': len(str(context)),
            'response_size': len(str(response))
        }
        
        self.interaction_history.append(interaction)
        
        # Mantener solo las últimas 50 interacciones para evitar memory leak
        if len(self.interaction_history) > 50:
            self.interaction_history = self.interaction_history[-50:]
    
    def get_project_context(self) -> Dict[str, Any]:
        """
        📊 Obtiene contexto completo del proyecto actual
        
        Returns:
            Contexto completo mantenido por el agente
        """
        return self.project_context.copy()
    
    def clear_project_context(self) -> None:
        """
        🧹 Limpia contexto del proyecto (para nuevo proyecto)
        """
        self.project_context = {}
        logger.info("🧹 Project context cleared")
    
    def get_interaction_history(self) -> List[Dict[str, Any]]:
        """
        📈 Obtiene historial de interacciones para análisis
        
        Returns:
            Historial de interacciones
        """
        return self.interaction_history.copy()
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        💚 Obtiene estado actual del agente
        
        Returns:
            Estado y estadísticas del agente
        """
        return {
            'status': 'active',
            'model': self.config['model'],
            'available_roles': get_available_roles(),
            'has_project_context': bool(self.project_context),
            'interaction_count': len(self.interaction_history),
            'last_activity': self.interaction_history[-1]['timestamp'] if self.interaction_history else None,
            'context_summary': {
                'momento_1_completed': 'momento_1_completed_at' in self.project_context,
                'momento_3_completed': 'quote_generation' in self.project_context,
                'project_industry': self.project_context.get('orchestration', {}).get('analysis', {}).get('primary_industry'),
                'complexity_score': self.project_context.get('orchestration', {}).get('analysis', {}).get('complexity_score')
            }
        }


# =====================================================
# 🌍 INSTANCIA GLOBAL DEL AGENTE
# =====================================================

_budy_agent: Optional[BudyAgent] = None


def get_budy_agent() -> BudyAgent:
    """
    Obtener instancia global del BudyAgent
    
    Returns:
        Instancia única del BudyAgent
    """
    global _budy_agent
    if _budy_agent is None:
        _budy_agent = BudyAgent()
    return _budy_agent


def reset_budy_agent() -> BudyAgent:
    """
    Resetear instancia global del BudyAgent (para testing)
    
    Returns:
        Nueva instancia del BudyAgent
    """
    global _budy_agent
    _budy_agent = BudyAgent()
    return _budy_agent
