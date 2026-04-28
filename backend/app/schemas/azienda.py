import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator

# B3 — fiscal-id format gates. P.IVA must be exactly 11 digits; ATECO must
# match the official "XX.XX" / "XX.XX.X" / "XX.XX.XX" shape (one or two
# trailing digits are both common in real visure). Empty / None passes the
# guard because both fields stay optional on the row.
_PARTITA_IVA_RE = re.compile(r"^\d{11}$")
_CODICE_ATECO_RE = re.compile(r"^\d{2}\.\d{2}(\.\d{1,2})?$")
_CAP_RE = re.compile(r"^\d{5}$")
_PROVINCIA_RE = re.compile(r"^[A-Z]{2}$")
# Codice fiscale: 16 alphanumeric (PF) or 11 digits (PG, often == P.IVA).
_CODICE_FISCALE_RE = re.compile(r"^([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]|\d{11})$")


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


def _validate_cap(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = v.strip()
    if cleaned == "":
        return cleaned
    if not _CAP_RE.match(cleaned):
        raise ValueError("CAP deve essere di 5 cifre")
    return cleaned


def _validate_provincia(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = v.strip().upper()
    if cleaned == "":
        return cleaned
    if not _PROVINCIA_RE.match(cleaned):
        raise ValueError("Provincia deve essere la sigla di 2 lettere (es. RM)")
    return cleaned


def _validate_codice_fiscale(v: str | None) -> str | None:
    if v is None:
        return v
    cleaned = v.strip().upper()
    if cleaned == "":
        return cleaned
    if not _CODICE_FISCALE_RE.match(cleaned):
        raise ValueError("Codice fiscale non valido")
    return cleaned


class AziendaBase(BaseModel):
    ragione_sociale: str
    partita_iva: str | None = None
    codice_fiscale: str | None = None
    forma_giuridica: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    cap_legale: str | None = None
    provincia_legale: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    cap_operativa: str | None = None
    provincia_operativa: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    pec: str | None = None
    email: str | None = None
    telefono: str | None = None
    sito_web: str | None = None
    numero_dipendenti_dichiarati: int | None = None
    data_costituzione: date | None = None
    capitale_sociale: float | None = None
    rea: str | None = None
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

    @field_validator("cap_legale", "cap_operativa")
    @classmethod
    def _check_cap(cls, v: str | None) -> str | None:
        return _validate_cap(v)

    @field_validator("provincia_legale", "provincia_operativa")
    @classmethod
    def _check_provincia(cls, v: str | None) -> str | None:
        return _validate_provincia(v)

    @field_validator("codice_fiscale")
    @classmethod
    def _check_codice_fiscale(cls, v: str | None) -> str | None:
        return _validate_codice_fiscale(v)


class AziendaUpdate(BaseModel):
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    codice_fiscale: str | None = None
    forma_giuridica: str | None = None
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    cap_legale: str | None = None
    provincia_legale: str | None = None
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    cap_operativa: str | None = None
    provincia_operativa: str | None = None
    attivita: str | None = None
    codice_ateco: str | None = None
    pec: str | None = None
    email: str | None = None
    telefono: str | None = None
    sito_web: str | None = None
    numero_dipendenti_dichiarati: int | None = None
    data_costituzione: date | None = None
    capitale_sociale: float | None = None
    rea: str | None = None
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

    @field_validator("cap_legale", "cap_operativa")
    @classmethod
    def _check_cap(cls, v: str | None) -> str | None:
        return _validate_cap(v)

    @field_validator("provincia_legale", "provincia_operativa")
    @classmethod
    def _check_provincia(cls, v: str | None) -> str | None:
        return _validate_provincia(v)

    @field_validator("codice_fiscale")
    @classmethod
    def _check_codice_fiscale(cls, v: str | None) -> str | None:
        return _validate_codice_fiscale(v)


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


# ----------------------------------------------------------------------------
# Autofill — POST /aziende/autofill
# ----------------------------------------------------------------------------

Confidence = Literal["high", "medium", "low"]


class AziendaAutofillFieldMeta(BaseModel):
    """Per-field provenance for the autofill response.

    The frontend renders a ✨ badge per filled field and uses this to label
    the source ("Suggerito da VIES", "Google + AI · verifica") so the
    operator knows which fields are deterministic vs best-effort.
    """

    confidence: Confidence
    source: str
    source_url: str | None = None


class AziendaAutofillResponse(BaseModel):
    """Response of POST /aziende/autofill.

    ``values`` is shaped like an ``AziendaCreate`` payload (subset — only
    the fields the pipeline could derive for this P.IVA). ``meta`` carries
    provenance keyed by the same field names. ``warnings`` surfaces any
    source that failed so the UI can say "VIES non disponibile".
    """

    partita_iva: str
    values: dict[str, str | int | float | None]
    meta: dict[str, AziendaAutofillFieldMeta]
    warnings: list[str] = []
