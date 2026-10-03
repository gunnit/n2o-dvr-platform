"""Which persone and mansioni the gestanti allegato covers.

Segnalazione 2026-10-02: a mansione held only by men is not assessed for
pregnancy; the assessment covers the mansioni where a woman works. Sex comes from
``Persona.sesso`` and, when that was left empty, from the codice fiscale. The
CF is read locally and never leaves the server (CLAUDE.md rule 1).
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

from app.services.codice_fiscale import extract_sex


def persona_sex(persona: Any) -> Literal["M", "F"] | None:
    """``sesso`` normalised ("f", " F " → "F"), else derived from the CF."""
    raw = (getattr(persona, "sesso", None) or "").strip().upper()
    if raw in ("M", "F"):
        return raw  # type: ignore[return-value]
    return extract_sex(getattr(persona, "codice_fiscale", None))


def normalize_mansione(mansione: str | None) -> str:
    """Collapse whitespace so 'Cuoco ' and 'cuoco' match the same mansione."""
    return " ".join((mansione or "").strip().split())


def male_only_mansione_keys(persone: Iterable[Any]) -> set[str]:
    """Lower-cased mansioni whose every holder is a man.

    These are the mansioni the allegato skips. A mansione stays in when at
    least one holder is a woman, or of unrecorded sex (the censimento often
    leaves Sesso blank; hiding those would hide real work), or when nobody
    holds it at all (added by hand, or kept after staff turnover).
    """
    holders: dict[str, list[str | None]] = {}
    for p in persone:
        mans = normalize_mansione(getattr(p, "mansione", None))
        if mans:
            holders.setdefault(mans.lower(), []).append(persona_sex(p))
    return {key for key, sexes in holders.items() if all(s == "M" for s in sexes)}
