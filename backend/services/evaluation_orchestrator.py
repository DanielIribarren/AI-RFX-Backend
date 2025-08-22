"""
Evaluador Orquestador Inteligente para RFX.
Combina detección automática de dominio con evaluación completa e inteligente.
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from backend.services.domain_detector import detect_rfx_domain, get_recommended_evaluators_for_domain
from backend.evals.base_evaluator import BaseEvaluator, EvaluationResult, EvaluatorFactory
from backend.evals.generic_evals import (
    CompletenessEvaluator,
    FormatValidationEvaluator, 
    ConsistencyEvaluator
)
from backend.evals.extraction_evals import (
    ProductCountEvaluator,
    ProductQualityEvaluator
)
from backend.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class EvaluationOrchestrator:
    """
    Orquestador inteligente que coordina la evaluación completa de RFX.
    
    Flujo:
    1. 🔍 Detecta automáticamente el dominio del RFX
    2. 🎯 Selecciona evaluadores apropiados (genéricos + específicos)
    3. ⚡ Ejecuta evaluación completa en paralelo
    4. 📊 Consolida y puntúa resultados
    5. 🎨 Genera reporte comprehensivo
    """
    
    def __init__(self):
        self.debug_mode = FeatureFlags.eval_debug_enabled()
        
        # Inicializar evaluadores genéricos (siempre disponibles)
        self.generic_evaluators = {
            'completeness': CompletenessEvaluator(),
            'format_validation': FormatValidationEvaluator(),
            'consistency': ConsistencyEvaluator()
        }
        
        # Inicializar evaluadores específicos por dominio
        self.domain_specific_evaluators = {
            'catering': {
                'product_count': ProductCountEvaluator(),
                'product_quality': ProductQualityEvaluator()
            }
            # Otros dominios se agregarán cuando implementemos sus evaluadores
        }
        
        # Configuración de pesos para scoring consolidado
        self.scoring_weights = {
            'generic': 0.7,  # Evaluadores genéricos peso 70%
            'domain_specific': 0.3  # Evaluadores específicos peso 30%
        }
        
        if self.debug_mode:
            logger.info(f"🎛️ Orquestador inicializado - Genéricos: {len(self.generic_evaluators)}, Específicos: {sum(len(evals) for evals in self.domain_specific_evaluators.values())}")
    
    def evaluate_rfx_complete(self, rfx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa un RFX de manera completa e inteligente.
        
        Args:
            rfx_data: Datos del RFX a evaluar
            
        Returns:
            Dict con evaluación completa:
            {
                'domain_detection': {...},
                'generic_evaluation': {...},
                'domain_specific_evaluation': {...},
                'consolidated_score': float,
                'recommendations': [...],
                'execution_summary': {...}
            }
        """
        
        start_time = datetime.now()
        client_name = rfx_data.get('solicitante') or rfx_data.get('nombre_solicitante', 'Unknown')
        logger.info(f"🚀 Iniciando evaluación completa de RFX: {client_name}")
        
        try:
            # 1. 🔍 DETECTAR DOMINIO AUTOMÁTICAMENTE
            if self.debug_mode:
                logger.info("🔍 Paso 1: Detectando dominio automáticamente...")
            
            domain_info = detect_rfx_domain(rfx_data)
            logger.info(f"🎯 Dominio detectado: {domain_info['primary_domain']} (confianza: {domain_info['confidence']:.2f})")
            
            # 2. ⚡ EJECUTAR EVALUADORES GENÉRICOS (siempre)
            if self.debug_mode:
                logger.info("⚡ Paso 2: Ejecutando evaluadores genéricos...")
            
            generic_results = self._run_generic_evaluators(rfx_data)
            
            # 3. 🎨 EJECUTAR EVALUADORES ESPECÍFICOS (si disponibles)
            if self.debug_mode:
                logger.info(f"🎨 Paso 3: Ejecutando evaluadores específicos para dominio: {domain_info['primary_domain']}")
            
            domain_specific_results = self._run_domain_specific_evaluators(
                rfx_data, 
                domain_info['primary_domain']
            )
            
            # 4. 📊 CONSOLIDAR PUNTUACIONES
            if self.debug_mode:
                logger.info("📊 Paso 4: Consolidando puntuaciones...")
            
            consolidated_score = self._calculate_consolidated_score(
                generic_results, 
                domain_specific_results
            )
            
            # 5. 💡 GENERAR RECOMENDACIONES
            if self.debug_mode:
                logger.info("💡 Paso 5: Generando recomendaciones inteligentes...")
            
            recommendations = self._generate_recommendations(
                rfx_data,
                domain_info,
                generic_results,
                domain_specific_results,
                consolidated_score
            )
            
            # 6. 📈 CREAR RESUMEN DE EJECUCIÓN
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_summary = {
                'execution_time_seconds': round(execution_time, 3),
                'evaluators_executed': len(generic_results) + len(domain_specific_results),
                'domain_detected': domain_info['primary_domain'],
                'domain_confidence': domain_info['confidence'],
                'overall_quality': self._categorize_quality(consolidated_score),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Evaluación completada en {execution_time:.2f}s - Score: {consolidated_score:.3f} ({execution_summary['overall_quality']})")
            
            return {
                'domain_detection': domain_info,
                'generic_evaluation': {
                    'results': generic_results,
                    'score': self._calculate_category_score(generic_results),
                    'count': len(generic_results)
                },
                'domain_specific_evaluation': {
                    'results': domain_specific_results,
                    'score': self._calculate_category_score(domain_specific_results),
                    'count': len(domain_specific_results),
                    'domain': domain_info['primary_domain']
                },
                'consolidated_score': consolidated_score,
                'recommendations': recommendations,
                'execution_summary': execution_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error en evaluación completa: {str(e)}")
            raise Exception(f"Error en evaluación de RFX: {str(e)}")
    
    def _run_generic_evaluators(self, rfx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta todos los evaluadores genéricos."""
        
        results = []
        
        for eval_name, evaluator in self.generic_evaluators.items():
            try:
                start_time = datetime.now()
                
                if self.debug_mode:
                    logger.debug(f"🔧 Ejecutando evaluador genérico: {eval_name}")
                
                result = evaluator.evaluate(rfx_data)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                results.append({
                    'evaluator': eval_name,
                    'category': 'generic',
                    'score': result.score,
                    'passed': result.passed,
                    'threshold': result.threshold,
                    'details': result.details,
                    'execution_time': round(execution_time, 3),
                    'timestamp': result.timestamp.isoformat()
                })
                
                if self.debug_mode:
                    logger.debug(f"✅ {eval_name}: {result.score:.3f} ({'PASS' if result.passed else 'FAIL'})")
                
            except Exception as e:
                logger.error(f"❌ Error en evaluador {eval_name}: {str(e)}")
                results.append({
                    'evaluator': eval_name,
                    'category': 'generic',
                    'score': 0.0,
                    'passed': False,
                    'threshold': 0.8,
                    'details': {'error': str(e), 'exception_type': type(e).__name__},
                    'execution_time': 0.0,
                    'timestamp': datetime.now().isoformat()
                })
        
        logger.info(f"📊 Evaluadores genéricos completados: {len(results)} ejecutados")
        return results
    
    def _run_domain_specific_evaluators(self, rfx_data: Dict[str, Any], domain: str) -> List[Dict[str, Any]]:
        """Ejecuta evaluadores específicos del dominio detectado."""
        
        results = []
        
        # Verificar si tenemos evaluadores específicos para este dominio
        if domain not in self.domain_specific_evaluators:
            logger.info(f"ℹ️ No hay evaluadores específicos implementados para dominio: {domain}")
            return results
        
        domain_evaluators = self.domain_specific_evaluators[domain]
        
        for eval_name, evaluator in domain_evaluators.items():
            try:
                start_time = datetime.now()
                
                if self.debug_mode:
                    logger.debug(f"🎯 Ejecutando evaluador específico: {eval_name} (dominio: {domain})")
                
                result = evaluator.evaluate(rfx_data)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                results.append({
                    'evaluator': eval_name,
                    'category': 'domain_specific',
                    'domain': domain,
                    'score': result.score,
                    'passed': result.passed,
                    'threshold': result.threshold,
                    'details': result.details,
                    'execution_time': round(execution_time, 3),
                    'timestamp': result.timestamp.isoformat()
                })
                
                if self.debug_mode:
                    logger.debug(f"✅ {eval_name}: {result.score:.3f} ({'PASS' if result.passed else 'FAIL'})")
                
            except Exception as e:
                logger.error(f"❌ Error en evaluador específico {eval_name}: {str(e)}")
                results.append({
                    'evaluator': eval_name,
                    'category': 'domain_specific',
                    'domain': domain,
                    'score': 0.0,
                    'passed': False,
                    'threshold': 0.8,
                    'details': {'error': str(e), 'exception_type': type(e).__name__},
                    'execution_time': 0.0,
                    'timestamp': datetime.now().isoformat()
                })
        
        logger.info(f"🎯 Evaluadores específicos ({domain}) completados: {len(results)} ejecutados")
        return results
    
    def _calculate_consolidated_score(self, generic_results: List[Dict], domain_results: List[Dict]) -> float:
        """Calcula score consolidado con pesos configurables."""
        
        generic_score = self._calculate_category_score(generic_results)
        domain_score = self._calculate_category_score(domain_results) if domain_results else 1.0
        
        # Aplicar pesos configurados
        consolidated = (
            generic_score * self.scoring_weights['generic'] +
            domain_score * self.scoring_weights['domain_specific']
        )
        
        if self.debug_mode:
            logger.debug(f"📊 Scores: genérico={generic_score:.3f} (peso {self.scoring_weights['generic']}), específico={domain_score:.3f} (peso {self.scoring_weights['domain_specific']}) → consolidado={consolidated:.3f}")
        
        return round(consolidated, 3)
    
    def _calculate_category_score(self, results: List[Dict]) -> float:
        """Calcula score promedio de una categoría de evaluadores."""
        
        if not results:
            return 1.0
        
        valid_scores = [r['score'] for r in results if isinstance(r['score'], (int, float))]
        
        if not valid_scores:
            return 0.0
            
        return round(sum(valid_scores) / len(valid_scores), 3)
    
    def _generate_recommendations(self, 
                                 rfx_data: Dict[str, Any],
                                 domain_info: Dict[str, Any], 
                                 generic_results: List[Dict],
                                 domain_results: List[Dict],
                                 consolidated_score: float) -> List[Dict[str, Any]]:
        """Genera recomendaciones inteligentes basadas en los resultados."""
        
        recommendations = []
        
        # 1. Recomendaciones basadas en score consolidado
        if consolidated_score < 0.5:
            recommendations.append({
                'type': 'critical',
                'category': 'overall_quality',
                'title': 'RFX requiere revisión crítica',
                'description': f'Score general bajo ({consolidated_score:.3f}). Revisar campos requeridos y formatos.',
                'priority': 'high',
                'score_impact': 'high'
            })
        elif consolidated_score < 0.7:
            recommendations.append({
                'type': 'warning',
                'category': 'overall_quality', 
                'title': 'RFX puede mejorarse',
                'description': f'Score moderado ({consolidated_score:.3f}). Considerar optimizaciones.',
                'priority': 'medium',
                'score_impact': 'medium'
            })
        elif consolidated_score >= 0.9:
            recommendations.append({
                'type': 'success',
                'category': 'overall_quality',
                'title': 'RFX de excelente calidad',
                'description': f'Score alto ({consolidated_score:.3f}). RFX bien estructurado y completo.',
                'priority': 'info',
                'score_impact': 'none'
            })
        
        # 2. Recomendaciones específicas por evaluador con score bajo
        all_results = generic_results + domain_results
        
        for result in all_results:
            if result['score'] < 0.6:
                category_label = 'genérico' if result['category'] == 'generic' else f"específico ({result.get('domain', 'unknown')})"
                recommendations.append({
                    'type': 'improvement',
                    'category': result['evaluator'],
                    'title': f'Mejorar {result["evaluator"]}',
                    'description': f'Evaluador {category_label} con score bajo ({result["score"]:.3f}). Revisar detalles específicos.',
                    'priority': 'high' if result['score'] < 0.4 else 'medium',
                    'score_impact': 'high' if result['score'] < 0.4 else 'medium',
                    'details': result['details']
                })
        
        # 3. Recomendaciones basadas en dominio detectado
        domain = domain_info['primary_domain']
        confidence = domain_info['confidence']
        
        if confidence < 0.5:
            recommendations.append({
                'type': 'info',
                'category': 'domain_detection',
                'title': 'Dominio no está claramente definido',
                'description': f'Confianza baja ({confidence:.3f}) en detección de dominio. Considerar especificar categoría explícitamente.',
                'priority': 'low',
                'score_impact': 'low'
            })
        
        # 4. Recomendaciones para implementaciones futuras
        available_domains = list(self.domain_specific_evaluators.keys())
        if domain not in available_domains and domain != 'generic':
            recommendations.append({
                'type': 'enhancement',
                'category': 'system_improvement',
                'title': f'Evaluadores específicos para {domain} en desarrollo',
                'description': f'Sistema detectó dominio {domain}. Evaluadores especializados mejorarán precisión cuando estén disponibles.',
                'priority': 'info',
                'score_impact': 'none'
            })
        
        # 5. Recomendaciones por campos faltantes (basado en evaluador de completeness)
        completeness_result = next((r for r in generic_results if r['evaluator'] == 'completeness'), None)
        if completeness_result and completeness_result['score'] < 0.8:
            missing_fields = completeness_result['details'].get('required_fields', {}).get('missing', [])
            if missing_fields:
                recommendations.append({
                    'type': 'improvement',
                    'category': 'data_completeness',
                    'title': 'Campos requeridos faltantes',
                    'description': f'Faltan campos críticos: {", ".join(missing_fields)}. Completar para mejorar el score.',
                    'priority': 'high',
                    'score_impact': 'high',
                    'missing_fields': missing_fields
                })
        
        if self.debug_mode:
            logger.debug(f"💡 Generadas {len(recommendations)} recomendaciones")
        
        return recommendations
    
    def _categorize_quality(self, score: float) -> str:
        """Categoriza la calidad del RFX basado en el score."""
        
        if score >= 0.9:
            return 'excellent'
        elif score >= 0.75:
            return 'good' 
        elif score >= 0.6:
            return 'acceptable'
        elif score >= 0.4:
            return 'needs_improvement'
        else:
            return 'poor'
    
    def get_evaluator_summary(self) -> Dict[str, Any]:
        """Retorna resumen de evaluadores disponibles."""
        
        return {
            'generic_evaluators': list(self.generic_evaluators.keys()),
            'domain_specific_evaluators': {
                domain: list(evaluators.keys()) 
                for domain, evaluators in self.domain_specific_evaluators.items()
            },
            'total_evaluators': len(self.generic_evaluators) + sum(
                len(evals) for evals in self.domain_specific_evaluators.values()
            ),
            'supported_domains': list(self.domain_specific_evaluators.keys()),
            'scoring_weights': self.scoring_weights
        }


# Factory para crear orquestador
def create_evaluation_orchestrator() -> EvaluationOrchestrator:
    """Factory function para crear instancia del orquestador."""
    return EvaluationOrchestrator()


# Función de conveniencia para evaluación rápida
def evaluate_rfx_intelligently(rfx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de conveniencia para evaluar RFX de manera inteligente.
    
    Usage:
        result = evaluate_rfx_intelligently(my_rfx_data)
        print(f"Score: {result['consolidated_score']}")
        print(f"Recommendations: {len(result['recommendations'])}")
    """
    
    orchestrator = create_evaluation_orchestrator()
    return orchestrator.evaluate_rfx_complete(rfx_data)