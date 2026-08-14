"""AI-suggested rischi interferenziali for a DUVRI (client request 2026-08).

Given the contractor activity context of one appalto — the attrezzature /
attivita chips the operator ticked, the oggetto dell'appalto, and the
luoghi (ambienti) of the committente where the work happens — the model
proposes additional interference risks (rischio + misure + DPI +
riferimento normativo) beyond what the static rules engine in
``app.data.duvri_interference_rules`` already covers.

The static rules stay the baseline: the prompt lists both the interferenze
already identified on the DUVRI and the static rules that fire for the
selected equipment, and instructs the model NOT to duplicate either. The
operator reviews every suggestion in the form ("Interferenze identificate")
and only accepted ones land in the document via the normal save path.

Uses gpt-5.4-mini (OPENAI_MODEL_MEASURES) at low reasoning effort — same
tier as the other domain-reasoning suggesters (DPI/rischi, HACCP CCP).

PII contract: only work-related signals are sent — equipment/activity
types, the works description, ambiente names and already-identified risk
texts. No contractor company names, no referente names, no partita IVA,
no codice fiscale. The caller must not pass any of those.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)

# Same limits as app.schemas.duvri.InterferenzaItem, so an accepted
# suggestion always passes validation on the DUVRI save path.
_MAX_RISCHIO_LEN = 500
_MAX_MISURE_LEN = 2000
_MAX_ITEMS = 8

# Italian labels for the canonical contractor equipment codes
# (CONTRACTOR_EQUIPMENT_TYPES in app.data.duvri_interference_rules).
# Mirrors EQUIPMENT_LABELS in the DUVRI page so the model reads the same
# wording the operator saw on the chips.
EQUIPMENT_LABELS: dict[str, str] = {
    "muletto": "Muletto / carrello elevatore",
    "transpallet_elettrico": "Transpallet elettrico",
    "ponteggio": "Ponteggio",
    "piattaforma_aerea": "Piattaforma aerea (PLE)",
    "gru": "Gru",
    "saldatrice": "Saldatrice",
    "fiamma_libera": "Fiamma libera",
    "prodotti_chimici": "Prodotti chimici",
    "pulizie_pavimenti": "Pulizie pavimenti",
    "macchinari_rumorosi": "Macchinari rumorosi",
    "attrezzature_elettriche_portatili": "Attrezzature elettriche portatili",
    "veicoli_trasporto": "Veicoli di trasporto",
    "scavo_movimento_terra": "Scavo / movimento terra",
    "lavori_in_quota": "Lavori in quota",
    "demolizioni": "Demolizioni",
}


class InterferenzaSuggerita(BaseModel):
    """One AI-proposed interference risk for the operator to review."""

    model_config = ConfigDict(extra="forbid")

    titolo: str = Field(
        description=(
            "Titolo breve dell'interferenza (max 10 parole), in italiano "
            "(es. 'Proiezione di scintille verso aree di transito')."
        )
    )
    rischio: str = Field(
        description=(
            "Descrizione del rischio interferenziale in 1-2 frasi: quale "
            "attivita' dell'appaltatore interferisce con il personale del "
            "committente (o di altri appaltatori) e con quale conseguenza. "
            "In italiano, max 500 caratteri."
        )
    )
    misure: str = Field(
        description=(
            "Misure di prevenzione, protezione e COORDINAMENTO tra "
            "committente e appaltatore (delimitazioni, sfasamento orari, "
            "permessi di lavoro, informazione reciproca). In italiano, "
            "concrete e attuabili, max 2000 caratteri."
        )
    )
    dpi: list[str] = Field(
        description=(
            "DPI richiesti al personale interferito e/o all'appaltatore "
            "(es. 'Casco di protezione', 'Gilet alta visibilita'). Lista "
            "vuota se nessun DPI aggiuntivo serve."
        )
    )
    riferimento: str = Field(
        description=(
            "Riferimento normativo italiano pertinente (es. 'D.Lgs. "
            "81/2008 art. 26', 'D.M. 02/09/2021')."
        )
    )


class InterferenzeSuggerite(BaseModel):
    """AI suggestions for a DUVRI's rischi interferenziali."""

    model_config = ConfigDict(extra="forbid")

    items: list[InterferenzaSuggerita] = Field(
        description=(
            "2-6 rischi interferenziali NON gia' coperti dalle interferenze "
            "esistenti ne' dalle regole standard elencate, ordinati dal "
            "piu' rilevante."
        )
    )
    sintesi: str = Field(
        description=(
            "1-2 frasi in italiano sul quadro complessivo delle "
            "interferenze di questo appalto e sulle priorita' di "
            "coordinamento."
        )
    )


SYSTEM_PROMPT = """Sei un consulente esperto di sicurezza sul lavoro
italiano (D.Lgs. 81/2008), specializzato nella redazione di DUVRI ai sensi
dell'art. 26 (Documento Unico di Valutazione dei Rischi da Interferenze).

Dato il contesto di un appalto (attrezzature/attivita' dell'appaltatore,
oggetto dei lavori, luoghi del committente dove si svolgono), proponi i
rischi INTERFERENZIALI aggiuntivi: rischi che nascono dalla compresenza
tra il personale dell'appaltatore e il personale del committente (o di
altri appaltatori) negli stessi luoghi.

Regole vincolanti:
- Solo rischi da INTERFERENZA (art. 26): esclusi i rischi propri
  dell'attivita' dell'appaltatore che non toccano terzi.
- NON duplicare le interferenze gia' identificate ne' quelle coperte
  dalle regole standard elencate nel prompt: proponi solo cio' che manca
  (combinazioni di attrezzature, specificita' dei luoghi, fasi di
  ingresso/uscita, emergenze, forniture, viabilita', servizi comuni).
- 2-6 proposte, ordinate per rilevanza. Se il contesto e' gia' ben
  coperto, proponine poche: la completezza non si misura in quantita'.
- Misure concrete e orientate al COORDINAMENTO (delimitazioni, sfasamento
  temporale, permessi di lavoro, riunioni di coordinamento, informazione
  reciproca), non generiche raccomandazioni.
- Cita sempre un riferimento normativo italiano pertinente.

Formato output: SOLO JSON che rispetta lo schema dato."""


def _build_context(
    oggetto_appalto: str | None,
    attrezzature: list[tuple[str, str | None]],
    luoghi: list[str],
    interferenze_esistenti: list[str],
    regole_standard_attive: list[str],
) -> str:
    """Compose the appalto context block. No PII (no names, no P.IVA)."""
    lines: list[str] = []
    lines.append(
        f"Oggetto dell'appalto: {oggetto_appalto.strip() if oggetto_appalto and oggetto_appalto.strip() else 'non specificato'}"
    )

    lines.append("Attrezzature / attivita' dell'appaltatore:")
    for tipo, descrizione in attrezzature:
        label = EQUIPMENT_LABELS.get(tipo, tipo.replace("_", " "))
        entry = f"  - {label}"
        if descrizione and descrizione.strip():
            entry += f" ({descrizione.strip()})"
        lines.append(entry)

    if luoghi:
        lines.append("Luoghi del committente interessati dai lavori:")
        for luogo in luoghi:
            lines.append(f"  - {luogo}")

    if interferenze_esistenti:
        lines.append(
            "Interferenze GIA' identificate su questo DUVRI (non riproporle):"
        )
        for rischio in interferenze_esistenti:
            lines.append(f"  - {rischio}")

    if regole_standard_attive:
        lines.append(
            "Interferenze gia' coperte dalle regole standard per queste "
            "attrezzature (non riproporle):"
        )
        for regola in regole_standard_attive:
            lines.append(f"  - {regola}")

    return "\n".join(lines)


def _normalize(text: str) -> str:
    """Comparison key for duplicate detection: casefolded, single-spaced."""
    return " ".join(text.split()).casefold()


async def suggest_interferenze(
    *,
    oggetto_appalto: str | None,
    attrezzature: list[tuple[str, str | None]],
    luoghi: list[str],
    interferenze_esistenti: list[str],
    regole_standard_attive: list[str],
) -> InterferenzeSuggerite:
    """AI: propose additional rischi interferenziali for one appalto.

    Args:
        oggetto_appalto: free-text works description (no personal data).
        attrezzature: (tipo, descrizione) pairs from the DUVRI form chips.
        luoghi: ambiente labels of the committente (e.g. "Magazzino (magazzino)").
        interferenze_esistenti: risk texts already on the DUVRI, so the
            model does not duplicate them.
        regole_standard_attive: "titolo: rischio" lines of the static rules
            that fire for the selected equipment — the AI complements the
            rules engine, it does not replay it.

    Returns:
        InterferenzeSuggerite with items truncated to the InterferenzaItem
        field limits and de-duplicated against the existing risk texts, so
        every accepted suggestion passes validation on the save path.
    """
    context = _build_context(
        oggetto_appalto,
        attrezzature,
        luoghi,
        interferenze_esistenti,
        regole_standard_attive,
    )
    prompt = (
        f"Contesto dell'appalto:\n{context}\n\n"
        f"Proponi i rischi interferenziali aggiuntivi per questo DUVRI."
    )

    logger.info(
        "Suggesting DUVRI interferenze (%d attrezzature, %d luoghi, "
        "%d esistenti, %d regole standard)",
        len(attrezzature),
        len(luoghi),
        len(interferenze_esistenti),
        len(regole_standard_attive),
    )
    response = await generate_structured(
        prompt,
        schema=InterferenzeSuggerite,
        system=SYSTEM_PROMPT,
        reasoning_effort="low",
    )

    # Post-validate: clamp to InterferenzaItem limits and drop anything that
    # duplicates an already-identified risk, so the frontend can hand an
    # accepted suggestion straight to the DUVRI save path.
    existing_keys = {_normalize(r) for r in interferenze_esistenti}
    items: list[InterferenzaSuggerita] = []
    dropped = 0
    for item in response.items:
        if _normalize(item.rischio) in existing_keys:
            dropped += 1
            continue
        items.append(
            InterferenzaSuggerita(
                titolo=item.titolo.strip(),
                rischio=item.rischio.strip()[:_MAX_RISCHIO_LEN],
                misure=item.misure.strip()[:_MAX_MISURE_LEN],
                dpi=[d.strip() for d in item.dpi if d and d.strip()],
                riferimento=item.riferimento.strip(),
            )
        )
        if len(items) >= _MAX_ITEMS:
            break
    if dropped:
        logger.warning(
            "AI returned %d interferenze duplicating existing ones — filtered",
            dropped,
        )

    return InterferenzeSuggerite(items=items, sintesi=response.sintesi)
