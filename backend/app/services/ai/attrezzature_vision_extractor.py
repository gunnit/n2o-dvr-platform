"""Vision-based attrezzatura extraction from ambiente photos.

Given the photos uploaded to an ambiente (step-ambienti), the model
identifies attrezzature/macchine/impianti visible in the images. The
operator reviews each suggestion and ticks which to add as actual
Attrezzatura rows tied to the ambiente.

Privacy contract (CLAUDE.md): photos may incidentally contain people in
the background, but the prompt instructs the model to ignore them and
only describe equipment. No PII fields (codice fiscale, ID docs, health
data) are sent — equipment names are not personal data.

Note: NO `from __future__ import annotations` — Pydantic + Literal aliases
fail to resolve without per-class model_rebuild() calls if it's enabled.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.models.ambiente import Ambiente
from app.models.azienda import Azienda
from app.services.ai.client import extract_from_images

logger = logging.getLogger(__name__)


class AttrezzaturaIdentificata(BaseModel):
    """One piece of equipment identified in the photos."""

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
            "Cosa hai visto nella foto che ti ha permesso di identificare "
            "questa attrezzatura, 1 frase breve in italiano (es. 'Visibile "
            "sullo sfondo della prima foto, con pannello di controllo "
            "frontale')."
        )
    )


class AttrezzatureIdentificate(BaseModel):
    """Wrapper for the structured-output response."""

    model_config = ConfigDict(extra="forbid")

    items: list[AttrezzaturaIdentificata] = Field(
        description=(
            "Tutte le attrezzature/macchine/impianti chiaramente visibili "
            "nelle foto, ordinate per evidenza decrescente. Solo "
            "attrezzature/macchine/impianti, MAI DPI (caschi, guanti, "
            "scarpe, occhiali). MAI persone."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano specializzato in D.Lgs. 81/2008 e censimento attrezzature
aziendali tramite analisi visiva.

Il tuo compito: guardare le foto di un ambiente di lavoro e identificare
le attrezzature/macchine/impianti chiaramente visibili.

Regole:
- Italiano tecnico, nomi concreti come comparirebbero in un inventario
  (es. "Tornio parallelo", "Affettatrice", "Carrello elevatore",
  "Cappa aspirante", "Compressore d'aria", "Scaffalatura industriale").
- MAI elencare DPI (caschi, guanti, scarpe antinfortunistiche, occhiali,
  mascherine): quelli sono in una sezione separata.
- MAI elencare persone, parti del corpo, vestiti, oggetti personali.
- MAI elencare arredo generico (sedie, tavoli) a meno che non sia
  funzionale per la lavorazione (es. "Banco da lavoro" e' OK).
- Se vedi un'attrezzatura ma non sei sicuro del tipo, descrivi cio' che
  vedi in modo generico (es. "Macchinario industriale non identificato")
  invece di inventare un nome specifico.
- Se non vedi attrezzature significative, restituisci una lista vuota.
- Se l'utente ha gia' dichiarato alcune attrezzature in questo ambiente,
  NON ripeterle.
- Una motivazione breve per ogni voce che indichi cosa hai visto."""


def _build_instructions(
    ambiente: Ambiente,
    azienda: Azienda,
    existing_descriptions: list[str] | None,
) -> str:
    """Assemble the per-call user instructions. No PII."""
    lines: list[str] = []
    lines.append(
        "Identifica le attrezzature/macchine/impianti visibili in queste foto."
    )
    lines.append("")
    lines.append("Contesto:")
    lines.append(f"- Ambiente: {ambiente.nome or '—'}")
    lines.append(f"- Tipo: {ambiente.tipo or '—'}")
    if ambiente.descrizione_attivita:
        lines.append(f"- Attivita' specifica: {ambiente.descrizione_attivita}")
    lines.append(f"- Azienda: {azienda.ragione_sociale}")
    if azienda.attivita:
        lines.append(f"- Attivita' aziendale: {azienda.attivita}")
    if azienda.codice_ateco:
        lines.append(f"- Codice ATECO: {azienda.codice_ateco}")
    if existing_descriptions:
        lines.append("")
        lines.append("Attrezzature gia' dichiarate (NON ripetere queste):")
        for d in sorted(set(existing_descriptions)):
            lines.append(f"  - {d}")
    return "\n".join(lines)


async def extract_attrezzature_from_photos(
    ambiente: Ambiente,
    azienda: Azienda,
    photo_paths: list[str | Path],
    existing_descriptions: list[str] | None = None,
) -> list[AttrezzaturaIdentificata]:
    """Identify attrezzature visible in the ambiente's photos.

    Uses OPENAI_MODEL_EXTRACTION (gpt-5.5) — vision-capable, accuracy
    matters more than latency here. The operator reviews each suggestion
    and ticks which to add as actual Attrezzatura rows.
    """
    if not photo_paths:
        return []

    instructions = _build_instructions(ambiente, azienda, existing_descriptions)
    logger.info(
        "Vision-extracting attrezzature for ambiente %s (tipo=%s) of azienda %s "
        "from %d photo(s)",
        ambiente.id,
        ambiente.tipo,
        azienda.id,
        len(photo_paths),
    )
    response = await extract_from_images(
        photo_paths,
        schema=AttrezzatureIdentificate,
        instructions=instructions,
        system=SYSTEM_PROMPT,
    )
    return response.items
