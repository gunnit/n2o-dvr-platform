"""AI-suggested DPI + rischi specifici per persona.

Given a single worker (mansione + attrezzature speciali + ambienti they
operate in + attrezzature in those ambienti), the model proposes:
  - which DPI codes are appropriate (from DPI_CATALOG)
  - which rischi specifici codes apply (from RISCHI_SPECIFICI_CATALOG)

The unit was changed from mansione to persona on 2026-04-30 (feedback
Luca Marchetti, 2026-04-29). Two saldatori in the same azienda may have
genuinely different exposures depending on which ambienti they cover and
which attrezzature speciali they're certified for.

Both lists are returned in one round-trip because the reasoning shares
context (a saldatore needs casco + visiera AND triggers cancerogeni). The
operator reviews each suggestion and ticks which to keep.

PII contract: name, codice fiscale, data di nascita are NOT sent. Only
the work-related signals (mansione, attrezzature speciali, ambienti,
attrezzature) reach the model.
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


# Human-readable labels for the structured attrezzature_speciali codes
# the operator ticks on the persona. Mirrors the labels in the wizard
# step + DVR generator's attrezzatura_to_rischio map.
ATTREZZATURE_SPECIALI_LABELS: dict[str, str] = {
    "lavori_in_quota": "Lavori in quota",
    "trabattelli": "Utilizzo di trabattelli",
    "ponteggi": "Utilizzo di ponteggi",
    "carrello_elevatore": "Utilizzo di carrelli elevatori",
    "ple": "Utilizzo di piattaforme di lavoro elevabili (PLE)",
    "gru": "Utilizzo di gru",
    "ruspa_escavatore": "Utilizzo di ruspe / escavatori",
    "patente_cde": "Guida professionale (patente C/D/E)",
    "adr": "Trasporto merci pericolose (ADR)",
}


class DpiRischiSuggerito(BaseModel):
    """AI suggestions for a single persona's DPI + rischi specifici."""

    model_config = ConfigDict(extra="forbid")

    dpi_codes: list[str] = Field(
        description=(
            "Codici DPI dal catalogo (es. 'caschi_industria', "
            "'guanti_meccanici'). Solo codici esistenti nel catalogo, "
            "ordinati dal piu' rilevante. Includere DPI obbligatori e "
            "fortemente raccomandati per la persona."
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
            "specificando se attrezzature speciali / ambienti / "
            "attrezzature le hanno guidate (es. 'PLE + trabattelli "
            "implica imbragatura + lavori in quota')."
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

Dato il profilo di un singolo lavoratore (mansione, attrezzature speciali
per cui e' qualificato, ambienti in cui opera, attrezzature presenti in
quegli ambienti), suggerisci:
  1. I codici DPI dal catalogo che dovrebbero essere obbligatori o
     fortemente raccomandati per QUESTA persona;
  2. I codici rischi specifici dal catalogo a cui QUESTA persona e'
     esposta.

Il profilo e' per UN lavoratore specifico, non per una mansione astratta:
due saldatori possono avere protocolli diversi se uno guida anche un PLE
e l'altro no.

Regole vincolanti:
- Restituisci SOLO codici presenti nei cataloghi forniti — non inventare
  codici nuovi. Se un DPI/rischio non e' in catalogo, omettilo.
- Sii completo ma non esagerato: 3-12 DPI tipicamente, 2-8 rischi.
- Privilegia codici specifici rispetto a generici (es. preferire
  'maschera_saldatura_arco' a 'schermo_facciale' per un saldatore).
- Le attrezzature speciali ticcate sulla persona sono segnali FORTI:
  PLE / trabattelli / ponteggi / lavori_in_quota -> imbragatura +
  caduta_dall_alto; carrello_elevatore / gru -> casco + segnaletica +
  carico_sospeso; patente_cde / adr -> rischio stradale + ergonomia +
  stress.
- Se la mansione e' impiegatizia / ufficio e non ci sono attrezzature
  speciali, sii minimal (es. 'occhiali_stanghette' per VDT, 'ergonomici'
  come rischio).

Formato output: SOLO JSON che rispetta lo schema dato."""


def _build_persona_context(
    mansione_nome: str | None,
    attrezzature_speciali_codes: list[str],
    ambienti: list[Ambiente],
    attrezzature: list[Attrezzatura],
) -> str:
    """Compose the persona context. No PII (names, codice fiscale)."""
    lines: list[str] = []
    lines.append(f"Mansione: {mansione_nome or 'non specificata'}")

    if attrezzature_speciali_codes:
        lines.append("Attrezzature speciali / qualifiche per cui e' abilitato:")
        for code in attrezzature_speciali_codes:
            label = ATTREZZATURE_SPECIALI_LABELS.get(code, code)
            lines.append(f"  - {label}")

    if ambienti:
        lines.append("Ambienti dove la persona opera:")
        for amb in ambienti:
            descr = (
                f"  - {amb.nome or '—'} (tipo: {amb.tipo or '—'}"
            )
            if amb.descrizione_attivita:
                descr += f", attivita': {amb.descrizione_attivita}"
            descr += ")"
            lines.append(descr)
    if attrezzature:
        lines.append("Attrezzature presenti negli ambienti:")
        for att in attrezzature:
            lines.append(f"  - {att.descrizione}")
    return "\n".join(lines)


async def suggest_dpi_rischi(
    *,
    mansione_nome: str | None,
    attrezzature_speciali_codes: list[str],
    ambienti: list[Ambiente],
    attrezzature: list[Attrezzatura],
) -> DpiRischiSuggerito:
    """AI: propose DPI + rischi specifici codes for a single persona.

    Invalid codes (not in the catalog) are filtered out before returning,
    so the frontend never sees a non-existent code.
    """
    persona_context = _build_persona_context(
        mansione_nome,
        attrezzature_speciali_codes,
        ambienti,
        attrezzature,
    )
    dpi_catalog_text = _format_catalog_for_prompt(DPI_CATALOG, "area")
    rischi_catalog_text = _format_catalog_for_prompt(
        RISCHI_SPECIFICI_CATALOG, "macro"
    )

    prompt = (
        f"Profilo lavoratore:\n{persona_context}\n\n"
        f"Catalogo DPI disponibili (codice — etichetta):\n"
        f"{dpi_catalog_text}\n\n"
        f"Catalogo Rischi Specifici disponibili (codice — etichetta):\n"
        f"{rischi_catalog_text}\n\n"
        f"Suggerisci DPI e rischi specifici per questa persona."
    )

    logger.info(
        "Suggesting DPI/rischi for persona (mansione=%r, %d attrezzature speciali, %d ambienti, %d attrezzature)",
        mansione_nome,
        len(attrezzature_speciali_codes),
        len(ambienti),
        len(attrezzature),
    )
    response = await generate_structured(
        prompt=prompt,
        schema=DpiRischiSuggerito,
        system=SYSTEM_PROMPT,
    )

    # Schema-level validation: filter to known codes only.
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

    return DpiRischiSuggerito(
        dpi_codes=[c for c in response.dpi_codes if c in valid_dpi],
        rischi_specifici_codes=[
            c for c in response.rischi_specifici_codes if c in valid_rischi
        ],
        motivazione=response.motivazione,
    )
