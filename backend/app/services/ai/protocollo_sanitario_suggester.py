"""AI-proposed protocollo sanitario for one mansione (segnalazione 2026-08-25).

Given a mansione, the union of its rischi specifici + DPI (aggregated from
the persone holding that role), the azienda's activity and the subset of
the occupational-disease reference table that matches those risks, the
model proposes:

  * the accertamenti sanitari with a cadence coherent with art. 41 D.Lgs.
    81/2008 and the specific risk (audiometria for rumore, spirometria for
    polveri, ...);
  * the overall periodicita' of the visita periodica;
  * which reference diseases are correlated — chosen ONLY from the rows in
    the prompt, by ``codice``, so the citation is always one we can back.

The proposal is never persisted here; the operator applies, edits or
discards it in the UI and PUT /protocollo-sanitario/mansioni saves it.

Privacy contract (CLAUDE.md): the prompt carries the mansione name, risk and
DPI codes with their catalogue labels, the azienda's activity/ATECO and the
reference table. It never carries a person's name, codice fiscale, sex, age
or any individual health fact — the aggregation in
``app.services.protocollo_sanitario`` only exposes role-level codes and a
head count, and this module reads nothing else from the persone.

Note: no ``from __future__ import annotations`` — the Literal alias below
must stay resolvable by Pydantic without model_rebuild().
"""

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.data.malattie_professionali import MalattiaProfessionale, get_malattia
from app.services.ai.client import generate_structured
from app.services.protocollo_sanitario import dpi_label, rischio_label

logger = logging.getLogger(__name__)

Periodicita = Literal["semestrale", "annuale", "biennale", "triennale", "quinquennale"]


class AccertamentoSuggerito(BaseModel):
    """One health check the MC should include in the protocol."""

    model_config = ConfigDict(extra="forbid")

    esame: str = Field(
        description=(
            "Nome dell'accertamento sanitario, in italiano, max 120 caratteri. "
            "Esempi: 'Visita medica generale', 'Audiometria', 'Spirometria', "
            "'Esame della funzione visiva', 'Esami ematochimici di base', "
            "'Valutazione del rachide'. Il primo elemento e' SEMPRE la visita "
            "medica (preventiva e periodica)."
        )
    )
    periodicita: str = Field(
        description=(
            "Cadenza dell'accertamento, max 60 caratteri. Usare il lessico: "
            "'preventiva', 'annuale', 'biennale', 'triennale', 'quinquennale', "
            "'semestrale', 'preventiva e annuale', 'alla cessazione'. "
            "Coerente con l'art. 41 D.Lgs. 81/2008 e con la norma specifica "
            "del rischio (es. VDT art. 176: quinquennale, biennale sopra i 50 "
            "anni o con prescrizioni)."
        )
    )
    motivazione: str = Field(
        description=(
            "1 frase italiana: quale rischio della mansione giustifica "
            "l'accertamento e con quale riferimento normativo."
        )
    )


class MalattiaScelta(BaseModel):
    """A disease picked from the reference rows given in the prompt."""

    model_config = ConfigDict(extra="forbid")

    codice: str = Field(
        description=(
            "Codice della malattia COPIATO ESATTAMENTE da uno dei codici "
            "elencati nella tabella di riferimento del prompt. Codici non "
            "presenti nella tabella vengono scartati."
        )
    )
    motivazione: str = Field(
        description=(
            "1 frase italiana: quale rischio specifico della mansione espone "
            "a questa malattia."
        )
    )


class ProtocolloSuggerito(BaseModel):
    """AI response: full protocol proposal for one mansione."""

    model_config = ConfigDict(extra="forbid")

    accertamenti: list[AccertamentoSuggerito] = Field(
        description=(
            "Da 2 a 8 accertamenti, il primo e' sempre la visita medica "
            "(preventiva e periodica). Includere solo accertamenti "
            "giustificati dai rischi elencati, niente esami di routine non "
            "motivati."
        )
    )
    periodicita: Periodicita = Field(
        description=(
            "Cadenza complessiva della visita periodica per la mansione. "
            "'annuale' e' il default di legge (art. 41 c. 2 lett. b); "
            "'quinquennale' per sole esposizioni VDT; 'semestrale' solo per "
            "esposizioni a cancerogeni/mutageni o casi previsti da norma "
            "specifica."
        )
    )
    malattie_correlate: list[MalattiaScelta] = Field(
        description=(
            "Malattie professionali correlate ai rischi della mansione, "
            "scelte SOLO tra i codici della tabella di riferimento fornita. "
            "Lista vuota se nessuna voce e' pertinente."
        )
    )
    motivazione: str = Field(
        description=(
            "Sintesi 2-3 frasi del ragionamento complessivo (rischi "
            "prevalenti, norma applicabile, eventuali punti che il Medico "
            "Competente deve confermare)."
        )
    )


SYSTEM_PROMPT = """Sei un Medico Competente esperto di medicina del lavoro
italiana (D.Lgs. 81/2008, art. 25 e art. 41) e proponi il protocollo di
sorveglianza sanitaria per UNA mansione aziendale.

Ricevi: la mansione, i rischi specifici e i DPI assegnati a quella mansione
(aggregati da tutte le persone che la svolgono), l'attivita' dell'azienda e
una tabella di riferimento di malattie professionali (D.M. 9 aprile 2008 e
Lista D.M. 10 giugno 2014) gia' filtrata sui rischi della mansione.

Devi proporre:
  1. accertamenti — visita medica (sempre per prima) piu' gli esami
     mirati giustificati da ciascun rischio, ognuno con la sua cadenza:
       - rumore: audiometria (preventiva, poi annuale o biennale in base
         al livello di esposizione, art. 196);
       - vibrazioni: valutazione vascolare/neurologica arti superiori o
         rachide (art. 204);
       - MMC / posture: valutazione del rachide e dell'apparato
         muscolo-scheletrico (art. 168);
       - VDT: esame della funzione visiva, valutazione apparato
         muscolo-scheletrico (art. 176: quinquennale, biennale >50 anni);
       - agenti chimici / polveri: spirometria, esami ematochimici mirati,
         visita dermatologica se sensibilizzanti (art. 229);
       - cancerogeni / amianto / silice: spirometria, Rx torace o esami
         mirati secondo protocollo, registro esposti (art. 242, 259);
       - biologici: controllo stato vaccinale (HBV, tetano), esami
         sierologici mirati (art. 279);
       - microclima: valutazione cardiovascolare;
       - lavori in quota / conduzione mezzi: valutazione dell'idoneita'
         psicofisica, screening alcol e sostanze ove previsto
         (Provvedimento 16/03/2006, Intesa 30/10/2007).
  2. periodicita' — cadenza complessiva della visita periodica.
  3. malattie_correlate — SOLO codici presenti nella tabella fornita.
  4. motivazione — sintesi del ragionamento.

Regole vincolanti:
- Non inventare rischi non elencati; se la mansione ha pochi rischi, il
  protocollo e' breve. Un impiegato con solo VDT ha visita + funzione
  visiva + rachide, periodicita' quinquennale.
- I codici delle malattie vanno copiati esattamente dalla tabella.
- Le cadenze devono essere coerenti con la norma citata: non proporre
  cadenze piu' brevi di quelle di legge senza un rischio che lo motivi.
- Il protocollo e' per la MANSIONE, non per una persona: nessun
  riferimento a individui.
- Scrivi in italiano, tono tecnico e sobrio.

Formato output: SOLO JSON che rispetta lo schema dato."""


def format_reference_rows(rows: list[MalattiaProfessionale]) -> str:
    if not rows:
        return "(nessuna voce della tabella corrisponde ai rischi elencati)"
    lines: list[str] = []
    for r in rows:
        stato = "tabellata" if r["tabellata"] else "NON tabellata"
        lines.append(
            f"- codice={r['codice']} | {r['malattia']} | agente: "
            f"{r['agente_o_rischio']} | {r['tabella']} ({stato})"
        )
    return "\n".join(lines)


def build_prompt(
    *,
    mansione: str,
    rischi_codes: list[str],
    dpi_codes: list[str],
    azienda: object,
    malattie_riferimento: list[MalattiaProfessionale],
) -> str:
    """Compose the user prompt. Pure — tested for the absence of PII.

    ``azienda`` is read for ragione_sociale / attivita / codice_ateco /
    descrizione_attivita only.
    """
    lines: list[str] = []
    lines.append(f"Mansione: {mansione}")
    lines.append("")
    if rischi_codes:
        lines.append("Rischi specifici della mansione (D.Lgs. 81/2008):")
        for c in rischi_codes:
            lines.append(f"  - {rischio_label(c)} [{c}]")
    else:
        lines.append("Rischi specifici della mansione: nessuno flaggato.")
    if dpi_codes:
        lines.append("DPI assegnati alla mansione:")
        for c in dpi_codes:
            lines.append(f"  - {dpi_label(c)} [{c}]")
    else:
        lines.append("DPI assegnati alla mansione: nessuno.")
    lines.append("")
    lines.append(f"Azienda: {getattr(azienda, 'ragione_sociale', None) or '—'}")
    attivita = getattr(azienda, "attivita", None)
    if attivita:
        lines.append(f"Attivita' aziendale: {attivita}")
    ateco = getattr(azienda, "codice_ateco", None)
    if ateco:
        lines.append(f"Codice ATECO: {ateco}")
    descr = getattr(azienda, "descrizione_attivita", None)
    if descr:
        lines.append(f"Descrizione attivita': {descr}")
    lines.append("")
    lines.append(
        "Tabella di riferimento delle malattie professionali (scegliere SOLO "
        "tra questi codici):"
    )
    lines.append(format_reference_rows(malattie_riferimento))
    lines.append("")
    lines.append(
        "Proponi il protocollo di sorveglianza sanitaria per questa mansione."
    )
    return "\n".join(lines)


async def suggest_protocollo(
    *,
    mansione: str,
    rischi_codes: list[str],
    dpi_codes: list[str],
    azienda: object,
    malattie_riferimento: list[MalattiaProfessionale],
) -> ProtocolloSuggerito:
    """Ask the model for a protocol proposal and validate the disease codes.

    Uses OPENAI_MODEL_MEASURES at `medium` effort: the model has to weigh
    several risks at once against per-risk statutory cadences, and `low`
    tends to collapse everything to "annuale".
    """
    prompt = build_prompt(
        mansione=mansione,
        rischi_codes=rischi_codes,
        dpi_codes=dpi_codes,
        azienda=azienda,
        malattie_riferimento=malattie_riferimento,
    )
    logger.info(
        "Suggesting protocollo sanitario for mansione %r (%d rischi, %d dpi)",
        mansione,
        len(rischi_codes),
        len(dpi_codes),
    )
    response = await generate_structured(
        prompt=prompt,
        schema=ProtocolloSuggerito,
        system=SYSTEM_PROMPT,
        reasoning_effort="medium",
    )

    # Server-side filter: only codes that were offered in the prompt survive,
    # so a citation in the DVR always resolves to a real reference row.
    allowed = {r["codice"] for r in malattie_riferimento}
    kept: list[MalattiaScelta] = []
    seen: set[str] = set()
    dropped: list[str] = []
    for m in response.malattie_correlate:
        code = (m.codice or "").strip()
        if code not in allowed or get_malattia(code) is None:
            dropped.append(m.codice)
            continue
        if code in seen:
            continue
        seen.add(code)
        kept.append(MalattiaScelta(codice=code, motivazione=m.motivazione))
    if dropped:
        logger.warning(
            "AI returned %d malattie outside the reference subset (%s) — filtered",
            len(dropped),
            dropped,
        )

    return ProtocolloSuggerito(
        accertamenti=response.accertamenti,
        periodicita=response.periodicita,
        malattie_correlate=kept,
        motivazione=response.motivazione,
    )
