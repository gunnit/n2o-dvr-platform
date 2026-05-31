"""Pydantic schemas for Rischio Chimico (MoVaRisCh) exposures.

One record per (worker x substance). The operator (or the AI suggester)
provides the exposure inputs; the server runs the MoVaRisCh maths
(app.services.movarisch_calculator) and persists the derived results.

Option strings are constrained to the documented MoVaRisCh sets — the same
Literals the calculator accepts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Documented option sets (mirror movarisch_calculator) ---
ProprietaFisiche = Literal[
    "Solido - Nebbia",
    "Bassa Volatilità",
    "Media / Alta volatilità e Polveri fini",
    "Stato gassoso",
]
QuantitaClasse = Literal["< 0,1 Kg", "0,1 - 1 Kg", "1 - 10 Kg", "10 - 100 Kg", ">= 100 Kg"]
TipologiaUso = Literal[
    "Sistema chiuso", "Inclusione in matrice", "Uso controllato", "Uso dispersivo"
]
TipologiaControllo = Literal[
    "Contenimento completo",
    "Aspirazione localizzata",
    "Segregazione / Separazione",
    "Ventilazione generale",
    "Manipolazione diretta",
]
TempoEsposizione = Literal[
    "< 15 minuti", "15 min - 2 ore", "2 - 4 ore", "4 - 6 ore", ">= 6 ore"
]
DistanzaClasse = Literal["< 1 m", "1 - 3 m", "3 - 5 m", "5 - 10 m", ">= 10 m"]
ContattoCutaneo = Literal[
    "Nessun contatto", "Contatto accidentale", "Contatto discontinuo", "Contatto esteso"
]


class RischioChimicoEsposizioneBase(BaseModel):
    persona_id: uuid.UUID | None = None
    sostanza_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None

    proprieta_fisiche: ProprietaFisiche | None = None
    quantita_classe: QuantitaClasse | None = None
    tipologia_uso: TipologiaUso | None = None
    tipologia_controllo: TipologiaControllo | None = None
    tempo_esposizione: TempoEsposizione | None = None
    distanza_classe: DistanzaClasse | None = None
    via_cutanea_applicabile: bool = False
    contatto_cutaneo: ContattoCutaneo | None = None

    note: str | None = Field(None, max_length=2000)


class RischioChimicoEsposizioneCreate(RischioChimicoEsposizioneBase):
    pass


class RischioChimicoEsposizioneUpdate(BaseModel):
    persona_id: uuid.UUID | None = None
    sostanza_id: uuid.UUID | None = None
    ambiente_id: uuid.UUID | None = None
    proprieta_fisiche: ProprietaFisiche | None = None
    quantita_classe: QuantitaClasse | None = None
    tipologia_uso: TipologiaUso | None = None
    tipologia_controllo: TipologiaControllo | None = None
    tempo_esposizione: TempoEsposizione | None = None
    distanza_classe: DistanzaClasse | None = None
    via_cutanea_applicabile: bool | None = None
    contatto_cutaneo: ContattoCutaneo | None = None
    human_reviewed: bool | None = None
    note: str | None = Field(None, max_length=2000)


class RischioChimicoEsposizioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    azienda_id: uuid.UUID
    persona_id: uuid.UUID | None
    sostanza_id: uuid.UUID | None
    ambiente_id: uuid.UUID | None

    proprieta_fisiche: str | None
    quantita_classe: str | None
    tipologia_uso: str | None
    tipologia_controllo: str | None
    tempo_esposizione: str | None
    distanza_classe: str | None
    via_cutanea_applicabile: bool
    contatto_cutaneo: str | None

    p_score: float | None
    governing_code: str | None
    is_cancerogeno: bool
    d_ind: int | None
    u_ind: int | None
    c_ind: int | None
    i_ind: int | None
    einal: float | None
    rinal: float | None
    ecute: int | None
    rcute: float | None
    rcum: float | None
    r_governing: float | None
    zona: str | None
    livello_salute: str | None
    livello_sicurezza: str | None

    ai_suggested: bool
    human_reviewed: bool
    note: str | None

    created_at: datetime
    updated_at: datetime


class RischioChimicoSuggestion(BaseModel):
    """AI-suggested exposure inputs for one (worker x substance), enums only,
    with a short Italian rationale + confidence. Reviewed before persistence."""

    proprieta_fisiche: ProprietaFisiche
    quantita_classe: QuantitaClasse
    tipologia_uso: TipologiaUso
    tipologia_controllo: TipologiaControllo
    tempo_esposizione: TempoEsposizione
    distanza_classe: DistanzaClasse
    via_cutanea_applicabile: bool
    contatto_cutaneo: ContattoCutaneo
    motivazione: str = Field(..., description="Breve motivazione in italiano")
    confidence: float = Field(..., ge=0, le=1)
