"""Build and audit a synthetic DVR Master integration fixture.

The harness deliberately avoids database and customer inputs.  It exercises the
complete existing Acme fixture and a richer, deterministic fixture containing
only fictional identities and generated image pixels.
"""

import argparse
import asyncio
import importlib
import json
import re
import shutil
import sys
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import pillow_heif
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw

from app.services.ambiente_photo import normalize_document_image
from app.services.document_generator.design import art_marker, section_first_blocks
from app.services.document_generator.docx_utils import BRAND_NAVY_HEX, RISK_COLORS
from app.services.document_generator.dvr_master import (
    DVRMasterGenerator,
    _saved_order_key,
)
from scripts.verify_all_generators import build_fixture, mk, patch_generators, run_one

_H1_HEADINGS = [
    "INDICE",
    "Premessa",
    "PARTE I — DATI GENERALI DELL'AZIENDA",
    "PARTE II — METODOLOGIA DI VALUTAZIONE",
    "PARTE III — VALUTAZIONE DEI RISCHI PER AMBIENTE DI LAVORO",
    "PARTE IV — PROGRAMMA DI MIGLIORAMENTO",
]
# The DVR cover is the VERA artwork of N2O's model (cover_dvr.jpg): pinned
# by hash, so swapping the asset file and its embedding together still fails.
_VERA_COVER_SHA256 = (
    "c2aba6d2c7b38ee3aed5b65b3c34b9636b0c4f76633d40056aa7abae2eb0b07a"
)
_VERA_COVER_DIMENSIONS = (1054, 1491)
_REPORT_KEYS = (
    "acme_regression",
    "vera_cover",
    "saved_people_order",
    "saved_environment_order",
    "external_roles",
    "grouped_equipment",
    "all_ten_photos",
    "effective_risks",
    "person_specific_risks",
    "dpi_dash_alignment",
    "topic_separators",
    "complete_improvements",
    "declaration_signatures",
    # Page map of N2O's 20 Oct model (spec §4.2.1).
    "page_map_dividers",
    "in_page_titles",
    "part_ii_renamed",
    "split_people_tables",
    "improvement_table_4_cols",
    "no_repeated_azienda_table",
    "no_photo_captions",
    "sign_panels",
    "signature_grid",
    "cover_and_back_art",
    "company_photo",
)

# ---------------------------------------------------------------------------
# The page map (spec §4.2.1), written out here rather than imported from the
# generator so the audit checks the generator against the spec, not against
# itself.
# ---------------------------------------------------------------------------

_PART_II_LABEL = "PARTE II — METODOLOGIA DI VALUTAZIONE"
_LEGACY_PART_II_LABEL = (
    "PARTE II — DESCRIZIONE DELL'ATTIVITÀ E METODOLOGIA DI VALUTAZIONE"
)
# Rows 4–10 and 15–18: in-page titles (Heading 2, page break before).
_IN_PAGE_TITLES = (
    "DOCUMENTO ELABORATO SUGLI ESITI DELLA VALUTAZIONE DEI RISCHI",
    "PRESENTAZIONE DELL'AZIENDA",
    "ANAGRAFICA AZIENDALE",
    "DATI ANAGRAFICI",
    "DATI OCCUPAZIONALI",
    "ORGANIZZAZIONE AZIENDALE DELLA SICUREZZA",
    "AMBIENTI DI LAVORO",
    "DEFINIZIONI",
    "METODOLOGIA DI VALUTAZIONE DEI RISCHI",
    "SCALA DI PROBABILITÀ (P)",
    "SCALA DEL DANNO (D)",
)
# Rows 11–14, 19, 21–28: (art key, title) of the 23 divider pages, in order.
_PAGE_MAP_DIVIDERS = (
    ("div_servizi_igienici", "SERVIZI IGIENICO-ASSISTENZIALI"),
    ("div_macchine", "MACCHINE, ATTREZZATURE ED IMPIANTI"),
    ("div_sostanze", "SOSTANZE, PRODOTTI E PREPARATI CHIMICI"),
    ("div_fattori_pericolo", "ELENCO FATTORI DI PERICOLO (Riferimento)"),
    ("div_ambienti", "IDENTIFICAZIONE DELL'AMBIENTE DI LAVORO E DEGLI ADDETTI"),
    ("div_mansioni", "MANSIONI CHE ESPONGONO I LAVORATORI A RISCHI SPECIFICI"),
    ("div_dpi", "DISPOSITIVI DI PROTEZIONE INDIVIDUALE (DPI)"),
    ("div_segnaletica", "SEGNALETICA DI SICUREZZA"),
    ("div_formazione", "PROGRAMMA DI INFORMAZIONE, FORMAZIONE E ADDESTRAMENTO"),
    (
        "div_miglioramento",
        "PROGRAMMA E PROCEDURE DI ATTUAZIONE DELLE MISURE DI MIGLIORAMENTO",
    ),
    ("div_leggi", "GESTIONE LEGGI E REGOLAMENTI"),
    ("div_sorveglianza", "GESTIONE SORVEGLIANZA SANITARIA"),
    ("div_formazione", "GESTIONE INFORMAZIONE, FORMAZIONE ED ADDESTRAMENTO"),
    ("div_riunione", "RIUNIONE PERIODICA"),
    ("div_infortuni", "GESTIONE DEGLI INFORTUNI"),
    ("div_comportamenti", "GESTIONE COMPORTAMENTI SCORRETTI DEI LAVORATORI"),
    ("div_gestione_dpi", "GESTIONE DPI"),
    ("div_infrastrutture", "GESTIONE INFRASTRUTTURE"),
    (
        "div_sensibili",
        "GESTIONE DEI LAVORATORI PARTICOLARMENTE SENSIBILI AL RISCHIO",
    ),
    ("div_acquisti", "GESTIONE ACQUISTI"),
    ("div_appalti", "GESTIONE DELLE LAVORAZIONI AFFIDATE IN APPALTO"),
    ("div_ambienti", "DOCUMENTI CORRELATI AL PRESENTE DVR"),
    ("div_dichiarazione", "DICHIARAZIONE DEL DATORE DI LAVORO"),
)
_DIVIDER_TITLES = tuple(title for _key, title in _PAGE_MAP_DIVIDERS)
# Row 23: the five sign panels after FORMA E CATEGORIE DEI CARTELLI.
_SIGN_PANELS = (
    ("sign_divieto", "CARTELLI DI DIVIETO"),
    ("sign_avvertimento", "CARTELLI DI AVVERTIMENTO"),
    ("sign_obbligo", "CARTELLI DI OBBLIGO"),
    ("sign_emergenza", "SEGNALI DI EMERGENZA ED EVACUAZIONE"),
    ("sign_antincendio", "SEGNALI DI PREVENZIONE INCENDI"),
)
_SIGN_PANEL_WIDTH = Cm(15.3)
_SIGNATURE_ROLES = (
    "Datore di Lavoro",
    "Responsabile del S.P.P.",
    "Medico Competente",
    "RLS",
)
_DATI_ANAGRAFICI_HEADERS = ["Nominativo", "Codice Fiscale", "Tipologia contrattuale"]
_DATI_OCCUPAZIONALI_HEADERS = ["Nominativo", "Mansione", "Ambiente di Lavoro"]
_IMPROVEMENT_HEADERS = ["Misura di Miglioramento", "Risorse", "Responsabile", "Priorità"]
_ART_DIR = BACKEND_ROOT / "assets" / "document_art"
_NUMBERED_HEADING = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s")
_PHOTO_CAPTION = re.compile(r"^Fig\. \d+ — ")
# The company photo's box on PRESENTAZIONE DELL'AZIENDA (spec §4.2.1 row 5).
_COMPANY_PHOTO_MAX = (Cm(16.5), Cm(11))


def _image_bytes(image: Image.Image, image_format: str) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def _company_photo_bytes() -> bytes:
    """A fictional 4:3 "office" drawn with PIL: no real premises or people.

    4:3 does not fit the 16.5 × 11 cm slot by width, so the audit also proves
    the generator scales to the height and keeps the aspect ratio.
    """
    image = Image.new("RGB", (480, 360), (232, 238, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 250, 479, 359), fill=(180, 186, 196))
    draw.rectangle((40, 60, 180, 200), fill=(150, 190, 230))
    draw.rectangle((230, 170, 440, 260), fill=(120, 90, 60))
    return _image_bytes(image, "JPEG")


def _next_paragraph_has_page_break(paragraph) -> bool:
    following = paragraph._p.getnext()
    return bool(
        following is not None
        and following.xpath('.//w:br[@w:type="page"]')
    )


def _assign_order_metadata(items: list, *, first_uuid: int) -> None:
    for index, item in enumerate(items):
        item.id = uuid.UUID(int=first_uuid + index)
        item.ordine = index
        item.created_at = datetime(2026, 1, index + 1)


def build_acme_fixture() -> dict:
    """Return the existing full Acme fixture with deterministic saved order."""
    fixture = build_fixture()
    fixture["azienda"].id = uuid.UUID(int=100)
    fixture["azienda"].organization_id = uuid.UUID(int=101)
    fixture["generated_at"] = datetime(2026, 8, 3, 9, 0, 0)
    _assign_order_metadata(fixture["ambienti"], first_uuid=200)
    _assign_order_metadata(fixture["persone"], first_uuid=300)
    _assign_order_metadata(fixture["attrezzature"], first_uuid=400)
    _assign_order_metadata(fixture["sostanze_chimiche"], first_uuid=500)
    for environment_index, environment in enumerate(fixture["ambienti"]):
        _assign_order_metadata(
            environment.valutazioni_rischio,
            first_uuid=600 + environment_index * 10,
        )

    # DATI ANAGRAFICI: Nominativo | Codice Fiscale | Tipologia contrattuale.
    fixture["expected_anagrafici_rows"] = [
        ["MARIO ROSSI", "—", "—"],
        ["LUCA BIANCHI", "—", "—"],
        ["GIULIA VERDI", "—", "—"],
        ["ANTONIO MARRONE", "—", "—"],
        ["VALENTINA RINALDI", "—", "—"],
    ]
    # DATI OCCUPAZIONALI: Nominativo | Mansione | Ambiente di Lavoro.
    fixture["expected_people_rows"] = [
        ["MARIO ROSSI", "DATORE DI LAVORO", "TUTTA L'AZIENDA (RUOLO TRASVERSALE)"],
        ["LUCA BIANCHI", "RSPP", "TUTTA L'AZIENDA (RUOLO TRASVERSALE)"],
        ["GIULIA VERDI", "RLS", "TUTTA L'AZIENDA (RUOLO TRASVERSALE)"],
        ["ANTONIO MARRONE", "OPERAIO TORNITORE", "—"],
        ["VALENTINA RINALDI", "IMPIEGATA (GESTANTE)", "—"],
    ]
    fixture["expected_environments"] = [
        "UFFICI AMMINISTRATIVI E TECNICI",
        "OFFICINA MECCANICA",
        "MAGAZZINO",
        "MENSA AZIENDALE CON CUCINA",
        "DEPOSITO CHIMICI",
        "AREA ESTERNA",
    ]
    fixture["expected_environment_rows"] = [
        ["UFFICI AMMINISTRATIVI E TECNICI", "Ufficio", "220 mq", "0"],
        ["OFFICINA MECCANICA", "Officina", "850 mq", "0"],
        ["MAGAZZINO", "Magazzino", "620 mq", "0"],
        ["MENSA AZIENDALE CON CUCINA", "Cucina", "180 mq", "0"],
        ["DEPOSITO CHIMICI", "Magazzino", "90 mq", "0"],
        ["AREA ESTERNA", "Esterno", "440 mq", "0"],
    ]
    fixture["expected_global_equipment_rows"] = [
        ["TORNIO PARALLELO CNC", "—", "SI", "SI"],
        ["FRESATRICE CNC", "—", "SI", "SI"],
        ["CARRELLO ELEVATORE", "—", "SI", "SI"],
        ["POSTAZIONE VDT", "—", "SI", "NO"],
    ]
    # (rows, columns) of every table. Against the pre-model layout: the
    # identity strip prints twice instead of five times (2×2, Acme has no
    # operative seat), the 5-column roster is DATI ANAGRAFICI + DATI
    # OCCUPAZIONALI (6×3 each), the signature table is the 2×2 grid (6×2)
    # and the improvement table has 4 columns.
    fixture["expected_table_inventory"] = {
        "total": 69,
        "dimensions": Counter(
            {
                (2, 1): 5,
                (2, 2): 8,
                (2, 3): 12,
                (2, 4): 1,
                (2, 5): 12,
                (3, 2): 2,
                (3, 6): 1,
                (5, 2): 6,
                (5, 3): 2,
                (5, 4): 2,
                (6, 2): 1,
                (6, 3): 2,
                (7, 4): 3,
                (9, 2): 1,
                (10, 5): 1,
                (15, 2): 6,
                (16, 2): 1,
                (17, 2): 1,
                (28, 2): 1,
                (33, 2): 1,
            }
        ),
    }
    return fixture


def build_luca_fixture() -> dict:
    """Return a deterministic, wholly synthetic staging-equivalent fixture."""
    fixture = build_acme_fixture()
    fixture["azienda"].ragione_sociale = "LUCA FIXTURE INDUSTRIA SRL"
    fixture["generated_at"] = datetime(2026, 8, 3, 9, 0, 0)
    zulu_env, alpha_env = fixture["ambienti"][:2]
    zulu_env.nome = "Zulu Reparto"
    zulu_env.ordine = 1
    zulu_env.created_at = datetime(2026, 1, 1)
    alpha_env.nome = "Alpha Reparto"
    alpha_env.ordine = 2
    alpha_env.created_at = datetime(2026, 1, 2)
    fixture["ambienti"] = [alpha_env, zulu_env]

    ddl = mk(
        id=uuid.UUID(int=700),
        nominativo="Datore Fixture",
        mansione="Datore",
        ordine=0,
        created_at=datetime(2026, 1, 1),
        is_esterno=False,
        ruolo_datore_lavoro=True,
        ruolo_rspp=False,
        ruolo_rls=False,
        ruolo_medico_competente=False,
        ruolo_primo_soccorso=False,
        ruolo_antincendio=False,
        ruolo_preposto=False,
        ambienti=[zulu_env, alpha_env],
        dpi_codes=[],
        rischi_specifici_codes=[],
        attrezzature_speciali=[],
    )
    zulu_worker = mk(
        id=uuid.UUID(int=701),
        nominativo="Zulu Worker",
        mansione="Operaio",
        ordine=1,
        created_at=datetime(2026, 1, 2),
        is_esterno=False,
        ruolo_datore_lavoro=False,
        ruolo_rspp=False,
        ruolo_rls=False,
        ruolo_medico_competente=False,
        ruolo_primo_soccorso=False,
        ruolo_antincendio=False,
        ruolo_preposto=False,
        ambienti=[zulu_env],
        dpi_codes=[],
        rischi_specifici_codes=["af_rumore"],
        attrezzature_speciali=[],
    )
    alpha_worker = mk(
        id=uuid.UUID(int=702),
        nominativo="Alpha Worker",
        mansione="Operaio",
        ordine=2,
        created_at=datetime(2026, 1, 3),
        is_esterno=False,
        ruolo_datore_lavoro=False,
        ruolo_rspp=False,
        ruolo_rls=True,
        ruolo_medico_competente=False,
        ruolo_primo_soccorso=False,
        ruolo_antincendio=False,
        ruolo_preposto=False,
        ambienti=[alpha_env],
        dpi_codes=[],
        rischi_specifici_codes=["mmc"],
        attrezzature_speciali=[],
    )
    external_rspp = mk(
        id=uuid.UUID(int=703),
        nominativo="Consulente RSPP",
        mansione="RSPP",
        ordine=3,
        created_at=datetime(2026, 1, 4),
        is_esterno=True,
        ruolo_datore_lavoro=False,
        ruolo_rspp=True,
        ruolo_rls=False,
        ruolo_medico_competente=False,
        ruolo_primo_soccorso=False,
        ruolo_antincendio=False,
        ruolo_preposto=False,
        ambienti=[],
        dpi_codes=[],
        rischi_specifici_codes=[],
        attrezzature_speciali=[],
    )
    external_medico = mk(
        id=uuid.UUID(int=704),
        nominativo="Consulente Medico",
        mansione="Medico",
        ordine=4,
        created_at=datetime(2026, 1, 5),
        is_esterno=True,
        ruolo_datore_lavoro=False,
        ruolo_rspp=False,
        ruolo_rls=False,
        ruolo_medico_competente=True,
        ruolo_primo_soccorso=False,
        ruolo_antincendio=False,
        ruolo_preposto=False,
        ambienti=[],
        dpi_codes=[],
        rischi_specifici_codes=[],
        attrezzature_speciali=[],
    )
    fixture["persone"] = [
        external_medico,
        alpha_worker,
        external_rspp,
        zulu_worker,
        ddl,
    ]
    zulu_env.persone = [ddl, zulu_worker]
    alpha_env.persone = [ddl, alpha_worker]

    fixture["attrezzature"] = [
        mk(
            id=uuid.UUID(int=800),
            descrizione=" Trapano   a colonna ",
            ambiente_id=alpha_env.id,
            marcatura_ce=True,
            verifiche_periodiche=False,
            ordine=1,
            created_at=datetime(2026, 1, 1),
        ),
        mk(
            id=uuid.UUID(int=801),
            descrizione="TRAPANO A COLONNA",
            ambiente_id=zulu_env.id,
            marcatura_ce=False,
            verifiche_periodiche=False,
            ordine=0,
            created_at=datetime(2026, 1, 2),
        ),
    ]
    applicable = mk(
        id=uuid.UUID(int=900),
        pericolo="RISK APPLICABLE SENTINEL",
        applicabile=True,
        ordine=1,
        created_at=datetime(2026, 1, 1),
        condizioni_esposizione="Condizione",
        rischio="Rischio",
        misure_prevenzione="Misura",
        probabilita_p=2,
        danno_d=3,
        livello_rischio="GRAVE",
    )
    disabled = mk(
        id=uuid.UUID(int=901),
        pericolo="RISK DISABLED SENTINEL",
        applicabile=False,
        ordine=2,
        created_at=datetime(2026, 1, 2),
    )
    zulu_env.valutazioni_rischio = [
        mk(
            id=uuid.UUID(int=902),
            categoria_rischio="Macchine",
            applicabile=False,
            ordine=0,
            created_at=datetime(2026, 1, 1),
            pericoli=[applicable, disabled],
        )
    ]
    alpha_env.valutazioni_rischio = []

    photos = []
    for index in range(10):
        image = Image.new(
            "RGB", (60 + index, 40 + index), (20 * index, 80, 160)
        )
        if index % 3 == 0:
            filename = f"foto-{index}.jpg"
            source = _image_bytes(image, "JPEG")
        elif index % 3 == 1:
            filename = f"foto-{index}.png"
            source = _image_bytes(image, "PNG")
        else:
            heif = pillow_heif.from_pillow(image)
            output = BytesIO()
            heif.save(output)
            filename = f"foto-{index}.heic"
            source = output.getvalue()
        normalized = normalize_document_image(source)
        photos.append(
            mk(
                id=uuid.UUID(int=1000 + index),
                filename=filename,
                file_path="/not-shared-on-worker/" + filename,
                document_image_bytes=normalized.content,
                document_image_content_type=normalized.content_type,
                created_at=datetime(2026, 1, 1, 9, index),
            )
        )

    measures = [
        mk(
            id=uuid.UUID(int=2),
            ordine=2,
            created_at=datetime(2026, 1, 2),
            priorita="MODESTO",
            misura="R2",
            misura_miglioramento="M2",
            procedura="P2",
            risorse="S2",
            responsabile="A2",
            scadenza="D2",
        ),
        mk(
            id=uuid.UUID(int=1),
            ordine=1,
            created_at=datetime(2026, 1, 1),
            priorita="GRAVE",
            misura="R1",
            misura_miglioramento="M1",
            procedura="P1",
            risorse="S1",
            responsabile="A1",
            scadenza="D1",
        ),
    ]
    company_photo = _company_photo_bytes()
    fixture["dvr_extras"] = {
        "foto_by_ambiente": {zulu_env.id: photos},
        "vdt_esposti_persona_ids": set(),
        "allegati_presenti": [],
        "misure_miglioramento": measures,
        "foto_presentazione": (company_photo, "image/jpeg"),
    }
    fixture["expected_company_photo"] = company_photo
    fixture["expected_people"] = [
        "DATORE FIXTURE",
        "ZULU WORKER",
        "ALPHA WORKER",
    ]
    # DATI OCCUPAZIONALI: one bullet per environment, in each person's order.
    fixture["expected_environment_bullets"] = [
        ["ZULU REPARTO", "ALPHA REPARTO"],
        ["ZULU REPARTO"],
        ["ALPHA REPARTO"],
    ]
    fixture["expected_environments"] = ["ZULU REPARTO", "ALPHA REPARTO"]
    # The ten photos, in saved order, as the bytes the DVR must embed.
    fixture["expected_photo_blobs"] = [photo.document_image_bytes for photo in photos]
    # The 2×2 grid of N2O's model: roles, names, a blank row to sign in.
    fixture["expected_signature_cells"] = [
        ["Datore di Lavoro", "Responsabile del S.P.P."],
        ["DATORE FIXTURE", "CONSULENTE RSPP"],
        ["", ""],
        ["Medico Competente", "RLS"],
        ["CONSULENTE MEDICO", "ALPHA WORKER"],
        ["", ""],
    ]
    return fixture


def _table_with_headers(doc: Document, headers: list[str]):
    return next(
        table
        for table in doc.tables
        if table.rows
        and [cell.text.strip() for cell in table.rows[0].cells] == headers
    )


def _text(doc: Document) -> str:
    return "\n".join(
        [paragraph.text for paragraph in doc.paragraphs]
        + [
            cell.text
            for table in doc.tables
            for row in table.rows
            for cell in row.cells
        ]
    )


def _heading_texts(doc: Document, level: int) -> list[str]:
    style = f"Heading {level}"
    return [
        paragraph.text
        for paragraph in doc.paragraphs
        if paragraph.style.name == style
    ]


def _expected_environment_titles(fixture: dict) -> list[str]:
    names = fixture.get("expected_environments")
    if names is None:
        names = [
            (environment.nome or "—").upper()
            for environment in sorted(fixture["ambienti"], key=_saved_order_key)
        ]
    return list(names)


def _expected_heading2(fixture: dict) -> list[str]:
    """Every Heading 2 of the page map, in order: rows 4–10, the dividers of
    rows 11–14, rows 15–18, the Part III divider, one title per environment,
    and the dividers of rows 21–28."""
    in_page = list(_IN_PAGE_TITLES)
    dividers = list(_DIVIDER_TITLES)
    return [
        *in_page[:7],
        *dividers[:4],
        *in_page[7:],
        dividers[4],
        *_expected_environment_titles(fixture),
        *dividers[5:],
    ]


def _is_page_break_only(element) -> bool:
    """A paragraph holding nothing but a page break: right before a title
    that breaks the page itself, it prints an empty page."""
    if element is None or element.tag != qn("w:p"):
        return False
    text = "".join(node.text or "" for node in element.iter(qn("w:t")))
    return (
        bool(element.xpath('.//w:br[@w:type="page"]'))
        and not text.strip()
        and not element.xpath(".//w:drawing")
    )


def _audit_page_boundaries(doc: Document) -> bool:
    """Every title opens a page without leaving an empty one behind.

    A divider title sits on an art page that starts its section, and what
    follows it starts on the next page. An in-page title (or its part label)
    carries page-break-before and is not preceded by a page-break-only
    paragraph. No two page-break paragraphs are adjacent.
    """
    firsts = [block for block in section_first_blocks(doc) if block is not None]
    for paragraph in doc.paragraphs:
        if paragraph.style.name != "Heading 2":
            continue
        title = paragraph._p
        art = _divider_art_paragraph(title)
        if art is not None:
            if not any(art is first for first in firsts):
                return False
            if not _content_after_starts_new_page(title):
                return False
            continue
        label = title.getprevious()
        opener = label if _style_name(label) == "Heading1" else title
        if not _page_break_before(opener) or _is_page_break_only(opener.getprevious()):
            return False
    flags = [
        bool(paragraph._p.xpath('.//w:br[@w:type="page"]'))
        for paragraph in doc.paragraphs
    ]
    return not any(left and right for left, right in zip(flags, flags[1:]))


def _audit_outline(doc: Document, fixture: dict) -> bool:
    return (
        _heading_texts(doc, 1) == _H1_HEADINGS
        and _heading_texts(doc, 2) == _expected_heading2(fixture)
        and _audit_page_boundaries(doc)
    )


def _audit_vera_cover(path: Path, doc: Document) -> bool:
    """The cover is the VERA artwork alone.

    The first section opens on the ``cover_dvr`` art paragraph, whose one
    picture is ``assets/document_art/cover_dvr.jpg`` with its pinned hash and
    size. No consultancy letterhead on the page; the footer logo is the VERA
    mark, as the fixture's organization uploaded none; the retired logos are
    not in the file.
    """
    art_dir = BACKEND_ROOT / "assets" / "document_art"
    firsts = section_first_blocks(doc)
    first = firsts[0] if firsts else None
    if first is None or art_marker(first) != "vera-art:cover:cover_dvr":
        return False
    blobs = [_picture_blob(doc.part, anchor) for anchor in first.xpath(".//wp:anchor")]
    if len(blobs) != 1 or blobs[0] != (art_dir / "cover_dvr.jpg").read_bytes():
        return False
    if sha256(blobs[0]).hexdigest() != _VERA_COVER_SHA256:
        return False
    try:
        with Image.open(BytesIO(blobs[0])) as image:
            if image.size != _VERA_COVER_DIMENSIONS:
                return False
    except OSError:
        return False

    footer_logos = set()
    for section in doc.sections:
        footer = section.footer
        for inline in footer._element.xpath(".//wp:inline"):
            footer_logos.add(_picture_blob(footer.part, inline))
    with ZipFile(path) as archive:
        media = [
            archive.read(name)
            for name in archive.namelist()
            if name.startswith("word/media/")
        ]
    retired = [
        (BACKEND_ROOT / "assets" / name).read_bytes()
        for name in ("logo.png", "n2o_vera_dvr.png")
        if (BACKEND_ROOT / "assets" / name).is_file()
    ]
    return (
        footer_logos == {(art_dir / "vera_italia_mark.png").read_bytes()}
        and not any(content in media for content in retired)
        and "Documento elaborato da" not in _text(doc)
    )


def _people_table(doc: Document, title: str):
    blocks = _blocks(doc)
    return _table_after(blocks, _heading_index(blocks, title))


def _audit_saved_people_order(doc: Document, fixture: dict) -> bool:
    tables = [_people_table(doc, "DATI ANAGRAFICI"), _people_table(doc, "DATI OCCUPAZIONALI")]
    return all(
        table is not None and _first_column(table)[1:] == fixture["expected_people"]
        for table in tables
    )


def _environment_titles(doc: Document) -> list[str] | None:
    """The titles between the Part III divider and MANSIONI: one per
    environment."""
    texts = _heading_texts(doc, 2)
    try:
        start = texts.index(_PAGE_MAP_DIVIDERS[4][1])
        end = texts.index(_PAGE_MAP_DIVIDERS[5][1])
    except ValueError:
        return None
    return texts[start + 1 : end]


def _audit_saved_environment_order(doc: Document, fixture: dict) -> bool:
    return _environment_titles(doc) == fixture["expected_environments"]


def _single_column_table_values(doc: Document, title: str) -> list[str] | None:
    """The value rows of the one-column table titled ``title`` (a role band
    of ORGANIZZAZIONE AZIENDALE DELLA SICUREZZA), else ``None``."""
    for table in doc.tables:
        if (
            table.rows
            and len(table.rows[0].cells) == 1
            and table.rows[0].cells[0].text.strip() == title
        ):
            return [row.cells[0].text.strip() for row in table.rows[1:]]
    return None


def _audit_external_roles(doc: Document, fixture: dict) -> bool:
    occupational = _people_table(doc, "DATI OCCUPAZIONALI")
    return (
        occupational is not None
        and _first_column(occupational)[1:] == fixture["expected_people"]
        and _single_column_table_values(
            doc, "Responsabile del Servizio di Prevenzione e Protezione"
        )
        == ["CONSULENTE RSPP (ESTERNO)"]
        and _single_column_table_values(doc, "Medico Competente")
        == ["CONSULENTE MEDICO (ESTERNO)"]
    )


def _audit_grouped_equipment(doc: Document, fixture: dict) -> bool:
    table = _table_with_headers(
        doc,
        [
            "Macchine, Attrezzature ed Impianti",
            "Ambiente",
            "Marcata CE",
            "Verifiche Periodiche",
        ],
    )
    return [
        [cell.text for cell in row.cells] for row in table.rows[1:]
    ] == [["TRAPANO A COLONNA", "ZULU REPARTO, ALPHA REPARTO", "MISTO", "NO"]]


def _audit_all_ten_photos(doc: Document, fixture: dict) -> bool:
    """All ten saved photos under "Foto e Planimetrie — ZULU REPARTO", in
    saved order: one picture per paragraph, fitted into 12 × 9 cm, no
    captions and no unavailable-photo markers."""
    blocks = _blocks(doc)
    start = _heading_index(blocks, "Foto e Planimetrie — ZULU REPARTO", level=3)
    if start is None:
        return False
    pictures = []
    for block in blocks[start + 1 :]:
        if not isinstance(block, Paragraph) or block.style.name.startswith("Heading"):
            break
        if _PHOTO_CAPTION.match(block.text):
            return False
        inlines = _inline_pictures(block._p)
        if len(inlines) > 1:
            return False
        if inlines:
            pictures.append(inlines[0])
    expected = fixture.get("expected_photo_blobs") or []
    return (
        len(pictures) == 10
        and [_picture_blob(doc.part, inline) for inline in pictures] == expected
        and all(
            _extent(inline)[0] <= Cm(12) and _extent(inline)[1] <= Cm(9)
            for inline in pictures
        )
        and "[Foto non disponibile:" not in _text(doc)
    )


def _audit_effective_risks(doc: Document, fixture: dict) -> bool:
    full = _text(doc)
    checklist_header = ["Categoria di Rischio", "Applicabile"]
    checklists = [
        table
        for table in doc.tables
        if table.rows
        and [cell.text.strip() for cell in table.rows[0].cells]
        == checklist_header
    ]
    machine_rows = [
        [cell.text.strip() for cell in row.cells]
        for table in checklists
        for row in table.rows[1:]
        if row.cells[0].text.strip() == "Macchine"
    ]
    risk_header = [
        "PERICOLO",
        "CONDIZIONI DI IMPIEGO O DI ESPOSIZIONE",
        "RISCHIO",
        "MISURE DI PREVENZIONE E PROTEZIONE ATTUATE E DPI",
        "I = P + 2*D",
    ]
    risk_tables = [
        table
        for table in doc.tables
        if table.rows
        and [cell.text.strip() for cell in table.rows[0].cells] == risk_header
    ]
    risk_rows = [
        [cell.text.strip() for cell in row.cells]
        for table in risk_tables
        for row in table.rows[1:]
    ]
    return (
        full.count("RISK APPLICABLE SENTINEL") == 1
        and "RISK DISABLED SENTINEL" not in full
        and machine_rows == [["Macchine", "SI"], ["Macchine", "NO"]]
        and len(risk_tables) == 1
        and risk_rows
        == [[
            "RISK APPLICABLE SENTINEL",
            "Condizione",
            "Rischio",
            "Misura",
            "P = 2; D = 3; I = 8; GRAVE",
        ]]
    )


def _audit_person_specific_risks(doc: Document, fixture: dict) -> bool:
    table = _table_with_headers(
        doc, ["Nominativo", "Mansione", "Rischio specifico"]
    )
    return [
        [cell.text for cell in row.cells] for row in table.rows[1:]
    ] == [
        ["ZULU WORKER", "OPERAIO", "Agenti fisici - Rumore"],
        [
            "ALPHA WORKER",
            "OPERAIO",
            "Movimentazione manuale dei carichi (MMC)",
        ],
    ]


def _audit_dpi_dash_alignment(doc: Document) -> bool:
    headers = ["Descrizione DPI", "Marca / Modello", "Note"]
    tables = [
        table
        for table in doc.tables
        if table.rows
        and [cell.text.strip() for cell in table.rows[0].cells] == headers
    ]
    cells = [row.cells[1] for table in tables for row in table.rows[1:]]
    return (
        len(tables) == 2
        and [cell.text.strip() for cell in cells] == ["—", "—"]
        and all(
            cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
            and all(
                paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
                for paragraph in cell.paragraphs
            )
            for cell in cells
        )
    )


def _audit_topic_separators(doc: Document, fixture: dict) -> bool:
    return _audit_outline(doc, fixture)


def _audit_complete_improvements(doc: Document, fixture: dict) -> bool:
    """Every saved measure, in saved order, with the four printed fields
    (Rischio, Attività / Procedura and Scadenza stay in the database)."""
    try:
        table = _table_with_headers(doc, _IMPROVEMENT_HEADERS)
    except StopIteration:
        return False
    rows = [[cell.text for cell in row.cells] for row in table.rows[1:]]
    return rows == [
        ["M1", "S1", "A1", "GRAVE"],
        ["M2", "S2", "A2", "MODESTO"],
    ]


def _audit_declaration_signatures(doc: Document, fixture: dict) -> bool:
    blocks = _blocks(doc)
    declaration = _heading_index(blocks, _PAGE_MAP_DIVIDERS[-1][1])
    grid = _signature_grid(doc)
    if declaration is None or grid is None:
        return False
    signature_cells = [[cell.text for cell in row.cells] for row in grid.rows]
    final_clause = next(
        (
            paragraph
            for paragraph in doc.paragraphs
            if paragraph.text.startswith("di impegnarsi a rielaborare")
        ),
        None,
    )
    place_date = next(
        (paragraph for paragraph in doc.paragraphs if ", lì " in paragraph.text),
        None,
    )
    sign_rows = (grid.rows[2], grid.rows[5])
    return (
        _content_after_starts_new_page(blocks[declaration]._p)
        and "DATORE FIXTURE, in qualità di Datore di Lavoro della "
        "LUCA FIXTURE INDUSTRIA SRL" in _text(doc)
        and signature_cells == fixture["expected_signature_cells"]
        and final_clause is not None
        and place_date is not None
        and bool(final_clause._p.xpath("./w:pPr/w:keepNext"))
        and bool(place_date._p.xpath("./w:pPr/w:keepNext"))
        and final_clause._p.getnext() is place_date._p
        and place_date._p.getnext() is grid._tbl
        and all(
            row.height >= Cm(2.5)
            and row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST
            for row in sign_rows
        )
        and all(row._tr.xpath("./w:trPr/w:cantSplit") for row in grid.rows)
    )


# ---------------------------------------------------------------------------
# Page-map audits (spec §4.2.1)
# ---------------------------------------------------------------------------


def _blocks(doc: Document) -> list:
    """Body paragraphs and tables, in document order, as python-docx objects."""
    blocks = []
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:p"):
            blocks.append(Paragraph(element, doc._body))
        elif element.tag == qn("w:tbl"):
            blocks.append(Table(element, doc._body))
    return blocks


def _is_heading(block, level: int, text: str | None = None) -> bool:
    return (
        isinstance(block, Paragraph)
        and block.style.name == f"Heading {level}"
        and (text is None or block.text == text)
    )


def _heading_index(blocks: list, text: str, level: int = 2) -> int | None:
    matches = [
        index
        for index, block in enumerate(blocks)
        if _is_heading(block, level, text)
    ]
    return matches[0] if len(matches) == 1 else None


def _page_break_before(element) -> bool:
    flags = element.xpath("./w:pPr/w:pageBreakBefore")
    return bool(flags) and flags[0].get(qn("w:val")) in (None, "1", "true", "on")


def _style_name(element) -> str | None:
    if element is None or element.tag != qn("w:p"):
        return None
    ids = element.xpath("./w:pPr/w:pStyle/@w:val")
    return ids[0] if ids else None


def _divider_art_paragraph(title_element):
    """The art paragraph of a divider title (skipping its part label), or None."""
    previous = title_element.getprevious()
    if _style_name(previous) == "Heading1":
        previous = previous.getprevious()
    marker = art_marker(previous) if previous is not None else None
    if marker and marker.startswith("vera-art:divider:"):
        return previous
    return None


def _divider_entries(doc: Document) -> list[tuple[str, str]]:
    """(art key, title) of every divider page, in document order. A divider
    counts only when its art paragraph is the first block of a section."""
    # Hold the elements themselves: lxml proxies are only identical (and
    # their id() stable) while a reference keeps them alive.
    firsts = [block for block in section_first_blocks(doc) if block is not None]
    entries = []
    for paragraph in doc.paragraphs:
        if paragraph.style.name != "Heading 2":
            continue
        art = _divider_art_paragraph(paragraph._p)
        if art is None or not any(art is first for first in firsts):
            continue
        entries.append((art_marker(art).split(":", 2)[2], paragraph.text))
    return entries


def _table_after(blocks: list, index: int | None):
    """The first table after ``blocks[index]``, before the next heading."""
    if index is None:
        return None
    for block in blocks[index + 1 :]:
        if isinstance(block, Table):
            return block
        if isinstance(block, Paragraph) and block.style.name.startswith("Heading"):
            return None
    return None


def _header_texts(table) -> list[str]:
    return [cell.text.strip() for cell in table.rows[0].cells] if table.rows else []


def _first_column(table) -> list[str]:
    return [row.cells[0].text.strip() for row in table.rows]


def _cell_fill(cell) -> str | None:
    fills = cell._tc.xpath("./w:tcPr/w:shd/@w:fill")
    return fills[0].upper() if fills else None


def _inline_pictures(element) -> list:
    return element.xpath(".//wp:inline")


def _picture_blob(part, inline) -> bytes | None:
    blips = inline.xpath(".//a:blip/@r:embed")
    if not blips:
        return None
    related = part.related_parts.get(blips[0])
    return related.blob if related is not None else None


def _extent(inline) -> tuple[int, int]:
    extent = inline.find(qn("wp:extent"))
    return int(extent.get("cx")), int(extent.get("cy"))


def _all_paragraph_texts(doc: Document) -> list[str]:
    texts = [paragraph.text for paragraph in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.extend(paragraph.text for paragraph in cell.paragraphs)
    return texts


def _content_after_starts_new_page(title_element) -> bool:
    """What follows a divider title opens the next page: a page break, or
    the next title's own page-break-before (the kit absorbs the break into
    it), or a section break."""
    following = title_element.getnext()
    if following is None or following.tag != qn("w:p"):
        return False
    return (
        bool(following.xpath('.//w:br[@w:type="page"]'))
        or _page_break_before(following)
        or bool(following.xpath("./w:pPr/w:sectPr"))
    )


def _audit_page_map_dividers(doc: Document) -> bool:
    entries = _divider_entries(doc)
    if entries != list(_PAGE_MAP_DIVIDERS):
        return False
    titles = [
        paragraph
        for paragraph in doc.paragraphs
        if paragraph.style.name == "Heading 2" and paragraph.text in _DIVIDER_TITLES
    ]
    return len(titles) == len(_DIVIDER_TITLES) and all(
        _content_after_starts_new_page(title._p) for title in titles
    )


def _audit_in_page_titles(doc: Document) -> bool:
    blocks = _blocks(doc)
    positions = [_heading_index(blocks, title) for title in _IN_PAGE_TITLES]
    if None in positions or positions != sorted(positions):
        return False
    for position in positions:
        title = blocks[position]._p
        label = title.getprevious()
        opener = label if _style_name(label) == "Heading1" else title
        if not _page_break_before(opener) or _divider_art_paragraph(title) is not None:
            return False
    headings = [
        paragraph.text
        for paragraph in doc.paragraphs
        if paragraph.style.name in ("Heading 1", "Heading 2", "Heading 3")
    ]
    return not any(_NUMBERED_HEADING.match(text) for text in headings)


def _audit_part_ii_renamed(doc: Document, fixture: dict) -> bool:
    blocks = _blocks(doc)
    h1 = [paragraph.text for paragraph in doc.paragraphs if paragraph.style.name == "Heading 1"]
    label = next(
        (
            index
            for index, block in enumerate(blocks)
            if _is_heading(block, 1, _PART_II_LABEL)
        ),
        None,
    )
    presentazione = _heading_index(blocks, "PRESENTAZIONE DELL'AZIENDA")
    anagrafica = _heading_index(blocks, "ANAGRAFICA AZIENDALE")
    description = (fixture["azienda"].descrizione_attivita or "").strip()[:40]
    moved = (
        presentazione is not None
        and anagrafica is not None
        and bool(description)
        and any(
            isinstance(block, Paragraph) and description in block.text
            for block in blocks[presentazione + 1 : anagrafica]
        )
        and sum(description in text for text in _all_paragraph_texts(doc)) == 1
    )
    return (
        h1.count(_PART_II_LABEL) == 1
        and _LEGACY_PART_II_LABEL not in _text(doc)
        and label is not None
        and _is_heading(blocks[label + 1], 2, "DEFINIZIONI")
        and not any("Descrizione dell'Attività" in text for text in _heading_texts(doc, 2))
        and moved
    )


def _bullet_style_numbered(doc: Document) -> bool:
    try:
        style = doc.styles["List Bullet"]
    except KeyError:
        return False
    return bool(style.element.xpath("./w:pPr/w:numPr/w:numId"))


def _audit_split_people_tables(doc: Document, fixture: dict) -> bool:
    blocks = _blocks(doc)
    anagrafici = _table_after(blocks, _heading_index(blocks, "DATI ANAGRAFICI"))
    occupazionali = _table_after(blocks, _heading_index(blocks, "DATI OCCUPAZIONALI"))
    if anagrafici is None or occupazionali is None:
        return False
    if (
        _header_texts(anagrafici) != _DATI_ANAGRAFICI_HEADERS
        or _header_texts(occupazionali) != _DATI_OCCUPAZIONALI_HEADERS
    ):
        return False
    expected_people = fixture["expected_people"]
    if (
        _first_column(anagrafici)[1:] != expected_people
        or _first_column(occupazionali)[1:] != expected_people
    ):
        return False
    # Environments are a real bulleted list: List Bullet paragraphs (numbered
    # through the style), no empty leading paragraph, one per environment.
    expected_bullets = fixture.get("expected_environment_bullets")
    for index, row in enumerate(occupazionali.rows[1:]):
        paragraphs = row.cells[2].paragraphs
        texts = [paragraph.text for paragraph in paragraphs]
        if expected_bullets is not None and texts != expected_bullets[index]:
            return False
        if texts == ["—"]:
            continue
        if not all(paragraph.style.name == "List Bullet" for paragraph in paragraphs):
            return False
        if any(not text.strip() for text in texts):
            return False
    return _bullet_style_numbered(doc)


def _audit_improvement_table_4_cols(doc: Document) -> bool:
    try:
        table = _table_with_headers(doc, _IMPROVEMENT_HEADERS)
    except StopIteration:
        return False
    portrait = all(
        section.orientation == WD_ORIENT.PORTRAIT
        and section.page_width < section.page_height
        for section in doc.sections
    )
    coloured = all(
        _cell_fill(row.cells[3]) == str(RISK_COLORS[row.cells[3].text.strip().upper()])
        for row in table.rows[1:]
        if row.cells[3].text.strip().upper() in RISK_COLORS
    )
    return portrait and coloured and len(table.columns) == 4


def _audit_no_repeated_azienda_table(doc: Document) -> bool:
    """The "Azienda | Sede Legale" identity strip prints on pages 4 and 5
    only: after the row-4 title and after PRESENTAZIONE DELL'AZIENDA."""
    blocks = _blocks(doc)
    strips = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, Table) and _first_column(block)[:2] == ["Azienda", "Sede Legale"]
    ]
    row_4 = _heading_index(blocks, _IN_PAGE_TITLES[0])
    presentazione = _heading_index(blocks, "PRESENTAZIONE DELL'AZIENDA")
    anagrafica = _heading_index(blocks, "ANAGRAFICA AZIENDALE")
    if None in (row_4, presentazione, anagrafica) or len(strips) != 2:
        return False
    light = all(
        _cell_fill(blocks[index].rows[0].cells[0]) == "F6F9FC" for index in strips
    )
    return light and row_4 < strips[0] < presentazione < strips[1] < anagrafica


def _audit_no_photo_captions(doc: Document) -> bool:
    return not any(_PHOTO_CAPTION.match(text) for text in _all_paragraph_texts(doc))


def _audit_sign_panels(doc: Document) -> bool:
    blocks = _blocks(doc)
    forma = _heading_index(blocks, "FORMA E CATEGORIE DEI CARTELLI", level=3)
    formazione = _heading_index(blocks, _PAGE_MAP_DIVIDERS[8][1])
    if forma is None or formazione is None:
        return False
    positions = []
    for number, (key, title) in enumerate(_SIGN_PANELS):
        matches = [
            index
            for index, block in enumerate(blocks)
            if isinstance(block, Paragraph)
            and block.text == title
            and not block.style.name.startswith("Heading")
        ]
        if len(matches) != 1:
            return False
        index = matches[0]
        caption = blocks[index]
        picture = blocks[index + 1] if index + 1 < len(blocks) else None
        if not isinstance(picture, Paragraph):
            return False
        inlines = _inline_pictures(picture._p)
        if len(inlines) != 1 or picture.text.strip():
            return False
        if _picture_blob(doc.part, inlines[0]) != (_ART_DIR / f"{key}.jpg").read_bytes():
            return False
        if abs(_extent(inlines[0])[0] - _SIGN_PANEL_WIDTH) > Cm(0.01):
            return False
        # Two panels per page: the first of each pair opens a page.
        if _page_break_before(caption._p) != (number % 2 == 0):
            return False
        positions.append(index)
    return forma < positions[0] and positions == sorted(positions) and positions[-1] < formazione


def _signature_grid(doc: Document):
    for table in doc.tables:
        if len(table.rows) == 6 and len(table.columns) == 2 and [
            cell.text.strip() for cell in table.rows[0].cells
        ] == list(_SIGNATURE_ROLES[:2]):
            return table
    return None


def _audit_signature_grid(doc: Document) -> bool:
    grid = _signature_grid(doc)
    if grid is None:
        return False
    roles = [cell for index in (0, 3) for cell in grid.rows[index].cells]
    if [cell.text.strip() for cell in roles] != list(_SIGNATURE_ROLES):
        return False
    if not all(_cell_fill(cell) == BRAND_NAVY_HEX for cell in roles):
        return False
    names = [cell.text.strip() for index in (1, 4) for cell in grid.rows[index].cells]
    signs = [grid.rows[2], grid.rows[5]]
    blocks = _blocks(doc)
    declaration = _heading_index(blocks, _PAGE_MAP_DIVIDERS[-1][1])
    grid_index = next(
        (index for index, block in enumerate(blocks) if isinstance(block, Table) and block._tbl is grid._tbl),
        None,
    )
    return (
        all(names)
        and all(
            row.height is not None
            and row.height >= Cm(2.5)
            and row.height_rule == WD_ROW_HEIGHT_RULE.AT_LEAST
            and not "".join(cell.text for cell in row.cells).strip()
            for row in signs
        )
        and declaration is not None
        and grid_index is not None
        and declaration < grid_index
    )


def _audit_cover_and_back_art(doc: Document) -> bool:
    firsts = section_first_blocks(doc)
    return (
        len(firsts) >= 2
        and art_marker(firsts[0]) == "vera-art:cover:cover_dvr"
        and art_marker(firsts[-1]) == "vera-art:back_cover:back_vera"
    )


def _company_photo_inlines(doc: Document) -> list | None:
    blocks = _blocks(doc)
    presentazione = _heading_index(blocks, "PRESENTAZIONE DELL'AZIENDA")
    anagrafica = _heading_index(blocks, "ANAGRAFICA AZIENDALE")
    if presentazione is None or anagrafica is None:
        return None
    found = []
    for block in blocks[presentazione + 1 : anagrafica]:
        element = block._p if isinstance(block, Paragraph) else block._tbl
        found.extend((block, inline) for inline in _inline_pictures(element))
    return found


def _audit_company_photo(doc: Document, photo: bytes | None) -> bool:
    """The photo under the light identity strip, centred, inside the
    16.5 × 11 cm box with its aspect kept; no slot at all without one."""
    found = _company_photo_inlines(doc)
    if found is None:
        return False
    if photo is None:
        return found == []
    if len(found) != 1:
        return False
    paragraph, inline = found[0]
    width, height = _extent(inline)
    with Image.open(BytesIO(photo)) as image:
        ratio = image.width / image.height
    blocks = _blocks(doc)
    strip = _table_after(blocks, _heading_index(blocks, "PRESENTAZIONE DELL'AZIENDA"))
    return (
        isinstance(paragraph, Paragraph)
        and paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
        and _picture_blob(doc.part, inline) == photo
        and width <= _COMPANY_PHOTO_MAX[0]
        and height <= _COMPANY_PHOTO_MAX[1]
        and abs(width / height - ratio) / ratio < 0.01
        and (width >= _COMPANY_PHOTO_MAX[0] - Cm(0.01) or height >= _COMPANY_PHOTO_MAX[1] - Cm(0.01))
        and strip is not None
        and strip._tbl.getparent().index(strip._tbl) < paragraph._p.getparent().index(paragraph._p)
    )


def _generator_patch_objects() -> list[object]:
    from app.services.document_generator import (
        _biologico_common,
        base,
        data_loader,
    )

    module_classes = [
        ("allegato_mmc", "AllegatoMmcGenerator"),
        ("allegato_vdt", "AllegatoVdtGenerator"),
        ("allegato_stress", "AllegatoStressGenerator"),
        ("allegato_gestanti", "AllegatoGestantiGenerator"),
        ("allegato_incendio", "AllegatoIncendioGenerator"),
        ("allegato_microclima", "AllegatoMicroclimaGenerator"),
        ("allegato_microclima_severo", "AllegatoMicroclimaSeveroGenerator"),
        ("pee_azienda", "PeeAziendaGenerator"),
        ("pee_comune", "PeeComuneGenerator"),
        ("duvri", "DuvriGenerator"),
        ("pos", "PosGenerator"),
        ("haccp_manuale", "HaccpManualeGenerator"),
        ("haccp_forms", "HaccpFormsGenerator"),
    ]
    modules = [
        importlib.import_module(
            f"app.services.document_generator.{module_name}"
        )
        for module_name, _class_name in module_classes
    ]
    version_classes = [
        getattr(module, class_name)
        for module, (_module_name, class_name) in zip(modules, module_classes)
    ]
    return [
        base.BaseDocumentGenerator,
        DVRMasterGenerator,
        *version_classes,
        data_loader,
        _biologico_common,
        *modules,
    ]


_MISSING_ATTRIBUTE = object()


def _changed_attributes(snapshots: list[tuple[object, dict]]) -> list[tuple]:
    changes = []
    for owner, before in snapshots:
        current = vars(owner)
        for name in before.keys() | current.keys():
            original = before.get(name, _MISSING_ATTRIBUTE)
            replacement = current.get(name, _MISSING_ATTRIBUTE)
            if replacement is not original:
                changes.append((owner, name, original))
    return changes


def _restore_attributes(changes: list[tuple]) -> None:
    for owner, name, original in reversed(changes):
        if original is _MISSING_ATTRIBUTE:
            if name in vars(owner):
                delattr(owner, name)
        else:
            setattr(owner, name, original)


@contextmanager
def _patched_generator_fixture(fixture: dict, output_dir: Path):
    snapshots = [
        (owner, dict(vars(owner))) for owner in _generator_patch_objects()
    ]
    try:
        patch_generators(fixture, str(output_dir))
    except BaseException:
        _restore_attributes(_changed_attributes(snapshots))
        raise
    changes = _changed_attributes(snapshots)
    try:
        yield
    finally:
        _restore_attributes(changes)


def _audit_acme_regression(path: Path, fixture: dict) -> bool:
    doc = Document(path)
    anagrafici = _people_table(doc, "DATI ANAGRAFICI")
    occupational = _people_table(doc, "DATI OCCUPAZIONALI")
    if anagrafici is None or occupational is None:
        return False
    environment_summary = _table_with_headers(
        doc, ["Ambiente", "Tipo", "Metratura", "N. Lavoratori"]
    )
    global_equipment = _table_with_headers(
        doc,
        [
            "Macchine, Attrezzature ed Impianti",
            "Ambiente",
            "Marcata CE",
            "Verifiche Periodiche",
        ],
    )
    actual_inventory = {
        "total": len(doc.tables),
        "dimensions": Counter(
            (len(table.rows), len(table.rows[0].cells))
            for table in doc.tables
        ),
    }
    return (
        fixture["azienda"].ragione_sociale in _text(doc)
        and _audit_outline(doc, fixture)
        and [
            [cell.text.strip() for cell in row.cells]
            for row in anagrafici.rows[1:]
        ]
        == fixture["expected_anagrafici_rows"]
        and [
            [cell.text.strip() for cell in row.cells]
            for row in occupational.rows[1:]
        ]
        == fixture["expected_people_rows"]
        and [
            [cell.text.strip() for cell in row.cells]
            for row in environment_summary.rows[1:]
        ]
        == fixture["expected_environment_rows"]
        and [
            [cell.text.strip() for cell in row.cells]
            for row in global_equipment.rows[1:]
        ]
        == fixture["expected_global_equipment_rows"]
        and actual_inventory == fixture["expected_table_inventory"]
    )


def build_and_audit(output_dir: Path) -> dict[str, bool]:
    """Generate the Acme and Luca DOCX files, then return all audit gates."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    acme = build_acme_fixture()
    with _patched_generator_fixture(acme, output_dir):
        acme_ok, acme_path, acme_message = asyncio.run(
            run_one("DVR_MASTER", acme["azienda"].id)
        )
        if not acme_ok:
            raise AssertionError(acme_message)
        stable_acme = output_dir / "DVR_Acme_Regression.docx"
        shutil.copy2(acme_path, stable_acme)

        fixture = build_luca_fixture()
        patch_generators(fixture, str(output_dir))

        async def rich_dvr_extras(self, data):
            return fixture["dvr_extras"]

        DVRMasterGenerator._load_dvr_extras = rich_dvr_extras
        ok, generated_path, message = asyncio.run(
            run_one("DVR_MASTER", fixture["azienda"].id)
        )
        if not ok:
            raise AssertionError(message)
        stable_path = output_dir / "DVR_Luca_Fixture.docx"
        shutil.copy2(generated_path, stable_path)

        report = audit_luca_docx(stable_path, fixture)
        report["acme_regression"] = _audit_acme_regression(stable_acme, acme)
        # Present when the fixture gives bytes (Luca), absent when not (Acme).
        report["company_photo"] = report["company_photo"] and _audit_company_photo(
            Document(stable_acme), None
        )
    return {key: report[key] for key in _REPORT_KEYS}


def audit_luca_docx(path: Path, fixture: dict) -> dict[str, bool]:
    """Audit exact structural acceptance behavior in a generated Luca DOCX."""
    doc = Document(path)
    return {
        "vera_cover": _audit_vera_cover(path, doc),
        "saved_people_order": _audit_saved_people_order(doc, fixture),
        "saved_environment_order": _audit_saved_environment_order(doc, fixture),
        "external_roles": _audit_external_roles(doc, fixture),
        "grouped_equipment": _audit_grouped_equipment(doc, fixture),
        "all_ten_photos": _audit_all_ten_photos(doc, fixture),
        "effective_risks": _audit_effective_risks(doc, fixture),
        "person_specific_risks": _audit_person_specific_risks(doc, fixture),
        "dpi_dash_alignment": _audit_dpi_dash_alignment(doc),
        "topic_separators": _audit_topic_separators(doc, fixture),
        "complete_improvements": _audit_complete_improvements(doc, fixture),
        "declaration_signatures": _audit_declaration_signatures(doc, fixture),
        "page_map_dividers": _audit_page_map_dividers(doc),
        "in_page_titles": _audit_in_page_titles(doc),
        "part_ii_renamed": _audit_part_ii_renamed(doc, fixture),
        "split_people_tables": _audit_split_people_tables(doc, fixture),
        "improvement_table_4_cols": _audit_improvement_table_4_cols(doc),
        "no_repeated_azienda_table": _audit_no_repeated_azienda_table(doc),
        "no_photo_captions": _audit_no_photo_captions(doc),
        "sign_panels": _audit_sign_panels(doc),
        "signature_grid": _audit_signature_grid(doc),
        "cover_and_back_art": _audit_cover_and_back_art(doc),
        "company_photo": _audit_company_photo(
            doc, fixture.get("expected_company_photo")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = build_and_audit(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
