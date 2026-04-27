import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator

# B3 — fiscal-id format gates. P.IVA must be exactly 11 digits; ATECO must
# match the official "XX.XX" / "XX.XX.X" / "XX.XX.XX" shape (one or two
# trailing digits are both common in real visure). Empty / None passes the
# guard because both fields stay optional on the row.
_PARTITA_IVA_RE = re.compile(r"^\d{11}$")
_CODICE_ATECO_RE = re.compile(r"^\d{2}\.\d{2}(\.\d{1,2})?$")


def _validate_partita_iva(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = v.strip()
    if cleaned == "":
        return cleaned
    if not _PARTITA_IVA_RE.match(cleaned):
        raise ValueError("Partita IVA deve essere di 11 cifre")
    return cleaned


def _validate_codice_ateco(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = v.strip()
    if cleaned == "":
        return cleaned
    if not _CODICE_ATECO_RE.match(cleaned):
        raise ValueError("Codice ATECO non valido (formato XX.XX o XX.XX.XX)")
    return cleaned


class AziendaBase(BaseModel):
    ragione_sociale: str
    partita_iva: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    orario_lavoro: str | None = None
    metratura_totale: float | None = None
    zona_sismica: int | None = None
    descrizione_attivita: str | None = None
    contesto_territoriale: str | None = None
    data_scadenza_dvr: date | None = None


class AziendaCreate(AziendaBase):
    @field_validator("partita_iva")
    @classmethod
    def _check_partita_iva(cls, v: str | None) -> str | None:
        return _validate_partita_iva(v)

    @field_validator("codice_ateco")
    @classmethod
    def _check_codice_ateco(cls, v: str | None) -> str | None:
        return _validate_codice_ateco(v)


class AziendaUpdate(BaseModel):
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    orario_lavoro: str | None = None
    metratura_totale: float | None = None
    zona_sismica: int | None = None
    descrizione_attivita: str | None = None
    contesto_territoriale: str | None = None
    data_scadenza_dvr: date | None = None
    survey_status: str | None = None

    @field_validator("partita_iva")
    @classmethod
    def _check_partita_iva(cls, v: str | None) -> str | None:
        return _validate_partita_iva(v)

    @field_validator("codice_ateco")
    @classmethod
    def _check_codice_ateco(cls, v: str | None) -> str | None:
        return _validate_codice_ateco(v)


class AziendaResponse(AziendaBase):
    id: uuid.UUID
    survey_status: str
    # US-2.1 AC1 — non-null when a visura camerale PDF has been uploaded.
    # The path + extracted snippet stay server-side; the frontend uses the
    # timestamp purely as a "visura present" indicator above the
    # description editor.
    visura_uploaded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
