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
from app.services.dpi_rules import (
    DPI_CATALOG,
    PHASES_CONSTRUCTION,
    ROLES_CONSTRUCTION,
    build_default_matrix,
)

# Italian labels for the standard phases — used when the operator hasn't
# defined custom fasi yet so the document still ships with a defensible
# 8-phase skeleton (D.Lgs. 81/2008 All. XV punto 3.2.1 d).
_PHASE_LABELS_IT: dict[str, str] = {
    "allestimento_cantiere": "Allestimento del cantiere",
    "scavi": "Scavi e movimento terra",
    "fondazioni": "Fondazioni",
    "getto_calcestruzzo": "Getto del calcestruzzo",
    "montaggio_ponteggi": "Montaggio dei ponteggi",
    "opere_murarie": "Opere murarie / strutturali",
    "finiture": "Finiture (intonaco, copertura, facciata)",
    "smobilizzo_cantiere": "Smobilizzo del cantiere",
}

# Italian labels for the standard construction roles.
_ROLE_LABELS_IT: dict[str, str] = {
    "carpentiere": "Carpentiere",
    "manovale": "Manovale",
    "gruista": "Gruista",
    "operatore_escavatore": "Operatore escavatore",
    "ponteggiatore": "Ponteggiatore",
    "saldatore": "Saldatore",
    "elettricista": "Elettricista",
    "muratore": "Muratore",
    "capo_cantiere": "Capo cantiere",
    "autista_mezzi": "Autista mezzi",
}
from app.services.pos_phases import dependency_violations_after_ordering
from app.schemas.pos_phase import PosPhase
from pydantic import ValidationError

TEMPLATE = TEMPLATES_DIR / "POS.docx"
TIPO_DOC = "pos"


class PosGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        persone = data.get("persone") or []
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

            # Anagrafica + dati cantiere (header)
            add_kv_table(doc, [
                ("Impresa esecutrice", azienda.ragione_sociale or ""),
                ("Indirizzo cantiere", p.cantiere_indirizzo or ""),
                ("Descrizione", p.cantiere_descrizione or ""),
                ("Data inizio", p.data_inizio.strftime("%d/%m/%Y") if p.data_inizio else "—"),
                ("Data fine", p.data_fine.strftime("%d/%m/%Y") if p.data_fine else "—"),
                ("Importo lavori", f"{float(p.importo_lavori):,.2f} EUR" if p.importo_lavori else "—"),
                ("Numero massimo lavoratori", str(p.numero_massimo_lavoratori) if p.numero_massimo_lavoratori else "—"),
            ])

            # Soggetti di riferimento (All. XV punto 3.2.1 b)
            add_heading(doc, "Soggetti di riferimento", level=3)
            add_kv_table(doc, [
                ("Committente", p.committente or "—"),
                ("Progettista responsabile", p.progettista_responsabile or "—"),
                ("Direttore dei lavori", p.direttore_lavori or "—"),
                ("Direttore operativo edilizia / strutture", p.direttore_operativo_edilizia or "—"),
                ("Direttore operativo impianti", p.direttore_operativo_impianti or "—"),
                ("Responsabile dei lavori", p.responsabile_lavori or "—"),
                ("Coordinatore per la sicurezza in fase di progettazione (CSP)", p.coordinatore_progettazione or "—"),
                ("Coordinatore per la sicurezza in fase di esecuzione (CSE)", p.coordinatore_sicurezza or "—"),
            ])

            # Dipendenti dell'azienda — tabella ruoli operativi
            _render_dipendenti_table(doc, persone)

            # Modalità organizzative (All. XV punto 3.2.1 c)
            _render_modalita_organizzative(doc, p)

            # Organizzazione logistica
            _render_organizzazione_logistica(doc, p)

            add_heading(doc, "Fasi lavorative", level=3)
            fasi = p.fasi_lavorative or []
            if fasi:
                _render_phase_sections(doc, fasi)
            else:
                _render_default_phase_skeleton(doc)

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
# Dipendenti / modalità organizzative / organizzazione logistica
# ---------------------------------------------------------------------------


def _render_dipendenti_table(doc, persone: list) -> None:
    """Render the "Dipendenti dell'azienda" table required by Luca's
    2026-05-25 annotated template — Nominativo / Mansione / Primo Soccorso /
    Antincendio / Preposto. Pulled live from the azienda's Persona rows.
    """
    add_heading(doc, "Dipendenti dell'azienda", level=3)
    if not persone:
        add_paragraph(doc, "Nessun dipendente registrato.", italic=True)
        return
    rows = []
    for pe in persone:
        rows.append([
            pe.nominativo or "—",
            pe.mansione or "—",
            "SI" if getattr(pe, "ruolo_primo_soccorso", False) else "NO",
            "SI" if getattr(pe, "ruolo_antincendio", False) else "NO",
            "SI" if getattr(pe, "ruolo_preposto", False) else "NO",
        ])
    add_data_table(
        doc,
        ["Nominativo", "Mansione", "Addetto Primo Soccorso", "Addetto Antincendio", "Preposto"],
        rows,
    )


def _render_modalita_organizzative(doc, pos) -> None:
    """Render the "Modalità organizzative" section (All. XV punto 3.2.1 c).

    All three fields are free-text. Skip the section entirely if none of
    them is populated, to avoid printing an empty section on small POS.
    """
    items = [
        ("Orario di lavoro", pos.orario_lavoro_cantiere),
        ("Turni", pos.turni_descrizione),
        # Feedback #57 (2026-05-26): label "Riunioni di coordinamento"
        # rinominato in "Descrizione del cantiere". DB column unchanged
        # (riunioni_coordinamento) — solo etichetta utente / docx.
        ("Descrizione del cantiere", pos.riunioni_coordinamento),
    ]
    if not any(v for _, v in items):
        return
    add_heading(doc, "Modalità organizzative", level=3)
    for label, value in items:
        if not value:
            continue
        add_paragraph(doc, label + ":", bold=True)
        add_paragraph(doc, value)


def _render_organizzazione_logistica(doc, pos) -> None:
    """Render the "Organizzazione logistica" section.

    `monoblocchi_installati` drives the boilerplate line ("Non saranno
    installati monoblocchi" vs the dettagli text). `modalita_pasti` is a
    free-text paragraph.
    """
    if not (
        pos.monoblocchi_installati
        or pos.monoblocchi_dettagli
        or pos.modalita_pasti
    ):
        return
    add_heading(doc, "Organizzazione logistica", level=3)
    if pos.monoblocchi_installati:
        add_paragraph(doc, "Monoblocchi installati in cantiere:", bold=True)
        add_paragraph(doc, pos.monoblocchi_dettagli or "Sì — dettagli da specificare.")
    else:
        add_paragraph(doc, "Non saranno installati monoblocchi in cantiere.")
    if pos.modalita_pasti:
        add_paragraph(doc, "Modalità consumazione pasti:", bold=True)
        add_paragraph(doc, pos.modalita_pasti)


# ---------------------------------------------------------------------------
# DPI matrix (US-4.8)
# ---------------------------------------------------------------------------


def _dpi_labels(codes: list[str]) -> str:
    """Render a list of DPI codes as comma-separated Italian labels.

    Feedback #61 (2026-05-26): the frontend stores the literal string
    ``__non_effettua__`` in a cell when the operator declared that a
    role does not perform a given phase. We collapse it to a single
    Italian-readable label so the printed POS doesn't leak the sentinel.
    """
    if not codes:
        return "—"
    if "__non_effettua__" in codes:
        return "Non effettua questa operazione"
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


def _render_default_phase_skeleton(doc) -> None:
    """Emit the 8 standard construction phases as a review-and-customize
    skeleton when the operator hasn't created custom fasi yet.

    Per D.Lgs. 81/2008 All. XV punto 3.2.1 d the POS must list le fasi
    lavorative previste in cantiere. The 8 default phases are the most
    common phases for an Italian cantiere edile; the operator is expected
    to remove/modify in fase di audit so the matrix matches the actual
    project. The Italian heading explains this so an inspector reading
    the doc understands why the rows look generic.
    """
    add_paragraph(
        doc,
        "Le fasi lavorative non sono ancora state personalizzate per "
        "questo cantiere. Di seguito le 8 fasi standard per un cantiere "
        "edile da rivedere con il Coordinatore CSE prima dell'inizio "
        "dei lavori.",
        italic=True,
        size=9,
    )
    rows = []
    for i, phase_key in enumerate(PHASES_CONSTRUCTION, 1):
        rows.append([str(i), _PHASE_LABELS_IT.get(phase_key, phase_key)])
    add_data_table(doc, ["#", "Fase standard"], rows)


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

    # If the operator hasn't configured a matrix yet, fall back to the
    # standard 10 roles × 8 phases default produced by build_default_matrix.
    # Mark the whole table as "default" so the reviewer knows it's a
    # rules-engine suggestion, not a per-client choice.
    using_default = False
    if not matrix or not roles or not phases:
        roles = ROLES_CONSTRUCTION
        phases = PHASES_CONSTRUCTION
        matrix = build_default_matrix(roles, phases)
        using_default = True

    add_heading(doc, "Matrice DPI per ruolo e fase", level=3)
    if using_default:
        add_paragraph(
            doc,
            "La matrice seguente e generata automaticamente dalle regole "
            "predefinite (D.Lgs. 81/2008 art. 77 e Tit. III). Il Datore di "
            "Lavoro verifica e personalizza ogni cella in fase di audit.",
            italic=True,
            size=9,
        )

    # Pre-compute defaults once so we can detect operator overrides.
    defaults = build_default_matrix(roles, phases)

    header = ["Ruolo"] + [_PHASE_LABELS_IT.get(p, p) for p in phases]
    data_rows: list[list[str]] = []
    for role in roles:
        row: list[str] = [_ROLE_LABELS_IT.get(role, role)]
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
