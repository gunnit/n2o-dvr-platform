"""Pure helpers that keep the Programma di Miglioramento free of repeats.

Segnalazione 2026-08-21 ("Molte misure di miglioramento me le ripete"):
measures are generated one pericolo at a time, so a measure that several
pericoli share — "formazione specifica dei lavoratori", "verifica
periodica delle attrezzature" — came back once per pericolo, each time as
its own row of Table 109. The DVR then printed the same measure five
times with a different risk label in front.

The fix keeps one row per *measure* and lists the pericoli it covers in
the "Rischio" column. Two measures are the same when their titles match
after the normalisation below (accents, case, punctuation and Italian
function words stripped), which is deliberately lenient: the model is
asked for stable titles, but "Formazione specifica dei lavoratori" and
"formazione specifica lavoratori" must still land on the same row.

No I/O, no ORM — the API layer and the DVR seeder both call these, and
the tests exercise them directly.
"""

from __future__ import annotations

import re
import unicodedata

RISK_LABEL_SEPARATOR = "; "

_NON_ALNUM_RE = re.compile(r"[^0-9a-z ]+")
_WS_RE = re.compile(r"\s+")

# Italian articles, prepositions and their elided/compound forms. Dropping
# them makes the key insensitive to the small rewordings the model
# produces between calls without touching the content words.
_FUNCTION_WORDS = frozenset(
    """
    il lo la i gli le l un una uno
    di del dello della dei degli delle d
    a al allo alla ai agli alle
    da dal dallo dalla dai dagli dalle
    in nel nello nella nei negli nelle
    su sul sullo sulla sui sugli sulle
    con per tra fra e ed o od
    dell dall nell sull all
    """.split()
)


def normalize_measure_key(text: str | None) -> str:
    """Collapse a measure title to a comparison key.

    Empty input gives an empty key, and callers must treat an empty key as
    "never merge" — a manual row with no title is not the same measure as
    another manual row with no title.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower().replace("'", " ").replace("’", " ")
    alnum = _NON_ALNUM_RE.sub(" ", lowered)
    tokens = [t for t in _WS_RE.split(alnum) if t and t not in _FUNCTION_WORDS]
    return " ".join(tokens)


def join_risk_labels(existing: str | None, label: str | None) -> str:
    """Append ``label`` to a "; "-separated risk list, without repeats.

    Comparison is case-insensitive on the whole label so "Cadute dall'alto"
    is not added twice with different capitalisation, while two genuinely
    different pericoli both stay listed.
    """
    clean = " ".join((label or "").split())
    if not clean:
        return existing or ""
    if not existing or not existing.strip():
        return clean
    parts = [p.strip() for p in existing.split(RISK_LABEL_SEPARATOR) if p.strip()]
    if clean.casefold() in {p.casefold() for p in parts}:
        return RISK_LABEL_SEPARATOR.join(parts)
    return RISK_LABEL_SEPARATOR.join([*parts, clean])
