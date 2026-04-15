"""Allegato VDT — Videoterminali. D.Lgs. 81/2008 Titolo VII."""

import os
from datetime import datetime

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_vdt
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

TEMPLATE = TEMPLATES_DIR / "ALLEGATO RISCHIO VDT.docx"
TIPO_DOC = "allegato_vdt"


class AllegatoVdtGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at: datetime = data["generated_at"]
        vdt_rows = await load_vdt(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"VALUTAZIONE SPECIFICA - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Numero postazioni VDT valutate", str(len(vdt_rows))),
            ("Lavoratori esposti (>=20 h/sett.)", str(sum(1 for r in vdt_rows if r.esposto))),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimento normativo", "D.Lgs. 81/2008 Titolo VII artt. 172-179"),
        ])

        add_heading(doc, "Definizione di lavoratore esposto", level=2)
        add_paragraph(doc, "Ai sensi dell'art. 173 del D.Lgs. 81/2008, si considera lavoratore esposto chi utilizza un'attrezzatura munita di videoterminale in modo sistematico o abituale per almeno 20 ore settimanali.")

        add_heading(doc, "Riepilogo postazioni", level=2)
        if not vdt_rows:
            add_paragraph(doc, "Nessuna postazione VDT valutata.", italic=True)
        else:
            headers = ["Postazione", "Ore/sett", "Esposto", "Idoneita visiva", "Sorveglianza"]
            rows = [[
                r.postazione or "",
                f"{float(r.ore_settimanali):.0f}",
                "SI" if r.esposto else "NO",
                r.idoneita_visiva or "—",
                r.periodicita_sorveglianza or "—",
            ] for r in vdt_rows]
            add_data_table(doc, headers, rows)

        add_heading(doc, "Check-list ergonomica per postazione", level=2)
        for idx, r in enumerate(vdt_rows, 1):
            add_heading(doc, f"{idx}. {r.postazione}", level=3)
            add_data_table(doc, ["Requisito", "Conformita"], [
                ["Schermo conforme (leggibilita, stabilita, regolazioni)", "SI" if r.schermo_conforme else "NO"],
                ["Tastiera separata e inclinabile", "SI" if r.tastiera_separata else "NO"],
                ["Sedile regolabile in altezza, con schienale regolabile", "SI" if r.sedile_regolabile else "NO"],
                ["Poggiapiedi disponibile se richiesto", "SI" if r.poggiapiedi_disponibile else "NO"],
                ["Illuminazione adeguata (300-500 lux)", "SI" if r.illuminazione_adeguata else "NO"],
                ["Assenza di riflessi e abbagliamento", "SI" if r.riflessi_assenti else "NO"],
                ["Spazio di lavoro sufficiente", "SI" if r.spazio_adeguato else "NO"],
                ["Pause previste (15 min ogni 2 ore)", "SI" if r.pause_previste else "NO"],
            ])

        add_heading(doc, "Sorveglianza sanitaria", level=2)
        add_paragraph(doc, "Art. 176 D.Lgs. 81/2008: la sorveglianza sanitaria e prevista con periodicita quinquennale per i lavoratori esposti, biennale per i lavoratori con prescrizioni o di eta superiore a 50 anni.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_VDT"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
