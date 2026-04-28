"""AI consolidator — merge raw VIES / Serper / Firecrawl into Azienda fields.

The model gets:
  - VIES result (deterministic — already parsed, included as ground truth)
  - Top 10 Serper organic snippets (titles + snippets + links)
  - Firecrawl markdown of the company homepage (truncated)

It returns a structured ``ConsolidatedAzienda`` whose fields map 1:1 to
``AziendaCreate``. The model is instructed to:
  - Leave a field None rather than guess
  - NEVER overwrite VIES values for ragione_sociale / sede legale
  - Never invent identity data (legal-rep names, codici fiscali of natural
    persons) — these stay outside the Azienda surface anyway

Privacy posture: the input is exclusively public-web text. The same
posture we already use for the visura snippet flow.
"""

from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, Field

from app.services.ai.client import generate_structured
from app.services.azienda_autofill.firecrawl import FirecrawlScrape
from app.services.azienda_autofill.serper import SerperResult
from app.services.azienda_autofill.snippet_extractor import ExtractedFacts
from app.services.azienda_autofill.vies import VIESResult

logger = logging.getLogger(__name__)


class ConsolidatedAzienda(BaseModel):
    """Fields the AI is allowed to fill from web data.

    Mirrors the AziendaCreate fields the autofill can plausibly derive.
    Everything is optional — the model is told to leave fields ``None``
    when not strongly supported by the inputs.
    """

    ragione_sociale: str | None = Field(
        default=None,
        description="Ragione sociale completa (es. 'ACME SRL'). Lascia None se non confermato.",
    )
    codice_fiscale: str | None = Field(
        default=None,
        description="Codice fiscale dell'azienda. Per società di capitali coincide spesso con la P.IVA.",
    )
    forma_giuridica: str | None = Field(
        default=None,
        description="Forma giuridica (es. SRL, SPA, SNC, SAS, Ditta Individuale).",
    )
    sede_legale_via: str | None = None
    sede_legale_citta: str | None = None
    cap_legale: str | None = None
    provincia_legale: str | None = Field(
        default=None,
        description="Sigla provincia, 2 lettere maiuscole (es. 'RM', 'MI').",
    )
    sede_operativa_via: str | None = None
    sede_operativa_citta: str | None = None
    cap_operativa: str | None = None
    provincia_operativa: str | None = None
    codice_ateco: str | None = Field(
        default=None,
        description="Codice ATECO formato 'XX.XX' o 'XX.XX.XX'.",
    )
    attivita: str | None = Field(
        default=None,
        description="Settore / oggetto sociale in 1-2 frasi (es. 'Commercio al dettaglio di articoli sportivi').",
    )
    pec: str | None = None
    email: str | None = None
    telefono: str | None = None
    sito_web: str | None = None
    numero_dipendenti_dichiarati: int | None = None
    capitale_sociale: float | None = None
    rea: str | None = None
    data_costituzione: date | None = None


SYSTEM_PROMPT = """Sei un assistente esperto di registri imprese italiani.
Devi estrarre i dati dell'azienda dalle fonti web fornite (VIES + fatti deterministici dal Registro Imprese + risultati Google + sito aziendale).

Regole di priorità:
1. I dati VIES e i FATTI DETERMINISTICI sono autoritativi. NON sovrascriverli, NON contraddirli.
2. Quando uno snippet di Google contiene una formulazione esplicita "Campo: valore" (esempi: "Codice Ateco: 62.01", "REA: BR-180454", "Capitale Sociale: € 10.000", "PEC: x@pec.it"), DEVI restituire quel valore. Non lasciarlo a null per cautela.
3. Per i campi descrittivi (attivita) puoi sintetizzare tu, basandoti sui dati di settore/oggetto sociale presenti negli snippet o nel sito aziendale.
4. Se un dato NON è presente in nessuna fonte, lascia il campo a null. Mai inventare.

Regole di formato:
- forma_giuridica: una delle sigle ufficiali: SRL, SRLS, SPA, SAPA, SNC, SAS, SCARL, SCRL, "Ditta Individuale", "Società Semplice", "Cooperativa", "Consorzio".
- codice_ateco: formato XX.XX o XX.XX.XX. Solo cifre e punti.
- provincia_legale / provincia_operativa: sigle di 2 lettere maiuscole (RM, MI, NA, ...).
- cap_legale / cap_operativa: codici postali italiani di 5 cifre.
- numero_dipendenti_dichiarati: intero positivo (>= 1). Se la fonte dice 'circa 50' usa 50. Mai dedurre, mai stimare.
- capitale_sociale: valore numerico in euro (50000.0 non '50.000 €'). Mai inferire da fatturato o stipendi.
- data_costituzione: formato YYYY-MM-DD. L'anno DEVE essere >= 1900, altrimenti lascia null.
- attivita: 1-2 frasi in italiano del settore / oggetto sociale, NON una pubblicità.
- pec / email: minuscolo.
- sito_web: URL completo con https://.

Privacy:
- NON includere dati personali (nomi, codici fiscali di persone fisiche, indirizzi privati di soci o amministratori).
"""


def _format_vies(vies: VIESResult | None) -> str:
    if vies is None or not vies.is_valid:
        return "VIES: nessun dato (P.IVA non valida o servizio non disponibile)"
    parts = ["VIES (autoritativo, NON sovrascrivere):"]
    if vies.ragione_sociale:
        parts.append(f"- ragione_sociale: {vies.ragione_sociale}")
    if vies.sede_legale_via:
        parts.append(f"- sede_legale_via: {vies.sede_legale_via}")
    if vies.sede_legale_citta:
        parts.append(f"- sede_legale_citta: {vies.sede_legale_citta}")
    if vies.cap_legale:
        parts.append(f"- cap_legale: {vies.cap_legale}")
    if vies.provincia_legale:
        parts.append(f"- provincia_legale: {vies.provincia_legale}")
    if vies.raw_address and not (vies.sede_legale_via and vies.cap_legale):
        parts.append(f"- indirizzo grezzo: {vies.raw_address}")
    return "\n".join(parts)


def _format_facts(facts: ExtractedFacts) -> str:
    """Render the deterministic snippet-extracted facts as a fixed block.

    These come from registry-formatted "Field: value" matches (regex,
    not AI), so they're treated as ground truth on equal footing with
    VIES. Listing them explicitly here prevents the consolidator from
    "playing it safe" and dropping values that are right there in the
    snippets.
    """
    parts: list[str] = ["Fatti deterministici dal Registro Imprese (autoritativo, NON sovrascrivere):"]
    if facts.codice_ateco:
        parts.append(f"- codice_ateco: {facts.codice_ateco}")
    if facts.rea:
        parts.append(f"- rea: {facts.rea}")
    if facts.pec:
        parts.append(f"- pec: {facts.pec}")
    if facts.codice_fiscale:
        parts.append(f"- codice_fiscale: {facts.codice_fiscale}")
    if facts.capitale_sociale is not None:
        parts.append(f"- capitale_sociale: {facts.capitale_sociale}")
    if facts.forma_giuridica:
        parts.append(f"- forma_giuridica: {facts.forma_giuridica}")
    if facts.sito_web:
        parts.append(f"- sito_web: {facts.sito_web}")
    if facts.telefono:
        parts.append(f"- telefono: {facts.telefono}")
    if len(parts) == 1:
        parts.append("(nessun fatto deterministico estratto)")
    return "\n".join(parts)


def _format_serper(results: list[SerperResult]) -> str:
    if not results:
        return "Risultati Google: nessuno."
    lines = ["Risultati Google (snippet — possono contenere ATECO, REA, PEC, capitale, sito):"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.title}")
        if r.snippet:
            lines.append(f"   {r.snippet}")
        if r.link:
            lines.append(f"   ({r.link})")
    return "\n".join(lines)


def _format_firecrawl(scrape: FirecrawlScrape | None) -> str:
    if scrape is None:
        return "Sito aziendale: non scansionato (URL non disponibile o scrape fallito)."
    return (
        f"Sito aziendale ({scrape.url}) — markdown:\n"
        f"--- inizio markdown ---\n{scrape.markdown}\n--- fine markdown ---"
    )


async def consolidate(
    *,
    partita_iva: str,
    vies: VIESResult | None,
    facts: ExtractedFacts,
    serper_results: list[SerperResult],
    firecrawl_scrape: FirecrawlScrape | None,
) -> ConsolidatedAzienda:
    """Run the AI consolidator over the four raw sources.

    Uses ``OPENAI_MODEL_MEASURES`` (gpt-5.4-mini) with low reasoning effort
    — this is structured-extraction, not deep reasoning. Total prompt is
    typically 1-10 KB depending on Firecrawl payload.
    """
    prompt = "\n\n".join(
        [
            f"Partita IVA: {partita_iva}",
            _format_vies(vies),
            _format_facts(facts),
            _format_serper(serper_results),
            _format_firecrawl(firecrawl_scrape),
            "Estrai i dati dell'azienda secondo lo schema. Per ogni 'Campo: valore' esplicito negli snippet, RIPORTA il valore. Lascia null solo i campi davvero non supportati.",
        ]
    )
    logger.info(
        "Consolidating autofill for %s (vies=%s, facts_keys=%d, serper=%d, firecrawl=%s)",
        partita_iva,
        bool(vies and vies.is_valid),
        sum(1 for f in (facts.codice_ateco, facts.rea, facts.pec, facts.codice_fiscale, facts.capitale_sociale, facts.forma_giuridica, facts.sito_web, facts.telefono) if f),
        len(serper_results),
        bool(firecrawl_scrape),
    )
    return await generate_structured(
        prompt=prompt,
        schema=ConsolidatedAzienda,
        system=SYSTEM_PROMPT,
        reasoning_effort="low",
    )
