"""Allegato Microclima Moderato - UNI EN ISO 7730 (PMV/PPD)."""

import os

from docx import Document
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_microclima
from app.services.document_generator.docx_utils import (
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    format_sede,
    page_break,
    slugify,
)

TIPO_DOC = "allegato_microclima"


def _compute_pmv_ppd(t_air, t_rad, v_air, rh, met, clo) -> tuple[float | None, float | None]:
    """Try pythermalcomfort; fall back to a simple heuristic if missing."""
    try:
        from pythermalcomfort.models import pmv_ppd
        result = pmv_ppd(
            tdb=float(t_air), tr=float(t_rad), vr=float(v_air), rh=float(rh),
            met=float(met), clo=float(clo), standard="ISO",
        )
        # pythermalcomfort returns dict or object with pmv/ppd keys
        if isinstance(result, dict):
            return float(result.get("pmv", 0)), float(result.get("ppd", 0))
        return float(getattr(result, "pmv", 0)), float(getattr(result, "ppd", 0))
    except Exception:
        # Simplified fallback: linear distance from 22 C optimal
        pmv = (float(t_air) - 22.0) * 0.25
        ppd = min(95.0, max(5.0, 5.0 + abs(pmv) * 25.0))
        return pmv, ppd


def _comfort_category(ppd: float | None) -> str:
    if ppd is None:
        return "—"
    if ppd < 6:
        return "Categoria A (eccellente)"
    if ppd < 10:
        return "Categoria B (buona)"
    if ppd < 15:
        return "Categoria C (accettabile)"
    return "Fuori categoria - azioni correttive"


class AllegatoMicroclimaGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        micro = await load_microclima(self.db, self.azienda_id)
        ambienti_map = {a.id: a for a in data["ambienti"]}

        # Filter moderato (the severo-caldo variant is handled separately)
        moderate_rows = [m for m in micro if (m.tipo_ambiente or "moderato") == "moderato"]

        doc = Document()
        add_heading(doc, "ALLEGATO RISCHIO MICROCLIMA - AMBIENTI MODERATI", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Sede", format_sede(azienda, "legale")),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimento normativo", "UNI EN ISO 7730:2006 - Ergonomia ambienti termici moderati"),
        ])

        add_heading(doc, "Metodologia", level=2)
        add_paragraph(doc, "La norma UNI EN ISO 7730 definisce il comfort termico mediante gli indici PMV (Predicted Mean Vote, scala -3..+3) e PPD (Predicted Percentage of Dissatisfied). I parametri considerati sono: temperatura dell'aria (tdb), temperatura radiante media (tr), velocita dell'aria (var), umidita relativa (RH), metabolismo (met) e isolamento del vestiario (clo).")

        add_data_table(doc, ["Categoria", "PPD", "Giudizio"], [
            ["A", "< 6%", "Eccellente comfort"],
            ["B", "< 10%", "Comfort buono"],
            ["C", "< 15%", "Comfort accettabile"],
            ["—", ">= 15%", "Necessarie azioni correttive"],
        ])

        add_heading(doc, "Parametri per ambiente", level=2)
        if not moderate_rows:
            add_paragraph(doc, "Nessun ambiente valutato nella fascia moderata.", italic=True)
        else:
            rows = []
            for m in moderate_rows:
                amb_name = ambienti_map[m.ambiente_id].nome if m.ambiente_id in ambienti_map else "—"
                pmv, ppd = _compute_pmv_ppd(m.temperatura_aria, m.temperatura_radiante, m.velocita_aria, m.umidita_relativa, m.metabolismo, m.isolamento_vestiario)
                rows.append([
                    amb_name,
                    f"{float(m.temperatura_aria):.1f}",
                    f"{float(m.temperatura_radiante):.1f}",
                    f"{float(m.velocita_aria):.2f}",
                    f"{float(m.umidita_relativa):.0f}",
                    f"{float(m.metabolismo):.2f}",
                    f"{float(m.isolamento_vestiario):.2f}",
                    f"{pmv:.2f}" if pmv is not None else "—",
                    f"{ppd:.1f}%" if ppd is not None else "—",
                    _comfort_category(ppd),
                ])
            add_data_table(doc, ["Ambiente", "t_aria (C)", "t_rad (C)", "v_aria (m/s)", "RH %", "met", "clo", "PMV", "PPD", "Categoria"], rows)

        add_heading(doc, "Misure correttive suggerite", level=2)
        add_paragraph(doc, "Per ambienti con PPD >= 15%: adeguare il sistema di climatizzazione, rivedere l'isolamento del vestiario, introdurre schermature solari o umidificatori, verificare la velocita dell'aria nelle postazioni.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_MICROCLIMA"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
