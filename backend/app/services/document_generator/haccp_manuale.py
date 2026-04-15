"""HACCP Manuale di Autocontrollo - Reg. CE 852/2004 + Reg. CE 178/2002."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_haccp
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

TEMPLATE = TEMPLATES_DIR / "HACCP.docx"
TIPO_DOC = "haccp"


class HaccpManualeGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        config, forms = await load_haccp(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"MANUALE HACCP - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Tipologia attivita", (config.tipologia_attivita if config else "—") or "—"),
            ("Numero pasti/giorno", str(config.numero_pasti_giorno) if (config and config.numero_pasti_giorno) else "—"),
            ("Responsabile HACCP", (config.responsabile_haccp if config else "—") or "—"),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimenti normativi", "Reg. CE 852/2004, Reg. CE 178/2002, Reg. CE 2073/2005"),
        ])

        add_heading(doc, "Campo di applicazione", level=2)
        add_paragraph(doc, "Il presente manuale si applica a tutte le fasi di preparazione, cottura, conservazione e somministrazione degli alimenti svolte presso l'azienda.")

        add_heading(doc, "Principi HACCP", level=2)
        add_paragraph(doc, "Il sistema si fonda sui 7 principi Codex Alimentarius: 1) analisi dei pericoli, 2) identificazione CCP, 3) limiti critici, 4) monitoraggio, 5) azioni correttive, 6) verifica, 7) documentazione.")

        if config:
            add_heading(doc, "Alimenti trattati", level=2)
            tipi = config.tipi_alimenti_trattati or []
            add_paragraph(doc, ", ".join(tipi) if tipi else "—")

            add_heading(doc, "Punti critici di controllo (CCP)", level=2)
            ccps = config.ccps or []
            if ccps:
                rows = [[c.get("codice", ""), c.get("nome", ""), c.get("limite_critico", "")] for c in ccps]
                add_data_table(doc, ["Codice", "CCP", "Limite critico"], rows)

        add_heading(doc, "Procedure di monitoraggio", level=2)
        add_paragraph(doc, "Ogni CCP e monitorato mediante le schede di autocontrollo SA-01 ÷ SA-16 (allegate), compilate secondo la frequenza indicata.")

        add_heading(doc, "Gestione delle non conformita", level=2)
        add_paragraph(doc, "In caso di superamento dei limiti critici, l'alimento viene isolato. Se non recuperabile, viene smaltito con registrazione sulla scheda SA-13. L'azione correttiva viene comunicata al responsabile HACCP.")

        add_heading(doc, "Formazione del personale", level=2)
        add_paragraph(doc, "Tutti gli operatori del settore alimentare ricevono formazione HACCP ai sensi dell'art. 4 del Reg. CE 852/2004 all'assunzione e aggiornamento biennale.")

        add_heading(doc, "Schede di autocontrollo allegate", level=2)
        if forms:
            add_data_table(doc, ["Codice", "Titolo"], [[f.form_code, f.form_title] for f in forms])
        else:
            add_paragraph(doc, "Schede non configurate.", italic=True)

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "HACCP"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
