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
from app.services.pos_phases import dependency_violations_after_ordering
from app.schemas.pos_phase import PosPhase
from pydantic import ValidationError

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
                _render_phase_sections(doc, fasi)

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


def _parse_phases(fasi_raw: list) -> list[PosPhase]:
    """Tolerantly parse the JSONB column into structured PosPhase rows.

    Older POS rows (pre-US-4.7) store loose ``{"fase": "...", "descrizione": "..."}``
    dicts without an ``id`` or ``ordine``. We promote them lazily so the
    generator can render either shape. Anything that still fails validation
    is dropped — safety documents must never fail to render over a stray
    row.
    """
    out: list[PosPhase] = []
    for i, raw in enumerate(fasi_raw or []):
        if not isinstance(raw, dict):
            continue
        # Back-compat: legacy rows used "fase" for the name.
        promoted = dict(raw)
        if "nome" not in promoted and "fase" in promoted:
            promoted["nome"] = promoted.pop("fase")
        promoted.setdefault("id", f"legacy-{i}")
        promoted.setdefault("ordine", i)
        try:
            out.append(PosPhase(**promoted))
        except ValidationError:
            continue
    return out


def _render_phase_sections(doc, fasi_raw: list) -> None:
    """Emit the per-phase sections for one POS (US-4.7).

    Structure:
      1. "Quadro sinottico" summary table — phases in drag-drop order with
         their dependencies, for the Gantt-like overview that the AC calls for.
      2. Per-phase narrative with rischi / DPI / mezzi and any NIOSH / rumore
         / vibrazioni snapshots.
      3. Footnote listing dependency violations (a phase declared after one
         of its declared predecessors — the generator does not refuse to
         render, per the endpoint comment).
    """
    phases = _parse_phases(fasi_raw)
    if not phases:
        # Fall back to the pre-US-4.7 tabular shape.
        rows = []
        for f in fasi_raw:
            if not isinstance(f, dict):
                continue
            rischi = ", ".join(f.get("rischi", [])) if isinstance(f.get("rischi"), list) else (f.get("rischi") or "")
            dpi = ", ".join(f.get("dpi", [])) if isinstance(f.get("dpi"), list) else (f.get("dpi") or "")
            mezzi = ", ".join(f.get("mezzi", [])) if isinstance(f.get("mezzi"), list) else (f.get("mezzi") or "")
            rows.append([f.get("fase", f.get("nome", "")), f.get("descrizione", ""), rischi, dpi, mezzi])
        if rows:
            add_data_table(doc, ["Fase", "Descrizione", "Rischi", "DPI", "Mezzi"], rows)
        return

    phases.sort(key=lambda p: p.ordine)
    name_by_id = {p.id: p.nome for p in phases}

    # --- 1. Quadro sinottico (fasi + precedenze) -----------------------
    add_paragraph(
        doc,
        "Quadro sinottico delle fasi lavorative in ordine di esecuzione. "
        "La colonna 'Dipende da' esplicita le fasi che devono essere "
        "completate prima dell'avvio della fase in riga (Gantt logico).",
        italic=True,
    )
    synoptic_rows = []
    for i, ph in enumerate(phases, 1):
        deps = ", ".join(name_by_id.get(d, d) for d in ph.dipende_da) or "—"
        synoptic_rows.append([str(i), ph.nome, deps])
    add_data_table(doc, ["#", "Fase", "Dipende da"], synoptic_rows)

    # --- 2. Per-phase detail ------------------------------------------
    for i, ph in enumerate(phases, 1):
        add_heading(doc, f"{i}. {ph.nome}", level=4)
        if ph.descrizione:
            add_paragraph(doc, ph.descrizione)

        detail_rows: list[tuple[str, str]] = [
            ("Rischi", ", ".join(ph.rischi) or "—"),
            ("DPI", ", ".join(ph.dpi) or "—"),
            ("Mezzi / attrezzature", ", ".join(ph.mezzi) or "—"),
        ]
        if ph.dipende_da:
            detail_rows.append(
                ("Precedenze", ", ".join(name_by_id.get(d, d) for d in ph.dipende_da))
            )
        add_kv_table(doc, detail_rows)

        if ph.niosh is not None:
            add_paragraph(doc, "Valutazione NIOSH (movimentazione manuale dei carichi):", bold=True)
            add_kv_table(
                doc,
                [
                    ("Peso sollevato (kg)", f"{ph.niosh.peso_sollevato:.2f}"),
                    ("Costante di peso CP (kg)", f"{ph.niosh.cp:.2f}"),
                    ("Fattori A·B·C·D·E·F", (
                        f"{ph.niosh.fattore_a:.2f} · {ph.niosh.fattore_b:.2f} · "
                        f"{ph.niosh.fattore_c:.2f} · {ph.niosh.fattore_d:.2f} · "
                        f"{ph.niosh.fattore_e:.2f} · {ph.niosh.fattore_f:.2f}"
                    )),
                    ("PLR (kg)", f"{ph.niosh.plr:.2f}" if ph.niosh.plr is not None else "—"),
                    ("IR", f"{ph.niosh.ir:.2f}" if ph.niosh.ir is not None else "—"),
                    ("Zona di rischio", ph.niosh.livello or "—"),
                ],
            )

        if ph.rumore is not None:
            add_paragraph(doc, "Esposizione al rumore:", bold=True)
            add_kv_table(
                doc,
                [
                    ("LEX,8h (dB(A))", f"{ph.rumore.lex_8h_dba:.1f}"),
                    ("Fascia", ph.rumore.fascia or "—"),
                    ("DPI uditivi obbligatori", "SI" if ph.rumore.dpi_obbligatori else "NO"),
                    ("Note", ph.rumore.note or "—"),
                ],
            )

        if ph.vibrazioni is not None:
            add_paragraph(doc, "Esposizione a vibrazioni meccaniche:", bold=True)
            add_kv_table(
                doc,
                [
                    ("A(8) mano-braccio (m/s²)",
                     f"{ph.vibrazioni.a8_mano_braccio:.2f}" if ph.vibrazioni.a8_mano_braccio is not None else "—"),
                    ("A(8) corpo intero (m/s²)",
                     f"{ph.vibrazioni.a8_corpo_intero:.2f}" if ph.vibrazioni.a8_corpo_intero is not None else "—"),
                    ("Entro i limiti di legge", "SI" if ph.vibrazioni.entro_limiti else "NO"),
                    ("Note", ph.vibrazioni.note or "—"),
                ],
            )

    # --- 3. Dependency-order footnote ---------------------------------
    violations = dependency_violations_after_ordering(phases)
    if violations:
        add_paragraph(
            doc,
            "Nota: le seguenti fasi risultano ordinate prima di una loro "
            "dichiarata precedenza. Verificare la programmazione del cantiere "
            "prima dell'avvio dei lavori.",
            italic=True,
            bold=True,
        )
        for dependent, missing in violations:
            add_paragraph(doc, f"  • '{dependent}' dipende da '{missing}' ma la precede nell'ordine.")


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
