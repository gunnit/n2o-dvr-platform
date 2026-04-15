"""NIOSH reference weight constant (CP) lookup per sex and age.

Per D.Lgs. 81/2008 Allegato XXXIII and ISO 11228-1. Values in kg.
See docs/context/REFERENCE_DATA.md NIOSH section.
"""

from typing import Literal

Sex = Literal["M", "F"]


def get_default_cp(sesso: Sex, eta: int) -> int:
    """Return the reference weight constant CP in kg.

    Age bands: giovane (15-17), adulto (18-45), anziano (>45).
    Ages < 15 are rejected (legally cannot work in Italy).
    """
    if eta < 15:
        raise ValueError(f"Eta non valida: {eta} (minimo 15 anni)")
    if sesso not in ("M", "F"):
        raise ValueError(f"Sesso non valido: {sesso!r} (atteso 'M' o 'F')")

    if sesso == "M":
        if eta <= 17:
            return 20
        if eta <= 45:
            return 25
        return 20
    # F
    if eta <= 17:
        return 15
    if eta <= 45:
        return 20
    return 15
