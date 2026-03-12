"""
Corporate code generation service for RFX and proposals.

Formats:
- RFX code: SAB-PP-{ORIGIN}-{YY}-{NNN}
- Proposal code: {RFX_CODE}-R{REV2}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class DocumentCodeService:
    CODE_PREFIX = "SAB"
    DEFAULT_DOCUMENT_TYPE = "PP"
    DEFAULT_ORIGIN = "AUT"
    HUMAN_ORIGIN = "H"

    ORIGIN_ALIASES = {
        "aut": "AUT",
        "automation": "AUT",
        "automatizado": "AUT",
        "ia": "AUT",
        "ai": "AUT",
        "h": "H",
        "human": "H",
        "humano": "H",
        "manual": "H",
    }

    def __init__(self, db_client):
        self.db_client = db_client

    @classmethod
    def normalize_origin(cls, origin: Optional[str]) -> str:
        normalized = str(origin or "").strip().lower()
        return cls.ORIGIN_ALIASES.get(normalized, cls.DEFAULT_ORIGIN)

    @staticmethod
    def build_rfx_code(document_type: str, origin: str, year: int, sequence: int) -> str:
        yy = int(year) % 100
        return f"{DocumentCodeService.CODE_PREFIX}-{document_type}-{origin}-{yy:02d}-{int(sequence):03d}"

    @classmethod
    def build_sequence_scope(cls, document_type: str, origin: str) -> str:
        return f"{document_type}-{origin}"

    @staticmethod
    def build_proposal_code(rfx_code: str, revision: int) -> str:
        return f"{rfx_code}-R{revision:02d}"

    def generate_rfx_code(
        self,
        rfx_type: Optional[str],
        year: Optional[int] = None,
        origin: Optional[str] = None,
    ) -> str:
        # Reserved for future variability per vertical/type.
        document_type = self.DEFAULT_DOCUMENT_TYPE
        normalized_origin = self.normalize_origin(origin)
        code_year = int(year or datetime.now(timezone.utc).year)
        sequence_scope = self.build_sequence_scope(document_type, normalized_origin)
        sequence = self._next_document_sequence("rfx", sequence_scope, code_year)
        return self.build_rfx_code(document_type, normalized_origin, code_year, sequence)

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
