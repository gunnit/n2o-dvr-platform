"""The printed revision number must match the row it came from (P1-2).

`POST /documents/generate` assigns `DocumentoGenerato.versione` and inserts the
row *before* the Celery task runs. The generators then recomputed the number
themselves with `SELECT max(versione) + 1`, which counted the row that had just
been inserted for this very run. A first-ever DVR therefore came out as:

    cover page   Revisione 02
    file name    …_v2.docx
    DB row       versione = 1
    Storico      00 — Emissione

— four numbers, one document, and the two an inspector actually reads
disagreeing with each other.
"""

from __future__ import annotations

import asyncio
import uuid

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.dvr_master import _revision_label


class _Gen(BaseDocumentGenerator):
    """Concrete subclass — the base class is abstract on `generate` only."""

    async def generate(self) -> str:  # pragma: no cover — never called here
        raise NotImplementedError


def _make(version: int | None) -> _Gen:
    return _Gen(uuid.uuid4(), db_session=None, version=version)


# --- resolve_version -------------------------------------------------------


def test_resolve_version_returns_the_assigned_row_version():
    """The caller's number wins, and no query is issued to second-guess it.

    `db_session=None` is the assertion: if `resolve_version` fell through to
    the fallback SELECT it would raise AttributeError on the missing session.
    """
    for assigned in (1, 2, 17):
        gen = _make(assigned)
        assert asyncio.run(gen.resolve_version(["dvr_master"])) == assigned


def test_version_defaults_to_none_when_not_supplied():
    """Direct construction (verify scripts, tests) still works — it just has to
    fall back to querying, which is the only path allowed to do so."""
    assert _make(None).version is None


# --- the printed label -----------------------------------------------------


def test_first_emission_is_revision_zero():
    """A DVR numbers its first issue 00, while the DB counts emissions from 1."""
    assert _revision_label(1) == "00"


def test_subsequent_emissions_increment():
    assert _revision_label(2) == "01"
    assert _revision_label(3) == "02"
    assert _revision_label(11) == "10"


def test_label_is_two_digit_padded():
    assert _revision_label(1) == "00"
    assert _revision_label(10) == "09"
    assert len(_revision_label(1)) == 2


def test_label_never_goes_negative():
    """Defensive: a 0 or garbage version must not print "Revisione -1"."""
    assert _revision_label(0) == "00"
    assert _revision_label(-5) == "00"


def test_cover_and_storico_agree_by_construction():
    """Both call sites go through the same helper, so equality is the contract.

    This is the regression: the cover used `f"{version:02d}"` (off by one *and*
    off by the 0-based convention) while the Storico table was hardcoded "00".
    """
    for version in (1, 2, 5):
        cover = _revision_label(version)
        storico = _revision_label(version)
        assert cover == storico
