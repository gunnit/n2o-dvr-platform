"""Pydantic schemas for VDT (Videoterminali) persistence (US-3.4 / US-3.5).

One VdtValutazione row per workstation/worker. The 20 h/week threshold
(D.Lgs. 81/2008 art. 173) is enforced server-side: ``esposto`` is always
derived from ``ore_settimanali`` so the form can never lie.

Surveillance scheduling (art. 176) is also derived: when the caller sets
``data_ultima_visita`` and ``eta_50_plus``, the server fills in
``data_prossima_visita`` and ``periodicita_sorveglianza`` via the
``vdt_surveillance`` module.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


IdoneitaVisiva = Literal["idoneo", "con prescrizioni", "non idoneo"]
PeriodicitaSorveglianza = Literal["biennale", "quinquennale"]


class VdtValutazioneBase(BaseModel):
    persona_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None

    postazione: str = Field(..., min_length=1, max_length=200)
    ore_settimanali: float = Field(..., ge=0, le=168)

    # Ergonomic checklist (REFERENCE_DATA.md VDT checklist)
    schermo_conforme: bool = True
    tastiera_separata: bool = True
    sedile_regolabile: bool = True
    poggiapiedi_disponibile: bool = True
    illuminazione_adeguata: bool = True
    riflessi_assenti: bool = True
    spazio_adeguato: bool = True
    pause_previste: bool = True

    # Surveillance
    idoneita_visiva: IdoneitaVisiva | None = None
    eta_50_plus: bool = False
    data_ultima_visita: date | None = None

    note: str | None = None


class VdtValutazioneCreate(VdtValutazioneBase):
    pass


class VdtValutazioneUpdate(BaseModel):
    persona_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None
    postazione: str | None = Field(None, min_length=1, max_length=200)
    ore_settimanali: float | None = Field(None, ge=0, le=168)

    schermo_conforme: bool | None = None
    tastiera_separata: bool | None = None
    sedile_regolabile: bool | None = None
    poggiapiedi_disponibile: bool | None = None
    illuminazione_adeguata: bool | None = None
    riflessi_assenti: bool | None = None
    spazio_adeguato: bool | None = None
    pause_previste: bool | None = None

    idoneita_visiva: IdoneitaVisiva | None = None
    eta_50_plus: bool | None = None
    data_ultima_visita: date | None = None

    note: str | None = None


class VdtValutazioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    persona_id: uuid.UUID | None
    ambiente_id: uuid.UUID | None

    postazione: str
    ore_settimanali: float
    esposto: bool

    schermo_conforme: bool
    tastiera_separata: bool
    sedile_regolabile: bool
    poggiapiedi_disponibile: bool
    illuminazione_adeguata: bool
    riflessi_assenti: bool
    spazio_adeguato: bool
    pause_previste: bool

    idoneita_visiva: str | None
    periodicita_sorveglianza: str | None
    eta_50_plus: bool
    data_ultima_visita: date | None
    data_prossima_visita: date | None

    note: str | None
    created_at: datetime
