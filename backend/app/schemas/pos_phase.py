"""Structured POS phase schema (US-4.7).

The POS row already carries ``fasi_lavorative: JSONB`` on the ORM model.
Before US-4.7 that column was a free-form ``list[dict]`` — any shape the
frontend happened to persist. This module pins the shape so the
phase-builder UI, the POS docx generator, and the dependency graph can
share a single contract.

Legal grounding: D.Lgs. 81/2008 Titolo IV, Allegato XV punto 2.2.2 —
individuazione delle fasi, analisi dei rischi e misure di prevenzione
per singola fase. The per-phase NIOSH / rumore / vibrazioni snapshots
correspond to the allegati richiamati nell'Allegato XV.2 (NIOSH via ISO
11228-1, rumore D.Lgs. 81 Titolo VIII Capo II, vibrazioni Capo III).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Sub-schemas per-phase ----------------------------------------------


class PhaseNiosh(BaseModel):
    """NIOSH inputs + computed result for a single lifting task in this phase.

    Fields mirror ``NioshRequest`` (``backend/app/schemas/calculation.py``) so
    the frontend can reuse the existing ``POST /api/v1/calculate/niosh``
    endpoint and then persist the response alongside the inputs. ``plr`` /
    ``ir`` / ``livello`` are optional on write — the frontend may compute
    locally before saving.
    """

    model_config = ConfigDict(extra="forbid")

    peso_sollevato: float = Field(..., gt=0, le=200, description="Peso sollevato (kg)")
    cp: float = Field(..., gt=0, le=40, description="Costante di peso (kg)")
    fattore_a: float = Field(..., ge=0, le=1)
    fattore_b: float = Field(..., ge=0, le=1)
    fattore_c: float = Field(..., ge=0, le=1)
    fattore_d: float = Field(..., ge=0, le=1)
    fattore_e: float = Field(..., ge=0, le=1)
    fattore_f: float = Field(..., ge=0, le=1)
    plr: float | None = Field(None, description="Peso Limite Raccomandato calcolato (kg)")
    ir: float | None = Field(None, description="Indice di sollevamento calcolato")
    livello: Literal["VERDE", "GIALLA", "ROSSA"] | None = None


class PhaseRumore(BaseModel):
    """Noise exposure snapshot for this phase (D.Lgs. 81 Titolo VIII Capo II).

    ``lex_8h_dba`` is the daily personal exposure averaged to 8 hours.
    Thresholds: 80 dB(A) → informativa, 85 → DPI obbligatori, 87 → limite
    di azione superato.
    """

    model_config = ConfigDict(extra="forbid")

    lex_8h_dba: float = Field(..., ge=0, le=140, description="LEX,8h (dB(A))")
    fascia: Literal["<80", "80-85", "85-87", ">87"] | None = None
    dpi_obbligatori: bool = False
    note: str | None = Field(None, max_length=500)


class PhaseVibrazioni(BaseModel):
    """Hand-arm and whole-body vibration exposure for this phase.

    Units: m/s² root-mean-square normalised to 8 hours (A(8)).
    Limits per D.Lgs. 81 Titolo VIII Capo III:
      * Mano-braccio: azione 2.5, limite 5.0
      * Corpo intero: azione 0.5, limite 1.0
    """

    model_config = ConfigDict(extra="forbid")

    a8_mano_braccio: float | None = Field(None, ge=0, le=30)
    a8_corpo_intero: float | None = Field(None, ge=0, le=30)
    entro_limiti: bool = True
    note: str | None = Field(None, max_length=500)


# --- Phase itself ---------------------------------------------------------


class PosPhase(BaseModel):
    """One work-phase row persisted to ``pos.fasi_lavorative``.

    ``id`` is client-assigned (UUID string). It's the stable key used by
    ``dipende_da`` and by the frontend drag-and-drop. We don't persist a
    separate phase UUID on the database side — phases live inside the
    JSONB column keyed by this ``id``.

    ``ordine`` is the 0-based authoritative order. The frontend drag
    handle rewrites this field. The POS docx generator renders phases
    sorted by ``ordine`` so the printed document matches what the
    operator arranged on screen.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64, description="Stable client-assigned phase id")
    ordine: int = Field(..., ge=0, le=10_000)
    nome: str = Field(..., min_length=1, max_length=200)
    descrizione: str | None = Field(None, max_length=4000)
    rischi: list[str] = Field(default_factory=list)
    dpi: list[str] = Field(default_factory=list)
    mezzi: list[str] = Field(default_factory=list)
    niosh: PhaseNiosh | None = None
    rumore: PhaseRumore | None = None
    vibrazioni: PhaseVibrazioni | None = None
    dipende_da: list[str] = Field(
        default_factory=list,
        description="IDs of phases this phase depends on (must precede it)",
    )

    @field_validator("rischi", "dpi", "mezzi", "dipende_da")
    @classmethod
    def _strip_and_dedup(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for item in v:
            if not isinstance(item, str):
                continue
            trimmed = item.strip()
            if trimmed and trimmed not in seen:
                seen.append(trimmed)
        return seen


class PosPhasesUpdate(BaseModel):
    """Body for ``PUT /aziende/{id}/pos/{pos_id}/fasi``."""

    model_config = ConfigDict(extra="forbid")

    fasi: list[PosPhase] = Field(..., description="Complete ordered phase list")
