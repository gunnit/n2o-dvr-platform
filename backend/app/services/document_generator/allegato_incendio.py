"""Allegato Rischio Incendio - D.M. 03/09/2021."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_incendio
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

TEMPLATE = TEMPLATES_DIR / "ALLEGATO RISCHIO INCENDIO.docx"
TIPO_DOC = "allegato_incendio"


class AllegatoIncendioGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        incendi = await load_incendio(self.db, self.azienda_id)
        ambienti_map = {a.id: a for a in data["ambienti"]}

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
            ("Riferimento normativo", "D.M. 03/09/2021 (Gestione della sicurezza antincendio nei luoghi di lavoro)"),
        ])

        add_heading(doc, "Metodologia di valutazione", level=2)
        add_paragraph(doc, "Il rischio incendio e valutato combinando tre indicatori, ciascuno in scala 1-3:")
        add_data_table(doc, ["Codice", "Indicatore", "Scala 1-3"], [
            ["INF", "Infiammabilita e carico d'incendio", "1=basso; 2=medio; 3=alto"],
            ["SI",  "Sorgenti di ignizione presenti", "1=assenti/rare; 2=discrete; 3=numerose"],
            ["PI",  "Presenza di persone e loro esodo", "1=semplice; 2=medio; 3=complesso"],
        ])
        add_paragraph(doc, "Classificazione del rischio = INF + SI + PI: 3-4 = BASSO, 5-7 = MEDIO, 8-9 = ALTO.")

        add_heading(doc, "Valutazione per ambiente", level=2)
        if not incendi:
            add_paragraph(doc, "Nessuna valutazione del rischio incendio disponibile.", italic=True)
        else:
            headers = ["Ambiente", "INF", "SI", "PI", "Totale", "Livello", "Uscite", "Estintori"]
            rows = []
            for v in incendi:
                amb_name = (
                ambienti_map[v.ambiente_id].nome
                if v.ambiente_id in ambienti_map
                else (v.nome_area or "—")
            )
                rows.append([
                    amb_name, str(v.inf), str(v.si), str(v.pi),
                    str(v.punteggio_totale or (v.inf + v.si + v.pi)),
                    v.livello_rischio or "",
                    str(v.uscite_emergenza), str(v.estintori_presenti),
                ])
            add_data_table(doc, headers, rows)

        add_heading(doc, "Misure di prevenzione e protezione", level=2)
        for v in incendi:
            amb_name = (
                ambienti_map[v.ambiente_id].nome
                if v.ambiente_id in ambienti_map
                else (v.nome_area or "—")
            )
            add_heading(doc, amb_name, level=3)
            add_paragraph(doc, v.misure_prevenzione or "Misure standard: estintori a portata, vie di fuga segnalate e libere, idoneo sistema di allarme.")

        add_heading(doc, "Gestione dell'emergenza", level=2)
        add_paragraph(doc, "Il personale e addestrato all'uso degli estintori. Il piano di emergenza (allegato PEE) descrive procedure dettagliate per ogni scenario d'incendio. E prevista esercitazione antincendio almeno annuale (D.M. 02/09/2021 art. 6).")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_INCENDIO"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
