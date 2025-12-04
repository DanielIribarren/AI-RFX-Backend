"""
Test unitario básico para RFXMessageHistory.

Verifica:
- Recuperación de historial desde rfx_chat_history
- Transformación a formato LangChain
- Manejo de errores
"""
import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage

from backend.services.chat_history import RFXMessageHistory


class TestRFXMessageHistory:
    """Tests para el adaptador de memoria LangChain"""
    
    @patch('backend.services.chat_history.get_database_client')
    def test_messages_property_returns_langchain_format(self, mock_db_client):
        """Verifica que messages retorna formato LangChain correcto"""
        # Mock de respuesta de Supabase
        mock_response = Mock()
        mock_response.data = [
            {
                "user_message": "Hola, agrega 5 manzanas",
                "assistant_message": "He agregado 5 manzanas al RFX.",
                "created_at": "2024-01-01T10:00:00Z"
            },
            {
                "user_message": "Cambia la cantidad a 10",
                "assistant_message": "He modificado la cantidad a 10 manzanas.",
                "created_at": "2024-01-01T10:05:00Z"
            }
        ]
        
        # Configurar mock
        mock_db = Mock()
        mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_db_client.return_value = mock_db
        
        # Ejecutar
        history = RFXMessageHistory(session_id="test-rfx-123")
        messages = history.messages
        
        # Verificar
        assert len(messages) == 4  # 2 turnos = 4 mensajes
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert messages[0].content == "Hola, agrega 5 manzanas"
        assert messages[1].content == "He agregado 5 manzanas al RFX."
    
    @patch('backend.services.chat_history.get_database_client')
    def test_messages_property_handles_empty_history(self, mock_db_client):
        """Verifica manejo de historial vacío"""
        # Mock de respuesta vacía
        mock_response = Mock()
        mock_response.data = []
        
        mock_db = Mock()
        mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_db_client.return_value = mock_db
        
        # Ejecutar
        history = RFXMessageHistory(session_id="test-rfx-456")
        messages = history.messages
        
        # Verificar
        assert len(messages) == 0
        assert messages == []
    
    @patch('backend.services.chat_history.get_database_client')
    def test_messages_property_handles_errors_gracefully(self, mock_db_client):
        """Verifica que errores retornan lista vacía (fallback)"""
        # Mock que lanza excepción
        mock_db = Mock()
        mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("Database error")
        mock_db_client.return_value = mock_db
        
        # Ejecutar
        history = RFXMessageHistory(session_id="test-rfx-789")
        messages = history.messages
        
        # Verificar fallback
        assert len(messages) == 0
        assert messages == []
    
    @patch('backend.services.chat_history.get_database_client')
    def test_add_messages_is_noop(self, mock_db_client):
        """Verifica que add_messages no hace nada (read-only)"""
        mock_db = Mock()
        mock_db_client.return_value = mock_db
        
        history = RFXMessageHistory(session_id="test-rfx-999")
        
        # Intentar agregar mensajes (no debería hacer nada)
        history.add_messages([
            HumanMessage(content="Test message")
        ])
        
        # Verificar que NO se llamó a ningún método de escritura
        assert not mock_db.client.table.return_value.insert.called
        assert not mock_db.client.table.return_value.update.called
    
    @patch('backend.services.chat_history.get_database_client')
    def test_clear_is_noop(self, mock_db_client):
        """Verifica que clear no hace nada (read-only)"""
        mock_db = Mock()
        mock_db_client.return_value = mock_db
        
        history = RFXMessageHistory(session_id="test-rfx-000")
        
        # Intentar limpiar historial (no debería hacer nada)
        history.clear()
        
        # Verificar que NO se llamó a ningún método de eliminación
        assert not mock_db.client.table.return_value.delete.called
    
    @patch('backend.services.chat_history.get_database_client')
    def test_messages_respects_limit(self, mock_db_client):
        """Verifica que se respeta el límite de 20 mensajes"""
        # Mock con muchos mensajes
        mock_response = Mock()
        mock_response.data = [
            {
                "user_message": f"Mensaje {i}",
                "assistant_message": f"Respuesta {i}",
                "created_at": f"2024-01-01T10:{i:02d}:00Z"
            }
            for i in range(15)  # 15 turnos = 30 mensajes potenciales
        ]
        
        mock_db = Mock()
        mock_execute = mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute
        mock_execute.return_value = mock_response
        mock_db_client.return_value = mock_db
        
        # Ejecutar
        history = RFXMessageHistory(session_id="test-rfx-limit")
        messages = history.messages
        
        # Verificar que se llamó con limit=20
        mock_db.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.assert_called_with(20)
        
        # Verificar que retorna todos los mensajes disponibles
        assert len(messages) == 30  # 15 turnos * 2 mensajes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
