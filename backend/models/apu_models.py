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

from typing import List, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


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
    specifications: Optional[str] = None
    notes: Optional[str] = None
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    unit_cost: Optional[float] = Field(None, ge=0)


class APUInput(BaseModel):
    """Full payload sent to the LLM as the user message."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    rfx_id: str
    project_name: str
    client_company: str
    rfx_date: str
    tasa_bcv: float = Field(0.0, ge=0)
    pct_admin_gg: float = Field(
        0.22,
        ge=0,
        le=1,
        validation_alias=AliasChoices("pct_admin_gg", "pct_costos_indirectos"),
        serialization_alias="pct_admin_gg",
    )
    pct_utilidad: float = Field(0.10, ge=0, le=1)
    pct_sobre_costo_labor: float = Field(6.6091, ge=0, le=20)
    products: List[APUProductInput]

    @property
    def pct_costos_indirectos(self) -> float:
        """Legacy alias kept until the Chevron builder fully replaces the old one."""
        return self.pct_admin_gg


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


class APUItemMaterial(BaseModel):
    """Chevron material row with desperdicio."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(..., min_length=1, max_length=80)
    unidad: str = Field(..., min_length=1, max_length=20)
    cantidad: float = Field(..., ge=0)
    desperdicio: float = Field(0.0, ge=0)
    precio_unitario_usd: float = Field(..., ge=0)
    es_precio_estimado: bool


class APUItemEquipo(BaseModel):
    """Chevron equipment row."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(..., min_length=1, max_length=80)
    cantidad_dias: float = Field(..., ge=0)
    costo_por_dia_usd: float = Field(..., ge=0)
    dep_o_alq: float = Field(1.0, ge=0)
    es_precio_estimado: bool


class APUItemMO(BaseModel):
    """Chevron labor row."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(..., min_length=1, max_length=80)
    cantidad_dias: float = Field(..., ge=0)
    costo_por_dia_usd: float = Field(..., ge=0)
    bono_usd: float = Field(0.0, ge=0)
    es_precio_estimado: bool


class APUPartida(BaseModel):
    """One full APU partida with backward-compatible and Chevron-ready fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    numero: str = Field(..., min_length=1, max_length=10)
    descripcion: str = Field(..., min_length=1, max_length=300)
    unidad: str = Field(..., min_length=1, max_length=20)
    cantidad_obra: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("cantidad_obra", "quantity_obra"),
        serialization_alias="cantidad_obra",
    )
    rendimiento_und_dia: float = Field(1.0, gt=0)
    rendimiento_descripcion: str = Field("", max_length=300)
    materiales: List[Union[APUItemMaterial, APUItemCosto]] = Field(default_factory=list)
    mano_obra: List[Union[APUItemMO, APUItemCosto]] = Field(default_factory=list)
    equipos: List[Union[APUItemEquipo, APUItemCosto]] = Field(default_factory=list)
    pct_sobre_costo_labor: float = Field(6.6091, ge=0, le=20)

    @field_validator("materiales", "mano_obra", "equipos")
    @classmethod
    def _no_negatives(
        cls,
        items: List[Union[APUItemMaterial, APUItemEquipo, APUItemMO, APUItemCosto]],
    ) -> List[Union[APUItemMaterial, APUItemEquipo, APUItemMO, APUItemCosto]]:
        for it in items:
            if isinstance(it, APUItemCosto):
                if it.cantidad < 0 or it.precio_unitario_usd < 0:
                    raise ValueError("APU items must not contain negative numbers")
        return items

    @property
    def quantity_obra(self) -> float:
        """Legacy alias used by the pre-Chevron builder."""
        return self.cantidad_obra


class APUOutput(BaseModel):
    """Top-level LLM output. This is the shape `apu_generator.py` validates."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    rfx_id: str
    project_name: str
    client_company: str
    rfx_date: str
    tasa_bcv: float = Field(..., ge=0)
    tasa_bcv_missing: bool
    pct_admin_gg: float = Field(
        ...,
        ge=0,
        le=1,
        validation_alias=AliasChoices("pct_admin_gg", "pct_costos_indirectos"),
        serialization_alias="pct_admin_gg",
    )
    pct_utilidad: float = Field(..., ge=0, le=1)
    pct_sobre_costo_labor: float = Field(6.6091, ge=0, le=20)
    pct_iva: float = Field(0.16, ge=0, le=1)
    partidas: List[APUPartida]
    warnings: List[str] = Field(default_factory=list)

    @property
    def pct_costos_indirectos(self) -> float:
        """Legacy alias used by the pre-Chevron builder."""
        return self.pct_admin_gg


# ─────────────────────────────────────────────────────────────────────────────
# API request (HTTP boundary → service)
# ─────────────────────────────────────────────────────────────────────────────


class APUGenerateRequest(BaseModel):
    """HTTP request body for POST /api/apu/generate."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    rfx_id: str = Field(..., min_length=1)
    tasa_bcv: Optional[float] = Field(None, ge=0)
    pct_admin_gg: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        validation_alias=AliasChoices("pct_admin_gg", "pct_costos_indirectos"),
        serialization_alias="pct_admin_gg",
    )
    pct_utilidad: Optional[float] = Field(None, ge=0, le=1)
    pct_sobre_costo_labor: Optional[float] = Field(None, ge=0, le=20)

    @property
    def pct_costos_indirectos(self) -> Optional[float]:
        """Legacy alias used by the current service signature."""
        return self.pct_admin_gg


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
