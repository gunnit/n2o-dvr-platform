"""PEE - Piano di Emergenza ed Evacuazione (variante aziendale)."""

import logging
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from sqlalchemy import func, select

from app.data.pee_procedures import merge_with_overrides
from app.models.ambiente import Ambiente
from app.models.ambiente_foto import AmbienteFoto
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

logger = logging.getLogger(__name__)

TEMPLATE = TEMPLATES_DIR / "PIANO GESTIONE EMERGENZE - AZIENDA.docx"
TIPO_DOC = "pee_azienda"


async def _find_planimetria_path(db, azienda_id) -> str | None:
    """Return the on-disk path of a planimetria photo for this azienda, if any.

    Heuristic: any ``ambienti_foto`` row whose filename (or path) contains
    the substring "planimetria" (case-insensitive) is treated as the floor
    plan. If multiple rows match we pick the most recent one. When no
    match exists we return ``None`` so the caller can render the placeholder.

    In fixture/test mode ``db`` is ``None`` (see scripts/verify_all_generators.py);
    we short-circuit so the test runner produces the placeholder output rather
    than crashing on the lookup.
    """
    if db is None:
        return None
    stmt = (
        select(AmbienteFoto)
        .join(Ambiente, Ambiente.id == AmbienteFoto.ambiente_id)
        .where(Ambiente.azienda_id == azienda_id)
        .where(
            func.lower(AmbienteFoto.filename).like("%planimetria%")
        )
        .order_by(AmbienteFoto.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    # Only embed if the file still exists on disk.
    if not row.file_path or not os.path.exists(row.file_path):
        return None
    return row.file_path


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

        # Planimetria (US-4.1 AC3): embed the uploaded floor plan if one exists
        # among ambienti_foto (filename containing "planimetria"); otherwise
        # render the placeholder text so the operator knows to attach one.
        add_heading(doc, "Planimetria di emergenza", level=2)
        planimetria_path = await _find_planimetria_path(self.db, self.azienda_id)
        if planimetria_path:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            try:
                run.add_picture(planimetria_path, width=Inches(6.0))
            except Exception:
                # Any load-time error (corrupt image, unsupported format)
                # falls back to the placeholder so generation never breaks.
                logger.exception(
                    "Failed to embed planimetria for azienda %s", self.azienda_id
                )
                add_paragraph(
                    doc,
                    "Inserire planimetria (immagine allegata non leggibile).",
                    italic=True,
                )
            add_paragraph(
                doc,
                "Planimetria indicativa con percorsi di esodo, uscite di sicurezza e punto di raccolta.",
                italic=True,
            )
        else:
            add_paragraph(doc, "Inserire planimetria", italic=True)

        # Structured A-E procedures per event type (US-4.2). Standard procedures
        # from app.data.pee_procedures are merged with per-client overrides
        # persisted in pee.scenari. We always render the full 5×5 grid so the
        # operator gets consistent coverage even when no overrides exist.
        add_heading(doc, "Procedure di emergenza per scenario", level=2)
        merged_events = merge_with_overrides(pee.scenari if pee else None)
        for event in merged_events:
            add_heading(doc, event["titolo"], level=3)
            for proc in event["procedure"]:
                suffix = " (personalizzata)" if proc.get("personalizzata") else ""
                add_paragraph(
                    doc,
                    f"{proc['lettera']}. {proc['titolo']}{suffix}",
                    bold=True,
                )
                add_paragraph(doc, proc["testo"])

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
