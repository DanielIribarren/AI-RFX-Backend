import os
import re
import sys
import types
from datetime import datetime, timezone
from uuid import UUID, uuid4

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

if "jose" not in sys.modules:
    jose_stub = types.ModuleType("jose")

    class _JWTError(Exception):
        pass

    class _JWT:
        @staticmethod
        def encode(*args, **kwargs):
            return "test-token"

        @staticmethod
        def decode(*args, **kwargs):
            return {}

    jose_stub.JWTError = _JWTError
    jose_stub.jwt = _JWT
    sys.modules["jose"] = jose_stub

if "backend.services.chat_agent" not in sys.modules:
    chat_agent_stub = types.ModuleType("backend.services.chat_agent")

    class _DummyChatAgent:
        def __init__(self, *args, **kwargs):
            pass

    chat_agent_stub.ChatAgent = _DummyChatAgent
    sys.modules["backend.services.chat_agent"] = chat_agent_stub

if "backend.services.rfx_chat_service" not in sys.modules:
    rfx_chat_service_stub = types.ModuleType("backend.services.rfx_chat_service")

    class _DummyRFXChatService:
        def __init__(self, *args, **kwargs):
            pass

    rfx_chat_service_stub.RFXChatService = _DummyRFXChatService
    sys.modules["backend.services.rfx_chat_service"] = rfx_chat_service_stub

import pytest
from flask import Flask

from backend.api import proposals as proposals_api
from backend.api import rfx as rfx_api
from backend.api import rfx_chat as rfx_chat_api
from backend.models.chat_models import ChatMetadata, ChatResponse, ChangeType, RFXChange
from backend.models.proposal_models import GeneratedProposal, ProposalStatus
from backend.models.rfx_models import RFXProcessed, RFXStatus, RFXType
from backend.services.document_code_service import DocumentCodeService
import backend.services.proposal_generator as proposal_generator_module
from backend.services.rfx_processor import RFXProcessorService
import backend.utils.auth_middleware as auth_middleware


class _RPCResponse:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class _FakeSupabaseClient:
    def __init__(self):
        self.document_sequences = {}
        self.proposal_revisions = {}

    def rpc(self, fn_name, payload):
        if fn_name == "next_document_code_seq":
            key = (
                str(payload.get("p_code_type")),
                str(payload.get("p_domain_prefix")),
                int(payload.get("p_year")),
            )
            self.document_sequences[key] = self.document_sequences.get(key, 0) + 1
            return _RPCResponse(self.document_sequences[key])

        if fn_name == "next_proposal_revision":
            rfx_id = str(payload.get("p_rfx_id"))
            self.proposal_revisions[rfx_id] = self.proposal_revisions.get(rfx_id, 0) + 1
            return _RPCResponse(self.proposal_revisions[rfx_id])

        raise AssertionError(f"Unexpected RPC function in test: {fn_name}")


class _FakeDatabaseClient:
    def __init__(self):
        self.client = _FakeSupabaseClient()
        self._companies = {}
        self._requesters = {}
        self.rfx_by_id = {}
        self.rfx_products = {}
        self.generated_documents = {}
        self.processing_status = {}
        self.regeneration_count = {}

    def insert_company(self, company_data):
        company_id = f"company-{len(self._companies) + 1}"
        company = {"id": company_id, **(company_data or {})}
        self._companies[company_id] = company
        return company

    def insert_requester(self, requester_data):
        requester_id = f"requester-{len(self._requesters) + 1}"
        requester = {"id": requester_id, **(requester_data or {})}
        self._requesters[requester_id] = requester
        return requester

    def insert_rfx(self, rfx_data):
        payload = dict(rfx_data or {})
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self.rfx_by_id[str(payload["id"])] = payload
        return payload

    def insert_rfx_products(self, rfx_id, products):
        self.rfx_products[str(rfx_id)] = list(products or [])
        return self.rfx_products[str(rfx_id)]

    def insert_rfx_history(self, _history):
        return {}

    def get_rfx_by_id(self, rfx_id):
        record = self.rfx_by_id.get(str(rfx_id))
        if not record:
            return None
        company = self._companies.get(record.get("company_id"), {})
        requester = self._requesters.get(record.get("requester_id"), {})
        return {**record, "companies": company, "requesters": requester}

    def get_rfx_products(self, rfx_id):
        return list(self.rfx_products.get(str(rfx_id), []))

    def get_proposals_by_rfx_id(self, rfx_id):
        proposals = [
            p for p in self.generated_documents.values()
            if str(p.get("rfx_id")) == str(rfx_id) and p.get("document_type") == "proposal"
        ]
        return sorted(proposals, key=lambda p: p.get("created_at", ""), reverse=True)

    def save_generated_document(self, doc_data):
        payload = dict(doc_data or {})
        self.generated_documents[str(payload["id"])] = payload
        return str(payload["id"])

    def upsert_processing_status(self, rfx_id, status_data):
        self.processing_status[str(rfx_id)] = dict(status_data or {})
        return self.processing_status[str(rfx_id)]

    def increment_regeneration_count(self, rfx_id):
        rid = str(rfx_id)
        self.regeneration_count[rid] = self.regeneration_count.get(rid, 0) + 1
        return self.regeneration_count[rid]


class _FakeSessionService:
    _sessions = {}

    def _build_first_message(self, preview_data):
        return f"Review the extracted preview for {preview_data.get('company_name', 'the request')}."

    def create_session(
        self,
        user_id,
        organization_id,
        preview_data,
        validated_data,
        evaluation_metadata=None,
        status="clarification",
        conversation_state=None,
        recent_events=None,
    ):
        session_id = str(uuid4())
        payload = {
            "id": session_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "status": status,
            "review_required": True,
            "review_confirmed": False,
            "preview_data": dict(preview_data or {}),
            "validated_data": dict(validated_data or {}),
            "evaluation_metadata": dict(evaluation_metadata or {}),
            "conversation_state": dict(conversation_state or {}),
            "recent_events": list(recent_events or []),
        }
        self._sessions[session_id] = payload
        return payload

    def get_session(self, session_id):
        return self._sessions.get(str(session_id))

    def get_session_for_user(self, session_id, user_id, organization_id):
        session = self.get_session(session_id)
        if not session:
            return None
        if str(session.get("user_id")) != str(user_id):
            return None
        if session.get("organization_id") and str(session.get("organization_id")) != str(organization_id):
            return None
        return session

    def update_session(self, session_id, updates):
        session = self._sessions.get(str(session_id))
        if not session:
            return None
        session.update(dict(updates or {}))
        return session

    def append_event(self, session_id, role, message, payload=None):
        session = self._sessions.get(str(session_id))
        if not session:
            return
        events = list(session.get("recent_events") or [])
        events.append({
            "role": role,
            "message": message,
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session["recent_events"] = events[-40:]

    def mark_confirmed(self, session_id, rfx_id):
        return self.update_session(
            session_id,
            {
                "status": "confirmed",
                "review_confirmed": True,
                "confirmed_rfx_id": str(rfx_id),
            },
        )


class _FakeCreditsService:
    def check_free_regeneration_available(self, organization_id, rfx_id):
        return False, 0, "No free regeneration available"

    def use_free_regeneration(self, rfx_id):
        return {"status": "success"}

    def check_credits_available(self, organization_id, operation, user_id=None):
        return True, 100, "OK"

    def consume_credits(self, organization_id, operation, rfx_id, user_id=None, description=""):
        return {"status": "success", "credits_remaining": 95}


class _FakeConversationStateService:
    async def upsert_state(self, **kwargs):
        return kwargs


class _PreviewProcessor:
    def __init__(self, *args, **kwargs):
        pass

    def process_rfx_case_preview(self, rfx_input, blobs, user_id=None, organization_id=None):
        preview_products = [
            {
                "id": "prod-1",
                "nombre": "Coffee break",
                "cantidad": 1,
                "unidad": "servicio",
                "precio_unitario": 120.0,
                "costo_unitario": 75.0,
                "total_estimated_cost": 120.0,
            },
        ]
        preview_data = {
            "id": str(uuid4()),
            "title": "Evento Corporativo QA",
            "description": "Prueba de flujo review->confirm",
            "email": "qa@sabra.test",
            "requester_name": "QA User",
            "company_name": "Sabra QA",
            "currency": "USD",
            "delivery_date": "2026-03-10",
            "delivery_time": "10:00:00",
            "location": "Caracas",
            "requirements": "Servicio completo",
            "requirements_confidence": 0.95,
            "products": preview_products,
            "metadata_json": {
                "nombre_empresa": "Sabra QA",
                "validated_currency": "USD",
            },
            "source_text": rfx_input.extracted_content or "RFX QA source text",
            "rfx_type": "catering",
        }
        validated_data = {
            "title": "Evento Corporativo QA",
            "nombre_empresa": "Sabra QA",
            "nombre_solicitante": "QA User",
            "email": "qa@sabra.test",
            "lugar": "Caracas",
            "fecha": "2026-03-10",
            "productos": preview_products,
        }
        return {
            "preview_data": preview_data,
            "validated_data": validated_data,
            "evaluation_metadata": {},
        }


def _build_confirm_processor(fake_db):
    class _ConfirmProcessor:
        _save_rfx_to_database = RFXProcessorService._save_rfx_to_database
        _fallback_next_rfx_sequence = RFXProcessorService._fallback_next_rfx_sequence

        def __init__(self, *args, **kwargs):
            self.db_client = fake_db
            self.document_code_service = DocumentCodeService(fake_db)

        def _create_rfx_processed(self, validated_data, rfx_input, evaluation_metadata=None):
            metadata_json = {
                "nombre_empresa": validated_data.get("nombre_empresa", "Sabra QA"),
                "email_empresa": "empresa@sabra.test",
                "telefono_empresa": "+58 000-000",
                "telefono_solicitante": "+58 111-111",
                "cargo_solicitante": "Compras",
                "validated_currency": "USD",
            }
            return RFXProcessed(
                id=uuid4(),
                rfx_type=RFXType.CATERING,
                title=validated_data.get("title", "RFX QA"),
                location=validated_data.get("lugar", "Caracas"),
                status=RFXStatus.IN_PROGRESS,
                original_pdf_text=rfx_input.extracted_content or "",
                requested_products=validated_data.get("productos") or [],
                metadata_json=metadata_json,
                requester_name=validated_data.get("nombre_solicitante", "QA User"),
                company_name=validated_data.get("nombre_empresa", "Sabra QA"),
                email=validated_data.get("email", "qa@sabra.test"),
                products=[],
            )

    return _ConfirmProcessor


def _build_fake_proposal_generation_service(fake_db):
    class _FakeProposalGenerationService:
        async def generate_proposal(self, rfx_data, proposal_request):
            code_service = DocumentCodeService(fake_db)
            rfx_id = str(proposal_request.rfx_id)
            rfx_record = fake_db.get_rfx_by_id(rfx_id) or {}
            rfx_code = rfx_record.get("rfx_code") or ((rfx_record.get("metadata_json") or {}).get("rfx_code"))
            if not rfx_code:
                raise AssertionError("RFX code missing before proposal generation in E2E test")

            revision = code_service.next_proposal_revision(rfx_id)
            proposal_internal_code = code_service.build_proposal_code(rfx_code, revision)
            proposal_code = rfx_code
            total_cost = float(sum(proposal_request.costs or []))
            created_at = datetime.now(timezone.utc)
            html_content = (
                "<html><body>"
                f"<p><strong>Código:</strong> {proposal_code}</p>"
                f"<p><strong>RFX:</strong> {rfx_code}</p>"
                "</body></html>"
            )

            proposal = GeneratedProposal(
                id=uuid4(),
                rfx_id=UUID(rfx_id),
                content_markdown="",
                content_html=html_content,
                itemized_costs=[],
                total_cost=total_cost,
                notes=proposal_request.notes,
                status=ProposalStatus.GENERATED,
                created_at=created_at,
                updated_at=created_at,
                metadata={
                    "proposal_code": proposal_code,
                    "proposal_code_internal": proposal_internal_code,
                    "rfx_code": rfx_code,
                    "proposal_revision": revision,
                },
            )

            fake_db.save_generated_document(
                {
                    "id": str(proposal.id),
                    "rfx_id": rfx_id,
                    "document_type": "proposal",
                    "content_html": html_content,
                    "total_cost": total_cost,
                    "created_at": created_at.isoformat(),
                    "metadata": proposal.metadata,
                    "proposal_code": proposal_internal_code,
                    "rfx_code_snapshot": rfx_code,
                    "proposal_revision": revision,
                    "version": 1,
                }
            )
            return proposal

    return _FakeProposalGenerationService


@pytest.fixture
def e2e_client(monkeypatch):
    fake_db = _FakeDatabaseClient()
    test_user_id = str(uuid4())

    monkeypatch.setattr(auth_middleware, "decode_token", lambda _token: {"sub": test_user_id})
    monkeypatch.setattr(
        auth_middleware.user_repository,
        "get_by_id",
        lambda _uuid: {
            "id": test_user_id,
            "email": "qa@sabra.test",
            "status": "active",
            "organization_id": None,
        },
    )

    monkeypatch.setattr(rfx_api, "RFXProcessorService", _PreviewProcessor)
    monkeypatch.setattr(rfx_api, "RFXProcessingSessionService", _FakeSessionService)
    monkeypatch.setattr(rfx_api, "get_credits_service", lambda: _FakeCreditsService())
    monkeypatch.setattr(
        rfx_api,
        "_submit_preview_processing",
        lambda session_id, rfx_input, valid_files, user_id, organization_id: rfx_api._process_preview_session(
            session_id,
            rfx_input,
            valid_files,
            user_id,
            organization_id,
        ),
    )
    monkeypatch.setattr(rfx_chat_api, "RFXProcessingSessionService", _FakeSessionService)
    monkeypatch.setattr(
        rfx_chat_api,
        "_get_rfx_processing_types",
        lambda: (__import__("backend.models.rfx_models", fromlist=["RFXInput", "RFXType"]).RFXInput,
                 __import__("backend.models.rfx_models", fromlist=["RFXInput", "RFXType"]).RFXType,
                 _build_confirm_processor(fake_db)),
    )
    monkeypatch.setattr(rfx_chat_api, "RFXConversationStateService", _FakeConversationStateService)
    monkeypatch.setattr(rfx_chat_api, "_get_database_client_instance", lambda: fake_db)
    monkeypatch.setattr(rfx_chat_api, "_get_credits_service_instance", lambda: _FakeCreditsService())

    monkeypatch.setattr(proposals_api, "get_database_client", lambda: fake_db)
    monkeypatch.setattr(proposals_api, "get_credits_service", lambda: _FakeCreditsService())
    monkeypatch.setattr(
        proposal_generator_module,
        "ProposalGenerationService",
        _build_fake_proposal_generation_service(fake_db),
    )

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rfx_api.rfx_bp)
    app.register_blueprint(rfx_chat_api.rfx_chat_bp)
    app.register_blueprint(proposals_api.proposals_bp)

    return app.test_client(), fake_db


def test_e2e_process_confirm_and_generate_proposal_with_corporate_nomenclature(e2e_client):
    client, fake_db = e2e_client
    headers = {"Authorization": "Bearer integration-test-token"}

    process_response = client.post(
        "/api/rfx/process",
        data={
            "id": "RFX-E2E-001",
            "tipo_rfx": "catering",
            "contenido_extraido": "Necesitamos un coffee break para 30 personas.",
        },
        headers=headers,
    )
    assert process_response.status_code == 200
    process_data = process_response.get_json()
    assert process_data["status"] == "success"
    assert process_data["review_required"] is True
    assert process_data["workflow_status"] == "processing_preview"
    session_id = process_data["session_id"]
    assert session_id

    review_state_response = client.get(
        f"/api/rfx/session/{session_id}/review/state",
        headers=headers,
    )
    assert review_state_response.status_code == 200
    review_state = review_state_response.get_json()["data"]
    assert review_state["workflow_status"] == "extracted_pending_review"
    assert review_state["preview_ready"] is True

    confirm_response = client.post(
        f"/api/rfx/session/{session_id}/review/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.get_json()
    assert confirm_data["status"] == "success"
    final_rfx_id = confirm_data["data"]["rfx_id"]
    assert final_rfx_id
    assert confirm_data["data"]["proposal_generated"] is True

    confirmed_state_response = client.get(
        f"/api/rfx/session/{session_id}/review/state",
        headers=headers,
    )
    assert confirmed_state_response.status_code == 200
    confirmed_state = confirmed_state_response.get_json()["data"]
    assert confirmed_state["review_confirmed"] is True
    assert confirmed_state["confirmed_rfx_id"] == final_rfx_id

    saved_rfx = fake_db.rfx_by_id.get(final_rfx_id)
    assert saved_rfx is not None, "Expected persisted rfx_v2 row in fake DB"
    saved_rfx_code = saved_rfx.get("rfx_code")
    assert saved_rfx_code is not None
    assert re.match(r"^SAB-PP-AUT-\d{2}-\d{3}$", saved_rfx_code), f"Unexpected rfx_code: {saved_rfx_code}"
    assert (saved_rfx.get("metadata_json") or {}).get("rfx_code") == saved_rfx_code

    saved_docs = list(fake_db.generated_documents.values())
    assert len(saved_docs) == 1
    assert re.match(r"^SAB-PP-AUT-\d{2}-\d{3}-R\d{2}$", saved_docs[0]["proposal_code"])
    saved_codes = saved_docs[0].get("metadata") or {}
    assert saved_codes.get("rfx_code") == saved_rfx_code
    assert re.match(r"^SAB-PP-AUT-\d{2}-\d{3}$", saved_codes.get("proposal_code", ""))
    assert saved_docs[0]["rfx_code_snapshot"] == saved_rfx_code


def test_session_chat_persists_preview_updates_before_confirm(e2e_client, monkeypatch):
    client, _fake_db = e2e_client
    headers = {"Authorization": "Bearer integration-test-token"}

    process_response = client.post(
        "/api/rfx/process",
        data={
            "id": "RFX-E2E-CHAT-001",
            "tipo_rfx": "catering",
            "contenido_extraido": "Necesitamos un cocktail para 85 personas en La Castellana.",
        },
        headers=headers,
    )
    assert process_response.status_code == 200
    session_id = process_response.get_json()["session_id"]

    class _FakeSessionReviewChatService:
        def process_message(self, **_kwargs):
            return ChatResponse(
                status="success",
                message="I added beverages and updated the delivery location.",
                confidence=0.92,
                reasoning=None,
                changes=[
                    RFXChange(
                        type=ChangeType.ADD_PRODUCT,
                        target="new",
                        data={
                            "nombre": "Beverage station",
                            "cantidad": 3,
                            "unidad": "servicios",
                            "precio_unitario": 25.0,
                            "costo_unitario": 10.0,
                        },
                        description="Added beverage station",
                    ),
                    RFXChange(
                        type=ChangeType.UPDATE_FIELD,
                        target="delivery_location",
                        data={"delivery_location": "La Castellana"},
                        description="Updated delivery location",
                    ),
                ],
                requires_confirmation=False,
                options=[],
                metadata=ChatMetadata(tokens_used=111, cost_usd=None, processing_time_ms=40, model_used="test-model"),
            )

    monkeypatch.setattr(
        rfx_chat_api,
        "_create_session_review_chat_service",
        lambda: _FakeSessionReviewChatService(),
    )
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

    chat_response = client.post(
        f"/api/rfx/session/{session_id}/chat",
        data={
            "id": session_id,
            "message": "Add three beverage stations and update the delivery location to La Castellana.",
            "context": "{}",
        },
        headers=headers,
    )
    assert chat_response.status_code == 200
    chat_data = chat_response.get_json()
    assert chat_data["status"] == "success"
    assert len(chat_data["preview_data"]["products"]) == 2
    assert chat_data["preview_data"]["location"] == "La Castellana"

    review_state_response = client.get(
        f"/api/rfx/session/{session_id}/review/state",
        headers=headers,
    )
    assert review_state_response.status_code == 200
    preview_data = review_state_response.get_json()["data"]["preview_data"]
    assert len(preview_data["products"]) == 2
    assert preview_data["location"] == "La Castellana"


def test_confirm_session_review_skips_auto_generation_when_preview_has_no_pricing(e2e_client, monkeypatch):
    client, fake_db = e2e_client
    headers = {"Authorization": "Bearer integration-test-token"}

    class _ZeroPricingPreviewProcessor:
        def __init__(self, *args, **kwargs):
            pass

        def process_rfx_case_preview(self, rfx_input, blobs, user_id=None, organization_id=None):
            preview_products = [
                {
                    "id": "prod-zero-1",
                    "nombre": "Cocktail service",
                    "cantidad": 1,
                    "unidad": "servicio",
                    "precio_unitario": 0.0,
                    "costo_unitario": 0.0,
                    "total_estimated_cost": 0.0,
                }
            ]
            preview_data = {
                "id": str(uuid4()),
                "title": "Evento sin pricing",
                "description": "QA zero pricing",
                "email": "qa@sabra.test",
                "requester_name": "QA User",
                "company_name": "Sabra QA",
                "currency": "USD",
                "delivery_date": "2026-03-10",
                "location": "Caracas",
                "requirements": "Servicio completo",
                "products": preview_products,
                "source_text": rfx_input.extracted_content or "",
                "rfx_type": "catering",
            }
            validated_data = {
                "title": "Evento sin pricing",
                "nombre_empresa": "Sabra QA",
                "nombre_solicitante": "QA User",
                "email": "qa@sabra.test",
                "lugar": "Caracas",
                "fecha": "2026-03-10",
                "productos": preview_products,
            }
            return {
                "preview_data": preview_data,
                "validated_data": validated_data,
                "evaluation_metadata": {},
            }

    applied_pricing_payloads = []

    monkeypatch.setattr(rfx_api, "RFXProcessorService", _ZeroPricingPreviewProcessor)
    monkeypatch.setattr(
        rfx_chat_api,
        "_apply_review_pricing_config",
        lambda rfx_id, pricing_config: applied_pricing_payloads.append((rfx_id, pricing_config)) or True,
    )
    monkeypatch.setattr(
        rfx_chat_api,
        "_generate_initial_proposal_for_rfx",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Auto-generation should be skipped when total_estimated is zero")),
    )

    process_response = client.post(
        "/api/rfx/process",
        data={
            "id": "RFX-E2E-ZERO-001",
            "tipo_rfx": "catering",
            "contenido_extraido": "Necesitamos un cocktail para 50 personas.",
        },
        headers=headers,
    )
    assert process_response.status_code == 200
    session_id = process_response.get_json()["session_id"]

    confirm_response = client.post(
        f"/api/rfx/session/{session_id}/review/confirm",
        json={
            "pricing_config": {
                "coordination_enabled": True,
                "coordination_rate": 0.18,
                "cost_per_person_enabled": True,
                "headcount": 50,
            }
        },
        headers=headers,
    )
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.get_json()
    assert confirm_data["status"] == "success"
    assert confirm_data["data"]["proposal_generated"] is False
    assert confirm_data["data"]["proposal_skipped"] is True
    assert confirm_data["data"]["pricing_config_applied"] is True
    assert confirm_data["data"]["total_estimated"] == 0.0
    assert applied_pricing_payloads, "Expected review pricing config to be applied before finishing confirmation"
    assert fake_db.generated_documents == {}
