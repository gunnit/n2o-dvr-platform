"""Pydantic schemas for AI-driven SDS (Safety Data Sheet) extraction.

These are the *intermediate* shapes returned by the OpenAI Responses API.
They are mapped onto SostanzaChimica before persistence — see
`app.services.ai.sds_extractor.to_db_dict`.

Per-field confidence drives the yellow-warning UI in US-1.9: any field
below CONFIDENCE_WARNING_THRESHOLD is flagged for human review.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# CLP/GHS hazard pictograms (Reg. CE 1272/2008). Codes match the
# frontend Step 6 enum (PITTOGRAMMI_GHS in step-sostanze.tsx).
GHSCode = Literal[
    "GHS01",  # Esplosivo
    "GHS02",  # Infiammabile
    "GHS03",  # Comburente
    "GHS04",  # Gas compresso
    "GHS05",  # Corrosivo
    "GHS06",  # Tossicita acuta
    "GHS07",  # Irritante
    "GHS08",  # Pericolo per la salute
    "GHS09",  # Pericolo per l'ambiente
]

StatoMiscela = Literal["solido", "liquido", "gassoso", "aerosol", "polvere", "pasta", "altro"]


class SDSExtraction(BaseModel):
    """One SDS PDF -> structured chemical data.

    Strict mode (responses.parse + text_format) requires every field to be
    present; nullable fields use `T | None`. `extra='forbid'` ensures the
    model can't return unknown fields.
    """

    model_config = ConfigDict(extra="forbid")

    # Identification
    nome_prodotto: str | None = Field(
        description="Commercial product name from Section 1.1 of the SDS."
    )
    nome_prodotto_confidence: float = Field(
        ge=0.0, le=1.0, description="0-1 confidence in nome_prodotto."
    )

    produttore: str | None = Field(
        description="Manufacturer/supplier company name from Section 1.3."
    )
    produttore_confidence: float = Field(ge=0.0, le=1.0)

    # Intended use — Section 1.2 of the SDS ("Pertinenti usi identificati")
    destinazione_uso: str | None = Field(
        description=(
            "Manufacturer-declared identified use from Section 1.2 of the SDS "
            "('Pertinenti usi identificati della sostanza o miscela'). One "
            "concise Italian phrase, e.g. 'Detergente professionale per "
            "superfici dure', 'Lubrificante per macchine utensili'. None if "
            "the section is missing or unreadable."
        )
    )
    destinazione_uso_confidence: float = Field(ge=0.0, le=1.0)

    # Physical state — Section 9 of the SDS
    stato_miscela: StatoMiscela | None = Field(
        description="Physical state of the substance/mixture at room temp."
    )
    stato_miscela_confidence: float = Field(ge=0.0, le=1.0)

    # Hazard classification — Section 2 of the SDS
    pittogrammi: list[GHSCode] = Field(
        description=(
            "GHS hazard pictograms present on the label. "
            "Empty list if the substance is not classified as hazardous."
        )
    )
    pittogrammi_confidence: float = Field(ge=0.0, le=1.0)

    frasi_h: list[str] = Field(
        description=(
            "H-statement codes (CLP). Format: 'H' + 3 digits, e.g. 'H225', 'H319'. "
            "Combined codes like 'H315+H320' are kept as-is. Empty list if none."
        )
    )
    frasi_h_confidence: float = Field(ge=0.0, le=1.0)

    frasi_p: list[str] = Field(
        description=(
            "P-statement codes (precautionary). Format: 'P' + 3 digits, e.g. 'P210', 'P305+P351+P338'. "
            "Empty list if none."
        )
    )
    frasi_p_confidence: float = Field(ge=0.0, le=1.0)

    # Quality flags
    extraction_notes: str | None = Field(
        description=(
            "Brief Italian note for the human reviewer if the SDS is unusual: "
            "scanned/poor quality, language other than Italian/English, missing sections, "
            "ambiguous classification, etc. None if extraction was straightforward."
        )
    )

    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Aggregate confidence for the whole extraction. "
            ">=0.8 = high, 0.5-0.8 = medium, <0.5 = low (recommend manual entry)."
        ),
    )


# UI threshold: fields below this trigger the yellow warning icon (US-1.9).
CONFIDENCE_WARNING_THRESHOLD = 0.7

# Below this, the extraction is considered failed and the UI offers
# "Inserisci manualmente" instead of the auto-populated row (US-1.9).
CONFIDENCE_FAILURE_THRESHOLD = 0.3
