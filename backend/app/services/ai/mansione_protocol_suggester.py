"""AI-suggested DPI + rischi specifici per mansione (Phase 5.1 + 5.2).

Given a mansione (job role), the ambienti those workers operate in, and
the equipment they use, the model proposes:
  - which DPI codes are appropriate (from DPI_CATALOG)
  - which rischi specifici codes apply (from RISCHI_SPECIFICI_CATALOG)

Both are returned in one round-trip because the reasoning shares context
(a saldatore needs casco + visiera AND triggers cancerogeni_mutageni).

The operator reviews each suggestion and ticks which ones to keep.
Persistence is the existing PUT /aziende/{id}/mansioni-sorveglianza.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.services.ai.client import generate_structured
from app.services.reference_data import (
    DPI_CATALOG,
    RISCHI_SPECIFICI_CATALOG,
)

logger = logging.getLogger(__name__)


class MansioneProtocolSuggerito(BaseModel):
    """AI suggestions for a single mansione's protocol."""

    model_config = ConfigDict(extra="forbid")

    dpi_codes: list[str] = Field(
        description=(
            "Codici DPI dal catalogo (es. 'caschi_industria', "
            "'guanti_meccanici'). Solo codici esistenti nel catalogo, "
            "ordinati dal piu' rilevante. Includere DPI obbligatori e "
            "fortemente raccomandati per la mansione."
        )
    )
    rischi_specifici_codes: list[str] = Field(
        description=(
            "Codici rischi specifici dal catalogo (es. 'af_rumore', "
            "'mmc'). Solo codici esistenti, ordinati per rilevanza."
        )
    )
    motivazione: str = Field(
        description=(
            "Sintesi in 1-2 frasi italiano del perche' di queste scelte, "
            "specificando se ci sono attrezzature/ambienti che le hanno "
            "guidate (es. 'Saldatura ad arco implica visiera + "
            "cancerogeni')."
        )
    )


def _format_catalog_for_prompt(
    catalog: dict[str, dict[str, str]],
    group_key: str,
) -> str:
    """Render the catalog as 'group:\n  code — etichetta' for the prompt."""
    by_group: dict[str, list[tuple[str, str]]] = {}
    for code, meta in catalog.items():
        by_group.setdefault(meta[group_key], []).append((code, meta["etichetta"]))

    lines: list[str] = []
    for group in sorted(by_group):
        lines.append(f"{group}:")
        for code, label in by_group[group]:
            lines.append(f"  {code} — {label}")
    return "\n".join(lines)


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano (D.Lgs. 81/2008) specializzato in protocollo di sorveglianza
sanitaria del Medico del Lavoro.

Dato il profilo di una mansione (ambienti dove opera, attrezzature
utilizzate), suggerisci:
  1. I DPI codici dal catalogo che dovrebbero essere obbligatori o
     fortemente raccomandati;
  2. I rischi specifici codici dal catalogo a cui questa mansione e'
     esposta.

Regole vincolanti:
- Restituisci SOLO codici presenti nei cataloghi forniti — non inventare
  codici nuovi. Se un DPI/rischio non e' in catalogo, omettilo.
- Sii completo ma non esagerato: 3-12 DPI tipicamente, 2-8 rischi.
- Privilegia codici specifici rispetto a quelli generici (es. preferire
  'maschera_saldatura_arco' a 'schermo_facciale' per un saldatore).
- Se la mansione e' impiegatizia/ufficio, sii minimal (es.
  'occhiali_stanghette' per VDT, 'ergonomici' come rischio).

Formato output: SOLO JSON che rispetta lo schema dato."""


def _build_persona_context(
    mansione_nome: str,
    ambienti: list[Ambiente],
    attrezzature: list[Attrezzatura],
) -> str:
    """Compose the persona context. No PII (names, codice fiscale)."""
    lines: list[str] = []
    lines.append(f"Mansione: {mansione_nome}")
    if ambienti:
        lines.append("Ambienti dove la mansione opera:")
        for amb in ambienti:
            descr = (
                f"  - {amb.nome or '—'} (tipo: {amb.tipo or '—'}"
            )
            if amb.descrizione_attivita:
                descr += f", attivita': {amb.descrizione_attivita}"
            descr += ")"
            lines.append(descr)
    if attrezzature:
        lines.append("Attrezzature utilizzate (su questi ambienti):")
        for att in attrezzature:
            lines.append(f"  - {att.descrizione}")
    return "\n".join(lines)


async def suggest_mansione_protocol(
    mansione_nome: str,
    ambienti: list[Ambiente],
    attrezzature: list[Attrezzatura],
) -> MansioneProtocolSuggerito:
    """AI: propose DPI + rischi specifici codes for a mansione.

    Invalid codes (not in the catalog) are filtered out before returning,
    so the frontend never sees a non-existent code.
    """
    persona_context = _build_persona_context(
        mansione_nome, ambienti, attrezzature
    )
    dpi_catalog_text = _format_catalog_for_prompt(DPI_CATALOG, "area")
    rischi_catalog_text = _format_catalog_for_prompt(
        RISCHI_SPECIFICI_CATALOG, "macro"
    )

    prompt = (
        f"Profilo mansione:\n{persona_context}\n\n"
        f"Catalogo DPI disponibili (codice — etichetta):\n"
        f"{dpi_catalog_text}\n\n"
        f"Catalogo Rischi Specifici disponibili (codice — etichetta):\n"
        f"{rischi_catalog_text}\n\n"
        f"Suggerisci il protocollo per questa mansione."
    )

    logger.info(
        "Suggesting protocol for mansione %r (%d ambienti, %d attrezzature)",
        mansione_nome,
        len(ambienti),
        len(attrezzature),
    )
    response = await generate_structured(
        prompt=prompt,
        schema=MansioneProtocolSuggerito,
        system=SYSTEM_PROMPT,
    )

    # Phase 5.4 — schema-level validation: filter to known codes only.
    # The model is instructed to stay within catalog but enforce server-side
    # so the frontend only sees codes it can render.
    valid_dpi = {c for c in response.dpi_codes if c in DPI_CATALOG}
    valid_rischi = {
        c for c in response.rischi_specifici_codes if c in RISCHI_SPECIFICI_CATALOG
    }

    dropped_dpi = set(response.dpi_codes) - valid_dpi
    dropped_rischi = set(response.rischi_specifici_codes) - valid_rischi
    if dropped_dpi or dropped_rischi:
        logger.warning(
            "AI returned %d invalid DPI codes (%s) and %d invalid rischi (%s) — filtered",
            len(dropped_dpi),
            sorted(dropped_dpi),
            len(dropped_rischi),
            sorted(dropped_rischi),
        )

    return MansioneProtocolSuggerito(
        dpi_codes=[c for c in response.dpi_codes if c in valid_dpi],
        rischi_specifici_codes=[
            c for c in response.rischi_specifici_codes if c in valid_rischi
        ],
        motivazione=response.motivazione,
    )
