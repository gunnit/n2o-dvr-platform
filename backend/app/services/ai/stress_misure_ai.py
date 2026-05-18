"""AI-suggested corrective measures for INAIL stress assessment.

Given an INAIL stress lavoro-correlato assessment (answers + computed
result), produces 3-6 concrete Italian misure correttive tailored to the
livello (BASSO/MEDIO/ALTO) and the sub-areas that scored highest.

Uses the Responses API via `generate_text` (plain Italian text — no
schema enforcement). Default model: OPENAI_MODEL_MEASURES (gpt-5.4-mini).

Privacy contract (CLAUDE.md):
  - Only aggregated stress scores + indicator text are sent.
  - No codice fiscale, ID document, or personal health data.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services.ai.client import generate_text
from app.services.stress_calculator import (
    INDICATOR_BY_ID,
    StressCalculationResult,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Sei un consulente italiano esperto di salute e sicurezza sul lavoro, "
    "specializzato nella valutazione dello stress lavoro-correlato secondo "
    "la metodologia INAIL (Indicatori Oggettivi, D.Lgs. 81/2008 art. 28). "
    "Rispondi sempre in italiano, con misure concrete, attuabili e coerenti "
    "con il livello di rischio."
)


def _top_indicators_per_area(
    answers: dict[str, str],
    calc: StressCalculationResult,
    *,
    limit_per_area: int = 5,
) -> dict[str, list[str]]:
    """Return the indicators that contributed most to the score, per area.

    For each macro-area (A / B / C) returns a list of up to `limit_per_area`
    indicator descriptions (Italian text) whose answer produced a non-zero
    score — i.e. the items "responsible" for the stress level.
    """
    contributing: dict[str, list[tuple[str, int]]] = {"A": [], "B": [], "C": []}

    for ind_id, raw in answers.items():
        ind = INDICATOR_BY_ID.get(ind_id)
        if not ind or not raw:
            continue
        # Recompute the indicator's score to identify positive contributors.
        mode = ind["scoring"]
        score = 0
        if mode == "tripartite":
            score = {"DIMINUITO": 0, "INALTERATO": 1, "AUMENTATO": 4}.get(raw, 0)
        elif mode == "binary_heavy":
            score = {"NO": 0, "SI": 4}.get(raw, 0)
        elif mode == "binary":
            score = {"SI": 0, "NO": 1}.get(raw, 0)
        elif mode == "binary_inverted":
            score = {"SI": 1, "NO": 0}.get(raw, 0)

        if score <= 0:
            continue

        macro = ind["area"][0]  # "A", "B", or "C"
        contributing[macro].append((ind["text"], score))

    out: dict[str, list[str]] = {}
    for macro, items in contributing.items():
        # Sort by descending contribution then take the top N.
        items.sort(key=lambda t: t[1], reverse=True)
        out[macro] = [text for text, _ in items[:limit_per_area]]
    return out


def _build_prompt(
    answers: dict[str, str],
    calc: StressCalculationResult,
) -> str:
    top = _top_indicators_per_area(answers, calc)

    def _bulletize(items: list[str]) -> str:
        if not items:
            return "  (nessun indicatore critico in questa area)"
        return "\n".join(f"  - {t}" for t in items)

    livello = calc["livello"]
    return (
        "Genera fra 3 e 6 misure correttive concrete per ridurre lo stress "
        "lavoro-correlato in azienda, sulla base della valutazione INAIL "
        "qui sotto.\n\n"
        f"Livello complessivo: {livello}\n"
        f"Punteggio totale: {calc['totale']}\n"
        f"  - Area A (eventi sentinella):  punteggio {calc['area_a_converted']} "
        f"(raw {calc['area_a_raw']}) — livello {calc['area_a_livello']}\n"
        f"  - Area B (contesto del lavoro): totale {calc['area_b_total']} — "
        f"livello {calc['area_b_livello']}\n"
        f"  - Area C (contenuto del lavoro): totale {calc['area_c_total']} — "
        f"livello {calc['area_c_livello']}\n\n"
        "Indicatori che hanno contribuito di piu' al punteggio:\n"
        "Area A (eventi sentinella aziendali):\n"
        f"{_bulletize(top['A'])}\n"
        "Area B (contesto organizzativo):\n"
        f"{_bulletize(top['B'])}\n"
        "Area C (contenuto del lavoro):\n"
        f"{_bulletize(top['C'])}\n\n"
        "Requisiti dell'output:\n"
        "- Tra 3 e 6 misure, una per riga, senza numerazione.\n"
        "- Ogni riga inizia con un verbo all'infinito (es. 'Istituire', "
        "'Rivedere', 'Formare').\n"
        "- Misure concrete e attuabili, coerenti con il livello "
        f"{livello} e con le aree critiche elencate sopra.\n"
        "- Italiano formale, max ~30 parole per riga.\n"
        "- Nessuna intestazione, nessun titolo, nessun bullet character, "
        "nessuna chiusura — solo le misure, una per riga.\n"
    )


async def suggest_stress_misure(
    answers: dict[str, str],
    calc: StressCalculationResult,
) -> str:
    """Return an Italian newline-separated list of corrective measures.

    The caller is responsible for stripping any private fields from
    `answers` before invoking this helper. `calc` is the StressCalculationResult
    produced by `calculate_stress(answers)`.

    The result is intended as a SUGGESTION — the operator must review and
    accept it before persisting into `misure_correttive`.
    """
    prompt = _build_prompt(answers, calc)
    text = await generate_text(
        prompt,
        system=SYSTEM_PROMPT,
        # OPENAI_MODEL_MEASURES (gpt-5.4-mini) — domain reasoning rather
        # than boilerplate, but "low" effort is plenty for a 3-6 item list.
        model=settings.OPENAI_MODEL_MEASURES,
        reasoning_effort="low",
        max_output_tokens=900,
    )
    return text.strip()
