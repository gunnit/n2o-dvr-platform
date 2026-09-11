"""Fill the front-matter forms of the donor allegato templates.

``ALLEGATO RISCHIO INCENDIO.docx`` and ``PIANO GESTIONE EMERGENZE - AZIENDA.docx``
are N2O's own blank master forms: a consultant used to write the anagrafica,
the roster, the safety roles and the list of ambienti into them by hand. The
generators opened the template and appended their assessment after it, so the
delivered document opened with pages of empty boxes asking for data the
platform already holds — the opposite of "una questione di revisione, non di
inserimento del dato" (audit 2026-09-11).

Everything here is written from the live survey. What the platform does not
model at all (ASPP, dirigente per la sicurezza) is marked ``[DA COMPILARE]``
rather than guessed or silently left blank, the same marker ``dvr_master``
uses for the sections only the RSPP can write.
"""

from __future__ import annotations

from typing import Iterable

from docx.shared import Pt

from app.services.document_generator.docx_utils import (
    TYPE_SCALE,
    _norm_text,
    _set_cell_text_keep_format,
    fill_label_table,
    find_label_table,
    format_comune,
)

DA_COMPILARE = "[DA COMPILARE]"
NON_NOMINATO = "Non nominato"

# The anagrafica form is the one table carrying all three labels; the cover
# repeats "Azienda" and the Organizzazione chapter repeats the role names.
_ANAGRAFICA_KEYS = ("Azienda", "Datore di Lavoro", "Medico Competente")

_ROLE_SHEETS = (
    # donor title row, flag on Persona
    ("Datore di Lavoro", "ruolo_datore_lavoro"),
    ("Responsabile del Servizio di Prev. e Prot.", "ruolo_rspp"),
    ("Rappresentante dei Lavoratori", "ruolo_rls"),
    ("Medico Competente", "ruolo_medico_competente"),
)

_ROLE_LABELS = (
    ("ruolo_datore_lavoro", "DdL"),
    ("ruolo_rspp", "RSPP"),
    ("ruolo_rls", "RLS"),
    ("ruolo_medico_competente", "Medico Competente"),
    ("ruolo_preposto", "Preposto"),
    ("ruolo_primo_soccorso", "Addetto primo soccorso"),
    ("ruolo_antincendio", "Addetto antincendio"),
)


def _people_with(persone: Iterable, flag: str) -> list:
    return [p for p in (persone or []) if getattr(p, flag, False)]


def _names(persone: Iterable, flag: str) -> str:
    """The nominativi holding a role, or a statement that nobody does.

    "Non nominato" is a fact about the survey — the operator filled the
    roster and ticked nobody — so it is safe to print and quick to correct.
    """
    people = _people_with(persone, flag)
    return ", ".join((p.nominativo or "").strip() for p in people if p.nominativo) or NON_NOMINATO


def _seat_lines(azienda, which: str) -> list[str]:
    """Street and comune as two lines: the donor label spans two rows."""
    via = (getattr(azienda, f"sede_{which}_via", None) or "").strip()
    comune = format_comune(
        getattr(azienda, f"cap_{which}", None),
        getattr(azienda, f"sede_{which}_citta", None),
        getattr(azienda, f"provincia_{which}", None),
    )
    return [x for x in (via, comune if comune != "—" else "") if x]


def _find_sheet(doc, title: str):
    """A single-column donor sheet: a title row with an empty row under it."""
    needle = _norm_text(title)
    for table in doc.tables:
        if len(table.columns) != 1 or len(table.rows) < 2:
            continue
        if _norm_text(table.rows[0].cells[0].text) == needle:
            return table
    return None


def _find_grid(doc, headers: Iterable[str], *, header_row: int = 0):
    """A data grid identified by the text of its header row."""
    wanted = [_norm_text(h) for h in headers]
    for table in doc.tables:
        if len(table.rows) <= header_row:
            continue
        cells = table.rows[header_row].cells
        if len(cells) < len(wanted):
            continue
        if [_norm_text(c.text) for c in cells[: len(wanted)]] == wanted:
            return table
    return None


def _write_rows(table, rows: list[list[str]], *, first_data_row: int) -> int:
    """Write ``rows`` into the form, then drop the spare ruled lines.

    Donor grids are sized for a pen (six ambienti, nine workers). Surplus
    rows are deleted rather than blanked so the document does not hand the
    reader an empty table to fill; rows carrying a vertical merge are left
    alone, since removing one orphans its continuation.
    """
    if not rows:
        # Nothing to say: leave the ruled form as it is, so the blank-form
        # sweep can drop it whole rather than leaving a bare header row.
        return 0
    existing = list(table.rows)
    for index, values in enumerate(rows):
        target = first_data_row + index
        row = existing[target] if target < len(existing) else table.add_row()
        cells = row.cells
        seen: list = []
        for c_index, cell in enumerate(cells):
            if any(cell._tc is s for s in seen):
                continue
            seen.append(cell._tc)
            value = values[c_index] if c_index < len(values) else ""
            _set_cell_text_keep_format(cell, value or "")
            if target >= len(existing):
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(TYPE_SCALE["table"])
    for row in existing[first_data_row + len(rows):]:
        if row._tr.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vMerge"):
            continue
        table._tbl.remove(row._tr)
    return len(rows)


def fill_front_matter(doc, *, azienda, persone, ambienti) -> dict[str, int]:
    """Fill anagrafica, roster, safety roles and the ambienti index.

    Returns a per-form count of what was written, so a generator's test can
    assert the template still matches the labels this module looks for.
    """
    written: dict[str, int] = {}

    anagrafica = find_label_table(doc, _ANAGRAFICA_KEYS)
    if anagrafica is not None:
        operativa = _seat_lines(azienda, "operativa") or _seat_lines(azienda, "legale")
        written["anagrafica"] = fill_label_table(
            doc,
            {
                "Azienda": azienda.ragione_sociale or "",
                "Attività": (
                    getattr(azienda, "attivita", None)
                    or getattr(azienda, "descrizione_attivita", None)
                    or ""
                ),
                "Sede legale": _seat_lines(azienda, "legale"),
                "Sede operativa": operativa,
                "Datore di Lavoro": _names(persone, "ruolo_datore_lavoro"),
                "Responsabile del Servizio di Prevenzione e Protezione (RSPP)":
                    _names(persone, "ruolo_rspp"),
                "Addetto del Servizio di Prevenzione e Protezione (ASPP)": DA_COMPILARE,
                "Medico Competente": _names(persone, "ruolo_medico_competente"),
                "Dirigente per la sicurezza": DA_COMPILARE,
                "Rappresentanti dei Lavoratori per la Sicurezza": _names(persone, "ruolo_rls"),
            },
            tables=[anagrafica],
        )

    roster = _find_grid(
        doc,
        ["Nominativo", "Mansione", "Ambiente di Lavoro", "Note", "Tipologia contrattuale"],
    )
    if roster is not None:
        rows = []
        for p in persone or []:
            ruoli = [
                label for flag, label in _ROLE_LABELS if getattr(p, flag, False)
            ]
            rows.append([
                p.nominativo or "",
                p.mansione or "",
                ", ".join(
                    (a.nome or "").strip() for a in (getattr(p, "ambienti", None) or [])
                ),
                ", ".join(ruoli),
                getattr(p, "tipologia_contrattuale", None) or "",
            ])
        written["dati_occupazionali"] = _write_rows(roster, rows, first_data_row=1)

    for title, flag in _ROLE_SHEETS:
        sheet = _find_sheet(doc, title)
        if sheet is None:
            continue
        fill_label_table(doc, {title: _names(persone, flag)}, tables=[sheet])
    written["ruoli"] = len(_ROLE_SHEETS)

    for title_prefix, flag in (
        ("Addetti al Primo Soccorso", "ruolo_primo_soccorso"),
        ("Addetti alla prevenzione incendi", "ruolo_antincendio"),
    ):
        grid = None
        for table in doc.tables:
            if len(table.rows) >= 2 and _norm_text(table.rows[0].cells[0].text).startswith(
                _norm_text(title_prefix)
            ):
                grid = table
                break
        if grid is None:
            continue
        people = _people_with(persone, flag)
        rows = [[p.nominativo or "", p.mansione or ""] for p in people] or [
            [NON_NOMINATO, ""]
        ]
        written[flag] = _write_rows(grid, rows, first_data_row=2)

    index = _find_grid(doc, ["n.", "Ambiente di Lavoro"])
    if index is not None:
        rows = [
            [str(i), (a.nome or "").strip()]
            for i, a in enumerate(ambienti or [], start=1)
        ]
        written["ambienti"] = _write_rows(index, rows, first_data_row=1)

    return written
