"""
BCV rate service for Budy AI.

Fetches and caches the official USD/VES rate with safe fallbacks.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import re
import ssl
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    import certifi
except Exception:  # pragma: no cover - optional dependency guard
    certifi = None

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class BCVRateError(RuntimeError):
    """Raised when the BCV rate cannot be resolved safely."""


class BCVRateService:
    """Fetch and cache BCV USD/VES rate snapshots."""

    # Public JSON proxies that expose BCV USD/VES — tried in order when the
    # primary provider is unreachable.
    FALLBACK_PROVIDERS: list = [
        "https://ve.dolarapi.com/v1/dolares/oficial",
        "https://api.exchangerate-api.com/v4/latest/USD",
    ]

    def __init__(
        self,
        provider_url: Optional[str] = None,
        ttl_minutes: Optional[int] = None,
        max_staleness_hours: Optional[int] = None,
    ) -> None:
        self.db = get_database_client()
        self.provider_url = provider_url or os.getenv("BCV_RATE_PROVIDER_URL", "https://www.bcv.org.ve/")
        self.ttl_minutes = ttl_minutes or int(os.getenv("BCV_RATE_TTL_MINUTES", "60"))
        self.max_staleness_hours = max_staleness_hours or int(
            os.getenv("BCV_RATE_MAX_STALENESS_HOURS", "24")
        )
        # Optional static override — set BCV_RATE_MANUAL_OVERRIDE=<rate> to bypass
        # all HTTP providers (e.g. for local dev without internet access).
        self._manual_override: Optional[float] = None
        raw_override = os.getenv("BCV_RATE_MANUAL_OVERRIDE", "").strip()
        if raw_override:
            try:
                self._manual_override = float(raw_override)
                logger.info("⚠️ BCV rate using manual override: %s", self._manual_override)
            except ValueError:
                logger.warning("⚠️ BCV_RATE_MANUAL_OVERRIDE is not a valid float: %s", raw_override)

    def get_current_rate(
        self,
        *,
        allow_stale: bool = True,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Return the current BCV snapshot, refreshing if needed."""
        latest = self._get_latest_snapshot()
        if latest and not force_refresh and self._is_fresh(latest):
            return latest

        try:
            fetched = self._fetch_provider_snapshot()
            saved = self._save_snapshot(fetched)
            logger.info("✅ BCV rate refreshed successfully: %s", saved.get("rate"))
            return saved
        except Exception as exc:
            if latest and allow_stale and self._is_within_staleness(latest):
                logger.warning("⚠️ BCV refresh failed, using stale snapshot: %s", exc)
                latest["is_stale"] = True
                return latest
            raise BCVRateError(f"Unable to resolve BCV rate: {exc}") from exc

    def convert_usd_to_ves(self, amount_usd: float, snapshot: Optional[Dict[str, Any]] = None) -> float:
        snapshot = snapshot or self.get_current_rate()
        rate = float(snapshot.get("rate") or 0)
        return round(float(amount_usd) * rate, 2)

    def _get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.db.client.table("exchange_rate_snapshots")
                .select("*")
                .eq("provider", "bcv")
                .eq("rate_type", "usd_ves")
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                return self._normalize_snapshot(response.data[0])
        except Exception as exc:
            logger.warning("⚠️ Failed to read cached BCV snapshot: %s", exc)
        return None

    def _save_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "provider": "bcv",
            "rate_type": "usd_ves",
            "base_currency": "USD",
            "quote_currency": "VES",
            "rate": snapshot["rate"],
            "source_url": snapshot.get("source_url") or self.provider_url,
            "raw_payload": snapshot.get("raw_payload") or {},
            "fetched_at": snapshot["fetched_at"],
            "expires_at": snapshot["expires_at"],
            "is_stale": False,
        }
        try:
            response = self.db.client.table("exchange_rate_snapshots").insert(payload).execute()
            if not response.data:
                raise BCVRateError("BCV snapshot insert returned no data")
            return self._normalize_snapshot(response.data[0])
        except Exception as exc:
            logger.warning("⚠️ Failed to persist BCV snapshot, returning in-memory snapshot: %s", exc)
            return self._normalize_snapshot(payload)

    def _fetch_provider_snapshot(self) -> Dict[str, Any]:
        if self._manual_override is not None:
            fetched_at = datetime.now(timezone.utc)
            expires_at = fetched_at + timedelta(minutes=self.ttl_minutes)
            return {
                "rate": self._manual_override,
                "source_url": "manual_override",
                "raw_payload": {"manual_override": True},
                "fetched_at": fetched_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_stale": False,
            }

        providers = [self.provider_url] + self.FALLBACK_PROVIDERS
        last_exc: Optional[Exception] = None
        for url in providers:
            try:
                body, content_type = self._fetch_provider_response(url)
                rate = self._extract_rate(body, content_type)
                break
            except Exception as exc:
                logger.warning("⚠️ BCV provider %s failed: %s", url, exc)
                last_exc = exc
        else:
            raise BCVRateError(f"All BCV providers failed. Last error: {last_exc}")
        fetched_at = datetime.now(timezone.utc)
        expires_at = fetched_at + timedelta(minutes=self.ttl_minutes)
        raw_payload: Dict[str, Any]
        if "json" in content_type.lower():
            try:
                raw_payload = json.loads(body)
            except json.JSONDecodeError:
                raw_payload = {"raw_body": body[:5000]}
        else:
            raw_payload = {"raw_body": body[:5000]}
        return {
            "rate": rate,
            "source_url": url,
            "raw_payload": raw_payload,
            "fetched_at": fetched_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_stale": False,
        }

    def _fetch_provider_response(self, url: Optional[str] = None) -> tuple[str, str]:
        target = url or self.provider_url
        headers = {"User-Agent": "BudyAI/1.0 (+https://budyai.local)"}
        req = urllib_request.Request(target, headers=headers)
        try:
            ssl_context = None
            if certifi is not None:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib_request.urlopen(req, timeout=10, context=ssl_context) as response:
                content_type = response.headers.get("Content-Type", "text/html")
                body = response.read().decode("utf-8", errors="ignore")
                return body, content_type
        except urllib_error.URLError as exc:
            raise BCVRateError(f"Provider request failed ({target}): {exc}") from exc

    def _extract_rate(self, body: str, content_type: str) -> float:
        if "json" in content_type.lower():
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise BCVRateError("Provider returned invalid JSON") from exc
            rate = self._extract_rate_from_json(payload)
            if rate is None:
                raise BCVRateError("JSON provider payload does not contain a BCV rate")
            return rate

        rate = self._extract_rate_from_html(body)
        if rate is None:
            raise BCVRateError("HTML provider payload does not contain a BCV rate")
        return rate

    def _extract_rate_from_json(self, payload: Any) -> Optional[float]:
        candidates = [
            payload.get("rate") if isinstance(payload, dict) else None,
            payload.get("usd") if isinstance(payload, dict) else None,
            payload.get("USD") if isinstance(payload, dict) else None,
            payload.get("promedio") if isinstance(payload, dict) else None,
            payload.get("precio") if isinstance(payload, dict) else None,
        ]
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                candidates.extend([data.get("rate"), data.get("usd"), data.get("USD")])
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and str(item.get("code", "")).upper() == "USD":
                        candidates.extend([item.get("rate"), item.get("value")])
            rates = payload.get("rates")
            if isinstance(rates, dict):
                candidates.append(rates.get("VES"))
        for candidate in candidates:
            parsed = self._parse_decimal(candidate)
            if parsed is not None:
                return parsed
        return None

    def _extract_rate_from_html(self, body: str) -> Optional[float]:
        normalized = re.sub(r"\s+", " ", body)
        patterns = [
            r"(?:USD|D[oó]lar(?:\s+estadounidense)?)\D{0,80}([0-9][0-9\.,]+)",
            r"id=[\"']dolar[\"'][^>]*>\D*([0-9][0-9\.,]+)",
            r"class=[\"'][^\"']*dolar[^\"']*[\"'][^>]*>\D*([0-9][0-9\.,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue
            parsed = self._parse_decimal(match.group(1))
            if parsed is not None:
                return parsed
        return None

    def _parse_decimal(self, raw_value: Any) -> Optional[float]:
        if raw_value in (None, ""):
            return None
        cleaned = str(raw_value).strip()
        cleaned = cleaned.replace("\xa0", "").replace("Bs.", "").replace("VES", "").strip()
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            value = Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
        return float(value)

    def _normalize_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(snapshot)
        normalized["rate"] = float(snapshot.get("rate") or 0)
        normalized["is_stale"] = bool(snapshot.get("is_stale", False))
        return normalized

    def _is_fresh(self, snapshot: Dict[str, Any]) -> bool:
        expires_at = self._parse_datetime(snapshot.get("expires_at"))
        if expires_at:
            return expires_at >= datetime.now(timezone.utc)
        fetched_at = self._parse_datetime(snapshot.get("fetched_at"))
        if not fetched_at:
            return False
        return fetched_at + timedelta(minutes=self.ttl_minutes) >= datetime.now(timezone.utc)

    def _is_within_staleness(self, snapshot: Dict[str, Any]) -> bool:
        fetched_at = self._parse_datetime(snapshot.get("fetched_at"))
        if not fetched_at:
            return False
        return fetched_at + timedelta(hours=self.max_staleness_hours) >= datetime.now(timezone.utc)

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


bcv_rate_service = BCVRateService()
