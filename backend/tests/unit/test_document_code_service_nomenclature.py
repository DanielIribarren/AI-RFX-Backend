import os
from datetime import datetime, timezone

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from backend.services.document_code_service import DocumentCodeService


class _RPCResponse:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class _FakeSupabaseClient:
    def __init__(self):
        self.sequences = {}
        self.revisions = {}

    def rpc(self, fn_name, payload):
        if fn_name == "next_document_code_seq":
            key = (
                str(payload.get("p_code_type")),
                str(payload.get("p_domain_prefix")),
                int(payload.get("p_year")),
            )
            self.sequences[key] = self.sequences.get(key, 0) + 1
            return _RPCResponse(self.sequences[key])

        if fn_name == "next_proposal_revision":
            rfx_id = str(payload.get("p_rfx_id"))
            self.revisions[rfx_id] = self.revisions.get(rfx_id, 0) + 1
            return _RPCResponse(self.revisions[rfx_id])

        raise AssertionError(f"Unexpected RPC function: {fn_name}")


class _FakeDBClient:
    def __init__(self):
        self.client = _FakeSupabaseClient()


def test_generate_rfx_code_uses_sab_pp_aut_yy_nnn_format():
    db = _FakeDBClient()
    service = DocumentCodeService(db)
    year = datetime.now(timezone.utc).year
    yy = year % 100

    code_1 = service.generate_rfx_code(rfx_type="catering", year=year, origin="automatizado")
    code_2 = service.generate_rfx_code(rfx_type="catering", year=year, origin="ia")
    code_h = service.generate_rfx_code(rfx_type="catering", year=year, origin="humano")

    assert code_1 == f"SAB-PP-AUT-{yy:02d}-001"
    assert code_2 == f"SAB-PP-AUT-{yy:02d}-002"
    assert code_h == f"SAB-PP-H-{yy:02d}-001"


def test_build_proposal_code_uses_rfx_code_plus_revision_suffix():
    db = _FakeDBClient()
    service = DocumentCodeService(db)
    year = datetime.now(timezone.utc).year
    yy = year % 100

    rfx_code = service.generate_rfx_code(rfx_type="catering", year=year, origin="aut")
    proposal_code = service.build_proposal_code(rfx_code, revision=1)

    assert rfx_code == f"SAB-PP-AUT-{yy:02d}-001"
    assert proposal_code == f"{rfx_code}-R01"
