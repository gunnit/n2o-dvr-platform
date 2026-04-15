"""POS - Piano Operativo di Sicurezza (D.Lgs. 81/2008 Titolo IV All. XV)."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_pos
from app.services.document_generator.docx_utils import (
    TEMPLATES_DIR,
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    page_break,
    replace_placeholders,
    slugify,
)
from app.services.dpi_rules import DPI_CATALOG, build_default_matrix

TEMPLATE = TEMPLATES_DIR / "POS.docx"
TIPO_DOC = "pos"


class PosGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        pos_rows = await load_pos(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"POS - {azienda.ragione_sociale}", level=1)

        if not pos_rows:
            add_paragraph(doc, "Nessun cantiere registrato per questa azienda.", italic=True)
        for idx, p in enumerate(pos_rows, 1):
            page_break(doc)
            add_heading(doc, f"{idx}. Cantiere: {p.cantiere_indirizzo}", level=2)
            add_kv_table(doc, [
                ("Impresa esecutrice", azienda.ragione_sociale or ""),
                ("Committente", p.committente or ""),
                ("Direttore dei lavori", p.direttore_lavori or ""),
                ("Coordinatore sicurezza", p.coordinatore_sicurezza or ""),
                ("Indirizzo cantiere", p.cantiere_indirizzo or ""),
                ("Descrizione", p.cantiere_descrizione or ""),
                ("Data inizio", p.data_inizio.strftime("%d/%m/%Y") if p.data_inizio else "—"),
                ("Data fine", p.data_fine.strftime("%d/%m/%Y") if p.data_fine else "—"),
                ("Importo lavori", f"{float(p.importo_lavori):,.2f} EUR" if p.importo_lavori else "—"),
                ("Numero massimo lavoratori", str(p.numero_massimo_lavoratori) if p.numero_massimo_lavoratori else "—"),
            ])

            add_heading(doc, "Fasi lavorative", level=3)
            fasi = p.fasi_lavorative or []
            if fasi:
                rows = []
                for f in fasi:
                    rischi = ", ".join(f.get("rischi", [])) if isinstance(f.get("rischi"), list) else (f.get("rischi") or "")
                    dpi = ", ".join(f.get("dpi", [])) if isinstance(f.get("dpi"), list) else (f.get("dpi") or "")
                    mezzi = ", ".join(f.get("mezzi", [])) if isinstance(f.get("mezzi"), list) else (f.get("mezzi") or "")
                    rows.append([f.get("fase", ""), f.get("descrizione", ""), rischi, dpi, mezzi])
                add_data_table(doc, ["Fase", "Descrizione", "Rischi", "DPI", "Mezzi"], rows)

            add_heading(doc, "Valutazioni specifiche", level=3)
            rum = p.valutazione_rumore or {}
            vib = p.valutazione_vibrazioni or {}
            add_kv_table(doc, [
                ("Lex 8h (dB(A))", str(rum.get("lex_8h_dba", "—"))),
                ("Fascia rumore", rum.get("fascia", "—")),
                ("DPI uditivi obbligatori", "SI" if rum.get("dpi_obbligatori") else "NO"),
                ("a8 mano-braccio (m/s^2)", str(vib.get("a8_mano_braccio", "—"))),
                ("a8 corpo intero (m/s^2)", str(vib.get("a8_corpo_intero", "—"))),
                ("Entro i limiti di legge", "SI" if vib.get("entro_limiti") else "NO"),
            ])

            add_heading(doc, "Mezzi e attrezzature", level=3)
            mezzi = p.mezzi_attrezzature or []
            add_data_table(doc, ["Tipo"], [[m.get("tipo", "")] for m in mezzi] or [["—"]])

            add_heading(doc, "Sostanze pericolose utilizzate in cantiere", level=3)
            sostanze = p.sostanze_pericolose or []
            add_data_table(doc, ["Sostanza", "Uso"], [[s.get("nome", ""), s.get("uso", "")] for s in sostanze] or [["—", "—"]])

            # US-4.8: DPI matrix (role x phase). Only emit when the operator
            # has actually built one — we never auto-seed at generation time
            # because the matrix is a per-client override surface.
            _render_dpi_matrix(doc, p)

        add_heading(doc, "Sottoscrizione", level=2)
        add_data_table(doc, ["Ruolo", "Firma"], [
            ["Datore di lavoro impresa esecutrice", "________________________"],
            ["Coordinatore sicurezza in esecuzione", "________________________"],
            ["Data", generated_at.strftime("%d/%m/%Y")],
        ])

        version = await self._next_version()
        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        filepath = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.docx")
        doc.save(filepath)
        return filepath

    async def _next_version(self) -> int:
        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "POS"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1


# ---------------------------------------------------------------------------
# DPI matrix (US-4.8)
# ---------------------------------------------------------------------------


def _dpi_labels(codes: list[str]) -> str:
    """Render a list of DPI codes as comma-separated Italian labels."""
    if not codes:
        return "—"
    return ", ".join(DPI_CATALOG.get(c, c) for c in codes)


def _render_dpi_matrix(doc, pos) -> None:
    """Emit the role x phase DPI matrix for one POS.

    Layout: rows = roles, columns = phases (first column is the role
    label). Cells list the DPI as Italian labels from DPI_CATALOG. Where
    an operator edited a cell (differs from the rules-engine default for
    this role/phase), we append " (personalizzato)" so the reviewer can
    spot customisations.

    Merge rule: if two adjacent rows have identical DPI across every
    phase, their phase cells are merged vertically (their role labels
    stay separate since they're semantically different).
    """
    matrix = pos.dpi_matrix or {}
    roles = pos.dpi_matrix_roles or []
    phases = pos.dpi_matrix_phases or []
    if not matrix or not roles or not phases:
        return

    add_heading(doc, "Matrice DPI per ruolo e fase", level=3)

    # Pre-compute defaults once so we can detect operator overrides.
    defaults = build_default_matrix(roles, phases)

    header = ["Ruolo"] + list(phases)
    data_rows: list[list[str]] = []
    for role in roles:
        row: list[str] = [role]
        for phase in phases:
            cell_codes = (matrix.get(phase, {}) or {}).get(role, []) or []
            default_codes = (defaults.get(phase, {}) or {}).get(role, []) or []
            label = _dpi_labels(cell_codes)
            if sorted(cell_codes) != sorted(default_codes):
                label = f"{label} (personalizzato)" if label != "—" else "— (personalizzato)"
            row.append(label)
        data_rows.append(row)

    table = add_data_table(doc, header, data_rows)

    # Vertical merge for adjacent rows with identical DPI across every
    # phase. python-docx merges are additive — cell.merge(other) merges
    # the rectangle they span, so we call it per column for each run of
    # identical rows. Column 0 (role) is left untouched so the labels
    # remain distinct.
    if len(data_rows) < 2:
        return
    run_start = 0
    for i in range(1, len(data_rows) + 1):
        same = (
            i < len(data_rows)
            and data_rows[i][1:] == data_rows[run_start][1:]
        )
        if not same:
            if i - run_start > 1:
                # +1 because the header occupies row 0 in the docx table.
                top_row = table.rows[run_start + 1]
                bot_row = table.rows[i - 1 + 1]
                for col in range(1, len(header)):
                    top_row.cells[col].merge(bot_row.cells[col])
            run_start = i
