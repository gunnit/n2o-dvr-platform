"""Allegato MMC — Movimentazione Manuale dei Carichi (NIOSH method).

Produces an .docx that starts from the ALLEGATO RISCHIO MMC.docx template
and appends azienda-specific NIOSH assessments (per worker, per task).
"""

import os
from datetime import datetime
from pathlib import Path

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_mmc
from app.services.document_generator.docx_utils import (
    RISK_COLORS,
    TEMPLATES_DIR,
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    page_break,
    replace_placeholders,
    slugify,
)

TEMPLATE = TEMPLATES_DIR / "ALLEGATO RISCHIO MMC.docx"
TIPO_DOC = "allegato_mmc"


class AllegatoMmcGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at: datetime = data["generated_at"]
        mmc_rows = await load_mmc(self.db, self.azienda_id)

        # Load template or start fresh if missing
        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            # Light-touch placeholder replacement for common markers
            replace_placeholders(doc, {
                "RAGIONE SOCIALE": azienda.ragione_sociale or "",
                "[AZIENDA]": azienda.ragione_sociale or "",
            })
        else:
            doc = Document()

        # Append azienda-specific dynamic section on a new page
        page_break(doc)
        add_heading(doc, f"VALUTAZIONE SPECIFICA - {azienda.ragione_sociale}", level=1)

        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Sede legale", f"{azienda.sede_legale_via or ''}, {azienda.sede_legale_citta or ''}"),
            ("Partita IVA", azienda.partita_iva or ""),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Metodo adottato", "NIOSH - ISO 11228-1 (PLR = CP x A x B x C x D x E x F)"),
        ])

        add_heading(doc, "Riepilogo compiti valutati", level=2)
        if not mmc_rows:
            add_paragraph(doc, "Nessuna attivita di movimentazione manuale dei carichi valutata per questa azienda.", italic=True)
        else:
            headers = ["Compito", "Peso (kg)", "PLR", "Indice IR", "Livello", "Note"]
            rows = []
            for r in mmc_rows:
                rows.append([
                    r.compito or "",
                    f"{float(r.peso_kg):.1f}",
                    f"{float(r.plr):.2f}" if r.plr else "",
                    f"{float(r.indice_ir):.2f}" if r.indice_ir else "",
                    r.livello_rischio or "",
                    (r.note or "")[:80],
                ])
            add_data_table(doc, headers, rows)

        # Calculation detail per task
        for idx, r in enumerate(mmc_rows, 1):
            page_break(doc)
            add_heading(doc, f"{idx}. {r.compito}", level=2)
            add_kv_table(doc, [
                ("Peso effettivamente sollevato", f"{float(r.peso_kg):.1f} kg"),
                ("Costante di peso (CP)", f"{float(r.cp):.1f} kg  [M adulto=25, F adulta=20, <18 anni ridotto]"),
                ("Fattore altezza A", f"{float(r.fattore_a):.2f}"),
                ("Fattore dislocazione B", f"{float(r.fattore_b):.2f}"),
                ("Fattore orizzontale C", f"{float(r.fattore_c):.2f}"),
                ("Fattore angolare D", f"{float(r.fattore_d):.2f}"),
                ("Fattore presa E", f"{float(r.fattore_e):.2f}"),
                ("Fattore frequenza F", f"{float(r.fattore_f):.2f}"),
                ("PLR (Peso Limite Raccomandato)", f"{float(r.plr):.2f} kg" if r.plr else "—"),
                ("Indice IR = peso / PLR", f"{float(r.indice_ir):.2f}" if r.indice_ir else "—"),
                ("Livello di rischio", r.livello_rischio or ""),
            ])
            add_paragraph(doc, "Interpretazione: IR<=0.75 VERDE - rischio trascurabile; 0.75-1.0 GIALLO - sorveglianza sanitaria; >1.0 ROSSO - riprogettazione.", italic=True, size=9)

        # Save
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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_MMC"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
