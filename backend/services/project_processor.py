"""
🎯 Project Processor Service - Servicio generalizado para procesamiento de proyectos
(anteriormente RFXProcessorService)

Versión: 3.0 - Integrado con BudyAgent y IA Contextual
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID

from backend.models.project_models import (
    ProjectInput, ProjectModel, ProjectTypeEnum, ProjectStatusEnum, PriorityLevel,
    ProjectContextModel, WorkflowStateModel
)
from backend.services.budy_agent import get_budy_agent
from backend.core.database import get_database_client
from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)


class ProjectProcessorService:
    """
    Servicio generalizado para procesamiento de proyectos
    Integra BudyAgent para análisis inteligente y procesamiento contextual
    """
    
    def __init__(self):
        self.budy_agent = get_budy_agent()
        self.db_client = get_database_client()
        self.openai_config = get_openai_config()
        
        # Configuraciones por industria
        self.industry_configs = {
            ProjectTypeEnum.CATERING: {
                "focus_fields": ["estimated_scope_size", "dietary_restrictions", "service_style"],
                "scope_unit": "people",
                "critical_dates": ["service_start_date", "proposal_deadline"],
                "complexity_factors": ["guest_count", "dietary_restrictions", "service_complexity"],
                "extraction_strategy": "catering_focused"
            },
            ProjectTypeEnum.CONSTRUCTION: {
                "focus_fields": ["materials", "labor_requirements", "timeline"],
                "scope_unit": "square_meters", 
                "critical_dates": ["project_start_date", "project_end_date"],
                "complexity_factors": ["project_size", "technical_requirements", "regulatory_compliance"],
                "extraction_strategy": "construction_focused"
            },
            ProjectTypeEnum.CONSULTING: {
                "focus_fields": ["technology_stack", "team_size", "methodology"],
                "scope_unit": "hours",
                "critical_dates": ["project_start_date", "delivery_deadline"],
                "complexity_factors": ["technical_complexity", "integration_requirements", "scalability_needs"],
                "extraction_strategy": "consulting_focused"
            },
            ProjectTypeEnum.EVENTS: {
                "focus_fields": ["event_type", "attendees", "venue_requirements"],
                "scope_unit": "attendees",
                "critical_dates": ["event_date", "setup_date"],
                "complexity_factors": ["attendee_count", "venue_complexity", "technical_requirements"],
                "extraction_strategy": "events_focused"
            },
            ProjectTypeEnum.GENERAL: {
                "focus_fields": ["scope", "requirements", "deliverables"],
                "scope_unit": "units",
                "critical_dates": ["start_date", "delivery_date"],
                "complexity_factors": ["scope_size", "technical_requirements", "timeline_constraints"],
                "extraction_strategy": "general_purpose"
            }
        }
        
        logger.info("🚀 ProjectProcessorService initialized with BudyAgent integration")
    
    async def process_project_documents(
        self, 
        project_input: ProjectInput, 
        files: List[Any],
        metadata: Dict[str, Any] = None
    ) -> ProjectModel:
        """
        Procesa documentos de proyecto usando IA contextual (BudyAgent)
        
        Args:
            project_input: Datos básicos del proyecto
            files: Archivos a procesar
            metadata: Metadatos adicionales
            
        Returns:
            ProjectModel: Proyecto procesado con análisis contextual
        """
        logger.info(f"🚀 Processing project: {project_input.title}")
        logger.info(f"📊 Project Type: {project_input.project_type}")
        logger.info(f"📄 Files: {len(files) if files else 0}")
        
        try:
            # 1. Preparar contexto para BudyAgent
            processing_context = self._prepare_processing_context(project_input, metadata)
            
            # 2. Extraer texto de archivos si están presentes
            document_text = await self._extract_text_from_files(files) if files else ""
            
            # 3. Análisis con BudyAgent (MOMENTO 1)
            budy_result = await self.budy_agent.analyze_and_extract(
                document=document_text,
                metadata=processing_context
            )
            
            # 4. Análisis contextual específico por industria
            context_analysis = await self._analyze_project_context(project_input, budy_result)
            
            # 5. Crear modelo de proyecto enriquecido
            project_model = await self._build_enriched_project_model(
                project_input, budy_result, context_analysis
            )
            
            # 6. Guardar contexto en BD
            await self._save_project_context(project_model.id, context_analysis)
            
            logger.info(f"✅ Project processing completed: {project_model.id}")
            return project_model
            
        except Exception as e:
            logger.error(f"❌ Error processing project: {str(e)}")
            # Fallback: crear proyecto básico sin análisis avanzado
            return self._create_fallback_project_model(project_input)
    
    async def _prepare_processing_context(
        self, 
        project_input: ProjectInput, 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Prepara contexto específico para el procesamiento"""
        
        industry_config = self.industry_configs.get(
            project_input.project_type, 
            self.industry_configs[ProjectTypeEnum.GENERAL]
        )
        
        context = {
            "project_id": getattr(project_input, 'id', None),
            "project_type": project_input.project_type.value,
            "extraction_strategy": industry_config["extraction_strategy"],
            "focus_fields": industry_config["focus_fields"],
            "scope_unit": industry_config["scope_unit"],
            "critical_dates": industry_config["critical_dates"],
            "processing_timestamp": datetime.utcnow().isoformat(),
            "processor_version": "3.0",
            **(metadata or {})
        }
        
        logger.info(f"🧠 Processing context prepared for project type: {project_input.project_type}")
        return context
    
    async def _extract_text_from_files(self, files: List[Any]) -> str:
        """Extrae texto de los archivos subidos"""
        try:
            # Implementación simplificada - en producción usar extractores específicos
            extracted_texts = []
            
            for file in files:
                if hasattr(file, 'read'):
                    # FileStorage object
                    content = file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='ignore')
                    extracted_texts.append(content)
                elif isinstance(file, dict):
                    # Dictionary with content
                    content = file.get('content', file.get('text', ''))
                    extracted_texts.append(str(content))
                else:
                    # String content
                    extracted_texts.append(str(file))
            
            combined_text = "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(extracted_texts)
            logger.info(f"📄 Extracted {len(combined_text)} characters from {len(files)} files")
            
            return combined_text[:50000]  # Limit to 50k chars for processing
            
        except Exception as e:
            logger.error(f"❌ Error extracting text from files: {str(e)}")
            return ""
    
    async def _analyze_project_context(
        self, 
        project_input: ProjectInput, 
        budy_result: Dict[str, Any]
    ) -> ProjectContextModel:
        """Análisis contextual específico del proyecto"""
        
        try:
            extracted_data = budy_result.get('extracted_data', {})
            quality_assessment = budy_result.get('quality_assessment', {})
            
            # Detectar tipo de proyecto y cliente basado en el análisis
            detected_project_type = self._detect_project_type_from_analysis(extracted_data)
            detected_client_type = self._detect_client_type_from_analysis(extracted_data)
            
            # Calcular score de complejidad
            complexity_score = self._calculate_complexity_score(project_input, extracted_data)
            
            # Extraer insights estructurados
            key_requirements = self._extract_key_requirements(extracted_data)
            implicit_needs = self._extract_implicit_needs(extracted_data)
            risk_factors = self._assess_risk_factors(project_input, extracted_data)
            
            context_model = ProjectContextModel(
                project_id=getattr(project_input, 'id', None),
                detected_project_type=detected_project_type,
                detected_client_type=detected_client_type,
                complexity_score=complexity_score,
                key_requirements=key_requirements,
                implicit_needs=implicit_needs,
                risk_factors=risk_factors,
                analysis_confidence=quality_assessment.get('confidence_level', 0.5),
                analysis_reasoning=f"Analysis based on {project_input.industry_type} industry patterns",
                ai_model_used=self.openai_config.model,
                tokens_consumed=budy_result.get('metadata', {}).get('tokens_used', 0),
                analyzed_at=datetime.utcnow()
            )
            
            logger.info(f"🧠 Context analysis completed - Complexity: {complexity_score:.2f}")
            return context_model
            
        except Exception as e:
            logger.error(f"❌ Error in context analysis: {str(e)}")
            # Fallback context
            return ProjectContextModel(
                project_id=getattr(project_input, 'id', None),
                complexity_score=0.5,
                analysis_confidence=0.3,
                analysis_reasoning="Fallback analysis due to processing error",
                analyzed_at=datetime.utcnow()
            )
    
    def _calculate_complexity_score(
        self, 
        project_input: ProjectInput, 
        extracted_data: Dict[str, Any]
    ) -> float:
        """Calcula score de complejidad del proyecto (0-1)"""
        
        factors = {
            "scope_size": 0.0,
            "budget_range": 0.0,
            "timeline_pressure": 0.0,
            "requirements_complexity": 0.0,
            "technical_complexity": 0.0
        }
        
        # Factor de tamaño
        if project_input.estimated_scope_size:
            factors["scope_size"] = min(project_input.estimated_scope_size / 1000, 1.0)
        
        # Factor de presupuesto
        if project_input.budget_range_min and project_input.budget_range_max:
            budget_range = project_input.budget_range_max - project_input.budget_range_min
            factors["budget_range"] = min(budget_range / 100000, 1.0)
        
        # Factor de cronograma
        if project_input.proposal_deadline:
            days_to_deadline = (project_input.proposal_deadline - datetime.now()).days
            factors["timeline_pressure"] = max(0, min(1.0, (30 - days_to_deadline) / 30))
        
        # Factor de complejidad de requerimientos
        requirements_text = project_input.requirements or ""
        requirements_length = len(requirements_text.split())
        factors["requirements_complexity"] = min(requirements_length / 500, 1.0)
        
        # Factor técnico basado en tipo de proyecto
        project_complexity = {
            ProjectTypeEnum.CONSTRUCTION: 0.8,
            ProjectTypeEnum.CONSULTING: 0.9,
            ProjectTypeEnum.EVENTS: 0.6,
            ProjectTypeEnum.CATERING: 0.4,
            ProjectTypeEnum.GENERAL: 0.5
        }
        factors["technical_complexity"] = project_complexity.get(
            project_input.project_type, 0.5
        )
        
        # Calcular score ponderado
        weights = {
            "scope_size": 0.25,
            "budget_range": 0.20,
            "timeline_pressure": 0.20,
            "requirements_complexity": 0.20,
            "technical_complexity": 0.15
        }
        
        complexity_score = sum(
            factors[factor] * weights[factor] 
            for factor in weights.keys()
        )
        
        return round(complexity_score, 4)
    
    def _extract_key_requirements(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae requerimientos clave del análisis"""
        requirements = []
        
        # Requerimientos funcionales
        functional_reqs = extracted_data.get('requirements', {}).get('functional', [])
        for req in functional_reqs:
            requirements.append({
                "type": "functional",
                "description": req,
                "priority": "high",
                "source": "extracted"
            })
        
        # Requerimientos técnicos
        technical_reqs = extracted_data.get('requirements', {}).get('technical', [])
        for req in technical_reqs:
            requirements.append({
                "type": "technical", 
                "description": req,
                "priority": "medium",
                "source": "extracted"
            })
        
        return requirements[:10]  # Limitar a 10 más importantes
    
    def _extract_implicit_needs(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae necesidades implícitas no expresadas directamente"""
        implicit_needs = []
        
        # Basado en el tipo de proyecto y patrones comunes
        project_details = extracted_data.get('project_details', {})
        industry = project_details.get('industry_domain', 'general')
        
        if industry == 'catering':
            implicit_needs.extend([
                {"need": "dietary_restrictions_handling", "probability": 0.8},
                {"need": "service_staff_coordination", "probability": 0.7},
                {"need": "equipment_logistics", "probability": 0.6}
            ])
        elif industry == 'events':
            implicit_needs.extend([
                {"need": "venue_setup_coordination", "probability": 0.9},
                {"need": "technical_support", "probability": 0.7},
                {"need": "contingency_planning", "probability": 0.8}
            ])
        
        return implicit_needs
    
    def _assess_risk_factors(
        self, 
        project_input: ProjectInput, 
        extracted_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evalúa factores de riesgo del proyecto"""
        risks = []
        
        # Riesgo de cronograma
        if project_input.proposal_deadline:
            days_to_deadline = (project_input.proposal_deadline - datetime.now()).days
            if days_to_deadline < 7:
                risks.append({
                    "type": "timeline",
                    "description": "Cronograma muy ajustado para propuesta",
                    "severity": "high",
                    "probability": 0.8
                })
        
        # Riesgo de presupuesto
        if not project_input.budget_range_min:
            risks.append({
                "type": "budget",
                "description": "Presupuesto no definido",
                "severity": "medium", 
                "probability": 0.6
            })
        
        # Riesgo de complejidad
        if len(project_input.requirements or "") > 1000:
            risks.append({
                "type": "complexity",
                "description": "Requerimientos extensos y complejos",
                "severity": "medium",
                "probability": 0.7
            })
        
        return risks
    
    async def _build_enriched_project_model(
        self,
        project_input: ProjectInput,
        budy_result: Dict[str, Any],
        context_analysis: ProjectContextModel
    ) -> ProjectModel:
        """Construye modelo de proyecto enriquecido con análisis"""
        
        extracted_data = budy_result.get('extracted_data', {})
        project_details = extracted_data.get('project_details', {})
        client_info = extracted_data.get('client_information', {})
        
            # Crear ProjectModel con datos enriquecidos
        project_model = ProjectModel(
            id=getattr(project_input, 'id', None),
            name=project_details.get('title', project_input.title),
            description=project_details.get('description', project_input.description),
            project_type=project_input.project_type,
            complexity_score=context_analysis.complexity_score,
            status=ProjectStatusEnum.ANALYZED,  # Estado después del análisis
            priority=PriorityLevel.MEDIUM,
            
            # Información del cliente (enriquecida)
            client_name=client_info.get('name', ''),
            client_company=client_info.get('company', ''),
            client_email=client_info.get('email', ''),
            client_phone=client_info.get('phone', ''),
            
            # Fechas (priorizando datos extraídos)
            proposal_deadline=project_input.proposal_deadline,
            service_start_date=project_input.service_start_date,
            service_end_date=project_input.service_end_date,
            
            # Presupuesto
            budget_range_min=project_input.budget_range_min,
            budget_range_max=project_input.budget_range_max,
            currency=project_input.currency,
            
            # Ubicación
            service_location=project_input.service_location,
            service_city=project_input.service_city,
            service_state=project_input.service_state,
            service_country=project_input.service_country,
            
            # Alcance enriquecido
            estimated_scope_size=project_input.estimated_scope_size,
            scope_unit=project_input.scope_unit,
            service_category=project_input.service_category,
            target_audience=project_input.target_audience,
            
            # Análisis y contexto
            requirements=project_input.requirements,
            requirements_confidence=budy_result.get('quality_assessment', {}).get('confidence_level', 0.5),
            context_analysis=context_analysis.dict() if context_analysis else {},
            
            # Metadatos de procesamiento
            metadata_json={
                "processing_method": "budy_agent_v1.0",
                "industry_detected": project_details.get('industry_domain'),
                "extraction_confidence": budy_result.get('quality_assessment', {}).get('confidence_level'),
                "processing_timestamp": datetime.utcnow().isoformat(),
                "budy_agent_version": "1.0"
            },
            
            # Timestamps
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=getattr(project_input, 'created_by', None),
            organization_id=getattr(project_input, 'organization_id', None)
        )
        
        return project_model
    
    async def _save_project_context(
        self, 
        project_id: Optional[UUID], 
        context_analysis: ProjectContextModel
    ):
        """Guarda contexto del proyecto en BD"""
        if not project_id:
            return
            
        try:
            context_data = {
                'project_id': str(project_id),
                'context_type': 'ai_analysis',
                'context_data': context_analysis.dict(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.db_client.insert_project_context(project_id, context_data)
            logger.info(f"💾 Project context saved for: {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving project context: {str(e)}")
    
    def _create_fallback_project_model(self, project_input: ProjectInput) -> ProjectModel:
        """Crea modelo de proyecto básico como fallback"""
        return ProjectModel(
            id=getattr(project_input, 'id', None),
            name=project_input.title,
            description=project_input.description,
            project_type=project_input.project_type,
            complexity_score=0.5,  # Score medio por defecto
            status=ProjectStatusEnum.DRAFT,
            priority=PriorityLevel.MEDIUM,
            
            # Datos básicos del input
            proposal_deadline=project_input.proposal_deadline,
            service_start_date=project_input.service_start_date,
            service_end_date=project_input.service_end_date,
            budget_range_min=project_input.budget_range_min,
            budget_range_max=project_input.budget_range_max,
            currency=project_input.currency,
            service_location=project_input.service_location,
            service_city=project_input.service_city,
            service_state=project_input.service_state,
            service_country=project_input.service_country,
            estimated_scope_size=project_input.estimated_scope_size,
            scope_unit=project_input.scope_unit,
            service_category=project_input.service_category,
            target_audience=project_input.target_audience,
            requirements=project_input.requirements,
            requirements_confidence=0.3,  # Baja confianza sin análisis
            
            # Metadatos mínimos
            metadata_json={
                "processing_method": "fallback",
                "processing_timestamp": datetime.utcnow().isoformat(),
                "note": "Created without AI analysis due to processing error"
            },
            
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=getattr(project_input, 'created_by', None),
            organization_id=getattr(project_input, 'organization_id', None)
        )


# Mantener backward compatibility
RFXProcessorService = ProjectProcessorService


# Singleton factory function
_project_processor_instance = None

def get_project_processor() -> ProjectProcessorService:
    """Get global project processor instance"""
    global _project_processor_instance
    if _project_processor_instance is None:
        _project_processor_instance = ProjectProcessorService()
    return _project_processor_instance
