"""Allegato Gestanti - D.Lgs. 151/2001."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_gestanti
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

TEMPLATE = TEMPLATES_DIR / "ALLEGATO GESTANTI.docx"
TIPO_DOC = "allegato_gestanti"


class AllegatoGestantiGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        gestanti = await load_gestanti(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"VALUTAZIONE SPECIFICA - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Lavoratrici in stato di gravidanza/allattamento notificate", str(len(gestanti))),
            ("Riferimento normativo", "D.Lgs. 26 marzo 2001 n. 151 (Testo Unico maternita)"),
        ])

        add_heading(doc, "Inquadramento normativo", level=2)
        add_paragraph(doc, "Il D.Lgs. 151/2001 tutela la salute delle lavoratrici in stato di gravidanza, puerperio (fino a 7 mesi dal parto) e durante l'allattamento. Gli Allegati A, B e C individuano rispettivamente i lavori vietati, quelli vietati salvo deroga e gli agenti nocivi cui non possono essere esposte.")

        if not gestanti:
            add_paragraph(doc, "Non sono presenti lavoratrici in stato di gravidanza o allattamento al momento della valutazione.", italic=True)
        for idx, g in enumerate(gestanti, 1):
            page_break(doc)
            nome = g.persona.nominativo if getattr(g, "persona", None) else "—"
            add_heading(doc, f"{idx}. Scheda lavoratrice", level=2)
            add_kv_table(doc, [
                ("Lavoratrice", nome),
                ("Stato", (g.stato or "").capitalize()),
                ("Data notifica", g.data_notifica.strftime("%d/%m/%Y") if g.data_notifica else "—"),
                ("Data presunto parto", g.data_presunto_parto.strftime("%d/%m/%Y") if g.data_presunto_parto else "—"),
                ("Mansione alternativa", g.mansione_alternativa or "—"),
                ("Astensione anticipata richiesta", "SI" if g.richiesta_astensione_anticipata else "NO"),
            ])
            add_heading(doc, "Rischi identificati e misure di adeguamento", level=3)
            rischi = g.rischi_vietati or []
            if rischi:
                rows = [[r.get("rischio", ""), r.get("allegato", ""), r.get("misura", "")] for r in rischi]
                add_data_table(doc, ["Rischio", "Allegato D.Lgs. 151/2001", "Misura adottata"], rows)
            else:
                add_paragraph(doc, "Nessun rischio vietato identificato.", italic=True)

            if g.misure_adeguamento:
                add_paragraph(doc, g.misure_adeguamento)

            add_heading(doc, "Firme", level=3)
            add_data_table(doc, ["Ruolo", "Firmatario"], [
                ["Lavoratrice", g.firma_lavoratrice or "________________________"],
                ["Datore di lavoro", g.firma_datore_lavoro or "________________________"],
                ["RSPP", g.firma_rspp or "________________________"],
                ["Medico competente", g.firma_medico_competente or "________________________"],
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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_GESTANTI"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
