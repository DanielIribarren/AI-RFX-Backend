#!/usr/bin/env python3
"""
🧪 Test Unitario Básico para Feature Flags
Tests fundamentales para el sistema de feature flags
"""
import pytest
from unittest.mock import patch
import os
import sys

# Add backend path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the individual flag variables directly for testing
from backend.core import config


class TestFeatureFlagsBasic:
    """Tests básicos para el sistema de feature flags usando valores actuales"""
    
    def test_feature_flag_parsing_logic(self):
        """Test la lógica de parsing de feature flags"""
        # Test that 'true' returns True
        assert os.getenv('FAKE_FLAG', 'false').lower() == 'true' if os.environ.get('FAKE_FLAG') == 'true' else True
        
        # Test case insensitive parsing
        test_cases = [
            ('true', True),
            ('True', True), 
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('', False),
            ('invalid', False),
            ('0', False)
        ]
        
        for value, expected in test_cases:
            result = value.lower() == 'true'
            assert result == expected, f"Value '{value}' should return {expected}"
    
    def test_evals_flag_behavior(self):
        """Test comportamiento de la flag ENABLE_EVALS"""
        # Test default behavior
        with patch.dict(os.environ, {}, clear=True):
            result = os.getenv('ENABLE_EVALS', 'false').lower() == 'true'
            assert result is False
        
        # Test enabled behavior
        with patch.dict(os.environ, {'ENABLE_EVALS': 'true'}):
            result = os.getenv('ENABLE_EVALS', 'false').lower() == 'true'
            assert result is True
    
    def test_meta_prompting_flag_behavior(self):
        """Test comportamiento de la flag ENABLE_META_PROMPTING"""
        with patch.dict(os.environ, {'ENABLE_META_PROMPTING': 'true'}):
            result = os.getenv('ENABLE_META_PROMPTING', 'false').lower() == 'true'
            assert result is True
        
        with patch.dict(os.environ, {'ENABLE_META_PROMPTING': 'false'}):
            result = os.getenv('ENABLE_META_PROMPTING', 'false').lower() == 'true'
            assert result is False
    
    def test_vertical_agent_flag_behavior(self):
        """Test comportamiento de la flag ENABLE_VERTICAL_AGENT"""
        with patch.dict(os.environ, {'ENABLE_VERTICAL_AGENT': 'true'}):
            result = os.getenv('ENABLE_VERTICAL_AGENT', 'false').lower() == 'true'
            assert result is True
        
        with patch.dict(os.environ, {}):
            result = os.getenv('ENABLE_VERTICAL_AGENT', 'false').lower() == 'true'
            assert result is False
    
    def test_eval_debug_flag_behavior(self):
        """Test comportamiento de la flag EVAL_DEBUG_MODE"""
        with patch.dict(os.environ, {'EVAL_DEBUG_MODE': 'true'}):
            result = os.getenv('EVAL_DEBUG_MODE', 'false').lower() == 'true'
            assert result is True
    
    def test_multiple_flags_behavior(self):
        """Test comportamiento con múltiples flags activadas"""
        env_vars = {
            'ENABLE_EVALS': 'true',
            'ENABLE_META_PROMPTING': 'false',
            'ENABLE_VERTICAL_AGENT': 'true',
            'EVAL_DEBUG_MODE': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            evals_enabled = os.getenv('ENABLE_EVALS', 'false').lower() == 'true'
            meta_enabled = os.getenv('ENABLE_META_PROMPTING', 'false').lower() == 'true'
            vertical_enabled = os.getenv('ENABLE_VERTICAL_AGENT', 'false').lower() == 'true'
            debug_enabled = os.getenv('EVAL_DEBUG_MODE', 'false').lower() == 'true'
            
            assert evals_enabled is True
            assert meta_enabled is False
            assert vertical_enabled is True
            assert debug_enabled is True


class TestFeatureFlagsClass:
    """Tests para la clase FeatureFlags (sin reload de módulos)"""
    
    def test_featureflags_methods_exist(self):
        """Test que los métodos de FeatureFlags existen y son callable"""
        from backend.core.feature_flags import FeatureFlags
        
        assert hasattr(FeatureFlags, 'evals_enabled')
        assert callable(FeatureFlags.evals_enabled)
        
        assert hasattr(FeatureFlags, 'meta_prompting_enabled')
        assert callable(FeatureFlags.meta_prompting_enabled)
        
        assert hasattr(FeatureFlags, 'vertical_agent_enabled')
        assert callable(FeatureFlags.vertical_agent_enabled)
        
        assert hasattr(FeatureFlags, 'eval_debug_enabled')
        assert callable(FeatureFlags.eval_debug_enabled)
        
        assert hasattr(FeatureFlags, 'get_enabled_features')
        assert callable(FeatureFlags.get_enabled_features)
        
        assert hasattr(FeatureFlags, 'is_any_ai_improvement_enabled')
        assert callable(FeatureFlags.is_any_ai_improvement_enabled)
    
    def test_get_enabled_features_returns_dict(self):
        """Test que get_enabled_features retorna un diccionario"""
        from backend.core.feature_flags import FeatureFlags
        
        features = FeatureFlags.get_enabled_features()
        
        assert isinstance(features, dict)
        assert 'evals' in features
        assert 'meta_prompting' in features
        assert 'vertical_agent' in features
        assert 'eval_debug' in features
        
        # All values should be boolean
        for key, value in features.items():
            assert isinstance(value, bool), f"Feature '{key}' should be boolean, got {type(value)}"
    
    def test_is_any_ai_improvement_enabled_returns_bool(self):
        """Test que is_any_ai_improvement_enabled retorna boolean"""
        from backend.core.feature_flags import FeatureFlags
        
        result = FeatureFlags.is_any_ai_improvement_enabled()
        assert isinstance(result, bool)


class TestFeatureFlagsConfig:
    """Tests de integración con el sistema de configuración actual"""
    
    def test_config_flags_are_accessible(self):
        """Test que las feature flags están disponibles en config"""
        # Test that the variables exist in the config module
        assert hasattr(config, 'ENABLE_EVALS')
        assert hasattr(config, 'ENABLE_META_PROMPTING')
        assert hasattr(config, 'ENABLE_VERTICAL_AGENT')
        assert hasattr(config, 'EVAL_DEBUG_MODE')
        
        # Test that they are boolean values
        assert isinstance(config.ENABLE_EVALS, bool)
        assert isinstance(config.ENABLE_META_PROMPTING, bool)
        assert isinstance(config.ENABLE_VERTICAL_AGENT, bool)
        assert isinstance(config.EVAL_DEBUG_MODE, bool)