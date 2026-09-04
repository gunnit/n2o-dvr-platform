"""Per-mansione aggregation for the protocollo sanitario.

Pure functions over Persona-like objects (anything with ``.mansione``,
``.dpi_codes``, ``.rischi_specifici_codes``): the API, the AI prompt
builder and the DVR §4.3 renderer all aggregate the same way, so the
union lives here once.

Only role-level facts leave this module — codes, labels and a head count.
Names, codici fiscali and any per-person health flag are never part of an
aggregate, which is what lets the AI prompt be built from its output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.data.malattie_professionali import MalattiaProfessionale, malattie_per_rischi
from app.schemas.protocollo_sanitario import normalize_mansione
from app.services.reference_data import DPI_CATALOG, RISCHI_SPECIFICI_CATALOG


@dataclass
class MansioneAggregate:
    mansione: str
    num_persone: int = 0
    rischi_codes: set[str] = field(default_factory=set)
    dpi_codes: set[str] = field(default_factory=set)

    @property
    def key(self) -> str:
        return self.mansione.lower()

    def rischi_items(self) -> list[dict[str, str]]:
        return [
            {"code": c, "etichetta": rischio_label(c)}
            for c in sorted(self.rischi_codes, key=rischio_label)
        ]

    def dpi_items(self) -> list[dict[str, str]]:
        return [
            {"code": c, "etichetta": dpi_label(c)}
            for c in sorted(self.dpi_codes, key=dpi_label)
        ]

    def malattie_riferimento(self) -> list[MalattiaProfessionale]:
        return malattie_per_rischi(self.rischi_codes)


def rischio_label(code: str) -> str:
    return RISCHI_SPECIFICI_CATALOG.get(code, {}).get("etichetta", code)


def dpi_label(code: str) -> str:
    return DPI_CATALOG.get(code, {}).get("etichetta", code)


def mansione_key(value: str | None) -> str:
    return normalize_mansione(value).lower()


def _is_external_consultant(person: object) -> bool:
    """External RSPP / MC are not workers under sorveglianza (mirrors the
    DVR's ``_employee_persons`` filter)."""
    return bool(
        getattr(person, "is_esterno", False)
        and (
            getattr(person, "ruolo_rspp", False)
            or getattr(person, "ruolo_medico_competente", False)
        )
    )


def aggregate_per_mansione(persone: list) -> dict[str, MansioneAggregate]:
    """Union of rischi + DPI codes per normalised mansione, keyed by
    ``mansione.lower()``. Persone without a mansione are skipped; the first
    spelling seen is kept as the display form."""
    out: dict[str, MansioneAggregate] = {}
    for p in persone:
        if _is_external_consultant(p):
            continue
        mans = normalize_mansione(getattr(p, "mansione", None))
        if not mans:
            continue
        agg = out.get(mans.lower())
        if agg is None:
            agg = MansioneAggregate(mansione=mans)
            out[mans.lower()] = agg
        agg.num_persone += 1
        agg.rischi_codes.update(
            c for c in (getattr(p, "rischi_specifici_codes", None) or []) if c
        )
        agg.dpi_codes.update(c for c in (getattr(p, "dpi_codes", None) or []) if c)
    return out
