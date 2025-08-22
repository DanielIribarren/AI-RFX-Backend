#!/usr/bin/env python3
"""
🧪 Test Unitario Básico para RFXProcessorService
Tests fundamentales sin dependencias externas
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Add backend path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.services.rfx_processor import RFXProcessorService
from backend.models.rfx_models import RFXInput, TipoRFX

class TestRFXProcessorBasic:
    """Tests básicos para RFXProcessorService con mocks"""
    
    @pytest.fixture
    def processor(self):
        """Fixture que crea un RFXProcessorService con dependencias mockeadas"""
        with patch('backend.services.rfx_processor.get_openai_config'), \
             patch('backend.services.rfx_processor.get_database_client'), \
             patch('backend.services.rfx_processor.OpenAI'), \
             patch('backend.services.rfx_processor.EmailValidator'), \
             patch('backend.services.rfx_processor.DateValidator'), \
             patch('backend.services.rfx_processor.TimeValidator'):
            
            processor = RFXProcessorService()
            # Mock the OpenAI client
            processor.openai_client = Mock()
            processor.db_client = Mock()
            return processor
    
    def test_extract_info_from_chunk_basic_success(self, processor):
        """Test básico: _extract_info_from_chunk con respuesta válida"""
        # Arrange
        test_chunk = "Catering para 50 personas, sandwiches y bebidas"
        expected_response = {
            "productos": [
                {"nombre": "Catering", "cantidad": 50, "unidad": "personas"}
            ],
            "nombre_solicitante": "Test Client",
            "email": "test@example.com"
        }
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps(expected_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        processor.openai_client.chat.completions.create.return_value = mock_response
        
        # Act
        result = processor._extract_info_from_chunk(test_chunk)
        
        # Assert
        assert "productos" in result
        assert len(result["productos"]) == 1
        assert result["productos"][0]["nombre"] == "Catering"
        assert result["productos"][0]["cantidad"] == 50
        
        # Verify OpenAI was called
        processor.openai_client.chat.completions.create.assert_called_once()
    
    def test_extract_info_from_chunk_invalid_json(self, processor):
        """Test: _extract_info_from_chunk con JSON inválido"""
        # Arrange
        test_chunk = "Invalid data"
        invalid_json_response = "{ invalid json }"
        
        # Mock OpenAI response with invalid JSON
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = invalid_json_response
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        processor.openai_client.chat.completions.create.return_value = mock_response
        
        # Act
        result = processor._extract_info_from_chunk(test_chunk)
        
        # Assert - should return empty result when JSON fails
        assert isinstance(result, dict)
        assert "productos" in result
        assert result["productos"] == []
    
    def test_combine_chunk_results_basic(self, processor):
        """Test básico: _combine_chunk_results con múltiples chunks"""
        # Arrange
        chunk_results = [
            {
                "productos": [{"nombre": "Sandwiches", "cantidad": 30, "unidad": "unidades"}],
                "nombre_solicitante": "Cliente A",
                "email": "clientea@test.com"
            },
            {
                "productos": [{"nombre": "Bebidas", "cantidad": 30, "unidad": "unidades"}],
                "lugar": "Oficina Central"
            }
        ]
        
        # Act
        result = processor._combine_chunk_results(chunk_results)
        
        # Assert
        assert "productos" in result
        assert len(result["productos"]) == 2
        assert result["nombre_solicitante"] == "Cliente A"  # First non-empty value
        assert result["email"] == "clientea@test.com"
        assert result["lugar"] == "Oficina Central"
        
        # Check products were combined
        product_names = [p["nombre"] for p in result["productos"]]
        assert "Sandwiches" in product_names
        assert "Bebidas" in product_names
    
    def test_combine_chunk_results_empty_chunks(self, processor):
        """Test: _combine_chunk_results con chunks vacíos"""
        # Arrange
        chunk_results = [
            {"productos": []},
            {"productos": []}
        ]
        
        # Act
        result = processor._combine_chunk_results(chunk_results)
        
        # Assert
        assert "productos" in result
        assert result["productos"] == []
        assert result["nombre_solicitante"] == ""
        assert result["email"] == ""
    
    @patch('backend.services.rfx_processor.chunk_text')
    def test_process_with_ai_basic_flow(self, mock_chunk_text, processor):
        """Test básico: _process_with_ai flow completo"""
        # Arrange
        test_text = "Catering para evento empresarial"
        mock_chunk_text.return_value = ["chunk1", "chunk2"]
        
        # Mock _extract_info_from_chunk calls
        def mock_extract_side_effect(chunk):
            if chunk == "chunk1":
                return {"productos": [{"nombre": "Catering", "cantidad": 1, "unidad": "servicio"}]}
            else:
                return {"productos": []}
        
        processor._extract_info_from_chunk = Mock(side_effect=mock_extract_side_effect)
        
        # Act
        result = processor._process_with_ai(test_text)
        
        # Assert
        assert "productos" in result
        assert len(result["productos"]) == 1
        
        # Verify chunk_text was called
        mock_chunk_text.assert_called_once_with(test_text, max_tokens=1000)
        
        # Verify _extract_info_from_chunk was called for each chunk
        assert processor._extract_info_from_chunk.call_count == 2
    
    def test_get_empty_extraction_result(self, processor):
        """Test: _get_empty_extraction_result returns correct structure"""
        # Act
        result = processor._get_empty_extraction_result()
        
        # Assert
        expected_keys = ["email", "nombre_solicitante", "productos", "hora_entrega", "fecha", "lugar", "texto_original_relevante"]
        for key in expected_keys:
            assert key in result
        
        assert result["productos"] == []
        assert isinstance(result, dict)

class TestRFXProcessorEdgeCases:
    """Tests para casos edge y manejo de errores"""
    
    @pytest.fixture
    def processor(self):
        """Fixture con mocks para edge cases"""
        with patch('backend.services.rfx_processor.get_openai_config'), \
             patch('backend.services.rfx_processor.get_database_client'), \
             patch('backend.services.rfx_processor.OpenAI'), \
             patch('backend.services.rfx_processor.EmailValidator'), \
             patch('backend.services.rfx_processor.DateValidator'), \
             patch('backend.services.rfx_processor.TimeValidator'):
            
            processor = RFXProcessorService()
            processor.openai_client = Mock()
            processor.db_client = Mock()
            return processor
    
    def test_extract_info_from_chunk_openai_exception(self, processor):
        """Test: _extract_info_from_chunk cuando OpenAI lanza excepción"""
        # Arrange
        test_chunk = "test chunk"
        processor.openai_client.chat.completions.create.side_effect = Exception("OpenAI Error")
        
        # Act
        result = processor._extract_info_from_chunk(test_chunk)
        
        # Assert - should return empty result when OpenAI fails
        assert isinstance(result, dict)
        assert "productos" in result
        assert result["productos"] == []
    
    def test_combine_chunk_results_overlapping_data(self, processor):
        """Test: _combine_chunk_results con datos overlapping"""
        # Arrange
        chunk_results = [
            {
                "productos": [{"nombre": "Café", "cantidad": 10, "unidad": "tazas"}],
                "nombre_solicitante": "Cliente Original",
                "email": "original@test.com"
            },
            {
                "productos": [{"nombre": "Té", "cantidad": 5, "unidad": "tazas"}],
                "nombre_solicitante": "Cliente Duplicado",  # Should be ignored
                "email": "duplicado@test.com"  # Should be ignored
            }
        ]
        
        # Act
        result = processor._combine_chunk_results(chunk_results)
        
        # Assert - should take first non-empty value
        assert result["nombre_solicitante"] == "Cliente Original"
        assert result["email"] == "original@test.com"
        
        # But combine all products
        assert len(result["productos"]) == 2


if __name__ == "__main__":
    """Ejecutar tests directamente"""
    pytest.main([__file__, "-v"])