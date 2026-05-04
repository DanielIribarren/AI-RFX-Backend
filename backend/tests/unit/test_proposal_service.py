import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.services.proposals.proposal_service import ProposalService


def test_resolve_company_info_prefers_business_unit_branding():
    service = ProposalService.__new__(ProposalService)

    class FakeExecuteResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeExecuteResult(
                [
                    {
                        "id": "bu-1",
                        "name": "BizBites",
                        "brand_name": "BizBites by Sabra",
                        "support_email": "sales@bizbites.test",
                        "support_phone": "+58 212 555 0000",
                        "metadata": {"address": "Caracas, Venezuela"},
                    }
                ]
            )

    class FakeClient:
        def table(self, _table_name):
            return FakeQuery()

    class FakeDB:
        client = FakeClient()

        @staticmethod
        def get_organization(_organization_id):
            return {"id": "org-1", "name": "Sabra Corporation", "billing_email": "billing@sabra.test"}

    service.db = FakeDB()  # type: ignore[attr-defined]

    result = service._resolve_company_info({"organization_id": "org-1", "business_unit_id": "bu-1"})

    assert result["name"] == "BizBites by Sabra"
    assert result["email"] == "sales@bizbites.test"
    assert result["phone"] == "+58 212 555 0000"
    assert result["address"] == "Caracas, Venezuela"


def test_resolve_company_info_falls_back_to_organization():
    service = ProposalService.__new__(ProposalService)

    class FakeExecuteResult:
        data = []

    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeExecuteResult()

    class FakeClient:
        def table(self, _table_name):
            return FakeQuery()

    class FakeDB:
        client = FakeClient()

        @staticmethod
        def get_organization(_organization_id):
            return {"id": "org-1", "name": "Acme Services"}

    service.db = FakeDB()  # type: ignore[attr-defined]

    result = service._resolve_company_info({"organization_id": "org-1"})

    assert result["name"] == "Acme Services"
    assert result["address"] == "Address available upon request"
    assert result["email"] == ""
