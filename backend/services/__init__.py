"""
Servicios del backend para el sistema de proyectos modernizado.
Incluye servicios legacy de RFX y nuevos servicios de IA contextual.
"""

from .domain_detector import (
    DomainDetectorService,
    detect_rfx_domain,
    is_domain_supported,
    get_recommended_evaluators_for_domain
)
from .evaluation_orchestrator import (
    EvaluationOrchestrator,
    create_evaluation_orchestrator,
    evaluate_rfx_intelligently
)
from .budy_agent import (
    BudyAgent,
    get_budy_agent
)
from .project_processor import (
    ProjectProcessorService,
    get_project_processor,
    # Legacy alias
    RFXProcessorService
)
from .ai_context_service import (
    AIContextService,
    get_ai_context_service,
    ai_context_service
)

__all__ = [
    # Legacy RFX services
    'DomainDetectorService',
    'detect_rfx_domain',
    'is_domain_supported',
    'get_recommended_evaluators_for_domain',
    'EvaluationOrchestrator',
    'create_evaluation_orchestrator',
    'evaluate_rfx_intelligently',
    
    # Modern AI services
    'BudyAgent',
    'get_budy_agent',
    'ProjectProcessorService',
    'get_project_processor',
    'RFXProcessorService',  # Legacy alias
    'AIContextService',
    'get_ai_context_service',
    'ai_context_service'
]
