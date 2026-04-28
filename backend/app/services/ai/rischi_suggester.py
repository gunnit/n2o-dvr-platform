"""AI-suggested rischi (risk applicability + default scoring) per ambiente — Phase 8.3.

Given an ambiente (tipo + descrizione), the equipment present, and the
azienda profile (attivita / codice ATECO), the model proposes which of
the 11 canonical risk categories should be marked applicabile=True, with
a starter pericolo description and conservative P/D scores.

The operator reviews each suggestion and ticks which to keep (merge, not
replace — pre-existing valutazioni are preserved). Persistence happens
via the existing batch endpoint POST /aziende/{a}/ambienti/{e}/rischi/batch.

Why an LLM and not the static _DEFAULT_APPLICABLE_RISKS map?
The static map keys off env type only ("Ufficio", "Cucina", ...). It
can't reason about "this Cucina is a gelateria with no gas burners" or
"this Ufficio has a lab annex with chemicals" — situations the
descrizione_attivita and the equipment list reveal. The static map stays
as a fallback and as the seed for AI prompt grounding.

Privacy contract (CLAUDE.md): no PII (codice fiscale, ID docs, health
data) is sent. Risk categories and equipment names are not personal data.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.azienda import Azienda
from app.services.ai.client import generate_structured
from app.services.reference_data import (
    CATEGORIA_LONG_TO_SHORT,
    HAZARD_LIBRARY,
    RISK_CATEGORIES,
    RISK_CATEGORY_NAMES,
    RISK_CATEGORY_SHORT_NAMES,
    get_default_pd,
)

logger = logging.getLogger(__name__)


class RischioSuggerito(BaseModel):
    """One AI-suggested risk row for an ambiente."""

    model_config = ConfigDict(extra="forbid")

    categoria_rischio: str = Field(
        description=(
            "Nome corto della categoria di rischio (forma usata dal DB e "
            "dal wizard). DEVE corrispondere ESATTAMENTE a una delle 11 "
            "etichette: Strutture, Macchine, Elettrici, Incendio, Chimici, "
            "Fisici, Biologici, Cancerogeni, Organizzazione, Psicologici, "
            "Ergonomici. Codici sconosciuti vengono scartati."
        )
    )
    applicabile: bool = Field(
        description=(
            "True se questa categoria si applica all'ambiente in esame. "
            "False se la categoria e' irrilevante (es. 'Agenti Cancerogeni' "
            "in un ufficio amministrativo senza esposizioni)."
        )
    )
    pericolo: str = Field(
        description=(
            "Descrizione del pericolo specifico identificato per questo "
            "ambiente, max 200 caratteri italiano. Esempio: 'Esposizione "
            "a calore radiante e umidita elevata durante la cottura'. "
            "Stringa vuota se applicabile=False."
        )
    )
    probabilita_p: int = Field(
        ge=1,
        le=4,
        description=(
            "Probabilita stimata su scala 1-4 (1=Bassa, 2=Medio-Bassa, "
            "3=Medio-Alta, 4=Elevata). Default conservativo: 1 per "
            "ambienti d'ufficio, 2 per produzione/cucina/officina."
        ),
    )
    danno_d: int = Field(
        ge=1,
        le=4,
        description=(
            "Danno stimato su scala 1-4 (1=Lieve, 2=Medio, 3=Grave, "
            "4=Gravissimo). Coerente con la severita potenziale del "
            "pericolo per la categoria (es. cancerogeni->4, ergonomici->2)."
        ),
    )
    motivazione: str = Field(
        description=(
            "Sintesi 1 frase del perche' di questa scelta, citando "
            "ambiente/attrezzature/attivita che hanno guidato la decisione."
        )
    )


class RischiSuggeriti(BaseModel):
    """AI response: full set of risk suggestions for one ambiente."""

    model_config = ConfigDict(extra="forbid")

    items: list[RischioSuggerito] = Field(
        description=(
            "Una entry per ognuna delle 11 categorie di rischio, con "
            "applicabile=True/False. Includere TUTTE le 11 categorie, "
            "non solo quelle applicabili — gli operatori vogliono vedere "
            "anche le 'NO' per conferma."
        )
    )
    sintesi: str = Field(
        description=(
            "Sintesi 1-2 frasi della valutazione complessiva dell'ambiente "
            "(es. 'Cucina di ristorante a media densita: rischi termici, "
            "macchine, biologici dominanti; cancerogeni e psicologici "
            "esclusi')."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano (D.Lgs. 81/2008) specializzato nella valutazione dei rischi
per ambiente di lavoro.

Dato un ambiente (tipo, descrizione attivita, attrezzature presenti) e
il profilo dell'azienda (settore ATECO, attivita), valuta TUTTE le 11
categorie canoniche di rischio e per ognuna proponi:
  1. applicabile (True/False) — se la categoria si applica all'ambiente;
  2. pericolo specifico — descrizione concreta del pericolo se
     applicabile, stringa vuota altrimenti;
  3. P (probabilita 1-4) e D (danno 1-4) — scoring conservativo iniziale
     che l'operatore puo' aggiustare;
  4. motivazione — 1 frase italiana che spiega il ragionamento.

Regole vincolanti:
- Restituisci ESATTAMENTE 11 entry, una per ognuna delle categorie
  canoniche fornite. NON inventare categorie nuove.
- Le categorie vanno copiate ESATTAMENTE come scritte nel catalogo
  (es. 'Agenti Chimici', NON 'Chimici' o 'agenti chimici').
- Sii decisionale: se un ufficio amministrativo non ha cancerogeni,
  applicabile=False con motivazione breve. Non flaggare tutto SI per
  paura.
- Scoring iniziale conservativo: P=1 per uffici, P=2 per
  produzione/cucina/officina, P=3 solo se attrezzature/attivita
  segnalano esposizione frequente. D segue la severita potenziale del
  pericolo (cancerogeni e elettrici alti, ergonomici medi).
- Rifletti il contesto reale: una pizzeria ha rischi termici/macchine/
  biologici alimentari; un commercialista ha solo strutture/elettrici/
  ergonomici/psicologici/organizzazione.

Formato output: SOLO JSON che rispetta lo schema dato."""


def _format_categories_for_prompt() -> str:
    """Render the 11 categories (short name + full name + hazard examples)."""
    lines: list[str] = []
    for rc in RISK_CATEGORIES:
        long_name = rc["categoria"]
        short_name = CATEGORIA_LONG_TO_SHORT.get(long_name, long_name)
        macro = rc["macro_categoria"]
        examples = HAZARD_LIBRARY.get(long_name, [])[:3]
        lines.append(f"- {short_name} (forma estesa: {long_name}, macro: {macro})")
        for ex in examples:
            lines.append(f"    es: {ex}")
    return "\n".join(lines)


def _build_context(
    ambiente: Ambiente,
    azienda: Azienda,
    attrezzature: list[Attrezzatura],
) -> str:
    """Compose the per-ambiente context. No PII."""
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
    if attrezzature:
        lines.append("")
        lines.append("Attrezzature presenti in questo ambiente:")
        for a in attrezzature:
            descr = a.descrizione or "—"
            ce = " (CE)" if getattr(a, "marcatura_ce", False) else ""
            lines.append(f"  - {descr}{ce}")
    else:
        lines.append("")
        lines.append("Attrezzature presenti in questo ambiente: nessuna dichiarata.")
    return "\n".join(lines)


async def suggest_rischi(
    ambiente: Ambiente,
    azienda: Azienda,
    attrezzature: list[Attrezzatura],
) -> RischiSuggeriti:
    """Generate AI suggestions for all 11 risk categories on an ambiente.

    Returns the full set (applicable + non-applicable) so the operator can
    confirm both. Server-side validation drops any categoria not in the
    canonical RISK_CATEGORY_NAMES list and clamps P/D to defaults if
    missing.

    Uses OPENAI_MODEL_MEASURES (gpt-5.4-mini) — needs domain reasoning over
    11 categories at once; costlier than the simpler suggesters but still
    a single round-trip. Runs at `medium` reasoning effort because the
    model has to weigh applicability AND default P/D for each of the 11
    categories simultaneously — `low` produced visibly weaker P/D scoring
    in spot checks.
    """
    context = _build_context(ambiente, azienda, attrezzature)
    catalog = _format_categories_for_prompt()
    prompt = (
        f"Contesto ambiente:\n{context}\n\n"
        f"Catalogo delle 11 categorie di rischio (con esempi di pericolo):\n"
        f"{catalog}\n\n"
        f"Valuta tutte le 11 categorie per questo ambiente."
    )
    logger.info(
        "Suggesting rischi for ambiente %s (tipo=%s) of azienda %s",
        ambiente.id,
        ambiente.tipo,
        azienda.id,
    )
    response = await generate_structured(
        prompt=prompt,
        schema=RischiSuggeriti,
        system=SYSTEM_PROMPT,
        reasoning_effort="medium",
    )

    # Server-side filter: accept only the 11 canonical short names.
    # Be lenient: if the model returned a long name, map back to short.
    short_set = set(RISK_CATEGORY_SHORT_NAMES)
    valid: list[RischioSuggerito] = []
    seen: set[str] = set()
    dropped: list[str] = []
    for item in response.items:
        cat = (item.categoria_rischio or "").strip()
        if cat not in short_set and cat in CATEGORIA_LONG_TO_SHORT:
            cat = CATEGORIA_LONG_TO_SHORT[cat]
        if cat not in short_set:
            dropped.append(item.categoria_rischio)
            continue
        if cat in seen:
            continue
        seen.add(cat)
        # Replace categoria_rischio with the canonical short form before
        # handing back to the API layer, so the frontend can match it
        # 1:1 against its own CATEGORIE_RISCHIO array.
        valid.append(
            RischioSuggerito(
                categoria_rischio=cat,
                applicabile=item.applicabile,
                pericolo=item.pericolo,
                probabilita_p=item.probabilita_p,
                danno_d=item.danno_d,
                motivazione=item.motivazione,
            )
        )

    if dropped:
        logger.warning(
            "AI returned %d unknown rischi categorie (%s) — filtered",
            len(dropped),
            dropped,
        )

    # If the model omitted any of the 11, add a conservative non-applicable
    # row so the operator sees the full grid. Defaults come from
    # get_default_pd, keyed by long name (its existing API).
    for short_cat in RISK_CATEGORY_SHORT_NAMES:
        if short_cat in seen:
            continue
        # Look up defaults by long name (get_default_pd accepts long names).
        long_cat = next(
            (lng for lng, sht in CATEGORIA_LONG_TO_SHORT.items() if sht == short_cat),
            None,
        )
        try:
            p_def, d_def = (
                get_default_pd(long_cat) if long_cat else (1, 1)
            )
        except ValueError:
            p_def, d_def = 1, 1
        valid.append(
            RischioSuggerito(
                categoria_rischio=short_cat,
                applicabile=False,
                pericolo="",
                probabilita_p=p_def,
                danno_d=d_def,
                motivazione="Categoria non flaggata dall'AI per questo ambiente.",
            )
        )

    return RischiSuggeriti(items=valid, sintesi=response.sintesi)
