"""AI-suggested detail fields for a HACCP Critical Control Point (feedback #66).

Given a CCP name (e.g. "Cottura", "Conservazione a freddo", "Ricevimento
materie prime") plus optional activity/sector context, the model proposes the
detail fields that make up a CCP row on an azienda's HACCP config:

  - fase: the process phase the CCP belongs to
  - pericolo: the food-safety hazard being controlled
  - limite_critico: the critical limit (temperature, time, etc.)
  - monitoraggio: how the limit is monitored
  - azione_correttiva: the corrective action when the limit is breached
  - frequenza: monitoring cadence

These mirror the ``CcpEntry`` schema fields exactly (``codice`` and ``nome``
are identity fields owned by the operator, so the model does not produce them).

Uses gpt-5.4-mini (OPENAI_MODEL_MEASURES) — food-safety domain reasoning
grounded in Reg. CE 852/2004 and HACCP Codex Alimentarius, no heavy
chain-of-thought needed. No personal data is ever sent to the model.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)


class HaccpCcpAiSuggestion(BaseModel):
    """AI suggestions for a single HACCP CCP's detail fields.

    Field names match ``app.schemas.haccp.CcpEntry`` so the result maps
    1:1 onto a CCP row (minus ``codice``/``nome``, which the operator owns).
    """

    model_config = ConfigDict(extra="forbid")

    fase: str = Field(
        description=(
            "Fase del processo produttivo a cui appartiene il CCP "
            "(es. 'Cottura / trattamento termico', 'Stoccaggio refrigerato', "
            "'Accettazione merci'). In italiano, concisa."
        )
    )
    pericolo: str = Field(
        description=(
            "Pericolo per la sicurezza alimentare controllato da questo CCP, "
            "con esempi di agenti quando pertinente (es. 'Sopravvivenza di "
            "microrganismi patogeni quali Salmonella, Listeria, E. coli'). "
            "In italiano."
        )
    )
    limite_critico: str = Field(
        description=(
            "Limite critico misurabile e oggettivo, con valori di temperatura "
            "e/o tempo dove applicabile (es. 'Temperatura al cuore "
            ">= 75 C per almeno 2 minuti'). In italiano."
        )
    )
    monitoraggio: str = Field(
        description=(
            "Modalita di monitoraggio del limite critico (es. 'Termometro a "
            "sonda calibrato sul pezzo piu spesso', 'Data-logger in ciascun "
            "comparto'). In italiano."
        )
    )
    azione_correttiva: str = Field(
        description=(
            "Azione correttiva da intraprendere al superamento del limite "
            "critico (es. 'Prolungare la cottura fino al raggiungimento del "
            "limite; se impossibile, scartare il prodotto'). In italiano."
        )
    )
    frequenza: str = Field(
        description=(
            "Frequenza del monitoraggio (es. 'Ogni cottura', '2 volte al "
            "giorno (mattina / sera)', 'Ogni consegna'). In italiano, breve."
        )
    )


SYSTEM_PROMPT = (
    "Sei un consulente esperto di sicurezza alimentare e sistemi HACCP in "
    "Italia. Conosci approfonditamente il Reg. CE 852/2004, il Reg. CE "
    "178/2002 e le linee guida del Codex Alimentarius per l'individuazione "
    "dei punti critici di controllo (CCP). Proponi limiti critici "
    "misurabili e prassi di monitoraggio realistiche per il settore della "
    "ristorazione e della produzione alimentare. Rispondi sempre in "
    "italiano tecnico-professionale."
)


async def suggest_ccp_details(
    ccp_nome: str,
    *,
    settore: str | None = None,
    attivita: str | None = None,
) -> HaccpCcpAiSuggestion:
    """Generate AI suggestions for a HACCP CCP's detail fields.

    Args:
        ccp_nome: name of the Critical Control Point (e.g. "Cottura",
            "Conservazione a freddo", "Ricevimento materie prime").
        settore: optional food sector / activity-type label for context
            (e.g. "Ristorazione", "Mensa aziendale", "Gelateria"). Free text.
        attivita: optional extra description of the activity to sharpen the
            suggestion. Free text. Never include personal data.

    Returns:
        HaccpCcpAiSuggestion with fase, pericolo, limite_critico,
        monitoraggio, azione_correttiva, frequenza.
    """
    context_lines = []
    if settore and settore.strip():
        context_lines.append(f"Tipologia di attivita: {settore.strip()}")
    if attivita and attivita.strip():
        context_lines.append(f"Contesto attivita: {attivita.strip()}")
    context = ("\n" + "\n".join(context_lines)) if context_lines else ""

    prompt = (
        f"Per il punto critico di controllo (CCP) denominato \"{ccp_nome}\" "
        f"di un manuale HACCP, genera i campi di dettaglio:{context}\n\n"
        f"1. fase — la fase del processo a cui appartiene il CCP\n"
        f"2. pericolo — il pericolo per la sicurezza alimentare controllato\n"
        f"3. limite_critico — il limite critico misurabile (temperature/tempi)\n"
        f"4. monitoraggio — come viene monitorato il limite\n"
        f"5. azione_correttiva — l'azione al superamento del limite\n"
        f"6. frequenza — la cadenza del monitoraggio\n\n"
        f"Basati sul Reg. CE 852/2004 e sulle linee guida HACCP del Codex "
        f"Alimentarius. Usa valori realistici per il settore alimentare "
        f"italiano."
    )

    logger.info("HACCP CCP AI suggestion for: %s", ccp_nome)
    return await generate_structured(
        prompt,
        schema=HaccpCcpAiSuggestion,
        system=SYSTEM_PROMPT,
        reasoning_effort="low",
    )
