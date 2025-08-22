import pytest
from unittest.mock import patch
from backend.evals.extraction_evals import (
    ProductCountEvaluator,
    ProductQualityEvaluator,
    evaluate_product_count,
    evaluate_product_quality
)

class TestProductCountEvaluator:
    
    def test_initialization_valid_params(self):
        '''Test inicialización con parámetros válidos'''
        evaluator = ProductCountEvaluator(min_products=2, max_products=30, threshold=0.9)
        
        assert evaluator.min_products == 2
        assert evaluator.max_products == 30
        assert evaluator.threshold == 0.9
    
    def test_initialization_invalid_params(self):
        '''Test inicialización con parámetros inválidos'''
        with pytest.raises(ValueError, match='min_products debe ser >= 0'):
            ProductCountEvaluator(min_products=-1)
        
        with pytest.raises(ValueError, match='max_products.*debe ser >= min_products'):
            ProductCountEvaluator(min_products=10, max_products=5)
    
    def test_evaluate_optimal_count(self):
        '''Test evaluación con cantidad óptima de productos'''
        evaluator = ProductCountEvaluator(min_products=1, max_products=10, threshold=0.8)
        data = {
            'productos': [
                {'nombre': 'Tequeños', 'cantidad': 50},
                {'nombre': 'Empanadas', 'cantidad': 30},
                {'nombre': 'Café', 'cantidad': 2}
            ]
        }
        
        result = evaluator.evaluate(data)
        
        assert result.score == 1.0
        assert result.passed == True
        assert result.category == 'product_count'
        assert result.details['status'] == 'OK'
        assert result.details['count'] == 3
        assert 'product_analysis' in result.details
    
    def test_evaluate_zero_products(self):
        '''Test evaluación con cero productos'''
        evaluator = ProductCountEvaluator(threshold=0.8)
        data = {'productos': []}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.0
        assert result.passed == False
        assert result.details['issue'] == 'No products found'
        assert result.details['severity'] == 'critical'
    
    def test_evaluate_too_few_products(self):
        '''Test evaluación con muy pocos productos'''
        evaluator = ProductCountEvaluator(min_products=5, threshold=0.8)
        data = {'productos': [{'nombre': 'Solo uno'}]}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.3
        assert result.passed == False
        assert result.details['issue'] == 'Too few products'
        assert result.details['min_expected'] == 5
    
    def test_evaluate_too_many_products(self):
        '''Test evaluación con demasiados productos'''
        evaluator = ProductCountEvaluator(max_products=2, threshold=0.8)
        data = {'productos': [{'nombre': f'Producto {i}'} for i in range(5)]}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.5
        assert result.passed == False
        assert result.details['issue'] == 'Too many products'
        assert result.details['max_expected'] == 2
    
    def test_evaluate_invalid_productos_type(self):
        '''Test evaluación con productos que no es lista'''
        evaluator = ProductCountEvaluator(threshold=0.8)
        data = {'productos': 'not a list'}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.0
        assert result.passed == False
        assert 'error' in result.details
        assert result.details['type_found'] == 'str'
    
    def test_evaluate_missing_productos_key(self):
        '''Test evaluación sin key productos'''
        evaluator = ProductCountEvaluator(threshold=0.8)
        data = {'other_key': 'value'}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.0
        assert result.passed == False
    
    @patch('backend.core.feature_flags.FeatureFlags.eval_debug_enabled')
    def test_debug_mode_includes_extra_info(self, mock_debug):
        '''Test debug mode agrega información extra'''
        mock_debug.return_value = True
        evaluator = ProductCountEvaluator(threshold=0.8)
        data = {'productos': [{'nombre': 'Test'}]}
        
        result = evaluator.evaluate(data)
        
        assert 'debug' in result.details
        assert 'productos_sample' in result.details['debug']
        assert 'evaluator_config' in result.details['debug']
    
    def test_analyze_products_structure(self):
        '''Test análisis de estructura de productos'''
        evaluator = ProductCountEvaluator()
        productos = [
            {'nombre': 'Tequeños', 'cantidad': 50},
            {'nombre': 'Empanadas', 'cantidad': 30},
            {'nombre': 'Tequeños', 'cantidad': 20},  # Duplicado
            {'nombre': 'Sin cantidad'},
            {'cantidad': 10}  # Sin nombre
        ]
        
        analysis = evaluator._analyze_products_structure(productos)
        
        assert analysis['total_count'] == 5
        assert analysis['with_names'] == 4  # 3 únicos + 1 duplicado
        assert analysis['with_quantities'] == 4  # Corregido: 4 productos tienen cantidad
        assert analysis['duplicates_detected'] == True
        assert len(analysis['unique_names']) == 3
        assert 'quantity_stats' in analysis
    
    def test_exception_handling(self):
        '''Test manejo de excepciones'''
        evaluator = ProductCountEvaluator(threshold=0.8)
        
        # Simular excepción con datos muy malformados que causen error interno
        with patch.object(evaluator, '_analyze_products_structure', side_effect=Exception('Test error')):
            data = {'productos': [{'nombre': 'Test'}]}
            result = evaluator.evaluate(data)
            
            assert result.score == 0.0
            assert result.passed == False
            assert 'error' in result.details

class TestProductQualityEvaluator:
    
    def test_initialization(self):
        '''Test inicialización básica'''
        evaluator = ProductQualityEvaluator(threshold=0.6)
        
        assert evaluator.threshold == 0.6
        assert 'pasapalos' in evaluator.catering_keywords
        assert 'tequeño' in evaluator.catering_keywords['pasapalos']
    
    def test_evaluate_high_quality_catering_products(self):
        '''Test con productos de alta calidad de catering'''
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {
            'productos': [
                {'nombre': 'Tequeños fritos'},
                {'nombre': 'Empanadas de queso'},
                {'nombre': 'Shot de chocolate'},
                {'nombre': 'Café espresso'}
            ]
        }
        
        result = evaluator.evaluate(data)
        
        assert result.score > 0.7  # Debería ser alto
        assert result.passed == True
        assert result.details['catering_products'] == 4
        assert result.details['catering_percentage'] > 80
        assert result.details['categories_found'] >= 3
    
    def test_evaluate_low_quality_products(self):
        '''Test con productos de baja calidad (no catering)'''
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {
            'productos': [
                {'nombre': 'Producto genérico'},
                {'nombre': 'Item aleatorio'},
                {'nombre': 'Cosa sin definir'}
            ]
        }
        
        result = evaluator.evaluate(data)
        
        assert result.score < 0.3  # Debería ser bajo
        assert result.passed == False
        assert result.details['catering_products'] == 0
        assert result.details['catering_percentage'] == 0.0
    
    def test_evaluate_mixed_quality_products(self):
        '''Test con mezcla de productos catering y no-catering'''
        evaluator = ProductQualityEvaluator(threshold=0.5)
        data = {
            'productos': [
                {'nombre': 'Tequeños'},  # Catering
                {'nombre': 'Producto genérico'},  # No catering
                {'nombre': 'Brownie de chocolate'},  # Catering
                {'nombre': 'Item random'}  # No catering
            ]
        }
        
        result = evaluator.evaluate(data)
        
        assert 0.4 < result.score < 0.8  # Score intermedio
        assert result.details['catering_products'] == 2
        assert result.details['catering_percentage'] == 50.0
        assert result.details['categories_found'] >= 1
    
    def test_evaluate_empty_products(self):
        '''Test con lista vacía de productos'''
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {'productos': []}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.0
        assert result.passed == False
        assert 'error' in result.details
    
    def test_evaluate_invalid_productos_type(self):
        '''Test con productos que no es lista'''
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {'productos': 'not a list'}
        
        result = evaluator.evaluate(data)
        
        assert result.score == 0.0
        assert result.passed == False
        assert 'error' in result.details
    
    def test_evaluate_string_products(self):
        '''Test con productos como strings directos'''
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {
            'productos': [
                'Tequeños fritos',
                'Empanadas de carne',
                'Shot de limón'
            ]
        }
        
        result = evaluator.evaluate(data)
        
        assert result.score > 0.7
        assert result.passed == True
        assert result.details['catering_products'] == 3
    
    @patch('backend.core.feature_flags.FeatureFlags.eval_debug_enabled')
    def test_debug_mode_shows_details(self, mock_debug):
        '''Test debug mode muestra detalles de productos'''
        mock_debug.return_value = True
        evaluator = ProductQualityEvaluator(threshold=0.7)
        data = {'productos': [{'nombre': 'Tequeños'}]}
        
        result = evaluator.evaluate(data)
        
        assert 'debug' in result.details
        assert 'product_details' in result.details['debug']
        assert 'catering_keywords_used' in result.details['debug']
    
    def test_catering_keywords_coverage(self):
        '''Test que keywords cubren categorías principales de catering'''
        evaluator = ProductQualityEvaluator()
        
        # Verificar categorías principales
        assert 'pasapalos' in evaluator.catering_keywords
        assert 'dulces' in evaluator.catering_keywords
        assert 'bebidas' in evaluator.catering_keywords
        assert 'principales' in evaluator.catering_keywords
        
        # Verificar keywords específicos
        assert 'tequeño' in evaluator.catering_keywords['pasapalos']
        assert 'shot' in evaluator.catering_keywords['dulces']
        assert 'café' in evaluator.catering_keywords['bebidas']

class TestHelperFunctions:
    
    def test_evaluate_product_count_helper(self):
        '''Test función helper evaluate_product_count'''
        data = {'productos': [{'nombre': 'Test'}, {'nombre': 'Test2'}]}
        
        result = evaluate_product_count(data, threshold=0.9, min_products=1, max_products=5)
        
        assert result.threshold == 0.9
        assert result.category == 'product_count'
        assert result.score == 1.0
    
    def test_evaluate_product_quality_helper(self):
        '''Test función helper evaluate_product_quality'''
        data = {'productos': [{'nombre': 'Tequeños'}, {'nombre': 'Empanadas'}]}
        
        result = evaluate_product_quality(data, threshold=0.6)
        
        assert result.threshold == 0.6
        assert result.category == 'product_quality'
        assert result.score > 0.6
    
    def test_helper_functions_with_edge_cases(self):
        '''Test helpers con casos edge'''
        empty_data = {'productos': []}
        
        count_result = evaluate_product_count(empty_data)
        quality_result = evaluate_product_quality(empty_data)
        
        assert count_result.score == 0.0
        assert quality_result.score == 0.0
        assert not count_result.passed
        assert not quality_result.passed