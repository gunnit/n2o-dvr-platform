"""Allegato Rischio Incendio - D.M. 03/09/2021."""

import os

from docx import Document
from sqlalchemy import func, select

from app.data.fire_measures import get_measures_for_level
from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_incendio
from app.services.document_generator.design import finish_document
from app.services.document_generator.docx_utils import (
    TEMPLATES_DIR,
    add_data_table,
    add_heading,
    add_kv_table,
    add_paragraph,
    fill_paragraph_blanks,
    format_comune,
    page_break,
    prune_toc_entries,
    remove_between,
    remove_blank_label_forms,
    replace_paragraph_text,
    scrub_body,
    slugify,
)
from app.services.document_generator.donor_front_matter import fill_front_matter
from app.services.document_generator.schede_ambienti import add_schede_ambienti

TEMPLATE = TEMPLATES_DIR / "ALLEGATO RISCHIO INCENDIO.docx"
TIPO_DOC = "allegato_incendio"

# The donor chapters between these two headings are the assessment itself:
# six blank per-ambiente sheets, the aree-omogenee matrix pre-filled with the
# form's default answers, and six blank measure sheets. All three are emitted
# below from the live valutazione, so the blank originals are dropped rather
# than printed alongside (audit 2026-09-11).
SUPERSEDED_CHAPTERS = (
    "Caratteristiche degli ambienti di lavoro",
    "Valutazione del Rischio Incendio per Aree Omogenee",
    "Misure Preventive, Protettive e Precauzionali di esercizio",
)
DONOR_ASSESSMENT_END = "Dichiarazione"

# Six prevention areas per REFERENCE_DATA.md §4.5. Each area has tiered
# measures keyed by the area's livello_rischio so an inspector sees a
# concrete plan, not generic boilerplate.
PREVENTION_CATEGORIES: list[tuple[str, str]] = [
    ("1. Ridurre la probabilità di insorgenza di un incendio",
     "Controllo periodico degli impianti elettrici, separazione materiali infiammabili, divieti di fumo, manutenzione apparecchiature."),
    ("2. Garantire l'esodo delle persone in sicurezza",
     "Vie di fuga sgombre e segnalate, porte tagliafuoco verificate, illuminazione di emergenza, punto di raccolta esterno."),
    ("3. Sistemi di allarme e segnalazione rapida",
     "Rilevatori di fumo/calore, pulsanti manuali di allarme, sirena acustica/luminosa, procedura di chiamata 115."),
    ("4. Estinzione dell'incendio",
     "Estintori (verifica semestrale), idranti UNI 45/70 dove richiesti, attrezzature di primo intervento, addetti formati."),
    ("5. Efficienza dei sistemi di protezione antincendio",
     "Manutenzione periodica registro antincendio, verifiche annuali estintori/idranti/rivelatori, controllo porte REI."),
    ("6. Informazione e formazione dei lavoratori",
     "Corso antincendio (livello 1/2/3) D.M. 02/09/2021 e aggiornamento almeno quinquennale."),
]

def prescrizioni_per_area(misure_prevenzione: str | None, livello_rischio: str | None) -> list[str]:
    """The livello-specific prescriptions to print for one area.

    They are the same list the operator reviewed on screen: the checklist in
    the UI is served by ``/calculate/fire-measures`` from
    ``app/data/fire_measures.py``. ``None`` means the checklist was left at
    its default (every measure of the band ticked), so the canonical list is
    printed; a saved selection — including an explicitly empty one — is
    printed verbatim. Before this the generator carried a private list, so
    unticking a measure in the UI never changed the document (UI/UX audit
    2026-09-07, F5).
    """
    if misure_prevenzione is None:
        band = (livello_rischio or "BASSO").capitalize()
        try:
            return get_measures_for_level(band)  # type: ignore[arg-type]
        except ValueError:
            return get_measures_for_level("Basso")
    return [line.strip() for line in misure_prevenzione.splitlines() if line.strip()]


class AllegatoIncendioGenerator(BaseDocumentGenerator):
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        generated_at = data["generated_at"]
        incendi = await load_incendio(self.db, self.azienda_id)
        ambienti_map = {a.id: a for a in data["ambienti"]}

        if TEMPLATE.exists():
            doc = Document(str(TEMPLATE))
            # Template normativa corrections (body only; the header/footer is
            # the consultancy letterhead). The title page cited only the
            # emergency-management decree and the body referenced the repealed
            # D.M. 16.02.1982 activity list.
            scrub_body(doc, {
                "e D.M. 02.09.2021": "e D.M. 03/09/2021 e D.M. 02.09.2021",
                "D.M. 16.02.1982": "D.P.R. 151/2011",
            })
            # The template is N2O's blank master form. Write the survey into
            # its front matter, drop the chapters this generator re-emits,
            # and sign the declaration — otherwise the client opens 28 pages
            # of empty boxes before reaching the assessment.
            fill_front_matter(
                doc,
                azienda=azienda,
                persone=data["persone"],
                ambienti=data["ambienti"],
            )
            removed = remove_between(doc, SUPERSEDED_CHAPTERS[0], DONOR_ASSESSMENT_END)
            if removed:
                prune_toc_entries(doc, SUPERSEDED_CHAPTERS)
                # The Criteri chapter points the reader at a table that lived
                # in the chapters just removed.
                replace_paragraph_text(
                    doc,
                    "individuazione aree omogenee",
                    "Le aree omogenee così individuate sono riportate nella "
                    "valutazione specifica in coda al presente documento.",
                )
            self._sign_declaration(doc, azienda, data["persone"], generated_at)
        else:
            doc = Document()

        page_break(doc)
        add_heading(doc, f"VALUTAZIONE SPECIFICA - {azienda.ragione_sociale}", level=1)
        add_kv_table(doc, [
            ("Azienda", azienda.ragione_sociale or ""),
            ("Data valutazione", generated_at.strftime("%d/%m/%Y")),
            ("Riferimento normativo", "D.M. 03/09/2021 (criteri di valutazione del rischio incendio) e D.M. 02/09/2021 (gestione emergenze e formazione); attività soggette ex D.P.R. 151/2011"),
        ])

        add_heading(doc, "Metodologia di valutazione", level=2)
        add_paragraph(doc, "Il rischio incendio e valutato combinando tre indicatori, ciascuno in scala 1-3:")
        add_data_table(doc, ["Codice", "Indicatore", "Scala 1-3"], [
            ["INF", "Infiammabilità e carico d'incendio", "1=basso; 2=medio; 3=alto"],
            ["SI",  "Sorgenti di ignizione presenti", "1=assenti/rare; 2=discrete; 3=numerose"],
            ["PI",  "Propagazione dell'incendio", "1=bassa; 2=media; 3=elevata"],
        ])
        add_paragraph(doc, "Classificazione del rischio = INF + SI + PI: 3-4 = BASSO, 5-7 = MEDIO, 8-9 = ALTO.")

        add_heading(doc, "Valutazione per ambiente", level=2)
        if not incendi:
            add_paragraph(doc, "Nessuna valutazione del rischio incendio disponibile.", italic=True)
        else:
            headers = ["Ambiente", "INF", "SI", "PI", "Totale", "Livello", "Uscite", "Estintori", "Idranti"]
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
                    str(v.idranti_presenti),
                ])
            add_data_table(doc, headers, rows)

        # Segnalazione 2026-08-25: per-ambiente scheda (descrizione con
        # metratura e materiali, persone max, sorgenti di innesco). Same
        # table as the PEE, from the same ambiente fields.
        add_schede_ambienti(
            doc, data["ambienti"], heading="Schede degli ambienti", level=2
        )

        # Company-wide aggregate (worst-case across areas + counts).
        if incendi:
            livelli = [v.livello_rischio or "" for v in incendi]
            counts = {
                "BASSO": livelli.count("BASSO"),
                "MEDIO": livelli.count("MEDIO"),
                "ALTO": livelli.count("ALTO"),
            }
            order = {"BASSO": 0, "MEDIO": 1, "ALTO": 2}
            worst = max((l for l in livelli if l in order), key=order.get, default="—")

            add_heading(doc, "Esito complessivo aziendale", level=2)
            add_kv_table(doc, [
                ("Ambienti valutati", str(len(incendi))),
                ("Aree a rischio BASSO", str(counts["BASSO"])),
                ("Aree a rischio MEDIO", str(counts["MEDIO"])),
                ("Aree a rischio ALTO", str(counts["ALTO"])),
                ("Livello aziendale (worst-case)", worst),
            ])

        add_heading(doc, "Misure di prevenzione e protezione per area", level=2)
        add_paragraph(
            doc,
            "Per ciascuna area di lavoro le misure sono organizzate nelle 6 categorie "
            "di prevenzione previste dal D.M. 03/09/2021 (REFERENCE_DATA §4.5). "
            "Alle misure standard si aggiungono prescrizioni specifiche calibrate "
            "sul livello di rischio assegnato.",
            italic=True,
            size=9,
        )
        for v in incendi:
            amb_name = (
                ambienti_map[v.ambiente_id].nome
                if v.ambiente_id in ambienti_map
                else (v.nome_area or "—")
            )
            livello = (v.livello_rischio or "BASSO").upper()
            add_heading(doc, f"{amb_name} — livello {livello}", level=3)

            # 6-category prevention table
            cat_rows = [[cat, contenuto] for cat, contenuto in PREVENTION_CATEGORIES]
            add_data_table(doc, ["Categoria di prevenzione", "Misure"], cat_rows)

            # Livello-specific prescriptions — the operator's checklist.
            add_heading(doc, f"Prescrizioni aggiuntive — livello {livello}", level=4)
            prescrizioni = prescrizioni_per_area(v.misure_prevenzione, v.livello_rischio)
            for m in prescrizioni:
                add_paragraph(doc, f"• {m}")
            if not prescrizioni:
                add_paragraph(
                    doc,
                    "Nessuna prescrizione aggiuntiva registrata per quest'area.",
                    italic=True,
                )

        add_heading(doc, "Gestione dell'emergenza", level=2)
        add_paragraph(
            doc,
            "Il piano di emergenza (allegato PEE) descrive le procedure per gli scenari d'incendio.",
        )
        declared_workers = getattr(azienda, "numero_dipendenti_dichiarati", None)
        if declared_workers is not None and declared_workers >= 10:
            add_paragraph(
                doc,
                "Per il numero di lavoratori modellato, le esercitazioni antincendio sono effettuate "
                "con cadenza almeno annuale (D.M. 02/09/2021, Allegato I, punto 1.3).",
            )
        else:
            add_paragraph(
                doc,
                "La cadenza delle esercitazioni antincendio deve essere verificata in base all'applicabilità "
                "dei criteri del D.M. 02/09/2021 al luogo di lavoro.",
            )

        add_heading(doc, "Sottoscrizione", level=2)
        add_data_table(doc, ["Ruolo", "Nominativo", "Firma"], [
            ["Datore di Lavoro", azienda.ragione_sociale or "", "________________________"],
            ["RSPP", "________________________", "________________________"],
            ["Addetto antincendio coordinatore", "________________________", "________________________"],
            ["Data", generated_at.strftime("%d/%m/%Y"), ""],
        ])

        version = await self._next_version()
        output_dir = self._get_output_dir()
        slug = slugify(azienda.ragione_sociale or "azienda")
        filepath = os.path.join(output_dir, f"{TIPO_DOC}_{slug}_v{version}.docx")
        # Audit 2026-09-03: the donor template's header/footer carried the
        # legacy N2O letterhead and literal placeholders; rewrite them from
        # the organization's branding and set honest file properties.
        finish_document(
            doc,
            title='Valutazione del Rischio Incendio',
            azienda=azienda,
            branding=self.branding,
            version=version,
            generated_at=generated_at,
            fill_cover=True,
        )
        # After the cover is filled, so a cover awaiting its values is never
        # mistaken for an abandoned form: what is still blank here is a donor
        # sheet the platform has no data for.
        remove_blank_label_forms(doc)
        doc.save(filepath)
        return filepath

    @staticmethod
    def _sign_declaration(doc, azienda, persone, generated_at) -> None:
        """Fill the donor declaration's ruled blanks from the survey.

        "Il sottoscritto, ____ in qualità di Datore di Lavoro della ____ con
        sede legale in ____" and the place-and-date line under it. The
        signature boxes below stay ruled: those are for a pen.
        """
        ddl = next((p for p in persone or [] if getattr(p, "ruolo_datore_lavoro", False)), None)
        sede = ", ".join(
            x for x in (
                (azienda.sede_legale_via or "").strip(),
                format_comune(
                    getattr(azienda, "cap_legale", None),
                    azienda.sede_legale_citta,
                    getattr(azienda, "provincia_legale", None),
                ),
            ) if x and x != "—"
        )
        fill_paragraph_blanks(doc, "Il sottoscritto", [
            (ddl.nominativo if ddl else "") or "",
            azienda.ragione_sociale or "",
            sede,
        ])
        comune = format_comune(
            None, azienda.sede_legale_citta, getattr(azienda, "provincia_legale", None)
        )
        replace_paragraph_text(
            doc,
            "), lì",
            f"{comune if comune != '—' else ''}, lì {generated_at.strftime('%d/%m/%Y')}".lstrip(", "),
        )

    async def _next_version(self) -> int:
        return await self.resolve_version([TIPO_DOC, "ALLEGATO_INCENDIO"])
