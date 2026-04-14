"""
INAIL Stress Lavoro-Correlato calculator.

Implements the "Metodo Indicatori Oggettivi" (Objective Indicators Method) per
INAIL guidelines. Three areas:

- Area A — Indicatori Aziendali (10 tripartite indicators)
  * Items 1-8: DIMINUITO=0, INALTERATO=1, AUMENTATO=4
  * Items 9-10: NO=0, SI=4 (binary, heavy)
  * Raw max: 40. Converted via band: 0-10 -> 0, 11-20 -> 2, 21-40 -> 5.

- Area B — Contesto del Lavoro (6 sub-areas, 30 binary indicators)
  * Normal scoring: SI=0 (positive present -> no stress), NO=1
  * Inverted scoring: SI=1 (negative present -> stress), NO=0
  * B6 special rule: if raw=0 insert -1 into total B, else 0

- Area C — Contenuto del Lavoro (4 sub-areas, 36 binary indicators)
  * Same SI/NO semantics as Area B

Final total = A_converted + B_total + C_total (max 67)
Bands: 0-17 BASSO, 18-34 MEDIO, 35-67 ALTO.

Reference: docs/context/REFERENCE_DATA.md section 3.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# -------------------------
# Indicator definitions
# -------------------------

ScoringMode = Literal[
    "tripartite",              # DIMINUITO=0, INALTERATO=1, AUMENTATO=4
    "binary_heavy",            # NO=0, SI=4 (Area A items 9-10)
    "binary",                  # SI=0, NO=1 (positive condition present)
    "binary_inverted",         # SI=1, NO=0 (negative condition present)
]

AreaCode = Literal["A", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "C4"]


class Indicator(TypedDict):
    id: str
    area: AreaCode
    text: str
    scoring: ScoringMode
    note: str  # Operator hint (may be empty)


INDICATORS: list[Indicator] = [
    # --- Area A — Indicatori Aziendali (10) ---
    {"id": "A.1",  "area": "A",  "scoring": "tripartite",   "note": "Se INALTERATO = 0 eventi, marcare DIMINUITO", "text": "Indici infortunistici"},
    {"id": "A.2",  "area": "A",  "scoring": "tripartite",   "note": "", "text": "Assenteismo (% ore assenza / ore lavorative)"},
    {"id": "A.3",  "area": "A",  "scoring": "tripartite",   "note": "", "text": "Assenza per malattia (escluso maternita, allattamento, congedo matrimoniale)"},
    {"id": "A.4",  "area": "A",  "scoring": "tripartite",   "note": "", "text": "% Ferie non godute"},
    {"id": "A.5",  "area": "A",  "scoring": "tripartite",   "note": "", "text": "% Rotazione del personale non programmata"},
    {"id": "A.6",  "area": "A",  "scoring": "tripartite",   "note": "Se INALTERATO = 0 eventi, marcare DIMINUITO", "text": "Cessazione rapporti di lavoro / turnover"},
    {"id": "A.7",  "area": "A",  "scoring": "tripartite",   "note": "Se INALTERATO = 0 eventi, marcare DIMINUITO", "text": "Procedimenti / sanzioni disciplinari"},
    {"id": "A.8",  "area": "A",  "scoring": "tripartite",   "note": "Se INALTERATO = 0 eventi, marcare DIMINUITO", "text": "Richieste visite mediche straordinarie dal medico competente"},
    {"id": "A.9",  "area": "A",  "scoring": "binary_heavy", "note": "", "text": "Segnalazioni scritte medico competente di condizioni stress al lavoro"},
    {"id": "A.10", "area": "A",  "scoring": "binary_heavy", "note": "", "text": "Istanze giudiziarie per licenziamento / demansionamento"},

    # --- B1 Funzione e Cultura Organizzativa (11) ---
    {"id": "B1.1",  "area": "B1", "scoring": "binary", "note": "", "text": "Diffusione organigramma aziendale"},
    {"id": "B1.2",  "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di procedure aziendali"},
    {"id": "B1.3",  "area": "B1", "scoring": "binary", "note": "", "text": "Diffusione delle procedure aziendali ai lavoratori"},
    {"id": "B1.4",  "area": "B1", "scoring": "binary", "note": "", "text": "Diffusione degli obiettivi aziendali ai lavoratori"},
    {"id": "B1.5",  "area": "B1", "scoring": "binary", "note": "", "text": "Sistema di gestione della sicurezza aziendale (certificazioni SA8000, BS OHSAS 18001:2007)"},
    {"id": "B1.6",  "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di un sistema di comunicazione aziendale (bacheca, internet, busta paga, volantini)"},
    {"id": "B1.7",  "area": "B1", "scoring": "binary", "note": "", "text": "Effettuazione riunioni / incontri tra dirigenti e lavoratori"},
    {"id": "B1.8",  "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di un piano formativo per la crescita professionale dei lavoratori"},
    {"id": "B1.9",  "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di momenti di comunicazione dell'azienda a tutto il personale"},
    {"id": "B1.10", "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di codice etico e di comportamento"},
    {"id": "B1.11", "area": "B1", "scoring": "binary", "note": "", "text": "Presenza di sistemi per il recepimento e la gestione dei casi di disagio lavorativo"},

    # --- B2 Ruolo nell'Ambito dell'Organizzazione (4) ---
    {"id": "B2.1", "area": "B2", "scoring": "binary",          "note": "", "text": "I lavoratori conoscono la linea gerarchica aziendale"},
    {"id": "B2.2", "area": "B2", "scoring": "binary",          "note": "", "text": "I ruoli sono chiaramente definiti"},
    {"id": "B2.3", "area": "B2", "scoring": "binary_inverted", "note": "", "text": "Vi e una sovrapposizione di ruoli differenti sulle stesse persone"},
    {"id": "B2.4", "area": "B2", "scoring": "binary_inverted", "note": "", "text": "Accade di frequente che dirigenti / preposti forniscano informazioni contrastanti"},

    # --- B3 Evoluzione della Carriera (3) ---
    {"id": "B3.1", "area": "B3", "scoring": "binary", "note": "", "text": "Sono definiti i criteri per l'avanzamento di carriera"},
    {"id": "B3.2", "area": "B3", "scoring": "binary", "note": "", "text": "Esistono sistemi premianti in relazione alla corretta gestione del personale"},
    {"id": "B3.3", "area": "B3", "scoring": "binary", "note": "", "text": "Esistono sistemi premianti in relazione al raggiungimento degli obiettivi di sicurezza"},

    # --- B4 Autonomia Decisionale / Controllo del Lavoro (5) ---
    {"id": "B4.1", "area": "B4", "scoring": "binary_inverted", "note": "", "text": "Il lavoro dipende da compiti precedentemente svolti da altri"},
    {"id": "B4.2", "area": "B4", "scoring": "binary",          "note": "", "text": "I lavoratori hanno sufficiente autonomia per l'esecuzione dei compiti"},
    {"id": "B4.3", "area": "B4", "scoring": "binary",          "note": "", "text": "I lavoratori hanno a disposizione le informazioni sulle decisioni aziendali"},
    {"id": "B4.4", "area": "B4", "scoring": "binary",          "note": "", "text": "Sono predisposti strumenti di partecipazione decisionale dei lavoratori"},
    {"id": "B4.5", "area": "B4", "scoring": "binary_inverted", "note": "", "text": "Sono presenti rigidi protocolli di supervisione sul lavoro svolto"},

    # --- B5 Rapporti Interpersonali sul Lavoro (3) ---
    {"id": "B5.1", "area": "B5", "scoring": "binary",          "note": "", "text": "Possibilita di comunicare con i dirigenti di grado superiore"},
    {"id": "B5.2", "area": "B5", "scoring": "binary",          "note": "", "text": "Vengono gestiti eventuali comportamenti prevaricatori o illeciti"},
    {"id": "B5.3", "area": "B5", "scoring": "binary_inverted", "note": "", "text": "Vi e la segnalazione frequente di conflitti / litigi"},

    # --- B6 Interfaccia Casa Lavoro / Conciliazione Vita-Lavoro (4) ---
    {"id": "B6.1", "area": "B6", "scoring": "binary", "note": "", "text": "Possibilita di effettuare la pausa pasto in luogo adeguato / mensa aziendale"},
    {"id": "B6.2", "area": "B6", "scoring": "binary", "note": "", "text": "Possibilita di orario flessibile"},
    {"id": "B6.3", "area": "B6", "scoring": "binary", "note": "", "text": "Possibilita di raggiungere il posto di lavoro con mezzi pubblici / navetta"},
    {"id": "B6.4", "area": "B6", "scoring": "binary", "note": "", "text": "Possibilita di svolgere lavoro part-time verticale / orizzontale"},

    # --- C1 Ambiente di Lavoro e Attrezzature (13) ---
    {"id": "C1.1",  "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Esposizione a rumore superiore al secondo livello d'azione"},
    {"id": "C1.2",  "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Inadeguato comfort acustico (ambiente non industriale)"},
    {"id": "C1.3",  "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Rischio cancerogeno / chimico non irrilevante"},
    {"id": "C1.4",  "area": "C1", "scoring": "binary",          "note": "", "text": "Microclima adeguato"},
    {"id": "C1.5",  "area": "C1", "scoring": "binary",          "note": "", "text": "Adeguato illuminamento (specie per attivita ad elevato impegno visivo)"},
    {"id": "C1.6",  "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Rischio movimentazione manuale dei carichi"},
    {"id": "C1.7",  "area": "C1", "scoring": "binary",          "note": "Se DPI non previsti, marcare SI", "text": "Disponibilita di adeguati e confortevoli DPI"},
    {"id": "C1.8",  "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Lavoro a rischio di aggressione fisica / lavoro solitario"},
    {"id": "C1.9",  "area": "C1", "scoring": "binary",          "note": "", "text": "Segnaletica di sicurezza chiara, immediata e pertinente ai rischi"},
    {"id": "C1.10", "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Esposizione a vibrazione superiore al limite d'azione"},
    {"id": "C1.11", "area": "C1", "scoring": "binary",          "note": "", "text": "Adeguata manutenzione macchine ed attrezzature"},
    {"id": "C1.12", "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Esposizione a radiazioni ionizzanti"},
    {"id": "C1.13", "area": "C1", "scoring": "binary_inverted", "note": "", "text": "Esposizione a rischio biologico"},

    # --- C2 Pianificazione dei Compiti (6) ---
    {"id": "C2.1", "area": "C2", "scoring": "binary_inverted", "note": "", "text": "Il lavoro subisce frequenti interruzioni"},
    {"id": "C2.2", "area": "C2", "scoring": "binary",          "note": "", "text": "Adeguatezza delle risorse strumentali necessarie"},
    {"id": "C2.3", "area": "C2", "scoring": "binary_inverted", "note": "", "text": "E presente un lavoro caratterizzato da alta monotonia"},
    {"id": "C2.4", "area": "C2", "scoring": "binary_inverted", "note": "", "text": "Lo svolgimento della mansione richiede di eseguire piu compiti contemporaneamente"},
    {"id": "C2.5", "area": "C2", "scoring": "binary",          "note": "", "text": "Chiara definizione dei compiti"},
    {"id": "C2.6", "area": "C2", "scoring": "binary",          "note": "", "text": "Adeguatezza delle risorse umane necessarie"},

    # --- C3 Carico di Lavoro / Ritmo (9) ---
    {"id": "C3.1", "area": "C3", "scoring": "binary",          "note": "", "text": "I lavoratori hanno autonomia nella esecuzione dei compiti"},
    {"id": "C3.2", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "Ci sono variazioni imprevedibili della quantita di lavoro"},
    {"id": "C3.3", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "Vi e assenza di compiti per lunghi periodi nel turno lavorativo"},
    {"id": "C3.4", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "E presente un lavoro caratterizzato da alta ripetitivita"},
    {"id": "C3.5", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "Il ritmo lavorativo per l'esecuzione del compito e prefissato"},
    {"id": "C3.6", "area": "C3", "scoring": "binary_inverted", "note": "Se macchine non previste, marcare NO", "text": "Il lavoratore non puo agire sul ritmo della macchina"},
    {"id": "C3.7", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "I lavoratori devono prendere decisioni rapide"},
    {"id": "C3.8", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "Lavoro con utilizzo di macchine ed attrezzature ad alto rischio"},
    {"id": "C3.9", "area": "C3", "scoring": "binary_inverted", "note": "", "text": "Lavoro con elevata responsabilita per terzi, impianti e produzione"},

    # --- C4 Orario di Lavoro (8) ---
    {"id": "C4.1", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "E presente regolarmente un orario lavorativo superiore alle 8 ore"},
    {"id": "C4.2", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "Viene abitualmente svolto lavoro straordinario"},
    {"id": "C4.3", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "E presente orario di lavoro rigido (non flessibile)"},
    {"id": "C4.4", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "La programmazione dell'orario varia frequentemente"},
    {"id": "C4.5", "area": "C4", "scoring": "binary",          "note": "", "text": "Le pause di lavoro non sono chiaramente definite"},
    {"id": "C4.6", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "E presente il lavoro a turni"},
    {"id": "C4.7", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "E presente il lavoro a turni notturni"},
    {"id": "C4.8", "area": "C4", "scoring": "binary_inverted", "note": "", "text": "E presente il turno notturno fisso o a rotazione"},
]

INDICATOR_BY_ID: dict[str, Indicator] = {ind["id"]: ind for ind in INDICATORS}

# -------------------------
# Area thresholds
# -------------------------

# Sub-area (B1..C4) -> (basso_max, medio_max, alto_max)
# Score <= basso_max -> BASSO; <= medio_max -> MEDIO; else ALTO.
SUBAREA_THRESHOLDS: dict[str, tuple[int, int, int]] = {
    "B1": (4, 7, 11),
    "B2": (1, 3, 4),
    "B3": (1, 2, 3),
    "B4": (1, 3, 5),
    "B5": (1, 2, 3),
    # B6 is handled via special rule (always contributes -1 or 0 to total B).
    "C1": (5, 9, 13),
    "C2": (2, 4, 6),
    "C3": (4, 7, 9),
    "C4": (2, 5, 8),
}

TOTALE_B_THRESHOLDS = (8, 17, 26)  # <=8 BASSO, <=17 MEDIO, else ALTO
TOTALE_C_THRESHOLDS = (13, 25, 36)
FINAL_THRESHOLDS = (17, 34, 67)    # <=17 BASSO, <=34 MEDIO, else ALTO


# -------------------------
# Scoring
# -------------------------


def _score_indicator(indicator: Indicator, answer: str) -> int:
    """Map a raw answer string to a numeric score for one indicator."""
    mode = indicator["scoring"]
    if mode == "tripartite":
        return {"DIMINUITO": 0, "INALTERATO": 1, "AUMENTATO": 4}[answer]
    if mode == "binary_heavy":
        return {"NO": 0, "SI": 4}[answer]
    if mode == "binary":
        return {"SI": 0, "NO": 1}[answer]
    if mode == "binary_inverted":
        return {"SI": 1, "NO": 0}[answer]
    raise ValueError(f"Unknown scoring mode {mode} for {indicator['id']}")


def _area_a_converted(raw: int) -> tuple[int, str]:
    """Convert raw Area A score (0-40) to (converted_score, livello)."""
    if raw <= 10:
        return 0, "BASSO"
    if raw <= 20:
        return 2, "MEDIO"
    return 5, "ALTO"


def _band(score: int, thresholds: tuple[int, int, int]) -> str:
    basso_max, medio_max, _ = thresholds
    if score <= basso_max:
        return "BASSO"
    if score <= medio_max:
        return "MEDIO"
    return "ALTO"


def _azione_per_livello(livello: str) -> str:
    if livello == "BASSO":
        return (
            "Nessun approfondimento richiesto. "
            "Monitoraggio periodico. Ripetere valutazione entro 2 anni."
        )
    if livello == "MEDIO":
        return (
            "Adottare azioni di miglioramento mirate. "
            "Se non si rileva miglioramento entro 1 anno, procedere al 2o livello "
            "(questionari di percezione lavoratori). Ripetere entro 2 anni."
        )
    return (
        "Procedere al 2o livello (valutazione percezione lavoratori). "
        "Verificare efficacia delle azioni entro 1 anno. Ripetere entro 2 anni."
    )


class StressSubAreaResult(TypedDict):
    score: int
    max: int
    livello: str


class StressCalculationResult(TypedDict):
    area_a_raw: int
    area_a_converted: int
    area_a_livello: str
    sub_areas_b: dict[str, StressSubAreaResult]
    area_b_total: int
    area_b_livello: str
    sub_areas_c: dict[str, StressSubAreaResult]
    area_c_total: int
    area_c_livello: str
    totale: int
    livello: str
    azione: str
    unanswered: list[str]


def calculate_stress(answers: dict[str, str]) -> StressCalculationResult:
    """Compute INAIL stress scoring from indicator answers.

    Args:
        answers: Mapping of indicator id (e.g. "A.1", "B1.3", "C4.8") to the
            operator's answer string. Expected values depend on scoring mode:
              - tripartite: "DIMINUITO" | "INALTERATO" | "AUMENTATO"
              - binary_heavy: "SI" | "NO"
              - binary / binary_inverted: "SI" | "NO"
            Missing or blank answers are reported in `unanswered`.

    Returns:
        StressCalculationResult with per-area breakdowns and the overall band.
    """
    unanswered: list[str] = []

    # Per-indicator scoring (skip unanswered so callers can see the final state
    # even when the assessment is incomplete)
    indicator_scores: dict[str, int] = {}
    for ind in INDICATORS:
        raw = answers.get(ind["id"])
        if not raw:
            unanswered.append(ind["id"])
            continue
        indicator_scores[ind["id"]] = _score_indicator(ind, raw)

    # --- Area A ---
    area_a_raw = sum(
        score for ind_id, score in indicator_scores.items() if ind_id.startswith("A.")
    )
    area_a_converted, area_a_livello = _area_a_converted(area_a_raw)

    # --- Area B sub-areas ---
    sub_areas_b: dict[str, StressSubAreaResult] = {}
    for sub in ("B1", "B2", "B3", "B4", "B5", "B6"):
        sub_indicators = [ind for ind in INDICATORS if ind["area"] == sub]
        score = sum(indicator_scores.get(ind["id"], 0) for ind in sub_indicators)
        max_score = len(sub_indicators)
        if sub == "B6":
            # Special rule: the SUB-AREA livello still follows thresholds
            # (conventionally treated as BASSO when raw is 0, else MEDIO/ALTO
            # by fraction), but the *contribution to Totale B* is -1 or 0.
            livello = "BASSO" if score == 0 else ("MEDIO" if score < max_score else "ALTO")
        else:
            livello = _band(score, SUBAREA_THRESHOLDS[sub])
        sub_areas_b[sub] = {"score": score, "max": max_score, "livello": livello}

    # Total B: B1-B5 raw + B6 normalized contribution.
    # B6 special rule: contributes -1 only when ALL 4 items are answered and
    # all are positive (raw=0). If the sub-area is partially unanswered, we
    # contribute 0 to avoid rewarding an incomplete assessment.
    b6_ids = {ind["id"] for ind in INDICATORS if ind["area"] == "B6"}
    b6_fully_answered = b6_ids.isdisjoint(unanswered)
    b6_contribution = -1 if (b6_fully_answered and sub_areas_b["B6"]["score"] == 0) else 0
    area_b_total = (
        sum(sub_areas_b[s]["score"] for s in ("B1", "B2", "B3", "B4", "B5"))
        + b6_contribution
    )
    area_b_livello = _band(max(area_b_total, 0), TOTALE_B_THRESHOLDS)

    # --- Area C sub-areas ---
    sub_areas_c: dict[str, StressSubAreaResult] = {}
    for sub in ("C1", "C2", "C3", "C4"):
        sub_indicators = [ind for ind in INDICATORS if ind["area"] == sub]
        score = sum(indicator_scores.get(ind["id"], 0) for ind in sub_indicators)
        max_score = len(sub_indicators)
        sub_areas_c[sub] = {
            "score": score,
            "max": max_score,
            "livello": _band(score, SUBAREA_THRESHOLDS[sub]),
        }

    area_c_total = sum(sub_areas_c[s]["score"] for s in ("C1", "C2", "C3", "C4"))
    area_c_livello = _band(area_c_total, TOTALE_C_THRESHOLDS)

    totale = area_a_converted + area_b_total + area_c_total
    livello = _band(max(totale, 0), FINAL_THRESHOLDS)

    return {
        "area_a_raw": area_a_raw,
        "area_a_converted": area_a_converted,
        "area_a_livello": area_a_livello,
        "sub_areas_b": sub_areas_b,
        "area_b_total": area_b_total,
        "area_b_livello": area_b_livello,
        "sub_areas_c": sub_areas_c,
        "area_c_total": area_c_total,
        "area_c_livello": area_c_livello,
        "totale": totale,
        "livello": livello,
        "azione": _azione_per_livello(livello),
        "unanswered": unanswered,
    }


# -------------------------
# Corrective measures (US-3.8)
# -------------------------

DEFAULT_MEASURES: dict[str, list[str]] = {
    "BASSO": [
        "Proseguire con le attivita di monitoraggio periodico dei principali indicatori aziendali (infortuni, assenteismo, turnover).",
        "Mantenere attive le procedure di comunicazione interna esistenti.",
        "Programmare la rivalutazione dello stress lavoro-correlato entro 2 anni.",
    ],
    "MEDIO": [
        "Istituire incontri periodici (trimestrali) tra dirigenti e lavoratori per raccogliere segnalazioni di disagio.",
        "Rivedere e diffondere procedure aziendali e organigramma, assicurandone la comprensione da parte di tutti i lavoratori.",
        "Introdurre o rafforzare strumenti di partecipazione decisionale (riunioni di team, suggerimenti strutturati).",
        "Pianificare formazione specifica su gestione del carico di lavoro e conciliazione vita-lavoro.",
        "Ripetere la valutazione oggettiva entro 12 mesi; se non migliora, procedere alla valutazione di percezione (2o livello).",
    ],
    "ALTO": [
        "Avviare immediatamente la valutazione di percezione dello stress (2o livello) tramite questionari anonimi ai lavoratori.",
        "Coinvolgere medico competente, RLS e RSPP in un piano straordinario di riduzione dello stress.",
        "Ridefinire compiti, ritmi e turnazione per abbattere le fonti di sovraccarico identificate nella checklist.",
        "Rafforzare i canali di segnalazione di conflitti e comportamenti prevaricatori e garantirne la gestione tempestiva.",
        "Verificare efficacia delle azioni correttive entro 12 mesi; monitoraggio continuo degli indicatori aziendali.",
    ],
}


def get_default_measures(livello: str) -> list[str]:
    """Return the suggested corrective measures for a given risk level."""
    return list(DEFAULT_MEASURES.get(livello, []))
