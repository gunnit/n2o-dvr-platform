"""AI-proposed D.Lgs. 151/2001 assessment for one mansione.

Client request (segnalazione 2026-08-25, confirmed 2026-09-04): a button
that, for each mansione, recognises the risks a pregnant worker would be
exposed to and either introduces limitations or declares the mansione not
compatible.

The keyword catalog in ``app.data.dlgs_151_2001`` only sees the job title.
It cannot tell that this "Impiegata" also runs the cella frigorifera twice a
day, or that this "Operaia" sits at a packaging line with no manual handling
at all. The DVR already holds that information — the pericoli assessed for
the ambienti where people with that mansione work, and the attrezzature in
those ambienti — so the model reasons over it and proposes:

  * ``rischi``              — keys from INCOMPATIBLE_RISKS only (validated
                              server-side, unknown keys are dropped);
  * ``rischi_aggiuntivi``   — free text for exposures the catalog lacks;
  * ``limitazioni``         — concrete measures the operator can adopt;
  * ``esito_proposto``      — one of the three esiti of the per-mansione
                              valutazione;
  * ``motivazione`` and ``riferimenti_normativi``.

The AI only PROPOSES. Nothing is persisted by the call; the operator
reviews, edits and saves through the existing PUT /gestanti/mansioni. A
``non_compatibile`` esito is a suggestion to the RSPP / medico competente,
never a decision.

Privacy contract (CLAUDE.md): the per-persona gestanti rows (pregnancy
state, dates) are personal health data and are never loaded here. The
prompt carries the mansione name, the azienda's activity / ATECO, the
assessed hazards and equipment descriptions, and the catalog vocabulary.
No names, no codici fiscali, no dates. ``build_context`` is the single
place the prompt is composed so a test can assert that.

Note: ``from __future__ import annotations`` is deliberately NOT used here —
with it, Pydantic can't resolve the ``EsitoProposto`` Literal alias without
a per-class model_rebuild() (see improvement_measures.py).
"""

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.data.dlgs_151_2001 import INCOMPATIBLE_RISKS
from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)


EsitoProposto = Literal[
    "compatibile", "compatibile_con_limitazioni", "non_compatibile"
]

# Upper bounds on the prompt: an azienda with dozens of ambienti and a full
# pericoli catalog would otherwise push hundreds of lines at the model for a
# single mansione. Beyond these the extra rows add cost, not signal.
MAX_PERICOLI_IN_PROMPT = 60
MAX_ATTREZZATURE_IN_PROMPT = 40


class PericoloContesto(BaseModel):
    """One assessed hazard fed to the model.

    A value object rather than the ORM row so the endpoint decides what
    crosses the privacy boundary (ambiente name, category, hazard text,
    exposure conditions, computed level) and nothing else does.
    """

    model_config = ConfigDict(extra="forbid")

    ambiente: str
    categoria: str
    pericolo: str
    condizioni: str | None = None
    livello: str | None = None


class GestantiMansioneSuggerita(BaseModel):
    """AI proposal for the per-mansione valutazione (art. 11 D.Lgs. 151/2001)."""

    model_config = ConfigDict(extra="forbid")

    rischi: list[str] = Field(
        description=(
            "Chiavi dei rischi incompatibili individuati per la mansione. "
            "DEVONO essere copiate ESATTAMENTE dal catalogo fornito (es. "
            "'night_shift', 'manual_handling_heavy'). Chiavi sconosciute "
            "vengono scartate. Lista vuota se nessun rischio del catalogo "
            "si applica."
        )
    )
    rischi_aggiuntivi: list[str] = Field(
        description=(
            "Rischi rilevanti per la gestante NON coperti dalle chiavi del "
            "catalogo, in testo libero italiano (max 150 caratteri "
            "ciascuno). Es. 'Stress da contatto con il pubblico in "
            "situazioni conflittuali'. Lista vuota se nulla da aggiungere."
        )
    )
    limitazioni: list[str] = Field(
        description=(
            "Limitazioni / misure di adeguamento concrete e verificabili "
            "che rendono la mansione compatibile, una per riga, in "
            "italiano (max 200 caratteri ciascuna). Es. 'Esonero dal "
            "lavoro notturno dalle 24:00 alle 06:00 (art. 53)'. Lista "
            "vuota se esito_proposto = 'compatibile'."
        )
    )
    esito_proposto: EsitoProposto = Field(
        description=(
            "Esito PROPOSTO al RSPP / medico competente: 'compatibile' "
            "(nessun rischio degli Allegati A/B/C), "
            "'compatibile_con_limitazioni' (i rischi sono eliminabili con "
            "le limitazioni elencate), 'non_compatibile' (il nucleo della "
            "mansione e' un lavoro vietato dell'Allegato A o una "
            "esposizione dell'Allegato B non derogabile: serve "
            "riallocazione o astensione anticipata)."
        )
    )
    motivazione: str = Field(
        description=(
            "2-3 frasi italiane che spiegano la proposta citando i pericoli "
            "valutati, le attrezzature e l'attivita' che l'hanno guidata. "
            "Deve chiarire che si tratta di una proposta da confermare."
        )
    )
    riferimenti_normativi: list[str] = Field(
        description=(
            "Riferimenti puntuali al D.Lgs. 151/2001 (Allegato A/B/C con "
            "lettera, art. 7, art. 11, art. 53, art. 17) e, se pertinente, "
            "al D.Lgs. 81/2008. Es. 'Allegato A lett. G D.Lgs. 151/2001'."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano (D.Lgs. 81/2008) specializzato nella tutela della maternita'
(D.Lgs. 151/2001, artt. 7, 11, 12, 17, 53 e Allegati A, B, C).

Devi valutare UNA mansione dal punto di vista di una lavoratrice in
gravidanza, puerperio (fino a 7 mesi dal parto) o allattamento. Ti vengono
forniti: la mansione, il profilo dell'azienda (attivita', ATECO), i pericoli
gia' valutati nel DVR per gli ambienti dove operano le persone con quella
mansione, le attrezzature presenti e il catalogo dei rischi incompatibili.

Per la mansione proponi:
  1. rischi — le chiavi del catalogo che si applicano (copiate ESATTAMENTE);
  2. rischi_aggiuntivi — esposizioni rilevanti che il catalogo non copre;
  3. limitazioni — misure concrete che eliminano il rischio per la gestante
     (esonero da compiti, cambio orario, postazione seduta, riduzione
     carichi, DPI, sorveglianza sanitaria specifica);
  4. esito_proposto — compatibile / compatibile_con_limitazioni /
     non_compatibile;
  5. motivazione e riferimenti_normativi.

Regole vincolanti:
- L'esito e' una PROPOSTA per il RSPP e il medico competente: sara' un
  operatore umano a confermarla o modificarla prima del salvataggio. Non
  esprimere giudizi sanitari sulla singola lavoratrice; valuta la mansione.
- Usa SOLO le chiavi del catalogo in `rischi`. Non inventare chiavi. Se un
  rischio reale non ha una chiave, mettilo in `rischi_aggiuntivi`.
- Ragiona sui pericoli valutati e sulle attrezzature, non solo sul titolo
  della mansione: una "impiegata" che lavora in cella frigorifera ha
  extreme_temperature; un "operaio" a una linea senza carichi non ha
  manual_handling_heavy.
- Sii decisionale ma prudente:
  * compatibile: nessun rischio degli Allegati A/B/C emerge dai dati;
  * compatibile_con_limitazioni: i rischi emersi sono eliminabili con le
    limitazioni elencate (e' il caso piu' frequente);
  * non_compatibile: il nucleo della mansione E' il lavoro vietato
    (Allegato A) o un'esposizione dell'Allegato B non derogabile, e nessuna
    limitazione realistica la rende compatibile: serve riallocazione o
    astensione anticipata (art. 17).
- Se esito_proposto != compatibile, `limitazioni` NON puo' essere vuota;
  per non_compatibile indica comunque la misura (riallocazione a mansione
  compatibile / richiesta di astensione anticipata).
- Limitazioni concrete e verificabili, in italiano, una per voce. Niente
  formule generiche come "adottare le misure necessarie".
- Riferimenti normativi puntuali (Allegato e lettera, articolo).

Formato output: SOLO JSON che rispetta lo schema dato."""


def _format_catalog_for_prompt() -> str:
    """Render the INCOMPATIBLE_RISKS vocabulary (key, Allegato, descrizione)."""
    lines: list[str] = []
    for key, info in INCOMPATIBLE_RISKS.items():
        lines.append(f"- {key} (Allegato {info['allegato']}): {info['descrizione']}")
    return "\n".join(lines)


def build_context(
    mansione: str,
    azienda,
    pericoli: list[PericoloContesto],
    attrezzature,
) -> str:
    """Compose the per-mansione context. No PII.

    ``azienda`` is read for ``attivita``, ``codice_ateco`` and
    ``descrizione_attivita`` only — never ``ragione_sociale`` (a ditta
    individuale's is the owner's name), ``codice_fiscale`` or ``persone``.
    ``attrezzature`` are read for ``descrizione`` only.
    """
    lines: list[str] = []
    lines.append(f"Mansione da valutare: {mansione}")
    lines.append("")

    attivita = getattr(azienda, "attivita", None)
    ateco = getattr(azienda, "codice_ateco", None)
    descrizione = getattr(azienda, "descrizione_attivita", None)
    lines.append("Profilo azienda:")
    lines.append(f"  Attivita': {attivita or '—'}")
    if ateco:
        lines.append(f"  Codice ATECO: {ateco}")
    if descrizione:
        lines.append(f"  Descrizione attivita': {descrizione}")
    lines.append("")

    if pericoli:
        lines.append(
            "Pericoli gia' valutati nel DVR per gli ambienti dove operano le "
            "persone con questa mansione:"
        )
        for p in pericoli[:MAX_PERICOLI_IN_PROMPT]:
            row = f"  - [{p.ambiente}] {p.categoria}: {p.pericolo}"
            if p.condizioni:
                row += f" — condizioni: {p.condizioni}"
            if p.livello:
                row += f" — livello: {p.livello}"
            lines.append(row)
        if len(pericoli) > MAX_PERICOLI_IN_PROMPT:
            lines.append(
                f"  (… altri {len(pericoli) - MAX_PERICOLI_IN_PROMPT} pericoli omessi)"
            )
    else:
        lines.append(
            "Pericoli valutati nel DVR: nessuno disponibile per questa mansione "
            "(ragiona sul titolo della mansione e sul profilo aziendale)."
        )
    lines.append("")

    descrizioni: list[str] = []
    seen: set[str] = set()
    for a in attrezzature or []:
        descr = (getattr(a, "descrizione", None) or "").strip()
        if not descr or descr.lower() in seen:
            continue
        seen.add(descr.lower())
        descrizioni.append(descr)
    if descrizioni:
        lines.append("Attrezzature presenti negli ambienti:")
        for descr in descrizioni[:MAX_ATTREZZATURE_IN_PROMPT]:
            lines.append(f"  - {descr}")
        if len(descrizioni) > MAX_ATTREZZATURE_IN_PROMPT:
            lines.append(
                f"  (… altre {len(descrizioni) - MAX_ATTREZZATURE_IN_PROMPT} attrezzature omesse)"
            )
    else:
        lines.append("Attrezzature presenti negli ambienti: nessuna dichiarata.")

    return "\n".join(lines)


def build_prompt(
    mansione: str,
    azienda,
    pericoli: list[PericoloContesto],
    attrezzature,
) -> str:
    """Full user prompt: context + catalog vocabulary + the ask."""
    context = build_context(mansione, azienda, pericoli, attrezzature)
    catalog = _format_catalog_for_prompt()
    return (
        f"Contesto:\n{context}\n\n"
        f"Catalogo dei rischi incompatibili D.Lgs. 151/2001 "
        f"(chiave — Allegato — descrizione):\n{catalog}\n\n"
        f"Valuta la mansione '{mansione}' per una lavoratrice gestante / "
        f"puerpera / in allattamento e proponi rischi, limitazioni ed esito."
    )


def sanitize_rischi_keys(keys: list[str]) -> list[str]:
    """Keep only INCOMPATIBLE_RISKS keys, de-duplicated, order preserved.

    The model is told to copy keys verbatim, but a hallucinated or
    re-spelled key must never reach the operator's checklist — the
    frontend matches keys 1:1 against the catalog rows it renders.
    """
    valid: list[str] = []
    dropped: list[str] = []
    for raw in keys or []:
        key = (raw or "").strip()
        if key not in INCOMPATIBLE_RISKS:
            dropped.append(raw)
            continue
        if key in valid:
            continue
        valid.append(key)
    if dropped:
        logger.warning(
            "AI returned %d unknown gestanti risk key(s) (%s) — filtered",
            len(dropped),
            dropped,
        )
    return valid


def _clean_lines(values: list[str]) -> list[str]:
    """Strip whitespace, drop empties and duplicates, keep order."""
    out: list[str] = []
    for v in values or []:
        s = (v or "").strip()
        if s and s not in out:
            out.append(s)
    return out


def sanitize_suggestion(
    raw: GestantiMansioneSuggerita,
) -> GestantiMansioneSuggerita:
    """Server-side validation of the model output before it reaches the API."""
    return GestantiMansioneSuggerita(
        rischi=sanitize_rischi_keys(raw.rischi),
        rischi_aggiuntivi=_clean_lines(raw.rischi_aggiuntivi),
        limitazioni=_clean_lines(raw.limitazioni),
        esito_proposto=raw.esito_proposto,
        motivazione=(raw.motivazione or "").strip(),
        riferimenti_normativi=_clean_lines(raw.riferimenti_normativi),
    )


async def suggest_gestanti_mansione(
    mansione: str,
    azienda,
    pericoli_context: list[PericoloContesto],
    attrezzature,
) -> GestantiMansioneSuggerita:
    """Propose the D.Lgs. 151/2001 valutazione for one mansione.

    Returns a proposal only — the caller never persists it. Runs on the
    shared domain-reasoning tier (OPENAI_MODEL_MEASURES) at ``medium``
    effort: the model has to weigh 14 catalog keys, derive limitations and
    pick an esito in one pass, the same multi-axis shape as the 11-category
    rischi suggester where ``low`` scored visibly worse.
    """
    prompt = build_prompt(mansione, azienda, pericoli_context, attrezzature)
    logger.info(
        "Suggesting gestanti valutazione for mansione %r of azienda %s "
        "(%d pericoli, %d attrezzature)",
        mansione,
        getattr(azienda, "id", None),
        len(pericoli_context),
        len(attrezzature or []),
    )
    response = await generate_structured(
        prompt=prompt,
        schema=GestantiMansioneSuggerita,
        system=SYSTEM_PROMPT,
        reasoning_effort="medium",
    )
    return sanitize_suggestion(response)
