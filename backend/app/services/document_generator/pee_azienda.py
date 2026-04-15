"""PEE - Piano di Emergenza ed Evacuazione (variante aziendale)."""

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

TEMPLATE = TEMPLATES_DIR / "PIANO GESTIONE EMERGENZE - AZIENDA.docx"
TIPO_DOC = "pee_azienda"


class PeeAziendaGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        pee = await load_pee(self.db, self.azienda_id, tipo="azienda")

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {
                "RAGIONE SOCIALE": azienda.ragione_sociale or "",
                "[AZIENDA]": azienda.ragione_sociale or "",
            })
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"PIANO DI EMERGENZA - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Sede", f"{azienda.sede_legale_via or ''}, {azienda.sede_legale_citta or ''}"),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Coordinatore emergenza", (pee.coordinatore_emergenza if pee else "—") or "—"),
            ("Punto di raccolta", (pee.punto_raccolta if pee else "—") or "—"),
            ("Frequenza prove", (pee.frequenza_prove if pee else "annuale") or "annuale"),
            ("Tempo evacuazione stimato (min)", str(pee.tempo_evacuazione_stimato_min) if pee and pee.tempo_evacuazione_stimato_min else "—"),
            ("Riferimento normativo", "D.M. 02/09/2021 (Criteri gestione emergenza luoghi di lavoro)"),
        ])

        if pee:
            add_heading(doc, "Numeri telefonici di emergenza", level=2)
            rows = [[k, v] for k, v in (pee.telefoni_emergenza or {}).items()]
            add_data_table(doc, ["Ente/Ruolo", "Numero"], rows or [["Numero Unico Europeo", "112"]])

            add_heading(doc, "Squadra di emergenza", level=2)
            members = pee.squadra_emergenza or []
            if members:
                add_data_table(doc, ["Nominativo", "Ruolo"], [[m.get("nome", ""), m.get("ruolo", "")] for m in members])
            else:
                add_paragraph(doc, "Squadra non configurata.", italic=True)

            add_heading(doc, "Vie di fuga e punto di raccolta", level=2)
            add_paragraph(doc, pee.vie_fuga or "Vie di fuga indicate dalla segnaletica di sicurezza UNI EN ISO 7010.")
            add_paragraph(doc, f"Punto di raccolta: {pee.punto_raccolta or '—'}")

            add_heading(doc, "Scenari di emergenza", level=2)
            for s in (pee.scenari or []):
                add_heading(doc, f"Scenario {s.get('codice', '')} - {s.get('titolo', '')}", level=3)
                add_paragraph(doc, s.get("procedura", ""))

        add_heading(doc, "Procedure generali di evacuazione", level=2)
        add_paragraph(doc, "1. Mantenere la calma. 2. Avvisare chiunque si trovi in difficolta. 3. Non utilizzare ascensori. 4. Dirigersi ordinatamente verso il punto di raccolta seguendo la segnaletica. 5. Non rientrare negli ambienti fino al cessato allarme.")

        add_heading(doc, "Formazione e prove di evacuazione", level=2)
        add_paragraph(doc, "La squadra di emergenza riceve formazione specifica (primo soccorso D.M. 388/2003 e antincendio D.M. 02/09/2021). Prove di evacuazione con cadenza almeno annuale con registrazione dell'esito.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "PEE_AZIENDA"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
