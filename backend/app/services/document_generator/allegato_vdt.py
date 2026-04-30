"""Allegato VDT - Videoterminali (D.Lgs. 81/2008 Titolo VII, artt. 172-179).

Generates the VDT attachment from scratch (no template loading) to avoid
leaking the donor template's pre-populated client data. Mirrors the
template structure end-to-end:

  1. Cover (logo, title, azienda, generation date + revision)
  2. Revision history
  3. TOC
  4. Introduzione (VDT theory)
  5. Anagrafica Aziendale
  6. Dati Occupazionali
  7. Organizzazione Aziendale della Sicurezza
  8. Principali fattori di rischio (vista, postura, affaticamento)
  9. La postazione di lavoro (videoterminale, ambiente, posizionamento)
 10. Elenco postazioni VDT
 11. Tavole di Valutazione (per worker: ore + esposizione + checklist)
 12. Quadro sinottico di esposizione
 13. Misure di prevenzione
 14. Programma di attuazione (sorveglianza sanitaria)
 15. Dichiarazione del Datore di Lavoro
 16. Signature block (DdL / RSPP / MC / RLS)
"""

from __future__ import annotations

import os
from datetime import datetime

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_vdt
from app.services.document_generator.docx_utils import (
    HEADER_BG,
    LOGO_PATH,
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    page_break,
    shade_cell,
    slugify,
    style_header_row,
)
from app.services.vdt_calculator import VDT_EXPOSURE_THRESHOLD_HOURS

TIPO_DOC = "allegato_vdt"

_EXPOSURE_COLORS = {
    "Esposto": "F4CCCC",      # rose — surveillance triggered
    "Non Esposto": "D9EAD3",  # green
}

_CHECKLIST_ITEMS: list[tuple[str, str]] = [
    ("schermo_conforme", "Schermo conforme (leggibilita, stabilita, regolazioni)"),
    ("tastiera_separata", "Tastiera separata e inclinabile"),
    ("sedile_regolabile", "Sedile a 5 razze, altezza/schienale regolabili"),
    ("poggiapiedi_disponibile", "Poggiapiedi disponibile su richiesta"),
    ("illuminazione_adeguata", "Illuminazione adeguata (300-500 lux)"),
    ("riflessi_assenti", "Assenza di riflessi e abbagliamenti"),
    ("spazio_adeguato", "Spazio di lavoro sufficiente"),
    ("pause_previste", "Pause previste (15 min ogni 2 ore di applicazione continuativa)"),
]


class AllegatoVdtGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        persone = data["persone"]
        ambienti = data["ambienti"]
        generated_at: datetime = data["generated_at"]
        vdt_rows = await load_vdt(self.db, self.azienda_id)
        version = await self._next_version()

        ambiente_by_id = {a.id: a for a in ambienti}
        persona_by_id = {p.id: p for p in persone}

        doc = Document()
        self._setup_styles(doc)

        self._add_cover(doc, azienda, generated_at, version)
        self._add_revision_table(doc, generated_at, version)
        self._add_toc(doc)
        self._add_introduzione(doc)
        self._add_anagrafica(doc, azienda)
        self._add_dati_occupazionali(doc, persone)
        self._add_organizzazione(doc, persone)
        self._add_fattori_rischio(doc)
        self._add_postazione_lavoro(doc)
        self._add_elenco_postazioni(doc, vdt_rows, ambiente_by_id)
        self._add_per_worker_assessments(doc, vdt_rows, persona_by_id, ambiente_by_id)
        self._add_quadro_sinottico(doc, vdt_rows, persona_by_id)
        self._add_misure_prevenzione(doc)
        self._add_programma_attuazione(doc, vdt_rows, persona_by_id)
        self._add_dichiarazione_ddl(doc, azienda, persone)
        self._add_signature_block(doc, persone)

        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        filepath = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.docx")
        doc.save(filepath)
        return filepath

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    async def _next_version(self) -> int:
        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_VDT"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1

    # ------------------------------------------------------------------
    # Style setup
    # ------------------------------------------------------------------

    def _setup_styles(self, doc: Document) -> None:
        for s in doc.sections:
            s.top_margin = Cm(2.0)
            s.bottom_margin = Cm(2.0)
            s.left_margin = Cm(2.5)
            s.right_margin = Cm(2.0)
        try:
            normal = doc.styles["Normal"]
            normal.font.name = "Calibri"
            normal.font.size = Pt(11)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def _add_cover(self, doc, azienda, generated_at: datetime, version: int) -> None:
        for _ in range(2):
            doc.add_paragraph("")

        if LOGO_PATH.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(str(LOGO_PATH), width=Inches(2.0))
            except Exception:
                p.add_run("[LOGO AZIENDALE]").italic = True

        doc.add_paragraph("")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("ALLEGATO RISCHIO VDT")
        run.bold = True
        run.font.size = Pt(22)
        run.font.color.rgb = HEADER_BG

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Valutazione del Rischio da Videoterminali")
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(
            "ai sensi del Titolo VII D.Lgs. 81/2008 e s.m.i. (D.Lgs. 106/09)"
        )
        run.font.size = Pt(11)
        run.italic = True
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        for _ in range(3):
            doc.add_paragraph("")

        ragione = (azienda.ragione_sociale or "—").upper()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(ragione)
        run.bold = True
        run.font.size = Pt(18)

        addr_bits = []
        if azienda.sede_legale_via:
            addr_bits.append(azienda.sede_legale_via)
        if azienda.sede_legale_citta:
            addr_bits.append(azienda.sede_legale_citta)
        if addr_bits:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" - ".join(addr_bits))
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        ident_bits = []
        if getattr(azienda, "partita_iva", None):
            ident_bits.append(f"P.IVA {azienda.partita_iva}")
        if getattr(azienda, "codice_ateco", None):
            ident_bits.append(f"ATECO {azienda.codice_ateco}")
        if ident_bits:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" · ".join(ident_bits))
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        for _ in range(3):
            doc.add_paragraph("")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(
            f"Revisione {version:02d} - {generated_at.strftime('%d/%m/%Y')}"
        )
        run.bold = True
        run.font.size = Pt(12)

        page_break(doc)

    # ------------------------------------------------------------------
    # Revision history
    # ------------------------------------------------------------------

    def _add_revision_table(self, doc, generated_at: datetime, version: int) -> None:
        add_heading(doc, "Storico delle Revisioni", level=2)
        headers = ["Rev.", "Motivazione", "Data"]
        rows = [[
            f"{version:02d}",
            "Emissione" if version == 1 else "Aggiornamento",
            generated_at.strftime("%d/%m/%Y"),
        ]]
        add_data_table(doc, headers, rows)
        doc.add_paragraph("")

    # ------------------------------------------------------------------
    # TOC
    # ------------------------------------------------------------------

    def _add_toc(self, doc) -> None:
        add_heading(doc, "Indice", level=1)
        p = doc.add_paragraph()
        run = p.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_begin)
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = ' TOC \\o "1-3" \\h \\z \\u '
        run._r.append(instr)
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run._r.append(fld_end)
        add_paragraph(
            doc,
            "(Premere Ctrl+A poi F9 per aggiornare l'indice)",
            italic=True,
            size=9,
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Introduzione
    # ------------------------------------------------------------------

    def _add_introduzione(self, doc) -> None:
        add_heading(doc, "Introduzione", level=1)
        for txt in [
            "L'utilizzo del videoterminale, soprattutto se prolungato, puo' provocare "
            "disturbi all'apparato muscolo-scheletrico, all'apparato visivo e fenomeni "
            "di affaticamento fisico o mentale. La rilevanza di tali disturbi e' "
            "strettamente correlata alla durata dell'esposizione e alle caratteristiche "
            "ergonomiche della postazione.",
            "Il Titolo VII del D.Lgs. 81/2008 (artt. 172-179) impone al datore di "
            "lavoro la valutazione del rischio per i lavoratori che utilizzano "
            "abitualmente videoterminali e definisce, all'art. 173, lavoratore esposto "
            "chi vi opera in modo sistematico o abituale per almeno "
            f"{int(VDT_EXPOSURE_THRESHOLD_HOURS)} ore settimanali, dedotte le pause.",
            "La presente valutazione classifica ciascuna postazione e ciascun "
            "lavoratore in funzione del tempo di utilizzo settimanale; per i "
            "lavoratori esposti viene predisposto il programma di sorveglianza "
            "sanitaria oculistica ai sensi dell'art. 176 (periodicita' "
            "quinquennale, biennale per gli over 50 o con prescrizioni).",
        ]:
            add_paragraph(doc, txt)
        page_break(doc)

    # ------------------------------------------------------------------
    # Anagrafica Aziendale
    # ------------------------------------------------------------------

    def _add_anagrafica(self, doc, azienda) -> None:
        add_heading(doc, "Anagrafica Aziendale", level=1)
        rows: list[tuple[str, str]] = [
            ("Azienda", azienda.ragione_sociale or "—"),
            ("Attivita / Codice ATECO", getattr(azienda, "codice_ateco", "") or "—"),
            ("Partita IVA", getattr(azienda, "partita_iva", "") or "—"),
            ("Codice Fiscale", getattr(azienda, "codice_fiscale", "") or "—"),
            ("Sede Legale - Via", azienda.sede_legale_via or "—"),
            ("Sede Legale - Citta", azienda.sede_legale_citta or "—"),
            ("Sede Operativa - Via", getattr(azienda, "sede_operativa_via", "") or "—"),
            ("Sede Operativa - Citta", getattr(azienda, "sede_operativa_citta", "") or "—"),
            ("Telefono", getattr(azienda, "telefono", "") or "—"),
            ("Email PEC", getattr(azienda, "email_pec", "") or "—"),
        ]
        add_kv_table(doc, rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Dati Occupazionali (no codice fiscale - GDPR)
    # ------------------------------------------------------------------

    def _add_dati_occupazionali(self, doc, persone: list) -> None:
        add_heading(doc, "Dati Occupazionali", level=1)
        if not persone:
            add_paragraph(doc, "Nessun lavoratore registrato per questa azienda.", italic=True)
            page_break(doc)
            return

        headers = ["Nominativo", "Mansione", "Sesso", "Fascia eta", "Tipologia contrattuale"]
        rows = []
        for p in persone:
            rows.append([
                p.nominativo or "—",
                p.mansione or "—",
                p.sesso or "—",
                p.fascia_eta or "—",
                p.tipologia_contrattuale or "—",
            ])
        add_data_table(doc, headers, rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Organizzazione Sicurezza
    # ------------------------------------------------------------------

    def _add_organizzazione(self, doc, persone: list) -> None:
        add_heading(doc, "Organizzazione Aziendale della Sicurezza", level=1)

        def _names(predicate) -> str:
            matched = [p.nominativo for p in persone if predicate(p) and p.nominativo]
            return ", ".join(matched) if matched else "—"

        rows = [
            ("Datore di Lavoro", _names(lambda p: bool(p.ruolo_datore_lavoro))),
            ("RSPP", _names(lambda p: bool(p.ruolo_rspp))),
            ("RLS", _names(lambda p: bool(p.ruolo_rls))),
            ("Medico Competente", _names(lambda p: bool(p.ruolo_medico_competente))),
            ("Addetti Primo Soccorso", _names(lambda p: bool(p.ruolo_primo_soccorso))),
            ("Addetti Antincendio", _names(lambda p: bool(p.ruolo_antincendio))),
            ("Preposti", _names(lambda p: bool(p.ruolo_preposto))),
        ]
        add_kv_table(doc, rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Principali fattori di rischio (static narrative)
    # ------------------------------------------------------------------

    def _add_fattori_rischio(self, doc) -> None:
        add_heading(doc, "Principali fattori di rischio", level=1)
        add_paragraph(
            doc,
            "I disturbi che i lavoratori addetti ai videoterminali possono accusare "
            "sono riconducibili a tre famiglie di rischio: sollecitazione degli "
            "organi della vista, posizione del corpo, affaticamento fisico e mentale.",
        )

        add_heading(doc, "Sollecitazione degli organi della vista", level=2)
        add_paragraph(
            doc,
            "Bruciore, lacrimazione, secchezza, fastidio alla luce, pesantezza, "
            "visione annebbiata o sdoppiata, stanchezza alla lettura. Sono dovuti a "
            "elevata sollecitazione e rapido affaticamento degli organi della vista "
            "causati da: errate condizioni di illuminazione; ubicazione sbagliata "
            "del videoterminale rispetto alle finestre; condizioni ambientali "
            "sfavorevoli (aria secca, correnti, temperatura); caratteristiche "
            "inadeguate di software o monitor; postazione non corretta; impegno "
            "visivo ravvicinato e protratto; difetti visivi non corretti.",
        )

        add_heading(doc, "Posizione del corpo", level=2)
        add_paragraph(
            doc,
            "Disturbi alla colonna vertebrale dovuti a errata postura e sedentarieta', "
            "disturbi muscolari da affaticamento e indolenzimento, disturbi a mano "
            "e avambraccio (dolore, formicolii, impaccio ai movimenti) per "
            "infiammazione di nervi e tendini sovraccaricati.",
        )

        add_heading(doc, "Affaticamento fisico o mentale", level=2)
        add_paragraph(
            doc,
            "Determinato da: cattiva organizzazione del lavoro (operazioni monotone "
            "ripetitive); cattive condizioni ambientali (temperatura, umidita', "
            "velocita' dell'aria); rumore ambientale che disturba l'attenzione; "
            "software non adeguato.",
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # La postazione di lavoro (static narrative)
    # ------------------------------------------------------------------

    def _add_postazione_lavoro(self, doc) -> None:
        add_heading(doc, "La postazione di lavoro", level=1)

        add_heading(doc, "Videoterminale, tastiera e mouse", level=2)
        add_paragraph(
            doc,
            "La postazione VDT deve essere allestita con attrezzature moderne e "
            "ergonomiche: monitor orientabile e inclinabile, con luminosita' e "
            "contrasto regolabili e privi di sfarfallii; tastiera indipendente, "
            "spostabile, di basso spessore e inclinabile, con tasti dotati di "
            "superficie opaca; mouse posizionato accanto alla tastiera con spazio "
            "sufficiente all'appoggio del polso. Software di facile uso, adeguato "
            "alla mansione, con velocita' di risposta congrua.",
        )

        add_heading(doc, "Condizioni ambientali", level=2)
        add_paragraph(
            doc,
            "Temperatura raccomandata 18-22 °C in inverno e 24-26 °C in estate; "
            "umidita' relativa 40-60%; assenza di correnti d'aria fastidiose. "
            "Illuminazione 300-500 lux, priva di abbagliamenti diretti o riflessi "
            "sullo schermo. Rumore ambientale tale da non disturbare l'attenzione "
            "ne' la comunicazione verbale.",
        )

        add_heading(doc, "Corretto posizionamento del videoterminale", level=2)
        add_paragraph(
            doc,
            "Il monitor va posizionato perpendicolarmente alle finestre per evitare "
            "abbagliamenti e riflessi; la direzione principale dello sguardo deve "
            "essere parallela al piano delle finestre. Distanza occhio-schermo "
            "50-70 cm. Il bordo superiore dello schermo deve trovarsi all'altezza "
            "degli occhi o leggermente sotto.",
        )

        add_heading(doc, "Piano di lavoro, sedia, poggiapiedi", level=2)
        add_paragraph(
            doc,
            "Piano di lavoro stabile, di profondita' adeguata e altezza regolabile "
            "(70-80 cm). Sedia a 5 razze con sedile e schienale regolabili in "
            "altezza e inclinazione. Poggiapiedi disponibile su richiesta del "
            "lavoratore quando l'altezza del piano di lavoro non consente l'appoggio "
            "completo dei piedi a terra.",
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Elenco postazioni VDT
    # ------------------------------------------------------------------

    def _add_elenco_postazioni(self, doc, vdt_rows: list, ambiente_by_id: dict) -> None:
        add_heading(doc, "Elenco postazioni VDT", level=1)
        if not vdt_rows:
            add_paragraph(
                doc,
                "Nessuna postazione VDT e' stata valutata per questa azienda.",
                italic=True,
            )
            page_break(doc)
            return

        # Group by postazione name to deduplicate (multiple workers may share one).
        postazioni: dict[str, str] = {}
        for r in vdt_rows:
            name = (r.postazione or "—").strip()
            if name in postazioni:
                continue
            ambiente = ambiente_by_id.get(r.ambiente_id) if r.ambiente_id else None
            postazioni[name] = (ambiente.nome if ambiente else "—") or "—"

        rows = [[name, ambiente] for name, ambiente in postazioni.items()]
        add_data_table(doc, ["Postazione VDT", "Ambiente di Lavoro"], rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Per-worker assessment grid (mirrors template T10..T18 layout)
    # ------------------------------------------------------------------

    def _add_per_worker_assessments(
        self,
        doc,
        vdt_rows: list,
        persona_by_id: dict,
        ambiente_by_id: dict,
    ) -> None:
        add_heading(doc, "Tavole di Valutazione del Rischio VDT", level=1)
        if not vdt_rows:
            add_paragraph(
                doc,
                "Nessuna postazione VDT e' stata valutata per questa azienda.",
                italic=True,
            )
            page_break(doc)
            return

        for i, r in enumerate(vdt_rows, 1):
            persona = persona_by_id.get(r.persona_id) if r.persona_id else None
            ambiente = ambiente_by_id.get(r.ambiente_id) if r.ambiente_id else None
            self._render_assessment_table(doc, i, r, persona, ambiente)

    def _render_assessment_table(self, doc, idx: int, r, persona, ambiente) -> None:
        nominativo = (persona.nominativo if persona else None) or "—"
        mansione = (persona.mansione if persona else None) or "—"

        ore = float(r.ore_settimanali or 0)
        esposto = bool(r.esposto)
        esp_label = "Esposto" if esposto else "Non Esposto"

        add_heading(doc, f"{idx}. {r.postazione or 'Postazione'}", level=2)
        if ambiente:
            add_paragraph(
                doc, f"Ambiente: {ambiente.nome or '—'}", italic=True, size=10
            )

        # Header table: Nominativo / Mansione / Ore / Rischio (mirrors template T10)
        table = doc.add_table(rows=0, cols=4)
        try:
            table.style = "Table Grid"
        except KeyError:
            pass
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        header_row = table.add_row().cells
        header_row[0].text = "Nominativo"
        header_row[1].text = nominativo
        header_row[2].text = "Mansione"
        header_row[3].text = mansione
        for cell in header_row:
            shade_cell(cell, "1A237E")
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.font.size = Pt(10)

        body = [
            ("Tempo di utilizzo", "ore/settimana", f"{ore:.1f}", ""),
            (
                "Soglia esposizione",
                "art. 173 D.Lgs. 81/2008",
                f">= {int(VDT_EXPOSURE_THRESHOLD_HOURS)} h/sett.",
                "",
            ),
            ("Rischio VDT", "Classificazione", esp_label, ""),
        ]
        for code, descr, val, _ in body:
            row = table.add_row().cells
            row[0].text = code
            row[1].text = descr
            row[2].text = val
            row[3].text = ""
            shade_cell(row[0], "F5F5F5")
            for p in row[0].paragraphs:
                for run in p.runs:
                    run.font.bold = True
                    run.font.size = Pt(10)
            for cell in (row[1], row[2], row[3]):
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)

        # Tint the classification row by exposure
        cls_row = table.rows[-1]
        tint = _EXPOSURE_COLORS.get(esp_label, "F5F5F5")
        for cell in cls_row.cells:
            shade_cell(cell, tint)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.bold = True

        # Postazione + attivita sub-row (mirrors template T10 R5)
        sub_row = table.add_row().cells
        sub_row[0].text = "Postazione"
        sub_row[1].text = r.postazione or "—"
        sub_row[2].text = "Ore/sett."
        sub_row[3].text = f"{ore:.1f}"
        for cell in sub_row:
            shade_cell(cell, "EEEEEE")

        # Ergonomic checklist
        add_paragraph(doc, "")
        add_paragraph(doc, "Check-list ergonomica della postazione", bold=True, size=10)
        check_rows = []
        for attr, label in _CHECKLIST_ITEMS:
            ok = bool(getattr(r, attr, False))
            check_rows.append([label, "SI" if ok else "NO"])
        add_data_table(doc, ["Requisito", "Conformita"], check_rows)

        # Surveillance summary (only meaningful when esposto)
        if esposto:
            add_paragraph(doc, "")
            add_paragraph(doc, "Sorveglianza sanitaria oculistica", bold=True, size=10)
            surv_rows = [
                ("Idoneita visiva", r.idoneita_visiva or "—"),
                ("Periodicita", r.periodicita_sorveglianza or "—"),
                (
                    "Eta >= 50 anni",
                    "SI" if r.eta_50_plus else "NO",
                ),
                (
                    "Ultima visita",
                    r.data_ultima_visita.strftime("%d/%m/%Y") if r.data_ultima_visita else "—",
                ),
                (
                    "Prossima visita",
                    r.data_prossima_visita.strftime("%d/%m/%Y") if r.data_prossima_visita else "—",
                ),
            ]
            add_kv_table(doc, surv_rows)

        if r.note:
            add_paragraph(doc, f"Note: {r.note}", italic=True, size=9)
        page_break(doc)

    # ------------------------------------------------------------------
    # Quadro sinottico
    # ------------------------------------------------------------------

    def _add_quadro_sinottico(self, doc, vdt_rows: list, persona_by_id: dict) -> None:
        add_heading(doc, "Quadro sinottico di esposizione", level=1)
        if not vdt_rows:
            add_paragraph(doc, "Nessuna valutazione presente.", italic=True)
            page_break(doc)
            return

        table = doc.add_table(rows=1, cols=4)
        try:
            table.style = "Table Grid"
        except KeyError:
            pass
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        hdr = table.rows[0]
        for i, h in enumerate([
            "Nominativo",
            "Mansione",
            "Tempo di utilizzo (h/sett)",
            "Rischio VDT",
        ]):
            hdr.cells[i].text = h
        style_header_row(hdr)

        for r in vdt_rows:
            persona = persona_by_id.get(r.persona_id) if r.persona_id else None
            nominativo = (persona.nominativo if persona else None) or (
                r.postazione or "—"
            )
            mansione = (persona.mansione if persona else None) or "—"
            ore = float(r.ore_settimanali or 0)
            esp_label = "Esposto" if r.esposto else "Non Esposto"

            row = table.add_row()
            row.cells[0].text = nominativo
            row.cells[1].text = mansione
            row.cells[2].text = f"{ore:.1f}" if ore > 0 else "—"
            row.cells[3].text = esp_label

            tint = _EXPOSURE_COLORS.get(esp_label, "FFFFFF")
            for cell in (row.cells[2], row.cells[3]):
                shade_cell(cell, tint)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.bold = True
                        run.font.size = Pt(10)
            for cell in (row.cells[0], row.cells[1]):
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(10)

        # Counters
        total = len(vdt_rows)
        esposti = sum(1 for r in vdt_rows if r.esposto)
        add_paragraph(doc, "")
        add_paragraph(
            doc,
            f"Totale valutati: {total} · Esposti: {esposti} · Non esposti: {total - esposti}",
            italic=True,
            size=10,
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Misure di prevenzione (static)
    # ------------------------------------------------------------------

    def _add_misure_prevenzione(self, doc) -> None:
        add_heading(doc, "Misure di prevenzione", level=1)

        add_heading(doc, "Pause", level=2)
        add_paragraph(
            doc,
            "Ai sensi dell'art. 175 del D.Lgs. 81/2008, il lavoratore esposto ha "
            "diritto a una pausa di 15 minuti ogni 120 minuti di applicazione "
            "continuativa al videoterminale. La pausa e' considerata a tutti gli "
            "effetti tempo di lavoro e non puo' essere accumulata a inizio o fine "
            "turno.",
        )

        add_heading(doc, "Muoversi di piu'", level=2)
        add_paragraph(
            doc,
            "Alternare la posizione seduta con brevi pause attive: alzarsi, fare "
            "qualche passo, sgranchire spalle e collo. La sedentarieta' prolungata "
            "amplifica i disturbi muscolo-scheletrici.",
        )

        add_heading(doc, "Training per gli occhi", level=2)
        add_paragraph(
            doc,
            "Ogni 20 minuti distogliere lo sguardo dallo schermo e fissare un "
            "punto distante (>= 6 metri) per circa 20 secondi (regola del 20-20-20). "
            "Sbattere consapevolmente le palpebre per ridurre la secchezza oculare.",
        )

        add_heading(doc, "Esercizi di stretching e rilassamento", level=2)
        add_paragraph(
            doc,
            "Eseguire periodicamente esercizi di mobilizzazione di collo, spalle, "
            "polsi e schiena. Mantenere la schiena appoggiata allo schienale, "
            "spalle rilassate, avambracci paralleli al pavimento durante la "
            "digitazione.",
        )

        add_heading(doc, "Lavoratrici gestanti", level=2)
        add_paragraph(
            doc,
            "Per le lavoratrici gestanti l'utilizzo del videoterminale non comporta "
            "rischi specifici da radiazioni; restano comunque applicabili le "
            "ordinarie tutele previste dal D.Lgs. 151/2001 (riduzione/adattamento "
            "delle mansioni in caso di affaticamento o disturbi posturali).",
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Programma di Attuazione (sorveglianza per esposto)
    # ------------------------------------------------------------------

    def _add_programma_attuazione(
        self, doc, vdt_rows: list, persona_by_id: dict
    ) -> None:
        add_heading(doc, "Programma di Attuazione delle Misure di Prevenzione", level=1)
        add_paragraph(
            doc,
            "Tutti i lavoratori esposti al rischio da utilizzo di attrezzature "
            f"munite di videoterminali per almeno {int(VDT_EXPOSURE_THRESHOLD_HOURS)} "
            "ore settimanali sono sottoposti a sorveglianza sanitaria oculistica "
            "ai sensi dell'art. 176 del D.Lgs. 81/2008, integrando i protocolli "
            "predisposti dal Medico Competente. La periodicita' standard e' "
            "quinquennale; e' biennale per i lavoratori di eta' pari o superiore "
            "a 50 anni e per quelli con prescrizioni o idoneita' parziale.",
        )
        add_paragraph(
            doc,
            "Tutti i dipendenti vengono sottoposti a formazione e informazione "
            "specifica sul rischio VDT (postura, ergonomia, gestione delle pause).",
        )

        esposti = [r for r in vdt_rows if r.esposto]
        if not esposti:
            add_paragraph(
                doc,
                "Nessun lavoratore risulta esposto: programma di sorveglianza "
                "sanitaria non attivato.",
                italic=True,
            )
            page_break(doc)
            return

        add_heading(doc, "Calendario sorveglianza sanitaria - lavoratori esposti", level=2)
        rows = []
        for r in esposti:
            persona = persona_by_id.get(r.persona_id) if r.persona_id else None
            nome = (persona.nominativo if persona else None) or (r.postazione or "—")
            rows.append([
                nome,
                r.periodicita_sorveglianza or ("biennale" if r.eta_50_plus else "quinquennale"),
                r.data_ultima_visita.strftime("%d/%m/%Y") if r.data_ultima_visita else "—",
                r.data_prossima_visita.strftime("%d/%m/%Y") if r.data_prossima_visita else "—",
            ])
        add_data_table(
            doc,
            ["Lavoratore", "Periodicita", "Ultima visita", "Prossima visita"],
            rows,
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Dichiarazione del Datore di Lavoro
    # ------------------------------------------------------------------

    def _add_dichiarazione_ddl(self, doc, azienda, persone) -> None:
        add_heading(doc, "Dichiarazione del Datore di Lavoro", level=1)
        ddl_names = [
            p.nominativo for p in persone if p.ruolo_datore_lavoro and p.nominativo
        ]
        ddl = ddl_names[0] if ddl_names else "il Datore di Lavoro"
        ragione = azienda.ragione_sociale or "l'Azienda"

        sede_bits = []
        if getattr(azienda, "sede_legale_via", None):
            sede_bits.append(azienda.sede_legale_via)
        if getattr(azienda, "sede_legale_citta", None):
            sede_bits.append(azienda.sede_legale_citta)
        sede = " - ".join(sede_bits) if sede_bits else "—"

        add_paragraph(
            doc,
            f"Il/la sottoscritto/a {ddl}, in qualita' di Datore di Lavoro di "
            f"{ragione}, con sede legale in {sede},",
        )
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("DICHIARA")
        run.bold = True
        run.font.size = Pt(13)

        add_paragraph(
            doc,
            "che il procedimento sulla valutazione dei rischi da uso di attrezzature "
            "munite di videoterminali ex Titolo VII del D.Lgs. n. 81/2008 e s.m.i. "
            "(D.Lgs. 106/09) e' stato attuato in collaborazione con il Responsabile "
            "del Servizio di Prevenzione e Protezione, con il Medico Competente ove "
            "nominato e previa consultazione del Rappresentante dei Lavoratori per "
            "la Sicurezza.",
        )
        add_paragraph(
            doc,
            "Le misure di prevenzione e protezione individuate nel Programma di "
            "Attuazione saranno adottate secondo il cronoprogramma concordato e "
            "verificate periodicamente. La presente valutazione sara' aggiornata "
            "in occasione di modifiche significative del processo lavorativo o "
            "dell'organizzazione del lavoro.",
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Signature block
    # ------------------------------------------------------------------

    def _add_signature_block(self, doc, persone) -> None:
        add_heading(doc, "Firme", level=1)

        def _first_or_dash(predicate) -> str:
            for p in persone:
                if predicate(p) and p.nominativo:
                    return p.nominativo
            return "—"

        ddl = _first_or_dash(lambda p: bool(p.ruolo_datore_lavoro))
        rspp = _first_or_dash(lambda p: bool(p.ruolo_rspp))
        mc = _first_or_dash(lambda p: bool(p.ruolo_medico_competente))
        rls = _first_or_dash(lambda p: bool(p.ruolo_rls))

        table = doc.add_table(rows=2, cols=2)
        try:
            table.style = "Table Grid"
        except KeyError:
            pass

        cells = [
            (0, 0, "Il Datore di Lavoro", ddl),
            (0, 1, "Il Responsabile del S.P.P.", rspp),
            (1, 0, "Il Medico Competente", mc),
            (1, 1, "Il Rappresentante dei Lavoratori (per consultazione)", rls),
        ]
        for r, c, label, name in cells:
            cell = table.rows[r].cells[c]
            cell.text = ""
            p1 = cell.paragraphs[0]
            run = p1.add_run(label)
            run.font.bold = True
            run.font.size = Pt(10)
            p2 = cell.add_paragraph(f"({name})")
            for run in p2.runs:
                run.font.size = Pt(10)
                run.italic = True
            cell.add_paragraph("")
            cell.add_paragraph("__________________________")
