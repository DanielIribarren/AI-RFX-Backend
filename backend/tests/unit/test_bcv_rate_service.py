import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.services.bcv_rate_service import BCVRateService


def test_extract_rate_from_html_with_decimal_comma():
    service = BCVRateService(provider_url="https://example.test")
    html = """
    <div class="currency-card">
      <span>USD</span>
      <strong>Bs. 99,12</strong>
    </div>
    """

    rate = service._extract_rate(html, "text/html")

    assert rate == 99.12


def test_extract_rate_from_json_payload():
    service = BCVRateService(provider_url="https://example.test")
    payload = '{"data": {"rate": "101,55"}}'

    rate = service._extract_rate(payload, "application/json")

    assert rate == 101.55


def test_save_snapshot_returns_in_memory_value_when_insert_fails():
    service = BCVRateService(provider_url="https://example.test")

    class FailingTable:
        def insert(self, _payload):
            raise Exception("new row violates row-level security policy for table exchange_rate_snapshots")

    class FailingClient:
        def table(self, _name):
            return FailingTable()

    service.db._client = FailingClient()  # type: ignore[attr-defined]

    snapshot = service._save_snapshot(
        {
            "rate": 36.5,
            "source_url": "manual_override",
            "raw_payload": {"manual_override": True},
            "fetched_at": "2026-03-20T00:00:00+00:00",
            "expires_at": "2026-03-20T01:00:00+00:00",
            "is_stale": False,
        }
    )

    assert snapshot["rate"] == 36.5
    assert snapshot["provider"] == "bcv"
