"""HACCP — 16 schede di autocontrollo (SA-01 .. SA-16) bundled into one zip.

Output: a single .docx per form, then all assembled into a .zip that is
returned as the "file" for this doc type. If zip creation is not possible,
returns the main index .docx.

US-4.4: each form is pre-branded with the N2O letterhead logo (when
``backend/app/assets/logo.png`` is present) and the client's
ragione sociale, and the operator can pick a subset of forms via
``options.selected_codes``.
"""

import io
import logging
import os
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.branding import Branding, resolve_logo_source
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

logger = logging.getLogger(__name__)

TIPO_DOC = "haccp_forms"
HACCP_TEMPLATES_DIR = TEMPLATES_DIR / "haccp"


def _normalize_code(code: str) -> str:
    """Compare codes ignoring case, hyphens and whitespace."""
    return (code or "").upper().replace("-", "").replace(" ", "").strip()


def _add_branding_header(doc, azienda, branding: Branding | None = None) -> None:
    """Stamp the consultancy logo + client ragione sociale at the top.

    Used both for the bundled INDEX doc and every individual SA-* form so the
    operator gets a uniformly branded packet (US-4.4 AC1). When the logo file
    is missing the header degrades to a plain client-name line — matching the
    DVR Master generator's degrade-gracefully behaviour. ``branding`` carries
    the per-organization logo (falls back to the committed default).
    """
    logo_src = resolve_logo_source(branding or Branding.default())
    if logo_src is not None:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        try:
            run.add_picture(logo_src, width=Inches(1.6))
        except Exception:
            # Corrupt or unreadable image — drop the picture and let the
            # client-name line below act as the brand mark.
            logger.exception("HACCP form logo embed failed")
    name = (azienda.ragione_sociale or "").strip()
    if name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(name)
        run.bold = True


class HaccpFormsGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        config, forms = await load_haccp(self.db, self.azienda_id)

        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        version = await self._next_version()

        # US-4.4 AC2: filter forms by the dialog-supplied selected_codes when
        # provided. Codes are normalised so the dialog can pass either
        # "SA-01" or "sa01"; missing/empty option means "all forms" so the
        # legacy "Genera Tutti" behaviour is preserved.
        selected_codes_raw = self.options.get("selected_codes")
        if selected_codes_raw:
            wanted = {_normalize_code(c) for c in selected_codes_raw}
            selected_forms = [f for f in forms if _normalize_code(f.form_code) in wanted]
        else:
            selected_forms = list(forms)

        # Build individual forms
        form_paths: list[str] = []
        for form in selected_forms:
            form_path = self._build_single_form(output_dir, slug, version, form, azienda)
            form_paths.append(form_path)

        # Build index document — also branded so the zip header sheet
        # carries the same letterhead as the forms inside it.
        index_doc = Document()
        _add_branding_header(index_doc, azienda, self.branding)
        add_heading(index_doc, f"SCHEDE DI AUTOCONTROLLO HACCP - {azienda.ragione_sociale}", level=1)
        add_kv_table(index_doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Responsabile HACCP", (config.responsabile_haccp if config else "—") or "—"),
            ("Numero schede allegate", str(len(form_paths))),
        ])
        add_heading(index_doc, "Elenco schede", level=2)
        add_data_table(
            index_doc,
            ["Codice", "Titolo"],
            [[f.form_code, f.form_title] for f in selected_forms] or [["—", "—"]],
        )

        # Package all into a zip file
        zip_path = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write index doc to zip
            idx_buf = io.BytesIO()
            index_doc.save(idx_buf)
            idx_buf.seek(0)
            zf.writestr("INDICE_schede_HACCP.docx", idx_buf.read())
            for fp in form_paths:
                zf.write(fp, arcname=os.path.basename(fp))
        return zip_path

    def _build_single_form(self, output_dir: str, slug: str, version: int, form, azienda) -> str:
        """Clone template form if available, or build from scratch; save .docx."""
        template_map = {
            # Known template filename patterns (some may not exist; fallback to scratch)
        }
        code = form.form_code
        template_candidate: Path | None = None
        if HACCP_TEMPLATES_DIR.exists():
            for p in HACCP_TEMPLATES_DIR.iterdir():
                if p.suffix.lower() == ".docx" and code.replace("-", "") in p.stem.replace("-", "").replace(" ", "").upper():
                    template_candidate = p
                    break
                if p.suffix.lower() == ".docx" and code.replace("-", "_") in p.stem.upper().replace("-", "_"):
                    template_candidate = p
                    break

        if template_candidate and template_candidate.exists():
            doc = Document(str(template_candidate))
            replace_placeholders(doc, {
                "RAGIONE SOCIALE": azienda.ragione_sociale or "",
                "[AZIENDA]": azienda.ragione_sociale or "",
            })
        else:
            doc = Document()

        # US-4.4 AC1: consultancy letterhead + client ragione sociale on
        # every form, regardless of whether the source template provided
        # its own placeholders.
        _add_branding_header(doc, azienda, self.branding)
        page_break(doc)
        add_heading(doc, f"{code} - {form.form_title}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Responsabile compilazione", ""),
            ("Periodo di riferimento", ""),
        ])
        add_heading(doc, "Registrazioni", level=2)
        righe = (form.data or {}).get("righe", [])
        if righe:
            headers = list(righe[0].keys()) if isinstance(righe[0], dict) else ["Riga"]
            rows = [[str(r.get(h, "")) for h in headers] if isinstance(r, dict) else [str(r)] for r in righe]
            add_data_table(doc, headers, rows)
        else:
            # Empty table with placeholder rows to compile
            add_data_table(doc, ["Data", "Responsabile", "Valore", "Note"], [["" , "", "", ""] for _ in range(15)])

        add_heading(doc, "Firma responsabile", level=2)
        add_paragraph(doc, "________________________")

        filename = f"{TIPO_DOC}_{code}_{slug}_v{version}.docx"
        filepath = os.path.join(output_dir, filename)
        doc.save(filepath)
        return filepath

    async def _next_version(self) -> int:
        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "HACCP_FORMS"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
