"""DUVRI - Documento Unico Valutazione Rischi Interferenze (art. 26 D.Lgs. 81/2008)."""

import os
import unicodedata

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator import data_loader as _data_loader
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_duvri
from app.services.document_generator.design import finish_document
from app.services.document_generator.docx_utils import (
    TEMPLATES_DIR,
    _norm_text,
    _set_cell_text_keep_format,
    _set_paragraph_text_keep_format,
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    format_sede,
    page_break,
    replace_placeholders,
    scrub_body,
    slugify,
)

TEMPLATE = TEMPLATES_DIR / "DUVRI.docx"
TIPO_DOC = "duvri"
UNKNOWN_ENVIRONMENT = "Ambiente non disponibile"


def _normalize_display_text(value) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _company_equipment_rows(data: dict) -> list[list[str]]:
    environment_names = {
        str(ambiente.id): _normalize_display_text(ambiente.nome)
        or UNKNOWN_ENVIRONMENT
        for ambiente in data["ambienti"]
        if getattr(ambiente, "id", None) is not None
    }
    records = []
    for equipment in data["attrezzature"]:
        description = _normalize_display_text(
            getattr(equipment, "descrizione", None)
        )
        if not description:
            continue
        environment = environment_names.get(
            str(getattr(equipment, "ambiente_id", None)),
            UNKNOWN_ENVIRONMENT,
        )
        records.append((
            environment,
            description,
            str(getattr(equipment, "id", "")),
        ))
    records.sort(
        key=lambda record: (
            record[0].casefold(),
            record[1].casefold(),
            record[2],
        )
    )
    return [[description, environment] for environment, description, _ in records]


def _body_paragraph_with_marker(doc: Document, marker: str):
    marker = marker.casefold()
    return next(
        (
            paragraph
            for paragraph in doc.paragraphs
            if marker in paragraph.text.casefold()
        ),
        None,
    )


def _add_company_equipment(doc: Document, rows: list[list[str]]) -> list:
    blocks = [add_heading(doc, "Attrezzature del committente", level=2)._p]
    if rows:
        blocks.append(
            add_data_table(
                doc,
                ["Attrezzatura del committente", "Ambiente"],
                rows,
            )._element
        )
    else:
        blocks.append(
            add_paragraph(
                doc,
                "Nessuna attrezzatura registrata nel Rischio Master.",
                italic=True,
            )._p
        )
    return blocks


def _insert_company_equipment_at_legacy_anchor(
    doc: Document,
    rows: list[list[str]],
) -> bool:
    anchor = _body_paragraph_with_marker(
        doc,
        "Attrezzature e mezzi messi a disposizione dal Committente",
    )
    if anchor is None:
        return False
    for block in _add_company_equipment(doc, rows):
        anchor._p.addprevious(block)
    return True


def _remove_body_paragraph_block(
    doc: Document,
    start_marker: str,
    end_marker: str,
    *,
    replacement: str | None = None,
) -> bool:
    """Remove a legacy body block delimited by stable text anchors."""
    paragraphs = list(doc.paragraphs)
    start = next(
        (
            index
            for index, paragraph in enumerate(paragraphs)
            if start_marker.casefold() in paragraph.text.casefold()
        ),
        None,
    )
    if start is None:
        return False
    end = next(
        (
            index
            for index, paragraph in enumerate(paragraphs[start:], start)
            if end_marker.casefold() in paragraph.text.casefold()
        ),
        None,
    )
    if end is None:
        return False
    if replacement:
        replacement_paragraph = add_paragraph(doc, replacement)
        paragraphs[start]._p.addprevious(replacement_paragraph._p)
    for paragraph in paragraphs[start : end + 1]:
        paragraph._p.getparent().remove(paragraph._p)
    return True


def _replace_body_tables_with_anchor(
    doc: Document,
    marker: str,
    replacement: str,
) -> None:
    """Replace donor tables with a narrow reference to current appalto data."""
    marker = marker.casefold()
    for table in list(doc.tables):
        table_text = "\n".join(
            cell.text for row in table.rows for cell in row.cells
        ).casefold()
        if marker in table_text:
            replacement_paragraph = add_paragraph(doc, replacement)
            table._element.addprevious(replacement_paragraph._p)
            table._element.getparent().remove(table._element)


def _remove_legacy_donor_equipment(doc: Document) -> None:
    """Drop template-only equipment examples without touching generic DUVRI text."""
    _remove_body_paragraph_block(
        doc,
        "Attrezzature e mezzi messi a disposizione dal Committente",
        "L’utilizzo di tali attrezzature avviene all’interno degli spazi aziendali condivisi",
    )
    _remove_body_paragraph_block(
        doc,
        "Movimentazione materiali – Muletto / Transpallet",
        "In caso di utilizzo contemporaneo, le attività sono coordinate tra preposti",
        replacement=(
            "Le misure di coordinamento applicabili sono riportate, per ciascun "
            "appalto, nella sezione Interferenze identificate in calce al "
            "presente documento."
        ),
    )
    _remove_body_paragraph_block(
        doc,
        "ATTIVITÀ DI SALDATURA – SVOLTA DA",
        "È vietato depositare materiali combustibili nelle aree limitrofe durante le operazioni",
    )
    _replace_body_tables_with_anchor(
        doc,
        "Attività operative RECOM",
        "Le date e le attività di ciascun appalto sono riportate nelle relative "
        "sezioni in calce al presente documento.",
    )
    _replace_body_tables_with_anchor(
        doc,
        "Possibili rischi/interferenze per RECOM",
        "Le attrezzature e le attività dell’appaltatore, con le relative "
        "interferenze, sono riportate nelle sezioni dedicate ai singoli appalti "
        "in calce al presente documento.",
    )


# ---------------------------------------------------------------------------
# Template body filling (segnalazione 2026-10-02 "rivedere la generazione
# output del documento DUVRI"). The donor template is kept for its fixed
# text, but its forms used to come out empty or with the donor's own data
# (Peschiera Borromeo phone numbers, "DA DEFINIRE" dates, dotted blanks).
# Each helper finds its form by content, never by position, and fills only
# what the platform knows; anything unknown stays blank for the pen.
# ---------------------------------------------------------------------------

_DOTS = "….·."


def _is_dotted(text: str) -> bool:
    t = (text or "").strip()
    return len(t) >= 2 and all(ch in _DOTS for ch in t)


def _fmt_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _role_names(persone, flag: str) -> str:
    return ", ".join(
        (getattr(p, "nominativo", None) or "").strip()
        for p in persone
        if getattr(p, flag, False) and (getattr(p, "nominativo", None) or "").strip()
    )


def _periodo(duvri_rows) -> tuple[str, str, str]:
    """Overall start, end and duration across the appalti."""
    starts = [d.data_inizio for d in duvri_rows if getattr(d, "data_inizio", None)]
    ends = [d.data_fine for d in duvri_rows if getattr(d, "data_fine", None)]
    inizio = min(starts) if starts else None
    fine = max(ends) if ends else None
    durata = ""
    if inizio and fine and fine >= inizio:
        giorni = (fine - inizio).days + 1
        durata = f"dal {_fmt_date(inizio)} al {_fmt_date(fine)} ({giorni} giorni)"
    return _fmt_date(inizio), _fmt_date(fine), durata


def _set_cell_all_text(cell, text: str) -> None:
    """Replace every text node of a cell, including runs nested in
    hyperlinks or fields that python-docx's ``paragraph.runs`` skips."""
    from docx.oxml.ns import qn

    nodes = list(cell._tc.iter(qn("w:t")))
    if not nodes:
        _set_cell_text_keep_format(cell, text)
        return
    nodes[0].text = text
    for node in nodes[1:]:
        node.text = ""


def _unique_cells(row) -> list:
    out = []
    for cell in row.cells:
        if not any(cell._tc is c._tc for c in out):
            out.append(cell)
    return out


def _fill_after_label(row, label_contains: str, value: str) -> bool:
    """Write ``value`` into the first empty cell after the label cell."""
    if not value:
        return False
    cells = _unique_cells(row)
    for i, cell in enumerate(cells):
        if _norm_text(label_contains) in _norm_text(cell.text):
            for target in cells[i + 1:]:
                if not (target.text or "").strip():
                    _set_cell_text_keep_format(target, value)
                    return True
            return False
    return False


def _fill_anagrafica(table, values: list[tuple[str, str]]) -> None:
    for row in table.rows:
        for label, value in values:
            if _fill_after_label(row, label, value):
                break


def _anagrafica_tables(doc: Document) -> list:
    """The committente and the appaltatore forms, in document order."""
    from docx.table import Table

    found = []
    for table in doc.tables:
        labels = " ".join(_norm_text(r.cells[0].text) for r in table.rows if r.cells)
        if "ragione sociale" in labels and "medico competente" in labels and "tel" in labels:
            found.append(Table(table._tbl, doc))
    return found


def _table_starting_with(doc: Document, text: str):
    needle = _norm_text(text)
    for table in doc.tables:
        if table.rows and _norm_text(table.rows[0].cells[0].text).startswith(needle):
            return table
    return None


def _fill_rows(table, rows: list[list[str]]) -> None:
    """Write ``rows`` below the header row, adding rows when needed and
    blanking the donor's surplus ones."""
    body = list(table.rows)[1:]
    for index, values in enumerate(rows):
        if index < len(body):
            cells = _unique_cells(body[index])
        else:
            cells = _unique_cells(table.add_row())
        for cell, value in zip(cells, values):
            _set_cell_text_keep_format(cell, value or "")
    for row in body[len(rows):]:
        for cell in _unique_cells(row):
            _set_cell_text_keep_format(cell, "")


_INCENDIO_LIVELLI = {
    "BASSO": None,  # the template already explains "basso"
    "MEDIO": (
        "Il rischio incendio “medio” indica una situazione in cui sono presenti sostanze "
        "infiammabili o materiali combustibili in quantità significative e/o sorgenti di "
        "innesco non trascurabili, con una possibile propagazione dell'incendio limitata; "
        "le misure di prevenzione, la formazione degli addetti e le procedure di emergenza "
        "devono essere coordinate tra committente e appaltatore."
    ),
    "ALTO": (
        "Il rischio incendio “alto” indica una situazione in cui la presenza di sostanze "
        "altamente infiammabili, carichi d'incendio elevati o sorgenti di innesco frequenti "
        "rende probabile lo sviluppo e la rapida propagazione di un incendio; prima dell'avvio "
        "delle attività l'appaltatore riceve istruzioni specifiche e gli addetti antincendio "
        "di entrambe le imprese sono formati per il livello di rischio alto."
    ),
}


def _fill_template_body(doc: Document, azienda, persone, duvri_rows, incendio_rows) -> None:
    ragione = azienda.ragione_sociale or ""
    lavoratori = [p for p in persone if not getattr(p, "is_esterno", False)]
    ddl = _role_names(persone, "ruolo_datore_lavoro")
    appaltatori = [d.appaltatore_ragione_sociale for d in duvri_rows if d.appaltatore_ragione_sociale]
    appaltatore = "; ".join(dict.fromkeys(appaltatori))
    sede_lavori = format_sede(azienda, "operativa")
    if sede_lavori == "—":
        sede_lavori = format_sede(azienda, "legale")
    inizio, fine, durata = _periodo(duvri_rows)

    # Anagrafica committente, then the appaltatore's own form.
    forms = _anagrafica_tables(doc)
    if forms:
        _fill_anagrafica(forms[0], [
            ("Ragione Sociale", ragione),
            ("Sede Legale", format_sede(azienda, "legale").replace("—", "")),
            ("Tel", getattr(azienda, "telefono", None) or ""),
            ("Datore di Lavoro", ddl),
            ("R.S.P.P", _role_names(persone, "ruolo_rspp")),
            ("Medico Competente", _role_names(persone, "ruolo_medico_competente")),
            ("R.L.S", _role_names(persone, "ruolo_rls")),
        ])
    if len(forms) > 1 and duvri_rows:
        first = duvri_rows[0]
        ragione_app = appaltatore
        if len(duvri_rows) == 1 and first.appaltatore_partita_iva:
            ragione_app = f"{appaltatore} (P.IVA {first.appaltatore_partita_iva})"
        _fill_anagrafica(forms[1], [("Ragione Sociale", ragione_app)])

    # Committente dell'opera / Responsabile dei Lavori.
    opera = _table_starting_with(doc, "Committente dell")
    if opera is not None:
        for row in opera.rows:
            _fill_after_label(row, "Committente dell", ragione)
            _fill_after_label(row, "Responsabile dei Lavori", ddl)

    # Dati relativi all'attività in appalto.
    attivita = _table_starting_with(doc, "Descrizione delle attività affidate")
    if attivita is not None:
        rows = list(attivita.rows)
        oggetti = "; ".join(dict.fromkeys(d.oggetto_appalto for d in duvri_rows if d.oggetto_appalto))
        if len(rows) > 1 and oggetti:
            _set_cell_text_keep_format(_unique_cells(rows[1])[0], oggetti)
        if len(rows) > 3:
            via = (getattr(azienda, "sede_operativa_via", None) or getattr(azienda, "sede_legale_via", None) or "").strip()
            if via:
                _set_cell_text_keep_format(_unique_cells(rows[3])[0], via)
        citta = (getattr(azienda, "sede_operativa_citta", None) or getattr(azienda, "sede_legale_citta", None) or "").strip()
        provincia = (getattr(azienda, "provincia_operativa", None) or getattr(azienda, "provincia_legale", None) or "").strip()
        for row in rows:
            _fill_after_label(row, "Città", citta)
            _fill_after_label(row, "Provincia", provincia)
            _fill_after_label(row, "Data inizio attività", inizio)
            _fill_after_label(row, "Durata attività", durata)

    # Elenco lavoratori del committente.
    elenco = _table_starting_with(doc, "Azienda Committente")
    if elenco is not None and _norm_text(elenco.rows[0].cells[1].text).startswith("nominativo"):
        _fill_rows(elenco, [
            [ragione, (p.nominativo or "").strip(), (p.mansione or "").strip()]
            for p in lavoratori
            if (p.nominativo or "").strip()
        ] or [["", "", ""]])

    # Soggetti di riferimento per le emergenze.
    emergenze = next(
        (
            t for t in doc.tables
            if t.rows
            and len(t.rows[0].cells) >= 3
            and _norm_text(t.rows[0].cells[0].text).strip() == "azienda"
            and _norm_text(t.rows[0].cells[1].text).strip().startswith("ruolo")
        ),
        None,
    )
    if emergenze is not None:
        body = list(emergenze.rows)[1:]
        for index, row in enumerate(body):
            cells = _unique_cells(row)
            if len(cells) < 3:
                continue
            ruolo = _norm_text(cells[1].text)
            committente_row = index < 2
            azienda_nome = ragione if committente_row else appaltatore
            if azienda_nome and not cells[0].text.strip():
                _set_cell_text_keep_format(cells[0], azienda_nome)
            if committente_row and not cells[2].text.strip():
                flag = "ruolo_antincendio" if "antincendio" in ruolo else "ruolo_primo_soccorso"
                nomi = _role_names(lavoratori, flag)
                if nomi:
                    _set_cell_text_keep_format(cells[2], nomi)

    # Numeri utili: the donor's local numbers go; the single European number
    # stays (as asked for the PEE, segnalazione 2026-08-03).
    for table in doc.tables:
        text = " ".join(c.text for r in table.rows for c in r.cells)
        if "Carabinieri" in text and "112" in text and len(table.columns) == 2:
            rows = list(table.rows)
            cells = _unique_cells(rows[0])
            _set_cell_all_text(
                cells[0],
                "Numero Unico di Emergenza (Carabinieri, Polizia, Vigili del Fuoco, Emergenza sanitaria)",
            )
            _set_cell_all_text(cells[1], "112")
            for row in rows[1:]:
                row._tr.getparent().remove(row._tr)
            break

    # Dates of the interference analysis.
    for paragraph in doc.paragraphs:
        text = _norm_text(paragraph.text)
        if text.startswith("data inizio:") and inizio:
            _set_paragraph_text_keep_format(paragraph, f"DATA INIZIO: {inizio}")
        elif text.startswith("data fine:"):
            _set_paragraph_text_keep_format(paragraph, f"DATA FINE: {fine or 'DA DEFINIRE'}")
        elif text.startswith("durata interferenza:"):
            _set_paragraph_text_keep_format(
                paragraph, f"DURATA INTERFERENZA: {durata or 'DA DEFINIRE'}"
            )

    # Fire risk level from the client's own incendio assessment.
    livelli = [(getattr(r, "livello_rischio", None) or "").upper() for r in incendio_rows]
    livello = next((lv for lv in ("ALTO", "MEDIO", "BASSO") if lv in livelli), None)
    if livello:
        for table in doc.tables:
            cells = _unique_cells(table.rows[0]) if table.rows else []
            if cells and _norm_text(cells[0].text).startswith("classificazione del livello di rischio incendio") and len(cells) >= 3:
                _set_cell_text_keep_format(cells[1], livello)
                if _INCENDIO_LIVELLI[livello]:
                    _set_cell_text_keep_format(cells[2], _INCENDIO_LIVELLI[livello])
                break

    _fill_dotted_blanks(doc, ddl=ddl, ragione=ragione, appaltatore=appaltatore, sede=sede_lavori)


def _fill_dotted_blanks(doc: Document, *, ddl: str, ragione: str, appaltatore: str, sede: str) -> None:
    """Fill the donor's "………" blanks whose meaning is clear from the text
    before them; any other blank is left for the pen."""
    for paragraph in doc.paragraphs:
        runs = paragraph.runs
        before = ""
        for run in runs:
            if _is_dotted(run.text):
                ctx = _norm_text(before)
                value = ""
                if ctx.endswith("il sottoscritto,"):
                    value = ddl
                elif ctx.endswith("datore di lavoro della"):
                    value = ragione
                elif ctx.endswith("presso"):
                    value = f" {sede}" if sede and sede != "—" else ""
                elif ctx.endswith("datore di lavoro committente ("):
                    value = ddl
                elif ctx.endswith(("impresa appaltatrice (", "personale di")) or not ctx:
                    value = appaltatore
                if value:
                    run.text = value
            before += run.text


class DuvriGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        duvri_rows = await load_duvri(self.db, self.azienda_id)
        company_equipment_rows = _company_equipment_rows(data)
        company_equipment_inserted = False

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
            # Blank the sample dates left in the template body; the generator
            # supplies the real appalto/sottoscrizione dates below.
            scrub_body(doc, {"01.11.2025": "__/__/____", "15/01/2026": "__/__/____"})
            company_equipment_inserted = _insert_company_equipment_at_legacy_anchor(
                doc,
                company_equipment_rows,
            )
            _remove_legacy_donor_equipment(doc)
            # Through the module so test harnesses can patch the loader.
            incendio_rows = await _data_loader.load_incendio(self.db, self.azienda_id)
            _fill_template_body(doc, azienda, data.get("persone") or [], duvri_rows, incendio_rows)
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"DUVRI - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Committente", azienda.ragione_sociale or ""),
            ("Sede", format_sede(azienda, "legale")),
            ("P.IVA committente", azienda.partita_iva or ""),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimento normativo", "Art. 26 D.Lgs. 81/2008 e D.Lgs. 106/2009"),
        ])

        add_heading(doc, "Oggetto del documento", level=2)
        add_paragraph(doc, "Il presente DUVRI individua le misure di prevenzione e protezione necessarie ad eliminare o ridurre al minimo i rischi derivanti dalle interferenze tra le attività del committente e quelle dell'impresa appaltatrice.")
        add_paragraph(doc, "Ai sensi dell'art. 26 comma 3-bis del D.Lgs. 81/2008 (introdotto dal D.Lgs. 106/2009), l'obbligo di redazione del DUVRI non si applica ai servizi di natura intellettuale, alle mere forniture di materiali o attrezzature, nonché ai lavori o servizi la cui durata non superi i cinque uomini-giorno, salvo che comportino rischi derivanti da agenti cancerogeni, biologici, atmosfere esplosive o dai rischi particolari di cui all'Allegato XI.")

        if not company_equipment_inserted:
            _add_company_equipment(doc, company_equipment_rows)

        if not duvri_rows:
            add_paragraph(doc, "Non risultano appalti attivi al momento della valutazione.", italic=True)
        for idx, d in enumerate(duvri_rows, 1):
            page_break(doc)
            add_heading(doc, f"{idx}. Appalto: {d.oggetto_appalto}", level=2)
            add_kv_table(doc, [
                ("Appaltatore", d.appaltatore_ragione_sociale or ""),
                ("P.IVA appaltatore", d.appaltatore_partita_iva or ""),
                ("Referente", d.appaltatore_referente or ""),
                ("Oggetto appalto", d.oggetto_appalto or ""),
                ("Data inizio", d.data_inizio.strftime("%d/%m/%Y") if d.data_inizio else "—"),
                ("Data fine", d.data_fine.strftime("%d/%m/%Y") if d.data_fine else "—"),
            ])
            if (d.note or "").strip():
                # Entered in the form but never printed before.
                add_heading(doc, "Note", level=3)
                add_paragraph(doc, d.note.strip())

            attrezz = d.attrezzature_appaltatore or []
            if attrezz:
                add_heading(doc, "Attrezzature / attività appaltatore", level=3)
                rows = [
                    [a.get("tipo", ""), a.get("descrizione", "") or ""]
                    for a in attrezz
                    if isinstance(a, dict)
                ]
                add_data_table(doc, ["Tipo", "Descrizione"], rows)

            add_heading(doc, "Interferenze identificate", level=3)
            interfs = d.interferenze or []
            if interfs:
                rows = []
                for i in interfs:
                    dpi = ", ".join(i.get("dpi", [])) if isinstance(i.get("dpi"), list) else (i.get("dpi") or "")
                    rows.append([i.get("rischio", ""), i.get("misure", ""), dpi])
                add_data_table(doc, ["Rischio da interferenza", "Misure di coordinamento", "DPI"], rows)
            else:
                add_paragraph(doc, "Nessuna interferenza rilevante identificata.", italic=True)

            add_heading(doc, "Sottoscrizione", level=3)
            add_data_table(doc, ["Ruolo", "Firma"], [
                ["Committente (Datore di Lavoro)", "________________________"],
                ["Appaltatore", "________________________"],
                ["Data", generated_at.strftime("%d/%m/%Y")],
            ])

        version = await self._next_version()
        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        filepath = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.docx")
        # Audit 2026-09-03: the donor template's header/footer carried the
        # legacy N2O letterhead and literal placeholders; rewrite them from
        # the organization's branding and set honest file properties.
        finish_document(
            doc,
            title='DUVRI - Valutazione dei Rischi da Interferenze',
            azienda=azienda,
            branding=self.branding,
            version=version,
            generated_at=generated_at,
            fill_cover=True,
            cover_values={
                "Oggetto dell'appalto": (duvri_rows[0].oggetto_appalto or '') if duvri_rows else '',
                'Azienda Committente': azienda.ragione_sociale or '',
                "Committente dell'opera": azienda.ragione_sociale or '',
                'Descrizione delle attività affidate in appalto': (duvri_rows[0].oggetto_appalto or '') if duvri_rows else '',
                'Datore di Lavoro Committente': next(
                    ((getattr(p, 'nominativo', None) or '') for p in (data.get('persone') or []) if getattr(p, 'ruolo_datore_lavoro', False)),
                    '',
                ),
                "Indirizzo presso cui si svolgerà l'appalto": format_sede(azienda, 'operativa') if format_sede(azienda, 'operativa') != '—' else format_sede(azienda, 'legale'),
            },
        )
        doc.save(filepath)
        return filepath

    async def _next_version(self) -> int:
        return await self.resolve_version([TIPO_DOC, "DUVRI"])
