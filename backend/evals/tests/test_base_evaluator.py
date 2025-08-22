import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from backend.evals.base_evaluator import BaseEvaluator, EvaluationResult, EvaluatorFactory

class MockEvaluator(BaseEvaluator):
    '''Evaluador mock para testing'''
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        # Simular evaluación simple
        score = data.get('score', 0.5)
        return self._create_result(
            score=score,
            category='mock',
            details={'test': True, 'data_keys': list(data.keys())}
        )

class TestEvaluationResult:
    
    def test_evaluation_result_creation(self):
        '''Test creación básica de EvaluationResult'''
        result = EvaluationResult(
            score=0.85,
            category='test',
            details={'key': 'value'},
            timestamp=datetime.now(),
            passed=True,
            threshold=0.8
        )
        
        assert result.score == 0.85
        assert result.category == 'test'
        assert result.passed == True
        assert result.threshold == 0.8
    
    def test_to_dict_serialization(self):
        '''Test serialización a diccionario'''
        timestamp = datetime.now()
        result = EvaluationResult(
            score=0.75,
            category='test',
            details={'data': 123},
            timestamp=timestamp,
            passed=False,
            threshold=0.8
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['score'] == 0.75
        assert result_dict['category'] == 'test'
        assert result_dict['details']['data'] == 123
        assert result_dict['timestamp'] == timestamp.isoformat()
        assert result_dict['passed'] == False
        assert result_dict['threshold'] == 0.8
    
    def test_str_representation(self):
        '''Test representación string'''
        result = EvaluationResult(
            score=0.9,
            category='test_eval',
            details={},
            timestamp=datetime.now(),
            passed=True,
            threshold=0.8
        )
        
        str_repr = str(result)
        
        assert '✅ PASS' in str_repr
        assert '[test_eval]' in str_repr
        assert 'Score: 0.90' in str_repr
        assert 'threshold: 0.8' in str_repr

class TestBaseEvaluator:
    
    def test_initialization_valid_threshold(self):
        '''Test inicialización con threshold válido'''
        evaluator = MockEvaluator(threshold=0.7, debug_mode=True)
        
        assert evaluator.threshold == 0.7
        assert evaluator.debug_mode == True
        assert evaluator.logger is not None
    
    def test_initialization_invalid_threshold(self):
        '''Test inicialización con threshold inválido'''
        with pytest.raises(ValueError, match='Threshold debe estar entre 0.0 y 1.0'):
            MockEvaluator(threshold=1.5)
        
        with pytest.raises(ValueError, match='Threshold debe estar entre 0.0 y 1.0'):
            MockEvaluator(threshold=-0.1)
    
    def test_create_result_valid_score(self):
        '''Test _create_result con score válido'''
        evaluator = MockEvaluator(threshold=0.8)
        
        result = evaluator._create_result(
            score=0.9,
            category='test',
            details={'key': 'value'}
        )
        
        assert result.score == 0.9
        assert result.category == 'test'
        assert result.passed == True  # 0.9 >= 0.8
        assert result.threshold == 0.8
    
    def test_create_result_score_normalization(self):
        '''Test _create_result normaliza scores fuera de rango'''
        evaluator = MockEvaluator(threshold=0.8)
        
        # Score mayor a 1.0
        result_high = evaluator._create_result(
            score=1.5,
            category='test',
            details={}
        )
        assert result_high.score == 1.0
        
        # Score menor a 0.0
        result_low = evaluator._create_result(
            score=-0.5,
            category='test',
            details={}
        )
        assert result_low.score == 0.0
    
    def test_evaluate_basic_functionality(self):
        '''Test funcionalidad básica de evaluate'''
        evaluator = MockEvaluator(threshold=0.8)
        data = {'score': 0.9, 'other': 'data'}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.9
        assert result.category == 'mock'
        assert result.passed == True
        assert 'test' in result.details
    
    def test_batch_evaluate_success(self):
        '''Test batch_evaluate con datos válidos'''
        evaluator = MockEvaluator(threshold=0.8)
        data_list = [
            {'score': 0.9},
            {'score': 0.7},
            {'score': 0.85}
        ]
        
        results = evaluator.batch_evaluate(data_list)
        
        assert len(results) == 3
        assert results[0].score == 0.9
        assert results[1].score == 0.7
        assert results[2].score == 0.85
    
    def test_batch_evaluate_with_errors(self):
        '''Test batch_evaluate maneja errores gracefully'''
        evaluator = MockEvaluator(threshold=0.8)
        
        # Mock evaluate para que falle en el segundo item
        original_evaluate = evaluator.evaluate
        def side_effect(data):
            if data.get('fail'):
                raise ValueError('Test error')
            return original_evaluate(data)
        
        evaluator.evaluate = side_effect
        
        data_list = [
            {'score': 0.9},
            {'score': 0.7, 'fail': True},  # Este fallará
            {'score': 0.85}
        ]
        
        results = evaluator.batch_evaluate(data_list)
        
        assert len(results) == 3
        assert results[0].score == 0.9  # Éxito
        assert results[1].score == 0.0  # Error -> score 0
        assert 'error' in results[1].details
        assert results[2].score == 0.85  # Éxito
    
    def test_get_summary_stats_normal_case(self):
        '''Test get_summary_stats con resultados normales'''
        evaluator = MockEvaluator(threshold=0.8)
        
        results = [
            EvaluationResult(0.9, 'test', {}, datetime.now(), True, 0.8),
            EvaluationResult(0.7, 'test', {}, datetime.now(), False, 0.8),
            EvaluationResult(0.85, 'test', {}, datetime.now(), True, 0.8),
        ]
        
        stats = evaluator.get_summary_stats(results)
        
        assert stats['count'] == 3
        assert stats['avg_score'] == pytest.approx((0.9 + 0.7 + 0.85) / 3, rel=1e-3)
        assert stats['pass_rate'] == pytest.approx(2/3, rel=1e-3)  # 2 passed de 3
        assert stats['min_score'] == 0.7
        assert stats['max_score'] == 0.9
        assert stats['threshold_used'] == 0.8
    
    def test_get_summary_stats_empty_list(self):
        '''Test get_summary_stats con lista vacía'''
        evaluator = MockEvaluator(threshold=0.8)
        
        stats = evaluator.get_summary_stats([])
        
        assert stats['count'] == 0
        assert stats['avg_score'] == 0.0
        assert stats['pass_rate'] == 0.0
        assert stats['min_score'] == 0.0
        assert stats['max_score'] == 0.0

class TestEvaluatorFactory:
    
    def test_register_and_create_evaluator(self):
        '''Test registro y creación de evaluadores'''
        EvaluatorFactory.register_evaluator('mock', MockEvaluator)
        
        evaluator = EvaluatorFactory.create_evaluator('mock', threshold=0.9)
        
        assert isinstance(evaluator, MockEvaluator)
        assert evaluator.threshold == 0.9
    
    def test_register_invalid_evaluator(self):
        '''Test registro de evaluador que no hereda de BaseEvaluator'''
        class InvalidEvaluator:
            pass
        
        with pytest.raises(ValueError, match='debe heredar de BaseEvaluator'):
            EvaluatorFactory.register_evaluator('invalid', InvalidEvaluator)
    
    def test_create_unknown_evaluator(self):
        '''Test creación de evaluador no registrado'''
        with pytest.raises(ValueError, match="Evaluador 'unknown' no registrado"):
            EvaluatorFactory.create_evaluator('unknown')
    
    def test_list_evaluators(self):
        '''Test listar evaluadores disponibles'''
        # Clear existing
        EvaluatorFactory._evaluators.clear()
        
        # Register test evaluators
        EvaluatorFactory.register_evaluator('mock1', MockEvaluator)
        EvaluatorFactory.register_evaluator('mock2', MockEvaluator)
        
        evaluators = EvaluatorFactory.list_evaluators()
        
        assert 'mock1' in evaluators
        assert 'mock2' in evaluators
        assert len(evaluators) == 2