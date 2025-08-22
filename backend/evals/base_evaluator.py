"""
Base class para todos los evaluadores del sistema RFX.
Proporciona interfaz común y utilidades para evaluación.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class EvaluationResult:
    """Resultado estándar de evaluación"""
    score: float  # 0.0 to 1.0
    category: str
    details: Dict[str, Any]
    timestamp: datetime
    passed: bool
    threshold: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte resultado a diccionario para serialización"""
        return {
            'score': self.score,
            'category': self.category,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'passed': self.passed,
            'threshold': self.threshold
        }
    
    def __str__(self) -> str:
        status = '✅ PASS' if self.passed else '❌ FAIL'
        return f"{status} [{self.category}] Score: {self.score:.2f} (threshold: {self.threshold})"

class BaseEvaluator(ABC):
    """Clase base para todos los evaluadores"""
    
    def __init__(self, threshold: float = 0.8, debug_mode: bool = False):
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold debe estar entre 0.0 y 1.0, recibido: {threshold}")
            
        self.threshold = threshold
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Log initialization si debug está habilitado
        if self.debug_mode:
            self.logger.info(f"Inicializado {self.__class__.__name__} con threshold={threshold}")
    
    @abstractmethod
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Evalúa los datos y retorna resultado
        
        Args:
            data: Diccionario con datos a evaluar
            
        Returns:
            EvaluationResult con score, detalles y metadata
        """
        pass
    
    def _create_result(self, score: float, category: str, details: Dict[str, Any]) -> EvaluationResult:
        """
        Helper para crear resultado consistente
        
        Args:
            score: Score entre 0.0 y 1.0
            category: Categoría del evaluador
            details: Detalles específicos de la evaluación
            
        Returns:
            EvaluationResult configurado correctamente
        """
        if not 0.0 <= score <= 1.0:
            self.logger.warning(f"Score {score} fuera de rango [0.0, 1.0], normalizando")
            score = max(0.0, min(1.0, score))
        
        result = EvaluationResult(
            score=score,
            category=category,
            details=details,
            timestamp=datetime.now(),
            passed=score >= self.threshold,
            threshold=self.threshold
        )
        
        # Log resultado si debug está habilitado
        if self.debug_mode:
            self.logger.info(f"Resultado evaluación: {result}")
        
        return result
    
    def batch_evaluate(self, data_list: List[Dict[str, Any]]) -> List[EvaluationResult]:
        """
        Evalúa múltiples datasets en batch
        
        Args:
            data_list: Lista de datasets para evaluar
            
        Returns:
            Lista de EvaluationResult
        """
        results = []
        for i, data in enumerate(data_list):
            try:
                result = self.evaluate(data)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error evaluando item {i}: {e}")
                # Crear resultado de error
                error_result = self._create_result(
                    score=0.0,
                    category=f"{self.__class__.__name__.lower()}_batch",
                    details={
                        'error': str(e),
                        'item_index': i,
                        'exception_type': type(e).__name__
                    }
                )
                results.append(error_result)
        
        return results
    
    def get_summary_stats(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Calcula estadísticas sumarias de una lista de resultados
        
        Args:
            results: Lista de EvaluationResult
            
        Returns:
            Diccionario con estadísticas
        """
        if not results:
            return {
                'count': 0,
                'avg_score': 0.0,
                'pass_rate': 0.0,
                'min_score': 0.0,
                'max_score': 0.0
            }
        
        scores = [r.score for r in results]
        pass_count = sum(1 for r in results if r.passed)
        
        return {
            'count': len(results),
            'avg_score': sum(scores) / len(scores),
            'pass_rate': pass_count / len(results),
            'min_score': min(scores),
            'max_score': max(scores),
            'threshold_used': self.threshold
        }


class EvaluatorFactory:
    """Factory para crear evaluadores de forma consistente"""
    
    _evaluators = {}
    
    @classmethod
    def register_evaluator(cls, name: str, evaluator_class: type):
        """Registra un evaluador en el factory"""
        if not issubclass(evaluator_class, BaseEvaluator):
            raise ValueError(f"Evaluator {evaluator_class} debe heredar de BaseEvaluator")
        cls._evaluators[name] = evaluator_class
    
    @classmethod
    def create_evaluator(cls, name: str, **kwargs) -> BaseEvaluator:
        """Crea instancia de evaluador por nombre"""
        if name not in cls._evaluators:
            available = list(cls._evaluators.keys())
            raise ValueError(f"Evaluador '{name}' no registrado. Disponibles: {available}")
        
        evaluator_class = cls._evaluators[name]
        return evaluator_class(**kwargs)
    
    @classmethod
    def list_evaluators(cls) -> List[str]:
        """Lista evaluadores disponibles"""
        return list(cls._evaluators.keys())