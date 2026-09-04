"""Pericolo suggester — filters the catalog for a given ambiente.

Inputs: an Ambiente row and the list of its Attrezzature.
Output: list of catalog rows annotated with whether they matched on
ambiente, attrezzatura, or both — so the UI can render a "perché" chip.

Two-step matching:

1. **Ambiente filter** — normalize ``ambiente.tipo`` to one of the
   canonical lowercase buckets (ufficio/magazzino/cucina/produzione/
   laboratorio/esterno/negozio/officina/altro). A pericolo with empty
   ``ambiente_tipi`` is universal; a pericolo whose ``ambiente_tipi``
   contains the canonical bucket also matches.

2. **Attrezzatura override** — even if the ambiente filter would have
   hidden a pericolo, surface it when at least one attrezzatura's
   descrizione contains one of the pericolo's ``attrezzatura_keywords``
   (case-insensitive substring). This catches "Saldatrice in ufficio" →
   should expose Macchine + Chimici + Cancerogeni even though the
   ambiente filter would suppress them for an Ufficio.

Custom (free-text) ambiente tipi flow through bucket normalization
that's intentionally generous: matches on substring, with a fallback
of "altro" so the UI never shows an empty list.
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ambiente import Ambiente
from app.models.attrezzatura import Attrezzatura
from app.models.pericolo_libreria import PericoloLibreria

# Map free-text ambiente tipi to canonical buckets — ordered by specificity.
# First substring hit wins. "Altro" is the implicit catch-all when nothing
# matches.
_TIPO_BUCKETS: list[tuple[str, str]] = [
    ("ufficio direzionale", "ufficio"),
    ("ufficio", "ufficio"),
    ("open space", "ufficio"),
    ("sala riunioni", "ufficio"),
    ("sala corsi", "ufficio"),
    ("aula formazione", "ufficio"),
    ("reception", "ufficio"),
    ("accoglienza", "ufficio"),
    ("sala server", "ufficio"),
    ("ced", "ufficio"),
    ("aula scolastica", "ufficio"),
    ("sala d'attesa", "ufficio"),
    # Order matters: "cucina industriale" before "cucina"
    ("cucina industriale", "cucina"),
    ("cucina", "cucina"),
    ("sala mensa", "cucina"),
    ("refettorio", "cucina"),
    ("bar", "cucina"),
    ("caffetteria", "cucina"),
    ("magazzino", "magazzino"),
    ("deposito", "magazzino"),
    ("archivio", "magazzino"),
    ("area carico", "magazzino"),
    ("laboratorio chimico", "laboratorio"),
    ("laboratorio analisi", "laboratorio"),
    ("laboratorio", "laboratorio"),
    ("studio medico", "laboratorio"),
    ("ambulatorio", "laboratorio"),
    ("officina meccanica", "officina"),
    ("officina elettrica", "officina"),
    ("officina", "officina"),
    ("capannone produttivo", "produzione"),
    ("reparto produzione", "produzione"),
    ("linea di assemblaggio", "produzione"),
    ("produzione", "produzione"),
    ("showroom", "negozio"),
    ("sala esposizione", "negozio"),
    ("punto vendita", "negozio"),
    ("negozio", "negozio"),
    ("area esterna", "esterno"),
    ("cortile", "esterno"),
    ("parcheggio", "esterno"),
    ("cantiere", "esterno"),
    ("esterno", "esterno"),
    # Generic fallbacks
    ("bagno", "altro"),
    ("servizi igienici", "altro"),
    ("spogliatoio", "altro"),
    ("locale tecnico", "altro"),
    ("centrale termica", "altro"),
    ("cabina elettrica", "altro"),
    ("palestra", "altro"),
]

CANONICAL_TIPI = {
    "ufficio", "magazzino", "cucina", "produzione",
    "laboratorio", "esterno", "negozio", "officina", "altro",
}


def normalize_ambiente_tipo(tipo: str | None) -> str:
    """Map free-text tipo to a canonical bucket. Defaults to 'altro'."""
    if not tipo:
        return "altro"
    t = tipo.strip().lower()
    if t in CANONICAL_TIPI:
        return t
    for needle, bucket in _TIPO_BUCKETS:
        if needle in t:
            return bucket
    return "altro"


def _attrezzatura_match(
    keywords: list[str], attrezzature: Iterable[Attrezzatura]
) -> list[str]:
    """Return descriptions of attrezzature whose descrizione contains any keyword."""
    if not keywords:
        return []
    matches: list[str] = []
    for att in attrezzature:
        desc = (att.descrizione or "").lower()
        if not desc:
            continue
        if any(kw.lower() in desc for kw in keywords):
            if att.descrizione not in matches:
                matches.append(att.descrizione)
    return matches


def exclusion_reason(row, bucket: str) -> str:
    """Why a catalog row was left out for an ambiente of type ``bucket``.

    Shown next to the "Ripristina" button (segnalazione 2026-08-19: the
    operator wants to see every risk of the categoria, not only the ones
    the automatic filter kept), so it names the rule, not a code.
    """
    tipi = ", ".join(row.ambiente_tipi or []) or "specifici"
    keywords = list(row.attrezzatura_keywords or [])
    if keywords:
        shown = ", ".join(keywords[:3])
        return (
            f"Previsto per ambienti di tipo {tipi} o con attrezzature quali "
            f"{shown}; questo ambiente è di tipo {bucket} e non ne ha."
        )
    return f"Previsto per ambienti di tipo {tipi}; questo ambiente è di tipo {bucket}."


def classify_catalog_row(
    row, bucket: str, attrezzature: Iterable[Attrezzatura]
) -> dict:
    """Apply the filter rules to one catalog row and say what happened.

    ``excluded`` is True when neither the ambiente type nor any attrezzatura
    keyword matched — the row the old filter silently dropped.
    """
    # ambiente_tipi == [] → universal
    ambiente_match = not row.ambiente_tipi or bucket in row.ambiente_tipi
    att_hits = _attrezzatura_match(
        list(row.attrezzatura_keywords or []), attrezzature
    )
    excluded = not ambiente_match and not att_hits
    return {
        "pericolo": row,
        "matches_ambiente": ambiente_match,
        "triggered_by_attrezzature": att_hits,
        "excluded": excluded,
        "exclusion_reason": exclusion_reason(row, bucket) if excluded else None,
    }


async def suggest_pericoli(
    db: AsyncSession,
    ambiente: Ambiente,
    attrezzature: list[Attrezzatura],
    *,
    categoria: str | None = None,
    include_excluded: bool = False,
) -> list[dict]:
    """Return [{pericolo, matches_ambiente, triggered_by_attrezzature, excluded,
    exclusion_reason}, ...].

    When ``categoria`` is provided, only that category's catalog rows are
    considered. Otherwise the full catalog is returned (caller groups).
    With ``include_excluded`` the rows the filter rejected come back too,
    flagged ``excluded`` with a reason, so the UI can offer to restore them.

    Ordering: the catalog row order (Strutture first, codes ascending
    within categoria) — preserved by sorting on ``code``.
    """
    bucket = normalize_ambiente_tipo(ambiente.tipo)

    q = select(PericoloLibreria)
    if categoria:
        q = q.where(PericoloLibreria.categoria == categoria)
    q = q.order_by(PericoloLibreria.code)

    rows = (await db.execute(q)).scalars().all()

    out: list[dict] = []
    for row in rows:
        info = classify_catalog_row(row, bucket, attrezzature)
        if info["excluded"] and not include_excluded:
            continue
        out.append(info)
    return out
