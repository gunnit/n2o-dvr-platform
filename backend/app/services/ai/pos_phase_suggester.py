"""AI-suggested phase details for POS construction phases (US-4.7).

Given a construction phase name, the model proposes:
  - descrizione: a concise description of the construction activity
  - rischi: typical workplace safety risks for that phase
  - dpi: required PPE (dispositivi di protezione individuale) for that phase

Uses gpt-5.4-mini (OPENAI_MODEL_MEASURES) — domain reasoning for
construction safety context, no heavy chain-of-thought needed.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.client import generate_structured

logger = logging.getLogger(__name__)


class PosPhaseAiSuggestion(BaseModel):
    """AI suggestions for a single POS construction phase."""

    model_config = ConfigDict(extra="forbid")

    descrizione: str = Field(
        description=(
            "Descrizione operativa della fase lavorativa in italiano, "
            "2-4 frasi. Deve descrivere concretamente le attivita' "
            "svolte in cantiere durante questa fase."
        )
    )
    rischi: list[str] = Field(
        description=(
            "Lista dei rischi tipici per la sicurezza associati a questa "
            "fase lavorativa (es. 'Caduta dall\\'alto', 'Schiacciamento', "
            "'Esposizione a rumore'). Da 3 a 8 rischi, ordinati per "
            "rilevanza. In italiano."
        )
    )
    dpi: list[str] = Field(
        description=(
            "Lista dei DPI obbligatori per questa fase lavorativa "
            "(es. 'Casco di protezione', 'Scarpe antinfortunistiche', "
            "'Imbragatura anticaduta'). Da 2 a 6 DPI, in italiano."
        )
    )


SYSTEM_PROMPT = (
    "Sei un esperto di sicurezza sul lavoro nei cantieri edili in Italia. "
    "Conosci approfonditamente il D.Lgs. 81/2008, il Titolo IV (cantieri "
    "temporanei o mobili) e le relative norme tecniche UNI. "
    "Rispondi sempre in italiano tecnico-professionale."
)


async def suggest_phase_details(
    fase_nome: str,
) -> PosPhaseAiSuggestion:
    """Generate AI suggestions for a POS construction phase.

    Args:
        fase_nome: name/type of the construction phase (e.g. "Scavo",
            "Montaggio ponteggi", "Getto calcestruzzo").

    Returns:
        PosPhaseAiSuggestion with descrizione, rischi, dpi.
    """
    prompt = (
        f"Per la fase lavorativa di cantiere edile denominata \"{fase_nome}\", "
        f"genera:\n"
        f"1. Una descrizione operativa delle attivita' svolte (2-4 frasi)\n"
        f"2. I rischi tipici per la sicurezza dei lavoratori (3-8 rischi)\n"
        f"3. I DPI obbligatori per questa fase (2-6 dispositivi)\n\n"
        f"Basati sulle prescrizioni del D.Lgs. 81/2008 Titolo IV e sulle "
        f"buone pratiche dei cantieri edili italiani."
    )

    logger.info("POS phase AI suggestion for: %s", fase_nome)
    return await generate_structured(
        prompt,
        schema=PosPhaseAiSuggestion,
        system=SYSTEM_PROMPT,
        reasoning_effort="low",
    )
