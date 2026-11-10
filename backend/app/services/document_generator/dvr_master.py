"""
DVR Master document generator.

Generates the Documento di Valutazione dei Rischi (DVR) — the master risk
assessment document required by D.Lgs. 81/2008 for every Italian workplace.

The page sequence is N2O's model of 2026-10-20 (spec
docs/superpowers/specs/2026-11-10-document-layout-redesign-design.md §4.2.1),
built from the design kit (``design`` page types, ``docx_utils`` tables):

- the VERA cover, the index and the Premessa;
- in-page titles for the identity pages, Part I's company data and Part II's
  method, and divider pages (full-page art, title mid-page) for the 23
  topics N2O chose — Part III opens on one, every Part IV procedure too;
- per environment: its name as a title, then machines, photos, the risk
  checklist and one page per risk category;
- the 4-column improvement table, the GESTIONE procedures, the related
  documents, the employer's declaration with its signature grid, and the
  back cover.
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.table import (
    WD_CELL_VERTICAL_ALIGNMENT,
    WD_ROW_HEIGHT_RULE,
    WD_TABLE_ALIGNMENT,
)
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.image.image import Image as DocxImage
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt
from docx.table import Table

from app.data.regional_regulations import get_regulations_for_comune
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.design import (
    ART,
    add_art_cover,
    add_back_cover,
    add_divider,
    add_section_title,
    add_sub_title,
    add_toc,
    art_path,
    finalize_toc,
    finish_document,
    setup_document,
)
from app.services.document_generator.docx_utils import (
    BRAND_NAVY,
    BRAND_NAVY_HEX,
    BRAND_SURFACE_HEX,
    HEADER_TEXT,
    NOTE_GREY,
    TYPE_SCALE,
    add_body_paragraph,
    add_bullets,
    add_data_table,
    add_kv_table,
    add_role_band,
    add_signature_grid,
    insert_in_order,
    keep_row_together,
    level_cell,
    set_run_font,
    set_table_borders,
    shade_cell,
    style_header_row,
)
from app.services.protocollo_sanitario import PROTOCOLLO_SANITARIO_ATTIVO
from app.services.reference_data import (
    HAZARD_LIBRARY,
    RISK_CATEGORIES,
    normalize_categoria_to_long,
)
from app.services.risk_calculator import calculate_risk_index

logger = logging.getLogger(__name__)


def _photo_image_sources(photo: object) -> list[BytesIO | str]:
    sources: list[BytesIO | str] = []
    content = getattr(photo, "document_image_bytes", None)
    if content:
        sources.append(BytesIO(content))
    path = getattr(photo, "file_path", None)
    if path and os.path.isfile(path):
        sources.append(path)
    return sources


def _effective_risk_sources(parent: object) -> list:
    children = list(getattr(parent, "pericoli", None) or [])
    if children:
        return [
            child
            for child in children
            if getattr(child, "applicabile", False)
        ]
    return [parent] if getattr(parent, "applicabile", False) else []


# ---------------------------------------------------------------------------
# Special worker-category riferimenti (client feedback 2026-08-13).
#
# The gestanti/minori/stranieri catalog rows (OR-03/04/05) used to carry the
# markers below in ``valutazione_riferimento``, and the risk tables printed
# them verbatim in the I column. The client asked that "Vedi normativa ..."
# never appear: gestanti rows defer to the dedicated allegato when the
# azienda has one, otherwise the operator scores P/D like any other row.
# The risk UI migrates these markers on load; this mapping covers rows that
# were never re-opened in the form after the change.
# ---------------------------------------------------------------------------
_LEGACY_RIFERIMENTO_MARKERS = frozenset({
    "Vedi normativa specifica (D.Lgs. 151/2001)",   # OR-03 gestanti
    "Vedi normativa specifica (D.Lgs. 345/99)",     # OR-04 minori
    "Verifica linguistica/formativa a cura del preposto",  # OR-05 stranieri
})

# Must match GESTANTI_ALLEGATO_RIFERIMENTO in
# frontend/src/components/survey/pericoli-panel.tsx so rows the form saves
# and legacy rows normalized here read identically in the DVR.
GESTANTI_ALLEGATO_RIFERIMENTO = (
    "Come da documento allegato: Valutazione Rischio Gestanti"
)

_LEGACY_GESTANTI_MARKER = "Vedi normativa specifica (D.Lgs. 151/2001)"


def _normalize_special_riferimento(
    riferimento: str | None, *, gestanti_allegato_presente: bool
) -> str | None:
    """Map legacy special-category markers to their current wording.

    - gestanti marker → the allegato reference when the azienda has a
      Valutazione Rischio Gestanti, otherwise ``None`` (the row falls back
      to its P/D score, or "—" when unscored);
    - minori / stranieri markers → ``None`` (indice-only rows);
    - any other "Vedi normativa ..." text → ``None`` — the DVR never prints
      a normativa deferral in place of the risk index;
    - everything else (e.g. "Come da documenti allegati") passes through.
    """
    if not riferimento:
        return riferimento
    text = riferimento.strip()
    if text == _LEGACY_GESTANTI_MARKER:
        return (
            GESTANTI_ALLEGATO_RIFERIMENTO
            if gestanti_allegato_presente
            else None
        )
    if text in _LEGACY_RIFERIMENTO_MARKERS:
        return None
    if text.lower().startswith("vedi normativa"):
        return None
    return riferimento


_ATTREZZATURA_RISK_LABELS = {
    "lavori_in_quota": "Lavori in quota",
    "trabattelli": "Utilizzo di trabattelli",
    "ponteggi": "Utilizzo di ponteggi",
    "carrello_elevatore": "Utilizzo di carrelli elevatori",
    "ple": "Utilizzo di piattaforme di lavoro elevabili (PLE)",
    "gru": "Utilizzo di gru",
    "ruspa_escavatore": "Utilizzo di ruspe ed escavatori",
    "patente_cde": "Guida professionale (patente C/D/E)",
    "adr": "Trasporto merci pericolose (ADR)",
}


def _person_specific_risk_labels(person: object, vdt_ids: set) -> list[str]:
    from app.services.reference_data import RISCHI_SPECIFICI_CATALOG

    labels: list[str] = []

    def add(label: str) -> None:
        if label and label not in labels:
            labels.append(label)

    if getattr(person, "id", None) in vdt_ids:
        add("Videoterminali")
    for code in getattr(person, "attrezzature_speciali", None) or []:
        add(_ATTREZZATURA_RISK_LABELS.get(code, code))
    for code in getattr(person, "rischi_specifici_codes", None) or []:
        item = RISCHI_SPECIFICI_CATALOG.get(code, {})
        add(item.get("etichetta", code))
    return labels


def _center_dpi_brand_model_placeholders(table: Table) -> None:
    headers = [cell.text.strip() for cell in table.rows[0].cells]
    if "Marca / Modello" not in headers:
        return
    column = headers.index("Marca / Modello")
    for row in table.rows[1:]:
        cell = row.cells[column]
        if cell.text.strip() not in {"-", "—"}:
            continue
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------------------------------------------------------------------------
# Parte II — Definizioni (Template Table 19, MIXED). Core D.Lgs. 81/2008
# terms from art. 2 — kept compact so the emitted table mirrors the
# template's 27-row shape without exploding the .docx size.
# ---------------------------------------------------------------------------

_DEFINIZIONI_ROWS: list[tuple[str, str]] = [
    ("LAVORATORE (LAV)",
     "Persona che, indipendentemente dalla tipologia contrattuale, svolge "
     "un'attività lavorativa nell'ambito dell'organizzazione di un datore "
     "di lavoro pubblico o privato, con o senza retribuzione."),
    ("DATORE DI LAVORO (DL)",
     "Soggetto titolare del rapporto di lavoro con il lavoratore o, "
     "comunque, il soggetto che ha la responsabilità dell'organizzazione "
     "stessa o dell'unità produttiva."),
    ("AZIENDA",
     "Il complesso della struttura organizzata dal datore di lavoro "
     "pubblico o privato."),
    ("DIRIGENTE",
     "Persona che attua le direttive del datore di lavoro organizzando "
     "l'attività lavorativa e vigilando su di essa."),
    ("PREPOSTO",
     "Persona che, in ragione delle competenze professionali e nei limiti "
     "di poteri gerarchici e funzionali adeguati alla natura dell'incarico "
     "conferitogli, sovrintende alla attività lavorativa."),
    ("RSPP",
     "Responsabile del Servizio di Prevenzione e Protezione — persona "
     "designata dal datore di lavoro, in possesso di attitudini e "
     "capacità adeguate, a cui il datore di lavoro si avvale per "
     "organizzare il servizio di prevenzione e protezione."),
    ("ASPP",
     "Addetto del Servizio di Prevenzione e Protezione — persona in "
     "possesso di attitudini e capacità adeguate che supporta il RSPP "
     "nell'organizzazione del servizio."),
    ("RLS",
     "Rappresentante dei Lavoratori per la Sicurezza — persona eletta o "
     "designata per rappresentare i lavoratori per quanto concerne gli "
     "aspetti della salute e della sicurezza durante il lavoro."),
    ("MEDICO COMPETENTE (MC)",
     "Medico in possesso di uno dei titoli e requisiti formativi e "
     "professionali richiesti dalla normativa, che collabora con il "
     "datore di lavoro ai fini della valutazione dei rischi e della "
     "sorveglianza sanitaria."),
    ("VALUTAZIONE DEI RISCHI",
     "Valutazione globale e documentata di tutti i rischi per la salute "
     "e la sicurezza dei lavoratori presenti nell'ambito "
     "dell'organizzazione in cui essi prestano la propria attività."),
    ("PERICOLO",
     "Proprieta o qualità intrinseca di un determinato fattore avente "
     "il potenziale di causare danni."),
    ("RISCHIO",
     "Probabilità di raggiungimento del livello potenziale di danno "
     "nelle condizioni di impiego o di esposizione a un determinato "
     "fattore o agente oppure alla loro combinazione."),
    ("PROBABILITÀ (P)",
     "Frequenza con cui un evento dannoso può verificarsi, valutata "
     "su scala 1-4 (Bassa, Medio-Bassa, Medio-Alta, Elevata)."),
    ("DANNO (D)",
     "Entità del danno atteso per il lavoratore esposto, valutata su "
     "scala 1-4 (Trascurabile, Modesto, Notevole, Ingente)."),
    ("INDICE DI RISCHIO (I)",
     "Calcolato come I = 2*D + P; range 3-12; livelli ACCETTABILE, "
     "MODESTO, GRAVE, GRAVISSIMO."),
    ("UNITÀ PRODUTTIVA",
     "Stabilimento o struttura finalizzati alla produzione di beni "
     "o all'erogazione di servizi, dotati di autonomia finanziaria e "
     "tecnico-funzionale."),
    ("DPI",
     "Dispositivo di Protezione Individuale — qualsiasi attrezzatura "
     "destinata ad essere indossata e tenuta dal lavoratore allo scopo "
     "di proteggerlo contro uno o più rischi."),
    ("SORVEGLIANZA SANITARIA",
     "Insieme degli atti medici finalizzati alla tutela dello stato di "
     "salute e sicurezza dei lavoratori, in relazione all'ambiente di "
     "lavoro, ai fattori di rischio professionali e alle modalità di "
     "svolgimento dell'attività lavorativa."),
    ("FORMAZIONE",
     "Processo educativo attraverso il quale trasferire ai lavoratori "
     "conoscenze e procedure utili alla acquisizione di competenze "
     "per lo svolgimento in sicurezza dei rispettivi compiti."),
    ("INFORMAZIONE",
     "Complesso delle attività dirette a fornire conoscenze utili alla "
     "identificazione, alla riduzione e alla gestione dei rischi "
     "nell'ambiente di lavoro."),
    ("ADDESTRAMENTO",
     "Complesso delle attività dirette a fare apprendere ai lavoratori "
     "l'uso corretto di attrezzature, macchine, impianti, sostanze, "
     "dispositivi, anche di protezione individuale, e le procedure di lavoro."),
    ("AGENTE",
     "L'agente chimico, fisico o biologico presente durante il lavoro "
     "e potenzialmente dannoso per la salute."),
    ("NORMA TECNICA",
     "Specifica tecnica, approvata e pubblicata da un'organizzazione "
     "internazionale, da un organismo europeo o nazionale di "
     "normalizzazione, la cui osservanza non è obbligatoria."),
    ("BUONA PRASSI",
     "Soluzioni organizzative o procedurali coerenti con la normativa "
     "vigente e con le norme di buona tecnica, adottate volontariamente e "
     "finalizzate a promuovere la salute e sicurezza sui luoghi di lavoro."),
    ("LINEE GUIDA",
     "Atti di indirizzo e coordinamento per l'applicazione della "
     "normativa in materia di salute e sicurezza."),
    ("MODELLO DI ORGANIZZAZIONE E GESTIONE",
     "Modello organizzativo e gestionale per la definizione e "
     "attuazione di una politica aziendale per la salute e sicurezza."),
    ("RESPONSABILITÀ SOCIALE",
     "Integrazione volontaria delle preoccupazioni sociali ed "
     "ecologiche delle aziende nelle loro operazioni commerciali e nei "
     "loro rapporti con le parti interessate."),
]

# Parte II — P/D criteria lookup tables (Template Tables 21 and 22).
_PROBABILITA_CRITERI_ROWS = [
    ("4", "ELEVATA",
     "Esiste correlazione diretta tra mancanza rilevata e possibilità "
     "che l'evento dannoso si verifichi; si sono già verificati casi "
     "analoghi in azienda o in realta simili."),
    ("3", "MEDIO ALTA",
     "La mancanza rilevata può provocare un danno, anche se non "
     "direttamente, seppur in modo automatico; sono noti rari episodi "
     "in azienda o in realta simili."),
    ("2", "MEDIO BASSA",
     "La mancanza rilevata può provocare un danno in circostanze "
     "particolari; non sono noti episodi in azienda."),
    ("1", "BASSA",
     "La mancanza rilevata può provocare un danno solo in circostanze "
     "eccezionali e in concomitanza con più eventi sfavorevoli; non "
     "sono noti episodi nel settore."),
]

_DANNO_CRITERI_ROWS = [
    ("4", "INGENTE",
     "Infortunio o episodio di esposizione con effetti letali o "
     "invalidità totale permanente."),
    ("3", "NOTEVOLE",
     "Infortunio o episodio di esposizione acuta con effetti di "
     "invalidità parziale permanente; patologie gravi a effetti "
     "progressivi."),
    ("2", "MODESTO",
     "Infortunio o episodio di esposizione acuta con inabilità "
     "temporanea reversibile."),
    ("1", "TRASCURABILE",
     "Infortunio o episodio di esposizione acuta con inabilità "
     "reversibile di rapida guarigione."),
]


# Ordered list of the 11 canonical risk categories grouped by macro-area.
# Drives both the SI/NO checklist (Table 26 per env) and the per-category
# 5-col risk tables (Tables 27+). Order matches the DVR template.
_CATEGORY_ORDER: list[tuple[str, str]] = [
    (rc["macro_categoria"], rc["categoria"]) for rc in RISK_CATEGORIES
]

# Macro-area row labels interleaved into the checklist so it mirrors the
# template's 3 section headers + 11 data rows = 14 rows layout.
_MACRO_LABELS: list[str] = [
    "Rischi per la Sicurezza",
    "Rischi per la Salute",
    "Rischi Trasversali",
]


# ---------------------------------------------------------------------------
# Parte IV — the 11 GESTIONE procedures (the template's §4.2–4.12; N2O's
# model titles them unnumbered, in capitals, each on its own divider page).
#
# Each entry mirrors the master template (DVR_TEMPLATE_MAPPING.md §10, paragraphs
# #1800–#2425) and is condensed to the procedural intent + responsibilities,
# not the verbatim 650-paragraph copy. Verbatim ingestion of the full template
# text is tracked separately; the contents below are sufficient to make the
# DVR a legally signable draft (audit verdict 2026-04-28: SHELL-ONLY → DRAFT).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProceduralSection:
    """One GESTIONE procedure of Part IV: a divider page (``heading`` over
    the ``art_key`` photo) followed by its text."""

    heading: str
    art_key: str
    body: tuple[str, ...] = ()
    bullets: tuple[str, ...] = ()
    docs: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Misura di miglioramento templates — keyed by the canonical risk categoria
# (long form, matches RISK_CATEGORIES). Each entry differentiates the
# Procedura and Risorse columns of T109 so the auto-seed pass produces
# operationally distinct rows instead of one repeated template string
# (audit F-002, 2026-04-28).
# ---------------------------------------------------------------------------
_MISURA_TEMPLATE_DEFAULT: dict[str, str] = {
    "procedura": (
        "Verifica dell'efficacia delle misure di prevenzione già in atto, "
        "definizione di procedura operativa dedicata e formazione "
        "specifica dei lavoratori esposti."
    ),
    "risorse": (
        "Tempo del RSPP / Preposto per la stesura della procedura; "
        "eventuale aggiornamento DPI; ore di formazione."
    ),
}

_MISURA_TEMPLATE_BY_CATEGORIA: dict[str, dict[str, str]] = {
    "Strutture": {
        "procedura": (
            "Sopralluogo tecnico per verifica conformità ai requisiti "
            "di sicurezza dei luoghi di lavoro (Allegato IV D.Lgs. 81/08); "
            "interventi edili o impiantistici sui non-conformi; "
            "verifica dell'efficacia tramite controllo programmato."
        ),
        "risorse": (
            "Tecnico abilitato per il sopralluogo; ditta esterna per "
            "interventi edili / impiantistici; budget per interventi "
            "strutturali."
        ),
    },
    "Macchine": {
        "procedura": (
            "Verifica della marcatura CE e dei manuali d'uso; controllo "
            "della funzionalità di protezioni fisse, mobili e di emergenza; "
            "manutenzione periodica programmata e registrata."
        ),
        "risorse": (
            "Manutentore qualificato; budget ricambi; tempo del Preposto "
            "per la verifica e la registrazione delle manutenzioni."
        ),
    },
    "Impianti Elettrici": {
        "procedura": (
            "Verifica periodica obbligatoria degli impianti elettrici e di "
            "messa a terra (D.P.R. 462/01); manutenzione programmata; "
            "informazione ai lavoratori sui rischi residui di natura "
            "elettrica."
        ),
        "risorse": (
            "Verificatore abilitato (ASL/ARPA o organismo notificato); "
            "elettricista qualificato; eventuale aggiornamento "
            "dell'impianto."
        ),
    },
    "Incendio-Esplosioni": {
        "procedura": (
            "Aggiornamento della valutazione del rischio incendio (D.M. "
            "03/09/2021); verifica periodica di estintori, idranti, "
            "porte REI e sistemi di rilevazione; esercitazioni di "
            "evacuazione almeno annuali."
        ),
        "risorse": (
            "Tecnico abilitato per il rinnovo del CPI; ditta manutentrice "
            "antincendio; tempo dei lavoratori per l'esercitazione."
        ),
    },
    "Agenti Chimici": {
        "procedura": (
            "Aggiornamento dell'inventario delle sostanze e delle SDS; "
            "valutazione del rischio chimico ai sensi degli artt. 222-232 "
            "D.Lgs. 81/08; verifica DPI specifici e adeguatezza della "
            "ventilazione."
        ),
        "risorse": (
            "Igienista industriale o consulente chimico; SDS aggiornate; "
            "eventuali campagne di campionamento ambientale."
        ),
    },
    "Agenti Fisici": {
        "procedura": (
            "Misurazione strumentale dell'agente fisico (rumore, "
            "vibrazioni, microclima, illuminamento, campi EM) ai sensi "
            "del Titolo VIII; confronto con i valori limite e azione "
            "se VLE/VAM superati."
        ),
        "risorse": (
            "Tecnico competente in acustica / vibrazioni; strumentazione "
            "di misura; eventuale Allegato dedicato (Microclima, Rumore)."
        ),
    },
    "Agenti Biologici": {
        "procedura": (
            "Valutazione del rischio biologico ai sensi del Titolo X "
            "D.Lgs. 81/08; classificazione degli agenti per gruppo di "
            "pericolo; protocollo di pulizia e disinfezione; sorveglianza "
            "sanitaria mirata."
        ),
        "risorse": (
            "Medico Competente; DPI specifici; protocollo di disinfezione "
            "(prodotti, frequenze, registro)."
        ),
    },
    "Agenti Cancerogeni": {
        "procedura": (
            "Valutazione del rischio cancerogeno ai sensi del Titolo IX "
            "Capo II; sostituzione dell'agente ove tecnicamente possibile; "
            "monitoraggio biologico e ambientale; registro degli esposti."
        ),
        "risorse": (
            "Medico Competente; tecnico per il monitoraggio; eventuale "
            "investimento in sistemi di confinamento."
        ),
    },
    "Organizzazione del Lavoro": {
        "procedura": (
            "Revisione dei carichi di lavoro, dei turni e delle pause; "
            "valutazione del rischio stress lavoro-correlato secondo "
            "metodologia INAIL; monitoraggio degli indicatori sentinella."
        ),
        "risorse": (
            "Tempo del SPP per la revisione dei processi; eventuale "
            "Allegato Stress; possibile coinvolgimento di consulente "
            "del lavoro."
        ),
    },
    "Fattori Psicologici": {
        "procedura": (
            "Indagine sui rischi psicosociali (carichi mentali, conflitti, "
            "molestie); definizione di canali di segnalazione e di un "
            "comitato per i casi più complessi; formazione su gestione "
            "dello stress."
        ),
        "risorse": (
            "Psicologo del lavoro / consulente HR; formazione dedicata; "
            "eventuali sportelli di ascolto."
        ),
    },
    "Fattori Ergonomici": {
        "procedura": (
            "Valutazione dei rischi ergonomici (MMC, posture, VDT, "
            "movimenti ripetitivi); riprogettazione delle postazioni; "
            "addestramento sulle corrette tecniche di sollevamento e "
            "lavoro."
        ),
        "risorse": (
            "Allegati MMC e VDT; ergonomo o fisioterapista occupazionale; "
            "budget per ausili meccanici e arredi conformi UNI EN 1335."
        ),
    },
}


# ---------------------------------------------------------------------------
# Formazione contenuti differenziati per famiglia di mansione (audit F-008).
# Maps a coarse-grained family classifier to (durata, contenuti) tuples.
# Defaults to "rischio medio" for unknown families.
# ---------------------------------------------------------------------------
_FORMAZIONE_BY_FAMILY: dict[str, tuple[str, str]] = {
    "operaio_industriale": (
        "12 ore (rischio alto)",
        "Macchine utensili, organi in movimento, marcatura CE, rumore, "
        "vibrazioni, MMC, agenti chimici industriali, DPI specifici "
        "(udito, mani, occhi, vie respiratorie).",
    ),
    "saldatura_termica": (
        "12 ore (rischio alto)",
        "Fumi di saldatura, raggi UV, rischio incendio/esplosione, "
        "spazi confinati, DPI specifici (maschera, visiera, guanti "
        "saldatura, abbigliamento ignifugo).",
    ),
    "magazziniere_carrellista": (
        "12 ore (rischio alto)",
        "Movimentazione manuale e meccanica dei carichi (NIOSH), "
        "stoccaggio merci, urti contro ostacoli, abilitazione "
        "carrelli elevatori.",
    ),
    "ristorazione": (
        "12 ore (rischio alto)",
        "Rischio biologico alimentare (HACCP), tagli e ustioni, "
        "rischio chimico (detergenti, sgrassanti), MMC, posture, "
        "DPI specifici (calzature antiscivolo, grembiuli, guanti).",
    ),
    "ufficio_vdt": (
        "8 ore (rischio medio)",
        "Esposizione a videoterminali (VDT) ai sensi degli artt. 173-176, "
        "ergonomia della postazione (Allegato XXXIV), illuminazione, "
        "stress correlato all'uso del PC, microclima.",
    ),
    "edile_cantiere": (
        "16 ore (rischio alto)",
        "Lavori in quota, opere provvisionali, lavori in spazi "
        "confinati, rischio elettrico, scavi, utilizzo macchine "
        "movimento terra, DPI III categoria.",
    ),
    "default": (
        "8 ore (rischio medio)",
        "Rischi specifici della mansione e dell'ambiente, misure di "
        "prevenzione, comportamenti di sicurezza, DPI assegnati.",
    ),
}


def _classify_mansione_family(nome: str) -> str:
    """Coarse-grained mansione classifier for the formazione grid."""
    s = (nome or "").lower()
    if any(k in s for k in ("salda",)):
        return "saldatura_termica"
    if any(k in s for k in ("magazz", "carrell", "logist")):
        return "magazziniere_carrellista"
    if any(k in s for k in ("torni", "fresat", "monta", "operaio", "officin")):
        return "operaio_industriale"
    if any(k in s for k in ("cuoc", "mensa", "cucina", "alimenta")):
        return "ristorazione"
    if any(k in s for k in (
        "impieg", "ufficio", "amministrat", "commerc", "tecnic", "videoterminal"
    )):
        return "ufficio_vdt"
    if any(k in s for k in ("cantier", "edile", "muratore", "carpentiere")):
        return "edile_cantiere"
    return "default"


_PART_IV_PROCEDURAL_SECTIONS: tuple[_ProceduralSection, ...] = (
    _ProceduralSection(
        heading="GESTIONE LEGGI E REGOLAMENTI",
        art_key="div_leggi",
        body=(
            "Il RSPP, in collaborazione con il Datore di Lavoro, ha la "
            "responsabilità di mantenere aggiornata la mappa delle leggi e "
            "dei regolamenti applicabili all'attività aziendale e di "
            "garantirne la diffusione presso i soggetti interessati.",
        ),
        bullets=(
            "ricerca delle leggi e regolamenti applicabili e identificazione "
            "di quelli relativi alle attività aziendali",
            "valutazione delle ricadute operative e organizzative delle "
            "novità normative",
            "diffusione interna e archiviazione delle versioni vigenti",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE SORVEGLIANZA SANITARIA",
        art_key="div_sorveglianza",
        body=(
            "Il Datore di Lavoro, tramite il Servizio di Prevenzione e "
            "Protezione, verifica la necessita di sottoporre i lavoratori "
            "a sorveglianza sanitaria nei casi previsti dalla normativa "
            "(art. 41 D.Lgs. 81/2008) e in funzione degli esiti della "
            "valutazione dei rischi.",
            "La sorveglianza ricorre nei casi previsti dalla legge — "
            "esposizione ad agenti chimici, fisici, biologici, "
            "movimentazione manuale dei carichi, videoterminali oltre la "
            "soglia di esposizione, lavoro notturno, gestanti e altri "
            "gruppi sensibili — e in tutti i casi richiesti dal lavoratore "
            "qualora il MC ne riconosca la correlazione con i rischi "
            "professionali.",
            "La nomina e l'eventuale revoca del Medico Competente sono "
            "formalizzate per iscritto e comunicate ai lavoratori e al RLS.",
        ),
        docs=(
            "Lettera di nomina del MC",
            "Protocollo di sorveglianza sanitaria",
            "Giudizi di idoneità alla mansione",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE INFORMAZIONE, FORMAZIONE ED ADDESTRAMENTO",
        art_key="div_formazione",
        body=(
            "Il Datore di Lavoro, in collaborazione con il RSPP e previa "
            "consultazione del RLS, programma le attività di informazione, "
            "formazione ed addestramento ai sensi degli artt. 36 e 37 del "
            "D.Lgs. 81/2008 e dell'Accordo Stato-Regioni 21/12/2011 "
            "(rep. atti 221/CSR) e successivi aggiornamenti.",
            "La programmazione tiene conto della valutazione dei rischi, "
            "delle mansioni svolte, dell'introduzione di nuove "
            "attrezzature o sostanze e delle segnalazioni provenienti dai "
            "preposti, dai lavoratori e dal Medico Competente.",
        ),
        bullets=(
            "formazione generale e specifica per ogni lavoratore in "
            "funzione del livello di rischio della mansione",
            "formazione aggiuntiva per preposti, dirigenti, RLS, addetti "
            "primo soccorso e antincendio",
            "addestramento sull'uso corretto di attrezzature, DPI e "
            "sostanze pericolose",
            "aggiornamento periodico nei termini previsti dalla normativa",
        ),
        docs=(
            "Registro formazione",
            "Attestati di partecipazione",
            "Verbali di addestramento",
        ),
    ),
    _ProceduralSection(
        heading="RIUNIONE PERIODICA",
        art_key="div_riunione",
        body=(
            "Il Datore di Lavoro, direttamente o tramite il RSPP, indice "
            "la riunione periodica ai sensi dell'art. 35 del D.Lgs. "
            "81/2008. La riunione si tiene almeno una volta all'anno per "
            "le aziende con più di 15 lavoratori, ed in occasione di "
            "significative variazioni delle condizioni di esposizione al "
            "rischio.",
            "Della riunione e redatto verbale tenuto a disposizione dei "
            "partecipanti per la consultazione.",
        ),
        docs=(
            "Convocazione della riunione",
            "Verbale di riunione periodica",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE DEGLI INFORTUNI",
        art_key="div_infortuni",
        body=(
            "Ogni infortunio e ogni mancato infortunio (near miss) sono "
            "segnalati al preposto e, per il tramite del RSPP, al Datore "
            "di Lavoro. La gestione comprende la segnalazione tempestiva, "
            "l'indagine sulle cause, l'eventuale costituzione di una "
            "commissione di indagine e l'aggiornamento della valutazione "
            "dei rischi qualora emergano fattori non precedentemente "
            "identificati.",
        ),
        bullets=(
            "segnalazione immediata al preposto e ai soccorsi",
            "denuncia all'INAIL nei termini di legge",
            "indagine interna sulle cause dirette e di radice",
            "aggiornamento del DVR e delle procedure operative ove "
            "necessario",
        ),
        docs=(
            "Registro infortuni",
            "Verbali di indagine",
            "Comunicazioni INAIL",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE COMPORTAMENTI SCORRETTI DEI LAVORATORI",
        art_key="div_comportamenti",
        body=(
            "Il preposto vigila sull'osservanza da parte dei lavoratori "
            "degli obblighi di legge e delle disposizioni aziendali in "
            "materia di salute e sicurezza (art. 19 D.Lgs. 81/2008). I "
            "comportamenti scorretti sono richiamati e gestiti attraverso "
            "il sistema disciplinare aziendale, in coerenza con il CCNL "
            "applicato.",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE DPI",
        art_key="div_gestione_dpi",
        body=(
            "I Dispositivi di Protezione Individuale sono forniti ai "
            "lavoratori a titolo personale, ai sensi degli artt. 74-79 "
            "del D.Lgs. 81/2008, dopo una valutazione dei rischi residui "
            "che non possono essere eliminati alla fonte o ridotti con "
            "misure tecniche o organizzative.",
        ),
        bullets=(
            "scelta dei DPI in funzione dei rischi specifici della "
            "mansione e in conformità al Reg. UE 2016/425",
            "consegna registrata su modulo nominativo (tipologia, codice, "
            "data di consegna, scadenza)",
            "addestramento all'uso corretto, alla manutenzione e alla "
            "conservazione dei DPI di III categoria e di tutti i DPI per "
            "udito",
            "gestione dei casi di inadeguatezza, intolleranza o "
            "deterioramento del DPI",
        ),
        docs=(
            "Modulo di consegna DPI",
            "Comunicazione di inadeguatezza DPI",
            "Schede tecniche dei DPI in dotazione",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE INFRASTRUTTURE",
        art_key="div_infrastrutture",
        body=(
            "Per tutte le macchine, attrezzature, impianti e infrastrutture "
            "presenti in azienda sono definite le responsabilità di "
            "manutenzione ordinaria, straordinaria e di verifica "
            "periodica obbligatoria (D.M. 11/04/2011, all. VII D.Lgs. "
            "81/2008).",
        ),
        docs=(
            "Registro delle attrezzature soggette a verifica periodica",
            "Verbali di manutenzione",
            "Libretti d'uso e manutenzione",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE DEI LAVORATORI PARTICOLARMENTE SENSIBILI AL RISCHIO",
        art_key="div_sensibili",
        body=(
            "L'azienda individua e tutela i lavoratori appartenenti a "
            "gruppi particolarmente sensibili al rischio: lavoratrici "
            "gestanti, puerpere o in periodo di allattamento (D.Lgs. "
            "151/2001), minori (D.Lgs. 345/1999), lavoratori con disabilità, "
            "lavoratori con specifiche prescrizioni del Medico Competente.",
            "Per ciascuna categoria sono adottate misure di prevenzione e "
            "protezione differenziate, riportate negli specifici allegati "
            "del presente DVR (Allegato Gestanti, Allegato Minori, valutazioni "
            "ergonomiche e di stress lavoro-correlato).",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE ACQUISTI",
        art_key="div_acquisti",
        body=(
            "Ogni acquisto di macchine, attrezzature, sostanze chimiche, "
            "DPI e arredi e preceduto dalla verifica della conformità ai "
            "requisiti di sicurezza e salute previsti dalla normativa "
            "vigente. Il RSPP e coinvolto nella definizione dei capitolati "
            "tecnici e nella valutazione preventiva dei rischi introdotti.",
        ),
    ),
    _ProceduralSection(
        heading="GESTIONE DELLE LAVORAZIONI AFFIDATE IN APPALTO",
        art_key="div_appalti",
        body=(
            "Per le lavorazioni affidate in appalto o a lavoratori "
            "autonomi, il Datore di Lavoro committente verifica i "
            "requisiti tecnico-professionali delle ditte appaltatrici "
            "(art. 26 D.Lgs. 81/2008) e promuove la cooperazione e il "
            "coordinamento, redigendo il D.U.V.R.I. nei casi previsti "
            "dalla normativa.",
            "N.B.: nel caso si rientri nel campo di applicazione del "
            "Titolo IV del D.Lgs. 81/2008 (cantieri temporanei o mobili) "
            "si applicano le disposizioni specifiche relative al "
            "coordinamento per la progettazione e per l'esecuzione "
            "dell'opera.",
        ),
        docs=(
            "Verifica idoneità tecnico-professionale",
            "D.U.V.R.I.",
            "Contratti d'appalto",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Part II static boilerplate content (extracted to keep the file lean)
# ---------------------------------------------------------------------------

_METODOLOGIA_INTRO_1 = (
    "La presente valutazione dei rischi e redatta ai sensi dell'art. 28 del "
    "D.Lgs. 9 aprile 2008, n. 81 e s.m.i., che impone al Datore di Lavoro la "
    "valutazione di tutti i rischi per la sicurezza e la salute dei lavoratori, "
    "tenendo conto della specificità delle mansioni, delle attrezzature e degli "
    "ambienti di lavoro."
)

_METODOLOGIA_INTRO_2 = (
    "Il metodo adottato si fonda sulla stima dell'Indice di Rischio (I) "
    "calcolato attraverso la formula I = 2*D + P, dove P rappresenta la "
    "Probabilità di accadimento dell'evento dannoso (scala 1-4) e D il Danno "
    "atteso per il lavoratore esposto (scala 1-4). L'indice risultante, "
    "compreso nell'intervallo 3-12, e associato a un livello di rischio e a "
    "una relativa priorità di intervento. L'impianto metodologico e coerente "
    "con i principi di valutazione del rischio della norma UNI EN ISO 14121-1."
)

_RISK_LEVEL_TABLE_ROWS = [
    ("3-4", "ACCETTABILE", "Monitoraggio", "Continuo"),
    ("5-6", "MODESTO", "Strumenti di minimizzazione", "1 anno"),
    ("7-8", "GRAVE", "Sensibilizzazione + controllo", "6 mesi"),
    ("9-12", "GRAVISSIMO", "Ricerca urgente misure", "Immediatamente"),
]

# ---------------------------------------------------------------------------
# Page map (spec §4.2.1): part labels, the titles that more than one method
# needs, sign panels and picture boxes.
# ---------------------------------------------------------------------------

_PART_I_LABEL = "PARTE I — DATI GENERALI DELL'AZIENDA"
_PART_II_LABEL = "PARTE II — METODOLOGIA DI VALUTAZIONE"
_PART_III_LABEL = "PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO"
_PART_IV_LABEL = "PARTE IV — PROGRAMMA DI MIGLIORAMENTO"

# Row 19: Part III opens once on this divider; each environment then opens on
# its own name (spec §4.2.3).
_ENVIRONMENTS_TITLE = "IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI"
_IMPROVEMENT_TITLE = "PROGRAMMA E PROCEDURE DI ATTUAZIONE DELLE MISURE DI MIGLIORAMENTO"

# Row 23: the five sign panels N2O added after FORMA E CATEGORIE DEI CARTELLI,
# two per page.
_SIGN_PANELS: tuple[tuple[str, str], ...] = (
    ("sign_divieto", "CARTELLI DI DIVIETO"),
    ("sign_avvertimento", "CARTELLI DI AVVERTIMENTO"),
    ("sign_obbligo", "CARTELLI DI OBBLIGO"),
    ("sign_emergenza", "SEGNALI DI EMERGENZA ED EVACUAZIONE"),
    ("sign_antincendio", "SEGNALI DI PREVENZIONE INCENDI"),
)
_SIGN_PANEL_WIDTH_CM = 15.3

# Boxes a picture is fitted into, aspect kept: environment photos (row 20b)
# and the company photo on PRESENTAZIONE DELL'AZIENDA (row 5).
_ENV_PHOTO_BOX_CM = (12.0, 9.0)
_COMPANY_PHOTO_BOX_CM = (16.5, 11.0)
_PICTURE_BORDER_HEX = "BFBFBF"

# Priority words an operator may type in the improvement grid, mapped to the
# colour scale (the model's own rows say "MEDIA").
_PRIORITY_LEVELS = {"ALTA": "ALTO", "MEDIA": "MEDIO", "BASSA": "BASSO"}

_CENTER = WD_ALIGN_PARAGRAPH.CENTER


def _heading(doc: Document, text: str, level: int):
    """``doc.add_heading`` with the kit's font on its run (front headings:
    INDICE, Premessa)."""
    paragraph = doc.add_heading(text, level=level)
    for run in paragraph.runs:
        set_run_font(run)
    return paragraph


def _gap(doc: Document, *, space_pt: float = 0):
    """An empty line between two blocks, ``space_pt`` taller than a line.
    Two tables need one: with nothing in between, Word draws them as a
    single table. Never used to end a section, where it could spill onto a
    page of its own."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(space_pt)
    return paragraph


def _italic_body(doc: Document, text: str):
    """A justified body paragraph in italic: the introductory notes N2O's
    model sets apart (programme, signage, training status) and the
    statements that stand in for an empty section."""
    paragraph = add_body_paragraph(doc, text)
    for run in paragraph.runs:
        run.font.italic = True
    return paragraph


def _note(doc: Document, text: str):
    """The italic grey note under a table (spec token ``note``)."""
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(4)
    set_run_font(paragraph.add_run(text), size=TYPE_SCALE["note"], italic=True, color=NOTE_GREY)
    return paragraph


def _write_cell(cell, text: str, *, bold=None, color=None, align=None, italic=None) -> None:
    """Replace a cell's content with ``text`` in the kit's table type: 10 pt
    Arial, no paragraph spacing. Line breaks become ``w:br``."""
    cell.text = text
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        if align is not None:
            paragraph.alignment = align
        for run in paragraph.runs:
            set_run_font(run, size=TYPE_SCALE["table"], bold=bold, italic=italic, color=color)


def _bullet_cell(cell, items: list[str]) -> None:
    """Fill a cell with a real bulleted list, or "—" when there is nothing."""
    if not add_bullets(cell, items, size_pt=TYPE_SCALE["table"]):
        _write_cell(cell, "—", align=_CENTER)


def _add_picture_border(inline) -> None:
    """A hairline frame around an inline picture, as in N2O's model."""
    sp_pr = inline.find(".//" + qn("pic:spPr"))
    if sp_pr is None:
        return
    line = OxmlElement("a:ln")
    line.set("w", "9525")
    fill = OxmlElement("a:solidFill")
    colour = OxmlElement("a:srgbClr")
    colour.set("val", _PICTURE_BORDER_HEX)
    fill.append(colour)
    line.append(fill)
    sp_pr.append(line)


def _add_fitted_picture(paragraph, source, box_cm: tuple[float, float], *, border: bool = True):
    """Add ``source`` (a path or a stream) to ``paragraph`` at the largest
    size that fits ``box_cm`` (width, height) with its aspect kept.

    Raises when the image is unreadable, so callers can fall back.
    """
    image = DocxImage.from_file(source)
    if not image.px_width or not image.px_height:
        raise ValueError("image without pixel dimensions")
    box_w, box_h = Cm(box_cm[0]), Cm(box_cm[1])
    scale = min(box_w / image.px_width, box_h / image.px_height)
    width = Emu(int(image.px_width * scale))
    height = Emu(int(image.px_height * scale))
    if hasattr(source, "seek"):
        source.seek(0)
    shape = paragraph.add_run().add_picture(source, width=width, height=height)
    if border:
        _add_picture_border(shape._inline)
    return shape


def _keep_case(heading, tail: str) -> None:
    """Print the ``tail`` of a title in its own case. The title style sets
    capitals; N2O's model keeps "(Riferimento)" in lower case under
    "ELENCO FATTORI DI PERICOLO". The paragraph's text is unchanged."""
    runs = heading.runs
    if not runs or not runs[-1].text.endswith(tail):
        return
    runs[-1].text = runs[-1].text[: -len(tail)]
    set_run_font(heading.add_run(tail), caps=False)


def _center_vertically(rows) -> None:
    """Centre every cell of ``rows`` vertically."""
    for row in rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _repeat_as_header(row) -> None:
    """Repeat ``row`` at the top of every page its table spans, and keep it
    on one page (a header row is short)."""
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        insert_in_order(
            tr_pr,
            OxmlElement("w:tblHeader"),
            ("tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"),
        )
    keep_row_together(row)


def _empty_cell(cell) -> None:
    """Leave a cell with one empty paragraph and a white fill, so a
    vertical merge moves nothing into the cell above."""
    tc = cell._tc
    for child in list(tc):
        if child.tag != qn("w:tcPr"):
            tc.remove(child)
    tc.append(OxmlElement("w:p"))
    shade_cell(cell, "FFFFFF")


def _merge_repeated_first_column(table) -> None:
    """Print each first-column value once over the data rows it labels: a
    vertical merge, centred on white (the hazard library of N2O's model)."""
    rows = list(table.rows)[1:]
    start = 0
    while start < len(rows):
        value = rows[start].cells[0].text
        end = start
        while end + 1 < len(rows) and rows[end + 1].cells[0].text == value:
            end += 1
        top = rows[start].cells[0]
        shade_cell(top, "FFFFFF")
        if end > start:
            for row in rows[start + 1 : end + 1]:
                _empty_cell(row.cells[0])
            top = top.merge(rows[end].cells[0])
        top.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in top.paragraphs:
            paragraph.alignment = _CENTER
        start = end + 1


_CROSS_SITE_LABEL = "Tutta l'azienda (ruolo trasversale)"


def _environment_names(person: object) -> list[str]:
    """The names of a person's environments, in the order assigned."""
    return [
        ambiente.nome
        for ambiente in (getattr(person, "ambienti", None) or [])
        if getattr(ambiente, "nome", None)
    ]


def _no_environment_label(person: object) -> str:
    """What the environment cell says for a person assigned to none: the
    cross-site roles (DdL, RSPP, RLS, MC) cover the whole company (audit
    F-011); anyone else is a dash."""
    cross_site = any(
        getattr(person, flag, False)
        for flag in ("ruolo_datore_lavoro", "ruolo_rspp", "ruolo_rls", "ruolo_medico_competente")
    )
    return _CROSS_SITE_LABEL if cross_site else "—"


def _revision_label(version: int) -> str:
    """`DocumentoGenerato.versione` (1-based) → the printed revision ("00").

    The database counts emissions from 1; a DVR numbers them from 0, because
    revision zero *is* the first issue. Both the cover page and the Storico
    Revisioni table go through here so they cannot drift apart — they did, and
    a first-ever DVR carried "Revisione 02" on the cover above a table that
    said "00 — Emissione" (P1-2).
    """
    return f"{max(0, version - 1):02d}"


def _saved_order_key(entity: object) -> tuple[bool, int, float, str]:
    """Order DVR records by their persisted position, then stable metadata."""
    order = getattr(entity, "ordine", None)
    created = getattr(entity, "created_at", None)
    created_key = created.timestamp() if created is not None else float("inf")
    return (
        order is None,
        order if order is not None else 0,
        created_key,
        str(getattr(entity, "id", "")),
    )


def _is_external_safety_consultant(person: object) -> bool:
    """Whether a person is an external RSPP or medico competente only."""
    return bool(
        getattr(person, "is_esterno", False)
        and (
            getattr(person, "ruolo_rspp", False)
            or getattr(person, "ruolo_medico_competente", False)
        )
    )


def _unique_keep_order(values) -> list[str]:
    """De-duplicate strings preserving first occurrence, dropping blanks."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _format_protocol_periodicita_cell(prot: object | None) -> str:
    """§4.3 last column: the saved protocol's periodicità + accertamenti,
    or the MC scaffold when no protocol has been recorded."""
    if prot is None:
        return "[DA COMPILARE — MC]"
    periodicita = (getattr(prot, "periodicita", None) or "").strip()
    parts = [periodicita.capitalize() if periodicita else "[DA COMPILARE — MC]"]
    accertamenti = []
    for a in getattr(prot, "accertamenti", None) or []:
        if not isinstance(a, dict):
            continue
        esame = (a.get("esame") or "").strip()
        if not esame:
            continue
        cadenza = (a.get("periodicita") or "").strip()
        accertamenti.append(f"{esame} ({cadenza})" if cadenza else esame)
    if accertamenti:
        parts.append("Accertamenti: " + "; ".join(accertamenti))
    return "\n".join(parts)


def _employee_persons(persons: list) -> list:
    """Exclude external safety consultants from the employee population."""
    return [person for person in persons if not _is_external_safety_consultant(person)]


def _assigned_employee_persons(ambiente: object, employees: list) -> list:
    """Return employees explicitly assigned to an environment."""
    ambiente_id = getattr(ambiente, "id", None)
    return [
        person
        for person in employees
        if any(
            getattr(item, "id", None) == ambiente_id
            for item in (getattr(person, "ambienti", None) or [])
        )
    ]


def _normalize_equipment_description(value: str | None) -> str:
    """Collapse equipment descriptions into a case-insensitive group key."""
    collapsed = " ".join(value.split()) if isinstance(value, str) else ""
    return (collapsed or "—").casefold()


def _mixed_flag(values: list[bool]) -> str:
    """Render a homogeneous boolean list or flag mixed source values."""
    unique = set(values)
    return "MISTO" if len(unique) > 1 else ("SI" if True in unique else "NO")


def _global_equipment_rows(attrezzature: list, ambienti: list) -> list[list[str]]:
    """Consolidate global equipment while retaining saved environment order."""
    environment_position = {
        getattr(item, "id", None): index for index, item in enumerate(ambienti)
    }
    environment_name = {
        getattr(item, "id", None): (
            getattr(item, "nome", None) or "—"
        ).upper()
        for item in ambienti
    }
    groups: dict[str, dict] = {}
    for source_position, item in enumerate(attrezzature):
        description = getattr(item, "descrizione", None)
        display = " ".join(description.split()) if isinstance(description, str) else ""
        display = display or "—"
        key = _normalize_equipment_description(display)
        group = groups.setdefault(
            key,
            {
                "display": display.upper(),
                "source_position": source_position,
                "environment_ids": [],
                "ce": [],
                "checks": [],
            },
        )
        environment_id = getattr(item, "ambiente_id", None)
        if environment_id not in group["environment_ids"]:
            group["environment_ids"].append(environment_id)
        group["ce"].append(bool(getattr(item, "marcatura_ce", False)))
        group["checks"].append(bool(getattr(item, "verifiche_periodiche", False)))

    def group_key(group: dict) -> tuple[int, int]:
        positions = [
            environment_position.get(item, len(ambienti))
            for item in group["environment_ids"]
        ]
        return (min(positions, default=len(ambienti)), group["source_position"])

    rows = []
    for group in sorted(groups.values(), key=group_key):
        ids = sorted(
            group["environment_ids"],
            key=lambda item: environment_position.get(item, len(ambienti)),
        )
        names = [environment_name.get(item, "—") for item in ids]
        rows.append([
            group["display"],
            ", ".join(dict.fromkeys(names)),
            _mixed_flag(group["ce"]),
            _mixed_flag(group["checks"]),
        ])
    return rows


class DVRMasterGenerator(BaseDocumentGenerator):
    """Generates the DVR Master document (.docx)."""

    async def generate(self) -> str:
        """Generate the DVR Master document.

        Returns:
            Absolute path to the generated .docx file.
        """
        data = dict(await self.load_data())
        data["persone"] = sorted(list(data.get("persone") or []), key=_saved_order_key)
        data["ambienti"] = sorted(list(data.get("ambienti") or []), key=_saved_order_key)
        employee_persons = _employee_persons(data["persone"])
        data["employee_persons"] = employee_persons
        azienda = data["azienda"]
        # DVR-specific extras: foto per ambiente, the company photo,
        # sorveglianza-sanitaria rows per mansione, allegato presence flags,
        # VDT exposure flags, and the misure di miglioramento program. Loaded
        # once here so the renderers don't fan out into N+1 queries.
        extras = await self._load_dvr_extras(data)

        # Look up the version BEFORE building the doc so the revision table
        # and the footer can show it. Same value is used in the filename
        # below — single source of truth.
        version = await self._get_next_version()

        doc = Document()
        self._setup_styles(doc)

        # The page map of N2O's model (spec §4.2.1), row by row.
        add_art_cover(doc, "cover_dvr")                              # 1
        toc_anchors = self._add_table_of_contents(doc)               # 2
        self._add_premessa(doc)                                      # 3
        self._add_pre_parte_i(doc, azienda, data["generated_at"], version)  # 4
        self._add_part_i(                                            # 5–14
            doc,
            azienda,
            data["persone"],
            employee_persons,
            data["attrezzature"],
            data["sostanze_chimiche"],
            data["ambienti"],
            foto_presentazione=extras.get("foto_presentazione"),
        )
        self._add_part_ii(doc)                                       # 15–18
        self._add_part_iii(                                          # 19–24
            doc,
            employee_persons,
            data["ambienti"],
            data["attrezzature"],
            extras,
        )
        self._add_part_iv(                                           # 25–28
            doc,
            azienda,
            data["persone"],
            employee_persons,
            extras,
            generated_at=data["generated_at"],
        )

        # Replace the TOC's cached body with the real outline that the
        # rest of the doc just emitted. Without this Word users who
        # decline the "update fields?" prompt on open see only the
        # placeholder line — the user feedback ("indice deve essere
        # esploso con paginazione e piu dettagliato"). After F9 the
        # field re-resolves with page numbers from the real headings.
        self._finalize_table_of_contents(doc, *toc_anchors)
        add_back_cover(doc)                                          # 29

        # Running header (title | client) and footer (logo · revision |
        # Pag. X di Y) on every page but the art pages, plus honest file
        # properties.
        finish_document(
            doc,
            title="Documento di Valutazione dei Rischi",
            azienda=azienda,
            branding=self.branding,
            version=version,
            generated_at=data["generated_at"],
        )

        # Save with the filename pattern required by US-2.8 AC2:
        # DVR_<ragione_sociale>_<YYYYMMDD>_v<N>.docx.
        # The <ragione_sociale> segment is slugified (lowercase,
        # alphanumeric + underscore) so the filename stays safe on both
        # POSIX and Windows checkouts. The date is the generation day
        # (UTC) so regenerations on the same day keep the same stamp.
        output_dir = self._get_output_dir()
        slug = self._slugify(azienda.ragione_sociale or "azienda")
        date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        filename = f"DVR_{slug}_{date_stamp}_v{version}.docx"
        filepath = os.path.join(output_dir, filename)

        doc.save(filepath)
        return filepath

    @staticmethod
    def _slugify(text: str, max_length: int = 40) -> str:
        """Produce a filesystem-safe slug from a free-form label.

        Lowercases the input, replaces any non-alphanumeric character with
        an underscore, collapses repeated underscores and trims them from
        the edges, then truncates to ``max_length`` characters.
        """
        lowered = (text or "").lower()
        replaced = re.sub(r"[^a-z0-9]+", "_", lowered)
        collapsed = re.sub(r"_+", "_", replaced).strip("_")
        if not collapsed:
            collapsed = "azienda"
        return collapsed[:max_length].rstrip("_") or "azienda"

    async def _load_dvr_extras(self, data: dict) -> dict:
        """Hydrate DVR-only data not loaded by the shared base loader.

        Returns a dict with:
          - ``foto_by_ambiente``: ambiente_id -> list[AmbienteFoto]
          - ``foto_presentazione``: the company photo as ``(bytes,
            content_type)``, or ``None`` (PRESENTAZIONE DELL'AZIENDA then
            prints no photo slot)
          - ``vdt_esposti_persona_ids``: set of persona_ids with VDT esposto=True
          - ``allegati_presenti``: ordered list of (slug, label) for applicable
            allegati, derived from MMC/VDT/Stress/Incendio/Gestanti/
            Microclima/Biologico assessment rows on this azienda
          - ``misure_miglioramento``: list[MisuraMiglioramento] ordered for
            T109 emission (auto-seeded from pericoli I>=7 when empty so the
            document is signable on day 1)

        DPI + rischi specifici flags now live on Persona itself
        (persona.dpi_codes / persona.rischi_specifici_codes), so the
        renderer reads them directly from data["persone"] — no extras
        lookup needed.

        Failure to load any single sub-source is non-fatal — the renderer
        falls back to the empty case rather than crashing the doc job.
        """
        from sqlalchemy import select
        from app.models.ambiente_foto import AmbienteFoto
        from app.models.biologico_valutazione import BiologicoValutazione
        from app.models.gestanti_valutazione import GestantiValutazione
        from app.models.incendio_valutazione import IncendioValutazione
        from app.models.microclima_valutazione import MicroclimaValutazione
        from app.models.misura_miglioramento import MisuraMiglioramento
        from app.models.mmc_valutazione import MmcValutazione
        from app.models.stress_valutazione import StressValutazione
        from app.models.vdt_valutazione import VdtValutazione

        ambienti = data.get("ambienti") or []
        ambiente_ids = [a.id for a in ambienti]

        # Foto per ambiente
        foto_by_ambiente: dict = {}
        if ambiente_ids:
            r = await self.db.execute(
                select(AmbienteFoto)
                .where(AmbienteFoto.ambiente_id.in_(ambiente_ids))
                .order_by(AmbienteFoto.created_at)
            )
            for foto in r.scalars().all():
                foto_by_ambiente.setdefault(foto.ambiente_id, []).append(foto)

        # Company photo for PRESENTAZIONE DELL'AZIENDA (spec §4.2.4). A
        # failed load prints the page without a photo slot rather than
        # failing the whole DVR; the savepoint keeps the transaction usable
        # for the loads below.
        foto_presentazione = None
        try:
            from app.services.document_generator.data_loader import (
                load_foto_presentazione,
            )

            async with self.db.begin_nested():
                foto_presentazione = await load_foto_presentazione(
                    self.db, self.azienda_id
                )
        except Exception:
            logger.warning(
                "DVR company photo could not be loaded; printing without it",
                exc_info=True,
            )

        # VDT esposti persona ids
        vdt_esposti_persona_ids: set = set()
        r = await self.db.execute(
            select(VdtValutazione).where(
                VdtValutazione.azienda_id == self.azienda_id,
                VdtValutazione.esposto.is_(True),
            )
        )
        for v in r.scalars().all():
            if v.persona_id is not None:
                vdt_esposti_persona_ids.add(v.persona_id)

        # Allegato presence detection — one row in the corresponding table
        # is enough for the allegato to be referenced by name.
        allegati_presenti: list[tuple[str, str]] = []
        incendio_present = False
        for model, slug, label in (
            (MmcValutazione, "mmc", "Allegato Movimentazione Manuale dei Carichi (MMC)"),
            (VdtValutazione, "vdt", "Allegato Videoterminali (VDT)"),
            (StressValutazione, "stress", "Allegato Stress Lavoro-Correlato"),
            (IncendioValutazione, "incendio", "Allegato Rischio Incendio"),
            (GestantiValutazione, "gestanti", "Allegato Lavoratrici Gestanti"),
            (MicroclimaValutazione, "microclima", "Allegato Microclima"),
            (BiologicoValutazione, "biologico", "Allegato Rischio Biologico"),
        ):
            r = await self.db.execute(
                select(model.id).where(model.azienda_id == self.azienda_id).limit(1)
            )
            if r.first() is not None:
                allegati_presenti.append((slug, label))
                if model is IncendioValutazione:
                    incendio_present = True

        # PEE (Piano di Emergenza ed Evacuazione) is mandatory under
        # D.M. 03/09/2021 art. 5 + D.Lgs. 81/2008 art. 43 when the workplace
        # has > 10 lavoratori OR an applicable incendio assessment. Audit
        # F-010 flagged the missing cross-reference; we add it here so the
        # allegati list correctly cites the document.
        employees = data.get("employee_persons", data.get("persone", []))
        if len(employees) > 10 or incendio_present:
            allegati_presenti.append((
                "pee", "Piano di Emergenza ed Evacuazione (PEE)"
            ))

        # Misure di miglioramento — auto-seed from pericoli I>=7 when empty
        # so the document is signable from day 1. Operators edit/extend the
        # rows via the API; subsequent generations preserve them.
        r = await self.db.execute(
            select(MisuraMiglioramento)
            .where(MisuraMiglioramento.azienda_id == self.azienda_id)
            .order_by(MisuraMiglioramento.ordine, MisuraMiglioramento.created_at)
        )
        misure = list(r.scalars().all())
        if not misure:
            misure = await self._auto_seed_misure(data)

        # Protocolli sanitari per mansione (segnalazione 2026-08-25) — the
        # MC-reviewed accertamenti / periodicita' / malattie correlate that
        # §4.3 prefers over its "[DA COMPILARE — MC]" scaffold.
        from app.models.protocollo_sanitario import ProtocolloSanitarioMansione

        r = await self.db.execute(
            select(ProtocolloSanitarioMansione)
            .where(ProtocolloSanitarioMansione.azienda_id == self.azienda_id)
            .order_by(ProtocolloSanitarioMansione.mansione)
        )
        protocolli_sanitari = list(r.scalars().all())

        return {
            "foto_by_ambiente": foto_by_ambiente,
            "foto_presentazione": foto_presentazione,
            "vdt_esposti_persona_ids": vdt_esposti_persona_ids,
            "allegati_presenti": allegati_presenti,
            "misure_miglioramento": misure,
            "protocolli_sanitari": protocolli_sanitari,
        }

    async def _auto_seed_misure(self, data: dict) -> list:
        """Derive a starter set of misure di miglioramento from pericoli with
        I >= 5 (MODESTO and above).

        Persists the rows so subsequent generations skip the seeding pass and
        operators can edit them via the API. Tempi:
          I >= 9 GRAVISSIMO → "Immediatamente (entro 30 giorni)"
          I = 7-8 GRAVE     → "Entro 6 mesi"
          I = 5-6 MODESTO   → "Entro 12 mesi (ciclo annuale)"

        Procedura/risorse text is differentiated by the parent valutazione's
        ``categoria_rischio`` rather than emitted as one identical template
        string — addresses audit F-002.
        """
        from app.models.misura_miglioramento import MisuraMiglioramento

        ambienti = data.get("ambienti") or []
        persone = data.get("persone") or []
        ddl = next((p for p in persone if p.ruolo_datore_lavoro), None)
        rspp = next((p for p in persone if p.ruolo_rspp), None)
        ddl_name = (ddl.nominativo if ddl else "DATORE DI LAVORO").upper()
        rspp_name = (rspp.nominativo if rspp else "RSPP").upper()

        # Per-ambiente preposto lookup (ambiente.preposto_id -> persona),
        # falling back to any ambiente persona with ruolo_preposto, else
        # any azienda-level preposto. Mirrors the resolution order used
        # in _add_env_identity_table so the same name flows through the
        # measures table.
        persone_by_id = {p.id: p for p in persone}
        global_preposto = next((p for p in persone if p.ruolo_preposto), None)

        def _resolve_preposto(amb) -> str:
            pid = getattr(amb, "preposto_id", None)
            if pid and pid in persone_by_id:
                return persone_by_id[pid].nominativo.upper()
            for pers in getattr(amb, "persone", None) or []:
                if getattr(pers, "ruolo_preposto", False):
                    return pers.nominativo.upper()
            if global_preposto:
                return global_preposto.nominativo.upper()
            return "PREPOSTO DA NOMINARE"

        # Categories whose interventions are typically structural -> DdL.
        # Categories that are operational/behavioural -> Preposto.
        # Everything else (procedure, formazione, chemical, biological,
        # psychosocial) -> RSPP.
        ddl_categories = {
            "Strutture",
            "Impianti Elettrici",
            "Incendio-Esplosioni",
        }
        preposto_categories = {
            "Macchine",
            "Agenti Fisici",
            "Fattori Ergonomici",
        }

        # One row per categoria, not per pericolo (segnalazione 2026-08-21,
        # "molte misure me le ripete"): the procedura/risorse template is
        # per categoria, so per-pericolo rows printed the same measure once
        # per pericolo and again for every ambiente it appeared in. Each
        # grouped row lists the pericoli it covers (with their ambiente) in
        # the "Rischio" column; tempi, priorita and the provenance link
        # follow the most severe pericolo in the group; the responsabile
        # column names every preposto involved when the categoria is theirs.
        from app.services.misure_dedupe import join_risk_labels

        grouped: dict[str, dict] = {}
        for amb in ambienti:
            for v in getattr(amb, "valutazioni_rischio", None) or []:
                cat_long = normalize_categoria_to_long(
                    getattr(v, "categoria_rischio", "") or ""
                ) or "Generico"
                for per in getattr(v, "pericoli", None) or []:
                    indice = getattr(per, "indice_i", None)
                    if indice is None or indice < 5:
                        continue
                    if not getattr(per, "applicabile", True):
                        continue
                    entry = grouped.setdefault(
                        cat_long,
                        {"labels": "", "top": per, "top_indice": -1, "preposti": []},
                    )
                    pericolo_text = (per.pericolo or "").strip() or cat_long
                    entry["labels"] = join_risk_labels(
                        entry["labels"],
                        f"{pericolo_text} ({(amb.nome or '').upper()})",
                    )
                    if indice > entry["top_indice"]:
                        entry["top"] = per
                        entry["top_indice"] = indice
                    if cat_long in preposto_categories:
                        preposto = _resolve_preposto(amb)
                        if preposto not in entry["preposti"]:
                            entry["preposti"].append(preposto)

        seeded: list[MisuraMiglioramento] = []
        ordine = 0
        for cat_long, entry in grouped.items():
            per = entry["top"]
            indice = entry["top_indice"]
            template = _MISURA_TEMPLATE_BY_CATEGORIA.get(
                cat_long, _MISURA_TEMPLATE_DEFAULT
            )
            livello = getattr(per, "livello_rischio", None) or ""
            if indice >= 9:
                tempi = "Immediatamente (entro 30 giorni)"
            elif indice >= 7:
                tempi = "Entro 6 mesi"
            else:
                tempi = "Entro 12 mesi (ciclo annuale)"

            if indice >= 9 or cat_long in ddl_categories:
                responsabile = ddl_name
            elif cat_long in preposto_categories:
                responsabile = "; ".join(entry["preposti"]) or _resolve_preposto(None)
            else:
                responsabile = rspp_name

            misura_text = f"Riduzione del rischio — {cat_long}: {entry['labels']}"
            # Procedura/risorse from the categoria template are a starting
            # point, not a finished plan. Mark them with a DA COMPILARE
            # prefix so an inspector immediately sees which rows still need
            # the RSPP to write the specific procedure for the actual
            # pericoli (audit F-002, 2026-04-29 rerun). The marker
            # disappears the moment the operator edits the row via the API.
            da_compilare = "[DA COMPILARE — RSPP] "
            misura = MisuraMiglioramento(
                azienda_id=self.azienda_id,
                pericolo_valutazione_id=per.id,
                misura=misura_text,
                procedura=da_compilare + template["procedura"],
                risorse=da_compilare + template["risorse"],
                responsabile=responsabile,
                scadenza=tempi,
                priorita=livello,
                ordine=ordine,
            )
            self.db.add(misura)
            seeded.append(misura)
            ordine += 1

        if seeded:
            await self.db.flush()
            # We do not commit here — leave the transaction open so the
            # surrounding generation request controls the boundary. The rows
            # are visible to subsequent reads in this session.
        return seeded

    async def _get_next_version(self) -> int:
        """The revision number to stamp on this DVR.

        Delegates to the base helper so the cover page, the file name and the
        ``documenti_generati`` row cannot disagree — they used to: this method
        recomputed ``max(versione) + 1`` *after* the API had already inserted
        the pending row, so a first-ever DVR came out as ``Revisione 02`` and
        ``…_v2.docx`` while the row said ``1`` and the document's own Storico
        Revisioni table said ``00 — Emissione`` (P1-2).
        """
        return await self.resolve_version(["dvr_master", "DVR_MASTER"])

    # ------------------------------------------------------------------
    # Document styles setup
    # ------------------------------------------------------------------

    def _setup_styles(self, doc: Document) -> None:
        """A4, Arial everywhere, the DVR's heading roles: the kit's ``dvr``
        profile (spec §4.1.4).

        Heading 1 is the 14 pt front heading (INDICE, Premessa; part labels
        add their own look on top), Heading 2 the 25 pt centred title in
        capitals, Heading 3 the 12 pt centred sub-title. Normal is Arial
        12 pt; tables write their 10 pt themselves. Every heading keeps with
        the next paragraph and never splits, so a title never ends a page on
        its own (user feedback 2026-05-12: "Impaginazione dovrebbe rispettare
        più le tabelle e i capitoli").
        """
        setup_document(doc, profile="dvr")

    # ------------------------------------------------------------------
    # Rows 2–3 — index and Premessa
    # ------------------------------------------------------------------

    def _add_table_of_contents(self, doc: Document):
        """INDICE: a real Word TOC field (``TOC \\o "1-3" \\h \\z \\u``).

        Its cached body is a placeholder until
        :meth:`_finalize_table_of_contents` rewrites it from the headings the
        rest of the document emits; Word refreshes the field, page numbers
        included, on open. Returns ``(field_start_p, end_p)``, the anchors the
        finalizer needs.
        """
        return add_toc(doc, title="INDICE")

    def _finalize_table_of_contents(self, doc: Document, field_start_p, end_p) -> None:
        """Replace the TOC field's cached body with the real outline.

        One line per Heading 1–3 after the field, indented by level, with a
        dot leader to the right margin, so the index reads complete before
        any refresh (user feedback 2026-05-12: "indice deve essere esploso
        con paginazione e più dettagliato"). Without headings the placeholder
        stays.
        """
        finalize_toc(doc, field_start_p, end_p)

    def _add_premessa(self, doc: Document) -> None:
        """Premessa — the legal preamble required by D.Lgs. 81/2008 art. 28.

        The master template carries ~20 paragraphs of foreword text under a
        Heading 1 "Premessa". The condensed version below preserves the
        binding obligations, the rielaborazione triggers (art. 29 c. 3) and
        the conservation requirement, and is sufficient for the document to
        read as a complete DVR rather than a numbered shell.
        """
        _heading(doc, "Premessa", 1)

        for body in (
            "Il presente documento rappresenta l'attuazione dell'obbligo "
            "previsto per il datore di lavoro dall'art. 17, comma 1, "
            "lettera a) del D.Lgs. 9 aprile 2008, n. 81 e s.m.i., relativo "
            "alla valutazione di tutti i rischi per la salute e la "
            "sicurezza dei lavoratori, e dall'art. 28 dello stesso decreto, "
            "che ne disciplina l'oggetto e le modalità di redazione.",
            "La valutazione dei rischi è stata effettuata in collaborazione "
            "con il Responsabile del Servizio di Prevenzione e Protezione "
            "(RSPP), con il Medico Competente — ove la sorveglianza "
            "sanitaria sia richiesta dalla normativa o dalla valutazione "
            "stessa — e previa consultazione del Rappresentante dei "
            "Lavoratori per la Sicurezza (RLS).",
            "L'analisi prende in considerazione la natura dell'attività, "
            "i luoghi di lavoro, le mansioni svolte, le attrezzature "
            "impiegate, le sostanze e i preparati pericolosi utilizzati, "
            "nonché le caratteristiche dei lavoratori, con particolare "
            "attenzione ai gruppi più sensibili al rischio quali "
            "lavoratrici gestanti, minori, lavoratori con prescrizioni "
            "del Medico Competente e lavoratori notturni.",
            "Il documento è conservato presso l'unità produttiva alla "
            "quale si riferisce e reso disponibile per la consultazione "
            "ai soggetti previsti dall'art. 18 e dagli artt. 50 e 47 del "
            "D.Lgs. 81/2008. La sua rielaborazione è prevista nei casi "
            "stabiliti dall'art. 29, comma 3 — modifiche significative "
            "del processo produttivo o dell'organizzazione del lavoro, "
            "infortuni significativi, evoluzione della tecnica, esiti "
            "della sorveglianza sanitaria — e comunque ad ogni successiva "
            "modifica delle condizioni operative.",
            # The sections are unnumbered since N2O's model, so the
            # programme is named by its part rather than by "§4.1".
            "Le misure di prevenzione e protezione attuate sono descritte, "
            "per ogni ambiente di lavoro, nella Parte III. Il programma "
            "delle misure di miglioramento di cui all'art. 28, comma 2, "
            "lettera c) è riportato nella Parte IV.",
        ):
            add_body_paragraph(doc, body)

    # ------------------------------------------------------------------
    # Row 4 — DOCUMENTO ELABORATO SUGLI ESITI DELLA VALUTAZIONE DEI RISCHI
    # (Template Tables 0, 1, 2)
    # ------------------------------------------------------------------

    def _add_pre_parte_i(
        self, doc: Document, azienda, generated_at: datetime, version: int
    ) -> None:
        """The identity page before Parte I: the light identity strip, the
        revision history and the Timbro e Firma box.

        ``version`` is the number the footer prints, passed down so the two
        cannot contradict each other (see :func:`_revision_label`). N2O's
        model dropped the "ex art. 17, comma 1, lettera a) …" line that used
        to sit under the title.
        """
        add_section_title(
            doc, "DOCUMENTO ELABORATO SUGLI ESITI DELLA VALUTAZIONE DEI RISCHI"
        )
        self._add_azienda_header_table(doc, azienda)
        # The model spreads the three tables out, about 2 cm apart.
        _gap(doc, space_pt=24)
        self._add_revision_history_table(doc, generated_at, version)
        _gap(doc, space_pt=24)
        self._add_timbro_firma_table(doc)

    def _add_revision_history_table(
        self, doc: Document, generated_at: datetime, version: int
    ) -> None:
        """Template Table 1 — Rev. | Motivazione | Data under a navy header.

        Emits a single row for the current emission, numbered from the same
        source as the footer. It used to be hardcoded to "00 — Emissione",
        so a regenerated DVR claimed to be a first issue no matter how many
        times it had been reissued.
        """
        rows = [[
            _revision_label(version),
            # Art. 29 c.3 is what makes a DVR get reissued, so name it rather
            # than repeating "Emissione" for a revision that isn't one.
            "Emissione" if version <= 1 else "Aggiornamento ex art. 29 c.3",
            generated_at.strftime("%d/%m/%Y"),
        ]]
        table = add_data_table(
            doc,
            ["Rev.", "Motivazione", "Data"],
            rows,
            column_widths_cm=[2.0, 11.0, 3.5],
        )
        style_header_row(table.rows[0], bg_hex=BRAND_NAVY_HEX)

    def _add_timbro_firma_table(self, doc: Document) -> None:
        """Template Table 2 — the "Timbro e Firma" box: a navy band over a
        blank area tall enough to stamp and sign."""
        table = doc.add_table(rows=2, cols=1)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        band_row, sign_row = table.rows
        band = band_row.cells[0]
        _write_cell(band, "Timbro e Firma", bold=True, color=HEADER_TEXT, align=_CENTER)
        shade_cell(band, BRAND_NAVY_HEX)
        band.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in band.paragraphs:
            paragraph.paragraph_format.keep_with_next = True
        _write_cell(sign_row.cells[0], "")
        sign_row.height = Cm(3.5)
        sign_row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for row in table.rows:
            keep_row_together(row)
        set_table_borders(table)

    # ------------------------------------------------------------------
    # Parte I — rows 5–14 (Template Tables 3–17)
    # ------------------------------------------------------------------

    def _add_part_i(
        self,
        doc: Document,
        azienda,
        persone: list,
        employee_persons: list,
        attrezzature: list,
        sostanze_chimiche: list,
        ambienti: list,
        *,
        foto_presentazione: tuple[bytes, str] | None = None,
    ) -> None:
        """Parte I — DATI GENERALI DELL'AZIENDA.

        In-page titles (rows 5–10): PRESENTAZIONE DELL'AZIENDA (identity
        strip, company photo, activity description), ANAGRAFICA AZIENDALE,
        DATI ANAGRAFICI, DATI OCCUPAZIONALI, ORGANIZZAZIONE AZIENDALE DELLA
        SICUREZZA and AMBIENTI DI LAVORO. Then four divider pages (rows
        11–14): SERVIZI IGIENICO-ASSISTENZIALI, MACCHINE, ATTREZZATURE ED
        IMPIANTI, SOSTANZE, PRODOTTI E PREPARATI CHIMICI and ELENCO FATTORI
        DI PERICOLO.

        Template tables (DVR_TEMPLATE_MAPPING.md): 3 identity, 4 anagrafica,
        5 occupational data (split in two by N2O), 6–9 roles, 10–11 addetti,
        12 ambienti, 13 equipment, 14 chemicals, 15–17 hazard library.
        """
        # Row 5 — the activity description moved here from Part II in
        # N2O's model, after the identity strip and the company photo.
        add_section_title(doc, "PRESENTAZIONE DELL'AZIENDA", part_label=_PART_I_LABEL)
        self._add_azienda_header_table(doc, azienda)
        self._add_company_photo(doc, foto_presentazione)
        self._add_activity_description(doc, azienda)

        # Row 6 — Table 4.
        add_section_title(doc, "ANAGRAFICA AZIENDALE")
        self._add_anagrafica_table(doc, azienda, persone, employee_persons)

        # Rows 7–8 — Table 5, split by N2O: who the workers are, then what
        # they do and where.
        add_section_title(doc, "DATI ANAGRAFICI")
        self._add_dati_anagrafici_table(doc, employee_persons)
        add_section_title(doc, "DATI OCCUPAZIONALI")
        self._add_dati_occupazionali_ambienti_table(doc, employee_persons)

        # Row 9 — Tables 6–11.
        add_section_title(doc, "ORGANIZZAZIONE AZIENDALE DELLA SICUREZZA")
        role_tables = [
            ("Datore di Lavoro",
             [p for p in persone if p.ruolo_datore_lavoro]),
            ("Responsabile del Servizio di Prevenzione e Protezione",
             [p for p in persone if p.ruolo_rspp]),
            ("Rappresentante dei Lavoratori per la Sicurezza",
             [p for p in persone if p.ruolo_rls]),
            ("Medico Competente",
             [p for p in persone if getattr(p, "ruolo_medico_competente", False)]),
        ]
        for index, (title, role_persone) in enumerate(role_tables):
            if index:
                _gap(doc, space_pt=4)
            self._add_single_role_title_table(doc, title, role_persone)
        _gap(doc, space_pt=6)
        self._add_addetti_role_table(
            doc,
            "Addetti al Primo Soccorso",
            [p for p in persone if p.ruolo_primo_soccorso],
        )
        _gap(doc, space_pt=6)
        self._add_addetti_role_table(
            doc,
            "Addetti alla Prevenzione Incendi e Lotta Antincendio",
            [p for p in persone if p.ruolo_antincendio],
        )

        # Row 10 — Table 12.
        add_section_title(doc, "AMBIENTI DI LAVORO")
        self._add_ambienti_summary_table(doc, ambienti, employee_persons)

        # Row 11 — required under D.Lgs. 81/2008 Allegato IV §1.10-1.16
        # (audit F-003).
        self._add_servizi_igienico_assistenziali_section(doc, azienda, employee_persons)

        # Row 12 — Table 13. Pass ambienti so the renderer can resolve
        # ambiente_id → nome without lazy-loading `attrezzatura.ambiente`
        # (the base loader doesn't selectinload that relationship, and lazy
        # access in an async session raises MissingGreenlet).
        add_divider(doc, "MACCHINE, ATTREZZATURE ED IMPIANTI", "div_macchine")
        self._add_attrezzature_table(doc, attrezzature, ambienti)

        # Row 13 — Table 14.
        add_divider(doc, "SOSTANZE, PRODOTTI E PREPARATI CHIMICI", "div_sostanze")
        self._add_sostanze_table(doc, sostanze_chimiche)

        # Row 14 — Tables 15, 16, 17: the static hazard library.
        title = add_divider(
            doc, "ELENCO FATTORI DI PERICOLO (Riferimento)", "div_fattori_pericolo"
        )
        _keep_case(title, "(Riferimento)")
        note = _note(
            doc,
            "N.B. Gli elenchi seguenti sono da intendersi indicativi e non "
            "esaustivi. Sono valutati in dettaglio per ogni ambiente di "
            "lavoro nella Parte III.",
        )
        note.paragraph_format.space_after = Pt(8)
        self._add_hazard_library_group(doc, "Rischi per la Sicurezza", [
            "Strutture", "Macchine", "Impianti Elettrici", "Incendio-Esplosioni",
        ])
        _gap(doc, space_pt=6)
        self._add_hazard_library_group(doc, "Rischi per la Salute", [
            "Agenti Chimici", "Agenti Fisici", "Agenti Biologici", "Agenti Cancerogeni",
        ])
        _gap(doc, space_pt=6)
        self._add_hazard_library_group(doc, "Rischi Trasversali", [
            "Organizzazione del Lavoro", "Fattori Psicologici", "Fattori Ergonomici",
        ])

    def _add_company_photo(self, doc: Document, foto) -> None:
        """Row 5 — the company photo under the identity strip (spec §4.2.4).

        Centred, as large as fits 16.5 × 11 cm with its aspect kept, framed
        by a hairline. ``foto`` is ``(bytes, content_type)`` from
        ``load_foto_presentazione``. No photo, no slot; unreadable bytes are
        logged and the page prints without them.
        """
        content = foto[0] if isinstance(foto, (tuple, list)) else foto
        if not content:
            return
        paragraph = doc.add_paragraph()
        paragraph.alignment = _CENTER
        paragraph.paragraph_format.space_before = Pt(12)
        try:
            _add_fitted_picture(paragraph, BytesIO(content), _COMPANY_PHOTO_BOX_CM)
        except Exception:
            paragraph._p.getparent().remove(paragraph._p)
            logger.warning(
                "DVR company photo could not be embedded; printing without it",
                exc_info=True,
            )

    def _add_activity_description(self, doc: Document, azienda) -> None:
        """Row 5 — what the company does: the narrative, the ciclo produttivo
        line and the regional references (Part II §2.1 until N2O's model
        moved them under PRESENTAZIONE DELL'AZIENDA)."""
        paragraphs = []
        descrizione = (azienda.descrizione_attivita or "").strip()
        if descrizione:
            # Split into multiple paragraphs on blank-line separators or on
            # sentence-group boundaries so the section reads as the
            # multi-paragraph narrative the spec expects (audit F-004).
            for body in self._split_descrizione_paragraphs(descrizione):
                paragraphs.append(add_body_paragraph(doc, body))
        else:
            placeholder = doc.add_paragraph()
            set_run_font(
                placeholder.add_run(
                    "[Descrizione dell'attività da compilare durante la revisione]"
                ),
                italic=True,
                color=NOTE_GREY,
            )
            paragraphs.append(placeholder)

        # Synthesized "ciclo produttivo" paragraph from ATECO + attivita +
        # zona sismica + orario lavoro — these structured fields exist
        # on the Azienda but aren't surfaced in the descrizione narrative.
        ciclo_bits: list[str] = []
        ateco = getattr(azienda, "codice_ateco", None)
        attivita = getattr(azienda, "attivita", None)
        if ateco and attivita:
            ciclo_bits.append(
                f"Ciclo produttivo: l'attività è classificata sotto il "
                f"codice ATECO {ateco} ({attivita})."
            )
        zona = getattr(azienda, "zona_sismica", None)
        if zona:
            ciclo_bits.append(
                f"Zona sismica di appartenenza: {zona} "
                "(O.P.C.M. 3274/2003 e successive deliberazioni regionali)."
            )
        orario = getattr(azienda, "orario_lavoro", None)
        if orario:
            ciclo_bits.append(
                f"Articolazione dell'orario di lavoro: {orario}."
            )
        if ciclo_bits:
            add_body_paragraph(doc, " ".join(ciclo_bits))

        contesto = (getattr(azienda, "contesto_territoriale", None) or "").strip()
        if contesto:
            add_body_paragraph(doc, f"Contesto territoriale: {contesto}")

        # US-2.2 AC1: regione + applicable regional regulations, driven off
        # sede_legale_citta (falls back to sede_operativa_citta). Silent
        # no-op for comuni not in the 158-entry lookup so the generator never
        # fails because of a missing regulation match — the operator fills
        # it in during review.
        sede_citta = (
            getattr(azienda, "sede_legale_citta", None)
            or getattr(azienda, "sede_operativa_citta", None)
            or ""
        )
        regione, regulations = get_regulations_for_comune(sede_citta.strip())
        if regione and regulations:
            add_body_paragraph(doc, f"Regione di riferimento: {regione}")
            lead = doc.add_paragraph()
            set_run_font(
                lead.add_run(
                    "Regolamenti regionali applicabili (in aggiunta al D.Lgs. 81/2008):"
                ),
                italic=True,
            )
            for reg in regulations:
                bullet = add_bullets(doc, [f"{reg['titolo']} — {reg['riferimento']}"])[0]
                set_run_font(bullet.add_run(f" ({reg['ambito']})"), italic=True)

        if paragraphs:
            paragraphs[0].paragraph_format.space_before = Pt(12)

    def _add_anagrafica_table(
        self, doc: Document, azienda, persone: list, employee_persons: list
    ) -> None:
        """Row 6 — ANAGRAFICA AZIENDALE (Template Table 4), the blue
        key/value table.

        Required rows (Ragione Sociale, Datore di Lavoro, Sede Legale, Sede
        Operativa) always render. Optional rows are SKIPPED entirely when
        null/empty — empty placeholder rows like "—" or "Non comunicato" are
        noise that an inspector flags. The audit gate in
        api/v1/documents._ensure_anagrafica_complete_for_dvr already blocks
        generation when ALL of CF/Tel/Email/PEC are missing, so at least one
        of those rows will always render.
        """
        ddl = next((p for p in persone if p.ruolo_datore_lavoro), None)
        ddl_label = (
            f"{(ddl.nominativo or '').upper()}"
            f"{f' — {ddl.mansione}' if ddl and ddl.mansione else ''}"
            if ddl else "—"
        )
        # Count of effective workers prefers the actual roster (Persone) over
        # the operator-declared figure on the Azienda. The declared count is
        # surfaced in parentheses when it diverges, so reviewers can spot
        # discrepancies between visura camerale and the live survey.
        actual_count = len(employee_persons or [])
        declared = getattr(azienda, "numero_dipendenti_dichiarati", None)
        if declared and declared != actual_count:
            dipendenti_label = f"{actual_count} (dichiarati: {declared})"
        else:
            dipendenti_label = str(actual_count)

        # Required rows — always rendered, even when the underlying field
        # is blank, so the table structure is recognisable.
        anagrafica_rows: list[tuple[str, str]] = [
            ("Ragione Sociale", azienda.ragione_sociale or "—"),
            ("Datore di Lavoro", ddl_label),
            # Street, then "CAP Comune (PROV)", on two lines as in the model.
            ("Sede Legale", self._format_seat_lines(
                azienda.sede_legale_via, azienda.sede_legale_citta,
                getattr(azienda, "cap_legale", None),
                getattr(azienda, "provincia_legale", None),
            )),
            ("Sede Operativa", self._format_seat_lines(
                azienda.sede_operativa_via, azienda.sede_operativa_citta,
                getattr(azienda, "cap_operativa", None),
                getattr(azienda, "provincia_operativa", None),
            )),
        ]

        # Optional rows — skip entirely when null/empty. Order preserved
        # to match the prior layout (Attivita / ATECO above contacts,
        # operativi at the bottom).
        def _add_optional(label: str, value, formatter=lambda v: str(v)) -> None:
            if value is None:
                return
            if isinstance(value, str) and not value.strip():
                return
            anagrafica_rows.append((label, formatter(value)))

        # The label is prose and takes the accent; the attribute name is schema
        # and must not (P1-1).
        _add_optional("Attività", getattr(azienda, "attivita", None))
        _add_optional("Codice ATECO", getattr(azienda, "codice_ateco", None))
        _add_optional("Partita IVA", getattr(azienda, "partita_iva", None))
        _add_optional("Codice Fiscale", getattr(azienda, "codice_fiscale", None))
        # REA (Repertorio Economico Amministrativo) — registry id present on
        # the azienda row but previously never rendered (audit F-302).
        _add_optional("REA", getattr(azienda, "rea", None))
        _add_optional("Telefono", getattr(azienda, "telefono", None))
        _add_optional("Email", getattr(azienda, "email", None))
        _add_optional("PEC", getattr(azienda, "pec", None))
        _add_optional("Orario di Lavoro", getattr(azienda, "orario_lavoro", None))
        # Numero dipendenti always rendered — derived from the Persone roster
        # and the declared figure, both of which the survey forces.
        anagrafica_rows.append(("Numero Totale Dipendenti", dipendenti_label))
        _add_optional(
            "Metratura Totale",
            getattr(azienda, "metratura_totale", None),
            formatter=lambda v: f"{v} mq",
        )
        _add_optional(
            "Zona Sismica",
            getattr(azienda, "zona_sismica", None),
            formatter=lambda v: str(v),
        )

        self._add_key_value_table(doc, anagrafica_rows, variant="blue")

    def _add_dati_anagrafici_table(self, doc: Document, persone: list) -> None:
        """Row 7 — DATI ANAGRAFICI: Nominativo | Codice Fiscale | Tipologia
        contrattuale, one row per employee in saved order.

        The first half of the old Table 5, which N2O's model splits in two.
        The column holds the persona's codice fiscale, so a dash reads as
        "CF not entered" (audit F-007, 2026-04-29 rerun).
        """
        headers = ["Nominativo", "Codice Fiscale", "Tipologia contrattuale"]
        rows = [
            [
                (p.nominativo or "—").upper(),
                getattr(p, "codice_fiscale", None) or "—",
                (p.tipologia_contrattuale or "—").upper(),
            ]
            for p in persone
        ] or [["—", "—", "—"]]
        self._add_data_table(doc, headers, rows, widths=[6.5, 5.5, 4.5])

    def _add_dati_occupazionali_ambienti_table(self, doc: Document, persone: list) -> None:
        """Row 8 — DATI OCCUPAZIONALI: Nominativo | Mansione | Ambiente di
        Lavoro, the environments as a real bulleted list, one per line, in
        the order they are assigned to the person.

        Cross-site roles (DdL / RSPP / RLS / MC) typically operate across the
        whole company and have no explicit ambiente assignment: they read
        "Tutta l'azienda (ruolo trasversale)" rather than a dash, so
        reviewers don't take it for missing data (audit F-011).
        """
        headers = ["Nominativo", "Mansione", "Ambiente di Lavoro"]
        if not persone:
            self._add_data_table(doc, headers, [["—", "—", "—"]])
            return
        table = self._add_data_table(
            doc,
            headers,
            [
                [(p.nominativo or "—").upper(), (p.mansione or "—").upper(), ""]
                for p in persone
            ],
            widths=[5.0, 5.0, 6.5],
        )
        for row, person in zip(table.rows[1:], persone):
            names = [name.upper() for name in _environment_names(person)]
            if names:
                _bullet_cell(row.cells[2], names)
            else:
                label = _no_environment_label(person).upper()
                _write_cell(row.cells[2], label, align=_CENTER if label == "—" else None)

    def _add_single_role_title_table(
        self, doc: Document, title: str, role_persone: list
    ) -> None:
        """Template Tables 6–9 — a role band: the role in white on the table
        blue over who holds it, "—" when nobody does.

        Feedback #10 (2026-04-29): MC and RSPP are frequently external
        consultants. We append "(ESTERNO)" to the name when `is_esterno` is
        set. The flag is only writable on MC/RSPP in the survey UI, so DdL
        and RLS rows naturally carry it false and render unchanged.
        """
        def _format(p) -> str:
            base = (p.nominativo or "").upper()
            return f"{base} (ESTERNO)" if getattr(p, "is_esterno", False) else base

        names = [name for name in (_format(p) for p in role_persone) if name.strip()]
        add_role_band(doc, title, "\n".join(names))

    def _add_addetti_role_table(
        self, doc: Document, title: str, role_persone: list
    ) -> None:
        """Template Tables 10, 11 — Nominativo | Mansione under a band naming
        the emergency role. Both header rows repeat on every page."""
        table = doc.add_table(rows=2, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        band = table.rows[0].cells[0].merge(table.rows[0].cells[1])
        _write_cell(band, title)
        style_header_row(table.rows[0])

        sub_row = table.rows[1]
        for i, text in enumerate(["Nominativo", "Mansione"]):
            cell = sub_row.cells[i]
            _write_cell(cell, text, bold=True, color=BRAND_NAVY, align=_CENTER)
            shade_cell(cell, BRAND_SURFACE_HEX)
        _repeat_as_header(sub_row)

        holders = [
            [(p.nominativo or "—").upper(), (p.mansione or "—").upper()]
            for p in role_persone
        ] or [["—", "—"]]
        for values in holders:
            row = table.add_row()
            for cell, text in zip(row.cells, values):
                _write_cell(cell, text, align=_CENTER if text == "—" else None)
        set_table_borders(table)

    def _add_servizi_igienico_assistenziali_section(
        self, doc: Document, azienda, persone: list
    ) -> None:
        """Row 11 — SERVIZI IGIENICO-ASSISTENZIALI (D.Lgs. 81/2008 Allegato IV
        §1.10-1.16), on its own divider page. Mandatory section for any
        workplace; the M/F separation requirement triggers above 10
        lavoratori.
        """
        add_divider(doc, "SERVIZI IGIENICO-ASSISTENZIALI", "div_servizi_igienici")

        n_dipendenti = len(persone or [])
        sex_distribution = {p.sesso for p in persone if getattr(p, "sesso", None)}
        mixed = sex_distribution >= {"M", "F"}

        add_body_paragraph(
            doc,
            "Le dotazioni igienico-assistenziali sono conformi ai requisiti "
            "minimi previsti dall'Allegato IV del D.Lgs. 81/2008 (§1.10 - "
            "1.16) per quanto riguarda servizi igienici, lavabi, spogliatoi "
            "e locali di riposo / refezione.",
        )
        if n_dipendenti > 10 and mixed:
            extra = (
                f"Con un numero di lavoratori pari a {n_dipendenti} e in "
                "presenza di personale di entrambi i sessi, l'azienda "
                "garantisce servizi igienici e spogliatoi distinti per "
                "uomini e donne (Allegato IV §1.13)."
            )
        elif n_dipendenti > 10:
            extra = (
                f"Con un numero di lavoratori pari a {n_dipendenti}, "
                "l'azienda garantisce servizi igienici e spogliatoi "
                "adeguati al numero degli addetti (Allegato IV §1.13)."
            )
        else:
            extra = (
                "Sono garantiti servizi igienici e spogliatoi adeguati "
                "al numero degli addetti (Allegato IV §1.13)."
            )
        add_body_paragraph(doc, extra)

        servizi_descr = (
            getattr(azienda, "servizi_igienici_descrizione", None) or ""
        ).strip()
        if servizi_descr:
            add_body_paragraph(doc, servizi_descr)
        else:
            add_bullets(doc, [
                "Servizi igienici aerati e illuminati naturalmente o "
                "con ricambio d'aria forzato.",
                "Lavabi con acqua corrente e dispenser per il lavaggio "
                "delle mani.",
                "Spogliatoi con armadietti individuali a doppio scomparto "
                "ove l'attività comporti l'uso di indumenti da lavoro.",
                "Locale di riposo/refezione adeguato quando i lavoratori "
                "consumano i pasti in azienda.",
            ])

    def _add_ambienti_summary_table(
        self, doc: Document, ambienti: list, employee_persons: list
    ) -> None:
        """Row 10 — Template Table 12: Ambiente | Tipo | Metratura | N. Lavoratori.

        Note on N. Lavoratori: a worker assigned to multiple ambienti is
        counted once per ambiente, so the column sum can exceed the total
        dipendenti reported in the Anagrafica (e.g. preposti + addetti
        emergenza operate across several aree). A footnote below the table
        makes the convention explicit so an inspector does not flag the
        discrepancy.
        """
        headers = ["Ambiente", "Tipo", "Metratura", "N. Lavoratori"]
        if not ambienti:
            rows = [["—", "—", "—", "0"]]
        else:
            rows = []
            for a in ambienti:
                mq = getattr(a, "superficie_mq", None)
                rows.append([
                    (a.nome or "—").upper(),
                    (a.tipo or "—"),
                    f"{mq} mq" if mq else "—",
                    str(len(_assigned_employee_persons(a, employee_persons))),
                ])
        self._add_data_table(doc, headers, rows, widths=[6.0, 4.5, 2.8, 3.2])
        # N2O's model ends the note at "più righe": the old pointer to
        # "§1.1" died with the section numbers.
        _note(
            doc,
            "Nota: la colonna \"N. Lavoratori\" conteggia ciascun addetto "
            "una volta per ogni ambiente in cui opera; preposti, addetti "
            "alle emergenze e personale con mansioni trasversali "
            "compaiono pertanto in più righe.",
        )

    def _add_attrezzature_table(
        self,
        doc: Document,
        attrezzature: list,
        ambienti: list | None = None,
    ) -> None:
        """Row 12 — Template Table 13, the global equipment inventory.

        Columns: Descrizione | Ambiente | Marcata CE | Verifiche periodiche.

        Rationale for the Ambiente column (feedback 2026-05-12: "macchine
        attrezzature impianti non mette le cose giuste"): the previous
        3-column variant rendered 1 row per piece of equipment with no
        location context, so identical descriptions (e.g. two "TRAPANO A
        COLONNA" rows from two different ambienti) looked like
        duplicates. Rows are grouped by description, each listing every
        ambiente that holds it, in the saved environment order.

        We resolve `ambiente_id → nome` via the in-memory ambienti list
        rather than lazy-loading `attrezzatura.ambiente`: the base
        loader doesn't selectinload that backref, and lazy access in an
        async session raises MissingGreenlet. ``ambienti=None`` keeps
        the old "Ambiente: —" behavior for any caller that doesn't
        thread the list through.
        """
        headers = [
            "Macchine, Attrezzature ed Impianti",
            "Ambiente",
            "Marcata CE",
            "Verifiche Periodiche",
        ]
        if not attrezzature:
            rows = [["Nessuna attrezzatura registrata.", "—", "—", "—"]]
        else:
            rows = _global_equipment_rows(attrezzature, ambienti or [])
        self._add_data_table(doc, headers, rows, widths=[6.0, 5.5, 2.2, 2.8])

    def _add_sostanze_table(self, doc: Document, sostanze: list) -> None:
        """Row 13 — Template Table 14, the chemical inventory + SDS detail.

        Two-block layout:
          1. Inventory table — name, manufacturer, use, destination, state,
             GHS pictogram codes (SDS-extracted when available, "—" for
             manually entered rows).
          2. Per-sostanza H/P phrase detail: every substance in the
             inventory gets an entry, those without SDS phrases an explicit
             "SDS non disponibile" line, so an inspector sees no apparent gap
             between the inventory count and the detail block.
        """
        headers = [
            "Sostanza / Prodotto",
            "Produttore / Distributore",
            "Attività / Uso",
            "Destinazione d'uso",
            "Stato",
            "Pittogrammi GHS",
        ]
        if not sostanze:
            self._add_data_table(
                doc,
                headers,
                [["Nessuna sostanza chimica registrata.", "—", "—", "—", "—", "—"]],
            )
            return

        rows = []
        for s in sostanze:
            pittogrammi = getattr(s, "pittogrammi", None) or []
            rows.append([
                (s.nome_prodotto or "—").upper(),
                (s.produttore or "—").upper(),
                (getattr(s, "attivita_uso", None) or "—"),
                (getattr(s, "destinazione_uso", None) or "—"),
                (getattr(s, "stato_miscela", None) or "—").upper(),
                ", ".join(pittogrammi) if pittogrammi else "—",
            ])
        self._add_data_table(doc, headers, rows)

        heading = doc.add_paragraph()
        heading.paragraph_format.space_before = Pt(12)
        heading.paragraph_format.keep_with_next = True
        set_run_font(
            heading.add_run("Dettaglio frasi di pericolo (H) e consigli di prudenza (P)"),
            bold=True,
            color=BRAND_NAVY,
        )

        size = TYPE_SCALE["table"]
        for s in sostanze:
            frasi_h = getattr(s, "frasi_h", None) or []
            frasi_p = getattr(s, "frasi_p", None) or []

            name = doc.add_paragraph()
            name.paragraph_format.space_before = Pt(6)
            name.paragraph_format.keep_with_next = True
            set_run_font(
                name.add_run((s.nome_prodotto or "—").upper()),
                size=size,
                bold=True,
                color=BRAND_NAVY,
            )
            for label, frasi in (("Frasi H: ", frasi_h), ("Frasi P: ", frasi_p)):
                if not frasi:
                    continue
                line = doc.add_paragraph()
                set_run_font(line.add_run(label), size=size, bold=True)
                set_run_font(line.add_run("; ".join(frasi)), size=size)
            if not frasi_h and not frasi_p:
                line = doc.add_paragraph()
                set_run_font(
                    line.add_run(
                        "SDS non disponibile — richiedere al fornitore "
                        "scheda di sicurezza aggiornata ex Reg. CE 1907/2006 "
                        "(REACH) e Reg. CE 1272/2008 (CLP) prima dell'uso."
                    ),
                    size=size,
                    italic=True,
                )

    def _add_hazard_library_group(
        self, doc: Document, macro_label: str, categorie: list[str]
    ) -> None:
        """Row 14 — Template Tables 15/16/17: the static hazard catalogue of
        one macro-area, each category name once over its rows, as in N2O's
        model."""
        rows: list[list[str]] = []
        for categoria in categorie:
            for item in HAZARD_LIBRARY.get(categoria, []):
                rows.append([categoria.upper(), item])

        if not rows:
            rows = [["—", "—"]]

        table = self._add_data_table(
            doc, headers=["Categoria", macro_label], rows=rows, widths=[4.5, 12.0]
        )
        _merge_repeated_first_column(table)

    # ------------------------------------------------------------------
    # Parte II — rows 15–18: method
    # ------------------------------------------------------------------

    def _add_part_ii(self, doc: Document) -> None:
        """Parte II — METODOLOGIA DI VALUTAZIONE (rows 15–18).

        DEFINIZIONI (Template Table 19), the method with its I → level table,
        the probability and damage scales (Tables 21, 22), each under an
        in-page title. The activity description that used to open Part II
        (§2.1) sits under PRESENTAZIONE DELL'AZIENDA since N2O's model, which
        also renamed the part.
        """
        add_section_title(doc, "DEFINIZIONI", part_label=_PART_II_LABEL)
        self._add_data_table(
            doc,
            headers=["Termine", "Definizione"],
            rows=[list(r) for r in _DEFINIZIONI_ROWS],
            widths=[4.5, 12.0],
        )

        add_section_title(doc, "METODOLOGIA DI VALUTAZIONE DEI RISCHI")
        add_body_paragraph(doc, _METODOLOGIA_INTRO_1)
        intro = add_body_paragraph(doc, _METODOLOGIA_INTRO_2)
        intro.paragraph_format.space_after = Pt(12)
        self._add_risk_level_table(doc)

        add_section_title(doc, "SCALA DI PROBABILITÀ (P)")
        self._add_data_table(
            doc,
            headers=["P", "Livello", "Criteri"],
            rows=[list(row) for row in _PROBABILITA_CRITERI_ROWS],
            widths=[1.5, 3.5, 11.5],
        )

        add_section_title(doc, "SCALA DEL DANNO (D)")
        self._add_data_table(
            doc,
            headers=["D", "Livello", "Criteri"],
            rows=[list(row) for row in _DANNO_CRITERI_ROWS],
            widths=[1.5, 3.5, 11.5],
        )

    def _add_risk_level_table(self, doc: Document) -> None:
        """The I range → Livello / Azione / Tempistica lookup table.

        The ``Livello`` cell takes the level's colour (``level_cell``), the
        same palette as the Part III risk tables and the app's risk chips.
        """
        table = self._add_data_table(
            doc,
            ["I", "Livello", "Azione", "Tempistica"],
            [list(row) for row in _RISK_LEVEL_TABLE_ROWS],
            widths=[2.0, 4.0, 6.5, 4.0],
        )
        for row in table.rows[1:]:
            # The model gives this small reference table generous rows.
            row.height = Cm(0.8)
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = _CENTER
            level_cell(row.cells[1], row.cells[1].text)

    # ------------------------------------------------------------------
    # Parte III — rows 19–24: risk assessment per environment
    # ------------------------------------------------------------------

    def _add_part_iii(
        self,
        doc: Document,
        persone: list,
        ambienti: list,
        attrezzature: list,
        extras: dict,
    ) -> None:
        """Parte III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO.

        Row 19: one divider for the whole part. Row 20, per environment in
        saved order: its name as an in-page title (identity and addetti
        tables, Template Tables 24–25), then machines, photos and the
        risk-category checklist (Table 26), each on a new page, and one page
        per applicable risk category (Tables 27+). N2O's model shows a single
        environment; the divider appearing once and the page per sub-block
        are extrapolated from it (spec §4.2.3).

        Rows 21–24: mansioni with specific risks, DPI, segnaletica and the
        training programme, each on its own divider.
        """
        add_divider(doc, _ENVIRONMENTS_TITLE, "div_ambienti", part_label=_PART_III_LABEL)
        if not ambienti:
            _italic_body(doc, "Nessun ambiente di lavoro registrato.")
        else:
            # Phase 8.2 — bucket attrezzature by ambiente_id once so each env
            # section gets its own slice. Anything without an ambiente_id is
            # silently skipped here (it still appears in the global Part I
            # inventory table, so it isn't lost).
            attrezzature_by_ambiente: dict = {}
            for att in attrezzature:
                amb_id = getattr(att, "ambiente_id", None)
                if amb_id is None:
                    continue
                attrezzature_by_ambiente.setdefault(amb_id, []).append(att)

            foto_by_ambiente = extras.get("foto_by_ambiente", {})
            vdt_ids = extras.get("vdt_esposti_persona_ids", set())
            # Gestanti-allegato presence rewrites the legacy "Vedi normativa"
            # marker on the gestanti risk row — see
            # _normalize_special_riferimento.
            gestanti_presente = any(
                slug == "gestanti"
                for slug, _ in (extras.get("allegati_presenti") or [])
            )
            persone_by_id = {getattr(p, "id", None): p for p in persone}
            for ambiente in ambienti:
                # VDT-esposti workers in this ambiente trigger a synthetic row
                # in the Agenti Fisici risk table referencing art. 174 + the
                # Allegato VDT (audit F-007).
                env_persone = _assigned_employee_persons(ambiente, persone)
                vdt_in_env = sum(
                    1 for p in env_persone
                    if getattr(p, "id", None) in vdt_ids
                )
                self._add_environment_section(
                    doc,
                    ambiente,
                    persone_by_id,
                    attrezzature_by_ambiente.get(ambiente.id, []),
                    foto_by_ambiente.get(ambiente.id, []),
                    persone,
                    vdt_in_env,
                    gestanti_allegato_presente=gestanti_presente,
                )

        self._add_mansioni_rischi_specifici_section(doc, persone, extras)
        self._add_dpi_per_persona_section(doc, persone, extras)
        self._add_segnaletica_section(doc)
        self._add_formazione_programma_section(doc, persone)

    def _add_azienda_header_table(self, doc: Document, azienda) -> None:
        """The light identity strip (Template Tables 3/23): Azienda, Sede
        Legale and Sede Operativa, each seat on two lines — street, then
        "CAP Comune (PROV)" — as in N2O's model.

        It prints on rows 4 and 5 only: the model dropped the copies that
        opened Parts II–IV and every environment.
        """
        rows = [
            ("Azienda", (azienda.ragione_sociale or "—").upper()),
            ("Sede Legale", self._format_seat_lines(
                azienda.sede_legale_via, azienda.sede_legale_citta,
                getattr(azienda, "cap_legale", None),
                getattr(azienda, "provincia_legale", None),
            )),
        ]
        if azienda.sede_operativa_via or azienda.sede_operativa_citta:
            rows.append(("Sede Operativa", self._format_seat_lines(
                azienda.sede_operativa_via, azienda.sede_operativa_citta,
                getattr(azienda, "cap_operativa", None),
                getattr(azienda, "provincia_operativa", None),
            )))
        # Issue #11 (2026-05-14): when the client has more than one
        # operating address, list the extras as additional rows under the
        # "Altre sedi operative" label. The list is whatever the operator
        # entered in the aziende form — empty rows have already been
        # filtered out at submit time, but defend against missing-attr
        # for older Azienda rows that pre-date the JSONB column.
        extras = getattr(azienda, "sedi_operative_extra", None) or []
        for sede in extras:
            if not isinstance(sede, dict):
                continue
            line = self._format_seat_lines(
                sede.get("via"),
                sede.get("citta") or sede.get("comune"),
                sede.get("cap"),
                sede.get("provincia"),
            )
            if line and line != "—":
                rows.append(("Altre sedi operative", line))
        self._add_key_value_table(doc, rows, variant="light")

    def _add_environment_section(
        self,
        doc: Document,
        ambiente,
        persone_by_id: dict,
        attrezzature: list,
        foto: list,
        employee_persons: list,
        vdt_count: int = 0,
        *,
        gestanti_allegato_presente: bool = False,
    ) -> None:
        """One environment (row 20), in the order of Template Tables 24–33:

          1. its name as the title, then identity (Table 24) and addetti
             (Table 25);
          2. new page: the machines, equipment and plant in this ambiente
             (Phase 8.2, the per-env slice of the Part I inventory);
          3. new page: photos and plans, when AmbienteFoto rows exist;
          4. new page: the risk-category checklist (Table 26);
          5. one page per applicable risk category (Tables 27+).
        """
        nome_ambiente = (ambiente.nome or "—").upper()
        add_section_title(doc, nome_ambiente)
        self._add_env_identity_table(doc, ambiente, persone_by_id)
        _gap(doc, space_pt=14)
        self._add_env_addetti_table(doc, ambiente, employee_persons)

        add_sub_title(
            doc, f"Macchine, Attrezzature ed Impianti — {nome_ambiente}", new_page=True
        )
        self._add_env_attrezzature_table(doc, attrezzature)

        if foto:
            self._add_env_foto_block(doc, nome_ambiente, foto)

        add_sub_title(
            doc, f"Identificazione dei Fattori di Rischio — {nome_ambiente}", new_page=True
        )
        self._add_env_risk_checklist(doc, ambiente)

        self._add_env_risk_tables(
            doc,
            ambiente,
            vdt_count=vdt_count,
            gestanti_allegato_presente=gestanti_allegato_presente,
        )

    def _add_env_foto_block(
        self, doc: Document, nome_ambiente: str, foto: list
    ) -> None:
        """Up to ten saved photos on a new page, each fitted into 12 × 9 cm
        and framed, without the "Fig. N — filename" captions N2O removed.
        Shared database bytes come before the local file; a photo with no
        readable source prints a filename-specific marker for the reviewer.
        """
        add_sub_title(doc, f"Foto e Planimetrie — {nome_ambiente}", new_page=True)
        for photo in foto[:10]:
            safe_name = Path(
                str(getattr(photo, "filename", None) or photo.id).replace("\\", "/")
            ).name[:255]
            embedded = False
            warned = False
            for source in _photo_image_sources(photo):
                paragraph = doc.add_paragraph()
                paragraph.alignment = _CENTER
                paragraph.paragraph_format.space_before = Pt(6)
                paragraph.paragraph_format.space_after = Pt(6)
                try:
                    _add_fitted_picture(paragraph, source, _ENV_PHOTO_BOX_CM)
                except Exception:
                    paragraph._element.getparent().remove(paragraph._element)
                    warned = True
                    logger.warning(
                        "DVR photo candidate could not be embedded",
                        extra={
                            "photo_id": str(photo.id),
                            "photo_filename": safe_name,
                        },
                    )
                    continue
                embedded = True
                break
            if embedded:
                continue
            marker = doc.add_paragraph()
            set_run_font(
                marker.add_run(f"[Foto non disponibile: {safe_name}]"),
                size=TYPE_SCALE["note"],
                italic=True,
                color=NOTE_GREY,
            )
            if not warned:
                logger.warning(
                    "DVR photo unavailable",
                    extra={
                        "photo_id": str(photo.id),
                        "photo_filename": safe_name,
                    },
                )

    # ------------------------------------------------------------------
    # Parte III tail — rows 21–24: mansioni, DPI, segnaletica, formazione
    # ------------------------------------------------------------------

    def _add_mansioni_rischi_specifici_section(
        self, doc: Document, persone: list, extras: dict
    ) -> None:
        """Row 21 — MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI
        (DOCUMENT_STRUCTURE.md §3.N+1), on its own divider.

        One row per exposed employee, so people with the same mansione do
        not inherit each other's risks; the risks are a bulleted list in the
        cell, as in N2O's model. Sources, per persona:
          - VDT esposti (>= 20h/week → "Videoterminali" rischio specifico)
          - persona.attrezzature_speciali codes (each maps to a rischio)
          - persona.rischi_specifici_codes ticked in the wizard
        """
        add_divider(
            doc, "MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI", "div_mansioni"
        )
        vdt_ids = extras.get("vdt_esposti_persona_ids", set())
        exposed = [
            (person, labels)
            for person in persone
            if (labels := _person_specific_risk_labels(person, vdt_ids))
        ]
        if not exposed:
            add_body_paragraph(
                doc, "Nessun lavoratore esposto a rischi specifici configurato."
            )
            return

        table = self._add_data_table(
            doc,
            ["Nominativo", "Mansione", "Rischio specifico"],
            [
                [
                    (getattr(person, "nominativo", None) or "—").upper(),
                    (getattr(person, "mansione", None) or "—").upper(),
                    "",
                ]
                for person, _labels in exposed
            ],
            widths=[4.8, 4.2, 7.5],
        )
        for row, (_person, labels) in zip(table.rows[1:], exposed):
            _bullet_cell(row.cells[2], labels)

    def _add_dpi_per_persona_section(
        self, doc: Document, persone: list, extras: dict
    ) -> None:
        """Row 22 — DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI), on its own
        divider: one sub-title per employee (the name in capitals, in the
        index, in saved order) over that person's own DPI — the codes ticked
        on the persona in the wizard — as in N2O's model (pp. 56–57). Two
        people with the same mansione keep their own tables.

        A person with no DPI gets an explicit "Nessun DPI specifico
        richiesto" row instead of silent omission, so an inspector can tell
        "no PPE for this worker, and why" from "this worker was forgotten".
        When the person's mansione names a gestante, the row cites the
        art. 12 D.Lgs. 151/2001 measures, documented even when no PPE is
        prescribed.
        """
        from app.services.reference_data import DPI_CATALOG

        add_divider(doc, "DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI)", "div_dpi")

        if not persone:
            _italic_body(
                doc,
                "Le dotazioni DPI per lavoratore sono in fase di compilazione. "
                "Nel frattempo, i DPI sono assegnati in base alla valutazione "
                "dei rischi descritta in Parte III e secondo la procedura "
                "di gestione dei DPI della Parte IV.",
            )
            return

        for person in sorted(persone, key=_saved_order_key):
            add_sub_title(doc, (person.nominativo or "").strip().upper() or "—")

            # Group by area so the table mirrors the DPI catalog layout.
            # Spec §3.N+2 requires Descrizione | Marca/Modello | Note;
            # Marca/Modello and Note are operator-completed at first audit
            # so we emit a defensible placeholder rather than blanks.
            by_area: dict[str, list[str]] = {}
            for code in sorted(set(getattr(person, "dpi_codes", None) or [])):
                meta = DPI_CATALOG.get(code) or {}
                by_area.setdefault(meta.get("area", "Altro"), []).append(
                    meta.get("etichetta", code)
                )
            rows = [
                [
                    f"{area}: {'; '.join(sorted(labels))}",
                    "Da definire al primo audit DPI",
                    "Conforme a Reg. UE 2016/425; verifica annuale",
                ]
                for area, labels in sorted(by_area.items())
            ]
            if not rows:
                gestante = "GESTANTE" in (person.mansione or "").upper()
                rows.append([
                    "Nessun DPI specifico richiesto — esposizione "
                    "limitata; tutela attraverso ergonomia della "
                    "postazione, sorveglianza sanitaria periodica "
                    "(allegato VDT) e formazione.",
                    "—",
                    "Misure di tutela art. 12 D.Lgs. 151/2001 — "
                    "rimozione dei rischi ex Allegati A/B/C; "
                    "se non rimovibili, modifica orario o mansione."
                    if gestante
                    else "Sorveglianza sanitaria e formazione ex art. 36-37 D.Lgs. 81/2008.",
                ])
            dpi_table = self._add_data_table(
                doc,
                headers=["Descrizione DPI", "Marca / Modello", "Note"],
                rows=rows,
                widths=[7.0, 4.5, 5.0],
                v_center=False,
            )
            _center_dpi_brand_model_placeholders(dpi_table)

    def _add_segnaletica_section(self, doc: Document) -> None:
        """Row 23 — SEGNALETICA DI SICUREZZA (D.Lgs. 81/2008 art. 161-166,
        Allegato XXIV-XXXII), on its own divider: the colour code, the sign
        shapes and the five sign panels N2O added, two per page.
        """
        add_divider(doc, "SEGNALETICA DI SICUREZZA", "div_segnaletica")

        _italic_body(
            doc,
            "L'azienda adotta segnaletica di sicurezza conforme al D.Lgs. "
            "81/2008 (artt. 161-166, allegati XXIV-XXXII) per richiamare "
            "l'attenzione su rischi residui, divieti, prescrizioni e "
            "indicazioni di emergenza.",
        )

        # Tabella 105 — Codifica cromatica (Allegato XXV D.Lgs. 81/2008).
        # Mappa colore -> significato e indicazioni d'uso.
        add_sub_title(doc, "CODIFICA CROMATICA DELLA SEGNALETICA")
        color_rows = [
            ["Rosso", "Divieto", "Atteggiamenti pericolosi", "Stop, dispositivi di interruzione, sgombero"],
            ["Rosso", "Pericolo / allarme", "Identificazione attrezzature antincendio", "Estintori, idranti, punto di raccolta"],
            ["Giallo o giallo-arancio", "Avvertimento", "Attenzione, cautela, verifica", "Pericolo elettrico, infiammabile, biologico"],
            ["Azzurro", "Prescrizione", "Comportamento o azione specifica, obbligo DPI", "Obbligo casco, guanti, occhiali, otoprotettori"],
            ["Verde", "Salvataggio / soccorso", "Porte, uscite, percorsi, materiali, postazioni, locali", "Uscita di emergenza, cassetta primo soccorso, defibrillatore"],
            ["Verde", "Situazione di sicurezza", "Ritorno alla normalità", "Punto di raccolta evacuazione"],
        ]
        self._add_data_table(
            doc,
            headers=["Colore", "Significato", "Indicazioni e precisazioni", "Esempi"],
            rows=color_rows,
        )

        # Tabella 106 — Forma dei cartelli (Allegato XXIV D.Lgs. 81/2008).
        # Mappa forma + colore -> categoria di cartello.
        add_sub_title(doc, "FORMA E CATEGORIE DEI CARTELLI", new_page=True)
        shape_rows = [
            ["Cartelli di divieto", "Tonda", "Pittogramma nero su fondo bianco; bordo e banda diagonale rossi", "Vietato fumare; vietato l'accesso ai non addetti; vietato spegnere con acqua"],
            ["Cartelli di avvertimento", "Triangolare", "Pittogramma nero su fondo giallo; bordo nero", "Pericolo elettrico; materiale infiammabile; carichi sospesi; rischio biologico"],
            ["Cartelli di prescrizione", "Tonda", "Pittogramma bianco su fondo azzurro", "Obbligo casco; obbligo guanti; obbligo occhiali; obbligo otoprotettori"],
            ["Cartelli di salvataggio", "Rettangolare o quadrata", "Pittogramma bianco su fondo verde", "Uscita di emergenza; direzione vie di fuga; punto di raccolta; defibrillatore"],
            ["Cartelli antincendio", "Rettangolare o quadrata", "Pittogramma bianco su fondo rosso", "Estintore; idrante; pulsante di allarme; scala antincendio"],
            ["Cartelli supplementari", "Rettangolare", "Testo nero su fondo bianco o coordinato al cartello principale", "Distanza, altezza, indicazioni testuali integrative"],
        ]
        self._add_data_table(
            doc,
            headers=["Categoria", "Forma", "Colori e caratteristiche", "Esempi"],
            rows=shape_rows,
        )

        self._add_sign_panels(doc)

    def _add_sign_panels(self, doc: Document) -> None:
        """The five sign panels of N2O's model, two per page: a caption (out
        of the index) over the panel at 15.3 cm. A panel whose own artwork
        is missing is left out rather than shown with another picture."""
        placed = 0
        for key, title in _SIGN_PANELS:
            path = art_path(key)
            if path is None or path.name != ART.get(key):
                logger.warning("Sign panel %r has no artwork; panel left out", key)
                continue
            caption = add_sub_title(doc, title, in_toc=False, new_page=placed % 2 == 0)
            picture = doc.add_paragraph()
            picture.alignment = _CENTER
            picture.paragraph_format.line_spacing = 1.0
            picture.paragraph_format.space_after = Pt(6)
            try:
                picture.add_run().add_picture(str(path), width=Cm(_SIGN_PANEL_WIDTH_CM))
            except Exception:
                for paragraph in (picture, caption):
                    paragraph._p.getparent().remove(paragraph._p)
                logger.warning("Sign panel %r could not be embedded; panel left out", key, exc_info=True)
                continue
            placed += 1

    def _add_formazione_programma_section(
        self, doc: Document, persone: list
    ) -> None:
        """Row 24 — PROGRAMMA DI INFORMAZIONE, FORMAZIONE E ADDESTRAMENTO
        (template §3.N+4), on its own divider. Driven by mansione/ruolo so
        the operator gets a starter grid covering the Accordo Stato-Regioni
        21/12/2011 obligations.
        """
        add_divider(
            doc, "PROGRAMMA DI INFORMAZIONE, FORMAZIONE E ADDESTRAMENTO", "div_formazione"
        )

        # Feedback #3 (2026-05-19): surface the current training-completion
        # status so the DdL sees at a glance how many workers still need the
        # latest cycle before the programma table.
        total = len(persone)
        if total > 0:
            done = sum(
                1 for p in persone if getattr(p, "training_recente_completato", False)
            )
            pending = total - done
            if pending == 0:
                status = (
                    f"Stato formazione attuale: tutti i {total} lavoratori "
                    "hanno completato la formazione più recente."
                )
            else:
                noun = "lavoratore" if pending == 1 else "lavoratori"
                verb = "necessita" if pending == 1 else "necessitano"
                status = (
                    f"Stato formazione attuale: {done}/{total} lavoratori "
                    f"hanno completato la formazione più recente; "
                    f"{pending} {noun} {verb} di aggiornamento."
                )
            _italic_body(doc, status).paragraph_format.space_after = Pt(8)

        rows: list[list[str]] = []

        # Generic worker formation — applies to every mansione.
        rows.append([
            "TUTTI I LAVORATORI",
            "Formazione generale",
            "4 ore",
            "Concetti generali in tema di prevenzione e sicurezza sul lavoro",
            "All'assunzione + aggiornamento quinquennale",
        ])

        # Risk-class-specific formation — durata + contenuti differentiated
        # by mansione family (operai industriali, ufficio, ristorazione,
        # logistica) so the operator gets a meaningful starter grid instead
        # of identical rows (audit F-008).
        seen_mansioni: set[str] = set()
        for p in persone:
            nome = (p.mansione or "").strip()
            if not nome or nome in seen_mansioni:
                continue
            seen_mansioni.add(nome)
            family = _classify_mansione_family(nome)
            durata, contenuti = _FORMAZIONE_BY_FAMILY[family]
            rows.append([
                nome.upper(),
                "Formazione specifica",
                durata,
                contenuti,
                "All'assunzione + aggiornamento quinquennale",
            ])

        # Role-specific formation
        if any(p.ruolo_rspp for p in persone):
            rows.append([
                "RSPP",
                "Modulo A + B + C",
                "Min. 100 ore",
                "Modulo A (28h), Modulo B (variabile per ATECO), Modulo C (24h)",
                "Aggiornamento 40 ore / 5 anni",
            ])
        if any(p.ruolo_rls for p in persone):
            rows.append([
                "RLS",
                "Formazione iniziale + aggiornamento",
                "32 ore + 8 h/anno",
                "Diritti e doveri del RLS, normativa, valutazione rischi",
                "Annuale (8 ore per >50 lavoratori, 4 ore per 15-50)",
            ])
        if any(p.ruolo_preposto for p in persone):
            rows.append([
                "PREPOSTO",
                "Formazione aggiuntiva",
                "8 ore",
                "Soggetti del SPP, vigilanza sull'applicazione delle misure",
                "Aggiornamento periodico (Accordo Stato-Regioni; obblighi del preposto rafforzati dal D.L. 146/2021 conv. L. 215/2021)",
            ])
        if any(p.ruolo_primo_soccorso for p in persone):
            rows.append([
                "ADDETTI PRIMO SOCCORSO",
                "Formazione D.M. 388/2003",
                "12 o 16 ore (gruppo A/B/C)",
                "BLS, gestione emergenze sanitarie, contenuti cassetta P.S.",
                "Aggiornamento triennale",
            ])
        if any(p.ruolo_antincendio for p in persone):
            rows.append([
                "ADDETTI ANTINCENDIO",
                "Formazione D.M. 02/09/2021",
                "4 / 8 / 16 ore (livello 1/2/3)",
                "Misure preventive, attrezzature antincendio, esercitazioni",
                "Aggiornamento quinquennale",
            ])
        if any(p.attrezzature_speciali for p in persone):
            rows.append([
                "ADDETTI ATTREZZATURE SPECIFICHE",
                "Abilitazione (Acc. SR 22/02/2012)",
                "8-16 ore + pratica",
                "Carrelli elevatori, PLE, gru, ruspe, ADR, lavori in quota",
                "Aggiornamento quinquennale",
            ])

        self._add_data_table(
            doc,
            headers=["Destinatari", "Tipologia", "Durata", "Contenuti", "Cadenza"],
            rows=rows,
            widths=[3.3, 3.0, 2.4, 4.6, 3.2],
        )

    def _add_env_attrezzature_table(
        self, doc: Document, attrezzature: list
    ) -> None:
        """Row 20a — the machines, equipment and plant of one environment
        (Phase 8.2)."""
        headers = [
            "Macchine, Attrezzature ed Impianti",
            "Marcata CE",
            "Verifiche Periodiche",
        ]
        if not attrezzature:
            rows = [["Nessuna attrezzatura associata a questo ambiente.", "—", "—"]]
        else:
            rows = [
                [
                    (a.descrizione or "—").upper(),
                    "SI" if a.marcatura_ce else "NO",
                    "SI" if a.verifiche_periodiche else "NO",
                ]
                for a in attrezzature
            ]
        table = self._add_data_table(doc, headers, rows, widths=[9.5, 3.0, 4.0])
        for row in table.rows[1:]:
            for cell in row.cells[1:]:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = _CENTER

    def _add_env_identity_table(
        self, doc: Document, ambiente, persone_by_id: dict
    ) -> None:
        """Template Table 24 — the environment's blue key/value block.

        Preposto resolution order:
          1. ``ambiente.preposto_id`` (explicit assignment)
          2. Any persona assigned to this ambiente with ``ruolo_preposto=True``
          3. Any azienda-level persona with ``ruolo_preposto=True``
          4. "Da nominare" — legally defensible placeholder per art. 19.
        """
        preposto_name: str | None = None
        preposto_id = getattr(ambiente, "preposto_id", None)
        if preposto_id and preposto_id in persone_by_id:
            preposto_name = persone_by_id[preposto_id].nominativo
        if not preposto_name:
            for pers in getattr(ambiente, "persone", None) or []:
                if getattr(pers, "ruolo_preposto", False):
                    preposto_name = pers.nominativo
                    break
        if not preposto_name:
            for pers in persone_by_id.values():
                if getattr(pers, "ruolo_preposto", False):
                    preposto_name = pers.nominativo
                    break
        preposto_name = (preposto_name or "Da nominare").upper()

        descrizione = (
            (ambiente.descrizione_attivita or "").strip()
            or (ambiente.tipo or "—")
        ).upper()

        rows: list[tuple[str, str]] = [
            ("Ambiente di lavoro", (ambiente.nome or "—").upper()),
            ("Tipologia", (ambiente.tipo or "—")),
        ]
        mq = getattr(ambiente, "superficie_mq", None)
        if mq:
            rows.append(("Metratura", f"{mq} mq"))
        rows.extend([
            ("Preposto per la sicurezza", preposto_name),
            ("Descrizione Attività", descrizione),
        ])
        self._add_key_value_table(doc, rows, variant="blue")

    def _add_env_addetti_table(
        self, doc: Document, ambiente, employee_persons: list
    ) -> None:
        """Template Table 25 — Nominativo / Mansione for addetti assigned to this env.

        Always emits the table shell so the per-env layout matches the
        template even when no persone_ambienti mapping exists yet; a single
        placeholder row signals the missing assignment to the operator.
        """
        addetti = _assigned_employee_persons(ambiente, employee_persons)
        if addetti:
            rows = [
                [(a.nominativo or "—").upper(), (a.mansione or "—").upper()]
                for a in addetti
            ]
        else:
            rows = [["—", "—"]]
        self._add_data_table(doc, headers=["Nominativo Addetti", "Mansione"], rows=rows)

    def _add_env_risk_checklist(self, doc: Document, ambiente) -> None:
        """Row 20c — Template Table 26: the SI/NO checklist of the 11 risk
        categories under their three macro-area rows.

        A category reads SI when at least one applicable valutazione_rischio
        of that categoria exists in this ambiente.
        """
        # Normalize short DB names ("Elettrici") to canonical long names
        # ("Impianti Elettrici") so the lookup against _CATEGORY_ORDER keys
        # actually matches. Without this every row silently shows NO.
        parents = list(
            getattr(ambiente, "valutazioni_rischio", None) or []
        )
        effective_by_parent = {
            id(parent): _effective_risk_sources(parent)
            for parent in parents
        }
        applicable_categories = {
            normalize_categoria_to_long(parent.categoria_rischio)
            for parent in parents
            if effective_by_parent[id(parent)]
        }

        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        header_row = table.rows[0]
        for cell, text in zip(header_row.cells, ["Categoria di Rischio", "Applicabile"]):
            _write_cell(cell, text)
        style_header_row(header_row)

        current_macro = None
        for macro, categoria in _CATEGORY_ORDER:
            if macro != current_macro:
                macro_row = table.add_row()
                merged = macro_row.cells[0].merge(macro_row.cells[1])
                _write_cell(merged, macro, bold=True, color=BRAND_NAVY)
                shade_cell(merged, BRAND_SURFACE_HEX)
                # A short label row: kept whole and with the first category.
                keep_row_together(macro_row)
                for paragraph in merged.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
                current_macro = macro

            row = table.add_row()
            _write_cell(row.cells[0], categoria)
            flag = "SI" if categoria in applicable_categories else "NO"
            _write_cell(row.cells[1], flag, align=_CENTER)
        set_table_borders(table)

    def _add_env_risk_tables(
        self,
        doc: Document,
        ambiente,
        vdt_count: int = 0,
        *,
        gestanti_allegato_presente: bool = False,
    ) -> None:
        """Row 20d — Template Tables 27+: one 5-col (PERICOLO/CONDIZIONI/
        RISCHIO/MISURE/I) table per applicable macro-category, in the
        canonical order, each on a new page under its caption.

        ``vdt_count``: when > 0, the Agenti Fisici table is force-emitted
        (even if no other agente fisico is applicable) and a synthetic VDT
        pericolo row is appended that references art. 174 D.Lgs. 81/2008
        and the Allegato VDT (audit F-007).
        """
        # Normalize short DB names to canonical long names so the per-category
        # tables actually emit (see _add_env_risk_checklist comment).
        parents = list(
            getattr(ambiente, "valutazioni_rischio", None) or []
        )
        effective_by_parent = {
            id(parent): _effective_risk_sources(parent)
            for parent in parents
        }
        by_category: dict[str, list] = {}
        for parent in parents:
            effective = effective_by_parent[id(parent)]
            if not effective:
                continue
            key = normalize_categoria_to_long(parent.categoria_rischio)
            if not key:
                continue
            by_category.setdefault(key, []).extend(effective)

        # Force the Agenti Fisici section when VDT addetti are present in
        # the ambiente — even if no other agente fisico has been ticked.
        if vdt_count > 0 and "Agenti Fisici" not in by_category:
            by_category["Agenti Fisici"] = []

        ordered_keys = [cat for _, cat in _CATEGORY_ORDER if cat in by_category]
        trailing = [k for k in by_category.keys() if k not in ordered_keys]

        if not ordered_keys and not trailing:
            notice = _italic_body(
                doc, "Nessun rischio applicabile identificato per questo ambiente."
            )
            notice.paragraph_format.space_before = Pt(12)
            return

        for cat_name in ordered_keys + trailing:
            inject_vdt = cat_name == "Agenti Fisici" and vdt_count > 0
            self._add_single_category_risk_table(
                doc,
                cat_name,
                by_category[cat_name],
                inject_vdt=inject_vdt,
                vdt_count=vdt_count,
                gestanti_allegato_presente=gestanti_allegato_presente,
            )

    def _add_single_category_risk_table(
        self,
        doc: Document,
        categoria: str,
        risks: list,
        inject_vdt: bool = False,
        vdt_count: int = 0,
        *,
        gestanti_allegato_presente: bool = False,
    ) -> None:
        """5-col risk table for a single category (Template Tables 27–33
        shape), on a new page under the category caption, which stays out
        of the index.

        When ``inject_vdt`` is True a synthetic videoterminali pericolo row
        is appended at the end. The synthetic row references art. 174
        D.Lgs. 81/2008 and the dedicated Allegato VDT and is scored
        P=2 D=2 I=6 MODESTO by default — operators tune the score in the
        Allegato VDT and the next regeneration picks up the real values.
        """
        add_sub_title(doc, categoria.upper(), in_toc=False, new_page=True)

        headers = [
            "PERICOLO",
            "CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE",
            "RISCHIO",
            "MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E DPI",
            # Mirrors the header used in the 54 risk-table cells of the N2O
            # template (DVR_TEMPLATE_MAPPING.md §"Risk assessment table column
            # structure"). The template writes the operands in this order in
            # its *tables* and as "I = 2*D + P" in its methodology *prose* —
            # both appear verbatim in the delivered DVR, matching the source
            # document. Same quantity either way; do not "normalize" one to
            # the other.
            "I = P + 2*D",
        ]

        # ``risks`` already contains the effective child rows (or a legacy
        # childless parent) selected by ``_add_env_risk_tables``.
        rows_to_emit = list(risks)

        # Synthetic VDT row when none of the existing children already
        # cover videoterminali — keeps the row dedupe-safe.
        if inject_vdt:
            already_covers_vdt = any(
                "videoterminal" in (getattr(r, "pericolo", "") or "").lower()
                for r in rows_to_emit
            )
            if not already_covers_vdt:
                from types import SimpleNamespace
                rows_to_emit.append(SimpleNamespace(
                    pericolo="Esposizione a videoterminali (VDT)",
                    condizioni_esposizione=(
                        f"{vdt_count} lavoratore/i con uso del VDT >= 20 "
                        "ore/settimana ai sensi dell'art. 173 D.Lgs. 81/08."
                    ),
                    rischio=(
                        "Affaticamento visivo, disturbi muscoloscheletrici, "
                        "stress correlato all'uso prolungato del VDT."
                    ),
                    misure_prevenzione=(
                        "Postazioni conformi all'allegato XXXIV; pause di "
                        "15 min ogni 120 min di applicazione continuativa; "
                        "sorveglianza sanitaria mirata. Vedi Allegato "
                        "Videoterminali (VDT)."
                    ),
                    probabilita_p=2,
                    danno_d=2,
                    valutazione_riferimento=None,
                ))

        rows: list[list[str]] = []
        levels: list[str | None] = []
        for source in rows_to_emit:
            p_val = source.probabilita_p
            d_val = source.danno_d
            riferimento = _normalize_special_riferimento(
                getattr(source, "valutazione_riferimento", None),
                gestanti_allegato_presente=gestanti_allegato_presente,
            )
            if p_val is not None and d_val is not None:
                result = calculate_risk_index(p_val, d_val)
                livello = result["livello_rischio"]
                indice_text = f"P = {p_val}; D = {d_val}; I = {result['indice_i']}; {livello}"
            elif riferimento:
                livello = None
                indice_text = riferimento
            else:
                livello = None
                indice_text = "—"
            rows.append([
                source.pericolo or "—",
                source.condizioni_esposizione or "—",
                source.rischio or "—",
                source.misure_prevenzione or "—",
                indice_text,
            ])
            levels.append(livello)

        table = self._add_data_table(
            doc, headers, rows, widths=[3.0, 3.3, 2.9, 4.3, 3.0], v_center=False
        )
        for row, livello in zip(table.rows[1:], levels):
            index_cell = row.cells[4]
            index_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in index_cell.paragraphs:
                paragraph.alignment = _CENTER
            if livello:
                level_cell(index_cell, livello)

    # ------------------------------------------------------------------
    # Parte IV — rows 25–28 (Template Tables 108, 109, 110)
    # ------------------------------------------------------------------

    def _add_part_iv(
        self,
        doc: Document,
        azienda,
        persone: list,
        employee_persons: list,
        extras: dict,
        generated_at: datetime | None = None,
    ) -> None:
        """Parte IV — PROGRAMMA DI MIGLIORAMENTO, every section on a divider
        (DVR_TEMPLATE_MAPPING.md §10):

          row 25  PROGRAMMA E PROCEDURE DI ATTUAZIONE DELLE MISURE DI
                  MIGLIORAMENTO under the part label: intro + Table 109
          row 26  the 11 GESTIONE procedures (the template's §4.2–4.12);
                  GESTIONE SORVEGLIANZA SANITARIA adds the per-mansione
                  protocol and the occupational diseases
          row 27  DOCUMENTI CORRELATI AL PRESENTE DVR
          row 28  DICHIARAZIONE DEL DATORE DI LAVORO and the signature grid
                  (Table 110)
        """
        add_divider(
            doc, _IMPROVEMENT_TITLE, "div_miglioramento", part_label=_PART_IV_LABEL
        )
        intro = _italic_body(
            doc,
            "Il programma di miglioramento è definito sulla base delle "
            "criticità emerse dalla valutazione dei rischi. Le misure sono "
            "ordinate per priorità in funzione del livello di rischio: "
            "rischi GRAVISSIMI (I >= 9) richiedono intervento immediato, "
            "rischi GRAVI (I = 7-8) entro sei mesi, rischi MODESTI o "
            "ACCETTABILI sono pianificati nel ciclo annuale di revisione.",
        )
        intro.paragraph_format.space_after = Pt(10)
        self._add_improvement_program_table(
            doc, extras.get("misure_miglioramento") or []
        )

        # Row 26. GESTIONE SORVEGLIANZA SANITARIA carries the mansione-level
        # protocol table aggregated from per-persona DPI + rischi flags
        # (audit recommendation, post-fix 2026-04-29; persona-level data
        # 2026-04-30).
        for spec in _PART_IV_PROCEDURAL_SECTIONS:
            self._add_procedural_section(doc, spec)
            if spec.art_key == "div_sorveglianza":
                self._add_sorveglianza_protocol_table(
                    doc,
                    employee_persons,
                    (extras.get("protocolli_sanitari") or [])
                    if PROTOCOLLO_SANITARIO_ATTIVO
                    else [],
                )

        # Row 27 — applicable allegati by name (audit F-016).
        self._add_allegati_cross_references(
            doc, extras.get("allegati_presenti") or []
        )

        # Row 28 — the binding declaration and the signature grid.
        self._add_dichiarazione_ddl(doc, azienda, persone, generated_at)
        self._add_signature_table(doc, persone)

    def _add_sorveglianza_protocol_table(
        self, doc: Document, persone: list, protocolli: list | None = None
    ) -> None:
        """Render the per-mansione Sorveglianza Sanitaria protocol table,
        aggregating per-persona DPI + rischi flags up to mansione (union),
        followed by the "Malattie professionali correlate" table.

        4 columns: Mansione | Rischi specifici | DPI assegnati | Periodicità
        (compilata dal Medico Competente). When a saved protocollo
        sanitario exists for the mansione (``protocolli``, rows of
        ``ProtocolloSanitarioMansione`` loaded by ``_load_dvr_extras``) the
        last column shows its periodicità and accertamenti; otherwise it
        stays the "[DA COMPILARE — MC]" scaffold, because the cadence is a
        medical decision the MC must make per mansione (art. 41 D.Lgs.
        81/2008) and we do not invent values that look authoritative.

        The second table lists, per mansione, the occupational diseases the
        role is exposed to: the saved ``malattie_correlate`` when a protocol
        exists, else the reference-table rows matching the mansione's rischi
        codes (D.M. 9/4/2008), explicitly marked "da confermare dal MC".
        Risks, DPI and diseases are bulleted lists in their cells.

        Falls back to a transparent "no data" paragraph when no persona
        carries any DPI/rischi flags and no protocol is saved.
        """
        from app.data.malattie_professionali import malattie_per_rischi
        from app.services.reference_data import (
            DPI_CATALOG,
            RISCHI_SPECIFICI_CATALOG,
        )

        add_sub_title(doc, "Protocollo di Sorveglianza Sanitaria per Mansione")

        # Aggregate per-persona codes up to mansione (union), keyed
        # case-insensitively so "Saldatore" and "saldatore" are one row.
        display: dict[str, str] = {}
        mansione_dpi: dict[str, set[str]] = {}
        mansione_rischi: dict[str, set[str]] = {}
        for p in persone:
            nome = " ".join((p.mansione or "").split())
            if not nome:
                continue
            key = nome.lower()
            display.setdefault(key, nome)
            dpi_codes = list(getattr(p, "dpi_codes", None) or [])
            rs_codes = list(getattr(p, "rischi_specifici_codes", None) or [])
            if dpi_codes:
                mansione_dpi.setdefault(key, set()).update(dpi_codes)
            if rs_codes:
                mansione_rischi.setdefault(key, set()).update(rs_codes)

        saved: dict[str, object] = {}
        for prot in protocolli or []:
            nome = " ".join((getattr(prot, "mansione", None) or "").split())
            if not nome:
                continue
            key = nome.lower()
            saved[key] = prot
            display.setdefault(key, nome)
            # The protocol's own snapshot keeps the row meaningful even when
            # the persone flags were cleared after the MC reviewed it.
            for item in getattr(prot, "rischi_specifici", None) or []:
                code = item.get("code") if isinstance(item, dict) else None
                if code:
                    mansione_rischi.setdefault(key, set()).add(code)

        all_keys = sorted(
            set(mansione_dpi) | set(mansione_rischi) | set(saved),
            key=lambda k: display[k],
        )

        if not all_keys:
            _italic_body(
                doc,
                "Nessuna mansione con sorveglianza sanitaria configurata. "
                "Il Medico Competente, in fase di nomina, definirà il "
                "protocollo specifico per le mansioni esposte ai rischi "
                "previsti dalla normativa.",
            )
            return

        lists: list[tuple[list[str], list[str]]] = []
        rows: list[list[str]] = []
        for key in all_keys:
            rischi_labels = sorted(
                RISCHI_SPECIFICI_CATALOG.get(c, {}).get("etichetta", c)
                for c in mansione_rischi.get(key, set())
            )
            dpi_labels = sorted(
                DPI_CATALOG.get(c, {}).get("etichetta", c)
                for c in mansione_dpi.get(key, set())
            )
            lists.append((rischi_labels, dpi_labels))
            rows.append([
                display[key].upper(),
                "",
                "",
                _format_protocol_periodicita_cell(saved.get(key)),
            ])

        table = self._add_data_table(
            doc,
            ["Mansione", "Rischi specifici", "DPI assegnati", "Periodicità (compilata dal MC)"],
            rows,
            widths=[3.4, 4.9, 4.2, 4.0],
        )
        for row, (rischi_labels, dpi_labels) in zip(table.rows[1:], lists):
            _bullet_cell(row.cells[1], rischi_labels)
            _bullet_cell(row.cells[2], dpi_labels)
        # Footnote clarifying authority for the periodicità column.
        _note(
            doc,
            "Nota: la periodicità della sorveglianza sanitaria e i "
            "protocolli specifici sono definiti dal Medico Competente in "
            "sede di nomina e di prima visita, ai sensi dell'art. 41 "
            "D.Lgs. 81/2008.",
        )

        # --- Malattie professionali correlate per mansione ---------------
        add_sub_title(doc, "Malattie professionali correlate per mansione")
        diseases: list[list[str] | str] = []
        rows2: list[list[str]] = []
        for key in all_keys:
            nome = display[key]
            prot = saved.get(key)
            saved_malattie = [
                m for m in (getattr(prot, "malattie_correlate", None) or [])
                if isinstance(m, dict) and (m.get("malattia") or "").strip()
            ] if prot is not None else []
            if saved_malattie:
                refs = _unique_keep_order(
                    (m.get("riferimento") or "").strip() for m in saved_malattie
                )
                diseases.append([m["malattia"].strip() for m in saved_malattie])
                rows2.append([nome.upper(), "", "; ".join(refs) if refs else "—"])
                continue
            ref_rows = malattie_per_rischi(mansione_rischi.get(key, set()))
            if ref_rows:
                refs = _unique_keep_order(r["tabella"] for r in ref_rows)
                diseases.append([r["malattia"] for r in ref_rows])
                rows2.append([nome.upper(), "", "; ".join(refs) + " — da confermare dal MC"])
            else:
                diseases.append(
                    "Nessuna malattia tabellata correlata ai rischi specifici censiti"
                )
                rows2.append([nome.upper(), "", "da confermare dal MC"])
        table2 = self._add_data_table(
            doc,
            ["Mansione", "Malattie correlate", "Riferimento tabellare"],
            rows2,
            widths=[3.4, 8.6, 4.5],
        )
        for row, entry in zip(table2.rows[1:], diseases):
            if isinstance(entry, list):
                _bullet_cell(row.cells[1], entry)
            else:
                _write_cell(row.cells[1], entry)
        _note(
            doc,
            "Fonte: D.M. 9 aprile 2008 (tabelle delle malattie professionali "
            "nell'industria e nell'agricoltura) e D.M. 10 giugno 2014 (elenco "
            "delle malattie con obbligo di denuncia ex art. 139 DPR 1124/1965). "
            "Le voci contrassegnate \"da confermare dal MC\" derivano dai rischi "
            "specifici censiti per la mansione e non da un giudizio medico.",
        )

    def _add_allegati_cross_references(
        self, doc: Document, allegati: list[tuple[str, str]]
    ) -> None:
        """Row 27 — DOCUMENTI CORRELATI AL PRESENTE DVR, on its own divider:
        each applicable allegato named verbatim in a navy bold bulleted list
        (audit F-016 / H16).

        The allegati list is computed in ``_load_dvr_extras`` from the actual
        assessment rows on this azienda, so the section only references
        documents that genuinely exist for this client.
        """
        add_divider(doc, "DOCUMENTI CORRELATI AL PRESENTE DVR", "div_ambienti")

        if not allegati:
            _italic_body(
                doc,
                "Nessun allegato di approfondimento applicabile sulla base "
                "delle valutazioni effettuate. La presente valutazione "
                "generale copre la totalità dei rischi rilevati.",
            )
            return

        add_body_paragraph(
            doc,
            "Costituiscono parte integrante del presente DVR i seguenti "
            "allegati di approfondimento, redatti secondo le metodologie "
            "previste dalla normativa di riferimento:",
        )
        for bullet in add_bullets(doc, [label for _slug, label in allegati]):
            for run in bullet.runs:
                set_run_font(run, bold=True, color=BRAND_NAVY)

    def _add_procedural_section(
        self, doc: Document, spec: "_ProceduralSection"
    ) -> None:
        """Row 26 — one GESTIONE procedure: its divider, the intro
        paragraph(s), an optional bulleted list and the "Documentazione
        collegata" line.
        """
        add_divider(doc, spec.heading, spec.art_key)
        for para in spec.body:
            add_body_paragraph(doc, para)
        if spec.bullets:
            add_bullets(doc, list(spec.bullets))
        if spec.docs:
            line = doc.add_paragraph()
            line.paragraph_format.space_before = Pt(6)
            set_run_font(line.add_run("Documentazione collegata: "), bold=True, italic=True)
            set_run_font(line.add_run("; ".join(spec.docs) + "."), italic=True)

    def _add_dichiarazione_ddl(
        self,
        doc: Document,
        azienda,
        persone: list,
        generated_at: datetime | None = None,
    ) -> None:
        """Row 28 — the binding declaration signed by the Datore di Lavoro,
        on its own divider.

        Names the actual DdL and ragione sociale and stamps luogo + data
        of redazione, mirroring the template's #2429 paragraph block, with
        "DICHIARA" and "‹COMUNE›, lì ‹data›" in bold navy as in N2O's model.
        """
        add_divider(doc, "DICHIARAZIONE DEL DATORE DI LAVORO", "div_dichiarazione")

        ddl = next((p for p in persone if p.ruolo_datore_lavoro), None)
        ddl_name = (ddl.nominativo if ddl and ddl.nominativo else "________________________").upper()
        rs = (azienda.ragione_sociale or "________________________").upper()

        add_body_paragraph(
            doc,
            f"Il/la sottoscritto/a, {ddl_name}, in qualità di Datore di "
            f"Lavoro della {rs}, ai sensi e per gli effetti dell'art. 28 "
            "del D.Lgs. 81/2008 e s.m.i.,",
        )

        dichiara = doc.add_paragraph()
        dichiara.alignment = _CENTER
        dichiara.paragraph_format.space_before = Pt(18)
        dichiara.paragraph_format.space_after = Pt(18)
        dichiara.paragraph_format.keep_with_next = True
        set_run_font(dichiara.add_run("DICHIARA"), bold=True, color=BRAND_NAVY)

        last_clause = None
        for clause in (
            "che il procedimento di valutazione dei rischi ex art. 17, "
            "comma 1, lettera a) del D.Lgs. 81/2008 e s.m.i. è stato "
            "effettuato in collaborazione con il RSPP, il Medico "
            "Competente (ove nominato) e previa consultazione del RLS;",
            "che la valutazione e tutti i suoi aggiornamenti sono "
            "documentati nel presente DVR, conservato presso l'unità "
            "produttiva e reso disponibile per la consultazione ai "
            "soggetti previsti dalla legge;",
            # The programme is named by its part: the sections are
            # unnumbered since N2O's model.
            "di aver individuato e descritto le misure di prevenzione e "
            "protezione attuate e di aver definito il programma delle "
            "misure di miglioramento riportato nella Parte IV;",
            "di impegnarsi a rielaborare la valutazione nei casi previsti "
            "dall'art. 29, comma 3 del D.Lgs. 81/2008 e s.m.i. "
            "(modifiche significative del processo produttivo, "
            "infortuni, evoluzione normativa, esiti della sorveglianza "
            "sanitaria).",
        ):
            last_clause = add_body_paragraph(doc, clause)

        if last_clause is not None:
            last_clause.paragraph_format.keep_with_next = True

        # Luogo, data — derived from sede operativa (or legale) and the
        # document's date, the one the footer's "Rev. NN del …" prints.
        citta = (
            azienda.sede_operativa_citta
            or azienda.sede_legale_citta
            or "_____________"
        )
        oggi = (generated_at or datetime.now(timezone.utc)).strftime("%d/%m/%Y")
        luogo_data = doc.add_paragraph()
        luogo_data.paragraph_format.space_before = Pt(18)
        luogo_data.paragraph_format.space_after = Pt(14)
        luogo_data.paragraph_format.keep_with_next = True
        set_run_font(luogo_data.add_run(f"{citta}, lì {oggi}"), bold=True, color=BRAND_NAVY)

    def _add_improvement_program_table(
        self, doc: Document, misure: list
    ) -> None:
        """Row 25 — Template Table 109 in N2O's four columns, portrait:
        Misura di Miglioramento | Risorse | Responsabile | Priorità, the
        priority coloured like a risk level.

        Rischio, Attività / Procedura and Scadenza left the printed table;
        their data stays in the database and the app (spec §4.2.2: the
        intro maps priority to timing for art. 28 c.2 lett. c, Responsabile
        and the GESTIONE procedures cover lett. d). A row whose concrete
        measure is still empty prints its risk-reduction text rather than a
        dash.

        When ``misure`` is empty the operator has actively cleared all
        rows — a single italic placeholder row keeps the table and flags it
        as not legally complete.
        """
        headers = ["Misura di Miglioramento", "Risorse", "Responsabile", "Priorità"]
        widths = [7.3, 3.4, 3.3, 2.5]
        if not misure:
            table = self._add_data_table(
                doc, headers, [["[Nessuna misura inserita]", "—", "—", "—"]], widths=widths
            )
            for run in table.rows[1].cells[0].paragraphs[0].runs:
                set_run_font(run, italic=True, color=NOTE_GREY)
            return

        rows = [
            [
                (m.misura_miglioramento or "").strip() or (m.misura or "").strip() or "—",
                m.risorse or "—",
                m.responsabile or "—",
                m.priorita or "—",
            ]
            for m in sorted(misure, key=_saved_order_key)
        ]
        table = self._add_data_table(doc, headers, rows, widths=widths)
        for row in table.rows[1:]:
            cell = row.cells[3]
            priorita = cell.text.strip().upper()
            level_cell(cell, _PRIORITY_LEVELS.get(priorita, priorita))

    def _add_signature_table(self, doc: Document, persone: list) -> None:
        """Template Table 110 — the 2×2 signature grid of N2O's model:
        Datore di Lavoro and Responsabile del S.P.P. over Medico Competente
        and RLS, each role in white on navy over the holder's name ("—"
        when vacant: the grid never shrinks) and a 2.5 cm row to sign in.
        """
        def _first(pred) -> str:
            match = next((p for p in persone if pred(p)), None)
            return ((match.nominativo or "") if match else "").upper()

        add_signature_grid(doc, [
            ("Datore di Lavoro", _first(lambda p: p.ruolo_datore_lavoro)),
            ("Responsabile del S.P.P.", _first(lambda p: p.ruolo_rspp)),
            ("Medico Competente", _first(lambda p: getattr(p, "ruolo_medico_competente", False))),
            ("RLS", _first(lambda p: p.ruolo_rls)),
        ])

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _split_descrizione_paragraphs(text: str) -> list[str]:
        """Split a free-form descrizione_attivita into 1-N paragraphs.

        Splits on (a) blank-line separators if present, otherwise (b) into
        chunks of ~3 sentences each so a long single-paragraph string
        becomes a paragraph-formatted narrative. Empty inputs return [].
        """
        text = (text or "").strip()
        if not text:
            return []
        # Honor explicit blank-line splits first.
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        if len(blocks) > 1:
            return blocks
        # Otherwise group sentences into chunks of 3.
        sentences = re.split(r"(?<=[\.!\?])\s+", text)
        chunks: list[str] = []
        buf: list[str] = []
        for s in sentences:
            buf.append(s)
            if len(buf) >= 3:
                chunks.append(" ".join(buf).strip())
                buf = []
        if buf:
            chunks.append(" ".join(buf).strip())
        return chunks or [text]

    def _format_address(
        self,
        via: str | None,
        citta: str | None,
        cap: str | None = None,
        provincia: str | None = None,
    ) -> str:
        """Format an Italian postal address as ``Via, CAP Comune (PROV)``.

        CAP and provincia are folded into the comune segment so the rendered
        address matches the conventional Italian layout an inspector expects
        (e.g. ``Via Verona 1/A, 20063 Cernusco sul Naviglio (MI)``). Every
        component is optional — missing parts are skipped without leaving
        stray separators or an orphan ``(PROV)``. Audit F-301 (2026-05-31):
        previously only ``via`` + ``città`` were emitted, silently dropping
        the CAP and province that are present on the azienda row.
        """
        citta_seg = (citta or "").strip()
        cap = (cap or "").strip()
        provincia = (provincia or "").strip()
        if cap and citta_seg:
            citta_seg = f"{cap} {citta_seg}"
        elif cap:
            citta_seg = cap
        if provincia and citta_seg:
            citta_seg = f"{citta_seg} ({provincia})"
        parts = [p for p in [(via or "").strip(), citta_seg] if p]
        return ", ".join(parts) if parts else "—"

    def _format_seat_lines(
        self,
        via: str | None,
        citta: str | None,
        cap: str | None = None,
        provincia: str | None = None,
    ) -> str:
        """A seat on two lines — the street, then "CAP Comune (PROV)" — the
        way the identity strips of N2O's model print it; "—" when empty."""
        comune = self._format_address(None, citta, cap, provincia)
        lines = [
            line
            for line in ((via or "").strip(), comune if comune != "—" else "")
            if line
        ]
        return "\n".join(lines) if lines else "—"

    def _add_key_value_table(
        self, doc: Document, rows: list[tuple[str, str]], *, variant: str = "blue"
    ) -> Table:
        """A two-column key/value table, built by the kit's ``add_kv_table``:
        ``"blue"`` labels (white on the table blue) for the Anagrafica and
        the environment identity, ``"light"`` (navy on the light surface)
        for the identity strips. Label and value are centred vertically, so
        a label faces a two-line seat the way it does in N2O's model. A
        short pair never splits across a page break — the label dangling
        alone was the most jarring case in operator feedback (2026-05-12)."""
        table = add_kv_table(doc, rows, variant=variant)
        _center_vertically(table.rows)
        return table

    def _add_data_table(
        self,
        doc: Document,
        headers: list[str],
        rows: list[list[str]],
        *,
        widths: list[float] | None = None,
        v_center: bool = True,
    ) -> Table:
        """A data table, built by the kit's ``add_data_table``: the blue
        header row repeats on every page and never splits, zebra rows, 10 pt
        text with numbers, levels and dashes centred. Data rows may split:
        a keep-together row taller than a page makes LibreOffice loop forever
        (commit e0875fa). ``widths`` are column widths in cm.

        ``v_center`` centres the data cells vertically, as N2O's model does
        next to bulleted lists and multi-line cells; the risk tables keep
        their text at the top, like the model's.
        """
        table = add_data_table(doc, headers, rows, column_widths_cm=widths)
        if v_center:
            _center_vertically(table.rows[1:])
        return table
