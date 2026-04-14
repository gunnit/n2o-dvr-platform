"""
Risk calculation engine for Italian workplace safety assessments.

Implements the following calculation methods:
- Risk Index: I = 2*D + P (DVR Master formula)
- NIOSH PLR/IR: Manual handling risk assessment
- Fire Risk: INF + SI + PI composite scoring
"""

from typing import Any

from app.services.reference_data import (
    DEFAULT_RISK_SCORES,
    get_default_scores,
)


def calculate_risk_index(p: int, d: int) -> dict:
    """Calculate the DVR risk index using the formula I = 2*D + P.

    This is NOT the standard P x D formula. N2O's DVR Master uses I = P + 2*D,
    giving heavier weight to the severity of damage (D).

    Args:
        p: Probabilita (1-4). 1=Bassa, 2=Medio Bassa, 3=Medio Alta, 4=Elevata.
        d: Danno (1-4). 1=Trascurabile, 2=Modesta, 3=Notevole, 4=Ingente.

    Returns:
        dict with keys:
            - probabilita_p: the P value
            - danno_d: the D value
            - indice_i: the computed index (range 3-12)
            - livello_rischio: risk level string
            - azione: recommended action description
            - tempistica: timeframe for action
    """
    if not (1 <= p <= 4):
        raise ValueError(f"Probabilita (P) must be 1-4, got {p}")
    if not (1 <= d <= 4):
        raise ValueError(f"Danno (D) must be 1-4, got {d}")

    indice = 2 * d + p

    if indice <= 4:
        livello = "ACCETTABILE"
        azione = (
            "Instaurare un sistema di verifica che consenta di mantenere "
            "nel tempo le condizioni di sicurezza preventivate"
        )
        tempistica = "Monitoraggio continuo"
    elif indice <= 6:
        livello = "MODESTO"
        azione = (
            "Predisporre gli strumenti necessari a minimizzare il rischio "
            "ed a verificare la efficacia delle azioni preventivate"
        )
        tempistica = "1 anno"
    elif indice <= 8:
        livello = "GRAVE"
        azione = (
            "Sensibilizzazione del personale. Controllo attuazione misure "
            "di prevenzione. Ricerca di ulteriori misure tecnico-organizzative"
        )
        tempistica = "6 mesi"
    else:
        livello = "GRAVISSIMO"
        azione = (
            "Sensibilizzazione del personale. Controllo attuazione misure. "
            "Ricerca urgente di ulteriori misure"
        )
        tempistica = "Immediatamente"

    return {
        "probabilita_p": p,
        "danno_d": d,
        "indice_i": indice,
        "livello_rischio": livello,
        "azione": azione,
        "tempistica": tempistica,
    }


def calculate_niosh(
    cp: float,
    a: float,
    b: float,
    c: float,
    d: float,
    e: float,
    f: float,
    peso_reale: float,
) -> dict:
    """Calculate the NIOSH Lifting Index for manual handling risk.

    Formula: PLR = CP x A x B x C x D x E x F
    Risk Index: IR = peso_reale / PLR

    Args:
        cp: Costante di Peso (weight constant). Males >18: 25kg, Females >18: 20kg.
        a: Fattore Altezza (height factor, 0.0-1.0).
        b: Fattore Dislocazione Verticale (vertical displacement factor, 0.0-1.0).
        c: Fattore Orizzontale (horizontal distance factor, 0.0-1.0).
        d: Fattore Dislocazione Angolare (asymmetry factor, 0.0-1.0).
        e: Fattore Presa (grip quality factor, 0.0-1.0).
        f: Fattore Frequenza (frequency factor, 0.0-1.0).
        peso_reale: Actual weight lifted in kg.

    Returns:
        dict with keys:
            - plr: Peso Limite Raccomandato (recommended weight limit in kg)
            - ir: Indice di Rischio (risk index)
            - area_rischio: risk zone (VERDE/GIALLA/ROSSA)
            - descrizione: description of the risk zone
            - azione: recommended action
    """
    if peso_reale < 0:
        raise ValueError(f"peso_reale must be >= 0, got {peso_reale}")

    factors = {"cp": cp, "a": a, "b": b, "c": c, "d": d, "e": e, "f": f}
    for name, value in factors.items():
        if value < 0:
            raise ValueError(f"Factor {name} must be >= 0, got {value}")

    plr = cp * a * b * c * d * e * f

    if plr <= 0:
        # If any factor is zero, PLR is zero and lifting is not recommended
        return {
            "plr": 0.0,
            "ir": float("inf"),
            "area_rischio": "ROSSA",
            "descrizione": "Sollevamento non raccomandato (fattore limitante a zero)",
            "azione": (
                "Intervento di prevenzione primaria: riprogettazione "
                "postazioni, riduzione carichi, ausili meccanici"
            ),
        }

    ir = round(peso_reale / plr, 3)

    if ir <= 0.75:
        area = "VERDE"
        descrizione = "Situazione accettabile"
        azione = "Nessun intervento specifico richiesto"
    elif ir <= 1.0:
        area = "GIALLA"
        descrizione = (
            "Situazione si avvicina ai limiti; "
            "1-10% della popolazione potrebbe essere a rischio"
        )
        azione = (
            "Attivare sorveglianza sanitaria, formazione specifica, "
            "interventi strutturali"
        )
    else:
        area = "ROSSA"
        descrizione = "Rischio per quote crescenti di popolazione"
        azione = (
            "Intervento di prevenzione primaria: riprogettazione "
            "postazioni, riduzione carichi, ausili meccanici"
        )

    return {
        "plr": round(plr, 2),
        "ir": ir,
        "area_rischio": area,
        "descrizione": descrizione,
        "azione": azione,
    }


def calculate_fire_risk(inf: int, si: int, pi: int) -> dict:
    """Calculate composite fire risk level.

    Each component is scored 1-3:
    - INF: Infiammabilita (flammability)
    - SI: Sorgenti di Innesco (ignition sources)
    - PI: Propagazione Incendio (fire propagation)

    Total = INF + SI + PI (range 3-9)

    Args:
        inf: Flammability score (1-3).
        si: Ignition sources score (1-3).
        pi: Fire propagation score (1-3).

    Returns:
        dict with keys:
            - inf: flammability score
            - si: ignition sources score
            - pi: fire propagation score
            - totale: sum of the three components
            - livello: risk level (Basso/Medio/Alto)
    """
    for name, value in [("inf", inf), ("si", si), ("pi", pi)]:
        if not (1 <= value <= 3):
            raise ValueError(f"{name} must be 1-3, got {value}")

    totale = inf + si + pi

    if totale <= 4:
        livello = "Basso"
    elif totale <= 7:
        livello = "Medio"
    else:
        livello = "Alto"

    return {
        "inf": inf,
        "si": si,
        "pi": pi,
        "totale": totale,
        "livello": livello,
    }


def get_default_risk_matrix() -> dict[tuple[str, str], tuple[int, int]]:
    """Return the full default (ambiente_tipo, categoria) -> (P, D) matrix.

    Thin wrapper over the reference_data lookup so callers that already
    import risk_calculator do not need a second import.
    """
    return dict(DEFAULT_RISK_SCORES)


def apply_default_scores_to_valutazioni(
    ambiente_tipo: str, valutazioni: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply default P/D scores to valutazioni that still carry the initial 1/1.

    Iterates over the list, and for every valutazione where both probabilita_p
    and danno_d are 1 (the wizard's initial value), overwrites them with the
    matrix default for the given (ambiente_tipo, categoria_rischio) pair and
    recomputes indice_i / livello_rischio. Other rows are left untouched so
    operator edits are preserved.

    Args:
        ambiente_tipo: Environment tipo (e.g. "ufficio").
        valutazioni: List of dicts with at least keys "categoria_rischio",
            "probabilita_p", "danno_d".

    Returns:
        A new list with the updated dicts (input list is not mutated).
    """
    updated: list[dict[str, Any]] = []
    for val in valutazioni:
        new_val = dict(val)
        current_p = new_val.get("probabilita_p") or 1
        current_d = new_val.get("danno_d") or 1
        if current_p == 1 and current_d == 1:
            categoria = new_val.get("categoria_rischio", "")
            p_def, d_def = get_default_scores(ambiente_tipo, categoria)
            new_val["probabilita_p"] = p_def
            new_val["danno_d"] = d_def
            computed = calculate_risk_index(p_def, d_def)
            new_val["indice_i"] = computed["indice_i"]
            new_val["livello_rischio"] = computed["livello_rischio"]
        updated.append(new_val)
    return updated
