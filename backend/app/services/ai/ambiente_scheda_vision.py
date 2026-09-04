"""Vision-based scheda ambiente from the ambiente photos.

Segnalazioni 2026-08-25 (incendio + PEE): for every ambiente the allegati
need a description of the room with the materials present and the
possible ignition sources. Luca asked for these to be recognised from the
photos already uploaded in step-ambienti. The model proposes the three
texts; the operator reads them next to the photos and saves what is
right. The maximum number of people is never proposed — it is a fact the
operator knows and a photo does not.

Privacy contract (CLAUDE.md): photos may incidentally contain people; the
prompt tells the model to ignore them and describe only the room, the
materials and the equipment. No PII is sent.

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


class SchedaAmbienteEstratta(BaseModel):
    """The three scheda texts the photos can support."""

    model_config = ConfigDict(extra="forbid")

    descrizione_locale: str = Field(
        description=(
            "Descrizione dell'ambiente in italiano, 1-3 frasi: tipo di "
            "locale, struttura (pareti, soffitto, pavimento), aperture, "
            "layout e destinazione d'uso visibile. Niente persone."
        )
    )
    materiali_presenti: str = Field(
        description=(
            "Materiali presenti rilevanti per il rischio incendio, elenco "
            "separato da punto e virgola (es. 'Scaffalature metalliche; "
            "imballaggi in cartone; bancali in legno; taniche di solvente'). "
            "Solo cio' che e' visibile nelle foto."
        )
    )
    sorgenti_innesco: str = Field(
        description=(
            "Possibili sorgenti di innesco visibili o deducibili dalle foto, "
            "elenco separato da punto e virgola (es. 'Quadro elettrico; "
            "prese multiple sotto carico; forno; lavorazioni a caldo'). "
            "Stringa vuota se non se ne vedono."
        )
    )
    motivazione: str = Field(
        description=(
            "In 1-2 frasi, cosa hai visto nelle foto a supporto di quanto "
            "scritto, cosi' l'operatore sa dove guardare per verificare."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano specializzato in prevenzione incendi (D.M. 03/09/2021) e piani
di emergenza (D.M. 02/09/2021).

Il tuo compito: guardare le foto di un ambiente di lavoro e compilare la
scheda dell'ambiente per l'allegato rischio incendio e per il piano di
emergenza: descrizione del locale, materiali presenti, possibili sorgenti
di innesco.

Regole:
- Descrivi SOLO cio' che e' visibile o chiaramente deducibile dalle foto.
  Non inventare materiali o impianti che non si vedono.
- Italiano tecnico e sobrio, come in una scheda di valutazione.
- MAI descrivere persone, volti, abbigliamento, oggetti personali.
- Per i materiali concentrati su cio' che pesa nel carico d'incendio:
  carta, cartone, legno, plastica, tessuti, liquidi infiammabili, bombole,
  imballaggi, arredi.
- Per le sorgenti di innesco: impianti e apparecchi elettrici, apparecchi
  a fiamma o a caldo, lavorazioni a caldo, superfici calde, fumo,
  cariche elettrostatiche.
- Se le foto non permettono di dire nulla su un campo, lascia una stringa
  vuota invece di riempirla con frasi generiche.
- NON stimare il numero massimo di persone: e' un dato dell'operatore."""


def _build_instructions(ambiente: Ambiente, azienda: Azienda) -> str:
    """Assemble the per-call user instructions. No PII."""
    lines: list[str] = ["Compila la scheda di questo ambiente a partire dalle foto."]
    lines.append("")
    lines.append("Contesto:")
    lines.append(f"- Ambiente: {ambiente.nome or '—'}")
    lines.append(f"- Tipo: {ambiente.tipo or '—'}")
    if ambiente.superficie_mq is not None:
        lines.append(f"- Superficie dichiarata: {ambiente.superficie_mq} mq")
    if ambiente.descrizione_attivita:
        lines.append(f"- Attivita' svolta: {ambiente.descrizione_attivita}")
    lines.append(f"- Azienda: {azienda.ragione_sociale}")
    if azienda.attivita:
        lines.append(f"- Attivita' aziendale: {azienda.attivita}")
    if azienda.codice_ateco:
        lines.append(f"- Codice ATECO: {azienda.codice_ateco}")
    return "\n".join(lines)


async def extract_scheda_from_photos(
    ambiente: Ambiente,
    azienda: Azienda,
    photo_paths: list[str | Path],
) -> SchedaAmbienteEstratta:
    """Propose descrizione, materiali and sorgenti di innesco from photos.

    Uses OPENAI_MODEL_EXTRACTION (gpt-5.5) — vision-capable. The result is
    a proposal: the endpoint never persists it, the operator saves the
    scheda through the ordinary ambiente update.
    """
    if not photo_paths:
        raise ValueError("At least one photo is required")

    logger.info(
        "Vision-extracting scheda for ambiente %s (tipo=%s) of azienda %s "
        "from %d photo(s)",
        ambiente.id,
        ambiente.tipo,
        azienda.id,
        len(photo_paths),
    )
    return await extract_from_images(
        photo_paths,
        schema=SchedaAmbienteEstratta,
        instructions=_build_instructions(ambiente, azienda),
        system=SYSTEM_PROMPT,
    )
