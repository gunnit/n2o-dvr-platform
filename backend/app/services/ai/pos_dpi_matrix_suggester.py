"""AI-suggested POS DPI matrix (mansione/ruolo x lavorazione/fase).

Feedback #64/#50 — instead of filling the role x phase DPI matrix cell by
cell, the operator clicks "Compila con AI" and the model proposes, for each
(ruolo, fase) pairing, which DPI codes are required. The operator then
reviews; the frontend only writes the AI suggestion into still-empty cells
and never overwrites an operator's choice.

Mirrors ``pos_phase_suggester.py`` (Pydantic structured output, Italian
domain prompt, light reasoning effort) and reuses the catalog-validation
pattern from ``dpi_rischi_suggester.py``: the model may only return DPI
codes that exist in ``DPI_CATALOG`` — anything else is dropped before the
result leaves this module.

Uses gpt-5.4-mini (OPENAI_MODEL_MEASURES) — construction-safety domain
reasoning, no heavy chain-of-thought needed.

Privacy: only work-related signals reach the model — role labels, phase
labels, DPI catalog, and (optionally) the azienda's ATECO / activity
description. No persone, names, codici fiscali or health data are sent.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.client import generate_structured

# Same DPI_CATALOG the POS matrix rules engine uses (services/dpi_rules.py),
# NOT the larger reference_data catalog — the cells store these codes.
from app.services.dpi_rules import DPI_CATALOG

logger = logging.getLogger(__name__)


class DpiMatrixCellSuggestion(BaseModel):
    """AI-suggested DPI for a single (ruolo, fase) cell."""

    model_config = ConfigDict(extra="forbid")

    ruolo: str = Field(
        description=(
            "Codice/chiave del ruolo esattamente come fornito nell'elenco "
            "ruoli in input (NON tradurre, NON inventare)."
        )
    )
    fase: str = Field(
        description=(
            "Codice/chiave della fase/lavorazione esattamente come fornito "
            "nell'elenco fasi in input (NON tradurre, NON inventare)."
        )
    )
    dpi_codes: list[str] = Field(
        description=(
            "Codici DPI dal catalogo (es. 'casco', 'scarpe', "
            "'imbragatura') obbligatori per questo ruolo durante questa "
            "fase. Solo codici presenti nel catalogo fornito. Lista vuota "
            "se questo ruolo non e' coinvolto nella fase."
        )
    )


class DpiMatrixAiSuggestion(BaseModel):
    """Full AI suggestion: one entry per (ruolo, fase) pairing."""

    model_config = ConfigDict(extra="forbid")

    celle: list[DpiMatrixCellSuggestion] = Field(
        description=(
            "Una voce per ogni combinazione (ruolo, fase) per cui si "
            "suggeriscono DPI. Combinazioni non pertinenti possono essere "
            "omesse o avere dpi_codes vuoto."
        )
    )


SYSTEM_PROMPT = (
    "Sei un esperto di sicurezza sul lavoro nei cantieri edili in Italia. "
    "Conosci approfonditamente il D.Lgs. 81/2008, il Titolo III (DPI) e il "
    "Titolo IV (cantieri temporanei o mobili) e le relative norme tecniche "
    "UNI/EN. Per ogni combinazione ruolo-fase indichi i DPI obbligatori che "
    "quel ruolo deve indossare durante quella lavorazione.\n\n"
    "Regole vincolanti:\n"
    "- Restituisci SOLO codici DPI presenti nel catalogo fornito — non "
    "inventare codici nuovi. Se un DPI non e' in catalogo, omettilo.\n"
    "- Usa i codici ruolo e fase ESATTAMENTE come forniti in input.\n"
    "- Sii conservativo verso la sicurezza: includi casco, scarpe "
    "antinfortunistiche e alta visibilita' come base su un cantiere "
    "attivo, e aggiungi i DPI specifici della lavorazione (imbragatura "
    "per lavori in quota, otoprotettori per fasi rumorose, guanti/occhiali "
    "per lavorazioni manuali, ecc.).\n"
    "- Se un ruolo non e' realisticamente coinvolto in una fase, lascia "
    "dpi_codes vuoto.\n"
    "Rispondi in italiano tecnico-professionale e solo nel formato JSON "
    "richiesto."
)


def _format_dpi_catalog(catalog: dict[str, str]) -> str:
    """Render the DPI catalog as 'codice — etichetta' lines for the prompt."""
    return "\n".join(f"  {code} — {label}" for code, label in catalog.items())


def _build_prompt(
    *,
    ruoli: list[str],
    fasi: list[str],
    azienda_context: str | None,
) -> str:
    ruoli_text = "\n".join(f"  - {r}" for r in ruoli)
    fasi_text = "\n".join(f"  - {f}" for f in fasi)
    dpi_text = _format_dpi_catalog(DPI_CATALOG)

    context_block = ""
    if azienda_context:
        context_block = (
            f"Contesto azienda (settore/attivita'):\n{azienda_context}\n\n"
        )

    return (
        f"{context_block}"
        f"Ruoli in cantiere (usa questi codici esatti):\n{ruoli_text}\n\n"
        f"Fasi / lavorazioni (usa questi codici esatti):\n{fasi_text}\n\n"
        f"Catalogo DPI disponibili (codice — etichetta):\n{dpi_text}\n\n"
        f"Per OGNI combinazione (ruolo, fase) suggerisci i codici DPI "
        f"obbligatori. Basati sulle prescrizioni del D.Lgs. 81/2008 "
        f"(Titoli III e IV) e sulle buone pratiche dei cantieri edili "
        f"italiani."
    )


async def suggest_dpi_matrix(
    *,
    ruoli: list[str],
    fasi: list[str],
    azienda_context: str | None = None,
) -> dict[str, dict[str, list[str]]]:
    """AI: propose DPI codes for every (ruolo, fase) cell of the POS matrix.

    Args:
        ruoli: role keys exactly as they appear in ``dpi_matrix_roles``
            (catalog keys or operator-added slugs).
        fasi: phase keys exactly as they appear in ``dpi_matrix_phases``.
        azienda_context: optional non-PII context (ATECO, activity
            description) to ground the suggestion. May be ``None``.

    Returns:
        A ``{fase: {ruolo: [dpi_codes]}}`` map (same shape as
        ``Pos.dpi_matrix``). Only known role/phase keys and DPI codes
        present in ``DPI_CATALOG`` survive; everything else is dropped so
        the frontend never receives an unknown code.
    """
    if not ruoli or not fasi:
        return {}

    ruoli_set = set(ruoli)
    fasi_set = set(fasi)

    prompt = _build_prompt(
        ruoli=ruoli, fasi=fasi, azienda_context=azienda_context
    )

    logger.info(
        "Suggesting POS DPI matrix (%d ruoli x %d fasi, context=%s)",
        len(ruoli),
        len(fasi),
        bool(azienda_context),
    )
    response = await generate_structured(
        prompt=prompt,
        schema=DpiMatrixAiSuggestion,
        system=SYSTEM_PROMPT,
        reasoning_effort="low",
    )

    matrix: dict[str, dict[str, list[str]]] = {}
    dropped_codes: set[str] = set()
    dropped_keys = 0

    for cell in response.celle:
        ruolo = cell.ruolo
        fase = cell.fase
        # Drop cells whose role/phase keys the AI invented or mangled.
        if ruolo not in ruoli_set or fase not in fasi_set:
            dropped_keys += 1
            continue
        valid = [c for c in cell.dpi_codes if c in DPI_CATALOG]
        dropped_codes.update(c for c in cell.dpi_codes if c not in DPI_CATALOG)
        if not valid:
            continue
        # Preserve catalog order; de-duplicate.
        ordered = [c for c in DPI_CATALOG if c in set(valid)]
        matrix.setdefault(fase, {})[ruolo] = ordered

    if dropped_codes or dropped_keys:
        logger.warning(
            "POS DPI matrix AI: dropped %d unknown DPI codes (%s) and "
            "%d cells with unknown role/phase keys",
            len(dropped_codes),
            sorted(dropped_codes),
            dropped_keys,
        )

    return matrix
