"""DUVRI - Documento Unico Valutazione Rischi Interferenze (art. 26 D.Lgs. 81/2008)."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_duvri
from app.services.document_generator.docx_utils import (
    TEMPLATES_DIR,
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


class DuvriGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        duvri_rows = await load_duvri(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
            # Blank the sample dates left in the template body; the generator
            # supplies the real appalto/sottoscrizione dates below.
            scrub_body(doc, {"01.11.2025": "__/__/____", "15/01/2026": "__/__/____"})
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
        add_paragraph(doc, "Il presente DUVRI individua le misure di prevenzione e protezione necessarie ad eliminare o ridurre al minimo i rischi derivanti dalle interferenze tra le attivita del committente e quelle dell'impresa appaltatrice.")
        add_paragraph(doc, "Ai sensi dell'art. 26 comma 3-bis del D.Lgs. 81/2008 (introdotto dal D.Lgs. 106/2009), l'obbligo di redazione del DUVRI non si applica ai servizi di natura intellettuale, alle mere forniture di materiali o attrezzature, nonche ai lavori o servizi la cui durata non superi i cinque uomini-giorno, salvo che comportino rischi derivanti da agenti cancerogeni, biologici, atmosfere esplosive o dai rischi particolari di cui all'Allegato XI.")

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
                ("Importo appalto (EUR)", f"{float(d.importo_appalto):,.2f}" if d.importo_appalto else "—"),
                ("Costi della sicurezza (EUR)", f"{float(d.costi_sicurezza):,.2f}" if d.costi_sicurezza else "—"),
            ])

            attrezz = d.attrezzature_appaltatore or []
            if attrezz:
                add_heading(doc, "Attrezzature / attivita appaltatore", level=3)
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
        doc.save(filepath)
        return filepath

    async def _next_version(self) -> int:
        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "DUVRI"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
