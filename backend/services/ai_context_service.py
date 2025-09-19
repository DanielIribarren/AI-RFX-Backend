"""
🧠 AI Context Service - Servicio de análisis contextual inteligente
Implementación completa del Día 6 según implementation_plan_a.md

Versión: 1.0 - Integrado con BudyAgent y DatabaseClient
"""
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from backend.models.project_models import (
    ProjectInput, ProjectModel, ProjectTypeEnum, ProjectStatusEnum, PriorityLevel,
    ProjectContextModel, WorkflowStateModel
)
from backend.services.budy_agent import get_budy_agent
from backend.core.database import get_database_client
from backend.core.config import get_openai_config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AIContextService:
    """
    Servicio de análisis contextual inteligente
    Implementa análisis automático de industria, complejidad y generación de workflows
    """
    
    def __init__(self):
        self.openai_config = get_openai_config()
        self.openai_client = AsyncOpenAI(api_key=self.openai_config.api_key)
        self.db_client = get_database_client()
        self.budy_agent = get_budy_agent()
        
        # Cache de configuraciones por industria
        self._industry_configs_cache = {}
        self._workflow_templates_cache = {}
        
        logger.info("🧠 AIContextService initialized successfully")
    
    async def analyze_project_context(
        self, 
        project: ProjectInput, 
        documents_text: str = "",
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Análisis contextual completo del proyecto
        
        Args:
            project: Datos del proyecto a analizar
            documents_text: Texto extraído de documentos
            project_id: ID del proyecto (opcional)
            
        Returns:
            Dict con análisis completo de contexto
        """
        logger.info(f"🧠 Starting context analysis for project: {project.title}")
        
        try:
            # 1. Análisis de industria y complejidad
            industry_analysis = await self._analyze_industry_context(project, documents_text)
            
            # 2. Análisis de complejidad
            complexity_analysis = await self._analyze_complexity(project, documents_text)
            
            # 3. Recomendaciones de estrategia
            strategy_recommendations = await self._generate_strategy_recommendations(
                industry_analysis, complexity_analysis
            )
            
            # 4. Análisis de riesgos
            risk_analysis = await self._analyze_project_risks(project, complexity_analysis)
            
            # 5. Consolidar análisis
            context_analysis = {
                "industry_analysis": industry_analysis,
                "complexity_analysis": complexity_analysis,
                "strategy_recommendations": strategy_recommendations,
                "risk_analysis": risk_analysis,
                "analysis_metadata": {
                    "model_used": self.openai_config.model,
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "service_version": "1.0",
                    "confidence_score": self._calculate_overall_confidence(
                        industry_analysis, complexity_analysis
                    ),
                    "processing_duration_seconds": None  # Will be set by caller
                }
            }
            
            # 6. Guardar en BD si tenemos project_id
            if project_id:
                await self._save_context_analysis(project_id, context_analysis)
            
            confidence = context_analysis['analysis_metadata']['confidence_score']
            logger.info(f"✅ Context analysis completed with confidence: {confidence:.2f}")
            
            return context_analysis
            
        except Exception as e:
            logger.error(f"❌ Error in context analysis: {str(e)}")
            return self._get_fallback_context_analysis(project)
    
    async def _analyze_industry_context(
        self, 
        project: ProjectInput, 
        documents_text: str
    ) -> Dict[str, Any]:
        """Análisis específico de industria usando IA"""
        
        prompt = f"""
        Analiza este proyecto y determina el contexto de industria:
        
        INFORMACIÓN DEL PROYECTO:
        - Título: {project.title}
        - Descripción: {project.description or 'No proporcionada'}
        - Tipo de proyecto: {project.project_type.value}
        - Categoría de servicio: {project.service_category or 'No especificada'}
        - Ubicación: {project.service_location or 'No especificada'}
        - Presupuesto estimado: {project.budget_range_min}-{project.budget_range_max} {project.currency}
        
        DOCUMENTOS ADJUNTOS:
        {documents_text[:2000] if documents_text else 'No hay documentos adjuntos'}
        
        Analiza y responde en JSON con:
        {{
            "detected_industry": "industria_detectada",
            "confidence_score": 0.95,
            "industry_indicators": ["indicador1", "indicador2"],
            "service_category_refined": "categoría_refinada",
            "market_context": {{
                "typical_scope": "descripción del alcance típico",
                "common_challenges": ["desafío1", "desafío2"],
                "success_factors": ["factor1", "factor2"],
                "pricing_patterns": "patrones de pricing típicos",
                "timeline_expectations": "expectativas de timeline"
            }},
            "competitive_landscape": {{
                "market_maturity": "emergente|maduro|saturado",
                "key_differentiators": ["diferenciador1", "diferenciador2"],
                "typical_margins": "rango de márgenes típicos"
            }},
            "reasoning": "explicación detallada del análisis"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Enriquecer con datos del cache/BD
            await self._enrich_industry_analysis(result, project.industry_type)
            
            logger.info(f"🎯 Industry detected: {result.get('detected_industry')} (confidence: {result.get('confidence_score')})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in industry analysis: {str(e)}")
            return self._get_fallback_industry_analysis(project)
    
    async def _analyze_complexity(
        self, 
        project: ProjectInput, 
        documents_text: str
    ) -> Dict[str, Any]:
        """Análisis de complejidad del proyecto"""
        
        # Factores cuantitativos
        complexity_factors = {
            "scope_size": project.estimated_scope_size or 0,
            "budget_range": (project.budget_range_max or 0) - (project.budget_range_min or 0),
            "timeline_pressure": self._calculate_timeline_pressure(project),
            "location_complexity": self._assess_location_complexity(project),
            "requirements_complexity": len(project.requirements.split('.')) if project.requirements else 0,
            "document_complexity": len(documents_text.split()) if documents_text else 0
        }
        
        # Score de complejidad base
        base_complexity_score = self._calculate_complexity_score(complexity_factors)
        
        # Análisis cualitativo con IA
        qualitative_analysis = await self._analyze_qualitative_complexity(project, documents_text)
        
        # Score final combinado
        final_complexity_score = (base_complexity_score * 0.6) + (qualitative_analysis.get('ai_complexity_score', 0.5) * 0.4)
        
        return {
            "complexity_score": round(final_complexity_score, 4),
            "complexity_level": self._get_complexity_level(final_complexity_score),
            "quantitative_factors": complexity_factors,
            "qualitative_analysis": qualitative_analysis,
            "risk_assessment": self._assess_project_risks(project, final_complexity_score),
            "recommended_approach": self._recommend_approach(final_complexity_score),
            "estimated_effort": self._estimate_effort(final_complexity_score, project.industry_type),
            "complexity_breakdown": {
                "technical": qualitative_analysis.get('technical_complexity', 0.5),
                "business": qualitative_analysis.get('business_complexity', 0.5),
                "operational": qualitative_analysis.get('operational_complexity', 0.5)
            }
        }
    
    async def _analyze_qualitative_complexity(
        self, 
        project: ProjectInput, 
        documents_text: str
    ) -> Dict[str, Any]:
        """Análisis cualitativo de complejidad usando IA"""
        
        prompt = f"""
        Analiza la complejidad cualitativa de este proyecto:
        
        PROYECTO:
        - Título: {project.title}
        - Tipo de proyecto: {project.project_type.value}
        - Requerimientos: {project.requirements or 'No especificados'}
        - Presupuesto: {project.budget_range_min}-{project.budget_range_max} {project.currency}
        
        DOCUMENTOS:
        {documents_text[:1500] if documents_text else 'No hay documentos'}
        
        Evalúa y responde en JSON:
        {{
            "ai_complexity_score": 0.75,
            "technical_complexity": 0.8,
            "business_complexity": 0.6,
            "operational_complexity": 0.7,
            "complexity_indicators": ["indicador1", "indicador2"],
            "challenge_areas": ["área1", "área2"],
            "simplification_opportunities": ["oportunidad1", "oportunidad2"],
            "complexity_reasoning": "explicación detallada"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1500
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"❌ Error in qualitative complexity analysis: {str(e)}")
            return {
                "ai_complexity_score": 0.5,
                "technical_complexity": 0.5,
                "business_complexity": 0.5,
                "operational_complexity": 0.5,
                "complexity_reasoning": f"Fallback analysis due to error: {str(e)}"
            }
    
    async def _generate_strategy_recommendations(
        self, 
        industry_analysis: Dict[str, Any], 
        complexity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Genera recomendaciones estratégicas basadas en análisis"""
        
        industry = industry_analysis.get("detected_industry", "general")
        complexity_score = complexity_analysis.get("complexity_score", 0.5)
        complexity_level = complexity_analysis.get("complexity_level", "medium")
        
        # Recomendaciones base por industria
        base_recommendations = await self._get_industry_base_recommendations(industry)
        
        # Ajustes por complejidad
        complexity_adjustments = self._get_complexity_adjustments(complexity_level)
        
        # Recomendaciones específicas
        specific_recommendations = await self._generate_specific_recommendations(
            industry_analysis, complexity_analysis
        )
        
        return {
            "pricing_strategy": self._recommend_pricing_strategy(industry, complexity_score),
            "timeline_strategy": self._recommend_timeline_strategy(complexity_level),
            "resource_strategy": self._recommend_resource_strategy(industry, complexity_score),
            "communication_strategy": self._recommend_communication_strategy(complexity_level),
            "risk_mitigation": self._recommend_risk_mitigation(complexity_analysis),
            "quality_assurance": self._recommend_qa_approach(complexity_level),
            "delivery_approach": self._recommend_delivery_approach(industry, complexity_score),
            "success_metrics": self._define_success_metrics(industry, complexity_level),
            "base_recommendations": base_recommendations,
            "complexity_adjustments": complexity_adjustments,
            "specific_recommendations": specific_recommendations
        }
    
    async def generate_workflow_steps(
        self, 
        project_id: str, 
        context_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Genera pasos de workflow inteligente basado en contexto
        """
        logger.info(f"🔄 Generating intelligent workflow for project: {project_id}")
        
        try:
            industry = context_analysis.get("industry_analysis", {}).get("detected_industry", "general")
            complexity_score = context_analysis.get("complexity_analysis", {}).get("complexity_score", 0.5)
            complexity_level = context_analysis.get("complexity_analysis", {}).get("complexity_level", "medium")
            
            # 1. Obtener template base por industria
            workflow_template = await self._get_industry_workflow_template(industry)
            
            # 2. Ajustar steps según complejidad
            adjusted_steps = self._adjust_workflow_for_complexity(workflow_template, complexity_score)
            
            # 3. Agregar steps específicos basados en análisis
            enhanced_steps = await self._enhance_workflow_with_context(
                adjusted_steps, context_analysis
            )
            
            # 4. Configurar automatización y validaciones
            final_steps = self._configure_workflow_automation(enhanced_steps, complexity_level)
            
            # 5. Guardar steps en BD
            await self._save_workflow_steps(project_id, final_steps)
            
            logger.info(f"✅ Generated {len(final_steps)} workflow steps")
            return final_steps
            
        except Exception as e:
            logger.error(f"❌ Error generating workflow: {str(e)}")
            return await self._get_fallback_workflow_steps(project_id)
    
    async def _get_industry_workflow_template(self, industry: str) -> List[Dict[str, Any]]:
        """Obtiene template de workflow por industria"""
        
        # Intentar obtener de cache
        if industry in self._workflow_templates_cache:
            return self._workflow_templates_cache[industry]
        
        try:
            # Buscar en configuraciones de industria en BD
            config_result = self.db_client.table('industry_configurations')\
                .select('workflow_template')\
                .eq('industry_type', industry)\
                .eq('is_default', True)\
                .eq('is_active', True)\
                .execute()
            
            if config_result.data and config_result.data[0].get('workflow_template'):
                workflow_template = config_result.data[0]['workflow_template']
                self._workflow_templates_cache[industry] = workflow_template
                return workflow_template
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch workflow template from DB: {str(e)}")
        
        # Fallback: workflows predefinidos por industria
        predefined_workflows = {
            "catering": [
                {
                    "step_number": 1,
                    "step_name": "Menu Analysis",
                    "step_type": "data_extraction",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 5,
                    "description": "Extract menu items, dietary restrictions, and service requirements"
                },
                {
                    "step_number": 2,
                    "step_name": "Guest Count Validation",
                    "step_type": "context_analysis",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 10,
                    "description": "Confirm guest count and service style requirements"
                },
                {
                    "step_number": 3,
                    "step_name": "Dietary Restrictions Review",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 15,
                    "description": "Review special dietary needs and allergies"
                },
                {
                    "step_number": 4,
                    "step_name": "Catering Pricing Configuration",
                    "step_type": "pricing_config",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 20,
                    "description": "Configure per-person pricing and service fees"
                },
                {
                    "step_number": 5,
                    "step_name": "Quote Generation",
                    "step_type": "proposal_generation",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 3,
                    "description": "Generate comprehensive catering proposal"
                }
            ],
            "construction": [
                {
                    "step_number": 1,
                    "step_name": "Technical Document Analysis",
                    "step_type": "data_extraction",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 10,
                    "description": "Extract technical specifications and requirements"
                },
                {
                    "step_number": 2,
                    "step_name": "Scope Definition",
                    "step_type": "context_analysis",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 30,
                    "description": "Define project scope and deliverables"
                },
                {
                    "step_number": 3,
                    "step_name": "Engineering Review",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 60,
                    "description": "Technical review by engineering team"
                },
                {
                    "step_number": 4,
                    "step_name": "Construction Pricing",
                    "step_type": "pricing_config",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 45,
                    "description": "Calculate materials, labor, and overhead costs"
                },
                {
                    "step_number": 5,
                    "step_name": "Proposal Generation",
                    "step_type": "proposal_generation",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 5,
                    "description": "Generate detailed construction proposal"
                }
            ],
            "it_services": [
                {
                    "step_number": 1,
                    "step_name": "Technical Requirements Analysis",
                    "step_type": "data_extraction",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 8,
                    "description": "Extract technology stack and integration requirements"
                },
                {
                    "step_number": 2,
                    "step_name": "Architecture Planning",
                    "step_type": "context_analysis",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 45,
                    "description": "Plan system architecture and approach"
                },
                {
                    "step_number": 3,
                    "step_name": "Technical Review",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 30,
                    "description": "Review technical approach and feasibility"
                },
                {
                    "step_number": 4,
                    "step_name": "Development Effort Estimation",
                    "step_type": "pricing_config",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 40,
                    "description": "Estimate development hours and resources"
                },
                {
                    "step_number": 5,
                    "step_name": "Proposal Generation",
                    "step_type": "proposal_generation",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 4,
                    "description": "Generate technical proposal and timeline"
                }
            ],
            "events": [
                {
                    "step_number": 1,
                    "step_name": "Event Requirements Analysis",
                    "step_type": "data_extraction",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 6,
                    "description": "Extract event type, size, and requirements"
                },
                {
                    "step_number": 2,
                    "step_name": "Venue and Logistics Planning",
                    "step_type": "context_analysis",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 25,
                    "description": "Plan venue setup and logistics coordination"
                },
                {
                    "step_number": 3,
                    "step_name": "Event Coordination Review",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 20,
                    "description": "Review event timeline and coordination needs"
                },
                {
                    "step_number": 4,
                    "step_name": "Event Services Pricing",
                    "step_type": "pricing_config",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 25,
                    "description": "Price event services and coordination"
                },
                {
                    "step_number": 5,
                    "step_name": "Event Proposal Generation",
                    "step_type": "proposal_generation",
                    "requires_human_input": False,
                    "auto_proceed": True,
                    "estimated_duration_minutes": 3,
                    "description": "Generate comprehensive event proposal"
                }
            ]
        }
        
        # Workflow genérico para industrias no especificadas
        generic_workflow = [
            {
                "step_number": 1,
                "step_name": "Document Analysis",
                "step_type": "data_extraction",
                "requires_human_input": False,
                "auto_proceed": True,
                "estimated_duration_minutes": 5,
                "description": "Extract key information from documents"
            },
            {
                "step_number": 2,
                "step_name": "Context Analysis", 
                "step_type": "context_analysis",
                "requires_human_input": False,
                "auto_proceed": True,
                "estimated_duration_minutes": 3,
                "description": "Analyze project context and requirements"
            },
            {
                "step_number": 3,
                "step_name": "Human Review",
                "step_type": "human_review", 
                "requires_human_input": True,
                "auto_proceed": False,
                "estimated_duration_minutes": 15,
                "description": "Review extracted information and context"
            },
            {
                "step_number": 4,
                "step_name": "Pricing Configuration",
                "step_type": "pricing_config",
                "requires_human_input": True,
                "auto_proceed": False,
                "estimated_duration_minutes": 10,
                "description": "Configure pricing strategy and rates"
            },
            {
                "step_number": 5,
                "step_name": "Proposal Generation",
                "step_type": "proposal_generation",
                "requires_human_input": False,
                "auto_proceed": True,
                "estimated_duration_minutes": 2,
                "description": "Generate project proposal"
            }
        ]
        
        workflow = predefined_workflows.get(industry, generic_workflow)
        self._workflow_templates_cache[industry] = workflow
        
        return workflow
    
    def _adjust_workflow_for_complexity(
        self, 
        workflow_template: List[Dict[str, Any]], 
        complexity_score: float
    ) -> List[Dict[str, Any]]:
        """Ajusta workflow según el score de complejidad"""
        
        adjusted_steps = []
        
        for step in workflow_template:
            adjusted_step = step.copy()
            
            # Ajustar tiempos según complejidad
            base_duration = step.get("estimated_duration_minutes", 10)
            complexity_multiplier = 1.0 + (complexity_score * 0.8)  # 0% - 80% incremento
            adjusted_duration = int(base_duration * complexity_multiplier)
            adjusted_step["estimated_duration_minutes"] = adjusted_duration
            
            # Para proyectos complejos, agregar más revisiones humanas
            if complexity_score > 0.7:
                if step["step_type"] in ["data_extraction", "context_analysis"]:
                    adjusted_step["requires_human_input"] = True
                    adjusted_step["auto_proceed"] = False
                    adjusted_step["complexity_note"] = "High complexity requires human validation"
            
            # Para proyectos simples, automatizar más pasos
            if complexity_score < 0.3:
                if step["step_type"] == "human_review":
                    adjusted_step["estimated_duration_minutes"] = max(5, adjusted_duration // 2)
                    adjusted_step["complexity_note"] = "Low complexity allows streamlined review"
            
            adjusted_steps.append(adjusted_step)
        
        # Agregar steps adicionales para alta complejidad
        if complexity_score > 0.8:
            additional_steps = [
                {
                    "step_number": len(adjusted_steps) + 1,
                    "step_name": "Complexity Risk Assessment",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 20,
                    "description": "Additional review for high complexity project",
                    "complexity_note": "Added due to high complexity score"
                },
                {
                    "step_number": len(adjusted_steps) + 2,
                    "step_name": "Stakeholder Alignment",
                    "step_type": "human_review",
                    "requires_human_input": True,
                    "auto_proceed": False,
                    "estimated_duration_minutes": 15,
                    "description": "Ensure stakeholder alignment on complex requirements",
                    "complexity_note": "Added due to high complexity score"
                }
            ]
            adjusted_steps.extend(additional_steps)
        
        return adjusted_steps
    
    async def _save_workflow_steps(
        self, 
        project_id: str, 
        workflow_steps: List[Dict[str, Any]]
    ):
        """Guarda pasos de workflow en la base de datos"""
        
        try:
            for step in workflow_steps:
                step_data = {
                    'project_id': project_id,
                    'step_number': step['step_number'],
                    'step_name': step['step_name'],
                    'step_type': step['step_type'],
                    'status': 'pending',
                    'step_config': {
                        'description': step.get('description', ''),
                        'complexity_note': step.get('complexity_note', ''),
                        'industry_specific': step.get('industry_specific', False)
                    },
                    'requires_human_input': step['requires_human_input'],
                    'auto_proceed': step['auto_proceed'],
                    'estimated_duration_minutes': step['estimated_duration_minutes'],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                self.db_client.insert_workflow_state(step_data)
            
            logger.info(f"💾 Saved {len(workflow_steps)} workflow steps for project {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving workflow steps: {str(e)}")
    
    # Helper methods
    def _calculate_timeline_pressure(self, project: ProjectInput) -> float:
        """Calcula presión de cronograma (0-1)"""
        if not project.proposal_deadline:
            return 0.3  # Presión media sin deadline
        
        days_to_deadline = (project.proposal_deadline - datetime.now()).days
        if days_to_deadline <= 0:
            return 1.0  # Máxima presión
        elif days_to_deadline >= 30:
            return 0.1  # Mínima presión
        else:
            return 1.0 - (days_to_deadline / 30.0)
    
    def _assess_location_complexity(self, project: ProjectInput) -> float:
        """Evalúa complejidad de ubicación (0-1)"""
        complexity = 0.0
        
        # Factor de país
        if project.service_country and project.service_country.lower() != 'mexico':
            complexity += 0.3
        
        # Factor de especificidad de ubicación
        if project.service_location:
            if len(project.service_location) > 50:  # Ubicación muy específica
                complexity += 0.2
            elif project.service_city and project.service_state:
                complexity += 0.1
        else:
            complexity += 0.2  # Sin ubicación específica
        
        return min(complexity, 1.0)
    
    def _calculate_complexity_score(self, factors: Dict[str, Any]) -> float:
        """Calcula score de complejidad base (0-1)"""
        weights = {
            "scope_size": 0.20,
            "budget_range": 0.15,
            "timeline_pressure": 0.20,
            "location_complexity": 0.10,
            "requirements_complexity": 0.20,
            "document_complexity": 0.15
        }
        
        normalized_factors = {}
        
        # Normalizar cada factor a 0-1
        normalized_factors["scope_size"] = min(factors["scope_size"] / 1000, 1.0)
        normalized_factors["budget_range"] = min(factors["budget_range"] / 100000, 1.0)
        normalized_factors["timeline_pressure"] = factors["timeline_pressure"]
        normalized_factors["location_complexity"] = factors["location_complexity"]
        normalized_factors["requirements_complexity"] = min(factors["requirements_complexity"] / 20, 1.0)
        normalized_factors["document_complexity"] = min(factors["document_complexity"] / 5000, 1.0)
        
        # Calcular score ponderado
        complexity_score = sum(
            normalized_factors[factor] * weights[factor] 
            for factor in weights.keys()
        )
        
        return round(complexity_score, 4)
    
    def _get_complexity_level(self, complexity_score: float) -> str:
        """Convierte score a nivel descriptivo"""
        if complexity_score <= 0.3:
            return "low"
        elif complexity_score <= 0.7:
            return "medium"
        else:
            return "high"
    
    def _calculate_overall_confidence(
        self, 
        industry_analysis: Dict[str, Any], 
        complexity_analysis: Dict[str, Any]
    ) -> float:
        """Calcula confianza general del análisis"""
        industry_confidence = industry_analysis.get('confidence_score', 0.5)
        complexity_confidence = 0.8  # Alta confianza en análisis cuantitativo
        
        # Promedio ponderado
        overall_confidence = (industry_confidence * 0.6) + (complexity_confidence * 0.4)
        
        return round(overall_confidence, 3)
    
    async def _save_context_analysis(self, project_id: str, analysis: Dict[str, Any]):
        """Guardar análisis contextual en BD"""
        
        try:
            analysis_record = {
                "project_id": project_id,
                "detected_industry": analysis["industry_analysis"].get("detected_industry"),
                "detected_complexity": analysis["complexity_analysis"].get("complexity_score"),
                "confidence_score": analysis["analysis_metadata"].get("confidence_score"),
                "market_context": analysis["industry_analysis"].get("market_context", {}),
                "recommended_pricing_strategy": analysis["strategy_recommendations"].get("pricing_strategy"),
                "analysis_model": self.openai_config.model,
                "analysis_timestamp": analysis["analysis_metadata"]["analysis_timestamp"],
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.db_client.insert_project_context(project_id, {
                'context_type': 'ai_contextual_analysis',
                'context_data': analysis_record,
                'created_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"💾 Context analysis saved for project: {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving context analysis: {str(e)}")
    
    # Fallback methods
    def _get_fallback_context_analysis(self, project: ProjectInput) -> Dict[str, Any]:
        """Análisis de contexto fallback en caso de error"""
        return {
            "industry_analysis": self._get_fallback_industry_analysis(project),
            "complexity_analysis": {
                "complexity_score": 0.5,
                "complexity_level": "medium",
                "complexity_reasoning": "Fallback analysis due to processing error"
            },
            "strategy_recommendations": {
                "pricing_strategy": "time_and_materials",
                "timeline_strategy": "standard",
                "fallback_note": "Basic recommendations due to analysis error"
            },
            "analysis_metadata": {
                "model_used": "fallback",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "confidence_score": 0.3,
                "service_version": "1.0-fallback"
            }
        }
    
    def _get_fallback_industry_analysis(self, project: ProjectInput) -> Dict[str, Any]:
        """Análisis de industria fallback"""
        return {
            "detected_industry": project.industry_type.value,
            "confidence_score": 0.3,
            "industry_indicators": ["declared_industry"],
            "service_category_refined": project.service_category or "general",
            "market_context": {
                "typical_scope": "Variable según proyecto",
                "common_challenges": ["Definición de scope", "Gestión de expectativas"],
                "success_factors": ["Comunicación clara", "Entrega a tiempo"]
            },
            "reasoning": "Fallback analysis based on declared industry type"
        }
    
    async def _get_fallback_workflow_steps(self, project_id: str) -> List[Dict[str, Any]]:
        """Workflow fallback básico"""
        return [
            {
                "step_number": 1,
                "step_name": "Basic Document Review",
                "step_type": "human_review",
                "requires_human_input": True,
                "auto_proceed": False,
                "estimated_duration_minutes": 15,
                "description": "Manual review of project documents"
            },
            {
                "step_number": 2,
                "step_name": "Basic Pricing Setup",
                "step_type": "pricing_config",
                "requires_human_input": True,
                "auto_proceed": False,
                "estimated_duration_minutes": 10,
                "description": "Basic pricing configuration"
            },
            {
                "step_number": 3,
                "step_name": "Simple Proposal Generation",
                "step_type": "proposal_generation",
                "requires_human_input": False,
                "auto_proceed": True,
                "estimated_duration_minutes": 5,
                "description": "Generate basic proposal"
            }
        ]


# Singleton instance
_ai_context_service_instance = None

def get_ai_context_service() -> AIContextService:
    """Get global AI context service instance"""
    global _ai_context_service_instance
    if _ai_context_service_instance is None:
        _ai_context_service_instance = AIContextService()
    return _ai_context_service_instance


# Convenience alias
ai_context_service = get_ai_context_service
