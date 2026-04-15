"""HACCP — 16 schede di autocontrollo (SA-01 .. SA-16) bundled into one zip.

Output: a single .docx per form, then all assembled into a .zip that is
returned as the "file" for this doc type. If zip creation is not possible,
returns the main index .docx.
"""

import io
import os
import zipfile
from pathlib import Path

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

TIPO_DOC = "haccp_forms"
HACCP_TEMPLATES_DIR = TEMPLATES_DIR / "haccp"


class HaccpFormsGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        config, forms = await load_haccp(self.db, self.azienda_id)

        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        version = await self._next_version()

        # Build individual forms
        form_paths: list[str] = []
        for form in forms:
            form_path = self._build_single_form(output_dir, slug, version, form, azienda)
            form_paths.append(form_path)

        # Build index document
        index_doc = Document()
        add_heading(index_doc, f"SCHEDE DI AUTOCONTROLLO HACCP - {azienda.ragione_sociale}", level=1)
        add_kv_table(index_doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Data emissione", generated_at.strftime("%d/%m/%Y")),
            ("Responsabile HACCP", (config.responsabile_haccp if config else "—") or "—"),
            ("Numero schede allegate", str(len(form_paths))),
        ])
        add_heading(index_doc, "Elenco schede", level=2)
        add_data_table(index_doc, ["Codice", "Titolo"], [[f.form_code, f.form_title] for f in forms] or [["—", "—"]])

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
