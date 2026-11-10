"""Allegato MMC - Movimentazione Manuale dei Carichi (NIOSH method).

Generates the MMC attachment from scratch (no template loading) to avoid
leaking the donor template's pre-populated client data. Mirrors the
template structure end-to-end:

  1. Cover page (logo, title, azienda, generation date + revision)
  2. Revision history
  3. TOC field
  4. Introduzione (NIOSH overview, static)
  5. Anagrafica Aziendale (current azienda)
  6. Dati Occupazionali — DVR Master Table 5 clone + MMC worker roster
     (Nome e Cognome | Sesso | Età | Mansione)
  7. Organizzazione Aziendale della Sicurezza (DdL/RSPP/RLS/MC)
  8. Metodologia NIOSH (CP, A, B, C, D, E, F factor reference tables)
  9. Per-worker assessment grid (all tasks grouped by worker)
 10. Quadro sinottico (one color-coded row per worker/task)
 11. Programma di Attuazione delle Misure (suggested measures per zone)
 12. Dichiarazione del Datore di Lavoro
 13. Signature block (DdL / RSPP / MC / RLS)
"""

from __future__ import annotations

import os
from datetime import datetime

from docx import Document
from docx.shared import Pt
from sqlalchemy import func, select

from app.data.niosh_factors import (
    FACTOR_A,
    FACTOR_B,
    FACTOR_C,
    FACTOR_D,
    FACTOR_E,
    FACTOR_F_TABLE,
    classify_ir,
    classify_lift,
    compute_plr,
)
from app.models.documento_generato import DocumentoGenerato
from app.services.codice_fiscale import extract_age, extract_sex
from app.services.document_generator.allegato_vdt import (
    ORGANIGRAMMA_HEADERS,
    organigramma_rows,
)
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_mmc
from app.services.document_generator.design import (
    add_back_cover,
    add_cover,
    add_revision_table,
    add_toc,
    finalize_toc,
    finish_document,
    setup_document,
)
from app.services.document_generator.dvr_master import _employee_persons
from app.services.document_generator.docx_utils import (
    BRAND_NAVY,
    BRAND_SURFACE_HEX,
    NOTE_GREY,
    TYPE_SCALE,
    add_body_paragraph,
    add_data_table,
    add_heading,
    add_kv_table,
    add_signature_grid,
    format_comune,
    level_cell,
    page_break,
    set_run_font,
    shade_cell,
    slugify,
)


TIPO_DOC = "allegato_mmc"
DOC_TITLE = "Allegato Rischio MMC"

# Each NIOSH area printed in its level colour (``level_cell``).
_AREA_LEVEL = {
    "Verde": "VERDE",
    "Gialla": "GIALLO",
    "Rossa": "ROSSO",
}

_ZONE_HEADINGS = {
    "Verde": "Area Verde - Rischio trascurabile (IR <= 0,75)",
    "Gialla": "Area Gialla - Sorveglianza sanitaria (0,75 < IR <= 1,00)",
    "Rossa": "Area Rossa - Riprogettazione e intervento (IR > 1,00)",
}

# Space (pt) above the notice an empty zone prints under its long heading:
# without it LibreOffice crowds the note into the Heading 2 above. The kit
# has no spacing token for this.
EMPTY_ZONE_NOTICE_SPACE_BEFORE_PT = 6

_DEFAULT_MEASURES_BY_ZONE = {
    "Verde": (
        "Mantenere le condizioni operative attuali. Sorveglianza sanitaria "
        "ordinaria; rivalutazione periodica in occasione di modifiche del "
        "ciclo produttivo o introduzione di nuove attrezzature."
    ),
    "Gialla": (
        "Avviare sorveglianza sanitaria mirata (visita medica con focus "
        "rachide). Pianificare azioni di riduzione del rischio: ausili meccanici "
        "(carrelli, transpallet, sollevatori), riprogettazione delle altezze di "
        "presa/deposito, riduzione della frequenza, formazione specifica art. 169 "
        "D.Lgs. 81/08."
    ),
    "Rossa": (
        "Intervento immediato richiesto. Adottare ausili meccanici per la "
        "movimentazione, ridisegnare la postazione (altezza, distanza, angoli), "
        "ridurre frequenza e durata della movimentazione, rotazione delle mansioni. "
        "Sorveglianza sanitaria con periodicità ravvicinata. Verifica efficacia "
        "delle misure entro 6 mesi."
    ),
}


def _body(doc, text: str, *, bold: bool = False, italic: bool = False):
    """A justified body paragraph (the kit's body role), optionally bold or
    italic."""
    paragraph = add_body_paragraph(doc, text)
    if bold or italic:
        set_run_font(paragraph.runs[0], bold=bold or None, italic=italic or None)
    return paragraph


def _note(doc, text: str):
    """The kit's note: 10 pt italic grey."""
    paragraph = doc.add_paragraph()
    set_run_font(paragraph.add_run(text), size=TYPE_SCALE["note"], italic=True, color=NOTE_GREY)
    return paragraph


def _label_cell(cell) -> None:
    """A row label in the kit's light look: navy bold on the surface tint."""
    shade_cell(cell, BRAND_SURFACE_HEX)
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            set_run_font(run, bold=True, color=BRAND_NAVY)


def _task_order_key(task: object) -> tuple[bool, float, str]:
    created = getattr(task, "created_at", None)
    created_key = created.timestamp() if created is not None else float("inf")
    return (
        created is None,
        created_key,
        str(getattr(task, "id", "")),
    )


def _person_order_key(person: object) -> tuple[bool, int, float, str]:
    """Keep worker groups in stable persisted order."""
    order = getattr(person, "ordine", None)
    created = getattr(person, "created_at", None)
    created_key = created.timestamp() if created is not None else float("inf")
    return (
        order is None,
        order if order is not None else 0,
        created_key,
        str(getattr(person, "id", "")),
    )


def group_mmc_rows(mmc_rows: list, persone: list) -> list[tuple[object | None, list]]:
    """Return every MMC task once, grouped in stable persisted worker order."""
    person_by_id = {
        getattr(person, "id", None): person
        for person in persone
        if getattr(person, "id", None) is not None
    }
    tasks_by_person: dict[object, list] = {}
    unassociated: list = []
    for row in mmc_rows:
        person_id = getattr(row, "persona_id", None)
        if person_id is not None and person_id in person_by_id:
            tasks_by_person.setdefault(person_id, []).append(row)
        else:
            unassociated.append(row)

    groups = [
        (person, sorted(tasks_by_person[person.id], key=_task_order_key))
        for person in sorted(person_by_id.values(), key=_person_order_key)
        if person.id in tasks_by_person
    ]
    if unassociated:
        groups.append((None, sorted(unassociated, key=_task_order_key)))
    return groups


class AllegatoMmcGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        persone = data["persone"]
        ambienti = data["ambienti"]
        generated_at: datetime = data["generated_at"]
        mmc_rows = await load_mmc(self.db, self.azienda_id)
        mmc_groups = group_mmc_rows(mmc_rows, persone)
        version = await self._next_version()

        ambiente_by_id = {a.id: a for a in ambienti}
        persona_by_id = {p.id: p for p in persone}

        doc = Document()
        setup_document(doc, profile="attachment")

        # Cover, storico and indice come from the shared design module so this
        # attachment is furnished like every other one (audit 2026-09-03: the
        # cover logo was the white sidebar mark — invisible on paper — and the
        # first issue printed "Revisione 01" while the DVR said "00"). The
        # cover and back cover are the kit's art pages (spec 2026-11-10 §4.4).
        add_cover(
            doc,
            title=DOC_TITLE,
            subtitle="Movimentazione Manuale dei Carichi — Azioni di Sollevamento",
            legal_basis="ai sensi del Titolo VI D.Lgs. 81/2008 e UNI EN ISO 11228-1 (NIOSH)",
            azienda=azienda,
            branding=self.branding,
            version=version,
            generated_at=generated_at,
        )
        add_revision_table(doc, version, generated_at)
        toc_anchors = add_toc(doc)
        self._add_introduzione(doc)
        self._add_anagrafica(doc, azienda)
        assessed_persone = [
            persona for persona, _tasks in mmc_groups if persona is not None
        ]
        self._add_dati_occupazionali(doc, persone, assessed_persone)
        self._add_organizzazione(doc, persone)
        self._add_metodologia(doc)
        self._add_per_worker_assessments(doc, mmc_groups, ambiente_by_id)
        self._add_quadro_sinottico(doc, mmc_groups)
        self._add_programma_attuazione(doc, mmc_rows, persona_by_id)
        self._add_dichiarazione_ddl(doc, azienda, persone)
        self._add_signature_block(doc, persone)

        finalize_toc(doc, *toc_anchors)
        add_back_cover(doc)
        finish_document(
            doc,
            title=DOC_TITLE,
            azienda=azienda,
            branding=self.branding,
            version=version,
            generated_at=generated_at,
        )

        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        filepath = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.docx")
        doc.save(filepath)
        return filepath

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    async def _next_version(self) -> int:
        return await self.resolve_version([TIPO_DOC, "ALLEGATO_MMC"])

    # ------------------------------------------------------------------
    # Introduzione (static narrative on NIOSH method)
    # ------------------------------------------------------------------

    def _add_introduzione(self, doc) -> None:
        add_heading(doc, "Introduzione", level=1)
        for txt in [
            "Le affezioni cronico-degenerative della colonna vertebrale rappresentano "
            "una delle principali cause di assenza per malattia nei lavoratori adulti. "
            "Il National Institute of Occupational Safety and Health (NIOSH - USA) "
            "pone tali patologie al secondo posto nella lista delle malattie "
            "professionali correlate al lavoro.",
            "Il Titolo VI del D.Lgs. 81/2008 (artt. 167-171 e Allegato XXXIII) impone "
            "al datore di lavoro la valutazione del rischio da movimentazione manuale "
            "dei carichi. Lo standard tecnico di riferimento per le azioni di "
            "sollevamento e' la norma UNI EN ISO 11228-1, che recepisce il modello "
            "NIOSH (revisione 1993).",
            "La presente valutazione applica la formula NIOSH per stimare, per ciascun "
            "compito di sollevamento svolto in azienda, il Peso Limite Raccomandato "
            "(PLR) e l'Indice di Rischio (IR), classificando ogni mansione nelle aree "
            "Verde (rischio trascurabile, IR <= 0,75), Gialla (sorveglianza, "
            "0,75 < IR <= 1,00) o Rossa (riprogettazione, IR > 1,00).",
        ]:
            _body(doc, txt)
        page_break(doc)

    # ------------------------------------------------------------------
    # Anagrafica Aziendale
    # ------------------------------------------------------------------

    def _add_anagrafica(self, doc, azienda) -> None:
        add_heading(doc, "Anagrafica Aziendale", level=1)
        rows: list[tuple[str, str]] = [
            ("Azienda", azienda.ragione_sociale or "—"),
            ("Attività / Codice ATECO", getattr(azienda, "codice_ateco", "") or "—"),
            ("Partita IVA", getattr(azienda, "partita_iva", "") or "—"),
            ("Codice Fiscale", getattr(azienda, "codice_fiscale", "") or "—"),
            ("Sede Legale - Via", azienda.sede_legale_via or "—"),
            ("Sede Legale - Città", format_comune(
                getattr(azienda, "cap_legale", None),
                azienda.sede_legale_citta,
                getattr(azienda, "provincia_legale", None))),
            ("Sede Operativa - Via", getattr(azienda, "sede_operativa_via", "") or "—"),
            ("Sede Operativa - Città", format_comune(
                getattr(azienda, "cap_operativa", None),
                getattr(azienda, "sede_operativa_citta", None),
                getattr(azienda, "provincia_operativa", None))),
            ("Telefono", getattr(azienda, "telefono", "") or "—"),
            ("Email PEC", getattr(azienda, "email_pec", "") or "—"),
        ]
        add_kv_table(doc, rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Dati Occupazionali
    # ------------------------------------------------------------------

    def _add_dati_occupazionali(
        self, doc, persone: list, assessed_persone: list | None = None
    ) -> None:
        """Client request (2026-08-13): the section must always carry the
        dati occupazionali table rendered exactly like the DVR Master's
        (Table 5, codice fiscale included), plus a second roster limited to
        Nome e Cognome | Sesso | Età | Mansione for the workers covered by
        the MMC assessment.
        """
        add_heading(doc, "Dati Occupazionali", level=1)
        employees = _employee_persons(persone)

        # Table 1 — the DVR Master's Table 5 over the same employees
        # (external safety consultants excluded), in the kit's table look:
        # the same rows as VDT's organigramma, a dash row when the roster is
        # empty ("sempre la tabella"). It no longer delegates to the DVR
        # renderer: the DVR now follows N2O's model of 2026-10-20, which
        # splits that table in two, and the attachments keep their
        # structure until N2O sends a model for each (spec 2026-11-10 §4.4).
        add_data_table(doc, ORGANIGRAMMA_HEADERS, organigramma_rows(employees))
        doc.add_paragraph("")

        # Table 2 — MMC-specific worker roster. Prefer the workers actually
        # associated to an MMC assessment; fall back to the full employee
        # roster when no assessment is linked to a person yet, so the table
        # always exists.
        add_heading(doc, "Lavoratori oggetto della valutazione MMC", level=2)
        roster = assessed_persone if assessed_persone else employees
        if not roster:
            _note(doc, "Nessun lavoratore registrato per questa azienda.")
            page_break(doc)
            return

        headers = ["Nome e Cognome", "Sesso", "Età", "Mansione"]
        rows = [
            [
                person.nominativo or "—",
                self._sesso_display(person),
                self._eta_display(person),
                person.mansione or "—",
            ]
            for person in roster
        ]
        add_data_table(doc, headers, rows)
        page_break(doc)

    @staticmethod
    def _sesso_display(person) -> str:
        """Stored sesso, else derived from the codice fiscale, else dash."""
        return (
            getattr(person, "sesso", None)
            or extract_sex(getattr(person, "codice_fiscale", None))
            or "—"
        )

    @staticmethod
    def _eta_display(person) -> str:
        """Age in completed years from the codice fiscale when parseable;
        otherwise the declared fascia_eta band (the only explicit age data
        the survey collects), otherwise a dash.
        """
        age = extract_age(getattr(person, "codice_fiscale", None))
        if age is not None:
            return str(age)
        return getattr(person, "fascia_eta", None) or "—"

    # ------------------------------------------------------------------
    # Organizzazione Aziendale Sicurezza
    # ------------------------------------------------------------------

    def _add_organizzazione(self, doc, persone: list) -> None:
        add_heading(doc, "Organizzazione Aziendale della Sicurezza", level=1)

        def _names(predicate) -> str:
            matched = [p.nominativo for p in persone if predicate(p) and p.nominativo]
            return ", ".join(matched) if matched else "—"

        rows = [
            ("Datore di Lavoro", _names(lambda p: bool(p.ruolo_datore_lavoro))),
            ("RSPP", _names(lambda p: bool(p.ruolo_rspp))),
            ("RLS", _names(lambda p: bool(p.ruolo_rls))),
            ("Medico Competente", _names(lambda p: bool(p.ruolo_medico_competente))),
            ("Addetti Primo Soccorso", _names(lambda p: bool(p.ruolo_primo_soccorso))),
            ("Addetti Antincendio", _names(lambda p: bool(p.ruolo_antincendio))),
            ("Preposti", _names(lambda p: bool(p.ruolo_preposto))),
        ]
        add_kv_table(doc, rows)
        page_break(doc)

    # ------------------------------------------------------------------
    # Metodologia NIOSH (CP, A, B, C, D, E, F reference tables)
    # ------------------------------------------------------------------

    def _add_metodologia(self, doc) -> None:
        add_heading(doc, "Metodologia - Il metodo NIOSH per azioni di sollevamento", level=1)
        _body(
            doc,
            "Per ogni compito di sollevamento si calcola il Peso Limite Raccomandato (PLR) "
            "moltiplicando la costante di peso CP (kg) per i sei fattori demoltiplicativi "
            "A, B, C, D, E, F. L'Indice di Rischio IR si ottiene come rapporto tra il peso "
            "effettivamente sollevato P e il PLR.",
        )
        _body(doc, "PLR = CP x A x B x C x D x E x F", bold=True)
        _body(doc, "IR = P / PLR", bold=True)
        _body(
            doc,
            "Soglie di accettabilità: IR <= 0,75 = VERDE (rischio trascurabile); "
            "0,75 < IR <= 1,00 = GIALLO (sorveglianza sanitaria); "
            "IR > 1,00 = ROSSO (riprogettazione del compito).",
            italic=True,
        )

        # CP table
        add_heading(doc, "CP - Costante di Peso (kg)", level=2)
        add_data_table(
            doc,
            ["Eta", "Maschi", "Femmine"],
            [
                ["> 18 anni", "25", "20"],
                ["15-18 anni", "20", "15"],
            ],
        )

        # Factor A
        add_heading(doc, "Fattore A - Altezza da terra delle mani all'inizio (cm)", level=2)
        _note(doc, "Formula: A = 1 - 0,003 * |V - 75|. Valore ottimale V = 75 cm (altezza nocche).")
        add_data_table(
            doc,
            ["Altezza V (cm)", "Fattore A"],
            [[str(int(x)), f"{y:.2f}"] for x, y in FACTOR_A],
        )

        # Factor B
        add_heading(doc, "Fattore B - Dislocazione verticale (cm)", level=2)
        add_data_table(
            doc,
            ["Dislocazione X (cm)", "Fattore B"],
            [[str(int(x)), f"{y:.2f}"] for x, y in FACTOR_B],
        )

        # Factor C
        add_heading(doc, "Fattore C - Distanza orizzontale (cm)", level=2)
        add_data_table(
            doc,
            ["Distanza H (cm)", "Fattore C"],
            [[str(int(x)), f"{y:.2f}"] for x, y in FACTOR_C],
        )

        # Factor D
        add_heading(doc, "Fattore D - Angolo di asimmetria (gradi)", level=2)
        add_data_table(
            doc,
            ["Angolo (gradi)", "Fattore D"],
            [[str(int(x)), f"{y:.2f}"] for x, y in FACTOR_D],
        )

        # Factor E
        add_heading(doc, "Fattore E - Giudizio sulla presa", level=2)
        add_data_table(
            doc,
            ["Giudizio", "Fattore E"],
            [[k, f"{v:.2f}"] for k, v in FACTOR_E.items()],
        )

        # Factor F
        add_heading(doc, "Fattore F - Frequenza dei gesti per durata del lavoro", level=2)
        f_rows = []
        for atti, breve, media, lunga in FACTOR_F_TABLE:
            label = f">{int(FACTOR_F_TABLE[-2][0])}" if atti >= 16 else (
                f"{atti:g}" if atti < 1 else str(int(atti))
            )
            f_rows.append([label, f"{breve:.2f}", f"{media:.2f}", f"{lunga:.2f}"])
        add_data_table(
            doc,
            [
                "Frequenza (atti/min)",
                "Breve durata (<1 ora)",
                "Media durata (1-2 ore)",
                "Lunga durata (>2 ore)",
            ],
            f_rows,
        )

        page_break(doc)

    # ------------------------------------------------------------------
    # Per-worker assessment grid (one 13x5 table per task, like template T14)
    # ------------------------------------------------------------------

    def _add_per_worker_assessments(
        self,
        doc,
        mmc_groups: list[tuple[object | None, list]],
        ambiente_by_id: dict,
    ) -> None:
        add_heading(doc, "Tavole di Valutazione del Rischio MMC", level=1)
        if not mmc_groups:
            _note(
                doc,
                "Nessuna attività di movimentazione manuale dei carichi e' stata "
                "valutata per questa azienda.",
            )
            page_break(doc)
            return

        task_index = 0
        for persona, tasks in mmc_groups:
            if persona is None:
                worker_heading = "Valutazioni non associate"
            else:
                worker_heading = (
                    f"{getattr(persona, 'nominativo', None) or '—'} — "
                    f"{getattr(persona, 'mansione', None) or '—'}"
                )
            add_heading(doc, worker_heading, level=2)
            for row in tasks:
                task_index += 1
                ambiente = (
                    ambiente_by_id.get(row.ambiente_id)
                    if getattr(row, "ambiente_id", None)
                    else None
                )
                self._render_assessment_table(
                    doc,
                    task_index,
                    row,
                    persona,
                    ambiente,
                )
                page_break(doc)

    def _render_assessment_table(self, doc, idx: int, r, persona, ambiente) -> None:
        nominativo = (persona.nominativo if persona else "—") or "—"
        mansione = (persona.mansione if persona else "—") or "—"

        add_heading(doc, f"{idx}. {r.compito or 'Compito'}", level=3)
        if ambiente:
            _note(doc, f"Ambiente: {ambiente.nome or '—'}")

        # Server-side recompute guard: if all 7 inputs are present, derive
        # multipliers + PLR + IR from the canonical lookup tables. This
        # protects against stored derivatives drifting out of sync with the
        # inputs (e.g. an old fixture that was never resaved through the API).
        # When inputs are absent we fall back to whatever the row has stored,
        # which is the legacy contract.
        recomputed = self._recompute_if_inputs_present(r)

        cp = float(recomputed.get("cp") if recomputed else r.cp or 25.0)
        peso = float(r.peso_kg or 0)
        plr = float(recomputed.get("plr") if recomputed else (r.plr or 0))
        ir = float(recomputed.get("ir") if recomputed else (r.indice_ir or 0))
        livello = (
            recomputed.get("livello") if recomputed
            else (r.livello_rischio or classify_ir(ir)).upper()
        )

        # Multipliers — recomputed values win over stored when both exist.
        mult_a = recomputed.get("fattore_a") if recomputed else r.fattore_a
        mult_b = recomputed.get("fattore_b") if recomputed else r.fattore_b
        mult_c = recomputed.get("fattore_c") if recomputed else r.fattore_c
        mult_d = recomputed.get("fattore_d") if recomputed else r.fattore_d
        mult_e = recomputed.get("fattore_e") if recomputed else r.fattore_e
        mult_f = recomputed.get("fattore_f") if recomputed else r.fattore_f

        sex_label = (
            "Maschi > 18 anni" if (r.sesso or "M") == "M" and (r.fascia_eta or "").startswith(">")
            else "Femmine > 18 anni" if (r.sesso or "M") == "F" and (r.fascia_eta or "").startswith(">")
            else "Maschi 15-18" if (r.sesso or "M") == "M"
            else "Femmine 15-18"
        )

        def _cell_str(val) -> str:
            if val is None:
                return "—"
            return str(val)

        def _factor_str(val) -> str:
            if val is None:
                return "—"
            try:
                return f"{float(val):.2f}"
            except (TypeError, ValueError):
                return "—"

        body_rows = [
            ("CP", "Costante di peso (kg)", sex_label, f"{cp:.0f}"),
            ("A", "Altezza da terra delle mani all'inizio del sollevamento (cm)",
             _cell_str(r.altezza_cm), _factor_str(mult_a)),
            ("B", "Dislocazione verticale del peso fra inizio e fine (cm)",
             _cell_str(r.dislocazione_cm), _factor_str(mult_b)),
            ("C", "Distanza orizzontale tra mani e mezzo delle caviglie (cm)",
             _cell_str(r.distanza_cm), _factor_str(mult_c)),
            ("D", "Angolo di asimmetria del peso (gradi)",
             _cell_str(r.angolo_gradi), _factor_str(mult_d)),
            ("E", "Giudizio sulla presa del carico",
             _cell_str(r.giudizio_presa), _factor_str(mult_e)),
            ("F", "Frequenza dei gesti (atti/min)",
             _cell_str(r.frequenza_atti_min), _factor_str(mult_f)),
            ("", "Durata del lavoro (minuti)",
             _cell_str(r.durata_min), ""),
            ("PLR", "Peso Limite Raccomandato",
             "", f"{plr:.2f} kg" if plr > 0 else "—"),
            ("P", "Peso effettivamente sollevato",
             "", f"{peso:.1f} kg"),
            ("IR = P/PLR", "Indice di rischio",
             "", f"{ir:.2f}" if plr > 0 else "—"),
        ]
        area = (
            "Verde" if livello == "VERDE"
            else "Gialla" if livello == "GIALLO"
            else "Rossa" if livello == "ROSSO"
            else "—"
        )

        # 13-row x 4-col kit table mirroring the template T14 layout, under
        # a header band with nominativo + mansione:
        #   col0 = Fattore (CP/A/B/C/D/E/F/PLR/P/IR), a light row label
        #   col1 = Descrizione
        #   col2 = Input (cm/gradi/giudizio/atti per minuto/durata)
        #   col3 = Valore (multiplier or final number)
        # The last row is the result, its zone in the level colour.
        table = add_data_table(
            doc,
            ["Nominativo", nominativo, "Mansione", mansione],
            [
                [code, descr, str(input_val), str(multiplier)]
                for code, descr, input_val, multiplier in body_rows
            ]
            + [["Risultato", "Classificazione", livello, area]],
        )
        for row in table.rows[1:]:
            _label_cell(row.cells[0])
        result_row = table.rows[-1].cells
        _label_cell(result_row[1])
        for cell in result_row[2:]:
            level_cell(cell, livello)

        if r.note:
            _note(doc, f"Note: {r.note}")

    # ------------------------------------------------------------------
    # Quadro sinottico
    # ------------------------------------------------------------------

    def _add_quadro_sinottico(
        self,
        doc,
        mmc_groups: list[tuple[object | None, list]],
    ) -> None:
        add_heading(doc, "Quadro sinottico di esposizione", level=1)
        if not mmc_groups:
            _note(doc, "Nessuna valutazione presente.")
            page_break(doc)
            return

        rows: list[list[str]] = []
        areas: list[str] = []
        for persona, tasks in mmc_groups:
            nominativo = (
                (getattr(persona, "nominativo", None) or "—")
                if persona is not None
                else "—"
            )
            mansione = (
                (getattr(persona, "mansione", None) or "—")
                if persona is not None
                else "—"
            )
            for task in tasks:
                recomputed = self._recompute_if_inputs_present(task)
                ir = (
                    float(recomputed["ir"])
                    if recomputed
                    else float(task.indice_ir or 0)
                )
                area = (
                    recomputed["area"]
                    if recomputed
                    else (
                        task.area_classificazione
                        or self._area_from_livello(task.livello_rischio)
                    )
                )

                rows.append(
                    [nominativo, mansione, task.compito or "—", f"{ir:.2f}", area or "—"]
                )
                areas.append(area or "")

        table = add_data_table(doc, ["Nominativo", "Mansione", "Compito", "IR", "Area"], rows)
        # IR and area in the area's level colour.
        for row, area in zip(table.rows[1:], areas):
            for cell in row.cells[3:]:
                level_cell(cell, _AREA_LEVEL.get(area, ""))

        page_break(doc)

    @staticmethod
    def _recompute_if_inputs_present(r) -> dict | None:
        """Return derived multipliers + PLR + IR + livello when all 7 NIOSH
        inputs are present on the row; otherwise None.

        Used as a generation-time guard so the document never displays stored
        PLR/IR values that have drifted out of sync with the inputs (e.g. when
        a fixture was hand-edited or the row predates a factor-table fix).
        """
        inputs = (
            r.altezza_cm,
            r.dislocazione_cm,
            r.distanza_cm,
            r.angolo_gradi,
            r.giudizio_presa,
            r.frequenza_atti_min,
            r.durata_min,
        )
        if any(v is None for v in inputs):
            return None
        cp = float(r.cp or 25.0)
        out = compute_plr(
            cp=cp,
            altezza_cm=float(r.altezza_cm),
            dislocazione_cm=float(r.dislocazione_cm),
            distanza_cm=float(r.distanza_cm),
            angolo_gradi=float(r.angolo_gradi),
            giudizio_presa=str(r.giudizio_presa),
            frequenza_atti_min=float(r.frequenza_atti_min),
            durata_min=float(r.durata_min),
        )
        peso = float(r.peso_kg or 0)
        plr = float(out["plr"])
        ir, livello = classify_lift(peso, plr)
        return {
            "cp": cp,
            "fattore_a": out["fattore_a"],
            "fattore_b": out["fattore_b"],
            "fattore_c": out["fattore_c"],
            "fattore_d": out["fattore_d"],
            "fattore_e": out["fattore_e"],
            "fattore_f": out["fattore_f"],
            "plr": plr,
            "ir": round(ir, 4),
            "livello": livello,
            "area": {"VERDE": "Verde", "GIALLO": "Gialla", "ROSSO": "Rossa"}[livello],
        }

    @staticmethod
    def _area_from_livello(livello: str | None) -> str:
        if not livello:
            return "—"
        u = livello.upper()
        if u == "VERDE":
            return "Verde"
        if u == "GIALLO":
            return "Gialla"
        if u == "ROSSO":
            return "Rossa"
        return "—"

    # ------------------------------------------------------------------
    # Programma di Attuazione delle Misure
    # ------------------------------------------------------------------

    def _add_programma_attuazione(
        self, doc, mmc_rows: list, persona_by_id: dict
    ) -> None:
        add_heading(doc, "Programma di Attuazione delle Misure di Prevenzione", level=1)
        if not mmc_rows:
            _note(doc, "Nessuna valutazione presente.")
            page_break(doc)
            return

        zones: dict[str, list] = {"Verde": [], "Gialla": [], "Rossa": []}
        for r in mmc_rows:
            recomp = self._recompute_if_inputs_present(r)
            area = (
                recomp["area"] if recomp
                else (r.area_classificazione or self._area_from_livello(r.livello_rischio))
            )
            if area in zones:
                zones[area].append(r)

        for zone, rows in zones.items():
            add_heading(doc, _ZONE_HEADINGS.get(zone, zone), level=2)
            if not rows:
                notice = _note(doc, f"Nessun lavoratore classificato in {zone.lower()}.")
                notice.paragraph_format.space_before = Pt(EMPTY_ZONE_NOTICE_SPACE_BEFORE_PT)
                continue

            # Table: lavoratore | AZIONE | misure — one row per employee
            # (client request 2026-08-13): every lifting action of the same
            # worker is aggregated in a single AZIONE cell (one per line),
            # and the proposed measures are deduplicated the same way.
            # Rows with no associated worker keep one row per assessment so
            # unrelated anonymous evaluations are never merged together.
            grouped: dict[object, dict] = {}
            for r in rows:
                persona = persona_by_id.get(r.persona_id) if r.persona_id else None
                key = (
                    persona.id
                    if persona is not None
                    else ("__unassigned__", getattr(r, "id", id(r)))
                )
                entry = grouped.setdefault(
                    key, {"persona": persona, "azioni": [], "misure": []}
                )
                entry["azioni"].append(r.compito or "—")
                misura = r.misure_proposte or _DEFAULT_MEASURES_BY_ZONE.get(zone, "")
                if misura and misura not in entry["misure"]:
                    entry["misure"].append(misura)

            data_rows = []
            for entry in grouped.values():
                persona = entry["persona"]
                nome = (persona.nominativo if persona else "—") or "—"
                data_rows.append(
                    [
                        nome,
                        "\n".join(entry["azioni"]),
                        "\n".join(entry["misure"]),
                    ]
                )

            tbl = add_data_table(
                doc,
                ["Lavoratore", "AZIONE", "Misure di prevenzione e protezione"],
                data_rows,
            )
            # Every row opens on the zone's level colour, so the zone stays
            # obvious when the table spans a page break (audit P3 #15); the
            # measures stay dark text on the kit's zebra rows.
            for row in tbl.rows[1:]:
                level_cell(row.cells[0], _AREA_LEVEL[zone])

        page_break(doc)

    # ------------------------------------------------------------------
    # Dichiarazione del Datore di Lavoro
    # ------------------------------------------------------------------

    def _add_dichiarazione_ddl(self, doc, azienda, persone) -> None:
        add_heading(doc, "Dichiarazione del Datore di Lavoro", level=1)
        ddl_names = [p.nominativo for p in persone if p.ruolo_datore_lavoro and p.nominativo]
        ddl = ddl_names[0] if ddl_names else "il Datore di Lavoro"
        ragione = azienda.ragione_sociale or "l'Azienda"
        _body(
            doc,
            f"Il sottoscritto {ddl}, in qualita di Datore di Lavoro di {ragione}, "
            "dichiara di aver effettuato la valutazione del rischio da movimentazione "
            "manuale dei carichi ai sensi del Titolo VI del D.Lgs. 81/2008 e della "
            "norma UNI EN ISO 11228-1 (metodo NIOSH), in collaborazione con il "
            "Responsabile del Servizio di Prevenzione e Protezione, il Medico "
            "Competente ove nominato e previa consultazione del Rappresentante dei "
            "Lavoratori per la Sicurezza.",
        )
        _body(
            doc,
            "Le misure di prevenzione e protezione individuate nel Programma di "
            "Attuazione saranno adottate secondo il cronoprogramma concordato e "
            "verificate periodicamente. La presente valutazione sarà aggiornata in "
            "occasione di modifiche significative del processo lavorativo, "
            "dell'organizzazione del lavoro o di insorgenza di patologie correlate.",
        )
        page_break(doc)

    # ------------------------------------------------------------------
    # Signature block
    # ------------------------------------------------------------------

    def _add_signature_block(self, doc, persone) -> None:
        add_heading(doc, "Firme", level=1)

        def _first_or_dash(predicate) -> str:
            for p in persone:
                if predicate(p) and p.nominativo:
                    return p.nominativo
            return "—"

        # The kit's signature grid: roles on navy, names ("—" when vacant)
        # and a blank row to sign in, two signatories per row.
        add_signature_grid(
            doc,
            [
                ("Il Datore di Lavoro", _first_or_dash(lambda p: bool(p.ruolo_datore_lavoro))),
                ("Il Responsabile del S.P.P.", _first_or_dash(lambda p: bool(p.ruolo_rspp))),
                ("Il Medico Competente", _first_or_dash(lambda p: bool(p.ruolo_medico_competente))),
                (
                    "Il Rappresentante dei Lavoratori (per consultazione)",
                    _first_or_dash(lambda p: bool(p.ruolo_rls)),
                ),
            ],
        )
