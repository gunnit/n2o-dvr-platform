"""Shared scaffolding for Biologico generators (alimentare/asilo/dentisti)."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_biologico
from app.services.document_generator.docx_utils import (
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    format_sede,
    slugify,
)


async def build_biologico_document(
    gen: BaseDocumentGenerator,
    *,
    settore_key: str,
    titolo: str,
    agenti_default: list,
    misure_default: list,
    dpi_default: list,
    protocollo_default: str,
    tipo_doc: str,
    tipo_aliases: list[str],
) -> str:
    data = await gen.load_data()
    azienda = data["azienda"]
    generated_at = data["generated_at"]
    rows = await load_biologico(gen.db, gen.azienda_id, settore_key)
    row = rows[0] if rows else None

    doc = Document()
    add_heading(doc, titolo, level=1)
    add_kv_table(doc, [
        ("Azienda", azienda.ragione_sociale or ""),
        ("Sede", format_sede(azienda, "legale")),
        ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
        ("Settore di riferimento", settore_key.capitalize()),
        ("Riferimento normativo", "D.Lgs. 81/2008 Titolo X - Esposizione ad agenti biologici"),
    ])

    add_heading(doc, "Inquadramento", level=2)
    add_paragraph(doc, "La valutazione segue il Titolo X del D.Lgs. 81/2008 e classifica gli agenti biologici nei gruppi da 1 a 4 dell'Allegato XLVI in base a patogenicita, contagiosita e disponibilita di terapia/profilassi.")

    add_heading(doc, "Agenti biologici identificati", level=2)
    agenti = (row.agenti_identificati if row and row.agenti_identificati else None) or agenti_default
    add_data_table(doc, ["Agente", "Gruppo", "Via di esposizione", "Patologia"],
                   [[a.get("nome", ""), a.get("gruppo", ""), a.get("via", ""), a.get("patologia", "")] for a in agenti])

    add_heading(doc, "Misure di prevenzione e protezione collettive", level=2)
    misure = (row.misure_protettive if row and row.misure_protettive else None) or [{"descrizione": m} for m in misure_default]
    for m in misure:
        add_paragraph(doc, f"- {m.get('descrizione', '')}")

    add_heading(doc, "Dispositivi di protezione individuale (DPI)", level=2)
    dpi = (row.dpi_richiesti if row and row.dpi_richiesti else None) or [{"descrizione": d} for d in dpi_default]
    for d in dpi:
        add_paragraph(doc, f"- {d.get('descrizione', '')}")

    add_heading(doc, "Sorveglianza sanitaria e formazione", level=2)
    add_paragraph(doc, (row.protocollo_sanitario if row and row.protocollo_sanitario else protocollo_default))
    if row and row.formazione_specifica:
        add_heading(doc, "Formazione specifica", level=3)
        add_paragraph(doc, row.formazione_specifica)

    add_heading(doc, "Esito valutazione", level=2)
    add_kv_table(doc, [
        ("Livello di rischio complessivo", (row.livello_rischio if row else "MEDIO") or "MEDIO"),
        ("Periodicita revisione", "Annuale o in caso di modifiche organizzative rilevanti"),
    ])

    version = await _next_version(gen, tipo_doc, tipo_aliases)
    output_dir = gen._get_output_dir()
    slug = slugify(azienda.ragione_sociale or "azienda")
    filepath = os.path.join(output_dir, f"{tipo_doc}_{slug}_v{version}.docx")
    doc.save(filepath)
    return filepath


async def _next_version(gen: BaseDocumentGenerator, tipo_doc: str, aliases: list[str]) -> int:
    stmt = (
        select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
        .where(DocumentoGenerato.azienda_id == gen.azienda_id)
        .where(DocumentoGenerato.tipo_documento.in_([tipo_doc] + aliases))
    )
    r = await gen.db.execute(stmt)
    return (r.scalar() or 0) + 1
