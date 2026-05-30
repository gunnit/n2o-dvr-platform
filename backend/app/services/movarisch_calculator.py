"""
MoVaRisCh chemical-risk calculator (Regioni Toscana, Emilia-Romagna, Lombardia).

Implements the model required by art. 223 c.1 D.Lgs. 81/08 (Titolo IX Capo I),
as used in N2O's "Allegato Rischio Chimico". Health risk:

    R = P x E
      Rinal = P x Einal           (inhalation)
      Rcute = P x Ecute           (dermal)
      Rcum  = sqrt(Rinal^2 + Rcute^2)   (when both routes apply)

- P  = highest hazard score among the substance's H-phrases (CLP 1272/2008)
       or legacy R-phrases. Carcinogens/mutagens (H340/H350/H351, R45/46/49)
       fall under Titolo IX Capo II and are flagged, not scored.
- Einal = I x d, where I is built through 4 cascading matrices
  (D -> U -> C -> I) and d scales by distance from source.
- Ecute from a single matrix (tipologia d'uso x livello contatto cutaneo).
- Health zones: VERDE / ARANCIO / GIALLO / ROSSA / NERA.
- Safety level ("rischio per la sicurezza"): Basso | Non Basso, worst across
  the substance's H-codes.

CORRECT-RULE NOTE (see docs/context/RISCHIO_CHIMICO_MAPPING.md sec. 4):
The source documents were produced by a third-party tool that emits D=0 ->
Einal=0 (and sometimes d=0) whenever the physical state was left as the generic
"Liquido" instead of one of the four documented volatility tiers. That zeroes
the inhalation route and contradicts the model's own stated range
(0.1 <= Rinal <= 100). This module implements the model-correct behaviour:
every physical state resolves to a real availability tier and Einal = I x d is
always > 0. The caller (AI suggester / operator) is responsible for classifying
a liquid as "Bassa Volatilità" or "Media / Alta volatilità" from the SDS.

Reference data: app/data/movarisch_reference.json (parsed verbatim from the
templates, not hand-typed). All option strings below match the seed exactly.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "movarisch_reference.json"

# --- Documented option sets (must match movarisch_reference.json -> matrices) ---
ProprietaFisiche = Literal[
    "Solido - Nebbia",
    "Bassa Volatilità",
    "Media / Alta volatilità e Polveri fini",
    "Stato gassoso",
]
QuantitaClasse = Literal["< 0,1 Kg", "0,1 - 1 Kg", "1 - 10 Kg", "10 - 100 Kg", ">= 100 Kg"]
TipologiaUso = Literal[
    "Sistema chiuso", "Inclusione in matrice", "Uso controllato", "Uso dispersivo"
]
TipologiaControllo = Literal[
    "Contenimento completo",
    "Aspirazione localizzata",
    "Segregazione / Separazione",
    "Ventilazione generale",
    "Manipolazione diretta",
]
TempoEsposizione = Literal[
    "< 15 minuti", "15 min - 2 ore", "2 - 4 ore", "4 - 6 ore", ">= 6 ore"
]
DistanzaClasse = Literal["< 1 m", "1 - 3 m", "3 - 5 m", "5 - 10 m", ">= 10 m"]
ContattoCutaneo = Literal[
    "Nessun contatto", "Contatto accidentale", "Contatto discontinuo", "Contatto esteso"
]
LivelloSalute = Literal["Irrilevante", "Superiore"]
ZonaSalute = Literal["VERDE", "ARANCIO", "GIALLO", "ROSSA", "NERA"]
LivelloSicurezza = Literal["Basso", "Non Basso"]


@lru_cache(maxsize=1)
def _ref() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


# Order of the matrix columns/rows (index positions matter — they map the option
# string to its column/row in the JSON matrices).
_QUANTITA_ORDER: list[str] = ["< 0,1 Kg", "0,1 - 1 Kg", "1 - 10 Kg", "10 - 100 Kg", ">= 100 Kg"]
_CHEMPHYS_ORDER: list[str] = [
    "Solido - Nebbia",
    "Bassa Volatilità",
    "Media / Alta volatilità e Polveri fini",
    "Stato gassoso",
]
_USO_ORDER: list[str] = [
    "Sistema chiuso", "Inclusione in matrice", "Uso controllato", "Uso dispersivo"
]
_CONTROLLO_ORDER: list[str] = [
    "Contenimento completo",
    "Aspirazione localizzata",
    "Segregazione / Separazione",
    "Ventilazione generale",
    "Manipolazione diretta",
]
_TEMPO_ORDER: list[str] = ["< 15 minuti", "15 min - 2 ore", "2 - 4 ore", "4 - 6 ore", ">= 6 ore"]
_DISTANZA_ORDER: list[str] = ["< 1 m", "1 - 3 m", "3 - 5 m", "5 - 10 m", ">= 10 m"]
_CONTATTO_ORDER: list[str] = [
    "Nessun contatto", "Contatto accidentale", "Contatto discontinuo", "Contatto esteso"
]

# Distance class -> d factor (documented; never 0).
_D_FACTOR: dict[str, float] = {
    "< 1 m": 1.0, "1 - 3 m": 0.75, "3 - 5 m": 0.5, "5 - 10 m": 0.25, ">= 10 m": 0.1
}

# Leading-code extractor for a phrase string like "H317 cat.1B - testo" or "R36/38 - testo".
_CODE_RE = re.compile(r"^\s*(EUH\d+[A-Za-z]?|H\d{3}(?:\s*cat\.?\s*\w+)?|R\d+(?:/\d+)*)", re.IGNORECASE)


# ----------------------------------------------------------------------------
# P — Indice di pericolosità
# ----------------------------------------------------------------------------

class PScoreResult(TypedDict):
    p: float
    governing_code: str | None
    is_cancerogeno: bool
    matched: list[str]
    unmatched: list[str]


def _extract_code(frase: str) -> str:
    """Return the leading hazard code of a phrase string, normalised.

    "H317 cat.1B - Può..." -> "H317 cat.1B" ; "R36/38 - ..." -> "R36/38".
    If the string is already a bare code it is returned as-is.
    """
    m = _CODE_RE.match(frase or "")
    if not m:
        return (frase or "").strip()
    code = m.group(1).strip()
    # Normalise "cat .1B" / "cat1B" spacing to "cat.1B"
    code = re.sub(r"cat\.?\s*", "cat.", code, flags=re.IGNORECASE)
    code = re.sub(r"\s+", " ", code)
    # Canonical case: H/EUH upper, keep category letter case as-is.
    if code[:1].lower() in ("h", "r", "e"):
        head = re.match(r"^[A-Za-z]+", code).group(0)
        code = head.upper() + code[len(head):]
    return code


def _lookup_h(code: str) -> tuple[float | None, bool, bool]:
    """Look up an H/EUH code. Returns (score, found, is_cancerogeno).

    Exact match first; for a bare code without category (e.g. "H300") that only
    exists with categories in the table, take the highest-scoring variant
    (conservative).
    """
    table: dict = _ref()["p_scores_h"]
    if code in table:
        sc = table[code]["score"]
        return _coerce(sc)
    # bare code -> category variants
    variants = [k for k in table if k == code or k.startswith(code + " ")]
    if variants:
        best, canc = None, False
        for k in variants:
            s, found, c = _coerce(table[k]["score"])
            canc = canc or c
            if s is not None and (best is None or s > best):
                best = s
        return best, True, canc
    return None, False, False


def _lookup_r(code: str) -> tuple[float | None, bool, bool]:
    """Look up a legacy R-phrase. JSON keys have no 'R' prefix (e.g. '36/38')."""
    table: dict = _ref()["p_scores_r"]
    key = code[1:] if code[:1].upper() == "R" else code
    if key in table:
        return _coerce(table[key]["score"])
    return None, False, False


def _coerce(score) -> tuple[float | None, bool, bool]:
    """(value, found, is_cancerogeno) from a raw seed score cell."""
    if isinstance(score, str) and score.upper().startswith("CANCEROG"):
        return None, True, True
    if isinstance(score, (int, float)):
        return float(score), True, False
    return None, False, False


def p_score(frasi: list[str]) -> PScoreResult:
    """Compute the hazard index P = highest score among the substance's phrases.

    - Carcinogen/mutagen codes are flagged (Titolo IX Capo II) and excluded from
      the numeric maximum.
    - Unclassified / non-hazardous substances floor at P = 1.0 (model minimum).
    """
    best: float | None = None
    governing: str | None = None
    is_canc = False
    matched: list[str] = []
    unmatched: list[str] = []

    for frase in frasi or []:
        code = _extract_code(frase)
        if not code:
            continue
        head = code[:1].upper()
        if head == "R" and not _ref()["p_scores_h"].get(code):
            score, found, canc = _lookup_r(code)
        else:
            score, found, canc = _lookup_h(code)
            if not found:  # some sheets list R-codes without the analyst tagging them H
                score, found, canc = _lookup_r(code)
        if not found:
            unmatched.append(code)
            continue
        matched.append(code)
        is_canc = is_canc or canc
        if score is not None and (best is None or score > best):
            best, governing = score, code

    p = best if best is not None else 1.0
    return {
        "p": p,
        "governing_code": governing,
        "is_cancerogeno": is_canc,
        "matched": matched,
        "unmatched": unmatched,
    }


# ----------------------------------------------------------------------------
# Einal — inhalation exposure (I x d)
# ----------------------------------------------------------------------------

class EinalResult(TypedDict):
    d_ind: int
    u_ind: int
    c_ind: int
    i_ind: int
    d_factor: float
    einal: float


def einal(
    proprieta_fisiche: ProprietaFisiche,
    quantita: QuantitaClasse,
    tipologia_uso: TipologiaUso,
    tipologia_controllo: TipologiaControllo,
    tempo_esposizione: TempoEsposizione,
    distanza: DistanzaClasse,
) -> EinalResult:
    """Einal = I x d via the 4 documented matrices. Always > 0 (correct rule)."""
    m = _ref()["matrices"]
    cp_i = _CHEMPHYS_ORDER.index(proprieta_fisiche)
    q_i = _QUANTITA_ORDER.index(quantita)
    d_lbl = m["M1_to_D"][cp_i][q_i]
    d_ind = int(m["D_values"][d_lbl])

    u_lbl = m["M2_to_U"][d_ind - 1][_USO_ORDER.index(tipologia_uso)]
    u_ind = int(m["U_values"][u_lbl])

    c_lbl = m["M3_to_C"][u_ind - 1][_CONTROLLO_ORDER.index(tipologia_controllo)]
    c_ind = int(m["C_values"][c_lbl])

    i_lbl = m["M4_to_I"][c_ind - 1][_TEMPO_ORDER.index(tempo_esposizione)]
    i_ind = int(m["I_values"][i_lbl])

    d_factor = _D_FACTOR[distanza]
    return {
        "d_ind": d_ind,
        "u_ind": u_ind,
        "c_ind": c_ind,
        "i_ind": i_ind,
        "d_factor": d_factor,
        "einal": round(i_ind * d_factor, 4),
    }


# ----------------------------------------------------------------------------
# Ecute — dermal exposure
# ----------------------------------------------------------------------------

class EcuteResult(TypedDict):
    label: str
    ecute: int


def ecute(tipologia_uso: TipologiaUso, contatto_cutaneo: ContattoCutaneo) -> EcuteResult:
    m = _ref()["matrices"]
    label = m["ECUTE_matrix"][_USO_ORDER.index(tipologia_uso)][_CONTATTO_ORDER.index(contatto_cutaneo)]
    return {"label": label, "ecute": int(m["Ecute_values"][label])}


# ----------------------------------------------------------------------------
# Health classification + cumulative risk
# ----------------------------------------------------------------------------

def classify_salute(r: float) -> tuple[ZonaSalute, LivelloSalute]:
    """Map governing R to (zona, livello).

    Boundaries per the documented criterion. The template prints "0,1<=R<15"
    (VERDE) and "15<R<21" (ARANCIO); R exactly 15 is assigned to ARANCIO — the
    conservative choice — to close the literal gap.
    """
    if r < 15:
        return "VERDE", "Irrilevante"
    if r < 21:
        return "ARANCIO", "Irrilevante"
    if r <= 40:
        return "GIALLO", "Superiore"
    if r <= 80:
        return "ROSSA", "Superiore"
    return "NERA", "Superiore"


# ----------------------------------------------------------------------------
# Safety level (rischio per la sicurezza)
# ----------------------------------------------------------------------------

class SafetyResult(TypedDict):
    livello: LivelloSicurezza
    unresolved: list[str]  # legacy R-codes (table is H-keyed) needing review


def safety_level(frasi: list[str]) -> SafetyResult:
    """'Non Basso' if any H-code is Non Basso, else 'Basso'.

    The documented safety table is keyed by H-codes only. Legacy R-only phrases
    cannot be resolved here and are returned in `unresolved` for operator review
    (modern CLP substances always carry H-codes, so this is a legacy edge case).
    """
    table: dict = _ref()["safety_level_by_code"]
    livello: LivelloSicurezza = "Basso"
    unresolved: list[str] = []
    for frase in frasi or []:
        code = _extract_code(frase)
        if not code:
            continue
        if code in table:
            if table[code] == "Non Basso":
                livello = "Non Basso"
        else:
            # bare H-code -> category variants
            variants = [k for k in table if k.startswith(code + " ")]
            if variants:
                if any(table[k] == "Non Basso" for k in variants):
                    livello = "Non Basso"
            elif code[:1].upper() == "R":
                unresolved.append(code)
    return {"livello": livello, "unresolved": unresolved}


# ----------------------------------------------------------------------------
# Full per-substance assessment (one scheda di rischio)
# ----------------------------------------------------------------------------

class SchedaResult(TypedDict):
    p: float
    governing_code: str | None
    is_cancerogeno: bool
    einal: float
    rinal: float
    ecute: int | None
    rcute: float | None
    rcum: float
    r_governing: float
    zona: ZonaSalute
    livello_salute: LivelloSalute
    livello_sicurezza: LivelloSicurezza
    indicators: EinalResult
    unmatched_codes: list[str]
    sicurezza_unresolved: list[str]


def assess(
    frasi: list[str],
    proprieta_fisiche: ProprietaFisiche,
    quantita: QuantitaClasse,
    tipologia_uso: TipologiaUso,
    tipologia_controllo: TipologiaControllo,
    tempo_esposizione: TempoEsposizione,
    distanza: DistanzaClasse,
    via_cutanea_applicabile: bool,
    contatto_cutaneo: ContattoCutaneo = "Nessun contatto",
) -> SchedaResult:
    """Compute a full chemical-risk scheda for one (worker x substance) exposure.

    `via_cutanea_applicabile` should be True when an H/R phrase indicates a
    dermal hazard, the SDS notes skin absorption, an OEL carries a 'pelle/skin'
    notation, or direct contact is possible (art. usage). When True the dermal
    route is included and the governing risk is Rcum; otherwise R = Rinal.
    """
    ps = p_score(frasi)
    p = ps["p"]
    e = einal(
        proprieta_fisiche, quantita, tipologia_uso, tipologia_controllo,
        tempo_esposizione, distanza,
    )
    rinal = round(p * e["einal"], 4)

    ecute_val: int | None = None
    rcute: float | None = None
    if via_cutanea_applicabile:
        ec = ecute(tipologia_uso, contatto_cutaneo)
        ecute_val = ec["ecute"]
        rcute = round(p * ecute_val, 4)
        rcum = round(math.sqrt(rinal**2 + rcute**2), 4)
        r_governing = rcum
    else:
        rcum = rinal
        r_governing = rinal

    zona, livello = classify_salute(r_governing)
    sic = safety_level(frasi)

    return {
        "p": p,
        "governing_code": ps["governing_code"],
        "is_cancerogeno": ps["is_cancerogeno"],
        "einal": e["einal"],
        "rinal": rinal,
        "ecute": ecute_val,
        "rcute": rcute,
        "rcum": rcum,
        "r_governing": r_governing,
        "zona": zona,
        "livello_salute": livello,
        "livello_sicurezza": sic["livello"],
        "indicators": e,
        "unmatched_codes": ps["unmatched"],
        "sicurezza_unresolved": sic["unresolved"],
    }
