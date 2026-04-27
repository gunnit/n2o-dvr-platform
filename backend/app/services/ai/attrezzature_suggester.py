"""AI-suggested attrezzature for an ambiente (Phase 5.3).

Given an environment (tipo + descrizione_attivita) and the company's
macrosector, the model proposes 3-8 typical pieces of equipment / impianti /
macchine that a safety consultant would expect to find. The operator then
ticks the ones that match reality and they get persisted as Attrezzatura
rows tied to the ambiente.

Privacy contract (CLAUDE.md): no PII (codice fiscale, ID docs, health
data) is sent. Equipment names are not personal data.

Note: NO `from __future__ import annotations` — Pydantic + Literal aliases
fail to resolve without per-class model_rebuild() calls if it's enabled.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)


class AttrezzaturaSuggerita(BaseModel):
    """One AI-suggested piece of equipment."""

    model_config = ConfigDict(extra="forbid")

    descrizione: str = Field(
        description=(
            "Nome dell'attrezzatura/macchina/impianto in italiano. Conciso "
            "(max 60 caratteri), come comparirebbe in una scheda "
            "manutenzione (es. 'Tornio parallelo', 'Cappa aspirante', "
            "'Carrello elevatore'). Niente DPI."
        )
    )
    motivazione: str = Field(
        description=(
            "Perche' questa attrezzatura e' tipica per questo ambiente, "
            "1 frase breve in italiano."
        )
    )


class AttrezzatureSuggerite(BaseModel):
    """Wrapper for the structured-output response."""

    model_config = ConfigDict(extra="forbid")

    items: list[AttrezzaturaSuggerita] = Field(
        description=(
            "Da 3 a 8 attrezzature tipiche per l'ambiente, ordinate per "
            "tipicita' decrescente. Solo attrezzature/macchine/impianti, "
            "MAI DPI (caschi, guanti, scarpe, occhiali...)."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano specializzato in D.Lgs. 81/2008 e censimento attrezzature
aziendali.

Dato un ambiente di lavoro (tipo, attivita', settore aziendale), elenca
da 3 a 8 attrezzature/macchine/impianti TIPICI che un consulente si
aspetterebbe di trovare in quel contesto, in ordine di tipicita'
decrescente.

Regole:
- Italiano tecnico, nomi concreti come comparirebbero in un inventario
  (es. "Tornio parallelo", "Affettatrice", "Carrello elevatore",
  "Cappa aspirante", "Compressore d'aria").
- MAI suggerire DPI (caschi, guanti, scarpe antinfortunistiche,
  occhiali, mascherine): quelli sono in una sezione separata.
- MAI suggerire arredo generico (sedie, tavoli) a meno che non sia
  funzionale (es. "Sedia ergonomica" e' OK per un Ufficio).
- Se l'utente ha gia' dichiarato alcune attrezzature, NON ripeterle.
- Una motivazione breve per ogni voce (1 frase)."""


def _build_context(
    ambiente: Ambiente,
    azienda: Azienda,
    existing_descriptions: list[str] | None,
) -> str:
    """Assemble the prompt context. No PII."""
    lines: list[str] = []
    lines.append(f"Ambiente: {ambiente.nome or '—'}")
    lines.append(f"Tipo: {ambiente.tipo or '—'}")
    if ambiente.descrizione_attivita:
        lines.append(f"Attivita' specifica: {ambiente.descrizione_attivita}")
    if ambiente.superficie_mq:
        lines.append(f"Superficie: {ambiente.superficie_mq} m2")
    lines.append("")
    lines.append(f"Azienda: {azienda.ragione_sociale}")
    if azienda.attivita:
        lines.append(f"Attivita' aziendale: {azienda.attivita}")
    if azienda.codice_ateco:
        lines.append(f"Codice ATECO: {azienda.codice_ateco}")
    if azienda.descrizione_attivita:
        lines.append(f"Descrizione attivita': {azienda.descrizione_attivita}")
    if existing_descriptions:
        lines.append("")
        lines.append(
            "Attrezzature gia' dichiarate (NON ripetere queste):"
        )
        for d in sorted(set(existing_descriptions)):
            lines.append(f"  - {d}")
    return "\n".join(lines)


async def suggest_attrezzature(
    ambiente: Ambiente,
    azienda: Azienda,
    existing_descriptions: list[str] | None = None,
) -> list[AttrezzaturaSuggerita]:
    """Generate 3-8 typical pieces of equipment for an ambiente.

    Uses OPENAI_MODEL_MEASURES (gpt-5-mini) — needs domain reasoning. The
    operator reviews each suggestion and ticks which to add as actual
    Attrezzatura rows (tied to ambiente_id, see Phase 2.3).
    """
    context = _build_context(ambiente, azienda, existing_descriptions)
    logger.info(
        "Suggesting attrezzature for ambiente %s (tipo=%s) of azienda %s",
        ambiente.id,
        ambiente.tipo,
        azienda.id,
    )
    response = await generate_structured(
        prompt=(
            f"Contesto:\n{context}\n\n"
            "Suggerisci le attrezzature tipiche per questo ambiente."
        ),
        schema=AttrezzatureSuggerite,
        system=SYSTEM_PROMPT,
    )
    return response.items
