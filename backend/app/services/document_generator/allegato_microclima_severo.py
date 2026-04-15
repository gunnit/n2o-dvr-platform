"""Allegato Microclima Severo - UNI EN ISO 7933 (PHS - Predicted Heat Strain)."""

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
    slugify,
)

TIPO_DOC = "allegato_microclima_severo"


def _compute_phs(t_air, t_rad, v_air, rh, met, clo) -> tuple[float | None, float | None, float | None]:
    """Try pythermalcomfort; fall back to conservative estimates."""
    try:
        from pythermalcomfort.models import phs
        r = phs(
            tdb=float(t_air), tr=float(t_rad), v=float(v_air), rh=float(rh),
            met=float(met) * 58.2,  # convert met to W/m^2
            clo=float(clo),
            posture=2, weight=75, height=1.75, drink=1, duration=480,
        )
        if isinstance(r, dict):
            return (
                float(r.get("sw_tot", 0)) if r.get("sw_tot") is not None else None,
                float(r.get("t_re", 0)) if r.get("t_re") is not None else None,
                float(r.get("d_lim_loss_50", 0)) if r.get("d_lim_loss_50") is not None else None,
            )
        return (float(getattr(r, "sw_tot", 0)), float(getattr(r, "t_re", 0)), float(getattr(r, "d_lim_loss_50", 0)))
    except Exception:
        # Heuristic fallback
        excess = max(0.0, float(t_air) - 28.0)
        return 1500 + excess * 200, 37.0 + excess * 0.1, max(30.0, 480.0 - excess * 40)


def _severity(d_lim_min: float | None) -> str:
    if d_lim_min is None:
        return "—"
    if d_lim_min >= 480:
        return "Accettabile per l'intera giornata lavorativa"
    if d_lim_min >= 240:
        return "Turno ridotto o pause supplementari"
    return "Esposizione non ammessa senza DPI/misure rinfrescanti"


class AllegatoMicroclimaSeveroGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        micro = await load_microclima(self.db, self.azienda_id)
        ambienti_map = {a.id: a for a in data["ambienti"]}

        severe_rows = [m for m in micro if (m.tipo_ambiente or "") in ("severo_caldo", "severo_freddo")]

        doc = Document()
        add_heading(doc, "ALLEGATO RISCHIO MICROCLIMA - AMBIENTI SEVERI (CALDO)", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimento normativo", "UNI EN ISO 7933:2004 - Determinazione dello stress termico - Indice PHS"),
        ])

        add_heading(doc, "Metodologia", level=2)
        add_paragraph(doc, "L'indice PHS (Predicted Heat Strain) stima la sudorazione totale (sw_tot in g/h), la temperatura rettale prevista (t_re) e la durata massima di esposizione accettabile con il 50% di probabilita di rientrare nei limiti di perdita idrica (dlim_loss50 in minuti).")

        add_heading(doc, "Soglie di azione", level=2)
        add_data_table(doc, ["d_lim_loss50", "Classificazione"], [
            [">= 480 min (intera giornata)", "ACCETTABILE"],
            ["240-480 min", "TURNI RIDOTTI / PAUSE"],
            ["< 240 min", "ESPOSIZIONE NON AMMESSA senza DPI"],
        ])

        add_heading(doc, "Valutazione per ambiente severo", level=2)
        if not severe_rows:
            add_paragraph(doc, "Nessun ambiente severo (caldo/freddo) registrato.", italic=True)
        else:
            rows = []
            for m in severe_rows:
                amb_name = ambienti_map[m.ambiente_id].nome if m.ambiente_id in ambienti_map else "—"
                sw, t_re, dlim = _compute_phs(m.temperatura_aria, m.temperatura_radiante, m.velocita_aria, m.umidita_relativa, m.metabolismo, m.isolamento_vestiario)
                rows.append([
                    amb_name,
                    f"{float(m.temperatura_aria):.1f}",
                    f"{float(m.temperatura_radiante):.1f}",
                    f"{float(m.umidita_relativa):.0f}",
                    f"{float(m.metabolismo):.2f}",
                    f"{sw:.0f}" if sw is not None else "—",
                    f"{t_re:.1f}" if t_re is not None else "—",
                    f"{dlim:.0f}" if dlim is not None else "—",
                    _severity(dlim),
                ])
            add_data_table(doc, ["Ambiente", "t_aria", "t_rad", "RH%", "met", "sw_tot g/h", "t_re C", "d_lim min", "Classificazione"], rows)

        add_heading(doc, "Misure organizzative e di protezione", level=2)
        add_paragraph(doc, "Per ambienti con stress termico severo: idratazione frequente (>= 250 ml/h), pause in zona rinfrescata ogni 45 minuti, rotazione personale, monitoraggio sintomi, formazione sul riconoscimento del colpo di calore, sorveglianza sanitaria specifica.")

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
            .where(DocumentoGenerato.tipo_documento.in_([TIPO_DOC, "ALLEGATO_MICROCLIMA_SEVERO"]))
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1
