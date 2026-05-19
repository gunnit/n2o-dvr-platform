import uuid

from pydantic import BaseModel, Field


class PersonaBase(BaseModel):
    nominativo: str
    codice_fiscale: str | None = None
    mansione: str | None = None
    tipologia_contrattuale: str | None = None
    sesso: str | None = None
    fascia_eta: str | None = ">18"
    ruolo_rspp: bool = False
    ruolo_rls: bool = False
    ruolo_primo_soccorso: bool = False
    ruolo_antincendio: bool = False
    ruolo_preposto: bool = False
    ruolo_datore_lavoro: bool = False
    ruolo_medico_competente: bool = False
    # External consultant flag (feedback #10, 2026-04-29). Surfaced in the
    # DVR §1.3 organigramma as an "(esterno)" suffix; only meaningful when
    # `ruolo_rspp` or `ruolo_medico_competente` is set.
    is_esterno: bool = False
    # Free-text note alongside the structured attrezzature_speciali flags.
    # Originally "qualifiche" (US-1.4), repurposed as a note 2026-04-28.
    qualifiche: str | None = None
    attrezzature_speciali: list[str] = Field(default_factory=list)
    # Per-persona DPI + rischi specifici (feedback 2026-04-29). Replaces
    # the previous mansioni_sorveglianza per-mansione grouping.
    dpi_codes: list[str] = Field(default_factory=list)
    rischi_specifici_codes: list[str] = Field(default_factory=list)
    dpi_rischi_note: str | None = None
    # Feedback #3 (2026-05-19): training-aggiornata flag. Bool only — no
    # date / expiry until the client asks for it.
    training_recente_completato: bool = False


class PersonaCreate(PersonaBase):
    # US-1.4: ambienti assegnati multi-select written through persone_ambienti.
    ambiente_ids: list[uuid.UUID] = Field(default_factory=list)


class PersonaUpdate(BaseModel):
    nominativo: str | None = None
    codice_fiscale: str | None = None
    mansione: str | None = None
    tipologia_contrattuale: str | None = None
    sesso: str | None = None
    fascia_eta: str | None = None
    ruolo_rspp: bool | None = None
    ruolo_rls: bool | None = None
    ruolo_primo_soccorso: bool | None = None
    ruolo_antincendio: bool | None = None
    ruolo_preposto: bool | None = None
    ruolo_datore_lavoro: bool | None = None
    ruolo_medico_competente: bool | None = None
    is_esterno: bool | None = None
    qualifiche: str | None = None
    attrezzature_speciali: list[str] | None = None
    dpi_codes: list[str] | None = None
    rischi_specifici_codes: list[str] | None = None
    dpi_rischi_note: str | None = None
    training_recente_completato: bool | None = None
    # When present the M2M is rewritten; when absent it is left untouched.
    ambiente_ids: list[uuid.UUID] | None = None


class PersonaResponse(PersonaBase):
    id: uuid.UUID
    azienda_id: uuid.UUID
    # US-1.4: ambienti assegnati exposed as a flat list of IDs.
    ambiente_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}
