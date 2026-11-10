"""Tests for per-persona DPI and specific-risk rendering in DVR Master.

Two persone with the same mansione can carry divergent flags. The
generator keeps each person's identity:
  - in the specific-risk table (one row per exposed person);
  - in the DPI section: one sub-title (the person's name) and one DPI
    table per person, as in N2O's model of 2026-10-20 (spec §4.2.1 row 22).
Only the Sorveglianza Sanitaria protocol, which the Medico Competente sets
per mansione, still aggregates (union) codes up to mansione.
"""

from dataclasses import dataclass, field

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table

from app.services.document_generator import dvr_master
from app.services.document_generator.dvr_master import DVRMasterGenerator

DPI_HEADER = ["Descrizione DPI", "Marca / Modello", "Note"]


@dataclass
class _FakePersona:
    id: str
    nominativo: str
    mansione: str | None
    dpi_codes: list[str] = field(default_factory=list)
    rischi_specifici_codes: list[str] = field(default_factory=list)
    attrezzature_speciali: list[str] = field(default_factory=list)
    ordine: int | None = None


def _new_generator() -> DVRMasterGenerator:
    """Construct a generator without DB context — we only call pure render
    helpers that take ``doc + persone + extras``."""
    gen = DVRMasterGenerator.__new__(DVRMasterGenerator)
    return gen


def _all_text(doc: Document) -> str:
    parts: list[str] = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _dpi_blocks(doc: Document) -> list[tuple[str, list[list[str]]]]:
    """(sub-title, table rows) of every person in the DPI section, in order.
    Each sub-title must be directly followed by its table."""
    blocks = []
    for paragraph in doc.paragraphs:
        if paragraph.style.name != "Heading 3":
            continue
        following = paragraph._p.getnext()
        assert following is not None and following.tag.endswith("}tbl"), paragraph.text
        table = Table(following, doc._body)
        blocks.append(
            (paragraph.text, [[cell.text for cell in row.cells] for row in table.rows])
        )
    return blocks


def test_dpi_gives_each_person_a_sub_title_and_their_own_table():
    """Two saldatori with different DPI: each gets their own sub-title and
    only their own DPI — no union across the shared mansione, no "varia"
    note."""
    persone = [
        _FakePersona(
            id="p1",
            nominativo="Mario Rossi",
            mansione="Saldatore",
            dpi_codes=["caschi_industria", "guanti_meccanici"],
        ),
        _FakePersona(
            id="p2",
            nominativo="Anna Bianchi",
            mansione="Saldatore",
            dpi_codes=["guanti_meccanici", "occhiali_stanghette"],
        ),
    ]

    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_persona_section(doc, persone, extras={})

    blocks = _dpi_blocks(doc)
    assert [title for title, _rows in blocks] == ["MARIO ROSSI", "ANNA BIANCHI"]
    (_m, mario), (_a, anna) = blocks
    assert mario[0] == DPI_HEADER and anna[0] == DPI_HEADER
    assert [row[0] for row in mario[1:]] == [
        "Mani: Guanti contro le aggressioni meccaniche",
        "Testa: Caschi di protezione per l'industria",
    ]
    assert [row[0] for row in anna[1:]] == [
        "Mani: Guanti contro le aggressioni meccaniche",
        "Vista: Occhiali a stanghette",
    ]
    assert "varia tra i lavoratori" not in _all_text(doc).lower()


def test_dpi_sub_titles_follow_saved_order_and_are_indexed():
    """Sub-titles are Heading 3 (in the index) in the persone's saved order."""
    persone = [
        _FakePersona(id="b", nominativo="Zeta Operaio", mansione="Operaio", ordine=2),
        _FakePersona(id="a", nominativo="Alfa Operaio", mansione="Operaio", ordine=1),
    ]

    doc = Document()
    _new_generator()._add_dpi_per_persona_section(doc, persone, extras={})

    assert [title for title, _rows in _dpi_blocks(doc)] == ["ALFA OPERAIO", "ZETA OPERAIO"]


def test_specific_risks_render_one_row_per_exposed_person_without_cross_inheritance():
    mario = _FakePersona(
        "p1", "Mario Rossi", "Operaio", rischi_specifici_codes=["af_rumore"]
    )
    anna = _FakePersona(
        "p2", "Anna Bianchi", "Operaio", rischi_specifici_codes=["mmc"]
    )
    doc = Document()
    _new_generator()._add_mansioni_rischi_specifici_section(
        doc, [mario, anna], {"vdt_esposti_persona_ids": set()}
    )
    table = doc.tables[-1]
    assert [cell.text for cell in table.rows[0].cells] == [
        "Nominativo",
        "Mansione",
        "Rischio specifico",
    ]
    assert [cell.text for cell in table.rows[1].cells][:2] == [
        "MARIO ROSSI",
        "OPERAIO",
    ]
    assert "Rumore" in table.rows[1].cells[2].text
    assert "Movimentazione" not in table.rows[1].cells[2].text
    assert [cell.text for cell in table.rows[2].cells][:2] == [
        "ANNA BIANCHI",
        "OPERAIO",
    ]
    assert "Movimentazione" in table.rows[2].cells[2].text
    assert "Rumore" not in table.rows[2].cells[2].text


def test_person_specific_risks_keep_saved_order_and_deduplicate_labels():
    person = _FakePersona(
        "p1",
        "Mario Rossi",
        "Operaio",
        rischi_specifici_codes=["af_rumore", "mmc", "af_rumore"],
        attrezzature_speciali=[
            "lavori_in_quota",
            "trabattelli",
            "ponteggi",
            "carrello_elevatore",
            "ple",
            "gru",
            "ruspa_escavatore",
            "patente_cde",
            "adr",
            "adr",
        ],
    )

    assert dvr_master._person_specific_risk_labels(person, {"p1"}) == [
        "Videoterminali",
        "Lavori in quota",
        "Utilizzo di trabattelli",
        "Utilizzo di ponteggi",
        "Utilizzo di carrelli elevatori",
        "Utilizzo di piattaforme di lavoro elevabili (PLE)",
        "Utilizzo di gru",
        "Utilizzo di ruspe ed escavatori",
        "Guida professionale (patente C/D/E)",
        "Trasporto merci pericolose (ADR)",
        "Agenti fisici - Rumore",
        "Movimentazione manuale dei carichi (MMC)",
    ]


def test_only_dpi_marca_modello_dash_is_centered_both_ways():
    doc = Document()
    _new_generator()._add_dpi_per_persona_section(
        doc, [_FakePersona("p", "Mario", "Operaio")], {}
    )
    table = next(
        table
        for table in doc.tables
        if table.rows
        and "Marca / Modello" in [
            cell.text.strip() for cell in table.rows[0].cells
        ]
    )
    column = [cell.text.strip() for cell in table.rows[0].cells].index(
        "Marca / Modello"
    )
    dash_cell = table.rows[1].cells[column]
    assert dash_cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert dash_cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
    assert (
        table.rows[1].cells[0].vertical_alignment
        != WD_CELL_VERTICAL_ALIGNMENT.CENTER
    )


def test_dpi_documents_a_person_with_no_dpi():
    """A person with no DPI flags still gets their sub-title and an explicit
    "nessun DPI" row (b780497).

    Silently omitting the person is the failure mode this guards: an
    inspector reading the DVR must be able to tell "no PPE is prescribed
    for this worker, and here is why" apart from "this worker was forgotten".
    """
    persone = [
        _FakePersona(id="p1", nominativo="Mario Rossi", mansione="Operaio"),
    ]
    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_persona_section(doc, persone, extras={})

    ((title, rows),) = _dpi_blocks(doc)
    assert title == "MARIO ROSSI"
    assert rows[0] == DPI_HEADER
    ((descrizione, marca, note),) = rows[1:]
    assert descrizione.startswith("Nessun DPI specifico richiesto")
    assert marca == "—"
    # The justification is the point of the row — a bare "nessuno" would
    # not be defensible at audit.
    assert "Sorveglianza sanitaria" in note


def test_dpi_gestante_note_follows_the_person_whose_mansione_triggers_it():
    """art. 12 D.Lgs. 151/2001 requires documented protective measures for
    a gestante worker even when no PPE is prescribed. The note goes on the
    row of the person whose mansione says so, not on a colleague's."""
    persone = [
        _FakePersona(id="p1", nominativo="Anna Bianchi", mansione="Impiegata gestante"),
        _FakePersona(id="p2", nominativo="Lia Verdi", mansione="Impiegata"),
    ]
    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_persona_section(doc, persone, extras={})

    (anna_title, anna), (lia_title, lia) = _dpi_blocks(doc)
    assert (anna_title, lia_title) == ("ANNA BIANCHI", "LIA VERDI")
    assert "151/2001" in anna[1][2]
    assert "151/2001" not in lia[1][2]


def test_dpi_lists_a_person_without_mansione_too():
    """The section is per person, so a person without a mansione still gets
    their sub-title and table."""
    persone = [
        _FakePersona(id="p1", nominativo="Mario Rossi", mansione=None),
        _FakePersona(id="p2", nominativo="Anna Bianchi", mansione="   "),
    ]
    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_persona_section(doc, persone, extras={})

    assert [title for title, _rows in _dpi_blocks(doc)] == ["MARIO ROSSI", "ANNA BIANCHI"]


def test_dpi_falls_back_when_there_is_nobody():
    """With nobody to tabulate, the section emits the 'in fase di
    compilazione' paragraph rather than a bare divider."""
    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_persona_section(doc, [], extras={})

    text = _all_text(doc).lower()
    assert "in fase di compilazione" in text
    assert not doc.tables


def test_sorveglianza_protocol_table_aggregates_per_mansione():
    """§4.3 protocol table must list each mansione once, aggregating the
    union of DPI + rischi codes from all persone with that mansione."""
    persone = [
        _FakePersona(
            id="p1",
            nominativo="Mario Rossi",
            mansione="Saldatore",
            dpi_codes=["caschi_industria"],
            rischi_specifici_codes=["af_rumore"],
        ),
        _FakePersona(
            id="p2",
            nominativo="Anna Bianchi",
            mansione="Saldatore",
            dpi_codes=["guanti_meccanici"],
            rischi_specifici_codes=["mmc"],
        ),
        _FakePersona(
            id="p3",
            nominativo="Lia Verdi",
            mansione="Impiegata",
            dpi_codes=["occhiali_stanghette"],
        ),
    ]
    gen = _new_generator()
    doc = Document()
    gen._add_sorveglianza_protocol_table(doc, persone)

    # Find the table; it must have headers + 2 mansione rows (Saldatore +
    # Impiegata), not 3 (one per persona).
    assert doc.tables, "protocol table should be rendered"
    table = doc.tables[-1]
    headers = [c.text.strip() for c in table.rows[0].cells]
    assert headers[0] == "Mansione"
    mansione_cells = [row.cells[0].text.strip() for row in table.rows[1:]]
    assert sorted(mansione_cells) == ["IMPIEGATA", "SALDATORE"]
