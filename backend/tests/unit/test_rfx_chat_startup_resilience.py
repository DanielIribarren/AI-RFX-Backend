#!/usr/bin/env python3
"""
🧪 Startup resilience tests for review routes, chat fallback behavior, and
optional component reporting.
"""
import json
import os
import subprocess
import sys
import textwrap
import types
from types import SimpleNamespace

from flask import Flask

# Minimal env required for config import during test collection.
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("SECRET_KEY", "test-secret")

# Add backend path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

fake_jose = types.ModuleType("jose")
fake_jose.JWTError = Exception
fake_jose.jwt = types.SimpleNamespace(
    decode=lambda *args, **kwargs: {},
    encode=lambda *args, **kwargs: "",
)
sys.modules.setdefault("jose", fake_jose)

import backend.api.health as health_module
import backend.api.rfx_chat as rfx_chat_module
import backend.utils.auth_middleware as auth_module
from backend.api.health import health_bp
from backend.api.rfx_chat import rfx_chat_bp
from backend.models.chat_models import ChatMetadata, ChatResponse, ChangeType, RFXChange


class _DummyTableQuery:
    def select(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": "test-user"}])


class _DummyDBClient:
    def __init__(self):
        self.client = self

    def table(self, *_args, **_kwargs):
        return _DummyTableQuery()


class _DummyBrowser:
    def close(self):
        return None


class _DummyChromium:
    def launch(self, **_kwargs):
        return _DummyBrowser()


class _DummyPlaywrightContext:
    def __enter__(self):
        return SimpleNamespace(chromium=_DummyChromium())

    def __exit__(self, exc_type, exc, tb):
        return False


def _fake_sync_playwright():
    return _DummyPlaywrightContext()


class _DummyConversationService:
    async def get_state(self, _rfx_id):
        return {"state": {}, "status": "active", "requires_clarification": False}

    async def get_recent_events(self, _rfx_id, limit=10):
        return []

    async def add_event(self, **_kwargs):
        return None

    async def upsert_state(self, **_kwargs):
        return None


class _DummyCreditsService:
    def check_credits_available(self, *_args, **_kwargs):
        return True, 20, None

    def consume_credits(self, *_args, **_kwargs):
        return {"status": "success", "credits_remaining": 19}


class _DummyChatPersistenceService:
    async def save_chat_message(self, **_kwargs):
        return {}


class _DummyRFXDB:
    def get_rfx_by_id(self, rfx_id):
        return {
            "id": rfx_id,
            "user_id": "11111111-1111-1111-1111-111111111111",
            "organization_id": None,
        }


class TestRFXChatStartupResilience:
    def test_review_routes_survive_missing_langchain_openai(self):
        """Review endpoints must remain registered even if chat LLM deps are missing."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        test_env = os.environ.copy()
        test_env.update({
            "ENVIRONMENT": "testing",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "OPENAI_API_KEY": "sk-test-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "SECRET_KEY": "test-secret",
            "CORS_ORIGINS": "http://127.0.0.1:3000",
        })

        script = textwrap.dedent(
            """
            import builtins
            import sys
            import types

            sys.path.insert(0, ".")
            real_import = builtins.__import__

            fake_flask_cors = types.ModuleType("flask_cors")
            fake_flask_cors.CORS = lambda *args, **kwargs: None
            sys.modules.setdefault("flask_cors", fake_flask_cors)
            fake_flask_mail = types.ModuleType("flask_mail")
            fake_flask_mail.Mail = lambda *args, **kwargs: None
            fake_flask_mail.Message = type("Message", (), {})
            sys.modules.setdefault("flask_mail", fake_flask_mail)
            fake_jose = types.ModuleType("jose")
            fake_jose.JWTError = Exception
            fake_jose.jwt = types.SimpleNamespace(
                decode=lambda *args, **kwargs: {},
                encode=lambda *args, **kwargs: "",
            )
            sys.modules.setdefault("jose", fake_jose)
            fake_fastapi = types.ModuleType("fastapi")
            fake_fastapi.FastAPI = lambda *args, **kwargs: None
            fake_fastapi.HTTPException = Exception
            fake_fastapi.Depends = lambda dependency=None: dependency
            fake_fastapi.BackgroundTasks = type("BackgroundTasks", (), {})
            fake_fastapi.status = types.SimpleNamespace(
                HTTP_200_OK=200,
                HTTP_201_CREATED=201,
                HTTP_400_BAD_REQUEST=400,
                HTTP_401_UNAUTHORIZED=401,
                HTTP_404_NOT_FOUND=404,
                HTTP_500_INTERNAL_SERVER_ERROR=500,
            )
            sys.modules.setdefault("fastapi", fake_fastapi)
            from flask import Blueprint
            fake_user_branding = types.ModuleType("backend.api.user_branding")
            fake_user_branding.user_branding_bp = Blueprint("user_branding", __name__)
            sys.modules.setdefault("backend.api.user_branding", fake_user_branding)

            def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name.startswith("langchain_openai"):
                    raise ModuleNotFoundError("No module named 'langchain_openai'")
                return real_import(name, globals, locals, fromlist, level)

            builtins.__import__ = guarded_import

            from backend.app import create_app

            app = create_app()
            routes = {rule.rule for rule in app.url_map.iter_rules()}
            optional_components = app.extensions.get("optional_components", {})

            assert "/api/rfx/session/<session_id>/review/state" in routes
            assert "/api/rfx/<rfx_id>/review/state" in routes
            assert optional_components["rfx_chat"]["status"] == "enabled"

            print("ROUTE_OK")
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            env=test_env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            "Subprocess failed while validating route resilience.\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "ROUTE_OK" in result.stdout

    def test_dependencies_health_reports_optional_components(self, monkeypatch):
        """Health dependencies endpoint should surface disabled optional components."""
        app = Flask(__name__)
        app.extensions["optional_components"] = {
            "rfx": {"status": "enabled", "message": "Component loaded successfully"},
            "rfx_chat": {
                "status": "disabled",
                "message": "No module named 'langchain_openai'",
                "error_type": "ModuleNotFoundError",
            },
        }
        app.register_blueprint(health_bp)

        monkeypatch.setattr(health_module, "get_database_client", lambda: _DummyDBClient())
        monkeypatch.setattr(
            health_module,
            "get_openai_config",
            lambda: SimpleNamespace(api_key="sk-test", model="gpt-4o", timeout=60),
        )
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "demo")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "demo-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "demo-secret")

        fake_sync_api = types.ModuleType("playwright.sync_api")
        fake_sync_api.sync_playwright = _fake_sync_playwright
        fake_playwright = types.ModuleType("playwright")
        fake_playwright.sync_api = fake_sync_api
        monkeypatch.setitem(sys.modules, "playwright", fake_playwright)
        monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

        response = app.test_client().get("/api/health/dependencies")
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["data"]["dependencies"]["database"]["status"] == "available"
        assert payload["data"]["dependencies"]["openai"]["status"] == "configured"
        assert payload["data"]["optional_components"]["rfx"]["status"] == "enabled"
        assert payload["data"]["optional_components"]["rfx_chat"]["status"] == "disabled"
        assert payload["data"]["optional_components"]["rfx_chat"]["error_type"] == "ModuleNotFoundError"

    def test_persisted_rfx_chat_falls_back_when_legacy_agent_is_unavailable(self, monkeypatch):
        """Data View chat should degrade to the lightweight fallback instead of returning 500."""
        app = Flask(__name__)
        app.register_blueprint(rfx_chat_bp)

        monkeypatch.setattr(auth_module, "decode_token", lambda _token: {"sub": "11111111-1111-1111-1111-111111111111"})
        monkeypatch.setattr(
            auth_module.user_repository,
            "get_by_id",
            lambda _user_id: {
                "id": "11111111-1111-1111-1111-111111111111",
                "status": "active",
                "organization_id": None,
                "email": "test@example.com",
            },
        )
        monkeypatch.setattr(rfx_chat_module, "_get_database_client_instance", lambda: _DummyRFXDB())
        monkeypatch.setattr(rfx_chat_module, "RFXConversationStateService", _DummyConversationService)
        monkeypatch.setattr(rfx_chat_module, "_get_credits_service_instance", lambda: _DummyCreditsService())
        monkeypatch.setattr(rfx_chat_module, "_create_chat_service", lambda: _DummyChatPersistenceService())

        def _raise_legacy_error():
            raise ModuleNotFoundError("No module named 'langchain_openai'")

        class _FallbackService:
            def process_message(self, **_kwargs):
                return ChatResponse(
                    status="success",
                    message="Listo, preparé el cambio solicitado.",
                    confidence=0.82,
                    changes=[
                        RFXChange(
                            type=ChangeType.UPDATE_FIELD,
                            target="title",
                            data={"title": "Evento actualizado"},
                            description="Actualizar titulo",
                        )
                    ],
                    requires_confirmation=False,
                    options=[],
                    metadata=ChatMetadata(model_used="gpt-test", processing_time_ms=120),
                )

        monkeypatch.setattr(rfx_chat_module, "_create_chat_agent", _raise_legacy_error)
        monkeypatch.setattr(rfx_chat_module, "_create_data_view_chat_service", lambda: _FallbackService())

        response = app.test_client().post(
            "/api/rfx/rfx-123/chat",
            data={
                "message": "Actualiza el titulo",
                "context": json.dumps({"current_products": []}),
            },
            headers={"Authorization": "Bearer test-token"},
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["message"] == "Listo, preparé el cambio solicitado."
        assert payload["metadata"]["chat_backend"] == "fallback_structured_chat"
        assert payload["metadata"]["degraded_mode"] is True
        assert payload["changes"][0]["target"] == "title"

    def test_persisted_rfx_chat_returns_actionable_503_when_all_backends_fail(self, monkeypatch):
        """If both chat backends fail, the user should get a controlled actionable response."""
        app = Flask(__name__)
        app.register_blueprint(rfx_chat_bp)

        monkeypatch.setattr(auth_module, "decode_token", lambda _token: {"sub": "11111111-1111-1111-1111-111111111111"})
        monkeypatch.setattr(
            auth_module.user_repository,
            "get_by_id",
            lambda _user_id: {
                "id": "11111111-1111-1111-1111-111111111111",
                "status": "active",
                "organization_id": None,
                "email": "test@example.com",
            },
        )
        monkeypatch.setattr(rfx_chat_module, "_get_database_client_instance", lambda: _DummyRFXDB())
        monkeypatch.setattr(rfx_chat_module, "RFXConversationStateService", _DummyConversationService)
        monkeypatch.setattr(rfx_chat_module, "_get_credits_service_instance", lambda: _DummyCreditsService())
        monkeypatch.setattr(rfx_chat_module, "_create_chat_service", lambda: _DummyChatPersistenceService())

        def _raise_legacy_error():
            raise ModuleNotFoundError("No module named 'langchain_openai'")

        def _raise_fallback_error():
            raise RuntimeError("openai unavailable")

        monkeypatch.setattr(rfx_chat_module, "_create_chat_agent", _raise_legacy_error)
        monkeypatch.setattr(rfx_chat_module, "_create_data_view_chat_service", _raise_fallback_error)

        response = app.test_client().post(
            "/api/rfx/rfx-123/chat",
            data={
                "message": "Actualiza el titulo",
                "context": json.dumps({"current_products": []}),
            },
            headers={"Authorization": "Bearer test-token"},
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        assert response.status_code == 503
        assert payload["status"] == "error"
        assert "manual" in payload["message"].lower()
        assert payload["metadata"]["chat_backend"] == "unavailable"
        assert payload["metadata"]["retryable"] is True
