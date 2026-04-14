"""AI-generated company description for DVR Part I (US-2.1).

Produces 200-400 word Italian boilerplate describing a company's activity,
sector, premises and personnel, derived from survey data only. NO personal
identifiers are sent to the AI (CLAUDE.md privacy contract).
"""

from __future__ import annotations

import logging

from app.models.azienda import Azienda
from app.services.ai.client import generate_text

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro italiano.
Scrivi la sezione "Descrizione dell'attivita'" della Parte I di un Documento
di Valutazione dei Rischi (DVR) ai sensi del D.Lgs. 81/2008.

Regole:
- Italiano formale e tecnico, stile consulenziale neutro.
- Lunghezza 200-400 parole.
- Include: settore produttivo, descrizione dell'attivita', layout produttivo
  (ambienti principali), organico e mansioni principali, eventuali rischi
  caratteristici del settore.
- NON inventare dati non presenti nei dati forniti. Se un dato manca, ometti
  quella frase invece di inventare.
- NON citare nomi di persone o dati personali.
- Restituisci SOLO il testo della descrizione, senza intestazioni o titoli."""


def _build_context(azienda: Azienda) -> str:
    """Build the user prompt with safe, anonymised company data."""
    lines: list[str] = []
    lines.append(f"Azienda: {azienda.ragione_sociale}")
    if azienda.codice_ateco:
        lines.append(f"Codice ATECO: {azienda.codice_ateco}")
    if azienda.attivita:
        lines.append(f"Attivita' dichiarata: {azienda.attivita}")
    if azienda.sede_operativa_citta:
        lines.append(f"Sede operativa: {azienda.sede_operativa_citta}")
    if azienda.metratura_totale:
        lines.append(f"Metratura totale: {azienda.metratura_totale} mq")
    if azienda.orario_lavoro:
        lines.append(f"Orario di lavoro: {azienda.orario_lavoro}")
    if azienda.zona_sismica:
        lines.append(f"Zona sismica: {azienda.zona_sismica}")

    # Ambienti (if loaded) — names and types, no location specifics
    ambienti = getattr(azienda, "ambienti", None) or []
    if ambienti:
        tipi = sorted({a.tipo for a in ambienti if getattr(a, "tipo", None)})
        lines.append(f"Ambienti di lavoro ({len(ambienti)}): {', '.join(tipi) or 'non specificato'}")

    # Personnel — only roles/counts, NEVER names or codice fiscale
    persone = getattr(azienda, "persone", None) or []
    if persone:
        mansioni: dict[str, int] = {}
        for p in persone:
            m = getattr(p, "mansione", None) or "non specificato"
            mansioni[m] = mansioni.get(m, 0) + 1
        mansioni_str = ", ".join(f"{n} {m}" for m, n in sorted(mansioni.items()))
        lines.append(f"Organico ({len(persone)} lavoratori): {mansioni_str}")

    return "\n".join(lines)


async def generate_company_description(azienda: Azienda) -> str:
    """Generate the Italian DVR Part I company description.

    Uses OPENAI_MODEL_GENERATION (default gpt-5-nano) — cheap boilerplate.
    Caller is responsible for persisting the result (typically to
    Azienda.descrizione_attivita) and for handling AIError.
    """
    context = _build_context(azienda)
    logger.info(
        "Generating company description for %s (%d bytes context)",
        azienda.ragione_sociale,
        len(context),
    )
    text = await generate_text(
        prompt=f"Dati dell'azienda:\n{context}\n\nScrivi la descrizione dell'attivita'.",
        system=SYSTEM_PROMPT,
        max_output_tokens=800,
    )
    return text.strip()
