#!/usr/bin/env python3
"""
🧪 Startup resilience tests for review routes and optional component reporting.
"""
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

import backend.api.health as health_module
from backend.api.health import health_bp


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

            sys.path.insert(0, ".")
            real_import = builtins.__import__

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
