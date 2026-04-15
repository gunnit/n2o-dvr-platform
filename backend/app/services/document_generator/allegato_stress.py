"""Allegato Stress Lavoro-Correlato — metodologia INAIL."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_stress
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

TEMPLATE = TEMPLATES_DIR / "ALLEGATO STRESS DA LAVORO CORRELATO.docx"
TIPO_DOC = "allegato_stress"


class AllegatoStressGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        stress = await load_stress(self.db, self.azienda_id)

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            replace_placeholders(doc, {"RAGIONE SOCIALE": azienda.ragione_sociale or "", "[AZIENDA]": azienda.ragione_sociale or ""})
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"VALUTAZIONE SPECIFICA - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Gruppo omogeneo", stress.gruppo_omogeneo if stress else "N/D"),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Metodologia", "INAIL 2011 - 3 aree: Eventi Sentinella (A), Contenuto (B), Contesto (C)"),
        ])

        add_heading(doc, "Inquadramento normativo", level=2)
        add_paragraph(doc, "Art. 28 comma 1-bis del D.Lgs. 81/2008 prevede la valutazione del rischio stress lavoro-correlato secondo le indicazioni della Commissione Consultiva Permanente (metodologia INAIL 2011).")

        if stress:
            add_heading(doc, "Punteggi per area", level=2)
            add_data_table(doc, ["Area", "Punteggio", "Livello parziale"], [
                ["A - Eventi sentinella (infortuni, assenze, turnover)", str(stress.punteggio_a or 0), _livello(stress.punteggio_a)],
                ["B - Contenuto del lavoro (ritmi, monotonia, orari)", str(stress.punteggio_b or 0), _livello(stress.punteggio_b)],
                ["C - Contesto del lavoro (comunicazione, autonomia)", str(stress.punteggio_c or 0), _livello(stress.punteggio_c)],
            ])
            add_heading(doc, "Esito complessivo", level=2)
            add_kv_table(doc, [
                ("Punteggio totale (A+B+C)", str(stress.punteggio_totale or 0)),
                ("Livello di rischio", stress.livello_rischio or "—"),
                ("Misure correttive pianificate", stress.misure_correttive or "Monitoraggio e aggiornamento annuale"),
            ])

            add_heading(doc, "Dettaglio indicatori per area", level=2)
            _area_detail(doc, "Area A - Eventi Sentinella", stress.area_a_eventi_sentinella or {})
            _area_detail(doc, "Area B - Contenuto del lavoro", stress.area_b_contenuto_lavoro or {})
            _area_detail(doc, "Area C - Contesto del lavoro", stress.area_c_contesto_lavoro or {})
        else:
            add_paragraph(doc, "Nessuna valutazione stress lavoro-correlato disponibile per questa azienda.", italic=True)

        add_heading(doc, "Azioni successive", level=2)
        add_paragraph(doc, "In presenza di rischio medio o alto e richiesta una valutazione approfondita con questionari soggettivi (HSE, OSI, ecc.) e l'adozione di misure correttive specifiche.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_STRESS"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1


def _livello(p: int | None) -> str:
    if p is None:
        return "—"
    if p <= 2:
        return "BASSO"
    if p <= 4:
        return "MEDIO"
    return "ALTO"


def _area_detail(doc, title: str, payload: dict) -> None:
    add_heading(doc, title, level=3)
    if not payload:
        add_paragraph(doc, "Nessun dato registrato.", italic=True, size=9)
        return
    rows = [[str(k), str(v)] for k, v in payload.items()]
    add_data_table(doc, ["Indicatore", "Risposta"], rows)
