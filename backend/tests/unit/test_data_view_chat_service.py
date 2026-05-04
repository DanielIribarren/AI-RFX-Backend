#!/usr/bin/env python3
"""
Unit tests for the lightweight fallback Data View chat service.
"""
import os
import sys
from types import SimpleNamespace

# Minimal env required for config import during test collection.
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("SECRET_KEY", "test-secret")

# Add backend path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.services.data_view_chat_service import DataViewChatService


class _FakeCompletions:
    def __init__(self, payload: str):
        self._payload = payload

    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._payload))],
            usage=SimpleNamespace(total_tokens=123),
            model="gpt-test",
        )


class _FakeClient:
    def __init__(self, payload: str):
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload))


class TestDataViewChatService:
    def test_process_message_builds_structured_chat_response(self):
        payload = """
        {
          "message": "Actualicé el titulo y la cantidad del producto.",
          "confidence": 0.87,
          "requires_confirmation": false,
          "options": [],
          "changes": [
            {
              "type": "update_field",
              "target": "title",
              "data": {"title": "Coctel corporativo Tecnoven"},
              "description": "Actualizar titulo"
            },
            {
              "type": "update_product",
              "target": "prod-1",
              "data": {"cantidad": 95},
              "description": "Actualizar cantidad del producto"
            }
          ]
        }
        """
        service = DataViewChatService(client=_FakeClient(payload), model="gpt-test")

        response = service.process_message(
            rfx_id="rfx-123",
            message="Actualiza el título y sube la cantidad del primer producto",
            context={
                "client_name": "Tecnoven",
                "current_products": [{"id": "prod-1", "nombre": "Tequenos", "cantidad": 85}],
            },
        )

        assert response.status == "success"
        assert response.message == "Actualicé el titulo y la cantidad del producto."
        assert response.confidence == 0.87
        assert len(response.changes) == 2
        assert response.changes[0].target == "title"
        assert response.changes[1].target == "prod-1"
        assert response.metadata.tokens_used == 123
        assert response.metadata.model_used == "gpt-test"

    def test_requires_confirmation_without_options_is_safely_disabled(self):
        payload = """
        {
          "message": "Necesito confirmar cuál producto quieres cambiar.",
          "confidence": 0.55,
          "requires_confirmation": true,
          "options": [],
          "changes": []
        }
        """
        service = DataViewChatService(client=_FakeClient(payload), model="gpt-test")

        response = service.process_message(
            rfx_id="rfx-123",
            message="Cambia el producto",
            context={"current_products": [{"id": "prod-1", "nombre": "Tequenos"}]},
        )

        assert response.status == "success"
        assert response.requires_confirmation is False
        assert response.options == []
