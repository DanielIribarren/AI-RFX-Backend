import os
from types import SimpleNamespace

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from backend.services.proposal_generator import ProposalGenerationService
from backend.services.document_code_service import DocumentCodeService
from backend.models.proposal_models import ProposalNotes


def _service() -> ProposalGenerationService:
    # We only need the pure HTML injection helper, not full service initialization.
    return object.__new__(ProposalGenerationService)


def test_inject_proposal_code_keeps_codigo_label_without_backreference_literals():
    service = _service()
    proposal_code = "SAB-PP-AUT-26-001-R01"
    html = "<p><strong>Código:</strong> OLD-123</p>"

    out = service._inject_proposal_code_in_html(html, proposal_code)

    assert "<strong>Código:</strong> SAB-PP-AUT-26-001-R01" in out
    assert "\\1" not in out
    assert "\\2" not in out


def test_inject_proposal_code_replaces_plain_codigo_pattern_without_literal_backreference():
    service = _service()
    proposal_code = "SAB-PP-AUT-26-001-R01"
    html = "<p>Código: OLD-PP-25-999-R01</p>"

    out = service._inject_proposal_code_in_html(html, proposal_code)

    assert "Código: SAB-PP-AUT-26-001-R01" in out
    assert "\\1" not in out


def test_inject_proposal_code_inserts_block_after_vigencia_without_backreference_literals():
    service = _service()
    proposal_code = "SAB-PP-AUT-26-001-R01"
    html = "<p><strong>Vigencia:</strong> 30 días</p>"

    out = service._inject_proposal_code_in_html(html, proposal_code)

    assert "<strong>Código:</strong> SAB-PP-AUT-26-001-R01" in out
    assert "\\1" not in out
    assert "\\2" not in out


def test_create_proposal_object_uses_display_code_without_revision_and_keeps_internal_code():
    service = _service()
    service.openai_config = SimpleNamespace(model="test-model")
    service.document_code_service = DocumentCodeService(SimpleNamespace(client=None))

    request = SimpleNamespace(
        rfx_id="8709c702-34e8-4f6f-ba93-f3eb533e6f85",
        notes=ProposalNotes(modality_description="", coordination="", additional_notes=""),
        history="",
    )
    proposal = service._create_proposal_object(
        rfx_data={"companies": {"name": "Cliente QA"}},
        html_content="<p><strong>Código:</strong> OLD</p>",
        proposal_request=request,
        pricing_calculation={"total": 100.0},
        proposal_code="SAB-PP-AUT-26-001",
        rfx_code="SAB-PP-AUT-26-001",
        proposal_revision=2,
    )

    metadata = proposal.metadata or {}
    assert metadata.get("proposal_code") == "SAB-PP-AUT-26-001"
    assert metadata.get("proposal_code_internal") == "SAB-PP-AUT-26-001-R02"
