"""AI-suggested improvement measures for risk assessments (US-2.6).

Given a risk evaluation (categoria, pericolo, condizioni, P/D scores),
produces 2-5 concrete Italian misure di prevenzione/protezione with
priority and suggested implementation timeframe.

Note: `from __future__ import annotations` is deliberately NOT used here —
with it, Pydantic can't resolve Literal type aliases (Priorita, TipoMisura)
without per-class model_rebuild() calls.
"""

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.valutazione_rischio import ValutazioneRischio
from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)


Priorita = Literal["bassa", "media", "alta", "urgente"]
TipoMisura = Literal["tecnica", "organizzativa", "dpi", "formazione", "sorveglianza_sanitaria"]


class MisuraSuggerita(BaseModel):
    """One AI-suggested improvement measure."""

    model_config = ConfigDict(extra="forbid")

    titolo: str = Field(description="Sintesi della misura, max 80 caratteri.")
    descrizione: str = Field(
        description=(
            "Descrizione operativa della misura in italiano, 1-3 frasi. "
            "Deve essere concreta e attuabile, non generica."
        )
    )
    tipo: TipoMisura = Field(
        description=(
            "Categoria della misura: tecnica (impianti/attrezzature), "
            "organizzativa (procedure/turni), dpi (dispositivi protezione individuale), "
            "formazione (corsi/addestramento), sorveglianza_sanitaria (visite mediche)."
        )
    )
    priorita: Priorita = Field(
        description=(
            "Coerente con l'indice di rischio: accettabile->bassa, modesto->media, "
            "grave->alta, gravissimo->urgente."
        )
    )
    tempistica: str = Field(
        description=(
            "Tempistica di implementazione suggerita in italiano, es. "
            "'immediata', 'entro 30 giorni', 'entro 6 mesi'."
        )
    )
    riferimento_normativo: str | None = Field(
        description=(
            "Articolo del D.Lgs. 81/2008 o norma tecnica pertinente, se applicabile. "
            "None se non c'e' un riferimento specifico."
        )
    )


class MisureSuggerite(BaseModel):
    """AI response: 2-5 suggested measures for a single risk."""

    model_config = ConfigDict(extra="forbid")

    misure: list[MisuraSuggerita] = Field(
        description="Da 2 a 5 misure di prevenzione ordinate per priorita' decrescente."
    )




SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro italiano
specializzato in D.Lgs. 81/2008.

Dato un rischio lavorativo identificato, suggerisci da 2 a 5 misure di
prevenzione/protezione concrete, attuabili e coerenti con la gerarchia
prevista dall'art. 15 del D.Lgs. 81/2008:
  1. Eliminazione del rischio alla fonte
  2. Sostituzione di cio' che e' pericoloso
  3. Misure tecniche collettive
  4. Misure organizzative
  5. Dispositivi di protezione individuale (DPI)
  6. Formazione e informazione

Regole:
- Italiano tecnico-consulenziale, senza fronzoli.
- Misure CONCRETE (es. "installare aspirazione localizzata sul banco di
  saldatura") non generiche (es. "ridurre l'esposizione").
- Ordina per priorita' decrescente.
- Cita l'articolo del D.Lgs. 81/2008 quando pertinente (es. "art. 71" per
  attrezzature, "art. 77" per DPI, "art. 36-37" per formazione)."""


def _build_risk_context(rischio: ValutazioneRischio) -> str:
    """Summarise the risk for the LLM. No personal data."""
    lines: list[str] = [f"Categoria di rischio: {rischio.categoria_rischio}"]
    if rischio.pericolo:
        lines.append(f"Pericolo identificato: {rischio.pericolo}")
    if rischio.condizioni_esposizione:
        lines.append(f"Condizioni di esposizione: {rischio.condizioni_esposizione}")
    if rischio.rischio:
        lines.append(f"Rischio: {rischio.rischio}")
    if rischio.probabilita_p is not None and rischio.danno_d is not None:
        lines.append(
            f"Probabilita' P={rischio.probabilita_p}/4, "
            f"Danno D={rischio.danno_d}/4, "
            f"Indice I={rischio.indice_i} ({rischio.livello_rischio})"
        )
    if rischio.misure_prevenzione:
        lines.append(
            f"Misure gia' presenti (NON suggerire duplicati): {rischio.misure_prevenzione}"
        )
    return "\n".join(lines)


async def suggest_measures(rischio: ValutazioneRischio) -> list[MisuraSuggerita]:
    """Generate 2-5 improvement measures for a single risk.

    Uses OPENAI_MODEL_MEASURES (default gpt-5-mini) -- needs domain reasoning.
    Raises AIError on API failure.
    """
    context = _build_risk_context(rischio)
    logger.info(
        "Suggesting measures for risk %s (cat=%s, level=%s)",
        rischio.id,
        rischio.categoria_rischio,
        rischio.livello_rischio,
    )
    response = await generate_structured(
        prompt=f"Valutazione del rischio:\n{context}\n\nSuggerisci le misure di miglioramento.",
        schema=MisureSuggerite,
        system=SYSTEM_PROMPT,
    )
    return response.misure
