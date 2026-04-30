"""Tests for the per-persona DPI + rischi specifici aggregation in the
DVR Master generator (refactor 2026-04-30).

Two persone with the same mansione can carry divergent flags. The
generator must:
  - aggregate (union) their codes when emitting the per-mansione tables
  - flag the row with a "varia per lavoratore" note when the persone
    diverge
  - omit the note when the persone share identical flags
"""

from dataclasses import dataclass, field

from docx import Document

from app.services.document_generator.dvr_master import DVRMasterGenerator


@dataclass
class _FakePersona:
    id: str
    nominativo: str
    mansione: str | None
    dpi_codes: list[str] = field(default_factory=list)
    rischi_specifici_codes: list[str] = field(default_factory=list)
    attrezzature_speciali: list[str] = field(default_factory=list)


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


def test_dpi_per_mansione_unions_codes_across_persone():
    """Two saldatori with overlapping but different DPI codes should both
    contribute to the mansione's DPI grid via union."""
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
    gen._add_dpi_per_mansione_section(doc, persone, extras={})

    text = _all_text(doc).lower()
    # Union: all three DPI labels (any per-code keyword) should appear
    # under the SALDATORE heading.
    assert "caschi" in text
    assert "guanti" in text
    assert "occhiali" in text
    # Divergent flags → varia note must appear
    assert "varia tra i lavoratori" in text


def test_dpi_per_mansione_no_varia_note_when_aligned():
    """When all persone with the mansione carry identical DPI flags,
    the 'varia per lavoratore' note must NOT appear."""
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
            dpi_codes=["caschi_industria", "guanti_meccanici"],
        ),
    ]

    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_mansione_section(doc, persone, extras={})

    text = _all_text(doc).lower()
    assert "varia tra i lavoratori" not in text


def test_rischi_specifici_section_aggregates_persona_codes():
    """rischi_specifici_codes ticked on the persona must surface in the
    aggregated 'Mansioni che espongono a rischi specifici' table, with a
    'varia per lavoratore' suffix when the persone diverge."""
    persone = [
        _FakePersona(
            id="p1",
            nominativo="Mario Rossi",
            mansione="Operaio",
            # 'af_rumore' = rumore (catalog), 'mmc' = movimentazione manuale
            rischi_specifici_codes=["af_rumore"],
        ),
        _FakePersona(
            id="p2",
            nominativo="Anna Bianchi",
            mansione="Operaio",
            rischi_specifici_codes=["af_rumore", "mmc"],
        ),
    ]

    gen = _new_generator()
    doc = Document()
    extras = {"vdt_esposti_persona_ids": set()}
    gen._add_mansioni_rischi_specifici_section(doc, persone, extras)

    text = _all_text(doc).lower()
    assert "operaio" in text
    # Both rischi present (union)
    assert "rumore" in text
    # Divergent → suffix surfaces
    assert "varia per lavoratore" in text


def test_dpi_per_mansione_falls_back_when_no_persona_has_flags():
    """When no persona carries any DPI flag, the section must emit the
    'in fase di compilazione' fallback paragraph instead of an empty grid."""
    persone = [
        _FakePersona(id="p1", nominativo="Mario Rossi", mansione="Operaio"),
    ]
    gen = _new_generator()
    doc = Document()
    gen._add_dpi_per_mansione_section(doc, persone, extras={})

    text = _all_text(doc).lower()
    assert "in fase di compilazione" in text


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
