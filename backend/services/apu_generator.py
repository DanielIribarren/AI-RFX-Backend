"""
APU Generator Service — Construction Civil Venezuela.

Pipeline contract (deliberately stricter than proposal_generator.py):
  1. Load RFX from DB.
  2. Normalize products[] (handles the 4-naming-conventions mess in one place).
  3. Call LLM with JSON-mode + temperature 0.0.
  4. Validate output with Pydantic — fail loud on bad shape.
  5. One automatic retry feeding the validation error back to the model.
  6. Run business invariants (partidas non-empty, items per partida, etc.).
  7. Build Excel with openpyxl using NATIVE formulas (subtotals, IVA, BCV).
  8. Upload to Supabase Storage and return a public URL.

Why this is NOT a copy of proposal_generator._call_ai:
  - proposal_generator returns broken HTML on retry failure (acceptable for visual).
  - We refuse to return a broken APU. Numerical errors propagate to invoices.
"""
from __future__ import annotations

import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import ValidationError

from backend.core.config import get_openai_config
from backend.core.database import get_database_client
from backend.models.apu_models import (
    APUInput,
    APUItemCosto,
    APUOutput,
    APUPartida,
    APUProductInput,
    APUResult,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_VERSION = "1.1"
PROMPT_FILENAME = "apu_construction_ve.md"

LLM_TEMPERATURE = 0.0
LLM_TOP_P = 1.0
LLM_MAX_TOKENS = 16000  # gpt-4o ceiling; 30 partidas with full breakdowns can run ~14k chars
LLM_MAX_ATTEMPTS = 2  # first try + 1 retry

STORAGE_BUCKET = "apu-exports"


# Excel style palette (mirrors the branding section in apu_construction_ve.md)
COLOR_HEADER_BG = "1F4E79"        # Azul acero
COLOR_TITLE_BG = "003366"          # Azul oscuro
COLOR_SECTION_BG = "D9E1F2"        # Azul grisáceo
COLOR_EDITABLE_BG = "FFF2CC"       # Amarillo (celda editable)
COLOR_TOTAL_BG = "FFE699"          # Amarillo más oscuro (total destacado)
COLOR_WHITE_TEXT = "FFFFFF"

FONT_NAME = "Arial"


class APUGenerationError(RuntimeError):
    """Raised when the APU pipeline cannot produce a valid output."""


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────


class APUGeneratorService:
    """Generates an APU Excel file for a given RFX."""

    def __init__(self) -> None:
        self.openai_config = get_openai_config()
        self.db_client = get_database_client()
        self.openai_client = None
        self._prompt_text = self._load_prompt()

    # -- public ---------------------------------------------------------------

    def generate(
        self,
        rfx_id: str,
        tasa_bcv: Optional[float] = None,
        pct_costos_indirectos: Optional[float] = None,
        pct_utilidad: Optional[float] = None,
    ) -> APUResult:
        """Run the full pipeline. Raises APUGenerationError on failure.

        Optional overrides take precedence over rfx_data values and defaults:
            tasa_bcv  → BCV rate to use (None = use 0 and flag as missing)
            pct_costos_indirectos → fraction in [0,1] (None = 0.20 default)
            pct_utilidad → fraction in [0,1] (None = 0.12 default)
        """
        started_at = time.time()
        logger.info("APU generation started for rfx_id=%s", rfx_id)

        rfx_data = self._load_rfx(rfx_id)
        apu_input = self._normalize_to_apu_input(
            rfx_id,
            rfx_data,
            tasa_bcv=tasa_bcv,
            pct_costos_indirectos=pct_costos_indirectos,
            pct_utilidad=pct_utilidad,
        )

        if not apu_input.products:
            raise APUGenerationError(
                f"RFX {rfx_id} has no products. Cannot generate APU."
            )

        output, attempts = self._call_llm_with_validation(apu_input)

        excel_bytes = _APUExcelBuilder(output).build()
        excel_url, storage_path = self._persist(rfx_id, excel_bytes)
        self._update_rfx_apu_metadata(
            rfx_id=rfx_id,
            excel_url=excel_url,
            storage_path=storage_path,
            partidas_count=len(output.partidas),
        )

        elapsed = time.time() - started_at
        logger.info(
            "APU generation completed rfx_id=%s attempts=%d partidas=%d elapsed=%.2fs",
            rfx_id, attempts, len(output.partidas), elapsed,
        )

        return APUResult(
            rfx_id=rfx_id,
            excel_url=excel_url,
            excel_storage_path=storage_path,
            prompt_version=PROMPT_VERSION,
            llm_attempts=attempts,
            warnings=output.warnings,
            partidas_count=len(output.partidas),
        )

    # -- internals: data ------------------------------------------------------

    def _load_rfx(self, rfx_id: str) -> Dict[str, Any]:
        rfx_data = self.db_client.get_rfx_by_id(rfx_id)
        if not rfx_data:
            raise APUGenerationError(f"RFX {rfx_id} not found")

        # Products live in a separate table (rfx_products) and are not embedded
        # by get_rfx_by_id. Mirror the proposal_generator pattern and merge them.
        products = self.db_client.get_rfx_products(rfx_id) or []
        rfx_data["productos"] = products
        return rfx_data

    def _normalize_to_apu_input(
        self,
        rfx_id: str,
        rfx_data: Dict[str, Any],
        tasa_bcv: Optional[float] = None,
        pct_costos_indirectos: Optional[float] = None,
        pct_utilidad: Optional[float] = None,
    ) -> APUInput:
        """Resolve the 4-naming-conventions mess into the prompt's canonical input."""
        productos = (
            rfx_data.get("productos")
            or rfx_data.get("products")
            or []
        )

        normalized: List[APUProductInput] = []
        for idx, p in enumerate(productos):
            normalized.append(
                APUProductInput(
                    id=str(p.get("id") or p.get("product_id") or f"p{idx + 1}"),
                    name=str(
                        p.get("product_name")
                        or p.get("name")
                        or p.get("nombre")
                        or f"Partida {idx + 1}"
                    ),
                    description=p.get("description") or p.get("descripcion"),
                    quantity=_safe_float(
                        p.get("quantity") or p.get("cantidad")
                    ),
                    unit=(
                        p.get("unit_of_measure")
                        or p.get("unit")
                        or p.get("unidad")
                    ),
                )
            )

        return APUInput(
            rfx_id=rfx_id,
            project_name=str(
                rfx_data.get("project_name")
                or rfx_data.get("title")
                or rfx_data.get("nombre_proyecto")
                or "Proyecto sin nombre"
            ),
            client_company=str(
                rfx_data.get("client_company")
                or rfx_data.get("company_name")
                or rfx_data.get("requester_company")
                or (rfx_data.get("companies") or {}).get("name")
                or "Cliente sin nombre"
            ),
            rfx_date=str(
                rfx_data.get("rfx_date")
                or rfx_data.get("created_at")
                or datetime.now(timezone.utc).date().isoformat()
            )[:10],
            tasa_bcv=(
                tasa_bcv
                if tasa_bcv is not None
                else _safe_float(rfx_data.get("tasa_bcv")) or 0.0
            ),
            pct_costos_indirectos=(
                pct_costos_indirectos
                if pct_costos_indirectos is not None
                else _safe_float(rfx_data.get("pct_costos_indirectos")) or 0.20
            ),
            pct_utilidad=(
                pct_utilidad
                if pct_utilidad is not None
                else _safe_float(rfx_data.get("pct_utilidad")) or 0.12
            ),
            products=normalized,
        )

    # -- internals: LLM -------------------------------------------------------

    def _call_llm_with_validation(self, apu_input: APUInput) -> Tuple[APUOutput, int]:
        """Strict pipeline: 1 try + 1 retry that includes the validation error.

        Three failure modes feed the retry loop:
          1. JSON parse error (output is not valid JSON)
          2. Pydantic schema error (shape/types/bounds wrong)
          3. Business invariant error (e.g., partida with all components empty)

        All three feed the same retry mechanism so the LLM can self-correct when
        we describe what went wrong.
        """
        last_error: Optional[str] = None
        last_raw_text: Optional[str] = None

        for attempt in range(1, LLM_MAX_ATTEMPTS + 1):
            raw_text = self._call_llm(
                apu_input,
                previous_attempt_text=last_raw_text,
                previous_error=last_error if attempt > 1 else None,
            )

            try:
                raw_dict = json.loads(raw_text)
            except json.JSONDecodeError as e:
                last_raw_text = raw_text
                last_error = f"Output is not valid JSON: {e.msg} at position {e.pos}"
                logger.warning(
                    "APU attempt %d: JSON parse failed (%s)", attempt, last_error
                )
                continue

            try:
                output = APUOutput.model_validate(raw_dict)
            except ValidationError as e:
                last_raw_text = raw_text
                last_error = self._summarize_validation_errors(e)
                logger.warning(
                    "APU attempt %d: schema validation failed (%s)", attempt, last_error
                )
                continue

            try:
                self._assert_invariants(output)
            except APUGenerationError as e:
                last_raw_text = raw_text
                last_error = f"Business invariant violated: {e}"
                logger.warning(
                    "APU attempt %d: invariants failed (%s)", attempt, last_error
                )
                continue

            return output, attempt

        raise APUGenerationError(
            f"LLM output failed validation after {LLM_MAX_ATTEMPTS} attempts. "
            f"Last error: {last_error}"
        )

    def _call_llm(
        self,
        apu_input: APUInput,
        previous_attempt_text: Optional[str] = None,
        previous_error: Optional[str] = None,
    ) -> str:
        client = self._get_openai_client()

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._prompt_text},
            {
                "role": "user",
                "content": apu_input.model_dump_json(indent=2),
            },
        ]

        if previous_attempt_text and previous_error:
            messages.append({"role": "assistant", "content": previous_attempt_text})
            messages.append({
                "role": "user",
                "content": (
                    "El JSON anterior falló validación. Errores:\n"
                    f"{previous_error}\n\n"
                    "Devuelve un JSON corregido que cumpla el contrato exactamente. "
                    "Solo el JSON, sin explicaciones, sin bloques de código."
                ),
            })

        response = client.chat.completions.create(
            model=self.openai_config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=LLM_TEMPERATURE,
            top_p=LLM_TOP_P,
            max_tokens=LLM_MAX_TOKENS,
        )

        choice = response.choices[0]
        content = (choice.message.content or "").strip()

        # When the model hits max_tokens it returns truncated (invalid) JSON.
        # Surface this loudly so the retry loop can attribute the failure correctly
        # rather than blaming the prompt.
        if choice.finish_reason == "length":
            logger.warning(
                "LLM output truncated (finish_reason=length, completion_tokens=%s). "
                "Increase LLM_MAX_TOKENS or reduce input partidas.",
                response.usage.completion_tokens if response.usage else "?",
            )

        return content

    def _get_openai_client(self):
        if self.openai_client is None:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=self.openai_config.api_key,
                max_retries=0,
            )
        return self.openai_client

    def _summarize_validation_errors(self, err: ValidationError) -> str:
        """Compact, model-friendly error summary."""
        lines = []
        for e in err.errors():
            loc = ".".join(str(x) for x in e["loc"])
            lines.append(f"- {loc}: {e['msg']}")
        return "\n".join(lines[:20])  # cap to keep retry payload bounded

    # -- internals: invariants ------------------------------------------------

    def _assert_invariants(self, output: APUOutput) -> None:
        if not output.partidas:
            raise APUGenerationError(
                "LLM returned zero partidas. Refusing to build empty APU."
            )

        for idx, partida in enumerate(output.partidas, start=1):
            total_items = (
                len(partida.materiales)
                + len(partida.mano_obra)
                + len(partida.equipos)
            )
            if total_items == 0:
                raise APUGenerationError(
                    f"Partida {idx} '{partida.descripcion}' has no items "
                    f"in any of materiales/mano_obra/equipos."
                )

    # -- internals: storage ---------------------------------------------------

    def _update_rfx_apu_metadata(
        self,
        rfx_id: str,
        excel_url: str,
        storage_path: str,
        partidas_count: int,
    ) -> None:
        """Track the latest APU on rfx_v2 so the UI can rehydrate without regenerating.

        Strict-mode: if this fails, we raise. Returning a successful APUResult while
        leaving the DB in an inconsistent state would mean the next page load
        wouldn't show the APU even though the file is in storage.
        """
        try:
            self.db_client.client.table("rfx_v2").update({
                "apu_excel_url": excel_url,
                "apu_excel_storage_path": storage_path,
                "apu_generated_at": datetime.now(timezone.utc).isoformat(),
                "apu_partidas_count": partidas_count,
                "apu_prompt_version": PROMPT_VERSION,
            }).eq("id", rfx_id).execute()
        except Exception as e:
            logger.error("APU metadata persist failed for rfx=%s: %s", rfx_id, e)
            raise APUGenerationError(
                f"APU generated but rfx_v2 metadata update failed: {e}"
            ) from e

    def _persist(self, rfx_id: str, excel_bytes: bytes) -> Tuple[str, str]:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        storage_path = f"{rfx_id}/apu-{ts}-{uuid.uuid4().hex[:8]}.xlsx"

        public_url = self.db_client.upload_file_to_storage(
            bucket=STORAGE_BUCKET,
            file_path=storage_path,
            file_data=excel_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        return public_url, storage_path

    # -- internals: prompt loading -------------------------------------------

    def _load_prompt(self) -> str:
        prompt_path = (
            Path(__file__).resolve().parent.parent / "prompts" / PROMPT_FILENAME
        )
        if not prompt_path.exists():
            raise APUGenerationError(
                f"APU prompt file not found at {prompt_path}"
            )
        return prompt_path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Excel builder
# ─────────────────────────────────────────────────────────────────────────────


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Single-sheet layout. Column map:
#   A: Descripción
#   B: Unidad
#   C: Cantidad
#   D: Precio Unitario USD
#   E: Subtotal USD     (formula = C * D)
#   F: Subtotal VES     (formula = E * tasa_bcv)
#
# Param cells (named) at fixed positions for formula references:
#   B9  = tasa_bcv             (yellow editable)
#   B10 = pct_costos_indirectos (yellow editable)
#   B11 = pct_utilidad          (yellow editable)
#   B12 = pct_iva               (fixed 0.16)
COL_DESC = "A"
COL_UNIT = "B"
COL_QTY = "C"
COL_PU_USD = "D"
COL_SUB_USD = "E"
COL_SUB_VES = "F"

CELL_TASA_BCV = "B9"
CELL_PCT_CI = "B10"
CELL_PCT_UTIL = "B11"
CELL_PCT_IVA = "B12"


class _APUExcelBuilder:
    """Builds the APU workbook. Formulas are native so the user can edit live."""

    def __init__(self, output: APUOutput) -> None:
        self.output = output
        self.wb = Workbook()
        self.ws: Worksheet = self.wb.active
        self.ws.title = "APU"
        self.row = 1

    # -- public ---------------------------------------------------------------

    def build(self) -> bytes:
        self._write_title()
        self._write_project_metadata()
        self._write_parameters()
        for partida in self.output.partidas:
            self._write_partida(partida)
        if self.output.warnings:
            self._write_warnings()
        self._adjust_columns()
        return self._to_bytes()

    # -- title ----------------------------------------------------------------

    def _write_title(self) -> None:
        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(row=self.row, column=1, value="ANÁLISIS DE PRECIOS UNITARIOS")
        cell.font = Font(name=FONT_NAME, size=16, bold=True, color=COLOR_WHITE_TEXT)
        cell.fill = PatternFill("solid", fgColor=COLOR_TITLE_BG)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        self.ws.row_dimensions[self.row].height = 28
        self.row += 1

        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(
            row=self.row, column=1,
            value="SARBA CORP — Construcción Civil Venezuela",
        )
        cell.font = Font(name=FONT_NAME, size=11, italic=True, color=COLOR_WHITE_TEXT)
        cell.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        self.ws.row_dimensions[self.row].height = 18
        self.row += 2  # leave a blank row

    # -- project metadata -----------------------------------------------------

    def _write_project_metadata(self) -> None:
        # 4 metadata rows; no trailing blank — the next section's colored header
        # provides the visual break, and the parameters block expects to start
        # at row 8 so that the named-cell layout (B9..B12) is preserved.
        labels = [
            ("Proyecto:", self.output.project_name),
            ("Cliente:", self.output.client_company),
            ("Fecha RFX:", self.output.rfx_date),
            ("RFX ID:", self.output.rfx_id),
        ]
        for label, value in labels:
            self.ws.cell(row=self.row, column=1, value=label).font = Font(
                name=FONT_NAME, bold=True
            )
            self.ws.merge_cells(f"B{self.row}:F{self.row}")
            cell = self.ws.cell(row=self.row, column=2, value=value)
            cell.font = Font(name=FONT_NAME)
            self.row += 1

    # -- parameters block -----------------------------------------------------

    def _write_parameters(self) -> None:
        # Section header (row 8 typically)
        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(row=self.row, column=1, value="PARÁMETROS GLOBALES")
        cell.font = Font(name=FONT_NAME, size=12, bold=True, color=COLOR_WHITE_TEXT)
        cell.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        self.row += 1

        # The next 4 rows MUST land at rows 9..12 to match CELL_TASA_BCV etc.
        # We assert that to avoid silent layout drift.
        if self.row != 9:
            raise APUGenerationError(
                f"Layout drift: parameters block expected at row 9, got row {self.row}"
            )

        bcv_value = self.output.tasa_bcv if not self.output.tasa_bcv_missing else 0
        self._write_param_row("Tasa BCV (USD → VES):", bcv_value, fmt="#,##0.00")
        self._write_param_row("% Costos Indirectos:", self.output.pct_costos_indirectos, fmt="0.00%")
        self._write_param_row("% Utilidad:", self.output.pct_utilidad, fmt="0.00%")
        self._write_param_row("% IVA (fijo):", self.output.pct_iva, fmt="0.00%", editable=False)

        # Register named cells so formulas can reference them by name (more robust)
        self._define_name("tasa_bcv", CELL_TASA_BCV)
        self._define_name("pct_ci", CELL_PCT_CI)
        self._define_name("pct_util", CELL_PCT_UTIL)
        self._define_name("pct_iva", CELL_PCT_IVA)

        self.row += 1  # blank

        if self.output.tasa_bcv_missing:
            self.ws.merge_cells(f"A{self.row}:F{self.row}")
            cell = self.ws.cell(
                row=self.row, column=1,
                value=("⚠ Tasa BCV no provista. Ingrese el valor en la celda B9 "
                       "para que los precios en VES se calculen automáticamente."),
            )
            cell.font = Font(name=FONT_NAME, size=10, italic=True, color="C00000")
            self.row += 2

    def _write_param_row(self, label: str, value: float, fmt: str, editable: bool = True) -> None:
        self.ws.cell(row=self.row, column=1, value=label).font = Font(
            name=FONT_NAME, bold=True
        )
        cell = self.ws.cell(row=self.row, column=2, value=value)
        cell.number_format = fmt
        cell.font = Font(name=FONT_NAME)
        if editable:
            cell.fill = PatternFill("solid", fgColor=COLOR_EDITABLE_BG)
        self.row += 1

    # -- partidas -------------------------------------------------------------

    def _write_partida(self, partida: APUPartida) -> None:
        # Partida title bar
        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(
            row=self.row, column=1,
            value=f"PARTIDA {partida.numero} — {partida.descripcion}",
        )
        cell.font = Font(name=FONT_NAME, size=12, bold=True, color=COLOR_WHITE_TEXT)
        cell.fill = PatternFill("solid", fgColor=COLOR_TITLE_BG)
        cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        self.ws.row_dimensions[self.row].height = 22
        self.row += 1

        # Sub-header line
        self.ws.cell(row=self.row, column=1, value="Unidad:").font = Font(
            name=FONT_NAME, bold=True, size=9
        )
        self.ws.cell(row=self.row, column=2, value=partida.unidad).font = Font(
            name=FONT_NAME, size=9
        )
        self.ws.cell(row=self.row, column=3, value="Cantidad obra:").font = Font(
            name=FONT_NAME, bold=True, size=9
        )
        c = self.ws.cell(row=self.row, column=4, value=partida.quantity_obra)
        c.font = Font(name=FONT_NAME, size=9)
        c.number_format = "#,##0.00"
        self.row += 1

        if partida.rendimiento_descripcion:
            self.ws.cell(row=self.row, column=1, value="Rendimiento:").font = Font(
                name=FONT_NAME, bold=True, italic=True, size=9
            )
            self.ws.merge_cells(f"B{self.row}:F{self.row}")
            self.ws.cell(
                row=self.row, column=2, value=partida.rendimiento_descripcion,
            ).font = Font(name=FONT_NAME, italic=True, size=9)
            self.row += 1
        self.row += 1  # blank

        # Three cost components, each returns the row of its USD subtotal cell
        sub_mat_row = self._write_component("MATERIALES", partida.materiales)
        sub_mo_row = self._write_component("MANO DE OBRA", partida.mano_obra)
        sub_eq_row = self._write_component("EQUIPOS", partida.equipos)

        # Totals block
        self._write_totals(sub_mat_row, sub_mo_row, sub_eq_row)
        self.row += 2  # spacing between partidas

    def _write_component(
        self, title: str, items: List[APUItemCosto]
    ) -> Optional[int]:
        """Returns the row index of the USD subtotal cell, or None if empty."""
        # Component title
        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(row=self.row, column=1, value=title)
        cell.font = Font(name=FONT_NAME, size=11, bold=True)
        cell.fill = PatternFill("solid", fgColor=COLOR_SECTION_BG)
        cell.alignment = Alignment(horizontal="left", indent=1)
        self.row += 1

        # Column headers
        headers = ["Descripción", "Unidad", "Cantidad", "P.U. USD", "Subtotal USD", "Subtotal VES"]
        for col_idx, header in enumerate(headers, start=1):
            c = self.ws.cell(row=self.row, column=col_idx, value=header)
            c.font = Font(name=FONT_NAME, bold=True, size=10, color=COLOR_WHITE_TEXT)
            c.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
            c.alignment = Alignment(horizontal="center")
            c.border = _thin_border()
        self.row += 1

        if not items:
            self.ws.merge_cells(f"A{self.row}:F{self.row}")
            cell = self.ws.cell(
                row=self.row, column=1, value="(sin ítems en este componente)",
            )
            cell.font = Font(name=FONT_NAME, italic=True, size=9, color="808080")
            cell.alignment = Alignment(horizontal="center")
            self.row += 1
            return None

        first_item_row = self.row
        for item in items:
            self._write_item_row(item)
        last_item_row = self.row - 1

        # Subtotal row
        self.ws.cell(row=self.row, column=3, value="Subtotal").font = Font(
            name=FONT_NAME, bold=True
        )
        sub_usd_cell = self.ws.cell(
            row=self.row, column=5,
            value=f"=SUM({COL_SUB_USD}{first_item_row}:{COL_SUB_USD}{last_item_row})",
        )
        sub_usd_cell.font = Font(name=FONT_NAME, bold=True)
        sub_usd_cell.number_format = "#,##0.00"
        sub_usd_cell.fill = PatternFill("solid", fgColor=COLOR_SECTION_BG)

        sub_ves_cell = self.ws.cell(
            row=self.row, column=6,
            value=f"={COL_SUB_USD}{self.row}*tasa_bcv",
        )
        sub_ves_cell.font = Font(name=FONT_NAME, bold=True)
        sub_ves_cell.number_format = "#,##0.00"
        sub_ves_cell.fill = PatternFill("solid", fgColor=COLOR_SECTION_BG)

        subtotal_row = self.row
        self.row += 1
        return subtotal_row

    def _write_item_row(self, item: APUItemCosto) -> None:
        r = self.row
        self.ws.cell(row=r, column=1, value=item.descripcion).font = Font(name=FONT_NAME, size=10)
        self.ws.cell(row=r, column=2, value=item.unidad).alignment = Alignment(horizontal="center")

        qty = self.ws.cell(row=r, column=3, value=item.cantidad)
        qty.number_format = "#,##0.0000"
        qty.alignment = Alignment(horizontal="right")

        pu = self.ws.cell(row=r, column=4, value=item.precio_unitario_usd)
        pu.number_format = "#,##0.0000"
        pu.alignment = Alignment(horizontal="right")
        if item.es_precio_estimado:
            pu.fill = PatternFill("solid", fgColor=COLOR_EDITABLE_BG)

        sub_usd = self.ws.cell(row=r, column=5, value=f"={COL_QTY}{r}*{COL_PU_USD}{r}")
        sub_usd.number_format = "#,##0.00"
        sub_usd.alignment = Alignment(horizontal="right")

        sub_ves = self.ws.cell(row=r, column=6, value=f"={COL_SUB_USD}{r}*tasa_bcv")
        sub_ves.number_format = "#,##0.00"
        sub_ves.alignment = Alignment(horizontal="right")

        for col in range(1, 7):
            self.ws.cell(row=r, column=col).border = _thin_border()

        self.row += 1

    def _write_totals(
        self,
        sub_mat_row: Optional[int],
        sub_mo_row: Optional[int],
        sub_eq_row: Optional[int],
    ) -> None:
        # Build a SUM expression over whichever subtotals exist (skip empty components)
        usd_refs = [
            f"{COL_SUB_USD}{r}" for r in (sub_mat_row, sub_mo_row, sub_eq_row) if r
        ]
        directo_formula = "+".join(usd_refs) if usd_refs else "0"

        # Costo Directo
        directo_row = self.row
        self._write_total_row("Costo Directo", f"={directo_formula}")

        # Costos Indirectos
        ci_row = self.row
        self._write_total_row(
            "Costos Indirectos",
            f"={COL_SUB_USD}{directo_row}*pct_ci",
        )

        # Utilidad — calculated on (Directo + CI), which is the venezuelan convention
        util_row = self.row
        self._write_total_row(
            "Utilidad",
            f"=({COL_SUB_USD}{directo_row}+{COL_SUB_USD}{ci_row})*pct_util",
        )

        # Subtotal sin IVA
        sub_no_iva_row = self.row
        self._write_total_row(
            "Subtotal sin IVA",
            f"={COL_SUB_USD}{directo_row}+{COL_SUB_USD}{ci_row}+{COL_SUB_USD}{util_row}",
        )

        # IVA
        iva_row = self.row
        self._write_total_row(
            "IVA",
            f"={COL_SUB_USD}{sub_no_iva_row}*pct_iva",
        )

        # Precio Unitario (highlighted)
        self._write_total_row(
            "PRECIO UNITARIO",
            f"={COL_SUB_USD}{sub_no_iva_row}+{COL_SUB_USD}{iva_row}",
            highlight=True,
        )

    def _write_total_row(self, label: str, formula: str, highlight: bool = False) -> None:
        r = self.row
        label_cell = self.ws.cell(row=r, column=1, value=label)
        label_cell.font = Font(name=FONT_NAME, bold=True, size=11)
        self.ws.merge_cells(f"A{r}:D{r}")
        label_cell.alignment = Alignment(horizontal="right", indent=1)

        usd_cell = self.ws.cell(row=r, column=5, value=formula)
        usd_cell.number_format = "#,##0.00"
        usd_cell.font = Font(name=FONT_NAME, bold=True)
        usd_cell.alignment = Alignment(horizontal="right")

        ves_cell = self.ws.cell(row=r, column=6, value=f"={COL_SUB_USD}{r}*tasa_bcv")
        ves_cell.number_format = "#,##0.00"
        ves_cell.font = Font(name=FONT_NAME, bold=True)
        ves_cell.alignment = Alignment(horizontal="right")

        if highlight:
            for col in (1, 5, 6):
                self.ws.cell(row=r, column=col).fill = PatternFill(
                    "solid", fgColor=COLOR_TOTAL_BG
                )
                self.ws.cell(row=r, column=col).font = Font(
                    name=FONT_NAME, bold=True, size=12,
                )
            self.ws.row_dimensions[r].height = 22

        for col in range(1, 7):
            self.ws.cell(row=r, column=col).border = _thin_border()

        self.row += 1

    # -- warnings -------------------------------------------------------------

    def _write_warnings(self) -> None:
        self.ws.merge_cells(f"A{self.row}:F{self.row}")
        cell = self.ws.cell(row=self.row, column=1, value="ADVERTENCIAS")
        cell.font = Font(name=FONT_NAME, size=11, bold=True, color="C00000")
        cell.fill = PatternFill("solid", fgColor=COLOR_SECTION_BG)
        self.row += 1
        for w in self.output.warnings:
            self.ws.merge_cells(f"A{self.row}:F{self.row}")
            wc = self.ws.cell(row=self.row, column=1, value=f"• {w}")
            wc.font = Font(name=FONT_NAME, size=9, color="606060")
            wc.alignment = Alignment(wrap_text=True)
            self.row += 1

    # -- finalize -------------------------------------------------------------

    def _adjust_columns(self) -> None:
        widths = {"A": 38, "B": 12, "C": 14, "D": 16, "E": 18, "F": 18}
        for col, w in widths.items():
            self.ws.column_dimensions[col].width = w

    def _define_name(self, name: str, cell_ref: str) -> None:
        defined_name = DefinedName(name=name, attr_text=f"APU!${cell_ref[0]}${cell_ref[1:]}")
        self.wb.defined_names[name] = defined_name

    def _to_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.wb.save(buf)
        return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _thin_border() -> Border:
    side = Side(style="thin", color="CCCCCC")
    return Border(left=side, right=side, top=side, bottom=side)
