"""
DVR Master document generator.

Generates the Documento di Valutazione dei Rischi (DVR) — the master risk
assessment document required by D.Lgs. 81/2008 for every Italian workplace.

Output: A .docx file with professional formatting including:
- Cover page with company name, date, and logo placeholder
- Table of contents placeholder
- Part I: Company data tables
- Part III: Risk assessment tables per environment with P/D/I color coding
- Part IV: Improvement measures placeholder
"""

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Mm, Pt, RGBColor

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.risk_calculator import calculate_risk_index


# ---------------------------------------------------------------------------
# Logo asset path (embedded on cover page when present)
# ---------------------------------------------------------------------------

_LOGO_PATH = Path(__file__).resolve().parents[3] / "assets" / "logo.png"


# ---------------------------------------------------------------------------
# Part II static boilerplate content (extracted to keep the file lean)
# ---------------------------------------------------------------------------

_METODOLOGIA_INTRO_1 = (
    "La presente valutazione dei rischi e redatta ai sensi dell'art. 28 del "
    "D.Lgs. 9 aprile 2008, n. 81 e s.m.i., che impone al Datore di Lavoro la "
    "valutazione di tutti i rischi per la sicurezza e la salute dei lavoratori, "
    "tenendo conto della specificita delle mansioni, delle attrezzature e degli "
    "ambienti di lavoro."
)

_METODOLOGIA_INTRO_2 = (
    "Il metodo adottato si fonda sulla stima dell'Indice di Rischio (I) "
    "calcolato attraverso la formula I = 2 x D + P, dove P rappresenta la "
    "Probabilita di accadimento dell'evento dannoso (scala 1-4) e D il Danno "
    "atteso per il lavoratore esposto (scala 1-4). L'indice risultante, "
    "compreso nell'intervallo 3-12, e associato a un livello di rischio e a "
    "una relativa priorita di intervento."
)

_RISK_LEVEL_TABLE_ROWS = [
    ("3-4", "ACCETTABILE", "Monitoraggio", "Continuo"),
    ("5-6", "MODESTO", "Strumenti di minimizzazione", "1 anno"),
    ("7-8", "GRAVE", "Sensibilizzazione + controllo", "6 mesi"),
    ("9-12", "GRAVISSIMO", "Ricerca urgente misure", "Immediatamente"),
]

_PROBABILITA_TABLE_ROWS = [
    ("1", "Bassa", "Raramente accade"),
    ("2", "Medio-Bassa", "Plausibile in certe condizioni"),
    ("3", "Medio-Alta", "Accade con una certa frequenza"),
    ("4", "Elevata", "Accade sistematicamente"),
]

_DANNO_TABLE_ROWS = [
    ("1", "Trascurabile", "Lesioni lievi reversibili"),
    ("2", "Modesto", "Inabilita temporanea reversibile"),
    ("3", "Notevole", "Lesioni permanenti parziali"),
    ("4", "Ingente", "Inabilita totale o decesso"),
]


# ---------------------------------------------------------------------------
# Color palette for risk levels
# ---------------------------------------------------------------------------

_RISK_COLORS = {
    "ACCETTABILE": RGBColor(0x4C, 0xAF, 0x50),   # Green
    "MODESTO": RGBColor(0xFF, 0xC1, 0x07),        # Amber
    "GRAVE": RGBColor(0xFF, 0x98, 0x00),           # Orange
    "GRAVISSIMO": RGBColor(0xF4, 0x43, 0x36),      # Red
}

_HEADER_BG = RGBColor(0x1A, 0x23, 0x7E)           # Dark blue for table headers
_HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)          # White text on headers
_LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)          # Alternating row background


class DVRMasterGenerator(BaseDocumentGenerator):
    """Generates the DVR Master document (.docx)."""

    async def generate(self) -> str:
        """Generate the DVR Master document.

        Returns:
            Absolute path to the generated .docx file.
        """
        data = await self.load_data()
        azienda = data["azienda"]

        doc = Document()
        self._setup_styles(doc)

        # Build document sections
        self._add_cover_page(doc, azienda, data["generated_at"])
        self._add_table_of_contents(doc)
        self._add_part_i(doc, azienda, data["persone"], data["attrezzature"])
        self._add_part_ii(doc, azienda)
        self._add_part_iii(doc, data["ambienti"])
        self._add_part_iv(doc)

        # Determine version and save with the filename pattern required
        # by US-2.8 AC2: DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx.
        # The <ragione_sociale> segment is slugified (lowercase,
        # alphanumeric + underscore) so the filename stays safe on both
        # POSIX and Windows checkouts. The date is the generation day
        # (UTC) so regenerations on the same day keep the same stamp.
        version = await self._get_next_version()
        output_dir = self._get_output_dir()
        slug = self._slugify(azienda.ragione_sociale or "azienda")
        date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        filename = f"DVR_{slug}_{date_stamp}_v{version}.docx"
        filepath = os.path.join(output_dir, filename)

        doc.save(filepath)
        return filepath

    @staticmethod
    def _slugify(text: str, max_length: int = 40) -> str:
        """Produce a filesystem-safe slug from a free-form label.

        Lowercases the input, replaces any non-alphanumeric character with
        an underscore, collapses repeated underscores and trims them from
        the edges, then truncates to ``max_length`` characters.
        """
        lowered = (text or "").lower()
        replaced = re.sub(r"[^a-z0-9]+", "_", lowered)
        collapsed = re.sub(r"_+", "_", replaced).strip("_")
        if not collapsed:
            collapsed = "azienda"
        return collapsed[:max_length].rstrip("_") or "azienda"

    async def _get_next_version(self) -> int:
        """Determine the next version number for this azienda's DVR."""
        from sqlalchemy import func, select
        from app.models.documento_generato import DocumentoGenerato

        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento == "dvr_master")
        )
        result = await self.db.execute(stmt)
        current_max = result.scalar()
        return current_max + 1

    # ------------------------------------------------------------------
    # Document styles setup
    # ------------------------------------------------------------------

    def _setup_styles(self, doc: Document) -> None:
        """Configure document-wide styles and defaults."""
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Calibri"
        font.size = Pt(10)

        # Heading styles
        for level in range(1, 4):
            heading_style = doc.styles[f"Heading {level}"]
            heading_style.font.name = "Calibri"
            heading_style.font.color.rgb = _HEADER_BG

        # Page margins
        for section in doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.0)

    # ------------------------------------------------------------------
    # Cover page
    # ------------------------------------------------------------------

    def _add_cover_page(
        self, doc: Document, azienda, generated_at: datetime
    ) -> None:
        """Add a professional cover page."""
        # Spacer
        for _ in range(6):
            doc.add_paragraph("")

        # Logo: embed from assets/logo.png if available, otherwise fall back
        # to an italic gray text placeholder so generation never breaks.
        if _LOGO_PATH.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            try:
                run.add_picture(str(_LOGO_PATH), width=Inches(2.0))
            except Exception:
                # Any image-loading issue degrades gracefully to the text
                # placeholder below (e.g. corrupt file).
                run.text = "[LOGO AZIENDALE]"
                run.font.size = Pt(14)
                run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
                run.font.italic = True
        else:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("[LOGO AZIENDALE]")
            run.font.size = Pt(14)
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            run.font.italic = True

        doc.add_paragraph("")

        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("DOCUMENTO DI VALUTAZIONE DEI RISCHI")
        run.bold = True
        run.font.size = Pt(24)
        run.font.color.rgb = _HEADER_BG

        # Subtitle
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("ai sensi del D.Lgs. 81/2008 e s.m.i.")
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph("")
        doc.add_paragraph("")

        # Company name
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(azienda.ragione_sociale.upper())
        run.bold = True
        run.font.size = Pt(18)

        # Address
        address_parts = []
        if azienda.sede_legale_via:
            address_parts.append(azienda.sede_legale_via)
        if azienda.sede_legale_citta:
            address_parts.append(azienda.sede_legale_citta)
        if address_parts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" — ".join(address_parts))
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        # Spacer
        for _ in range(4):
            doc.add_paragraph("")

        # Date and version info
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Data: {generated_at.strftime('%d/%m/%Y')}")
        run.font.size = Pt(12)

        # Page break
        doc.add_page_break()

    # ------------------------------------------------------------------
    # Table of contents placeholder
    # ------------------------------------------------------------------

    def _add_table_of_contents(self, doc: Document) -> None:
        """Add a table of contents placeholder page."""
        doc.add_heading("INDICE", level=1)

        p = doc.add_paragraph()
        run = p.add_run(
            "[Indice generato automaticamente — aggiornare dopo la revisione finale]"
        )
        run.font.italic = True
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        doc.add_paragraph("")

        # Manual TOC entries
        toc_entries = [
            ("PARTE I", "Dati Generali dell'Azienda"),
            ("PARTE II", "Descrizione dell'Attivita e dei Cicli Produttivi"),
            ("PARTE III", "Valutazione dei Rischi per Ambiente di Lavoro"),
            ("PARTE IV", "Programma di Miglioramento"),
        ]
        for part, title in toc_entries:
            p = doc.add_paragraph()
            run = p.add_run(f"{part} — {title}")
            run.font.size = Pt(11)

        doc.add_page_break()

    # ------------------------------------------------------------------
    # Part I — Company data
    # ------------------------------------------------------------------

    def _add_part_i(
        self, doc: Document, azienda, persone: list, attrezzature: list
    ) -> None:
        """Add Part I: company data tables."""
        doc.add_heading("PARTE I — DATI GENERALI DELL'AZIENDA", level=1)

        # Section 1: Anagrafica Aziendale
        doc.add_heading("1. Anagrafica Aziendale", level=2)
        company_data = [
            ("Ragione Sociale", azienda.ragione_sociale or "—"),
            ("Sede Legale", self._format_address(
                azienda.sede_legale_via, azienda.sede_legale_citta
            )),
            ("Sede Operativa", self._format_address(
                azienda.sede_operativa_via, azienda.sede_operativa_citta
            )),
            ("Attivita", azienda.attivita or "—"),
            ("Codice ATECO", azienda.codice_ateco or "—"),
            ("Orario di Lavoro", azienda.orario_lavoro or "—"),
            ("Metratura Totale", f"{azienda.metratura_totale} mq" if azienda.metratura_totale else "—"),
            ("Zona Sismica", str(azienda.zona_sismica) if azienda.zona_sismica else "—"),
        ]
        self._add_key_value_table(doc, company_data)

        doc.add_paragraph("")

        # Section 2: Figure della Sicurezza
        doc.add_heading("2. Figure della Sicurezza", level=2)
        safety_roles = {
            "Datore di Lavoro": [p for p in persone if p.ruolo_datore_lavoro],
            "RSPP": [p for p in persone if p.ruolo_rspp],
            "RLS": [p for p in persone if p.ruolo_rls],
            "Addetto Primo Soccorso": [p for p in persone if p.ruolo_primo_soccorso],
            "Addetto Antincendio": [p for p in persone if p.ruolo_antincendio],
            "Preposto": [p for p in persone if p.ruolo_preposto],
        }
        role_rows = []
        for role, role_persone in safety_roles.items():
            names = ", ".join(p.nominativo for p in role_persone) if role_persone else "—"
            role_rows.append((role, names))
        self._add_key_value_table(doc, role_rows)

        doc.add_paragraph("")

        # Section 3: Elenco Lavoratori
        doc.add_heading("3. Elenco Lavoratori", level=2)
        if persone:
            headers = ["N.", "Nominativo", "Mansione", "Contratto", "Sesso"]
            rows = []
            for i, p in enumerate(persone, 1):
                rows.append([
                    str(i),
                    p.nominativo,
                    p.mansione or "—",
                    p.tipologia_contrattuale or "—",
                    p.sesso or "—",
                ])
            self._add_data_table(doc, headers, rows)
        else:
            p = doc.add_paragraph("Nessun lavoratore registrato.")
            p.runs[0].font.italic = True

        doc.add_paragraph("")

        # Section 4: Attrezzature
        doc.add_heading("4. Attrezzature di Lavoro", level=2)
        if attrezzature:
            headers = ["N.", "Descrizione", "Marcatura CE", "Verifiche Periodiche"]
            rows = []
            for i, att in enumerate(attrezzature, 1):
                rows.append([
                    str(i),
                    att.descrizione,
                    "SI" if att.marcatura_ce else "NO",
                    "SI" if att.verifiche_periodiche else "NO",
                ])
            self._add_data_table(doc, headers, rows)
        else:
            p = doc.add_paragraph("Nessuna attrezzatura registrata.")
            p.runs[0].font.italic = True

        doc.add_page_break()

    # ------------------------------------------------------------------
    # Part II — Activity description and risk assessment methodology
    # ------------------------------------------------------------------

    def _add_part_ii(self, doc: Document, azienda) -> None:
        """Add Part II: activity description and risk methodology.

        Renders four sub-sections:
          2.1 Descrizione dell'Attivita (from azienda fields, with placeholder
              fallback when the survey field is empty).
          2.2 Metodologia di Valutazione dei Rischi (static boilerplate with
              a color-coded risk-level lookup table).
          2.3 Scala di Probabilita (P).
          2.4 Scala del Danno (D).
        """
        doc.add_heading(
            "PARTE II — DESCRIZIONE DELL'ATTIVITA E METODOLOGIA DI VALUTAZIONE",
            level=1,
        )

        # 2.1 — Activity description
        doc.add_heading("2.1 Descrizione dell'Attivita", level=2)

        descrizione = (azienda.descrizione_attivita or "").strip()
        if descrizione:
            p = doc.add_paragraph()
            run = p.add_run(descrizione)
            run.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            run = p.add_run(
                "[Descrizione dell'attivita da compilare durante la revisione]"
            )
            run.font.size = Pt(10)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        contesto = (getattr(azienda, "contesto_territoriale", None) or "").strip()
        if contesto:
            p = doc.add_paragraph()
            run = p.add_run(f"Contesto territoriale: {contesto}")
            run.font.size = Pt(10)

        doc.add_paragraph("")

        # 2.2 — Risk assessment methodology
        doc.add_heading("2.2 Metodologia di Valutazione dei Rischi", level=2)

        p = doc.add_paragraph()
        run = p.add_run(_METODOLOGIA_INTRO_1)
        run.font.size = Pt(10)

        p = doc.add_paragraph()
        run = p.add_run(_METODOLOGIA_INTRO_2)
        run.font.size = Pt(10)

        doc.add_paragraph("")
        self._add_risk_level_table(doc)
        doc.add_paragraph("")

        # 2.3 — Probability scale
        doc.add_heading("2.3 Scala di Probabilita (P)", level=2)
        self._add_data_table(
            doc,
            headers=["P", "Descrizione", "Esempio"],
            rows=[list(row) for row in _PROBABILITA_TABLE_ROWS],
        )
        doc.add_paragraph("")

        # 2.4 — Damage scale
        doc.add_heading("2.4 Scala del Danno (D)", level=2)
        self._add_data_table(
            doc,
            headers=["D", "Descrizione", "Effetto"],
            rows=[list(row) for row in _DANNO_TABLE_ROWS],
        )

        doc.add_page_break()

    def _add_risk_level_table(self, doc: Document) -> None:
        """Render the I-range -> Livello/Azione/Tempistica lookup table.

        The ``Livello`` column is shaded with the same ``_RISK_COLORS``
        palette used by Part III so the reader sees a consistent color
        language across the document.
        """
        headers = ["I", "Livello", "Azione", "Tempistica"]
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        # Header row
        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = _HEADER_TEXT
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        # Data rows
        for i_range, livello, azione, tempistica in _RISK_LEVEL_TABLE_ROWS:
            row = table.add_row()
            values = [i_range, livello, azione, tempistica]
            for col_idx, text in enumerate(values):
                cell = row.cells[col_idx]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.size = Pt(9)

                if col_idx in (0, 3):
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Color the Livello cell (white bold text on palette color)
                if col_idx == 1 and livello in _RISK_COLORS:
                    self._set_cell_bg(cell, _RISK_COLORS[livello])
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ------------------------------------------------------------------
    # Part III — Risk assessment per environment
    # ------------------------------------------------------------------

    def _add_part_iii(self, doc: Document, ambienti: list) -> None:
        """Add Part III: risk assessment tables per environment."""
        doc.add_heading(
            "PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO",
            level=1,
        )

        if not ambienti:
            p = doc.add_paragraph("Nessun ambiente di lavoro registrato.")
            p.runs[0].font.italic = True
            doc.add_page_break()
            return

        for ambiente in ambienti:
            self._add_environment_section(doc, ambiente)

    def _add_environment_section(self, doc: Document, ambiente) -> None:
        """Add the risk assessment section for a single environment."""
        # Environment header
        doc.add_heading(
            f"Ambiente: {ambiente.nome} ({ambiente.tipo})", level=2
        )

        # Environment details
        details = []
        if ambiente.superficie_mq:
            details.append(f"Superficie: {ambiente.superficie_mq} mq")
        if ambiente.descrizione_attivita:
            details.append(f"Attivita: {ambiente.descrizione_attivita}")
        if details:
            p = doc.add_paragraph(" | ".join(details))
            p.runs[0].font.size = Pt(9)
            p.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph("")

        risks = ambiente.valutazioni_rischio
        applicable_risks = [r for r in risks if r.applicabile]

        if not applicable_risks:
            p = doc.add_paragraph(
                "Nessun rischio applicabile identificato per questo ambiente."
            )
            p.runs[0].font.italic = True
            doc.add_paragraph("")
            return

        # Risk assessment table
        headers = [
            "Categoria",
            "Pericolo",
            "Condizioni di Esposizione",
            "Rischio",
            "Misure di Prevenzione e Protezione",
            "P",
            "D",
            "I",
            "Livello",
        ]
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        # Header row
        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.bold = True
            run.font.size = Pt(8)
            run.font.color.rgb = _HEADER_TEXT
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        # Data rows
        for risk in applicable_risks:
            row = table.add_row()
            p_val = risk.probabilita_p
            d_val = risk.danno_d

            # Calculate risk index if P and D are available
            if p_val is not None and d_val is not None:
                result = calculate_risk_index(p_val, d_val)
                indice = result["indice_i"]
                livello = result["livello_rischio"]
            else:
                indice = None
                livello = None

            values = [
                risk.categoria_rischio,
                risk.pericolo or "—",
                risk.condizioni_esposizione or "—",
                risk.rischio or "—",
                risk.misure_prevenzione or "—",
                str(p_val) if p_val is not None else "—",
                str(d_val) if d_val is not None else "—",
                str(indice) if indice is not None else "—",
                livello or "—",
            ]

            for i, text in enumerate(values):
                cell = row.cells[i]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.size = Pt(8)

                # Center-align the numeric and level columns
                if i >= 5:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Color the risk level cell
                if i == 8 and livello and livello in _RISK_COLORS:
                    self._set_cell_bg(cell, _RISK_COLORS[livello])
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True

                # Color the I (index) cell with lighter version
                if i == 7 and livello and livello in _RISK_COLORS:
                    self._set_cell_bg(cell, _RISK_COLORS[livello])
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True

        # Set column widths (approximate)
        widths = [Cm(2.2), Cm(3.0), Cm(3.0), Cm(2.5), Cm(4.0), Cm(0.8), Cm(0.8), Cm(0.8), Cm(2.0)]
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = width

        doc.add_paragraph("")

    # ------------------------------------------------------------------
    # Part IV — Improvement measures
    # ------------------------------------------------------------------

    def _add_part_iv(self, doc: Document) -> None:
        """Add Part IV: improvement measures placeholder."""
        doc.add_heading("PARTE IV — PROGRAMMA DI MIGLIORAMENTO", level=1)

        p = doc.add_paragraph()
        run = p.add_run(
            "Il programma di miglioramento viene definito sulla base delle "
            "criticita emerse dalla valutazione dei rischi. Le misure sono "
            "ordinate per priorita in funzione del livello di rischio."
        )
        run.font.size = Pt(10)

        doc.add_paragraph("")

        # Placeholder improvement table
        headers = [
            "N.",
            "Ambiente",
            "Rischio",
            "Livello",
            "Misura Proposta",
            "Priorita",
            "Responsabile",
            "Scadenza",
        ]
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = _HEADER_TEXT
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        # Add a single placeholder row
        row = table.add_row()
        placeholders = [
            "1",
            "[Ambiente]",
            "[Descrizione rischio]",
            "[Livello]",
            "[Misura di miglioramento]",
            "[Alta/Media/Bassa]",
            "[Nome]",
            "[GG/MM/AAAA]",
        ]
        for i, text in enumerate(placeholders):
            cell = row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.font.size = Pt(9)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        doc.add_paragraph("")

        # Signature block
        doc.add_paragraph("")
        doc.add_paragraph("")

        signatures = [
            ("Il Datore di Lavoro", "___________________________"),
            ("Il RSPP", "___________________________"),
            ("Il RLS", "___________________________"),
            ("Il Medico Competente", "___________________________"),
        ]
        for title, line in signatures:
            p = doc.add_paragraph()
            run = p.add_run(f"{title}:\t{line}")
            run.font.size = Pt(10)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _format_address(self, via: str | None, citta: str | None) -> str:
        """Format an address from its components."""
        parts = [p for p in [via, citta] if p]
        return ", ".join(parts) if parts else "—"

    def _add_key_value_table(
        self, doc: Document, rows: list[tuple[str, str]]
    ) -> None:
        """Add a simple two-column key-value table."""
        table = doc.add_table(rows=len(rows), cols=2)
        table.style = "Table Grid"

        for i, (key, value) in enumerate(rows):
            # Key cell
            cell_key = table.rows[i].cells[0]
            cell_key.text = ""
            p = cell_key.paragraphs[0]
            run = p.add_run(key)
            run.bold = True
            run.font.size = Pt(9)
            cell_key.width = Cm(5)

            # Value cell
            cell_val = table.rows[i].cells[1]
            cell_val.text = ""
            p = cell_val.paragraphs[0]
            run = p.add_run(value)
            run.font.size = Pt(9)
            cell_val.width = Cm(12)

            # Alternating row colors
            if i % 2 == 0:
                self._set_cell_bg(cell_key, _LIGHT_GRAY)
                self._set_cell_bg(cell_val, _LIGHT_GRAY)

    def _add_data_table(
        self, doc: Document, headers: list[str], rows: list[list[str]]
    ) -> None:
        """Add a multi-column data table with styled header."""
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"

        # Header row
        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = _HEADER_TEXT
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        # Data rows
        for row_idx, row_data in enumerate(rows):
            row = table.add_row()
            for i, text in enumerate(row_data):
                cell = row.cells[i]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.size = Pt(9)

                # Center-align the first column (row number)
                if i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Alternating row colors
            if row_idx % 2 == 0:
                for cell in row.cells:
                    self._set_cell_bg(cell, _LIGHT_GRAY)

    @staticmethod
    def _set_cell_bg(cell, color: RGBColor) -> None:
        """Set a table cell's background (shading) color.

        Uses the low-level XML API since python-docx does not expose
        cell shading directly.
        """
        shading_elm = cell._element.get_or_add_tcPr()
        shading = shading_elm.find(qn("w:shd"))
        if shading is None:
            shading = shading_elm.makeelement(qn("w:shd"), {})
            shading_elm.append(shading)
        shading.set(qn("w:fill"), f"{color}")
        shading.set(qn("w:val"), "clear")
