"""PEE - Piano Gestione Emergenze variante Comune/Edificio."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_pee
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

TEMPLATE = TEMPLATES_DIR / "PIANO GESTIONE EMERGENZE - COMUNE.docx"
TIPO_DOC = "pee_comune"


class PeeComuneGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        pee = await load_pee(self.db, self.azienda_id, tipo="comune") or await load_pee(self.db, self.azienda_id, tipo="azienda")

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"PIANO DI EMERGENZA EDIFICIO - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda riferimento", azienda.ragione_sociale or ""),
            ("Sede", f"{azienda.sede_legale_via or ''}, {azienda.sede_legale_citta or ''}"),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Tipo", "Edificio multi-tenant"),
        ])

        add_heading(doc, "Obiettivo", level=2)
        add_paragraph(doc, "Il presente piano descrive la gestione coordinata delle emergenze in edificio condiviso, con attribuzione di ruoli e procedure tra le diverse aziende occupanti e l'amministratore condominiale.")

        if pee:
            add_heading(doc, "Numeri di emergenza", level=2)
            tel = pee.telefoni_emergenza or {"Numero Unico Europeo": "112"}
            add_data_table(doc, ["Ente/Ruolo", "Numero"], [[k, v] for k, v in tel.items()])
            add_heading(doc, "Coordinamento emergenze", level=2)
            add_kv_table(doc, [
                ("Coordinatore emergenza", pee.coordinatore_emergenza or "—"),
                ("Punto di raccolta", pee.punto_raccolta or "—"),
                ("Vie di fuga", pee.vie_fuga or "—"),
            ])

        add_heading(doc, "Procedure comuni multi-tenant", level=2)
        add_paragraph(doc, "In caso di attivazione dell'allarme generale dell'edificio, tutte le aziende interrompono le attivita, attivano il proprio coordinatore locale e procedono all'evacuazione verso il punto di raccolta condominiale.")

        add_heading(doc, "Manutenzione dei presidi comuni", level=2)
        add_paragraph(doc, "Gli impianti antincendio comuni (rivelazione, idranti, porte REI) sono manutenuti dall'amministratore condominiale con cadenza almeno semestrale e documentazione conservata a disposizione.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "PEE_COMUNE"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
