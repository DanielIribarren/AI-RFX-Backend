import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.services.budy_domain_service import BudyDomainService, is_virtual_business_unit_id
import pytest


def test_calculate_payment_summary_full_payment():
    service = BudyDomainService()
    proposal = {"pricing_snapshot": {"reference_total_usd": 500}}
    payments = [
        {"status": "confirmed", "amount_usd": 300},
        {"status": "confirmed", "amount_usd": 200},
        {"status": "submitted", "amount_usd": 50},
    ]

    summary = service._calculate_payment_summary(proposal, payments)

    assert summary["contract_total_usd"] == 500
    assert summary["confirmed_total_usd"] == 500
    assert summary["remaining_total_usd"] == 0
    assert summary["is_fully_paid"] is True


def test_calculate_payment_summary_partial_payment():
    service = BudyDomainService()
    proposal = {"total_cost": 800}
    payments = [
        {"status": "confirmed", "amount_usd": 300},
        {"status": "submitted", "amount_usd": 100},
    ]

    summary = service._calculate_payment_summary(proposal, payments)

    assert summary["contract_total_usd"] == 800
    assert summary["confirmed_total_usd"] == 300
    assert summary["submitted_total_usd"] == 100
    assert summary["remaining_total_usd"] == 500
    assert summary["is_fully_paid"] is False


def test_ensure_default_business_unit_falls_back_to_virtual_when_rls_blocks_insert():
    service = BudyDomainService()

    class FakeExecuteResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def insert(self, _payload):
            raise Exception('new row violates row-level security policy for table "business_units"')

        def execute(self):
            return FakeExecuteResult([])

    class FakeClient:
        def table(self, table_name):
            return FakeQuery(table_name)

    service.db._client = FakeClient()  # type: ignore[attr-defined]
    service.db.get_organization = lambda organization_id: {  # type: ignore[assignment]
        "id": organization_id,
        "name": "Sabra Corporation",
        "slug": "sabra-corporation",
    }

    unit = service.ensure_default_business_unit("org-123")

    assert unit["id"] == "virtual-org-123"
    assert unit["name"] == "Sabra Corporation"
    assert unit["metadata"]["virtual"] is True


def test_list_opportunities_passes_business_unit_and_stage_filters_to_db():
    service = BudyDomainService()
    captured = {}

    class FakeDB:
        def get_rfx_history(self, **kwargs):
            captured.update(kwargs)
            return [{"id": "rfx-1"}]

    service.db = FakeDB()  # type: ignore[assignment]
    service._batch_latest_proposals = lambda _rfx_ids: {}  # type: ignore[assignment]
    service._map_rfx_to_opportunity = lambda record, _proposal: {"id": record["id"]}  # type: ignore[assignment]

    result = service.list_opportunities(
        user_id="user-1",
        organization_id="org-1",
        business_unit_id="bu-1",
        sales_stage="sent",
    )

    assert result == [{"id": "rfx-1"}]
    assert captured["organization_id"] == "org-1"
    assert captured["business_unit_id"] == "bu-1"
    assert captured["sales_stage"] == "sent"


def test_list_opportunities_drops_virtual_business_unit_id_filter():
    service = BudyDomainService()
    captured = {}

    class FakeDB:
        def get_rfx_history(self, **kwargs):
            captured.update(kwargs)
            return []

    service.db = FakeDB()  # type: ignore[assignment]
    service._batch_latest_proposals = lambda _rfx_ids: {}  # type: ignore[assignment]
    service._map_rfx_to_opportunity = lambda record, _proposal: {"id": record["id"]}  # type: ignore[assignment]

    service.list_opportunities(
        user_id="user-1",
        organization_id="org-1",
        business_unit_id="virtual-org-1",
    )

    assert captured["business_unit_id"] is None


def test_is_virtual_business_unit_id_helper():
    assert is_virtual_business_unit_id("virtual-abc") is True
    assert is_virtual_business_unit_id("abc-virtual") is False
    assert is_virtual_business_unit_id("") is False
    assert is_virtual_business_unit_id(None) is False


def test_list_catalog_items_drops_virtual_business_unit_id_filter():
    service = BudyDomainService()
    captured = {"eq_calls": []}

    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def eq(self, field, value):
            captured["eq_calls"].append((field, value))
            return self

        def execute(self):
            class R:
                data = []
            return R()

    class FakeTable:
        def __call__(self, _name):
            return FakeQuery()

    class FakeClient:
        def table(self, name):
            return FakeQuery()

    class FakeDB:
        client = FakeClient()

    service.db = FakeDB()  # type: ignore[assignment]

    service.list_catalog_items("org-1", business_unit_id="virtual-org-1")

    eq_fields = [field for field, _ in captured["eq_calls"]]
    assert "business_unit_id" not in eq_fields
    assert ("organization_id", "org-1") in captured["eq_calls"]


def test_list_payment_methods_drops_virtual_business_unit_id_filter():
    service = BudyDomainService()
    captured = {"eq_calls": []}

    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def eq(self, field, value):
            captured["eq_calls"].append((field, value))
            return self

        def execute(self):
            class R:
                data = []
            return R()

    class FakeClient:
        def table(self, _name):
            return FakeQuery()

    class FakeDB:
        client = FakeClient()

    service.db = FakeDB()  # type: ignore[assignment]

    service.list_payment_methods("org-1", business_unit_id="virtual-org-1")

    eq_fields = [field for field, _ in captured["eq_calls"]]
    assert "business_unit_id" not in eq_fields
    assert ("organization_id", "org-1") in captured["eq_calls"]


def test_ensure_business_unit_access_rejects_virtual_id():
    service = BudyDomainService()

    class FakeDB:
        client = None

    service.db = FakeDB()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="business unit persistida"):
        service._ensure_business_unit_access("org-1", "virtual-org-1")


def test_publish_proposal_rejects_zero_priced_contract():
    service = BudyDomainService()

    class FakeDB:
        def get_document_by_id(self, _proposal_id):
            return {
                "id": "proposal-1",
                "rfx_id": "rfx-1",
                "total_cost": 0,
            }

        def get_rfx_products(self, _rfx_id):
            return [
                {
                    "product_name": "Cocktail service",
                    "estimated_unit_price": 100,
                    "unit_cost": 50,
                }
            ]

    service.db = FakeDB()  # type: ignore[assignment]

    import backend.services.budy_domain_service as budy_module

    original_get_and_validate = budy_module.get_and_validate_rfx_ownership
    try:
        budy_module.get_and_validate_rfx_ownership = lambda *_args, **_kwargs: (  # type: ignore[assignment]
            {"id": "rfx-1", "business_unit_id": None},
            None,
        )
        with pytest.raises(ValueError, match="Configure pricing so the proposal total is greater than \\$0"):
            service.publish_proposal(
                user_id="user-1",
                organization_id=None,
                proposal_id="proposal-1",
                payload={},
            )
    finally:
        budy_module.get_and_validate_rfx_ownership = original_get_and_validate  # type: ignore[assignment]


def test_get_opportunity_returns_backend_publish_readiness_issues():
    service = BudyDomainService()

    class FakeDB:
        def get_rfx_products(self, _rfx_id):
            return [
                {
                    "id": "prod-1",
                    "product_name": "Cocktail service",
                    "estimated_unit_price": 0,
                    "unit_cost": 25,
                },
                {
                    "id": "prod-2",
                    "product_name": "Waitstaff",
                    "estimated_unit_price": 150,
                    "unit_cost": 0,
                },
            ]

        def get_proposals_by_rfx_id(self, _rfx_id):
            return []

    service.db = FakeDB()  # type: ignore[assignment]

    import backend.services.budy_domain_service as budy_module

    original_get_and_validate = budy_module.get_and_validate_rfx_ownership
    try:
        budy_module.get_and_validate_rfx_ownership = lambda *_args, **_kwargs: (  # type: ignore[assignment]
            {
                "id": "rfx-1",
                "title": "",
                "companies": {"name": ""},
                "requesters": {},
            },
            None,
        )

        result = service.get_opportunity("user-1", "org-1", "rfx-1")

        assert result["can_publish_proposal"] is False
        assert "Add a title in Data View." in result["proposal_readiness_issues"]
        assert "Add the client name in Data View." in result["proposal_readiness_issues"]
        assert any("unit price" in issue for issue in result["proposal_readiness_issues"])
        assert any("unit cost" in issue for issue in result["proposal_readiness_issues"])
        assert "Generate the proposal draft from Budget before publishing." in result["proposal_readiness_issues"]
    finally:
        budy_module.get_and_validate_rfx_ownership = original_get_and_validate  # type: ignore[assignment]


def test_get_payment_submissions_normalizes_trailing_question_mark():
    service = BudyDomainService()

    class FakeExecuteResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeExecuteResult(
                [
                    {
                        "id": "payment-1",
                        "proof_file_url": "https://example.com/proof.png?",
                    }
                ]
            )

    class FakeClient:
        def table(self, _table_name):
            return FakeQuery()

    class FakeDB:
        client = FakeClient()

        @staticmethod
        def extract_storage_path_from_url(_bucket, url):
            assert url == "https://example.com/proof.png"
            return "proposal-1/proof.png"

        @staticmethod
        def create_signed_storage_url(_bucket, file_path, expires_in=3600):
            assert file_path == "proposal-1/proof.png"
            assert expires_in == 3600
            return "https://example.com/signed-proof.png?token=abc"

    service.db = FakeDB()  # type: ignore[assignment]

    result = service._get_payment_submissions("proposal-1")

    assert result[0]["proof_file_url"] == "https://example.com/signed-proof.png?token=abc"
