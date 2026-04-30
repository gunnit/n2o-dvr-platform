"""NIOSH factor lookup tables (ISO 11228-1 / D.Lgs. 81/2008 Allegato XXXIII).

Single source of truth for the multipliers that compose `PLR = CP * A * B * C * D * E * F`.
The frontend used to hardcode these arrays in `mmc-form.tsx`; the calculator
endpoint and document generator now both import from here so the math agrees
across surfaces. See docs/context/REFERENCE_DATA.md §1 for the source tables.
"""

from __future__ import annotations

from typing import Literal


# Linear interpolation between adjacent rows of a sorted [(input, multiplier)] table.
def _interp(table: list[tuple[float, float]], x: float) -> float:
    if not table:
        return 1.0
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


# ---------------------------------------------------------------------------
# Factor A — Altezza da terra delle mani all'inizio del sollevamento (cm)
#   Optimal V = 75 cm (knuckle height) → A = 1.00
#   Formula: A = 1 - 0.003 * |V - 75|, with V > 175 → A = 0
# ---------------------------------------------------------------------------
FACTOR_A: list[tuple[float, float]] = [
    (0, 0.78),
    (25, 0.85),
    (50, 0.93),
    (75, 1.00),
    (100, 0.93),
    (125, 0.85),
    (150, 0.78),
    (175, 0.00),
]


def factor_a(altezza_cm: float) -> float:
    """Multiplier for vertical hand height at lift origin."""
    return _interp(FACTOR_A, max(0.0, altezza_cm))


# ---------------------------------------------------------------------------
# Factor B — Dislocazione verticale del peso fra inizio e fine (cm)
# ---------------------------------------------------------------------------
FACTOR_B: list[tuple[float, float]] = [
    (25, 1.00),
    (30, 0.97),
    (40, 0.93),
    (50, 0.91),
    (70, 0.88),
    (100, 0.87),
    (170, 0.85),
    (175, 0.00),
]


def factor_b(dislocazione_cm: float) -> float:
    return _interp(FACTOR_B, max(0.0, dislocazione_cm))


# ---------------------------------------------------------------------------
# Factor C — Distanza orizzontale tra mani e caviglie (cm)
# ---------------------------------------------------------------------------
FACTOR_C: list[tuple[float, float]] = [
    (25, 1.00),
    (30, 0.83),
    (40, 0.63),
    (50, 0.50),
    (55, 0.45),
    (60, 0.42),
    (63, 0.00),
]


def factor_c(distanza_cm: float) -> float:
    return _interp(FACTOR_C, max(0.0, distanza_cm))


# ---------------------------------------------------------------------------
# Factor D — Angolo di asimmetria (gradi)
# ---------------------------------------------------------------------------
FACTOR_D: list[tuple[float, float]] = [
    (0, 1.00),
    (30, 0.90),
    (60, 0.81),
    (90, 0.71),
    (120, 0.62),
    (135, 0.57),
    (180, 0.00),
]


def factor_d(angolo_gradi: float) -> float:
    return _interp(FACTOR_D, max(0.0, angolo_gradi))


# ---------------------------------------------------------------------------
# Factor E — Giudizio sulla presa
# ---------------------------------------------------------------------------
GiudizioPresa = Literal["Buono", "Discreto", "Scarso"]

FACTOR_E: dict[str, float] = {
    "Buono": 1.00,
    "Discreto": 0.95,
    "Scarso": 0.90,
}


def factor_e(giudizio: str) -> float:
    return FACTOR_E.get(giudizio.strip().capitalize(), 0.90)


# ---------------------------------------------------------------------------
# Factor F — Frequenza dei gesti × durata del lavoro
#
# Rows: actions per minute. Columns: duration band in minutes.
#   Breve durata (<60 min)
#   Media durata (60-120 min)
#   Lunga durata (>120 min, up to 8h)
# Per REFERENCE_DATA.md §1.7. Linear interpolation on the row axis.
# ---------------------------------------------------------------------------
DurataBand = Literal["breve", "media", "lunga"]

# Each row: (actions_per_min, F_breve, F_media, F_lunga)
FACTOR_F_TABLE: list[tuple[float, float, float, float]] = [
    (0.2, 1.00, 0.95, 0.85),
    (0.5, 0.97, 0.92, 0.81),
    (1, 0.94, 0.88, 0.75),
    (2, 0.91, 0.84, 0.65),
    (3, 0.88, 0.79, 0.55),
    (4, 0.84, 0.72, 0.45),
    (5, 0.80, 0.60, 0.35),
    (6, 0.75, 0.50, 0.27),
    (7, 0.70, 0.42, 0.22),
    (8, 0.60, 0.35, 0.18),
    (9, 0.52, 0.30, 0.15),
    (10, 0.45, 0.26, 0.13),
    (11, 0.41, 0.23, 0.00),
    (12, 0.37, 0.21, 0.00),
    (13, 0.34, 0.00, 0.00),
    (14, 0.31, 0.00, 0.00),
    (15, 0.28, 0.00, 0.00),
    (16, 0.00, 0.00, 0.00),  # >15 actions/min → 0 in every band
]


def durata_band(durata_min: float) -> DurataBand:
    """Map lifting duration in minutes to the F-table band."""
    if durata_min < 60:
        return "breve"
    if durata_min <= 120:
        return "media"
    return "lunga"


def factor_f(frequenza_atti_min: float, durata_min: float) -> float:
    """Lookup F = f(frequency, duration). Saturates above 15 actions/min."""
    if frequenza_atti_min <= 0:
        return 1.0
    band = durata_band(durata_min)
    col = {"breve": 1, "media": 2, "lunga": 3}[band]
    rows = [(r[0], r[col]) for r in FACTOR_F_TABLE]
    return _interp(rows, frequenza_atti_min)


# ---------------------------------------------------------------------------
# Composite calculation helpers
# ---------------------------------------------------------------------------


def compute_plr(
    cp: float,
    altezza_cm: float,
    dislocazione_cm: float,
    distanza_cm: float,
    angolo_gradi: float,
    giudizio_presa: str,
    frequenza_atti_min: float,
    durata_min: float,
) -> dict[str, float]:
    """Return all six factors + PLR, rounded to 2/4 decimals respectively.

    Useful at generation time so the doc shows both inputs and multipliers.
    """
    a = factor_a(altezza_cm)
    b = factor_b(dislocazione_cm)
    c = factor_c(distanza_cm)
    d = factor_d(angolo_gradi)
    e = factor_e(giudizio_presa)
    f = factor_f(frequenza_atti_min, durata_min)
    plr = cp * a * b * c * d * e * f
    return {
        "fattore_a": round(a, 2),
        "fattore_b": round(b, 2),
        "fattore_c": round(c, 2),
        "fattore_d": round(d, 2),
        "fattore_e": round(e, 2),
        "fattore_f": round(f, 2),
        "plr": round(plr, 4),
    }


def classify_ir(ir: float) -> str:
    """Return VERDE / GIALLO / ROSSO per NIOSH thresholds."""
    if ir <= 0.75:
        return "VERDE"
    if ir <= 1.0:
        return "GIALLO"
    return "ROSSO"
