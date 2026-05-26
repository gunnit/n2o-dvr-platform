"""POS schemas (US-4.8).

Covers the POS CRUD surface plus the DPI matrix sub-resource that powers
the role x phase DPI matrix UI. The matrix itself is free-form JSON so
the rules engine can evolve without schema churn — validation of the DPI
codes happens on the frontend (against the DPI_CATALOG keys returned by
the /meta endpoint).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# --- DPI matrix aliases ---------------------------------------------------

DpiMatrix = dict[str, dict[str, list[str]]]
"""{phase_key: {role_key: [dpi_code, ...]}}"""


# --- POS base / CRUD ------------------------------------------------------


class PosBase(BaseModel):
    cantiere_indirizzo: str = Field(..., min_length=1, max_length=500)
    cantiere_descrizione: str | None = None
    # Soggetti di riferimento (All. XV punto 3.2.1 b). CSE keeps the historic
    # `coordinatore_sicurezza` name for backwards compatibility; CSP lives in
    # the new `coordinatore_progettazione` field.
    committente: str | None = Field(None, max_length=255)
    progettista_responsabile: str | None = Field(None, max_length=255)
    direttore_lavori: str | None = Field(None, max_length=255)
    direttore_operativo_edilizia: str | None = Field(None, max_length=255)
    direttore_operativo_impianti: str | None = Field(None, max_length=255)
    responsabile_lavori: str | None = Field(None, max_length=255)
    coordinatore_progettazione: str | None = Field(None, max_length=255)
    coordinatore_sicurezza: str | None = Field(None, max_length=255)  # CSE
    data_inizio: date | None = None
    data_fine: date | None = None
    importo_lavori: float | None = None
    numero_massimo_lavoratori: int | None = None
    # Modalità organizzative (All. XV punto 3.2.1 c). Free-text.
    orario_lavoro_cantiere: str | None = None
    turni_descrizione: str | None = None
    riunioni_coordinamento: str | None = None
    # Organizzazione logistica.
    monoblocchi_installati: bool = False
    monoblocchi_dettagli: str | None = None
    modalita_pasti: str | None = None
    fasi_lavorative: list[dict] = Field(default_factory=list)
    valutazione_rumore: dict = Field(default_factory=dict)
    valutazione_vibrazioni: dict = Field(default_factory=dict)
    mezzi_attrezzature: list[dict] = Field(default_factory=list)
    sostanze_pericolose: list[dict] = Field(default_factory=list)
    dpi_matrix: DpiMatrix = Field(default_factory=dict)
    dpi_matrix_roles: list[str] = Field(default_factory=list)
    dpi_matrix_phases: list[str] = Field(default_factory=list)
    note: str | None = None


class PosCreate(BaseModel):
    # Only cantiere_indirizzo is required on create. Everything else can be
    # filled in later from the matrix editor / document generation flow.
    cantiere_indirizzo: str = Field(..., min_length=1, max_length=500)
    cantiere_descrizione: str | None = None
    committente: str | None = Field(None, max_length=255)
    progettista_responsabile: str | None = Field(None, max_length=255)
    direttore_lavori: str | None = Field(None, max_length=255)
    direttore_operativo_edilizia: str | None = Field(None, max_length=255)
    direttore_operativo_impianti: str | None = Field(None, max_length=255)
    responsabile_lavori: str | None = Field(None, max_length=255)
    coordinatore_progettazione: str | None = Field(None, max_length=255)
    coordinatore_sicurezza: str | None = Field(None, max_length=255)
    data_inizio: date | None = None
    data_fine: date | None = None
    importo_lavori: float | None = None
    numero_massimo_lavoratori: int | None = None
    orario_lavoro_cantiere: str | None = None
    turni_descrizione: str | None = None
    riunioni_coordinamento: str | None = None
    monoblocchi_installati: bool = False
    monoblocchi_dettagli: str | None = None
    modalita_pasti: str | None = None
    fasi_lavorative: list[dict] = Field(default_factory=list)
    valutazione_rumore: dict = Field(default_factory=dict)
    valutazione_vibrazioni: dict = Field(default_factory=dict)
    mezzi_attrezzature: list[dict] = Field(default_factory=list)
    sostanze_pericolose: list[dict] = Field(default_factory=list)
    dpi_matrix: DpiMatrix | None = None
    dpi_matrix_roles: list[str] | None = None
    dpi_matrix_phases: list[str] | None = None
    note: str | None = None


class PosUpdate(BaseModel):
    cantiere_indirizzo: str | None = Field(None, min_length=1, max_length=500)
    cantiere_descrizione: str | None = None
    committente: str | None = Field(None, max_length=255)
    progettista_responsabile: str | None = Field(None, max_length=255)
    direttore_lavori: str | None = Field(None, max_length=255)
    direttore_operativo_edilizia: str | None = Field(None, max_length=255)
    direttore_operativo_impianti: str | None = Field(None, max_length=255)
    responsabile_lavori: str | None = Field(None, max_length=255)
    coordinatore_progettazione: str | None = Field(None, max_length=255)
    coordinatore_sicurezza: str | None = Field(None, max_length=255)
    data_inizio: date | None = None
    data_fine: date | None = None
    importo_lavori: float | None = None
    numero_massimo_lavoratori: int | None = None
    orario_lavoro_cantiere: str | None = None
    turni_descrizione: str | None = None
    riunioni_coordinamento: str | None = None
    monoblocchi_installati: bool | None = None
    monoblocchi_dettagli: str | None = None
    modalita_pasti: str | None = None
    fasi_lavorative: list[dict] | None = None
    valutazione_rumore: dict | None = None
    valutazione_vibrazioni: dict | None = None
    mezzi_attrezzature: list[dict] | None = None
    sostanze_pericolose: list[dict] | None = None
    dpi_matrix: DpiMatrix | None = None
    dpi_matrix_roles: list[str] | None = None
    dpi_matrix_phases: list[str] | None = None
    note: str | None = None


class PosResponse(PosBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DPI matrix endpoint bodies ------------------------------------------


class DpiMatrixUpdate(BaseModel):
    """Body for ``POST /aziende/{id}/pos/{pos_id}/dpi-matrix``.

    ``matrix`` semantics:
      * ``None`` → rebuild from ``build_default_matrix(roles, phases)`` and
        overwrite whatever was in ``dpi_matrix`` (the "Rigenera dai default"
        action).
      * ``dict`` (possibly empty) → persist verbatim. Used for cell-level
        overrides — the frontend sends the full matrix every time.
    """

    roles: list[str] = Field(..., description="Roles selected for this POS")
    phases: list[str] = Field(..., description="Phases selected for this POS")
    matrix: DpiMatrix | None = Field(
        None,
        description=(
            "Full {phase: {role: [dpi_codes]}} matrix. Null = regenerate "
            "from the global rules engine."
        ),
    )


class DpiCatalogResponse(BaseModel):
    """GET /aziende/{id}/pos/meta/dpi-catalog — static lookup data."""

    roles: list[str]
    phases: list[str]
    dpi_catalog: dict[str, str]
