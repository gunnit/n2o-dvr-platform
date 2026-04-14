"""
Microclima (thermal comfort / thermal stress) calculator.

Wraps the `pythermalcomfort` library (v3.x API) to compute:

- PMV/PPD per ISO 7730:2006 — comfort zones for normal indoor environments.
- PHS per ISO 7933:2023 — predicted heat strain for severe heat exposure.

The library's 3.x API exposes `pythermalcomfort.models.pmv_ppd_iso(tdb, tr,
vr, rh, met, clo, ...)` and `pythermalcomfort.models.phs(tdb, tr, v, rh, met,
clo, posture, ...)` which return dataclass instances.

References:
- docs/context/FORMULAS_AND_CALCULATIONS.md sections 6-7
- https://pythermalcomfort.readthedocs.io/
"""

from __future__ import annotations

import math
from typing import Any

from pythermalcomfort.models import phs as _phs_model
from pythermalcomfort.models import pmv_ppd_iso as _pmv_ppd_iso


# ---------------------------------------------------------------------------
# PMV / PPD (ISO 7730)
# ---------------------------------------------------------------------------


def _pmv_sensation_it(pmv: float) -> str:
    """Italian PMV sensation label per the ISO 7730 7-point scale.

    The scale is symmetric: +3 Molto caldo, +2 Caldo, +1 Leggermente caldo,
    0 Neutrale, -1 Leggermente freddo, -2 Freddo, -3 Molto freddo. Rounds
    to the nearest integer step and clamps at the extremes.
    """
    if math.isnan(pmv):
        return "Fuori soglia"
    # Midpoint rounding to the 7-point scale
    bucket = max(-3, min(3, round(pmv)))
    labels = {
        -3: "Molto freddo",
        -2: "Freddo",
        -1: "Leggermente freddo",
        0: "Neutrale",
        1: "Leggermente caldo",
        2: "Caldo",
        3: "Molto caldo",
    }
    return labels[bucket]


def _iso_7730_category(pmv: float, ppd: float) -> tuple[str, bool]:
    """Return (category, compliant) per ISO 7730:2006 Annex A.

    - A: PPD < 6%  AND |PMV| < 0.2
    - B: PPD < 10% AND |PMV| < 0.5
    - C: PPD < 15% AND |PMV| < 0.7

    Compliance with at least category C is required for normal offices.
    """
    if math.isnan(pmv) or math.isnan(ppd):
        return "FUORI_SOGLIA", False
    abs_pmv = abs(pmv)
    if ppd < 6 and abs_pmv < 0.2:
        return "A", True
    if ppd < 10 and abs_pmv < 0.5:
        return "B", True
    if ppd < 15 and abs_pmv < 0.7:
        return "C", True
    return "FUORI_SOGLIA", False


def calculate_pmv_ppd(
    air_temp: float,
    mean_radiant_temp: float,
    air_velocity: float,
    humidity: float,
    metabolic_rate: float,
    clothing_insulation: float,
) -> dict[str, Any]:
    """Compute PMV, PPD, Italian sensation, ISO 7730 category, and compliance.

    Args:
        air_temp: Dry bulb air temperature tdb [°C].
        mean_radiant_temp: Mean radiant temperature tr [°C].
        air_velocity: Relative air speed vr [m/s].
        humidity: Relative humidity rh [%].
        metabolic_rate: Metabolic rate met [met].
        clothing_insulation: Clothing insulation clo [clo].

    Returns:
        dict with keys: pmv, ppd, sensation (Italian), category (A|B|C|
        FUORI_SOGLIA), compliant (bool).
    """
    result = _pmv_ppd_iso(
        tdb=air_temp,
        tr=mean_radiant_temp,
        vr=air_velocity,
        rh=humidity,
        met=metabolic_rate,
        clo=clothing_insulation,
        model="7730-2005",
        limit_inputs=False,  # surface the number; compliance is checked separately
        round_output=True,
    )
    pmv_val = float(result.pmv)
    ppd_val = float(result.ppd)
    category, compliant = _iso_7730_category(pmv_val, ppd_val)
    return {
        "pmv": pmv_val,
        "ppd": ppd_val,
        "sensation": _pmv_sensation_it(pmv_val),
        "category": category,
        "compliant": compliant,
    }


# ---------------------------------------------------------------------------
# PHS (ISO 7933)
# ---------------------------------------------------------------------------


def _phs_livello(d_lim: float, duration_min: int) -> str:
    """Classify PHS outcome by binding exposure limit.

    - ACCETTABILE: d_lim >= planned duration (full shift tolerable).
    - LIMITE: 60 min <= d_lim < planned duration (reduced exposure needed).
    - CRITICO: d_lim < 60 min (immediate intervention required).
    """
    if math.isnan(d_lim):
        return "FUORI_SOGLIA"
    if d_lim >= duration_min:
        return "ACCETTABILE"
    if d_lim >= 60:
        return "LIMITE"
    return "CRITICO"


def calculate_phs(
    air_temp: float,
    mean_radiant_temp: float,
    air_velocity: float,
    humidity: float,
    metabolic_rate: float,
    clothing_insulation: float,
    posture: str = "standing",
    acclimatized: bool = True,
    drink_free: bool = True,
    duration_min: int = 480,
) -> dict[str, Any]:
    """Compute Predicted Heat Strain (ISO 7933:2023).

    Inputs per docs/context/FORMULAS_AND_CALCULATIONS.md section 7. The
    library exposes posture as a string ("sitting" | "standing" |
    "crouching"), and acclimatization + free drinking as flags (int 100/0
    and 1/0 respectively in the underlying API).

    Returns:
        dict with: t_re, t_sk, d_lim_t_re, d_lim_loss_50, d_lim_loss_95,
        sweat_loss_g, d_lim (binding minimum), livello.
    """
    if posture not in ("sitting", "standing", "crouching"):
        raise ValueError(
            f"posture must be 'sitting'|'standing'|'crouching', got {posture!r}"
        )

    result = _phs_model(
        tdb=air_temp,
        tr=mean_radiant_temp,
        v=air_velocity,
        rh=humidity,
        met=metabolic_rate,
        clo=clothing_insulation,
        posture=posture,
        wme=0,
        acclimatized=100 if acclimatized else 0,
        drink=1 if drink_free else 0,
        duration=duration_min,
        round_output=True,
    )

    d_lim_t_re = float(result.d_lim_t_re)
    d_lim_loss_50 = float(result.d_lim_loss_50)
    d_lim_loss_95 = float(result.d_lim_loss_95)

    # Binding limit: the smallest of the three Dlim constraints.
    # NaNs from the ISO applicability limits propagate; filter them out if any.
    candidates = [
        x for x in (d_lim_t_re, d_lim_loss_50, d_lim_loss_95) if not math.isnan(x)
    ]
    d_lim = min(candidates) if candidates else float("nan")

    return {
        "t_re": float(result.t_re),
        "t_sk": float(result.t_sk),
        "d_lim_t_re": d_lim_t_re,
        "d_lim_loss_50": d_lim_loss_50,
        "d_lim_loss_95": d_lim_loss_95,
        "sweat_loss_g": float(result.sweat_loss_g),
        "d_lim": d_lim,
        "livello": _phs_livello(d_lim, duration_min),
    }
