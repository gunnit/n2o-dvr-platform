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

from app.data.regional_regulations import get_regulations_for_comune
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.reference_data import (
    HAZARD_LIBRARY,
    RISK_CATEGORIES,
    normalize_categoria_to_long,
)
from app.services.risk_calculator import calculate_risk_index


# ---------------------------------------------------------------------------
# Parte II — Definizioni (Template Table 19, MIXED). Core D.Lgs. 81/2008
# terms from art. 2 — kept compact so the emitted table mirrors the
# template's 27-row shape without exploding the .docx size.
# ---------------------------------------------------------------------------

_DEFINIZIONI_ROWS: list[tuple[str, str]] = [
    ("LAVORATORE (LAV)",
     "Persona che, indipendentemente dalla tipologia contrattuale, svolge "
     "un'attivita lavorativa nell'ambito dell'organizzazione di un datore "
     "di lavoro pubblico o privato, con o senza retribuzione."),
    ("DATORE DI LAVORO (DL)",
     "Soggetto titolare del rapporto di lavoro con il lavoratore o, "
     "comunque, il soggetto che ha la responsabilita dell'organizzazione "
     "stessa o dell'unita produttiva."),
    ("AZIENDA",
     "Il complesso della struttura organizzata dal datore di lavoro "
     "pubblico o privato."),
    ("DIRIGENTE",
     "Persona che attua le direttive del datore di lavoro organizzando "
     "l'attivita lavorativa e vigilando su di essa."),
    ("PREPOSTO",
     "Persona che, in ragione delle competenze professionali e nei limiti "
     "di poteri gerarchici e funzionali adeguati alla natura dell'incarico "
     "conferitogli, sovrintende alla attivita lavorativa."),
    ("RSPP",
     "Responsabile del Servizio di Prevenzione e Protezione — persona "
     "designata dal datore di lavoro, in possesso di attitudini e "
     "capacita adeguate, a cui il datore di lavoro si avvale per "
     "organizzare il servizio di prevenzione e protezione."),
    ("ASPP",
     "Addetto del Servizio di Prevenzione e Protezione — persona in "
     "possesso di attitudini e capacita adeguate che supporta il RSPP "
     "nell'organizzazione del servizio."),
    ("RLS",
     "Rappresentante dei Lavoratori per la Sicurezza — persona eletta o "
     "designata per rappresentare i lavoratori per quanto concerne gli "
     "aspetti della salute e della sicurezza durante il lavoro."),
    ("MEDICO COMPETENTE (MC)",
     "Medico in possesso di uno dei titoli e requisiti formativi e "
     "professionali richiesti dalla normativa, che collabora con il "
     "datore di lavoro ai fini della valutazione dei rischi e della "
     "sorveglianza sanitaria."),
    ("VALUTAZIONE DEI RISCHI",
     "Valutazione globale e documentata di tutti i rischi per la salute "
     "e la sicurezza dei lavoratori presenti nell'ambito "
     "dell'organizzazione in cui essi prestano la propria attivita."),
    ("PERICOLO",
     "Proprieta o qualita intrinseca di un determinato fattore avente "
     "il potenziale di causare danni."),
    ("RISCHIO",
     "Probabilita di raggiungimento del livello potenziale di danno "
     "nelle condizioni di impiego o di esposizione a un determinato "
     "fattore o agente oppure alla loro combinazione."),
    ("PROBABILITA (P)",
     "Frequenza con cui un evento dannoso puo verificarsi, valutata "
     "su scala 1-4 (Bassa, Medio-Bassa, Medio-Alta, Elevata)."),
    ("DANNO (D)",
     "Entita del danno atteso per il lavoratore esposto, valutata su "
     "scala 1-4 (Trascurabile, Modesto, Notevole, Ingente)."),
    ("INDICE DI RISCHIO (I)",
     "Calcolato come I = 2 x D + P; range 3-12; livelli ACCETTABILE, "
     "MODESTO, GRAVE, GRAVISSIMO."),
    ("UNITA PRODUTTIVA",
     "Stabilimento o struttura finalizzati alla produzione di beni "
     "o all'erogazione di servizi, dotati di autonomia finanziaria e "
     "tecnico-funzionale."),
    ("DPI",
     "Dispositivo di Protezione Individuale — qualsiasi attrezzatura "
     "destinata ad essere indossata e tenuta dal lavoratore allo scopo "
     "di proteggerlo contro uno o piu rischi."),
    ("SORVEGLIANZA SANITARIA",
     "Insieme degli atti medici finalizzati alla tutela dello stato di "
     "salute e sicurezza dei lavoratori, in relazione all'ambiente di "
     "lavoro, ai fattori di rischio professionali e alle modalita di "
     "svolgimento dell'attivita lavorativa."),
    ("FORMAZIONE",
     "Processo educativo attraverso il quale trasferire ai lavoratori "
     "conoscenze e procedure utili alla acquisizione di competenze "
     "per lo svolgimento in sicurezza dei rispettivi compiti."),
    ("INFORMAZIONE",
     "Complesso delle attivita dirette a fornire conoscenze utili alla "
     "identificazione, alla riduzione e alla gestione dei rischi "
     "nell'ambiente di lavoro."),
    ("ADDESTRAMENTO",
     "Complesso delle attivita dirette a fare apprendere ai lavoratori "
     "l'uso corretto di attrezzature, macchine, impianti, sostanze, "
     "dispositivi, anche di protezione individuale, e le procedure di lavoro."),
    ("AGENTE",
     "L'agente chimico, fisico o biologico presente durante il lavoro "
     "e potenzialmente dannoso per la salute."),
    ("NORMA TECNICA",
     "Specifica tecnica, approvata e pubblicata da un'organizzazione "
     "internazionale, da un organismo europeo o nazionale di "
     "normalizzazione, la cui osservanza non e obbligatoria."),
    ("BUONA PRASSI",
     "Soluzioni organizzative o procedurali coerenti con la normativa "
     "vigente e con le norme di buona tecnica, adottate volontariamente e "
     "finalizzate a promuovere la salute e sicurezza sui luoghi di lavoro."),
    ("LINEE GUIDA",
     "Atti di indirizzo e coordinamento per l'applicazione della "
     "normativa in materia di salute e sicurezza."),
    ("MODELLO DI ORGANIZZAZIONE E GESTIONE",
     "Modello organizzativo e gestionale per la definizione e "
     "attuazione di una politica aziendale per la salute e sicurezza."),
    ("RESPONSABILITA SOCIALE",
     "Integrazione volontaria delle preoccupazioni sociali ed "
     "ecologiche delle aziende nelle loro operazioni commerciali e nei "
     "loro rapporti con le parti interessate."),
]

# Parte II — P/D criteria lookup tables (Template Tables 21 and 22).
_PROBABILITA_CRITERI_ROWS = [
    ("4", "ELEVATA",
     "Esiste correlazione diretta tra mancanza rilevata e possibilita "
     "che l'evento dannoso si verifichi; si sono gia verificati casi "
     "analoghi in azienda o in realta simili."),
    ("3", "MEDIO ALTA",
     "La mancanza rilevata puo provocare un danno, anche se non "
     "direttamente, seppur in modo automatico; sono noti rari episodi "
     "in azienda o in realta simili."),
    ("2", "MEDIO BASSA",
     "La mancanza rilevata puo provocare un danno in circostanze "
     "particolari; non sono noti episodi in azienda."),
    ("1", "BASSA",
     "La mancanza rilevata puo provocare un danno solo in circostanze "
     "eccezionali e in concomitanza con piu eventi sfavorevoli; non "
     "sono noti episodi nel settore."),
]

_DANNO_CRITERI_ROWS = [
    ("4", "INGENTE",
     "Infortunio o episodio di esposizione con effetti letali o "
     "invalidita totale permanente."),
    ("3", "NOTEVOLE",
     "Infortunio o episodio di esposizione acuta con effetti di "
     "invalidita parziale permanente; patologie gravi a effetti "
     "progressivi."),
    ("2", "MODESTO",
     "Infortunio o episodio di esposizione acuta con inabilita "
     "temporanea reversibile."),
    ("1", "TRASCURABILE",
     "Infortunio o episodio di esposizione acuta con inabilita "
     "reversibile di rapida guarigione."),
]


# Ordered list of the 11 canonical risk categories grouped by macro-area.
# Drives both the SI/NO checklist (Table 26 per env) and the per-category
# 5-col risk tables (Tables 27+). Order matches the DVR template.
_CATEGORY_ORDER: list[tuple[str, str]] = [
    (rc["macro_categoria"], rc["categoria"]) for rc in RISK_CATEGORIES
]

# Macro-area row labels interleaved into the checklist so it mirrors the
# template's 3 section headers + 11 data rows = 14 rows layout.
_MACRO_LABELS: list[str] = [
    "Rischi per la Sicurezza",
    "Rischi per la Salute",
    "Rischi Trasversali",
]


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

        # Look up the version BEFORE building the doc so the cover page
        # can show it. Same value is used in the filename below — single
        # source of truth.
        version = await self._get_next_version()

        doc = Document()
        self._setup_styles(doc)

        # Build document sections
        self._add_cover_page(doc, azienda, data["generated_at"], version)
        self._add_table_of_contents(doc)
        self._add_pre_parte_i(doc, azienda, data["generated_at"])
        self._add_part_i(
            doc,
            azienda,
            data["persone"],
            data["attrezzature"],
            data["sostanze_chimiche"],
            data["ambienti"],
        )
        self._add_part_ii(doc, azienda)
        self._add_part_iii(
            doc,
            azienda,
            data["persone"],
            data["ambienti"],
            data["attrezzature"],
        )
        self._add_part_iv(doc, azienda, data["persone"])

        # Save with the filename pattern required by US-2.8 AC2:
        # DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx.
        # The <ragione_sociale> segment is slugified (lowercase,
        # alphanumeric + underscore) so the filename stays safe on both
        # POSIX and Windows checkouts. The date is the generation day
        # (UTC) so regenerations on the same day keep the same stamp.
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
        self, doc: Document, azienda, generated_at: datetime, version: int
    ) -> None:
        """Add a professional cover page.

        Layout (top → bottom): logo, title block, company identity block
        (name + address + P.IVA + ATECO), date+version footer.
        Every field falls back gracefully when missing so generation
        never crashes on a sparse survey.
        """
        # Top spacer — kept tight (3 lines) so the title sits above the
        # vertical center, leaving room for the identity block below.
        for _ in range(3):
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
        run = p.add_run("ai sensi degli artt. 17 e 28 del D.Lgs. 81/2008 e s.m.i.")
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        doc.add_paragraph("")
        doc.add_paragraph("")

        # Company name — guard against None ragione_sociale (sparse surveys
        # were crashing here previously with AttributeError on .upper()).
        ragione = (azienda.ragione_sociale or "—").upper()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(ragione)
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

        # Identity line: P.IVA + ATECO when available
        identity_bits: list[str] = []
        partita_iva = getattr(azienda, "partita_iva", None)
        if partita_iva:
            identity_bits.append(f"P.IVA {partita_iva}")
        codice_ateco = getattr(azienda, "codice_ateco", None)
        if codice_ateco:
            identity_bits.append(f"ATECO {codice_ateco}")
        if identity_bits:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" · ".join(identity_bits))
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        # Spacer before footer
        for _ in range(3):
            doc.add_paragraph("")

        # Date and version block — single centered paragraph with both bits.
        # Format the version with a 2-digit pad (Rev. 01) to mirror the
        # convention Luca uses on the master template.
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(
            f"Revisione {version:02d} — {generated_at.strftime('%d/%m/%Y')}"
        )
        run.font.size = Pt(12)
        run.bold = True

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
    # Pre-Parte I — Frontispiece (Template Tables 0, 1, 2)
    # ------------------------------------------------------------------

    def _add_pre_parte_i(
        self, doc: Document, azienda, generated_at: datetime
    ) -> None:
        """Render the front-matter block that appears before Parte I.

        Tables 0, 1, 2 from DVR_TEMPLATE_MAPPING.md — azienda identity,
        revision history, and a stamped-signature placeholder. The revision
        row uses the azienda's own DVR version (next-version - 1 because
        ``_get_next_version`` is called later; for the front page we reflect
        the current emission).
        """
        p = doc.add_paragraph()
        run = p.add_run(
            "ex art. 17, comma 1, lettera a) ed art. 28 del "
            "D.Lgs. 81/2008 e s.m.i."
        )
        run.bold = True
        run.font.size = Pt(11)

        doc.add_paragraph("")
        self._add_azienda_header_table(doc, azienda)
        doc.add_paragraph("")

        doc.add_heading("Storico Revisioni", level=3)
        self._add_revision_history_table(doc, generated_at)
        doc.add_paragraph("")

        self._add_timbro_firma_table(doc)
        doc.add_page_break()

    def _add_revision_history_table(
        self, doc: Document, generated_at: datetime
    ) -> None:
        """Template Table 1 — Rev./Motivazione/Data (7×3 DYNAMIC).

        Emits a single row for the current emission. Real clients will have
        this backed by the ``DocumentoGenerato`` version log in a later
        iteration; for now it's a truthful single-entry record.
        """
        headers = ["Rev.", "Motivazione", "Data"]
        rows = [[
            "00",
            "Emissione",
            generated_at.strftime("%d/%m/%Y"),
        ]]
        self._add_data_table(doc, headers, rows)

    def _add_timbro_firma_table(self, doc: Document) -> None:
        """Template Table 2 — single-cell 'Timbro e Firma' placeholder (2×1)."""
        table = doc.add_table(rows=2, cols=1)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.LEFT

        header_cell = table.rows[0].cells[0]
        header_cell.text = ""
        p = header_cell.paragraphs[0]
        run = p.add_run("Timbro e Firma")
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = _HEADER_TEXT
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._set_cell_bg(header_cell, _HEADER_BG)

        body_cell = table.rows[1].cells[0]
        body_cell.text = ""
        body_cell.paragraphs[0].add_run("\n\n\n")

    # ------------------------------------------------------------------
    # Part I — Company data (Template Tables 3–17)
    # ------------------------------------------------------------------

    def _add_part_i(
        self,
        doc: Document,
        azienda,
        persone: list,
        attrezzature: list,
        sostanze_chimiche: list,
        ambienti: list,
    ) -> None:
        """Full Parte I with 15-table parity against the master template.

        Layout (Tables 3–17 in DVR_TEMPLATE_MAPPING.md):
          3   Azienda header (5×2)
          4   Anagrafica Aziendale (12×2)
          5   Dati occupazionali grid (N×5)
          6–9 Single-role titles (Datore di Lavoro / RSPP / RLS / Medico)
          10  Addetti Primo Soccorso
          11  Addetti Antincendio
          12  Ambienti + N.Lavoratori
          13  Attrezzature / Marcatura CE / Verifiche
          14  Sostanze chimiche / Produttore / Attivita
          15–17 Static hazard library (Sicurezza / Salute / Trasversali)
        """
        doc.add_heading("PARTE I — DATI GENERALI DELL'AZIENDA", level=1)

        # Table 3 — Presentazione dell'azienda
        doc.add_heading("1. Presentazione dell'Azienda", level=2)
        self._add_azienda_header_table(doc, azienda)
        doc.add_paragraph("")

        # Table 4 — Anagrafica Aziendale (12-row key-value)
        doc.add_heading("2. Anagrafica Aziendale", level=2)
        anagrafica_rows = [
            ("Ragione Sociale", azienda.ragione_sociale or "—"),
            ("Attivita",
             f"{azienda.codice_ateco or '—'} — {azienda.attivita or '—'}"),
            ("Sede Legale", self._format_address(
                azienda.sede_legale_via, azienda.sede_legale_citta
            )),
            ("Sede Operativa", self._format_address(
                azienda.sede_operativa_via, azienda.sede_operativa_citta
            )),
            ("Partita IVA", getattr(azienda, "partita_iva", None) or "—"),
            ("Codice Fiscale", getattr(azienda, "codice_fiscale", None) or "—"),
            ("Telefono", getattr(azienda, "telefono", None) or "—"),
            ("Email", getattr(azienda, "email", None) or "—"),
            ("PEC", getattr(azienda, "pec", None) or "—"),
            ("Orario di Lavoro", azienda.orario_lavoro or "—"),
            ("Metratura Totale",
             f"{azienda.metratura_totale} mq" if azienda.metratura_totale else "—"),
            ("Zona Sismica",
             str(azienda.zona_sismica) if azienda.zona_sismica else "—"),
        ]
        self._add_key_value_table(doc, anagrafica_rows)
        doc.add_paragraph("")

        # Table 5 — Dati occupazionali (Nominativo | Mansione | Ambiente | Note | Contratto)
        doc.add_heading("3. Dati Occupazionali", level=2)
        self._add_dati_occupazionali_table(doc, persone)
        doc.add_paragraph("")

        # Tables 6–9 — Organizzazione Aziendale della Sicurezza
        doc.add_heading("4. Organizzazione Aziendale della Sicurezza", level=2)
        role_tables = [
            ("Datore di Lavoro",
             [p for p in persone if p.ruolo_datore_lavoro]),
            ("Responsabile del Servizio di Prevenzione e Protezione",
             [p for p in persone if p.ruolo_rspp]),
            ("Rappresentante dei Lavoratori per la Sicurezza",
             [p for p in persone if p.ruolo_rls]),
            ("Medico Competente",
             [p for p in persone if getattr(p, "ruolo_medico_competente", False)]),
        ]
        for title, role_persone in role_tables:
            self._add_single_role_title_table(doc, title, role_persone)
            doc.add_paragraph("")

        # Tables 10, 11 — Addetti Primo Soccorso / Antincendio
        self._add_addetti_role_table(
            doc,
            "Addetti al Primo Soccorso",
            [p for p in persone if p.ruolo_primo_soccorso],
        )
        doc.add_paragraph("")
        self._add_addetti_role_table(
            doc,
            "Addetti alla Prevenzione Incendi e Lotta Antincendio",
            [p for p in persone if p.ruolo_antincendio],
        )
        doc.add_paragraph("")

        # Table 12 — Ambienti di Lavoro + N. Lavoratori
        doc.add_heading("5. Ambienti di Lavoro", level=2)
        self._add_ambienti_summary_table(doc, ambienti)
        doc.add_paragraph("")

        # Table 13 — Macchine, attrezzature ed impianti
        doc.add_heading("6. Macchine, Attrezzature ed Impianti", level=2)
        self._add_attrezzature_table(doc, attrezzature)
        doc.add_paragraph("")

        # Table 14 — Sostanze, prodotti e preparati chimici
        doc.add_heading("7. Sostanze, Prodotti e Preparati Chimici", level=2)
        self._add_sostanze_table(doc, sostanze_chimiche)
        doc.add_paragraph("")

        # Tables 15, 16, 17 — Static hazard library
        doc.add_heading("8. Elenco Fattori di Pericolo (Riferimento)", level=2)
        p = doc.add_paragraph()
        run = p.add_run(
            "N.B. Gli elenchi seguenti sono da intendersi indicativi e non "
            "esaustivi. Sono valutati in dettaglio per ogni ambiente di "
            "lavoro nella Parte III."
        )
        run.font.size = Pt(9)
        run.font.italic = True
        doc.add_paragraph("")

        self._add_hazard_library_group(doc, "Rischi per la Sicurezza", [
            "Strutture", "Macchine", "Impianti Elettrici", "Incendio-Esplosioni",
        ])
        doc.add_paragraph("")
        self._add_hazard_library_group(doc, "Rischi per la Salute", [
            "Agenti Chimici", "Agenti Fisici", "Agenti Biologici", "Agenti Cancerogeni",
        ])
        doc.add_paragraph("")
        self._add_hazard_library_group(doc, "Rischi Trasversali", [
            "Organizzazione del Lavoro", "Fattori Psicologici", "Fattori Ergonomici",
        ])

        doc.add_page_break()

    def _add_dati_occupazionali_table(self, doc: Document, persone: list) -> None:
        """Template Table 5 — 5-col lavoratori grid including ambiente assignments."""
        headers = ["Nominativo", "Mansione", "Ambiente di Lavoro", "Note", "Tipologia contrattuale"]
        if not persone:
            self._add_data_table(doc, headers, [["—", "—", "—", "—", "—"]])
            return

        rows = []
        for p in persone:
            ambienti_names = ", ".join(
                (a.nome or "")
                for a in (getattr(p, "ambienti", None) or [])
                if getattr(a, "nome", None)
            ) or "—"
            note = getattr(p, "codice_fiscale", None) or "—"
            rows.append([
                (p.nominativo or "—").upper(),
                (p.mansione or "—").upper(),
                ambienti_names.upper(),
                note,
                (p.tipologia_contrattuale or "—").upper(),
            ])
        self._add_data_table(doc, headers, rows)

    def _add_single_role_title_table(
        self, doc: Document, title: str, role_persone: list
    ) -> None:
        """Template Tables 6–9 — single-column title table with the role-holder's name."""
        names = [(p.nominativo or "").upper() for p in role_persone] or ["—"]
        table = doc.add_table(rows=1 + len(names), cols=1)
        table.style = "Table Grid"

        header_cell = table.rows[0].cells[0]
        header_cell.text = ""
        hp = header_cell.paragraphs[0]
        hrun = hp.add_run(title)
        hrun.bold = True
        hrun.font.size = Pt(9)
        hrun.font.color.rgb = _HEADER_TEXT
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._set_cell_bg(header_cell, _HEADER_BG)

        for i, name in enumerate(names, start=1):
            c = table.rows[i].cells[0]
            c.text = ""
            cp = c.paragraphs[0]
            crun = cp.add_run(name)
            crun.font.size = Pt(9)
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_addetti_role_table(
        self, doc: Document, title: str, role_persone: list
    ) -> None:
        """Template Tables 10, 11 — Nominativo/Mansione grid with a spanning header."""
        table = doc.add_table(rows=2, cols=2)
        table.style = "Table Grid"

        merged = table.rows[0].cells[0].merge(table.rows[0].cells[1])
        merged.text = ""
        p = merged.paragraphs[0]
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = _HEADER_TEXT
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._set_cell_bg(merged, _HEADER_BG)

        sub_row = table.rows[1]
        for i, text in enumerate(["Nominativo", "Mansione"]):
            c = sub_row.cells[i]
            c.text = ""
            cp = c.paragraphs[0]
            crun = cp.add_run(text)
            crun.bold = True
            crun.font.size = Pt(9)
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(c, _LIGHT_GRAY)

        if not role_persone:
            row = table.add_row()
            row.cells[0].text = "—"
            row.cells[1].text = "—"
            return

        for p in role_persone:
            row = table.add_row()
            for i, text in enumerate([
                (p.nominativo or "—").upper(),
                (p.mansione or "—").upper(),
            ]):
                c = row.cells[i]
                c.text = ""
                cp = c.paragraphs[0]
                crun = cp.add_run(text)
                crun.font.size = Pt(9)

    def _add_ambienti_summary_table(self, doc: Document, ambienti: list) -> None:
        """Template Table 12 — Ambiente | N. Lavoratori."""
        headers = ["Ambiente", "N. Lavoratori"]
        if not ambienti:
            rows = [["—", "0"]]
        else:
            rows = [
                [(a.nome or "—").upper(), str(len(getattr(a, "persone", None) or []))]
                for a in ambienti
            ]
        self._add_data_table(doc, headers, rows)

    def _add_attrezzature_table(self, doc: Document, attrezzature: list) -> None:
        """Template Table 13 — Descrizione | Marcata CE | Verifiche periodiche."""
        headers = ["Macchine, Attrezzature ed Impianti", "Marcata CE", "Verifiche Periodiche"]
        if not attrezzature:
            rows = [["Nessuna attrezzatura registrata.", "—", "—"]]
        else:
            rows = [
                [
                    (a.descrizione or "—").upper(),
                    "SI" if a.marcatura_ce else "NO",
                    "SI" if a.verifiche_periodiche else "NO",
                ]
                for a in attrezzature
            ]
        self._add_data_table(doc, headers, rows)

    def _add_sostanze_table(self, doc: Document, sostanze: list) -> None:
        """Template Table 14 — chemical inventory + SDS hazard detail.

        Two-block layout:
          1. Inventory table (4 cols) — name, manufacturer, state, GHS
             pictogram codes (joined). Uses SDS-extracted pittogrammi when
             available; falls back to "—" for manually entered rows.
          2. Per-sostanza H/P phrase detail block, emitted only for
             sostanze that have at least one hazard phrase. Skipped
             entirely when no SDS data exists, so manually-entered rows
             stay compact.
        """
        headers = [
            "Sostanza / Prodotto",
            "Produttore / Distributore",
            "Stato",
            "Pittogrammi GHS",
        ]
        if not sostanze:
            rows = [["Nessuna sostanza chimica registrata.", "—", "—", "—"]]
            self._add_data_table(doc, headers, rows)
            return

        rows = []
        for s in sostanze:
            pittogrammi = getattr(s, "pittogrammi", None) or []
            pittogrammi_text = ", ".join(pittogrammi) if pittogrammi else "—"
            rows.append([
                (s.nome_prodotto or "—").upper(),
                (s.produttore or "—").upper(),
                (getattr(s, "stato_miscela", None) or "—").upper(),
                pittogrammi_text,
            ])
        self._add_data_table(doc, headers, rows)

        # Phase 8.5 — emit per-sostanza H/P detail only when SDS data is
        # present. We don't add a heading when nothing has SDS data, so the
        # absence is invisible (operator-friendly).
        sostanze_with_sds = [
            s for s in sostanze
            if (getattr(s, "frasi_h", None) or [])
            or (getattr(s, "frasi_p", None) or [])
        ]
        if not sostanze_with_sds:
            return

        doc.add_paragraph("")
        p = doc.add_paragraph()
        run = p.add_run("Dettaglio frasi di pericolo (H) e consigli di prudenza (P)")
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = _HEADER_BG

        for s in sostanze_with_sds:
            frasi_h = getattr(s, "frasi_h", None) or []
            frasi_p = getattr(s, "frasi_p", None) or []

            p = doc.add_paragraph()
            run = p.add_run((s.nome_prodotto or "—").upper())
            run.bold = True
            run.font.size = Pt(9)

            if frasi_h:
                p = doc.add_paragraph()
                run = p.add_run("Frasi H: ")
                run.bold = True
                run.font.size = Pt(9)
                run = p.add_run("; ".join(frasi_h))
                run.font.size = Pt(9)

            if frasi_p:
                p = doc.add_paragraph()
                run = p.add_run("Frasi P: ")
                run.bold = True
                run.font.size = Pt(9)
                run = p.add_run("; ".join(frasi_p))
                run.font.size = Pt(9)

            doc.add_paragraph("")

    def _add_hazard_library_group(
        self, doc: Document, macro_label: str, categorie: list[str]
    ) -> None:
        """Template Tables 15/16/17 — 2-col static hazard catalog per macro-area."""
        rows: list[list[str]] = []
        for categoria in categorie:
            items = HAZARD_LIBRARY.get(categoria, [])
            for item in items:
                rows.append([categoria, item])

        if not rows:
            rows = [["—", "—"]]

        self._add_data_table(doc, headers=["Categoria", macro_label], rows=rows)

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

        # Template Table 18 — Azienda identity block at the top of Parte II
        self._add_azienda_header_table(doc, azienda)
        doc.add_paragraph("")

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

        # US-2.2 AC1: inject regione + applicable regional regulations into
        # Parte II Contesto Territoriale. Driven off sede_legale_citta (falls
        # back to sede_operativa_citta when absent). Silent no-op for comuni
        # not in the 158-entry lookup so the generator never fails because of
        # a missing regulation match — the operator fills it in during review.
        sede_citta = (
            getattr(azienda, "sede_legale_citta", None)
            or getattr(azienda, "sede_operativa_citta", None)
            or ""
        )
        regione, regulations = get_regulations_for_comune(sede_citta.strip())
        if regione and regulations:
            p = doc.add_paragraph()
            run = p.add_run(f"Regione di riferimento: {regione}")
            run.font.size = Pt(10)
            run.font.bold = True

            p = doc.add_paragraph()
            run = p.add_run(
                "Regolamenti regionali applicabili (in aggiunta al D.Lgs. 81/2008):"
            )
            run.font.size = Pt(10)
            run.font.italic = True

            for reg in regulations:
                bullet = doc.add_paragraph(style="List Bullet")
                run = bullet.add_run(f"{reg['titolo']} — ")
                run.font.size = Pt(10)
                run.font.bold = True
                run = bullet.add_run(reg["riferimento"])
                run.font.size = Pt(10)
                run = bullet.add_run(f" ({reg['ambito']})")
                run.font.size = Pt(10)
                run.font.italic = True

        doc.add_paragraph("")

        # Template Table 19 — Definizioni (glossary)
        doc.add_heading("2.2 Definizioni", level=2)
        self._add_data_table(
            doc,
            headers=["Termine", "Definizione"],
            rows=[list(r) for r in _DEFINIZIONI_ROWS],
        )
        doc.add_paragraph("")

        # 2.3 — Risk assessment methodology
        doc.add_heading("2.3 Metodologia di Valutazione dei Rischi", level=2)

        p = doc.add_paragraph()
        run = p.add_run(_METODOLOGIA_INTRO_1)
        run.font.size = Pt(10)

        p = doc.add_paragraph()
        run = p.add_run(_METODOLOGIA_INTRO_2)
        run.font.size = Pt(10)

        doc.add_paragraph("")
        self._add_risk_level_table(doc)
        doc.add_paragraph("")

        # Template Table 21 — Scala di Probabilita (P) with full criteria column
        doc.add_heading("2.4 Scala di Probabilita (P)", level=2)
        self._add_data_table(
            doc,
            headers=["P", "Livello", "Criteri"],
            rows=[list(row) for row in _PROBABILITA_CRITERI_ROWS],
        )
        doc.add_paragraph("")

        # Template Table 22 — Scala del Danno (D) with full criteria column
        doc.add_heading("2.5 Scala del Danno (D)", level=2)
        self._add_data_table(
            doc,
            headers=["D", "Livello", "Criteri"],
            rows=[list(row) for row in _DANNO_CRITERI_ROWS],
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

    def _add_part_iii(
        self,
        doc: Document,
        azienda,
        persone: list,
        ambienti: list,
        attrezzature: list,
    ) -> None:
        """Add Part III: per-environment risk assessment block.

        Emits the template-shaped env block (tables 23–33 in DVR_TEMPLATE_MAPPING.md):
          - Table 23 (once): azienda identity header — Ragione Sociale + Sede.
          - Per environment: 5 tables — identity, addetti, attrezzature
            present (Phase 8.2 — DVR esploso), risk-category checklist
            (SI/NO), and one 5-col risk table per applicable macro-category.
        """
        doc.add_heading(
            "PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO",
            level=1,
        )

        self._add_azienda_header_table(doc, azienda)
        doc.add_paragraph("")

        if not ambienti:
            p = doc.add_paragraph("Nessun ambiente di lavoro registrato.")
            p.runs[0].font.italic = True
            doc.add_page_break()
            return

        # Phase 8.2 — bucket attrezzature by ambiente_id once so each env
        # section gets its own slice. Anything without an ambiente_id is
        # silently skipped here (it still appears in the global Part I
        # inventory table, so it isn't lost).
        attrezzature_by_ambiente: dict = {}
        for att in attrezzature:
            amb_id = getattr(att, "ambiente_id", None)
            if amb_id is None:
                continue
            attrezzature_by_ambiente.setdefault(amb_id, []).append(att)

        persone_by_id = {getattr(p, "id", None): p for p in persone}
        for ambiente in ambienti:
            env_attrezzature = attrezzature_by_ambiente.get(ambiente.id, [])
            self._add_environment_section(
                doc, ambiente, persone_by_id, env_attrezzature
            )

    def _add_azienda_header_table(self, doc: Document, azienda) -> None:
        """Template Table 23 — Azienda / Sede identity block (once, at top of Parte III)."""
        rows = [
            ("Azienda", (azienda.ragione_sociale or "—").upper()),
            ("Sede Legale", azienda.sede_legale_via or "—"),
            ("Sede Legale", azienda.sede_legale_citta or "—"),
        ]
        if azienda.sede_operativa_via or azienda.sede_operativa_citta:
            rows.append(
                ("Sede Operativa", self._format_address(
                    azienda.sede_operativa_via, azienda.sede_operativa_citta
                ))
            )
        self._add_key_value_table(doc, rows)

    def _add_environment_section(
        self,
        doc: Document,
        ambiente,
        persone_by_id: dict,
        attrezzature: list,
    ) -> None:
        """Render the env section for a single environment.

        Phase 8.2 — DVR esploso per ambiente: now also lists the
        attrezzature present in this ambiente (the global Part I inventory
        stays in place; this is the per-env slice the operator asked for).

        Order mirrors tables 24–33 in the template:
          1. Identity (Table 24) — ambiente / preposto / descrizione.
          2. Addetti (Table 25) — nominativo / mansione.
          3. Attrezzature presenti in questo ambiente (Phase 8.2).
          4. Risk-category checklist (Table 26) — SI/NO per macro-area.
          5. One 5-col risk table per applicable macro-category.
        """
        nome_ambiente = (ambiente.nome or "—").upper()
        doc.add_heading(
            f"Identificazione dell'Ambiente di Lavoro e degli Addetti — {nome_ambiente}",
            level=2,
        )

        self._add_env_identity_table(doc, ambiente, persone_by_id)
        doc.add_paragraph("")
        self._add_env_addetti_table(doc, ambiente)
        doc.add_paragraph("")

        # Phase 8.2 — Attrezzature per ambiente. Reuses the same column
        # shape as the global Part I inventory so the visual pattern is
        # consistent. Empty slice → single placeholder row.
        doc.add_heading(
            f"Macchine, Attrezzature ed Impianti — {nome_ambiente}",
            level=3,
        )
        self._add_env_attrezzature_table(doc, attrezzature)
        doc.add_paragraph("")

        doc.add_heading(
            f"Identificazione dei Fattori di Rischio — {nome_ambiente}",
            level=3,
        )
        self._add_env_risk_checklist(doc, ambiente)
        doc.add_paragraph("")

        self._add_env_risk_tables(doc, ambiente)
        doc.add_page_break()

    def _add_env_attrezzature_table(
        self, doc: Document, attrezzature: list
    ) -> None:
        """Per-ambiente equipment table (Phase 8.2)."""
        headers = [
            "Macchine, Attrezzature ed Impianti",
            "Marcata CE",
            "Verifiche Periodiche",
        ]
        if not attrezzature:
            rows = [["Nessuna attrezzatura associata a questo ambiente.", "—", "—"]]
        else:
            rows = [
                [
                    (a.descrizione or "—").upper(),
                    "SI" if a.marcatura_ce else "NO",
                    "SI" if a.verifiche_periodiche else "NO",
                ]
                for a in attrezzature
            ]
        self._add_data_table(doc, headers, rows)

    def _add_env_identity_table(
        self, doc: Document, ambiente, persone_by_id: dict
    ) -> None:
        """Template Table 24 — 3×2 DYNAMIC key-value block for the environment."""
        preposto_name = "—"
        preposto_id = getattr(ambiente, "preposto_id", None)
        if preposto_id and preposto_id in persone_by_id:
            preposto_name = (persone_by_id[preposto_id].nominativo or "—").upper()

        descrizione = (
            (ambiente.descrizione_attivita or "").strip()
            or (ambiente.tipo or "—")
        ).upper()

        rows = [
            ("Ambiente di lavoro", (ambiente.nome or "—").upper()),
            ("Preposto per la sicurezza", preposto_name),
            ("Descrizione Attività", descrizione),
        ]
        self._add_key_value_table(doc, rows)

    def _add_env_addetti_table(self, doc: Document, ambiente) -> None:
        """Template Table 25 — Nominativo / Mansione for addetti assigned to this env.

        Always emits the table shell so the per-env layout matches the
        template even when no persone_ambienti mapping exists yet; a single
        placeholder row signals the missing assignment to the operator.
        """
        addetti = list(getattr(ambiente, "persone", []) or [])
        if addetti:
            rows = [
                [(a.nominativo or "—").upper(), (a.mansione or "—").upper()]
                for a in addetti
            ]
        else:
            rows = [["—", "—"]]
        self._add_data_table(doc, headers=["Nominativo Addetti", "Mansione"], rows=rows)

    def _add_env_risk_checklist(self, doc: Document, ambiente) -> None:
        """Template Table 26 — 14-row SI/NO checklist for the 11 risk categories.

        Row layout: macro-area label row, then its categories with SI/NO
        derived from whether at least one applicable valutazione_rischio
        exists with that categoria in this ambiente.
        """
        # Normalize short DB names ("Elettrici") to canonical long names
        # ("Impianti Elettrici") so the lookup against _CATEGORY_ORDER keys
        # actually matches. Without this every row silently shows NO.
        applicable_by_category = {
            normalize_categoria_to_long(r.categoria_rischio): True
            for r in ambiente.valutazioni_rischio
            if getattr(r, "applicabile", False)
        }

        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"

        header_row = table.rows[0]
        for i, text in enumerate(["Categoria di Rischio", "Applicabile"]):
            cell = header_row.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = _HEADER_TEXT
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        current_macro = None
        for macro, categoria in _CATEGORY_ORDER:
            if macro != current_macro:
                macro_row = table.add_row()
                merged = macro_row.cells[0].merge(macro_row.cells[1])
                merged.text = ""
                p = merged.paragraphs[0]
                run = p.add_run(macro)
                run.bold = True
                run.font.size = Pt(9)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                self._set_cell_bg(merged, _LIGHT_GRAY)
                current_macro = macro

            row = table.add_row()
            cell_label = row.cells[0]
            cell_label.text = ""
            p = cell_label.paragraphs[0]
            run = p.add_run(categoria)
            run.font.size = Pt(9)

            cell_flag = row.cells[1]
            cell_flag.text = ""
            p = cell_flag.paragraphs[0]
            flag = "SI" if applicable_by_category.get(categoria) else "NO"
            run = p.add_run(flag)
            run.font.size = Pt(9)
            run.bold = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_env_risk_tables(self, doc: Document, ambiente) -> None:
        """Template Tables 27+ — one 5-col (PERICOLO/CONDIZIONI/RISCHIO/MISURE/I)
        table per applicable macro-category, emitted in the canonical order."""
        # Normalize short DB names to canonical long names so the per-category
        # tables actually emit (see _add_env_risk_checklist comment).
        by_category: dict[str, list] = {}
        for r in ambiente.valutazioni_rischio:
            if not getattr(r, "applicabile", False):
                continue
            key = normalize_categoria_to_long(r.categoria_rischio)
            if not key:
                continue
            by_category.setdefault(key, []).append(r)

        ordered_keys = [cat for _, cat in _CATEGORY_ORDER if cat in by_category]
        trailing = [k for k in by_category.keys() if k not in ordered_keys]

        if not ordered_keys and not trailing:
            p = doc.add_paragraph(
                "Nessun rischio applicabile identificato per questo ambiente."
            )
            p.runs[0].font.italic = True
            return

        for cat_name in ordered_keys + trailing:
            self._add_single_category_risk_table(doc, cat_name, by_category[cat_name])
            doc.add_paragraph("")

    def _add_single_category_risk_table(
        self, doc: Document, categoria: str, risks: list
    ) -> None:
        """5-col risk table for a single category (Template Tables 27–33 shape)."""
        p = doc.add_paragraph()
        run = p.add_run(categoria.upper())
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = _HEADER_BG

        headers = [
            "PERICOLO",
            "CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE",
            "RISCHIO",
            "MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E DPI",
            "I = P + 2*D",
        ]
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            hp = cell.paragraphs[0]
            hrun = hp.add_run(text)
            hrun.bold = True
            hrun.font.size = Pt(8)
            hrun.font.color.rgb = _HEADER_TEXT
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        # Phase 3 (1:N): when the parent valutazione_rischio has children
        # in pericoli_valutazione, emit one row per child — that's the
        # template-faithful layout. When no children exist (legacy data),
        # fall back to the parent's single pericolo/condizioni/misure
        # block so older DVRs still render.
        rows_to_emit: list = []
        for risk in risks:
            children = [
                c for c in (getattr(risk, "pericoli", []) or [])
                if getattr(c, "applicabile", True)
            ]
            if children:
                rows_to_emit.extend(children)
            else:
                rows_to_emit.append(risk)

        for source in rows_to_emit:
            p_val = source.probabilita_p
            d_val = source.danno_d
            riferimento = getattr(source, "valutazione_riferimento", None)
            if p_val is not None and d_val is not None:
                result = calculate_risk_index(p_val, d_val)
                indice = result["indice_i"]
                livello = result["livello_rischio"]
                indice_text = f"P = {p_val}; D = {d_val}; I = {indice}; {livello}"
            elif riferimento:
                livello = None
                indice_text = riferimento
            else:
                livello = None
                indice_text = "—"

            row = table.add_row()
            values = [
                source.pericolo or "—",
                source.condizioni_esposizione or "—",
                source.rischio or "—",
                source.misure_prevenzione or "—",
                indice_text,
            ]
            for i, text in enumerate(values):
                cell = row.cells[i]
                cell.text = ""
                cp = cell.paragraphs[0]
                crun = cp.add_run(text)
                crun.font.size = Pt(8)
                if i == 4:
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    if livello and livello in _RISK_COLORS:
                        self._set_cell_bg(cell, _RISK_COLORS[livello])
                        crun.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        crun.bold = True

        widths = [Cm(3.5), Cm(4.0), Cm(3.0), Cm(4.5), Cm(3.5)]
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = width

    # ------------------------------------------------------------------
    # Part IV — Improvement measures (Template Tables 108, 109, 110)
    # ------------------------------------------------------------------

    def _add_part_iv(self, doc: Document, azienda, persone: list) -> None:
        """Parte IV with 3-table parity — azienda header, improvement program,
        signatures."""
        doc.add_heading("PARTE IV — PROGRAMMA DI MIGLIORAMENTO", level=1)

        # Template Table 108 — Azienda header
        self._add_azienda_header_table(doc, azienda)
        doc.add_paragraph("")

        doc.add_heading(
            "Programma e Procedure di attuazione delle Misure di Miglioramento",
            level=2,
        )
        p = doc.add_paragraph()
        run = p.add_run(
            "Il programma di miglioramento e definito sulla base delle "
            "criticita emerse dalla valutazione dei rischi. Le misure sono "
            "ordinate per priorita in funzione del livello di rischio."
        )
        run.font.size = Pt(10)
        doc.add_paragraph("")

        # Template Table 109 — Misure di miglioramento (5-col grid)
        self._add_improvement_program_table(doc)
        doc.add_paragraph("")
        doc.add_paragraph("")

        # Template Table 110 — Signature block (2×3)
        self._add_signature_table(doc, persone)

    def _add_improvement_program_table(self, doc: Document) -> None:
        """Template Table 109 — 5-col measures grid with a placeholder row for
        operator completion."""
        headers = [
            "Misure di miglioramento",
            "Procedure per l'attuazione delle misure di miglioramento",
            "Risorse necessarie per l'attuazione",
            "Responsabile",
            "Tempi di attuazione",
        ]
        placeholder_row = [
            "[Misura]",
            "[Procedura]",
            "[Risorse]",
            "[Responsabile]",
            "[Scadenza]",
        ]
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        header_row = table.rows[0]
        for i, text in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = ""
            hp = cell.paragraphs[0]
            hrun = hp.add_run(text)
            hrun.bold = True
            hrun.font.size = Pt(9)
            hrun.font.color.rgb = _HEADER_TEXT
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._set_cell_bg(cell, _HEADER_BG)

        row = table.add_row()
        for i, text in enumerate(placeholder_row):
            c = row.cells[i]
            c.text = ""
            cp = c.paragraphs[0]
            crun = cp.add_run(text)
            crun.font.size = Pt(9)
            crun.font.italic = True
            crun.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    def _add_signature_table(self, doc: Document, persone: list) -> None:
        """Template Table 110 — 2×3 signature grid with DL / RSPP / Medico
        (row 1) and RLS (row 2, merged center cell)."""
        def _first(pred) -> str:
            match = next((p for p in persone if pred(p)), None)
            return (match.nominativo if match else "").upper()

        dl = _first(lambda p: p.ruolo_datore_lavoro) or "—"
        rspp = _first(lambda p: p.ruolo_rspp) or "—"
        medico = _first(lambda p: getattr(p, "ruolo_medico_competente", False)) or "—"
        rls = _first(lambda p: p.ruolo_rls) or "—"

        table = doc.add_table(rows=2, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        def _fill(cell, title_line: str, name_line: str) -> None:
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(title_line)
            run.bold = True
            run.font.size = Pt(9)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2 = cell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run2 = p2.add_run(name_line)
            run2.font.size = Pt(9)
            p3 = cell.add_paragraph()
            p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run3 = p3.add_run("___________________________")
            run3.font.size = Pt(9)

        _fill(table.rows[0].cells[0], "Il Datore di Lavoro", f"({dl})")
        _fill(table.rows[0].cells[1], "", "")
        _fill(table.rows[0].cells[2], "Il Responsabile del S.P.P.", f"({rspp})")

        _fill(table.rows[1].cells[0], "Il Medico Competente", f"({medico})")
        _fill(table.rows[1].cells[1], "", "")
        _fill(
            table.rows[1].cells[2],
            "Per consultazione\nIl Rappresentante dei Lavoratori",
            f"({rls})",
        )

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
