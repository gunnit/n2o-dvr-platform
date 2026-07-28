"""The generated documents must be written in correct Italian (P1-1).

A DVR is signed by the datore di lavoro and read by an inspector. Shipping
«La valutazione dei rischi **e** stata effettuata» or «Scala di **Probabilita**»
is not a cosmetic slip: `e` and `è` are different words, and the whole document
reads as machine-produced.

The generators had accumulated 138 un-accented Italian words — `dvr_master.py`
alone contained exactly one accented character in 3.6k lines — because the
boilerplate was authored in ASCII. Nothing failed, so nothing caught it.

This test reads the *string literals* of every generator, not the file bytes:
identifiers and schema keys legitimately spell `attivita` without an accent
(`getattr(azienda, "attivita")`, `descrizione_attivita`), and flagging those
would make the test unfixable.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

GENERATORS = Path(__file__).resolve().parents[1] / "app" / "services" / "document_generator"

# Truncated forms that are always wrong in prose, mapped to the correct word.
# Only unambiguous ones: `necessita`, `evita`, `visita`, `garantita`,
# `allestita`, `esplicita` and `perdita` are real un-accented Italian and are
# deliberately absent.
FORBIDDEN: dict[str, str] = {
    "attivita": "attività",
    "probabilita": "probabilità",
    "responsabilita": "responsabilità",
    "modalita": "modalità",
    "idoneita": "idoneità",
    "periodicita": "periodicità",
    "conformita": "conformità",
    "criticita": "criticità",
    "capacita": "capacità",
    "velocita": "velocità",
    "umidita": "umidità",
    "unita": "unità",
    "qualita": "qualità",
    "citta": "città",
    "societa": "società",
    "disponibilita": "disponibilità",
    "rintracciabilita": "rintracciabilità",
    "puo": "può",
    "piu": "più",
    "gia": "già",
    "nonche": "nonché",
    "perche": "perché",
    "poiche": "poiché",
    "cosi": "così",
    "cioe": "cioè",
    "sara": "sarà",
    "verra": "verrà",
    "potra": "potrà",
    "dovra": "dovrà",
}

# `è` written as a bare `e` before a participle/adjective — the error that
# changes the meaning of a sentence rather than just its spelling.
BARE_E = re.compile(
    r"(?<![\w.])e\s+(stat[ao]|previst[ao]|conservat[ao]|riportat[ao]|definit[ao]"
    r"|obbligatori[ao]|vietat[ao]|consentit[ao]|richiest[ao]|necessari[ao])\b"
)


def _string_literals(path: Path):
    """(line, literal, source_line) for every STRING token in the module."""
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING:
            row = tok.start[0]
            yield row, tok.string, lines[row - 1] if row <= len(lines) else ""


# A string in one of these positions names a field, not a thing on the page.
# Matching on the *call* rather than on the literal's shape is what lets a
# one-word display label like `_add_optional("Attività", …)` still be checked —
# skipping every bare word, as an earlier version did, let that one through.
_KEY_POSITION = re.compile(
    r"""(?:
        getattr\s*\(\s*[\w.]+\s*,\s*      # getattr(obj, "field"
      | \.\s*get\s*\(\s*                  # d.get("key"
      | \[\s*                             # d["key"]
      | \bin_\s*\(\s*\[?                  # col.in_(["a", "b"])
      | ==\s*                             # col == "value"
    )$""",
    re.VERBOSE,
)


def _is_key_position(literal: str, source_line: str) -> bool:
    idx = source_line.find(literal)
    if idx < 0:
        return False
    if _KEY_POSITION.search(source_line[:idx].rstrip()):
        return True
    # `{"criticita": "alta"}` — a literal followed by a colon is a dict key.
    # Note this is the key only: the *value* after the colon is still checked,
    # because that is what reaches the page.
    after = source_line[idx + len(literal) :].lstrip()
    return after.startswith(":")


GENERATOR_FILES = sorted(GENERATORS.glob("*.py"))


@pytest.mark.parametrize("path", GENERATOR_FILES, ids=lambda p: p.name)
def test_no_unaccented_italian_in_generated_prose(path: Path):
    offenders: list[str] = []
    for line, literal, source_line in _string_literals(path):
        if _is_key_position(literal, source_line):
            continue
        for wrong, right in FORBIDDEN.items():
            for variant in (wrong, wrong.capitalize(), wrong.upper()):
                if re.search(r"(?<![\w.])" + variant + r"(?![\w])", literal):
                    offenders.append(f"{path.name}:{line} «{variant}» -> «{right}»")
    assert not offenders, "Un-accented Italian in document prose:\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize("path", GENERATOR_FILES, ids=lambda p: p.name)
def test_no_bare_e_where_the_verb_is_meant(path: Path):
    offenders: list[str] = []
    for line, literal, _source_line in _string_literals(path):
        for m in BARE_E.finditer(literal):
            offenders.append(f"{path.name}:{line} «{m.group(0)}» -> «è {m.group(1)}»")
    assert not offenders, "«e» used where «è» is meant:\n  " + "\n  ".join(offenders)


def test_the_dvr_master_actually_contains_accents():
    """A canary against a future "fix" that strips accents wholesale again.

    The DVR is the flagship document and its boilerplate is long enough that a
    correct Italian rendering cannot plausibly contain fewer than a few dozen
    accented characters. It shipped with exactly one.
    """
    src = (GENERATORS / "dvr_master.py").read_text(encoding="utf-8")
    accented = re.findall(r"[àèéìòù]", src)
    assert len(accented) > 50, f"only {len(accented)} accented characters in dvr_master.py"
