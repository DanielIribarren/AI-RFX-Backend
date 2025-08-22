"""
Módulo de evaluación para el sistema RFX AI Agent.
Proporciona clases base y evaluadores especializados para validar respuestas del agente.

Arquitectura escalable:
- BaseEvaluator: Clase base para todos los evaluadores
- Generic Evaluators: Funcionan para cualquier tipo de RFX/industria
- Extraction Evaluators: Especializados en productos de catering
- Factory Pattern: Creación dinámica de evaluadores
"""

from .base_evaluator import BaseEvaluator, EvaluationResult, EvaluatorFactory

# Evaluadores genéricos (universales)
from .generic_evals import (
    CompletenessEvaluator,
    FormatValidationEvaluator, 
    ConsistencyEvaluator,
    evaluate_completeness,
    evaluate_format_validation,
    evaluate_consistency,
    register_generic_evaluators
)

# Evaluadores específicos de extracción (catering)
from .extraction_evals import (
    ProductCountEvaluator, 
    ProductQualityEvaluator,
    evaluate_product_count,
    evaluate_product_quality,
    register_extraction_evaluators
)

__version__ = '1.1.0'  # Bumped para refactorización arquitectónica

__all__ = [
    # Base system
    'BaseEvaluator',
    'EvaluationResult', 
    'EvaluatorFactory',
    
    # Generic evaluators (universal)
    'CompletenessEvaluator',
    'FormatValidationEvaluator',
    'ConsistencyEvaluator',
    'evaluate_completeness',
    'evaluate_format_validation', 
    'evaluate_consistency',
    
    # Extraction evaluators (catering-specific)
    'ProductCountEvaluator',
    'ProductQualityEvaluator',
    'evaluate_product_count',
    'evaluate_product_quality'
]

# Auto-registro de todos los evaluadores
register_generic_evaluators()
register_extraction_evaluators()