import os
import re
import sys
import types
from datetime import datetime, timezone
from uuid import uuid4

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

if "PyPDF2" not in sys.modules:
    pypdf2_stub = types.ModuleType("PyPDF2")
    pypdf2_stub.PdfReader = object
    sys.modules["PyPDF2"] = pypdf2_stub

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, _name):
            return self

        def __call__(self, *args, **kwargs):
            return self

    openai_stub.OpenAI = _DummyOpenAI
    sys.modules["openai"] = openai_stub

from backend.models.rfx_models import RFXProcessed, RFXStatus, RFXType
from backend.services.document_code_service import DocumentCodeService
from backend.services.rfx_processor import RFXProcessorService


class _RPCResponse:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class _FakeSupabaseClient:
    def __init__(self):
        self.sequences = {}

    def rpc(self, fn_name, payload):
        if fn_name != "next_document_code_seq":
            raise AssertionError(f"Unexpected RPC function: {fn_name}")

        key = (
            str(payload.get("p_code_type")),
            str(payload.get("p_domain_prefix")),
            int(payload.get("p_year")),
        )
        self.sequences[key] = self.sequences.get(key, 0) + 1
        return _RPCResponse(self.sequences[key])


class _FakeDBClient:
    def __init__(self):
        self.client = _FakeSupabaseClient()
        self.last_rfx_data = None

    def insert_company(self, company_data):
        return {"id": "company-1", **company_data}

    def insert_requester(self, requester_data):
        return {"id": "requester-1", **requester_data}

    def insert_rfx(self, rfx_data):
        self.last_rfx_data = dict(rfx_data)
        return {"id": rfx_data["id"], **rfx_data}

    def insert_rfx_products(self, _rfx_id, _products):
        return []

    def insert_rfx_history(self, _history):
        return {}


def test_save_rfx_persists_canonical_rfx_code_in_column_and_metadata():
    fake_db = _FakeDBClient()
    service = object.__new__(RFXProcessorService)
    service.db_client = fake_db
    service.document_code_service = DocumentCodeService(fake_db)

    rfx_processed = RFXProcessed(
        id=uuid4(),
        rfx_type=RFXType.CATERING,
        title="RFX E2E Test",
        location="Caracas",
        status=RFXStatus.IN_PROGRESS,
        metadata_json={
            "nombre_empresa": "Sabra QA",
            "telefono_empresa": "+58 000-000",
            "validated_currency": "USD",
        },
        requester_name="QA User",
        company_name="Sabra QA",
        email="qa@sabra.test",
        products=[],
    )

    service._save_rfx_to_database(
        rfx_processed=rfx_processed,
        user_id=str(uuid4()),
        organization_id=None,
    )

    assert fake_db.last_rfx_data is not None
    stored_code = fake_db.last_rfx_data.get("rfx_code")
    stored_metadata_code = (fake_db.last_rfx_data.get("metadata_json") or {}).get("rfx_code")

    current_yy = datetime.now(timezone.utc).year % 100
    expected_pattern = rf"^SAB-PP-AUT-{current_yy:02d}-\d{{3}}$"

    assert stored_code is not None
    assert stored_metadata_code == stored_code
    assert re.match(expected_pattern, stored_code), f"Unexpected code format: {stored_code}"
