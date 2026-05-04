import json
import os
import sys
from types import SimpleNamespace
import types

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("SECRET_KEY", "test-secret")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

if "jose" not in sys.modules:
    fake_jose = types.ModuleType("jose")
    fake_jose.JWTError = Exception
    fake_jose.jwt = SimpleNamespace(decode=lambda *args, **kwargs: {}, encode=lambda *args, **kwargs: "")
    sys.modules["jose"] = fake_jose

import backend.api.rfx_chat as rfx_chat_api
from backend.services.session_review_chat_service import SessionReviewChatService


class _FakeCompletions:
    def __init__(self, payload):
        self._payload = payload

    def create(self, **_kwargs):
        return SimpleNamespace(
            model="gpt-4o-mini",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(self._payload))
                )
            ],
            usage=SimpleNamespace(total_tokens=321),
        )


class _FakeClient:
    def __init__(self, payload):
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload))


def test_session_review_chat_service_parses_structured_json():
    service = SessionReviewChatService(
        client=_FakeClient(
            {
                "message": "I added beverages and updated the headcount note.",
                "confidence": 0.91,
                "requires_confirmation": False,
                "options": [],
                "changes": [
                    {
                        "type": "add_product",
                        "target": "new",
                        "data": {
                            "nombre": "Bebidas variadas",
                            "cantidad": 3,
                            "unidad": "unidades",
                        },
                        "description": "Added beverages",
                    },
                    {
                        "type": "update_field",
                        "target": "requirements",
                        "data": {"requirements": "85 attendees, beverages included"},
                        "description": "Updated requirements",
                    },
                ],
            }
        )
    )

    result = service.process_message(
        session_id="session-1",
        message="Add beverages and update the requirements.",
        context={"current_products": []},
    )

    assert result.status == "success"
    assert result.confidence == 0.91
    assert len(result.changes) == 2
    assert result.changes[0].type.value == "add_product"
    assert result.changes[1].type.value == "update_field"
    assert result.metadata.model_used == "gpt-4o-mini"


def test_apply_session_chat_changes_handles_product_lifecycle(monkeypatch):
    preview_data = {
        "products": [
            {
                "id": "prod-1",
                "nombre": "Tequenos",
                "cantidad": 10,
                "unidad": "unidades",
                "precio_unitario": 1.0,
                "costo_unitario": 0.5,
            }
        ]
    }
    validated_data = {"productos": list(preview_data["products"])}

    monkeypatch.setattr(
        rfx_chat_api,
        "_resolve_session_products",
        lambda products, _preview_data, _organization_id: [
            {
                **product,
                "precio_unitario": product.get("precio_unitario", 0),
                "costo_unitario": product.get("costo_unitario", 0),
                "estimated_line_total": float(product.get("cantidad", 0)) * float(product.get("precio_unitario", 0)),
            }
            for product in products
        ],
    )

    added = rfx_chat_api._apply_session_chat_changes(
        preview_data,
        validated_data,
        [
            {
                "type": "add_product",
                "target": "new",
                "data": {"nombre": "Bebidas", "cantidad": 4, "unidad": "unidades"},
            }
        ],
        organization_id="org-1",
    )
    assert added is True
    assert len(preview_data["products"]) == 2

    updated = rfx_chat_api._apply_session_chat_changes(
        preview_data,
        validated_data,
        [
            {
                "type": "update_product",
                "target": "prod-1",
                "data": {"cantidad": 25},
            }
        ],
        organization_id="org-1",
    )
    assert updated is True
    assert preview_data["products"][0]["cantidad"] == 25

    deleted = rfx_chat_api._apply_session_chat_changes(
        preview_data,
        validated_data,
        [
            {
                "type": "delete_product",
                "target": "prod-1",
                "data": {},
            }
        ],
        organization_id="org-1",
    )
    assert deleted is True
    assert len(preview_data["products"]) == 1
    assert preview_data["products"][0]["nombre"] == "Bebidas"
