"""DPI rules engine for POS matrix (role x phase).

US-4.8 — For each POS an operator gets an auto-populated matrix that maps
each construction role to the DPI (personal protective equipment) they must
wear during each work phase. The rules in this module are intentionally
conservative: they bias towards adding DPI, never removing one the
legislation considers mandatory. Operators can override individual cells
at the POS level; those overrides stay on the POS row (``dpi_matrix``) and
never mutate the global rules here.

Construction roles and phases are the ones most commonly used by N2O
(Italian cantiere edile). The DPI catalog uses EN (European Norm) codes
from D.Lgs. 81/2008 Titolo III and the 2019/2021 DPI regulations so the
generated POS docx cites them correctly.
"""

from __future__ import annotations

# --- Canonical lists ------------------------------------------------------

ROLES_CONSTRUCTION: list[str] = [
    "carpentiere",
    "manovale",
    "gruista",
    "operatore_escavatore",
    "ponteggiatore",
    "saldatore",
    "elettricista",
    "muratore",
    "capo_cantiere",
    "autista_mezzi",
]

PHASES_CONSTRUCTION: list[str] = [
    "allestimento_cantiere",
    "scavi",
    "fondazioni",
    "getto_calcestruzzo",
    "montaggio_ponteggi",
    "opere_murarie",
    "finiture",
    "smobilizzo_cantiere",
]

DPI_CATALOG: dict[str, str] = {
    "casco": "Casco di protezione EN 397",
    "scarpe": "Scarpe antinfortunistiche S3",
    "imbragatura": "Imbragatura EN 361",
    "guanti": "Guanti da lavoro EN 388",
    "occhiali": "Occhiali EN 166",
    "otoprotettori": "Otoprotettori EN 352",
    "maschera": "Maschera FFP3 EN 149",
    "gilet_alta_visibilita": "Gilet alta visibilità EN ISO 20471",
    "ginocchiere": "Ginocchiere EN 14404",
    "facciale": "Schermo facciale EN 166",
}


# --- Rule sets ------------------------------------------------------------

# Base DPI every role wears on a cantiere, every phase. D.Lgs. 81/2008
# art. 77 requires casco + scarpe + alta visibilità on any active site.
_BASE_DPI: tuple[str, ...] = ("casco", "scarpe", "gilet_alta_visibilita")

# Phases where work-at-height kicks in. ``finiture`` is included because it
# covers facade/roof finishing — the main fall-from-height driver after
# ponteggi are up.
_WORK_AT_HEIGHT_PHASES: set[str] = {"montaggio_ponteggi", "finiture"}
_WORK_AT_HEIGHT_ROLES: set[str] = {"ponteggiatore", "carpentiere", "muratore"}

# Phases with elevated noise exposure; manual roles get otoprotettori.
_LOUD_PHASES: set[str] = {
    "scavi",
    "getto_calcestruzzo",
    "opere_murarie",
    "smobilizzo_cantiere",
}

# Roles that move cargo/people on the site — they already get base DPI +
# otoprotettori (constant exposure to machinery noise) but nothing else
# phase-specific because they don't work with their hands on site.
_CAB_ROLES: set[str] = {"gruista", "autista_mezzi", "capo_cantiere"}

# Roles considered "manual" — they physically handle materials and so pick
# up guanti on digging / foundation / concrete phases and otoprotettori on
# the loud phases above.
_MANUAL_ROLES: set[str] = {
    "carpentiere",
    "manovale",
    "operatore_escavatore",
    "ponteggiatore",
    "muratore",
    "elettricista",
    "saldatore",
}


def suggest_dpi(role: str, phase: str) -> list[str]:
    """Return the DPI codes required for a given role x phase pairing.

    The returned list preserves ``DPI_CATALOG`` insertion order so the UI
    renders chips in a consistent sequence regardless of which rules
    fired. Duplicates are removed.
    """
    dpi: set[str] = set(_BASE_DPI)

    # Saldatore — welding-specific DPI in every phase (they only show up
    # when there's welding work, so we always kit them up).
    if role == "saldatore":
        dpi.update({"occhiali", "guanti", "maschera", "facciale"})

    # Cab/supervisor roles: add constant otoprotettori, nothing else.
    if role in _CAB_ROLES:
        dpi.add("otoprotettori")

    # Work-at-height — imbragatura for the roles that physically climb.
    if phase in _WORK_AT_HEIGHT_PHASES and role in _WORK_AT_HEIGHT_ROLES:
        dpi.add("imbragatura")

    # Concrete pouring: ginocchiere + guanti for those kneeling to finish.
    if phase == "getto_calcestruzzo" and role in {"manovale", "muratore"}:
        dpi.update({"ginocchiere", "guanti"})

    # Digging / foundations: guanti for all manual roles.
    if phase in {"scavi", "fondazioni"} and role in _MANUAL_ROLES:
        dpi.add("guanti")

    # Loud phases: otoprotettori for exposed manual roles.
    if phase in _LOUD_PHASES and role in _MANUAL_ROLES:
        dpi.add("otoprotettori")

    # Preserve catalog order; drop anything not in the catalog (defensive
    # against rule mistakes).
    return [code for code in DPI_CATALOG.keys() if code in dpi]


def build_default_matrix(
    roles: list[str], phases: list[str]
) -> dict[str, dict[str, list[str]]]:
    """Build a full ``{phase: {role: [dpi_codes]}}`` matrix from the rules.

    Roles/phases unknown to the engine still get the base DPI set so a
    custom role added by the operator doesn't end up with an empty cell.
    """
    matrix: dict[str, dict[str, list[str]]] = {}
    for phase in phases:
        matrix[phase] = {}
        for role in roles:
            matrix[phase][role] = suggest_dpi(role, phase)
    return matrix
