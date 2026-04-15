"""D.Lgs. 151/2001 — catalog of incompatible risks for gestanti / puerpere / allattamento.

The 2001 decree (Tutela della maternita') prohibits or restricts certain
working conditions for pregnant workers (gestanti), women who gave birth
in the last 7 months (puerpere) and breastfeeding workers (allattamento).

The prohibitions are organised in three Allegati attached to the decree:

    Allegato A -- lavori vietati: absolute prohibitions, the worker MUST
                 be reassigned (or placed on mandatory early leave).
    Allegato B -- lavori vietati salvo deroga: prohibited unless a specific
                 risk assessment proves no residual risk.
    Allegato C -- agenti e condizioni per cui la lavoratrice non puo' essere
                 esposta senza valutazione specifica.

This module provides a keyword-based lookup table so the cross-reference
engine can match a worker's `mansione` (job title) against incompatible
risks. Matching is intentionally fuzzy: the engine lowercases the mansione
and checks whether any of the keywords appears as a substring. This is the
best we can do without a proper mansionario taxonomy; operators always
review the suggestions before persisting them.

See also:
    docs/context/LEGISLATION_REFERENCE.md (D.Lgs. 151/2001 entry)
    docs/context/DOCUMENT_STRUCTURE.md (Allegato Gestanti section)
"""

from __future__ import annotations

from typing import Literal, TypedDict

Allegato = Literal["A", "B", "C"]
RiskKey = str


class RiskInfo(TypedDict):
    allegato: Allegato
    descrizione: str
    incompatible_mansione_keywords: list[str]


# NOTE: keywords MUST be lowercase. The cross-reference engine compares
# against `mansione.lower()` using substring matching.
INCOMPATIBLE_RISKS: dict[RiskKey, RiskInfo] = {
    # ---- Allegato A (lavori vietati in gravidanza) ----
    "manual_handling_heavy": {
        "allegato": "A",
        "descrizione": (
            "Movimentazione manuale di carichi pesanti (> 3 kg) in modo ripetitivo "
            "o di carichi occasionali superiori ai limiti previsti da NIOSH per gestante."
        ),
        "incompatible_mansione_keywords": [
            "magazzinier",
            "facchin",
            "operai",
            "carrellista",
            "montat",
            "imballagg",
            "movimentazione",
        ],
    },
    "prolonged_standing": {
        "allegato": "A",
        "descrizione": (
            "Posizioni di lavoro prolungate in piedi o posture fisse per piu' di meta' "
            "dell'orario di lavoro (art. 7 e Allegato A lett. G)."
        ),
        "incompatible_mansione_keywords": [
            "commess",
            "cameriera",
            "cameriere",
            "barista",
            "cuoc",
            "aiuto cuoc",
            "parrucchier",
            "estetist",
            "cassier",
        ],
    },
    "night_shift": {
        "allegato": "A",
        "descrizione": (
            "Lavoro notturno (fascia 24:00 - 06:00) dall'accertamento della gravidanza "
            "fino al compimento di un anno di eta' del figlio (art. 53)."
        ),
        "incompatible_mansione_keywords": [
            "notturn",
            "infermier",
            "guardia",
            "vigilanz",
            "portier",
            "turnist",
        ],
    },
    "driving_heavy_vehicles": {
        "allegato": "A",
        "descrizione": (
            "Conduzione di mezzi di trasporto pesanti, carrelli elevatori e macchine "
            "operatrici con vibrazioni al corpo intero."
        ),
        "incompatible_mansione_keywords": [
            "autist",
            "camionist",
            "carrellista",
            "conducent",
            "mulettist",
        ],
    },
    "step_ladders_scaffolding": {
        "allegato": "A",
        "descrizione": (
            "Lavori su scale, impalcature, ponteggi e in generale in quota (Allegato A "
            "lett. E): rischio di caduta pregiudizievole per la gestante."
        ),
        "incompatible_mansione_keywords": [
            "imbianchin",
            "muratore",
            "edil",
            "antennist",
            "cantier",
            "tecnico di cantiere",
        ],
    },

    # ---- Allegato B (lavori vietati salvo deroga) ----
    "chemical_exposure_cmr": {
        "allegato": "B",
        "descrizione": (
            "Esposizione ad agenti chimici cancerogeni, mutageni o tossici per la "
            "riproduzione (CMR) classificati H340, H350, H360, H361 (Allegato B)."
        ),
        "incompatible_mansione_keywords": [
            "chimic",
            "verniciat",
            "saldat",
            "laborator",
            "galvani",
            "trattamenti super",
            "pittor",
            "resinator",
        ],
    },
    "ionizing_radiation": {
        "allegato": "B",
        "descrizione": (
            "Esposizione a radiazioni ionizzanti (raggi X, radioisotopi) — vietata "
            "per gestanti e allattamento (D.Lgs. 101/2020 e Allegato B)."
        ),
        "incompatible_mansione_keywords": [
            "radiolog",
            "radiograf",
            "tsrm",
            "tecnico di radiologia",
            "dentist",
            "odontotecnic",
            "medicina nuclear",
        ],
    },
    "biological_agents": {
        "allegato": "B",
        "descrizione": (
            "Esposizione ad agenti biologici del gruppo 2, 3 o 4 (toxoplasma, rosolia, "
            "CMV, HBV, HIV, TBC) salvo immunizzazione documentata (Allegato B lett. A.1)."
        ),
        "incompatible_mansione_keywords": [
            "infermier",
            "oss",
            "operatore socio sanitar",
            "medico",
            "dentist",
            "veterinar",
            "asilo",
            "educatric",
            "maestra",
            "insegnant",
            "laborator",
        ],
    },
    "hand_arm_vibrations": {
        "allegato": "B",
        "descrizione": (
            "Esposizione a vibrazioni meccaniche trasmesse al sistema mano-braccio "
            "(utensili ad impatto, trapani, mole) oltre i valori d'azione (Allegato B lett. B.2)."
        ),
        "incompatible_mansione_keywords": [
            "carpent",
            "edil",
            "muratore",
            "fabbro",
            "saldat",
            "tornit",
            "fresat",
        ],
    },

    # ---- Allegato C (agenti e condizioni -- valutazione specifica) ----
    "whole_body_vibrations": {
        "allegato": "C",
        "descrizione": (
            "Vibrazioni trasmesse al corpo intero (A(8) > 0.5 m/s^2): riduzione del "
            "flusso utero-placentare, aumento del rischio di aborto (Allegato C)."
        ),
        "incompatible_mansione_keywords": [
            "autist",
            "camionist",
            "trattorist",
            "mulettist",
            "carrellista",
        ],
    },
    "extreme_temperature": {
        "allegato": "C",
        "descrizione": (
            "Esposizione a temperature estreme (caldo severo > 30 C o freddo < 0 C) "
            "o microclima severo (Allegato C lett. A.2)."
        ),
        "incompatible_mansione_keywords": [
            "fonderia",
            "fonditore",
            "fornaio",
            "fornai",
            "cella frigorifera",
            "macellaio",
            "pescheria",
            "cuoc",
            "altoforno",
        ],
    },
    "noise_exposure": {
        "allegato": "C",
        "descrizione": (
            "Esposizione a rumore (L_ex,8h > 80 dB(A)): possibili effetti sul feto "
            "dopo la 20a settimana (Allegato C lett. A.3)."
        ),
        "incompatible_mansione_keywords": [
            "tornit",
            "fresat",
            "carpent",
            "saldat",
            "operai",
            "cantier",
            "imballaggi",
        ],
    },
    "psychophysical_fatigue": {
        "allegato": "C",
        "descrizione": (
            "Affaticamento mentale e fisico: ritmi serrati, lavoro a cottimo, "
            "catena di montaggio (art. 11 e Allegato C lett. F)."
        ),
        "incompatible_mansione_keywords": [
            "catena di montaggio",
            "operai di linea",
            "cottimo",
            "confezionament",
        ],
    },
    "pressurized_environments": {
        "allegato": "C",
        "descrizione": (
            "Lavori in ambienti iperbarici o in atmosfere con pressione diversa "
            "da quella atmosferica (Allegato C lett. A.1.c)."
        ),
        "incompatible_mansione_keywords": [
            "sommozzator",
            "palombar",
            "camera iperbaric",
        ],
    },
}


def find_matches_for_mansione(mansione: str) -> list[tuple[RiskKey, RiskInfo]]:
    """Return every catalog entry whose keywords overlap the given mansione.

    Matching is case-insensitive substring. The `mansione` is normalised to
    lowercase once and each keyword is tested with `in`. Duplicates are
    de-duplicated by risk_key so a mansione that matches two keywords of the
    same risk is reported once.
    """
    if not mansione:
        return []

    needle = mansione.lower()
    hits: list[tuple[RiskKey, RiskInfo]] = []
    for key, info in INCOMPATIBLE_RISKS.items():
        for kw in info["incompatible_mansione_keywords"]:
            if kw in needle:
                hits.append((key, info))
                break
    return hits


def has_any_incompatible_risk(mansione: str) -> bool:
    """Cheap boolean probe used to pick a suggested alternative mansione."""
    return len(find_matches_for_mansione(mansione)) > 0
