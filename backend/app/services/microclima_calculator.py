"""
Microclima (thermal comfort / thermal stress) calculator.

Wraps the pinned `pythermalcomfort` 4.4.2 API to compute:

- PMV/PPD per ISO 7730:2006 — comfort zones for normal indoor environments.
- PHS per ISO 7933:2023 — predicted heat strain for severe heat exposure.
- IREQ per UNI EN ISO 11079:2008 — required clothing insulation for severe
  cold exposure (pragmatic closed-form implementation, see `calculate_ireq`).

The library exposes `pythermalcomfort.models.pmv_ppd_iso(tdb, tr,
vr, rh, met, clo, ...)` and `pythermalcomfort.models.phs(tdb, tr, v, rh, met,
clo, posture, ...)` which return dataclass instances. This module retains the
repository's established ISO 11079:2008 IREQ calculation while using the
library's wind-chill temperature model (ISO 11079 Annex D / JAG-TI).

References:
- docs/context/FORMULAS_AND_CALCULATIONS.md sections 6-7
- https://pythermalcomfort.readthedocs.io/
"""

from __future__ import annotations

import math
from typing import Any

try:
    from pythermalcomfort.models import phs as _phs_model
    from pythermalcomfort.models import pmv_ppd_iso as _pmv_ppd_iso
    from pythermalcomfort.models import wind_chill_temperature as _wct_model
except Exception as exc:  # preserve document fallbacks if the optional model fails
    _phs_model = None
    _pmv_ppd_iso = None
    _wct_model = None
    _THERMAL_MODEL_IMPORT_ERROR: Exception | None = exc
else:
    _THERMAL_MODEL_IMPORT_ERROR = None


def _require_thermal_model(model, name: str):
    if model is None:
        raise RuntimeError(f"pythermalcomfort model {name} is unavailable") from _THERMAL_MODEL_IMPORT_ERROR
    return model


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
    result = _require_thermal_model(_pmv_ppd_iso, "pmv_ppd_iso")(
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

    result = _require_thermal_model(_phs_model, "phs")(
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


# ---------------------------------------------------------------------------
# IREQ — severe cold stress (UNI EN ISO 11079:2008)
#
# Pragmatic closed-form implementation mirroring the ISO 11079 decision
# logic (IREQneutral / IREQminimal / DLE) without the full iterative
# clothing-surface-temperature solver. Numeric constants and their sources:
#
#   - 1 met = 58.15 W/m², 1 clo = 0.155 m²K/W          (ISO 8996 / ISO 9920)
#   - neutral mean skin temp t_sk = 35.7 − 0.0285·M     (ISO 7730 comfort eq.)
#   - minimal-strain mean skin temp t_sk = 30 °C        (ISO 11079 "IREQmin"
#     criterion: highest acceptable body cooling, slight thermal strain)
#   - respiratory losses C_res + E_res =
#       0.0014·M·(34 − t_a) + 0.0173·M·(5.87 − p_a)     (ISO 7730 §4 heat
#     balance, p_a in kPa)
#   - minimal skin evaporation E_sk ≈ 5% of (M − RES)   (first-order allowance
#     for the low skin wettedness ISO 11079 assumes in cold, w ≈ 0.06)
#   - still-air boundary layer I_a = 0.7 clo            (ISO 9920 §5, typical
#     static value used by ISO 11079 informative examples)
#   - wind reduction of resultant total insulation:
#       f = exp(−0.281·(v−0.15) + 0.044·(v−0.15)²)      (ISO 9920 correction
#     for resultant insulation, walking speed 0; valid v ≤ 3.5 m/s — higher
#     wind speeds are clamped to the validity bound)
#   - allowed body heat debt Q_lim = 40 Wh/m²           (ISO 11079 §4.4 —
#     drives the DLE, duration-limited exposure, when insulation is
#     below IREQminimal)
#   - wind chill temperature t_wc (JAG/TI formula) and its frostbite bands
#     per ISO 11079:2008 Annex D, Table D.1: t_wc ≤ −25 °C freezing of
#     exposed skin possible within ~30 min, ≤ −35 °C within ~10 min,
#     ≤ −60 °C within ~2 min.
# ---------------------------------------------------------------------------

_MET_TO_W_M2 = 58.15  # 1 met [W/m²] (ISO 8996)
_CLO_TO_M2KW = 0.155  # 1 clo [m²K/W] (ISO 9920)
_STILL_AIR_CLO = 0.7  # boundary air layer insulation, static [clo] (ISO 9920)
_Q_LIM_WH_M2 = 40.0  # allowed body heat debt [Wh/m²] (ISO 11079 §4.4)
_T_SK_MINIMAL = 30.0  # minimal-strain mean skin temperature [°C] (ISO 11079)


def _p_sat_kpa(t: float) -> float:
    """Saturation water vapour pressure [kPa] (Magnus formula, over water)."""
    return 0.6105 * math.exp(17.27 * t / (t + 237.3))


def _wind_insulation_factor(air_velocity: float) -> float:
    """Wind reduction factor for resultant total insulation (ISO 9920).

    Correction for air movement at zero walking speed:
    f = exp(−0.281·(v − 0.15) + 0.044·(v − 0.15)²), valid for
    0.15 ≤ v ≤ 3.5 m/s. Outside the range v is clamped, so stronger winds
    use the 3.5 m/s reduction (~0.64) — conservative enough for a
    screening-level assessment.
    """
    v = min(max(air_velocity, 0.15), 3.5) - 0.15
    return math.exp(-0.281 * v + 0.044 * v * v)


def _wind_chill_c(air_temp: float, air_velocity: float) -> float | None:
    """Wind chill temperature t_wc [°C] per ISO 11079:2008 Annex D (JAG/TI).

    The formula wants the wind speed at 10 m above ground in km/h; workplace
    measurements are taken at body level, so we apply the customary ×1.5
    terrain scaling (Annex D guidance). Below the 4.8 km/h validity floor the
    index is undefined and calm air gives no aggravation: return the air
    temperature itself. Above 10 °C wind chill is meaningless: return None.
    """
    if air_temp > 10.0:
        return None
    v10_kmh = air_velocity * 1.5 * 3.6
    if v10_kmh < 4.8:
        return round(air_temp, 1)
    model = _require_thermal_model(_wct_model, "wind_chill_temperature")
    return float(model(tdb=air_temp, v=v10_kmh, round_output=True).wct)


def _frostbite_class(t_wc: float | None) -> str:
    """Frostbite-risk band per ISO 11079:2008 Annex D, Table D.1."""
    if t_wc is None:
        return "NON_APPLICABILE"
    if t_wc > -25:
        return "BASSO"
    if t_wc > -35:
        return "MODERATO"  # freezing of exposed skin possible within ~30 min
    if t_wc > -60:
        return "ALTO"  # within ~10 min
    return "ESTREMO"  # within ~2 min


def calculate_ireq(
    air_temp: float,
    mean_radiant_temp: float,
    air_velocity: float,
    humidity: float,
    metabolic_rate: float,
    clothing_insulation: float,
    duration_min: int = 480,
) -> dict[str, Any]:
    """Severe cold stress screening per UNI EN ISO 11079:2008 (IREQ).

    Computes the required clothing insulation for thermal neutrality
    (IREQneutral) and for the highest acceptable body cooling (IREQminimal),
    compares them with the clothing actually worn, and — when the clothing is
    below IREQminimal — the duration-limited exposure DLE from the allowed
    body heat debt Q_lim = 40 Wh/m². Local cooling (frostbite) risk is
    screened via the Annex D wind chill temperature.

    Args:
        air_temp: Air temperature t_a [°C] (cold environments, ≤ 10 °C).
        mean_radiant_temp: Mean radiant temperature t_r [°C].
        air_velocity: Air / wind speed at body level [m/s].
        humidity: Relative humidity [%].
        metabolic_rate: Metabolic rate [met].
        clothing_insulation: Basic insulation of the clothing worn Icl [clo].
        duration_min: Planned exposure (shift or work session) [minutes].

    Returns:
        dict with keys: t_o (operative temp), ireq_neutral, ireq_minimal
        (required basic clothing insulation [clo], wind penalty included),
        icl (echoed input), delta_clo (extra insulation recommended, ≥ 0),
        dle_min (duration-limited exposure [min] or None when not binding),
        t_wc (wind chill temperature [°C] or None), frostbite_risk
        (BASSO|MODERATO|ALTO|ESTREMO|NON_APPLICABILE), livello
        (ACCETTABILE|LIMITE|CRITICO).
    """
    m = metabolic_rate * _MET_TO_W_M2  # [W/m²]
    t_o = (air_temp + mean_radiant_temp) / 2.0  # operative temperature

    # Heat available for dry exchange through clothing.
    p_a = (humidity / 100.0) * _p_sat_kpa(air_temp)  # [kPa]
    res = 0.0014 * m * (34.0 - air_temp) + 0.0173 * m * (5.87 - p_a)
    e_sk = 0.05 * max(m - res, 0.0)  # minimal skin evaporation allowance
    m_net = max(m - res - e_sk, 10.0)  # [W/m²], floored defensively

    t_sk_neutral = 35.7 - 0.0285 * m  # ISO 7730 neutral skin temperature
    f_wind = _wind_insulation_factor(air_velocity)

    def _required_clothing_clo(t_sk: float) -> float:
        """Basic clothing insulation needed so that, wind-corrected and with
        the boundary air layer added, the dry heat loss balances m_net."""
        required_total_clo = max(0.0, (t_sk - t_o) / m_net) / _CLO_TO_M2KW
        return max(0.0, required_total_clo / f_wind - _STILL_AIR_CLO)

    ireq_neutral = _required_clothing_clo(t_sk_neutral)
    ireq_minimal = _required_clothing_clo(_T_SK_MINIMAL)
    icl = clothing_insulation

    # General-cooling classification (ISO 11079 decision scheme).
    if icl >= ireq_neutral:
        livello = "ACCETTABILE"
    elif icl >= ireq_minimal:
        livello = "LIMITE"
    else:
        livello = "CRITICO"

    # DLE — only binding when insulation is below the minimal requirement.
    dle_min: float | None = None
    if livello == "CRITICO":
        i_tot_avail = (icl + _STILL_AIR_CLO) * f_wind * _CLO_TO_M2KW  # [m²K/W]
        storage = m_net - (_T_SK_MINIMAL - t_o) / i_tot_avail  # [W/m²], < 0
        if storage < 0:
            dle_min = min(480.0, round(60.0 * _Q_LIM_WH_M2 / abs(storage), 0))

    # Local cooling (frostbite) screening escalates the overall level:
    # ISO 11079 requires both general and local cooling to be evaluated,
    # and the stricter one governs.
    t_wc = _wind_chill_c(air_temp, air_velocity)
    frostbite = _frostbite_class(t_wc)
    if frostbite in ("ALTO", "ESTREMO"):
        livello = "CRITICO"
    elif frostbite == "MODERATO" and livello == "ACCETTABILE":
        livello = "LIMITE"

    return {
        "t_o": round(t_o, 1),
        "ireq_neutral": round(ireq_neutral, 2),
        "ireq_minimal": round(ireq_minimal, 2),
        "icl": round(icl, 2),
        "delta_clo": round(max(0.0, ireq_neutral - icl), 2),
        "dle_min": dle_min,
        "t_wc": t_wc,
        "frostbite_risk": frostbite,
        "livello": livello,
    }
