"""
APU (Análisis de Precio Unitario) — Pydantic schemas.

Two layers:
- Input  models: what `apu_generator.py` builds from the RFX (post-normalization)
                 and feeds to the LLM. These mirror the contract documented in
                 `backend/prompts/apu_construction_ve.md`.
- Output models: what the LLM returns and what we validate before building Excel.
                 Strict bounds catch silent corruption that would produce a
                 numerically incorrect APU.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# INPUT (apu_generator.py → LLM)
# ─────────────────────────────────────────────────────────────────────────────


class APUProductInput(BaseModel):
    """One product item after the repo's naming variants have been normalized."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)


class APUInput(BaseModel):
    """Full payload sent to the LLM as the user message."""

    model_config = ConfigDict(extra="forbid")

    rfx_id: str
    project_name: str
    client_company: str
    rfx_date: str
    tasa_bcv: float = Field(0.0, ge=0)
    pct_costos_indirectos: float = Field(0.20, ge=0, le=1)
    pct_utilidad: float = Field(0.12, ge=0, le=1)
    products: List[APUProductInput]


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT (LLM → Excel builder)
# ─────────────────────────────────────────────────────────────────────────────


class APUItemCosto(BaseModel):
    """Single line item: material, mano de obra, or equipo."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(..., min_length=1, max_length=80)
    unidad: str = Field(..., min_length=1, max_length=20)
    cantidad: float = Field(..., ge=0)
    precio_unitario_usd: float = Field(..., ge=0)
    es_precio_estimado: bool


class APUPartida(BaseModel):
    """One full APU partida with its three cost components."""

    model_config = ConfigDict(extra="forbid")

    numero: str = Field(..., min_length=1, max_length=10)
    descripcion: str = Field(..., min_length=1, max_length=300)
    unidad: str = Field(..., min_length=1, max_length=20)
    quantity_obra: float = Field(..., gt=0)
    rendimiento_descripcion: str = Field("", max_length=300)
    materiales: List[APUItemCosto] = Field(default_factory=list)
    mano_obra: List[APUItemCosto] = Field(default_factory=list)
    equipos: List[APUItemCosto] = Field(default_factory=list)

    @field_validator("materiales", "mano_obra", "equipos")
    @classmethod
    def _no_negatives(cls, items: List[APUItemCosto]) -> List[APUItemCosto]:
        # Pydantic ge=0 already covers this per-field; this is a defense in depth
        # in case someone widens the field constraint later.
        for it in items:
            if it.cantidad < 0 or it.precio_unitario_usd < 0:
                raise ValueError("APU items must not contain negative numbers")
        return items


class APUOutput(BaseModel):
    """Top-level LLM output. This is the shape `apu_generator.py` validates."""

    model_config = ConfigDict(extra="forbid")

    rfx_id: str
    project_name: str
    client_company: str
    rfx_date: str
    tasa_bcv: float = Field(..., ge=0)
    tasa_bcv_missing: bool
    pct_costos_indirectos: float = Field(..., ge=0, le=1)
    pct_utilidad: float = Field(..., ge=0, le=1)
    pct_iva: float = Field(0.16, ge=0, le=1)
    partidas: List[APUPartida]
    warnings: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# API request (HTTP boundary → service)
# ─────────────────────────────────────────────────────────────────────────────


class APUGenerateRequest(BaseModel):
    """HTTP request body for POST /api/apu/generate."""

    model_config = ConfigDict(extra="ignore")

    rfx_id: str = Field(..., min_length=1)
    tasa_bcv: Optional[float] = Field(None, ge=0)
    pct_costos_indirectos: Optional[float] = Field(None, ge=0, le=1)
    pct_utilidad: Optional[float] = Field(None, ge=0, le=1)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT (apu_generator.py → API caller)
# ─────────────────────────────────────────────────────────────────────────────


class APUResult(BaseModel):
    """What the service returns to the API layer."""

    model_config = ConfigDict(extra="forbid")

    rfx_id: str
    excel_url: str
    excel_storage_path: str
    prompt_version: str
    llm_attempts: int
    warnings: List[str] = Field(default_factory=list)
    partidas_count: int
