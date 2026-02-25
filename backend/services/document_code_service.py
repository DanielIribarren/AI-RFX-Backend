"""
Corporate code generation service for RFX and proposals.

Formats:
- RFX code: RFX-{DOMAIN}-{YEAR}-{SEQ6}
- Proposal code: {RFX_CODE}-R{REV2}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class DocumentCodeService:
    DOMAIN_PREFIXES = {
        "catering": "CAT",
        "construction": "CON",
        "events": "EVT",
        "event": "EVT",
        "supplies": "SUP",
        "services": "SRV",
        "maintenance": "MNT",
    }

    def __init__(self, db_client):
        self.db_client = db_client

    @classmethod
    def get_domain_prefix(cls, rfx_type: Optional[str]) -> str:
        normalized = str(rfx_type or "").strip().lower()
        return cls.DOMAIN_PREFIXES.get(normalized, "OTH")

    @staticmethod
    def build_rfx_code(domain_prefix: str, year: int, sequence: int) -> str:
        return f"RFX-{domain_prefix}-{year}-{sequence:06d}"

    @staticmethod
    def build_proposal_code(rfx_code: str, revision: int) -> str:
        return f"{rfx_code}-R{revision:02d}"

    def generate_rfx_code(self, rfx_type: Optional[str], year: Optional[int] = None) -> str:
        prefix = self.get_domain_prefix(rfx_type)
        code_year = int(year or datetime.now(timezone.utc).year)
        sequence = self._next_document_sequence("rfx", prefix, code_year)
        return self.build_rfx_code(prefix, code_year, sequence)

    def next_proposal_revision(self, rfx_id: str | UUID) -> int:
        try:
            response = self.db_client.client.rpc(
                "next_proposal_revision",
                {"p_rfx_id": str(rfx_id)},
            ).execute()
            revision = int(self._extract_scalar(response.data) or 0)
            if revision <= 0:
                raise ValueError(f"Invalid proposal revision response: {response.data}")
            return revision
        except Exception as exc:
            logger.error(f"❌ Failed to get next proposal revision for {rfx_id}: {exc}")
            raise

    def _next_document_sequence(self, code_type: str, domain_prefix: str, year: int) -> int:
        try:
            response = self.db_client.client.rpc(
                "next_document_code_seq",
                {
                    "p_code_type": code_type,
                    "p_domain_prefix": domain_prefix,
                    "p_year": int(year),
                },
            ).execute()
            sequence = int(self._extract_scalar(response.data) or 0)
            if sequence <= 0:
                raise ValueError(f"Invalid document sequence response: {response.data}")
            return sequence
        except Exception as exc:
            logger.error(
                "❌ Failed to get next document code sequence "
                f"(type={code_type}, domain={domain_prefix}, year={year}): {exc}"
            )
            raise

    @staticmethod
    def _extract_scalar(payload: Any) -> Any:
        if payload is None:
            return None

        # Supabase RPC can return scalar, list[scalar], or list[{fn_name: value}]
        if isinstance(payload, list):
            if not payload:
                return None
            first = payload[0]
            if isinstance(first, dict):
                if len(first) == 1:
                    return next(iter(first.values()))
                # defensive fallback for unexpected shapes
                for key in (
                    "next_document_code_seq",
                    "next_proposal_revision",
                    "value",
                ):
                    if key in first:
                        return first[key]
                return None
            return first

        if isinstance(payload, dict):
            if len(payload) == 1:
                return next(iter(payload.values()))
            for key in ("next_document_code_seq", "next_proposal_revision", "value"):
                if key in payload:
                    return payload[key]

        return payload
