"""
🤖 AI Agents Package - Sistema de Agentes Especializados para Generación de Propuestas

Arquitectura de 3 Agentes:
1. ProposalGeneratorAgent - Inserta datos en template HTML del usuario
2. TemplateValidatorAgent - Valida consistencia con branding original
3. PDFOptimizerAgent - Optimiza HTML para conversión PDF profesional

Comunicación: JSON entre agentes
Orquestador: AgentOrchestrator coordina el flujo completo
"""

from backend.services.ai_agents.proposal_generator_agent import ProposalGeneratorAgent
from backend.services.ai_agents.template_validator_agent import TemplateValidatorAgent
from backend.services.ai_agents.pdf_optimizer_agent import PDFOptimizerAgent
from backend.services.ai_agents.agent_orchestrator import AgentOrchestrator
from backend.services.ai_agents.rfx_orchestrator_agent import RFXOrchestratorAgent

__all__ = [
    'ProposalGeneratorAgent',
    'TemplateValidatorAgent',
    'PDFOptimizerAgent',
    'AgentOrchestrator',
    'RFXOrchestratorAgent',
]
