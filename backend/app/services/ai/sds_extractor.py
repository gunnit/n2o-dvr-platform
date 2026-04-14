"""SDS (Schede di Sicurezza) extraction service.

Given a chemical Safety Data Sheet PDF, extracts the structured fields
required for the SostanzaChimica record using OpenAI vision + structured
outputs (gpt-5.4-mini by default).

Privacy: SDS files contain only chemical/product information — no personal
data — so they are explicitly authorized for AI processing per CLAUDE.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.exceptions import AIError
from app.schemas.sds_extraction import (
    CONFIDENCE_FAILURE_THRESHOLD,
    CONFIDENCE_WARNING_THRESHOLD,
    SDSExtraction,
)
from app.services.ai.client import extract_from_pdf

logger = logging.getLogger(__name__)


# Italian extraction prompt. Tuned for SDS structure (Reg. UE 2020/878,
# Sezione 1, 2, 9). Instructs the model on confidence semantics.
EXTRACTION_INSTRUCTIONS = """Sei un assistente esperto di sicurezza chimica.

Estrai i campi richiesti dalla Scheda di Sicurezza (SDS / SdS) allegata.
La SDS segue il formato del Regolamento UE 2020/878 (16 sezioni standard).

Linee guida per i campi:
- nome_prodotto: cerca in Sezione 1.1 "Identificatore del prodotto".
- produttore: cerca in Sezione 1.3 "Identificazione del fornitore" -- nome
  ragione sociale, NON l'indirizzo.
- stato_miscela: cerca in Sezione 9.1 "Stato fisico". Mappa a uno dei
  valori ammessi (solido / liquido / gassoso / aerosol / polvere / pasta /
  altro). Se incerto, usa "altro".
- pittogrammi: cerca in Sezione 2.2 "Elementi dell'etichetta". Riporta i
  codici GHS01-GHS09 visibili. Se la sostanza NON e' classificata pericolosa
  ("non e' una sostanza/miscela pericolosa"), restituisci lista vuota.
- frasi_h: cerca in Sezione 2.2 e 3. Codici nel formato "H" + 3 cifre
  (es. H225, H319). Mantieni i codici combinati come "H315+H320" se presenti.
- frasi_p: cerca in Sezione 2.2. Codici "P" + 3 cifre (es. P210, P305+P351+P338).

Linee guida per la confidence (0.0-1.0):
- 1.0 = campo letto chiaramente, nessuna ambiguita
- 0.7-0.9 = campo presente ma con qualche dubbio (es. testo parzialmente
  leggibile, formato non standard)
- 0.4-0.6 = ricostruito da contesto, valore probabile ma non certo
- 0.0-0.3 = campo non trovato, illeggibile, o sostanza non classificata
  (per pittogrammi/frasi vuote restituisci confidence ~0.9 se la sezione 2.2
  conferma esplicitamente che non e' pericolosa, altrimenti 0.2)

extraction_notes: usa SOLO se la SDS ha problemi rilevanti per la revisione
umana (PDF scansionato di bassa qualita, lingua non italiana/inglese,
sezioni mancanti, ecc.). Altrimenti restituisci null.

overall_confidence: media pesata delle confidence di nome_prodotto,
pittogrammi e frasi_h (i campi piu' critici per la valutazione del rischio).

Ricorda: se il PDF e' completamente illeggibile o non e' una SDS, restituisci
tutti i campi a null/lista vuota con confidence 0 ed extraction_notes che
spiega il problema."""


async def extract_sds(pdf_path: str | Path) -> SDSExtraction:
    """Extract structured chemical data from one SDS PDF.

    Returns a fully-validated SDSExtraction. Raises AIError on API failure
    or invalid PDF. A successful return with low overall_confidence is NOT
    an error — the caller decides whether to surface it for review or fail.
    """
    path = Path(pdf_path)
    logger.info("Extracting SDS: %s", path.name)

    extraction = await extract_from_pdf(
        path,
        schema=SDSExtraction,
        instructions=EXTRACTION_INSTRUCTIONS,
    )

    logger.info(
        "SDS extracted: %s (overall_confidence=%.2f, %d pittogrammi, %d H, %d P)",
        extraction.nome_prodotto or "<unknown>",
        extraction.overall_confidence,
        len(extraction.pittogrammi),
        len(extraction.frasi_h),
        len(extraction.frasi_p),
    )
    return extraction


def to_db_dict(
    extraction: SDSExtraction,
    *,
    sds_file_path: str | None = None,
) -> dict:
    """Map an SDSExtraction onto a SostanzaChimica-compatible dict.

    Sets ai_extracted=True, ai_confidence=overall_confidence,
    human_reviewed=False. The caller adds azienda_id and persists.

    Returns None for nome_prodotto (NOT NULL in DB) only if the extraction
    completely failed -- in that case use the failure handler below.
    """
    return {
        "nome_prodotto": extraction.nome_prodotto or "(da revisionare)",
        "produttore": extraction.produttore,
        "stato_miscela": extraction.stato_miscela,
        "pittogrammi": list(extraction.pittogrammi),
        "frasi_h": list(extraction.frasi_h),
        "frasi_p": list(extraction.frasi_p),
        "ai_extracted": True,
        "ai_confidence": extraction.overall_confidence,
        "human_reviewed": False,
        "sds_file_path": sds_file_path,
    }


def low_confidence_fields(extraction: SDSExtraction) -> list[str]:
    """List of field names whose confidence < CONFIDENCE_WARNING_THRESHOLD.

    Used by the API/UI to drive the per-cell yellow warning icon (US-1.9
    acceptance criterion 2).
    """
    fields = {
        "nome_prodotto": extraction.nome_prodotto_confidence,
        "produttore": extraction.produttore_confidence,
        "stato_miscela": extraction.stato_miscela_confidence,
        "pittogrammi": extraction.pittogrammi_confidence,
        "frasi_h": extraction.frasi_h_confidence,
        "frasi_p": extraction.frasi_p_confidence,
    }
    return [name for name, conf in fields.items() if conf < CONFIDENCE_WARNING_THRESHOLD]


def is_failed_extraction(extraction: SDSExtraction) -> bool:
    """True if overall_confidence is below the failure threshold.

    The UI should show "Estrazione fallita / Inserisci manualmente" rather
    than auto-populating the row (US-1.9 acceptance criterion 3).
    """
    return extraction.overall_confidence < CONFIDENCE_FAILURE_THRESHOLD
