"""Scheda ambiente table shared by the incendio and PEE allegati.

Segnalazioni 2026-08-25: both allegati must show, for every ambiente, the
description of the room with its size and materials, the maximum number of
people present and the possible ignition sources. The facts live on the
``Ambiente`` row (entered once, proposed from photos, confirmed by the
operator); this module renders them the same way in both documents so a
reader moving from the incendio allegato to the PEE finds the same table.
"""

from __future__ import annotations

from typing import Iterable

from app.services.document_generator.docx_utils import (
    add_data_table,
    add_heading,
    add_paragraph,
)

SCHEDA_HEADERS = [
    "Ambiente",
    "Descrizione del locale",
    "Superficie (mq)",
    "Materiali presenti",
    "Persone max",
    "Sorgenti di innesco",
]

_EMPTY_NOTE = (
    "Schede ambiente non compilate: descrizione del locale, materiali "
    "presenti, numero massimo di persone e sorgenti di innesco si inseriscono "
    "nella scheda di ciascun ambiente (valutazione incendio o piano di "
    "emergenza)."
)

_INTRO = (
    "Per ogni ambiente: descrizione del locale con la superficie, materiali "
    "presenti rilevanti per il carico d'incendio, affollamento massimo "
    "previsto e possibili sorgenti di innesco."
)


def _fmt_mq(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def scheda_rows(ambienti: Iterable) -> list[list[str]]:
    """One row per ambiente that has at least one scheda field filled.

    Ambienti with nothing filled are skipped rather than printed as a row
    of dashes — the empty-state note below the heading says what to do.
    """
    rows: list[list[str]] = []
    for amb in ambienti or []:
        descrizione = getattr(amb, "descrizione_locale", None)
        materiali = getattr(amb, "materiali_presenti", None)
        max_persone = getattr(amb, "max_persone", None)
        innesco = getattr(amb, "sorgenti_innesco", None)
        if not any(v not in (None, "") for v in (descrizione, materiali, max_persone, innesco)):
            continue
        rows.append(
            [
                getattr(amb, "nome", None) or "—",
                descrizione or "—",
                _fmt_mq(getattr(amb, "superficie_mq", None)),
                materiali or "—",
                str(max_persone) if max_persone is not None else "—",
                innesco or "—",
            ]
        )
    return rows


def add_schede_ambienti(
    doc,
    ambienti: Iterable,
    *,
    heading: str = "Schede degli ambienti",
    level: int = 2,
) -> int:
    """Append the heading and the table; return how many rows were printed."""
    add_heading(doc, heading, level=level)
    rows = scheda_rows(ambienti)
    if not rows:
        add_paragraph(doc, _EMPTY_NOTE, italic=True)
        return 0
    add_paragraph(doc, _INTRO, italic=True, size=9)
    add_data_table(doc, SCHEDA_HEADERS, rows)
    return len(rows)
