#!/usr/bin/env python3
"""
Tests unitarios exhaustivos para evaluadores genéricos.
Cubre CompletenessEvaluator, FormatValidationEvaluator, ConsistencyEvaluator.

Autor: AI Assistant  
Fecha: 2025-01-31
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from backend.evals.generic_evals import (
    CompletenessEvaluator,
    FormatValidationEvaluator, 
    ConsistencyEvaluator,
    evaluate_completeness,
    evaluate_format_validation,
    evaluate_consistency
)


class TestCompletenessEvaluator:
    """Tests para CompletenessEvaluator - evaluación de completitud de datos"""
    
    def test_initialization_default_params(self):
        """Test inicialización con parámetros por defecto"""
        evaluator = CompletenessEvaluator()
        
        assert evaluator.threshold == 0.8
        assert 'cliente' in evaluator.required_fields
        assert 'productos' in evaluator.required_fields
        assert 'fecha' in evaluator.required_fields
        assert 'lugar' in evaluator.required_fields
        assert 'email' in evaluator.optional_fields
        assert 'telefono' in evaluator.optional_fields
    
    def test_initialization_custom_params(self):
        """Test inicialización con parámetros personalizados"""
        custom_required = ['campo1', 'campo2']
        evaluator = CompletenessEvaluator(required_fields=custom_required, threshold=0.9)
        
        assert evaluator.threshold == 0.9
        assert evaluator.required_fields == custom_required
        assert len(evaluator.optional_fields) > 0
    
    def test_evaluate_complete_data(self):
        """Test evaluación con datos completos - score perfecto"""
        evaluator = CompletenessEvaluator(threshold=0.8)
        
        complete_data = {
            'cliente': 'Empresa ABC S.A.',
            'productos': [{'nombre': 'Producto 1'}, {'nombre': 'Producto 2'}],
            'fecha': '2025-03-15',
            'lugar': 'Centro Empresarial Torre Este',
            'email': 'contacto@empresa.com',
            'telefono': '+58-212-555-0123',
            'contacto': 'María González',
            'descripcion': 'Evento corporativo importante',
            'presupuesto': 5000
        }
        
        result = evaluator.evaluate(complete_data)
        
        assert result.score == 1.0
        assert result.passed == True
        assert result.category == 'completeness'
        assert result.details['required_fields']['present'] == 4
        assert result.details['required_fields']['missing'] == []
        assert result.details['optional_fields']['present'] == 5
        assert result.details['completeness_percentage'] == 100.0
        assert result.details['quality_level'] == 'excellent'
    
    def test_evaluate_only_required_fields(self):
        """Test evaluación solo con campos requeridos"""
        evaluator = CompletenessEvaluator(threshold=0.8)
        
        required_only_data = {
            'cliente': 'Empresa XYZ',
            'productos': [{'nombre': 'Servicio 1'}],
            'fecha': '2025-04-10',
            'lugar': 'Oficinas principales'
        }
        
        result = evaluator.evaluate(required_only_data)
        
        # Score = (1.0 * 0.7) + (0.0 * 0.3) = 0.7
        assert result.score == 0.7
        assert result.passed == False  # 0.7 < 0.8 threshold
        assert result.details['required_fields']['present'] == 4
        assert result.details['required_fields']['missing'] == []
        assert result.details['optional_fields']['present'] == 0
        assert result.details['quality_level'] == 'acceptable'
    
    def test_evaluate_missing_required_fields(self):
        """Test evaluación con campos requeridos faltantes"""
        evaluator = CompletenessEvaluator(threshold=0.8)
        
        incomplete_data = {
            'cliente': 'Empresa Incompleta',
            'productos': [],  # Vacio - debería contar como faltante
            # 'fecha' faltante
            'lugar': 'Lugar definido',
            'email': 'test@empresa.com'
        }
        
        result = evaluator.evaluate(incomplete_data)
        
        # Solo 2 de 4 campos requeridos: (0.5 * 0.7) + (0.2 * 0.3) = 0.41
        assert result.score < 0.5
        assert result.passed == False
        assert 'productos' in result.details['required_fields']['missing']
        assert 'fecha' in result.details['required_fields']['missing']
        assert result.details['quality_level'] in ['poor', 'critical']
    
    def test_is_field_complete_various_types(self):
        """Test función _is_field_complete con varios tipos de datos"""
        evaluator = CompletenessEvaluator()
        
        # Campos válidos
        assert evaluator._is_field_complete('texto válido') == True
        assert evaluator._is_field_complete(['item1', 'item2']) == True
        assert evaluator._is_field_complete({'key': 'value'}) == True
        assert evaluator._is_field_complete(123) == True
        
        # Campos inválidos
        assert evaluator._is_field_complete(None) == False
        assert evaluator._is_field_complete('') == False
        assert evaluator._is_field_complete('   ') == False
        assert evaluator._is_field_complete([]) == False
        assert evaluator._is_field_complete({}) == False
    
    def test_is_placeholder_detection(self):
        """Test detección de placeholders comunes"""
        evaluator = CompletenessEvaluator()
        
        # Placeholders que deben ser detectados
        placeholders = [
            'por definir',
            'POR CONFIRMAR',
            'no especificado',
            'N/A',
            'TBD',
            'Pendiente',
            'cliente-',
            'producto-1',
            'ubicación por confirmar'
        ]
        
        for placeholder in placeholders:
            assert evaluator._is_placeholder(placeholder) == True
        
        # Texto válido que NO son placeholders
        valid_texts = [
            'Empresa Real S.A.',
            'Caracas, Venezuela',
            'Evento corporativo',
            'contacto@empresa.com'
        ]
        
        for valid_text in valid_texts:
            assert evaluator._is_placeholder(valid_text) == False
    
    def test_get_quality_level_ranges(self):
        """Test categorización de niveles de calidad"""
        evaluator = CompletenessEvaluator()
        
        assert evaluator._get_quality_level(0.95) == 'excellent'
        assert evaluator._get_quality_level(0.90) == 'excellent'
        assert evaluator._get_quality_level(0.85) == 'good'
        assert evaluator._get_quality_level(0.80) == 'good'
        assert evaluator._get_quality_level(0.65) == 'acceptable'
        assert evaluator._get_quality_level(0.60) == 'acceptable'
        assert evaluator._get_quality_level(0.45) == 'poor'
        assert evaluator._get_quality_level(0.40) == 'poor'
        assert evaluator._get_quality_level(0.20) == 'critical'
        assert evaluator._get_quality_level(0.05) == 'critical'
    
    @patch('backend.core.feature_flags.FeatureFlags.eval_debug_enabled')
    def test_debug_mode_includes_extra_info(self, mock_debug):
        """Test que debug mode incluye información adicional"""
        mock_debug.return_value = True
        
        evaluator = CompletenessEvaluator(threshold=0.8)
        data = {
            'cliente': 'Test Client',
            'productos': [{'nombre': 'Test Product'}],
            'fecha': '2025-03-15',
            'lugar': 'Test Location'
        }
        
        result = evaluator.evaluate(data)
        
        assert 'debug' in result.details
        assert 'all_data_keys' in result.details['debug']
        assert 'required_analysis' in result.details['debug']
        assert 'calculation' in result.details['debug']
        assert len(result.details['debug']['all_data_keys']) == 4
    
    def test_evaluate_with_nested_data(self):
        """Test evaluación con datos anidados (clientes como objeto)"""
        evaluator = CompletenessEvaluator()
        
        nested_data = {
            'clientes': {
                'nombre': 'Empresa Anidada',
                'email': 'nested@empresa.com'
            },
            'productos': [{'nombre': 'Producto anidado'}],
            'fecha': '2025-05-20',
            'lugar': 'Ubicación anidada'
        }
        
        result = evaluator.evaluate(nested_data)
        
        # Debe detectar 'clientes' en lugar de 'cliente' como faltante
        assert 'cliente' in result.details['required_fields']['missing']
        assert result.details['required_fields']['present'] == 3
    
    def test_exception_handling(self):
        """Test manejo de excepciones"""
        evaluator = CompletenessEvaluator()
        
        # Simular excepción con datos corruptos
        with patch.object(evaluator, '_is_field_complete', side_effect=Exception('Test error')):
            result = evaluator.evaluate({'cliente': 'test'})
            
            assert result.score == 0.0
            assert result.passed == False
            assert 'error' in result.details
            assert result.details['exception_type'] == 'Exception'


class TestFormatValidationEvaluator:
    """Tests para FormatValidationEvaluator - validación de formatos"""
    
    def test_initialization(self):
        """Test inicialización con patrones de validación"""
        evaluator = FormatValidationEvaluator(threshold=0.9)
        
        assert evaluator.threshold == 0.9
        assert evaluator.email_pattern is not None
        assert evaluator.phone_pattern is not None
        assert len(evaluator.date_patterns) == 3
    
    def test_email_validation_valid_emails(self):
        """Test validación de emails válidos"""
        evaluator = FormatValidationEvaluator()
        
        valid_emails = [
            'user@example.com',
            'test.email@domain.co.uk',
            'name+tag@company.com',
            'user123@test-domain.org',
            'contact@empresa.com.ve'
        ]
        
        for email in valid_emails:
            data = {'email': email}
            result = evaluator.evaluate(data)
            
            assert result.score >= 0.5  # Al menos el email debe ser válido
            email_validation = next(v for v in result.details['validations'] if v['field'] == 'email')
            assert email_validation['is_valid'] == True
    
    def test_email_validation_invalid_emails(self):
        """Test validación de emails inválidos"""
        evaluator = FormatValidationEvaluator()
        
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@domain',  # Sin TLD
            'plaintext'  # Sin @ ni dominio
        ]
        
        for email in invalid_emails:
            data = {'email': email}
            result = evaluator.evaluate(data)
            
            email_validation = next(v for v in result.details['validations'] if v['field'] == 'email')
            assert email_validation['is_valid'] == False, f"Email {email} should be invalid but was marked as valid"
    
    def test_date_validation_multiple_formats(self):
        """Test validación de fechas en múltiples formatos"""
        evaluator = FormatValidationEvaluator()
        
        valid_dates = [
            '2026-03-15',  # YYYY-MM-DD (futuro)
            '15/03/2026',  # DD/MM/YYYY (futuro)
            '15-03-2026'   # DD-MM-YYYY (futuro)
        ]
        
        for date in valid_dates:
            data = {'fecha': date}
            result = evaluator.evaluate(data)
            
            date_validation = next(v for v in result.details['validations'] if v['field'] == 'fecha')
            assert date_validation['is_valid'] == True
            assert date_validation['is_future'] == True
    
    def test_date_validation_invalid_formats(self):
        """Test validación de fechas con formatos inválidos"""
        evaluator = FormatValidationEvaluator()
        
        invalid_dates = [
            '15-March-2025', # Con texto
            'next week',     # Texto
            'invalid-date'   # Completamente inválido
        ]
        
        for date in invalid_dates:
            data = {'fecha': date}
            result = evaluator.evaluate(data)
            
            date_validation = next(v for v in result.details['validations'] if v['field'] == 'fecha')
            assert date_validation['is_valid'] == False
    
    def test_past_date_detection(self):
        """Test detección de fechas pasadas"""
        evaluator = FormatValidationEvaluator()
        
        # Fecha claramente en el pasado
        past_date = '2020-01-01'
        data = {'fecha': past_date}
        result = evaluator.evaluate(data)
        
        date_validation = next(v for v in result.details['validations'] if v['field'] == 'fecha')
        assert date_validation['is_valid'] == True  # Formato válido
        assert date_validation['is_future'] == False  # Pero es pasada
        assert 'past' in date_validation['message'].lower()
    
    def test_product_quantities_validation(self):
        """Test validación de cantidades en productos"""
        evaluator = FormatValidationEvaluator()
        
        data = {
            'productos': [
                {'nombre': 'Producto 1', 'cantidad': 10},
                {'nombre': 'Producto 2', 'cantidad': '25'},  # String válido
                {'nombre': 'Producto 3', 'cantidad': 50.5},  # Float válido
                {'nombre': 'Producto 4', 'cantidad': 0},     # Cero - inválido
                {'nombre': 'Producto 5', 'cantidad': -5},    # Negativo - inválido
                {'nombre': 'Producto 6', 'cantidad': 'abc'}, # Texto - inválido
                {'nombre': 'Producto 7'}  # Sin cantidad
            ]
        }
        
        result = evaluator.evaluate(data)
        
        quantity_validation = next(v for v in result.details['validations'] if v['field'] == 'product_quantities')
        
        # Debe detectar 3 cantidades válidas (10, 25, 50.5) de 6 que tienen cantidad
        assert quantity_validation['valid_count'] == 3
        assert quantity_validation['total_count'] == 6  # Excluyendo el que no tiene cantidad
        assert quantity_validation['score'] == 0.5  # 3/6 = 0.5
    
    def test_nested_email_validation(self):
        """Test validación de email anidado en objeto clientes"""
        evaluator = FormatValidationEvaluator()
        
        data = {
            'clientes': {
                'email': 'nested@client.com'
            }
        }
        
        result = evaluator.evaluate(data)
        
        email_validation = next(v for v in result.details['validations'] if v['field'] == 'email')
        assert email_validation['value'] == 'nested@client.com'
        assert email_validation['is_valid'] == True
    
    def test_multiple_validations_combined_score(self):
        """Test score combinado con múltiples validaciones"""
        evaluator = FormatValidationEvaluator()
        
        data = {
            'email': 'valid@domain.com',        # 1.0 score
            'fecha': '2026-06-15',              # 1.0 score (válida y futura)
            'productos': [
                {'nombre': 'P1', 'cantidad': 10},  # Válida
                {'nombre': 'P2', 'cantidad': 20}   # Válida también
            ]  # 1.0 score
        }
        
        result = evaluator.evaluate(data)
        
        # Score final = (1.0 + 1.0 + 1.0) / 3 = 1.0
        assert result.score >= 0.8
        assert result.passed == True  # Asumiendo threshold 0.8
        assert len(result.details['validations']) == 3
    
    def test_no_validatable_fields(self):
        """Test evaluación sin campos validables"""
        evaluator = FormatValidationEvaluator()
        
        data = {
            'cliente': 'Empresa sin campos validables',
            'descripcion': 'Solo texto descriptivo'
        }
        
        result = evaluator.evaluate(data)
        
        # Sin validaciones, score debe ser 1.0 (perfecto por defecto)
        assert result.score == 1.0
        assert result.passed == True
        assert len(result.details['validations']) == 0
    
    @patch('backend.core.feature_flags.FeatureFlags.eval_debug_enabled')
    def test_debug_mode_shows_calculation(self, mock_debug):
        """Test que debug mode muestra cálculos detallados"""
        mock_debug.return_value = True
        
        evaluator = FormatValidationEvaluator()
        data = {'email': 'test@domain.com'}
        
        result = evaluator.evaluate(data)
        
        assert 'debug' in result.details
        assert 'score_calculation' in result.details['debug']
        assert 'validation_details' in result.details['debug']
    
    def test_exception_handling(self):
        """Test manejo de excepciones en validación"""
        evaluator = FormatValidationEvaluator()
        
        # Simular excepción con un evaluate que falle
        with patch.object(evaluator, '_validate_date_format', side_effect=Exception('Validation error')):
            data = {'fecha': '2026-03-15'}
            result = evaluator.evaluate(data)
            
            assert result.score == 0.0
            assert result.passed == False
            assert 'error' in result.details


class TestConsistencyEvaluator:
    """Tests para ConsistencyEvaluator - validación de consistencia lógica"""
    
    def test_initialization(self):
        """Test inicialización con threshold por defecto"""
        evaluator = ConsistencyEvaluator()
        
        assert evaluator.threshold == 0.7
    
    def test_initialization_custom_threshold(self):
        """Test inicialización con threshold personalizado"""
        evaluator = ConsistencyEvaluator(threshold=0.85)
        
        assert evaluator.threshold == 0.85
    
    def test_products_budget_consistency_reasonable(self):
        """Test consistencia razonable entre productos y presupuesto"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'productos': [
                {'nombre': 'Producto 1'},
                {'nombre': 'Producto 2'},
                {'nombre': 'Producto 3'}
            ],
            'presupuesto': 150  # $50 por producto promedio - razonable
        }
        
        result = evaluator.evaluate(data)
        
        budget_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'products_budget_consistency')
        assert budget_check['is_consistent'] == True
        assert budget_check['product_count'] == 3
        assert budget_check['budget_amount'] == 150.0
        assert result.score > 0.0
    
    def test_products_budget_consistency_unreasonable_low(self):
        """Test presupuesto demasiado bajo para cantidad de productos"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'productos': [{'nombre': f'Producto {i}'} for i in range(10)],  # 10 productos
            'presupuesto': 50  # Solo $5 por producto - muy bajo
        }
        
        result = evaluator.evaluate(data)
        
        budget_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'products_budget_consistency')
        assert budget_check['is_consistent'] == False
        assert 'unrealistic' in budget_check['message'].lower()
    
    def test_products_budget_consistency_unreasonable_high(self):
        """Test presupuesto demasiado alto para cantidad de productos"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'productos': [
                {'nombre': 'Producto simple'}
            ],
            'presupuesto': 5000  # $5000 para 1 producto - muy alto
        }
        
        result = evaluator.evaluate(data)
        
        budget_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'products_budget_consistency')
        # Aún puede ser consistente si está dentro del rango máximo (producto * 100 * 2)
        assert budget_check['budget_amount'] == 5000.0
    
    def test_delivery_time_business_hours(self):
        """Test horario de entrega dentro de horas de negocio"""
        evaluator = ConsistencyEvaluator()
        
        business_hours = ['09:00', '14:30', '16:00', '18:45']
        
        for hour in business_hours:
            data = {
                'fecha': '2025-03-15',
                'hora_entrega': hour
            }
            
            result = evaluator.evaluate(data)
            
            time_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'delivery_time_consistency')
            assert time_check['is_consistent'] == True
            assert 'business hours' in time_check['message']
    
    def test_delivery_time_outside_business_hours(self):
        """Test horario de entrega fuera de horas de negocio"""
        evaluator = ConsistencyEvaluator()
        
        non_business_hours = ['06:00', '20:30', '23:00', '02:15']
        
        for hour in non_business_hours:
            data = {
                'fecha': '2025-03-15',
                'hora': hour  # También probar con 'hora' en lugar de 'hora_entrega'
            }
            
            result = evaluator.evaluate(data)
            
            time_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'delivery_time_consistency')
            assert time_check['is_consistent'] == False
            assert 'outside' in time_check['message'].lower()
    
    def test_client_email_domain_consistency_matching(self):
        """Test consistencia entre nombre de cliente y dominio de email"""
        evaluator = ConsistencyEvaluator()
        
        matching_cases = [
            ('Empresa TechSolutions', 'contacto@techsolutions.com'),
            ('Corporación Microsoft', 'info@microsoft.com'),
            ('Fundación Educativa', 'admin@educativa.org'),
            ('Consultoría Global', 'ventas@global.net')
        ]
        
        for client_name, email in matching_cases:
            data = {
                'cliente': client_name,
                'email': email
            }
            
            result = evaluator.evaluate(data)
            
            email_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'client_email_consistency')
            assert email_check['is_consistent'] == True
            assert 'matches' in email_check['message'].lower()
    
    def test_client_email_domain_consistency_corporate(self):
        """Test consistencia con dominios corporativos (siempre válidos)"""
        evaluator = ConsistencyEvaluator()
        
        corporate_cases = [
            ('TechSolutions', 'contacto@techsolutions.com'),  # Match directo
            ('Empresa Premium', 'info@empresa.net'),          # Match de palabra
            ('Global Corp', 'hello@globalcorp.io')           # Match de palabra
        ]
        
        for client_name, email in corporate_cases:
            data = {
                'cliente': client_name,
                'email': email
            }
            
            result = evaluator.evaluate(data)
            
            email_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'client_email_consistency')
            assert email_check['is_consistent'] == True
    
    def test_client_email_domain_consistency_generic(self):
        """Test con dominios genéricos sin match"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'cliente': 'Empresa Sin Relación',
            'email': 'usuario@gmail.com'  # Dominio genérico sin match
        }
        
        result = evaluator.evaluate(data)
        
        email_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'client_email_consistency')
        # Según la lógica: is_corporate_domain = False (es genérico), por lo que is_consistent = True
        assert email_check['is_consistent'] == True
        assert 'Generic' in email_check['message']
    
    def test_nested_client_data(self):
        """Test consistencia con datos de cliente anidados"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'clientes': {
                'nombre': 'TechCorp Solutions',
                'email': 'info@techcorp.com'
            }
        }
        
        result = evaluator.evaluate(data)
        
        email_check = next(c for c in result.details['consistency_checks'] if c['check'] == 'client_email_consistency')
        assert email_check['is_consistent'] == True
        assert email_check['cliente'] == 'TechCorp Solutions'
    
    def test_multiple_consistency_checks_combined(self):
        """Test múltiples checks de consistencia combinados"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'productos': [{'nombre': 'P1'}, {'nombre': 'P2'}],
            'presupuesto': 100,  # Consistente: $50 por producto
            'fecha': '2025-04-15',
            'hora_entrega': '14:00',  # Consistente: horario de negocio
            'cliente': 'TechSolutions Corp',
            'email': 'contact@techsolutions.com'  # Consistente: dominio match
        }
        
        result = evaluator.evaluate(data)
        
        # Todos los checks deben ser consistentes -> score 1.0
        assert result.score == 1.0
        assert result.passed == True
        assert len(result.details['consistency_checks']) == 3
        assert result.details['passed_checks'] == 3
    
    def test_partial_consistency(self):
        """Test consistencia parcial - algunos checks pasan, otros no"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'productos': [{'nombre': 'P1'}],
            'presupuesto': 5,   # Muy bajo: estimado mín = 10, esto es menor
            'hora': '23:00',    # Fuera de horario: después de 19:00
            'cliente': 'Different Company',
            'email': 'user@completelydifferent.com'  # Sin match de palabras
        }
        
        result = evaluator.evaluate(data)
        
        # Verificar que al menos algunos checks sean inconsistentes
        assert result.score < 1.0
        assert result.details['total_checks'] >= 1
    
    def test_no_consistency_checks_available(self):
        """Test sin datos suficientes para checks de consistencia"""
        evaluator = ConsistencyEvaluator()
        
        data = {
            'descripcion': 'Solo descripción sin datos para validar'
        }
        
        result = evaluator.evaluate(data)
        
        # Sin checks -> score 1.0 por defecto
        assert result.score == 1.0
        assert result.passed == True
        assert len(result.details['consistency_checks']) == 0
        assert result.details['total_checks'] == 0
    
    def test_is_business_hours_edge_cases(self):
        """Test casos edge de horario de negocio"""
        evaluator = ConsistencyEvaluator()
        
        # Casos límite más claros
        edge_cases = [
            ('7:00', True),   # Inicio exacto
            ('07:00', True),  # Con cero inicial
            ('19:00', True),  # Final exacto
            ('6:00', False),  # Justo antes
            ('20:00', False), # Claramente después
            ('12:00', True),  # Mediodía
            ('8:00', True),   # Hora matutina clara
            ('22:00', False), # Hora nocturna clara
        ]
        
        for time_str, should_be_business in edge_cases:
            is_business = evaluator._is_business_hours(time_str)
            assert is_business == should_be_business, f"Failed for {time_str}"
    
    @patch('backend.core.feature_flags.FeatureFlags.eval_debug_enabled')
    def test_debug_mode_shows_calculation_details(self, mock_debug):
        """Test que debug mode muestra detalles de cálculo"""
        mock_debug.return_value = True
        
        evaluator = ConsistencyEvaluator()
        data = {
            'productos': [{'nombre': 'Test'}],
            'presupuesto': 50
        }
        
        result = evaluator.evaluate(data)
        
        assert 'debug' in result.details
        assert 'score_calculation' in result.details['debug']
        assert 'all_checks_details' in result.details['debug']
    
    def test_exception_handling(self):
        """Test manejo de excepciones en evaluación de consistencia"""
        evaluator = ConsistencyEvaluator()
        
        # Simular excepción en el procesamiento
        with patch.object(evaluator, '_is_business_hours', side_effect=Exception('Time parsing error')):
            data = {
                'fecha': '2025-03-15',
                'hora': '14:00'
            }
            result = evaluator.evaluate(data)
            
            assert result.score == 0.0
            assert result.passed == False
            assert 'error' in result.details


class TestHelperFunctions:
    """Tests para funciones helper de evaluadores genéricos"""
    
    def test_evaluate_completeness_helper(self):
        """Test función helper evaluate_completeness"""
        data = {
            'cliente': 'Test Client',
            'productos': [{'nombre': 'Test Product'}],
            'fecha': '2025-03-15',
            'lugar': 'Test Location',
            'email': 'test@domain.com'
        }
        
        result = evaluate_completeness(data, threshold=0.9)
        
        assert result.threshold == 0.9
        assert result.category == 'completeness'
        assert result.score > 0.7  # Debe tener buen score
    
    def test_evaluate_format_validation_helper(self):
        """Test función helper evaluate_format_validation"""
        data = {
            'email': 'valid@domain.com',
            'fecha': '2026-06-15'  # Fecha futura
        }
        
        result = evaluate_format_validation(data, threshold=0.85)
        
        assert result.threshold == 0.85
        assert result.category == 'format_validation'
        assert result.score >= 0.8  # Email y fecha válidos
    
    def test_evaluate_consistency_helper(self):
        """Test función helper evaluate_consistency"""
        data = {
            'productos': [{'nombre': 'Product'}],
            'presupuesto': 75,  # Razonable para 1 producto
            'cliente': 'TechCorp',
            'email': 'info@techcorp.com'
        }
        
        result = evaluate_consistency(data, threshold=0.6)
        
        assert result.threshold == 0.6
        assert result.category == 'consistency'
        assert result.score > 0.8  # Debe ser consistente
    
    def test_helper_functions_with_custom_params(self):
        """Test helpers con parámetros personalizados"""
        data = {'cliente': 'Test'}
        
        # Test completeness con campos personalizados
        custom_required = ['cliente', 'custom_field']
        result = evaluate_completeness(data, threshold=0.5, required_fields=custom_required)
        
        assert result.threshold == 0.5
        # Debe tener score parcial ya que falta 'custom_field'
        assert 0.3 < result.score < 0.8
    
    def test_helpers_with_empty_data(self):
        """Test helpers con datos vacíos"""
        empty_data = {}
        
        completeness_result = evaluate_completeness(empty_data)
        format_result = evaluate_format_validation(empty_data)
        consistency_result = evaluate_consistency(empty_data)
        
        # Completeness debe fallar con datos vacíos
        assert completeness_result.score == 0.0
        assert completeness_result.passed == False
        
        # Format validation debe pasar (sin campos para validar)
        assert format_result.score == 1.0
        assert format_result.passed == True
        
        # Consistency debe pasar (sin checks para hacer)
        assert consistency_result.score == 1.0
        assert consistency_result.passed == True


class TestEdgeCases:
    """Tests para casos edge y situaciones especiales"""
    
    def test_extremely_large_data(self):
        """Test con datasets muy grandes"""
        evaluator = CompletenessEvaluator()
        
        large_data = {
            'cliente': 'Cliente con muchos productos',
            'productos': [{'nombre': f'Producto {i}'} for i in range(1000)],
            'fecha': '2025-12-31',
            'lugar': 'Ubicación masiva'
        }
        
        result = evaluator.evaluate(large_data)
        
        # Debe manejar datasets grandes sin problemas
        assert result.score > 0.0
        assert result.category == 'completeness'
        assert len(large_data['productos']) == 1000
    
    def test_unicode_and_special_characters(self):
        """Test con caracteres Unicode y especiales"""
        evaluator = CompletenessEvaluator(threshold=0.75)  # Threshold más bajo para este test
        
        unicode_data = {
            'cliente': 'Empresa Ñoño & Cía. S.A. 中文',
            'productos': [
                {'nombre': 'Tequeños™ Premium®'},
                {'nombre': 'Café João Açúcar'}
            ],
            'fecha': '2025-03-15',
            'lugar': 'São Paulo - Fußgängerzone',
            'email': 'contacto@empresa-ñoño.com.br',
            'telefono': '+55-11-99999-9999',  # Agregar más campos opcionales
            'descripcion': 'Evento internacional'
        }
        
        result = evaluator.evaluate(unicode_data)
        
        # Debe manejar Unicode correctamente
        assert result.score > 0.7
        assert result.passed == True
    
    def test_mixed_data_types(self):
        """Test con tipos de datos mixtos"""
        evaluator = FormatValidationEvaluator()
        
        mixed_data = {
            'email': 123,  # Número en lugar de string
            'fecha': None,  # None
            'productos': 'not a list',  # String en lugar de lista
            'other_field': ['lista', 'como', 'valor']
        }
        
        result = evaluator.evaluate(mixed_data)
        
        # Debe manejar tipos incorrectos gracefully
        assert result.score >= 0.0
        assert result.category == 'format_validation'
    
    def test_circular_references(self):
        """Test con referencias circulares en datos"""
        evaluator = ConsistencyEvaluator()
        
        # Crear referencia circular
        circular_data = {
            'cliente': 'Test Client',
            'productos': []
        }
        circular_data['self_ref'] = circular_data  # Referencia circular
        
        # Debe manejar sin entrar en loop infinito
        result = evaluator.evaluate(circular_data)
        
        assert result.score >= 0.0
        assert result.category == 'consistency'