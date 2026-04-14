"""
VDT (Videoterminali / Display Screen Equipment) exposure classifier.

Per D.Lgs. 81/2008 Titolo VII, a worker who uses a VDT >= 20 hours/week is
classified as "Esposto" and is subject to mandatory health surveillance
(sorveglianza sanitaria oculistica). This is a trivial threshold check —
there is no scoring model. The only computation is:

    Esposto = (ore_settimanali >= 20)

Health surveillance requires an eye/sight examination before assignment to
the VDT workstation, then at intervals set by the medico competente
(typically 5 years, or 2 years for workers over 50 or with specific
prescriptions).

Reference: docs/context/FORMULAS_AND_CALCULATIONS.md section 3,
docs/context/REFERENCE_DATA.md section 5.
"""

from __future__ import annotations

from typing import Literal

VDT_EXPOSURE_THRESHOLD_HOURS: float = 20.0

ExposureLabel = Literal["ESPOSTO", "NON_ESPOSTO"]


def classify_exposure(hours_per_week: float) -> ExposureLabel:
    """Classify a worker's VDT exposure based on weekly usage hours.

    Args:
        hours_per_week: Weekly VDT usage in hours. Must be >= 0. The 20h
            threshold is inclusive (exactly 20 hours/week counts as ESPOSTO
            per D.Lgs. 81/2008 art. 173).

    Returns:
        "ESPOSTO" if hours_per_week >= 20, otherwise "NON_ESPOSTO".
    """
    if hours_per_week < 0:
        raise ValueError(f"hours_per_week must be >= 0, got {hours_per_week}")
    return "ESPOSTO" if hours_per_week >= VDT_EXPOSURE_THRESHOLD_HOURS else "NON_ESPOSTO"


def requires_health_surveillance(exposure: str) -> bool:
    """Return True if the given exposure label triggers health surveillance.

    Under D.Lgs. 81/2008 art. 176, VDT workers classified as ESPOSTO must
    undergo sorveglianza sanitaria — an eye/sight examination before being
    assigned to the workstation and at intervals set by the medico competente.
    """
    return exposure == "ESPOSTO"
