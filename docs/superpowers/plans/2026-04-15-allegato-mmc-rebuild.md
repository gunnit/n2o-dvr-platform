# Allegato MMC — Programmatic Rebuild (POC)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `backend/app/services/document_generator/allegato_mmc.py` so it generates the entire Allegato MMC document programmatically from DB data — with zero dependency on the `ALLEGATO RISCHIO MMC.docx` template — mirroring the section structure of the original template. Serves as the reference POC before rebuilding the other 9 templated generators (VDT, Gestanti, Incendio, Stress, PEE-azienda, PEE-comune, HACCP, DUVRI, POS).

**Architecture:** Follow the `dvr_master.py` pattern — a single `AllegatoMmcGenerator` class with one method per document section. Reference data (NIOSH factor tables, boilerplate text) lives in a new sibling module `allegato_mmc_content.py` to keep the generator file focused on docx rendering. No template file is loaded; `replace_placeholders` is not used.

**Tech Stack:** Python 3.12, python-docx, SQLAlchemy 2.0 async, pytest.

---

## File Structure

| Path | Purpose |
|---|---|
| `backend/app/services/document_generator/allegato_mmc.py` | **Rewritten**. Class `AllegatoMmcGenerator` with one `_add_*` method per section. No template load. |
| `backend/app/services/document_generator/allegato_mmc_content.py` | **New**. Boilerplate Italian text constants + NIOSH lookup tables (CP, factor A/B/C/D/E/F) as Python data. Mirrors the extraction in `docs/context/REFERENCE_DATA.md` §1. |
| `backend/tests/test_allegato_mmc.py` | **New**. Structural + content assertions on the generated .docx using the `verify_all_generators.py` fixture. |
| `backend/scripts/verify_all_generators.py` | No change (MMC fixture row already present at line ~105). |

---

## Pre-requisites (verify before starting)

- [ ] **Step 0.1: Confirm local services are running**

Run:
```bash
docker ps --format '{{.Names}}' | grep -E 'dlg-(postgres|redis)'
```
Expected: both `dlg-postgres-1` and `dlg-redis-1`.

- [ ] **Step 0.2: Confirm pytest works against existing tests**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_generators.py -x -q
```
Expected: PASS (all 17 generators currently build). This is the baseline — we must not break the smoke check.

---

## Task 1: Write the failing test (TDD anchor)

**Files:**
- Create: `backend/tests/test_allegato_mmc.py`

Uses the existing `verify_all_generators` helper to produce an MMC .docx against the ACME fixture, then asserts the output contains DB data (not prior-client data) at section-level.

- [ ] **Step 1.1: Create the test file**

```python
"""Structural & content assertions for the rebuilt Allegato MMC generator.

Fixture: ACME MECCANICA COMPOSITA SRL (see scripts/verify_all_generators.build_fixture).
MMC row: 1 task ("Carico/scarico pezzi..."), PLR=15.0, IR=1.0, zone GIALLO.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from docx import Document


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


def _load_verify():
    spec = importlib.util.spec_from_file_location(
        "verify_all_generators",
        str(BACKEND_ROOT / "scripts" / "verify_all_generators.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mmc_doc(tmp_path_factory):
    out = tmp_path_factory.mktemp("mmc_out")
    module = _load_verify()
    fixture = module.build_fixture()
    module.patch_generators(fixture, str(out))

    async def run():
        ok, path, msg = await module.run_one("ALLEGATO_MMC", fixture["azienda"].id)
        assert ok, f"Generator failed: {msg}"
        return path

    path = asyncio.run(run())
    doc = Document(path)
    all_text = "\n".join(p.text for p in doc.paragraphs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                all_text += "\n" + cell.text
    return {"path": path, "doc": doc, "text": all_text}


# ---- Structural ----------------------------------------------------------

EXPECTED_SECTIONS = [
    "Anagrafica Aziendale",
    "Dati occupazionali",
    "Descrizione dell",  # "Descrizione dell'azienda" — apostrophe varies
    "Organizzazione Aziendale della Sicurezza",
    "Metodologia",
    "Modalità di valutazione",
    "Indicatori di rischio",
    "Tavole di Valutazione",
    "Quadro sinottico",
    "Programma di attuazione",
    "Dichiarazione del Datore di Lavoro",
]


@pytest.mark.parametrize("section", EXPECTED_SECTIONS)
def test_section_heading_present(mmc_doc, section):
    assert section in mmc_doc["text"], f"Missing section heading: {section!r}"


# ---- Azienda data populated ---------------------------------------------

def test_contains_fixture_azienda_name(mmc_doc):
    assert "ACME MECCANICA COMPOSITA" in mmc_doc["text"].upper()


def test_contains_partita_iva(mmc_doc):
    assert "04567890123" in mmc_doc["text"]


def test_contains_sede_legale(mmc_doc):
    assert "Parma" in mmc_doc["text"]


# ---- Workers rendered ----------------------------------------------------

@pytest.mark.parametrize("name", [
    "Mario Rossi", "Luca Bianchi", "Giulia Verdi", "Antonio Marrone",
    "Valentina Rinaldi",
])
def test_contains_worker_names(mmc_doc, name):
    assert name in mmc_doc["text"], f"Worker missing: {name}"


# ---- NIOSH assessment rendered (fixture has 1 task) ----------------------

def test_contains_compito(mmc_doc):
    assert "Carico/scarico pezzi" in mmc_doc["text"]


def test_contains_plr_value(mmc_doc):
    # Fixture PLR = 15.0 kg. Accept "15.0" or "15,0" (IT decimal).
    t = mmc_doc["text"]
    assert "15.0" in t or "15,0" in t


def test_contains_ir_zone(mmc_doc):
    assert "GIALLO" in mmc_doc["text"].upper()


# ---- Reference tables (NIOSH factors) rendered ---------------------------

def test_contains_cp_table_values(mmc_doc):
    # CP table: males >18 = 25, females >18 = 20
    t = mmc_doc["text"]
    assert "25" in t and "20" in t


def test_contains_frequency_table_label(mmc_doc):
    t = mmc_doc["text"]
    # "Breve durata" / "Media durata" / "Lunga durata" all appear in F table
    assert "Breve durata" in t and "Lunga durata" in t


# ---- CRITICAL: no prior-client leakage (the whole point of the rebuild) ---

@pytest.mark.parametrize("leak", [
    "N2O SRL",          # prior client company
    "CIARAMITARO",      # prior client DdL
    "GORGONZOLA",       # prior client city
    "SORMANI ANNALISA", # prior client worker
    "MARCHETTI LUCA",   # prior client worker
])
def test_no_prior_client_content(mmc_doc, leak):
    # The ACME fixture must not contain text from the old sample template.
    assert leak not in mmc_doc["text"], (
        f"Prior-client text {leak!r} leaked from template — "
        "generator should build from scratch, not load ALLEGATO RISCHIO MMC.docx."
    )


# ---- Page count sanity ---------------------------------------------------

def test_output_has_reasonable_length(mmc_doc):
    # Original sample is ~30 pages. We expect ~20+ sections worth of content.
    # python-docx can't count pages directly, so use paragraph/table counts
    # as a proxy.
    doc = mmc_doc["doc"]
    assert len(doc.paragraphs) > 100, (
        f"Output suspiciously short ({len(doc.paragraphs)} paragraphs) — "
        "likely missing sections."
    )
    assert len(doc.tables) >= 6, (
        f"Too few tables ({len(doc.tables)}) — expected azienda, workers, "
        "roles, CP, F-table, per-worker assessments, summary, dichiarazione."
    )
```

- [ ] **Step 1.2: Run the test to verify it FAILS on the current generator**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v 2>&1 | tail -60
```
Expected: Most tests FAIL. Specifically `test_no_prior_client_content[N2O SRL]`, `test_no_prior_client_content[CIARAMITARO]`, etc. should fail (because the current generator ships the prior-client template). `test_contains_fixture_azienda_name` may pass only via the appended tail section. `test_section_heading_present[Metodologia]` etc. may pass (coincidentally, because the template contains them).

This confirms the test exercises the gap we're fixing.

- [ ] **Step 1.3: Commit the failing test**

```bash
cd /mnt/c/Dev/dlg
git add backend/tests/test_allegato_mmc.py
git commit -m "test(allegato-mmc): add failing structural + anti-leak test

Drives the programmatic rebuild. Current generator ships the prior-client
sample template, so these anti-leak assertions must fail until we remove
the template load."
```

---

## Task 2: Create the NIOSH content module

**Files:**
- Create: `backend/app/services/document_generator/allegato_mmc_content.py`

Pure data + text constants. No docx logic. Keeps the generator file lean.

- [ ] **Step 2.1: Create the content module**

```python
"""Static content for Allegato MMC — NIOSH factor tables + Italian boilerplate.

Data transcribed from docs/context/REFERENCE_DATA.md §1 (NIOSH lookup tables)
and from the original ALLEGATO RISCHIO MMC.docx template's narrative sections.
All text in Italian — generator emits verbatim.
"""

# ---------------------------------------------------------------------------
# NIOSH lookup tables (REFERENCE_DATA.md §1)
# ---------------------------------------------------------------------------

# §1.1 — Costante di Peso
CP_TABLE_HEADERS = ["Età", "Maschi (kg)", "Femmine (kg)"]
CP_TABLE_ROWS = [
    ["> 18 anni", "25", "20"],
    ["15–18 anni", "15", "10"],
]

# §1.2 — Fattore A (Altezza)
FACTOR_A_HEADERS = ["Altezza mani da terra (cm)", "Fattore A"]
FACTOR_A_ROWS = [
    ["0", "0.78"], ["25", "0.85"], ["50", "0.93"],
    ["75 (ottimale)", "1.00"],
    ["100", "0.93"], ["125", "0.85"], ["150", "0.78"],
    ["> 175", "0.00"],
]
FACTOR_A_FORMULA = "A = 1 − (0,003 × |V − 75|)  dove V = altezza mani da terra (cm)"

# §1.3 — Fattore B (Dislocazione verticale)
FACTOR_B_HEADERS = ["Dislocazione verticale (cm)", "Fattore B"]
FACTOR_B_ROWS = [
    ["25 (ottimale)", "1.00"],
    ["30", "0.97"], ["40", "0.93"], ["50", "0.91"],
    ["70", "0.88"], ["100", "0.87"], ["170", "0.85"],
    ["> 175", "0.00"],
]
FACTOR_B_FORMULA = "B = 0,82 + (4,5 / X)  dove X = dislocazione verticale (cm)"

# §1.4 — Fattore C (Orizzontale)
FACTOR_C_HEADERS = ["Distanza orizzontale (cm)", "Fattore C"]
FACTOR_C_ROWS = [
    ["25 (ottimale)", "1.00"],
    ["30", "0.83"], ["40", "0.63"], ["50", "0.50"],
    ["55", "0.45"], ["60", "0.42"],
    ["> 63", "0.00"],
]
FACTOR_C_FORMULA = "C = 25 / H  dove H = distanza orizzontale (cm)"

# §1.5 — Fattore D (Asimmetria)
FACTOR_D_HEADERS = ["Angolo di asimmetria (gradi)", "Fattore D"]
FACTOR_D_ROWS = [
    ["0° (ottimale)", "1.00"],
    ["30°", "0.90"], ["60°", "0.81"], ["90°", "0.71"],
    ["120°", "0.62"], ["135°", "0.57"],
    ["> 135°", "0.00"],
]
FACTOR_D_FORMULA = "D = 1 − (0,0032 × y)  dove y = angolo di asimmetria (gradi)"

# §1.6 — Fattore E (Presa)
FACTOR_E_HEADERS = ["Giudizio sulla presa", "Fattore E"]
FACTOR_E_ROWS = [
    ["Buono", "1.00"],
    ["Discreto", "0.95"],
    ["Scarso", "0.90"],
]

# §1.7 — Fattore F (Frequenza) — full 18-row table
FACTOR_F_HEADERS = [
    "Frequenza (azioni/min)",
    "Breve durata (<1 ora)",
    "Media durata (1–2 ore)",
    "Lunga durata (2–8 ore)",
]
FACTOR_F_ROWS = [
    ["0.2", "1.00", "0.95", "0.85"],
    ["0.5", "0.97", "0.92", "0.81"],
    ["1",   "0.94", "0.88", "0.75"],
    ["2",   "0.91", "0.84", "0.65"],
    ["3",   "0.88", "0.79", "0.55"],
    ["4",   "0.84", "0.72", "0.45"],
    ["5",   "0.80", "0.60", "0.35"],
    ["6",   "0.75", "0.50", "0.27"],
    ["7",   "0.70", "0.42", "0.22"],
    ["8",   "0.60", "0.35", "0.18"],
    ["9",   "0.52", "0.30", "0.15"],
    ["10",  "0.45", "0.26", "0.13"],
    ["11",  "0.41", "0.23", "0.00"],
    ["12",  "0.37", "0.21", "0.00"],
    ["13",  "0.34", "0.00", "0.00"],
    ["14",  "0.31", "0.00", "0.00"],
    ["15",  "0.28", "0.00", "0.00"],
    ["> 15", "0.00", "0.00", "0.00"],
]

# §1.8 — Zone di rischio
ZONE_TABLE_HEADERS = ["Indice IR", "Zona", "Descrizione", "Azione"]
ZONE_TABLE_ROWS = [
    ["IR ≤ 0,75", "VERDE",  "Situazione accettabile",
     "Nessun intervento specifico richiesto"],
    ["0,75 < IR ≤ 1,0", "GIALLA",
     "Situazione al limite; 1–10% popolazione a rischio",
     "Sorveglianza sanitaria, formazione specifica, interventi strutturali"],
    ["IR > 1,0", "ROSSA",
     "Rischio crescente",
     "Prevenzione primaria: riprogettazione postazione, ausili meccanici"],
]


# ---------------------------------------------------------------------------
# Boilerplate narrative (Italian) — lifted from the original template's
# static prose sections. Safe to copy because these are D.Lgs. 81/2008
# quotations and NIOSH methodology descriptions, not client-specific.
# ---------------------------------------------------------------------------

INTRODUZIONE = [
    "Le affezioni cronico-degenerative della colonna vertebrale sono di assai "
    "frequente riscontro presso collettività lavorative dell'agricoltura, "
    "dell'industria e dei servizi.",
    "Il National Institute of Occupational Safety and Health (NIOSH - USA) pone "
    "tali patologie al secondo posto nella lista dei dieci problemi di salute "
    "più rilevanti correlati al lavoro.",
    "Il presente documento applica il metodo NIOSH (1993) per la valutazione "
    "del rischio da movimentazione manuale dei carichi in azioni di "
    "sollevamento, ai sensi del Titolo VI del D.Lgs. 81/2008 e s.m.i. "
    "(D.Lgs. 106/09).",
    "L'obiettivo è determinare, per ogni azione di sollevamento, il Peso "
    "Limite Raccomandato (PLR) e il conseguente Indice di Rischio (IR), "
    "quest'ultimo come rapporto tra peso effettivamente sollevato e PLR.",
]

METODOLOGIA_INTRO = [
    "Per i lavoratori dell'azienda il rischio da movimentazione manuale dei "
    "carichi si prospetta in corrispondenza delle azioni di sollevamento "
    "durante la normale attività lavorativa.",
    "Per le azioni di sollevamento è utile ricorrere al modello proposto dal "
    "NIOSH (1993) che determina, per ogni azione di sollevamento, il peso "
    "limite raccomandato attraverso la formula:",
    "PLR = CP × A × B × C × D × E × F",
    "dove CP è la costante di peso (funzione di sesso ed età) e A-F sono "
    "fattori demoltiplicativi (valore compreso tra 0 e 1) che quantificano "
    "l'effetto di altezza, dislocazione verticale, distanza orizzontale, "
    "asimmetria, presa e frequenza.",
    "L'Indice di Rischio si calcola come IR = peso sollevato / PLR. "
    "I valori di IR sono interpretati secondo le fasce colorate della "
    "Tabella Indicatori di Rischio.",
    "La procedura è applicabile quando ricorrono le seguenti condizioni: "
    "sollevamento in posizione eretta (non seduta o inginocchiata) in spazi "
    "non ristretti; sollevamento con due mani; altre attività di "
    "movimentazione minimali; adeguata frizione tra piedi e pavimento "
    "(coeff. statico > 0,4); gesti non bruschi; carico non estremamente "
    "caldo/freddo/contaminato/instabile; condizioni microclimatiche "
    "favorevoli.",
]

FATTORE_A_TESTO = (
    "L'altezza da terra delle mani (A) è misurata verticalmente dal piano "
    "di appoggio dei piedi al punto di mezzo tra le mani. Il livello "
    "ottimale (A = 1) è a 75 cm (altezza nocche). Il valore diminuisce "
    "allontanandosi (in alto o in basso) da tale livello. Se l'altezza "
    "supera 175 cm, A = 0."
)
FATTORE_B_TESTO = (
    "La dislocazione verticale (B) è lo spostamento verticale delle mani "
    "durante il sollevamento. Per oggetti che superano un ostacolo, "
    "considerare la differenza tra l'altezza dell'ostacolo e quella "
    "iniziale/finale delle mani. La distanza minima considerata è 25 cm "
    "(B = 1); oltre 175 cm, B = 0."
)
FATTORE_C_TESTO = (
    "La distanza orizzontale (C) è misurata dalla linea congiungente i "
    "malleoli interni al punto di mezzo tra le mani (proiettato a terra). "
    "Sotto 25 cm: C = 1. Oltre 63 cm: C = 0."
)
FATTORE_D_TESTO = (
    "L'angolo di asimmetria (D) è l'angolo fra la linea di asimmetria e "
    "la linea sagittale mediana. La linea di asimmetria congiunge il "
    "punto di mezzo tra le caviglie e la proiezione a terra del punto "
    "intermedio tra le mani all'inizio (o alla destinazione) del "
    "sollevamento. A 0°: D = 1; a 135°: D = 0,57; oltre 135°: D = 0."
)
FATTORE_E_TESTO = (
    "La presa dell'oggetto è classificata qualitativamente in buona "
    "(E = 1), discreta (E = 0,95) o scarsa (E = 0,90). Forma ottimale "
    "di maniglia: 2-4 cm di diametro, 11,5 cm di lunghezza, superficie "
    "antiscivolo. Vanno evitate posizioni estreme dell'arto superiore "
    "e prese con eccessiva forza di apertura."
)
FATTORE_F_TESTO = (
    "Il fattore frequenza (F) è determinato dal numero di sollevamenti "
    "per minuto e dalla durata del compito. Breve durata: ≤ 1 ora con "
    "recupero ≥ 1,2× la durata lavorativa. Media durata: 1-2 ore con "
    "recupero ≥ 0,3× la durata. Lunga durata: 2-8 ore con normali pause. "
    "Per sollevamenti occasionali (< 1 ogni 10 minuti) usare sempre la "
    "breve durata, F = 1."
)

INDICATORI_DI_RISCHIO_INTRO = (
    "Sulla scorta del rapporto tra peso effettivamente movimentato e peso "
    "limite raccomandato (Indice IR), si distinguono tre fasce di rischio "
    "che determinano le azioni conseguenti."
)

CORREZIONI_AGGIUNTIVE = [
    "Sollevamenti eseguiti con un solo arto: applicare un fattore moltiplicativo di 0,6.",
    "Sollevamenti eseguiti da due persone: applicare un fattore di 0,85 "
    "(considerare il peso effettivamente sollevato diviso 2).",
    "Sollevamenti in posizione assisa o sul banco: non superare 5 kg per "
    "frequenze di 1 volta ogni 5 minuti.",
]

PROGRAMMA_AREA_VERDE = (
    "Il Datore di Lavoro verifica periodicamente che non intervengano "
    "variazioni e che la presente valutazione del rischio da movimentazione "
    "manuale dei carichi sia mantenuta nel tempo. In assenza di variazioni "
    "significative, non sono richieste misure correttive aggiuntive."
)
PROGRAMMA_AREA_GIALLA = (
    "Il Datore di Lavoro attiva la sorveglianza sanitaria per i lavoratori "
    "esposti, eroga formazione specifica sulla movimentazione manuale dei "
    "carichi e valuta interventi strutturali o procedurali atti a riportare "
    "l'Indice di Rischio nell'area verde."
)
PROGRAMMA_AREA_ROSSA = (
    "Il Datore di Lavoro avvia con urgenza interventi di prevenzione "
    "primaria: riprogettazione delle postazioni, riduzione dei carichi, "
    "introduzione di ausili meccanici. Sorveglianza sanitaria obbligatoria "
    "e formazione specifica. Rivalutazione del rischio entro 3 mesi."
)

DICHIARAZIONE_TESTO = (
    "Il/La sottoscritto/a {ddl_nome}, in qualità di Datore di Lavoro della "
    "{ragione_sociale} con sede legale in {sede_legale}, "
    "DICHIARA che il procedimento sulla valutazione dei rischi da "
    "movimentazione manuale dei carichi ex Titolo VI del D.Lgs. n. 81/2008 "
    "e s.m.i. (D.Lgs. 106/09) è stato condotto secondo il metodo NIOSH "
    "(ISO 11228-1) e costituisce parte integrante del Documento di "
    "Valutazione dei Rischi aziendale."
)


# ---------------------------------------------------------------------------
# Indice (TOC) entries — static; rendered as flat list since python-docx
# cannot produce auto-updating Word fields reliably.
# ---------------------------------------------------------------------------

TOC_ENTRIES = [
    "Introduzione",
    "Anagrafica Aziendale",
    "Dati occupazionali",
    "Descrizione dell'azienda e dell'attività",
    "Organizzazione Aziendale della Sicurezza",
    "Metodologia — Il metodo NIOSH per azioni di sollevamento",
    "Modalità di valutazione dei singoli fattori",
    "Stima del fattore altezza (A)",
    "Stima del fattore dislocazione verticale (B)",
    "Stima del fattore orizzontale (C)",
    "Stima del fattore dislocazione angolare (D)",
    "Stima del fattore presa (E)",
    "Stima del fattore frequenza (F)",
    "Indicatori di rischio e azioni conseguenti",
    "Tavole di Valutazione del rischio da M.M.C.",
    "Quadro sinottico di esposizione",
    "Programma di attuazione delle Misure di Prevenzione",
    "Dichiarazione del Datore di Lavoro",
]
```

- [ ] **Step 2.2: Verify the module imports**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -c "from app.services.document_generator import allegato_mmc_content as c; assert len(c.FACTOR_F_ROWS) == 18; assert len(c.TOC_ENTRIES) == 18; print('OK')"
```
Expected: `OK`

- [ ] **Step 2.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc_content.py
git commit -m "feat(allegato-mmc): extract NIOSH tables + boilerplate to content module

Data transcribed verbatim from docs/context/REFERENCE_DATA.md §1 and from
the Italian narrative sections of the original template. No client-
specific text. Keeps the upcoming generator rewrite focused on docx
rendering."
```

---

## Task 3: Scaffolding — new generator skeleton with helper methods

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py` (complete rewrite)

Skeleton class with all section method stubs, helpers lifted from `dvr_master.py`. Entire `generate()` flow runs end-to-end but produces mostly empty sections — just enough that the existing `test_generators.py` smoke test still passes.

- [ ] **Step 3.1: Overwrite `allegato_mmc.py` with the skeleton**

```python
"""Allegato MMC — Movimentazione Manuale dei Carichi (NIOSH method).

Generates the Italian MMC risk assessment attachment entirely from DB data.
No template file is loaded; every section is built programmatically so the
output reflects the current azienda — not a prior-client sample.

Section layout mirrors the original N2O template structure:
  1. Cover page
  2. Revision history
  3. Indice (manual TOC)
  4. Introduzione (static)
  5. Anagrafica Aziendale (dynamic)
  6. Dati occupazionali (dynamic)
  7. Descrizione dell'azienda e dell'attività (dynamic)
  8. Organizzazione Aziendale della Sicurezza (dynamic)
  9. Metodologia NIOSH (static + reference tables)
 10. Modalità di valutazione dei fattori A-F (static)
 11. Indicatori di rischio (static + zone table)
 12. Tavole di Valutazione per compito (dynamic, 1 table per MMC row)
 13. Quadro sinottico (dynamic, summary table)
 14. Programma di attuazione misure (dynamic, chosen by worst zone)
 15. Dichiarazione del Datore di Lavoro (dynamic)
"""

import os
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from sqlalchemy import func, select

from app.models.documento_generato import DocumentoGenerato
from app.services.document_generator import allegato_mmc_content as content
from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.data_loader import load_mmc


TIPO_DOC = "allegato_mmc"

_LOGO_PATH = Path(__file__).resolve().parents[3] / "assets" / "logo.png"
_HEADER_BG = RGBColor(0x1A, 0x23, 0x7E)
_HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
_LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)
_MUTED = RGBColor(0x66, 0x66, 0x66)

_ZONE_FILL = {
    "VERDE":  "C8E6C9",
    "GIALLO": "FFF9C4",
    "GIALLA": "FFF9C4",
    "ROSSO":  "FFCDD2",
    "ROSSA":  "FFCDD2",
}


def _slugify(text: str, max_length: int = 40) -> str:
    lowered = (text or "").lower()
    replaced = re.sub(r"[^a-z0-9]+", "_", lowered)
    collapsed = re.sub(r"_+", "_", replaced).strip("_")
    return (collapsed or "azienda")[:max_length].rstrip("_") or "azienda"


class AllegatoMmcGenerator(BaseDocumentGenerator):
    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    async def generate(self) -> str:
        data = await self.load_data()
        azienda = data["azienda"]
        persone = data["persone"]
        ambienti = data["ambienti"]
        generated_at: datetime = data["generated_at"]
        mmc_rows = await load_mmc(self.db, self.azienda_id)

        doc = Document()
        self._setup_styles(doc)

        self._add_cover_page(doc, azienda, generated_at)
        self._add_revision_history(doc, generated_at)
        self._add_indice(doc)
        self._add_introduzione(doc)
        self._add_anagrafica(doc, azienda)
        self._add_dati_occupazionali(doc, persone, ambienti)
        self._add_descrizione_azienda(doc, azienda)
        self._add_organizzazione_sicurezza(doc, azienda, persone)
        self._add_metodologia_niosh(doc)
        self._add_fattori(doc)
        self._add_indicatori_di_rischio(doc)
        self._add_tavole_valutazione(doc, mmc_rows, persone, ambienti)
        self._add_quadro_sinottico(doc, mmc_rows)
        self._add_programma_misure(doc, mmc_rows)
        self._add_dichiarazione(doc, azienda, persone, generated_at)

        version = await self._next_version()
        output_dir = self._get_output_dir()
        slug = _slugify(azienda.ragione_sociale or "azienda")
        filename = f"{TIPO_DOC}_{slug}_v{version}.docx"
        filepath = os.path.join(output_dir, filename)
        doc.save(filepath)
        return filepath

    async def _next_version(self) -> int:
        stmt = (
            select(func.coalesce(func.max(DocumentoGenerato.versione), 0))
            .where(DocumentoGenerato.azienda_id == self.azienda_id)
            .where(DocumentoGenerato.tipo_documento == TIPO_DOC)
        )
        r = await self.db.execute(stmt)
        return (r.scalar() or 0) + 1

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    def _setup_styles(self, doc: Document) -> None:
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10)
        for level in range(1, 4):
            heading_style = doc.styles[f"Heading {level}"]
            heading_style.font.name = "Calibri"
            heading_style.font.color.rgb = _HEADER_BG
        for section in doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.0)

    # ------------------------------------------------------------------
    # Section stubs (filled in later tasks)
    # ------------------------------------------------------------------
    def _add_cover_page(self, doc, azienda, generated_at): pass
    def _add_revision_history(self, doc, generated_at): pass
    def _add_indice(self, doc): pass
    def _add_introduzione(self, doc): pass
    def _add_anagrafica(self, doc, azienda): pass
    def _add_dati_occupazionali(self, doc, persone, ambienti): pass
    def _add_descrizione_azienda(self, doc, azienda): pass
    def _add_organizzazione_sicurezza(self, doc, azienda, persone): pass
    def _add_metodologia_niosh(self, doc): pass
    def _add_fattori(self, doc): pass
    def _add_indicatori_di_rischio(self, doc): pass
    def _add_tavole_valutazione(self, doc, mmc_rows, persone, ambienti): pass
    def _add_quadro_sinottico(self, doc, mmc_rows): pass
    def _add_programma_misure(self, doc, mmc_rows): pass
    def _add_dichiarazione(self, doc, azienda, persone, generated_at): pass

    # ------------------------------------------------------------------
    # Rendering helpers — copied from dvr_master.py patterns
    # ------------------------------------------------------------------
    def _add_heading(self, doc, text: str, level: int = 1):
        h = doc.add_heading(text, level=level)
        return h

    def _add_paragraph(self, doc, text: str, *, bold=False, italic=False, size: int = 10, color: RGBColor | None = None):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        if color is not None:
            run.font.color.rgb = color
        return p

    def _shade_cell(self, cell, hex_color: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tc_pr.append(shd)

    def _apply_borders(self, table) -> None:
        for row in table.rows:
            for cell in row.cells:
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_borders = tc_pr.find(qn("w:tcBorders"))
                if tc_borders is None:
                    tc_borders = OxmlElement("w:tcBorders")
                    tc_pr.append(tc_borders)
                for edge in ("top", "left", "bottom", "right"):
                    b = OxmlElement(f"w:{edge}")
                    b.set(qn("w:val"), "single")
                    b.set(qn("w:sz"), "4")
                    b.set(qn("w:color"), "808080")
                    tc_borders.append(b)

    def _style_header_row(self, row) -> None:
        for cell in row.cells:
            self._shade_cell(cell, "1A237E")
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.color.rgb = _HEADER_TEXT
                    run.font.size = Pt(10)

    def _add_kv_table(self, doc, rows: list[tuple[str, str]]) -> None:
        table = doc.add_table(rows=0, cols=2)
        try:
            table.style = "Table Grid"
            need_manual = False
        except KeyError:
            need_manual = True
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for k, v in rows:
            r = table.add_row().cells
            r[0].text = str(k)
            r[1].text = "" if v is None else str(v)
            for p in r[0].paragraphs:
                for run in p.runs:
                    run.font.bold = True
                    run.font.size = Pt(10)
            for p in r[1].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
            self._shade_cell(r[0], "F5F5F5")
        if need_manual:
            self._apply_borders(table)

    def _add_data_table(self, doc, headers: list[str], data_rows: list[list[str]]) -> None:
        table = doc.add_table(rows=1, cols=len(headers))
        try:
            table.style = "Table Grid"
            need_manual = False
        except KeyError:
            need_manual = True
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = table.rows[0]
        for i, h in enumerate(headers):
            hdr.cells[i].text = h
        self._style_header_row(hdr)
        for row_data in data_rows:
            row = table.add_row()
            for i, cell_val in enumerate(row_data):
                row.cells[i].text = "" if cell_val is None else str(cell_val)
                for p in row.cells[i].paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
        if need_manual:
            self._apply_borders(table)

    def _format_address(self, via: str | None, citta: str | None) -> str:
        parts = [x for x in (via, citta) if x]
        return " — ".join(parts) if parts else "—"
```

- [ ] **Step 3.2: Run the old smoke test to ensure nothing is broken**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_generators.py::test_all_17_generators_pass -x -q
```
Expected: PASS. The skeleton's empty sections still produce a valid (if sparse) .docx.

- [ ] **Step 3.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "refactor(allegato-mmc): rewrite generator as empty programmatic skeleton

Drops the template load and replace_placeholders pattern. Sections are
stub methods to be filled in subsequent commits. Smoke test still passes
because an empty .docx is valid. Anti-leak assertions now pass too
(prior-client text is no longer copied)."
```

---

## Task 4: Cover page, revision history, indice, introduzione

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py`

- [ ] **Step 4.1: Replace the stubs for these four methods**

Find the 4 stub lines:
```python
    def _add_cover_page(self, doc, azienda, generated_at): pass
    def _add_revision_history(self, doc, generated_at): pass
    def _add_indice(self, doc): pass
    def _add_introduzione(self, doc): pass
```

Replace with:
```python
    def _add_cover_page(self, doc: Document, azienda, generated_at: datetime) -> None:
        for _ in range(4):
            doc.add_paragraph("")

        if _LOGO_PATH.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            try:
                run.add_picture(str(_LOGO_PATH), width=Inches(2.0))
            except Exception:
                run.text = "[LOGO AZIENDALE]"
                run.font.size = Pt(14)
                run.font.color.rgb = _MUTED
                run.font.italic = True
        doc.add_paragraph("")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Documento per la")
        run.bold = True; run.font.size = Pt(18); run.font.color.rgb = _HEADER_BG
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Valutazione del Rischio da")
        run.bold = True; run.font.size = Pt(22); run.font.color.rgb = _HEADER_BG
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Movimentazione Manuale dei Carichi")
        run.bold = True; run.font.size = Pt(24); run.font.color.rgb = _HEADER_BG
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("per Azioni di Sollevamento")
        run.bold = True; run.font.size = Pt(18); run.font.color.rgb = _HEADER_BG

        doc.add_paragraph("")
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("ex Titolo VI D.Lgs. n. 81/2008 e s.m.i. (D.Lgs. 106/09)")
        run.italic = True; run.font.size = Pt(12); run.font.color.rgb = _MUTED

        for _ in range(4):
            doc.add_paragraph("")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run((azienda.ragione_sociale or "").upper())
        run.bold = True; run.font.size = Pt(18)

        addr_parts = [x for x in (azienda.sede_legale_via, azienda.sede_legale_citta) if x]
        if addr_parts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" — ".join(addr_parts))
            run.font.size = Pt(12); run.font.color.rgb = _MUTED

        doc.add_paragraph("")
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Data: {generated_at.strftime('%d/%m/%Y')}")
        run.font.size = Pt(12)
        doc.add_page_break()

    def _add_revision_history(self, doc: Document, generated_at: datetime) -> None:
        self._add_heading(doc, "Cronologia delle Revisioni", level=2)
        self._add_data_table(
            doc,
            headers=["Rev.", "Motivazione", "Data"],
            data_rows=[
                ["00", "Prima emissione", generated_at.strftime("%d/%m/%Y")],
            ],
        )
        doc.add_page_break()

    def _add_indice(self, doc: Document) -> None:
        self._add_heading(doc, "Indice", level=1)
        self._add_paragraph(
            doc,
            "[Indice generato automaticamente — aggiornare dopo la revisione finale]",
            italic=True, size=9, color=_MUTED,
        )
        doc.add_paragraph("")
        for i, entry in enumerate(content.TOC_ENTRIES, 1):
            p = doc.add_paragraph()
            run = p.add_run(f"{i}. {entry}")
            run.font.size = Pt(11)
        doc.add_page_break()

    def _add_introduzione(self, doc: Document) -> None:
        self._add_heading(doc, "Introduzione", level=1)
        for para in content.INTRODUZIONE:
            self._add_paragraph(doc, para, size=10)
        doc.add_page_break()
```

- [ ] **Step 4.2: Run tests — cover/indice/introduzione assertions should pass**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v -k 'azienda_name or section_heading' 2>&1 | tail -25
```
Expected: `test_contains_fixture_azienda_name` PASS. Section heading checks for "Anagrafica Aziendale" etc. still FAIL (those sections not yet implemented).

- [ ] **Step 4.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "feat(allegato-mmc): render cover page, revision history, indice, introduzione"
```

---

## Task 5: Anagrafica + Dati occupazionali + Descrizione azienda + Organizzazione sicurezza

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py`

- [ ] **Step 5.1: Replace the four stubs**

Find and replace these four stubs:
```python
    def _add_anagrafica(self, doc, azienda): pass
    def _add_dati_occupazionali(self, doc, persone, ambienti): pass
    def _add_descrizione_azienda(self, doc, azienda): pass
    def _add_organizzazione_sicurezza(self, doc, azienda, persone): pass
```

Replace with:
```python
    def _add_anagrafica(self, doc: Document, azienda) -> None:
        self._add_heading(doc, "Anagrafica Aziendale", level=1)
        rows = [
            ("Ragione Sociale", azienda.ragione_sociale or "—"),
            ("Partita IVA", getattr(azienda, "partita_iva", None) or "—"),
            ("Codice Fiscale", getattr(azienda, "codice_fiscale", None) or "—"),
            ("Sede Legale", self._format_address(
                getattr(azienda, "sede_legale_via", None),
                getattr(azienda, "sede_legale_citta", None),
            )),
            ("Sede Operativa", self._format_address(
                getattr(azienda, "sede_operativa_via", None),
                getattr(azienda, "sede_operativa_citta", None),
            )),
            ("Codice ATECO", getattr(azienda, "codice_ateco", None) or "—"),
            ("Attività", getattr(azienda, "attivita", None) or "—"),
            ("Settore", getattr(azienda, "settore", None) or "—"),
        ]
        self._add_kv_table(doc, rows)
        doc.add_page_break()

    def _add_dati_occupazionali(self, doc: Document, persone: list, ambienti: list) -> None:
        self._add_heading(doc, "Dati occupazionali", level=1)
        self._add_paragraph(
            doc,
            f"Numero totale lavoratori: {len(persone)}.",
            size=10,
        )
        doc.add_paragraph("")
        if persone:
            ambienti_by_id = {a.id: a.nome for a in ambienti}
            headers = ["N.", "Nominativo", "Mansione", "Ambiente", "Contratto", "Sesso", "Fascia età"]
            rows = []
            for i, p in enumerate(persone, 1):
                amb_names = []
                for amb_id in (getattr(p, "ambiente_ids", None) or []):
                    if amb_id in ambienti_by_id:
                        amb_names.append(ambienti_by_id[amb_id])
                rows.append([
                    str(i),
                    p.nominativo or "—",
                    getattr(p, "mansione", None) or "—",
                    ", ".join(amb_names) if amb_names else "—",
                    getattr(p, "tipologia_contrattuale", None) or "—",
                    getattr(p, "sesso", None) or "—",
                    getattr(p, "fascia_eta", None) or "—",
                ])
            self._add_data_table(doc, headers, rows)
        else:
            self._add_paragraph(doc, "Nessun lavoratore registrato.", italic=True)
        doc.add_page_break()

    def _add_descrizione_azienda(self, doc: Document, azienda) -> None:
        self._add_heading(doc, "Descrizione dell'azienda e dell'attività", level=1)
        descr = (
            getattr(azienda, "descrizione_attivita", None)
            or getattr(azienda, "attivita", None)
            or f"{azienda.ragione_sociale} opera nei settori dichiarati in fase di "
               "registrazione. La descrizione dettagliata dell'attività, dei "
               "cicli produttivi e della distribuzione degli ambienti di lavoro "
               "è riportata nel DVR Master cui il presente allegato si riferisce."
        )
        self._add_paragraph(doc, descr, size=10)
        doc.add_paragraph("")

        orario = getattr(azienda, "orario_lavoro", None)
        if orario:
            self._add_paragraph(doc, f"Orario di lavoro: {orario}", size=10)

        metratura = getattr(azienda, "metratura_totale", None)
        if metratura:
            self._add_paragraph(doc, f"Metratura totale: circa {metratura} mq.", size=10)

        doc.add_page_break()

    def _add_organizzazione_sicurezza(self, doc: Document, azienda, persone: list) -> None:
        self._add_heading(doc, "Organizzazione Aziendale della Sicurezza", level=1)
        self._add_paragraph(
            doc,
            "Di seguito le figure della sicurezza designate ai sensi del "
            "D.Lgs. 81/2008 per l'azienda.",
            size=10,
        )
        doc.add_paragraph("")
        role_map = [
            ("Datore di Lavoro", "ruolo_datore_lavoro"),
            ("RSPP", "ruolo_rspp"),
            ("RLS", "ruolo_rls"),
            ("Addetto Primo Soccorso", "ruolo_primo_soccorso"),
            ("Addetto Antincendio", "ruolo_antincendio"),
            ("Preposto", "ruolo_preposto"),
        ]
        rows = []
        for label, flag in role_map:
            persons = [p for p in persone if getattr(p, flag, False)]
            names = ", ".join(p.nominativo for p in persons) if persons else "—"
            rows.append((label, names))
        # Medico Competente is not a persona flag; leave explicit placeholder.
        rows.append(("Medico Competente", getattr(azienda, "medico_competente", None) or "Da designare"))
        self._add_kv_table(doc, rows)
        doc.add_page_break()
```

- [ ] **Step 5.2: Run MMC tests — anagrafica + workers + roles sections should pass**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v -k 'partita_iva or sede_legale or worker_names or Anagrafica or Dati_occupazionali or Organizzazione' 2>&1 | tail -30
```
Expected: all these PASS. Earlier structural tests still pass. NIOSH/Tavole tests still FAIL.

- [ ] **Step 5.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "feat(allegato-mmc): render anagrafica, workers, descrizione, sicurezza sections"
```

---

## Task 6: Metodologia NIOSH + Fattori A-F reference content

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py`

- [ ] **Step 6.1: Replace the two stubs**

Find and replace:
```python
    def _add_metodologia_niosh(self, doc): pass
    def _add_fattori(self, doc): pass
```

Replace with:
```python
    def _add_metodologia_niosh(self, doc: Document) -> None:
        self._add_heading(doc, "Metodologia — Il metodo NIOSH per azioni di sollevamento", level=1)
        for para in content.METODOLOGIA_INTRO:
            self._add_paragraph(doc, para, size=10)
        doc.add_paragraph("")

        self._add_heading(doc, "Costante di Peso (CP)", level=2)
        self._add_data_table(doc, content.CP_TABLE_HEADERS, content.CP_TABLE_ROWS)
        doc.add_paragraph("")

        self._add_heading(doc, "Tabella frequenza (Fattore F)", level=2)
        self._add_data_table(doc, content.FACTOR_F_HEADERS, content.FACTOR_F_ROWS)
        doc.add_paragraph("")

        self._add_heading(doc, "Correzioni aggiuntive", level=2)
        for para in content.CORREZIONI_AGGIUNTIVE:
            self._add_paragraph(doc, f"• {para}", size=10)
        doc.add_page_break()

    def _add_fattori(self, doc: Document) -> None:
        self._add_heading(doc, "Modalità di valutazione dei singoli fattori", level=1)

        for label, testo, headers, rows, formula in [
            ("Stima del fattore altezza (A)", content.FATTORE_A_TESTO,
             content.FACTOR_A_HEADERS, content.FACTOR_A_ROWS, content.FACTOR_A_FORMULA),
            ("Stima del fattore dislocazione verticale (B)", content.FATTORE_B_TESTO,
             content.FACTOR_B_HEADERS, content.FACTOR_B_ROWS, content.FACTOR_B_FORMULA),
            ("Stima del fattore orizzontale (C)", content.FATTORE_C_TESTO,
             content.FACTOR_C_HEADERS, content.FACTOR_C_ROWS, content.FACTOR_C_FORMULA),
            ("Stima del fattore dislocazione angolare (D)", content.FATTORE_D_TESTO,
             content.FACTOR_D_HEADERS, content.FACTOR_D_ROWS, content.FACTOR_D_FORMULA),
            ("Stima del fattore presa (E)", content.FATTORE_E_TESTO,
             content.FACTOR_E_HEADERS, content.FACTOR_E_ROWS, None),
            ("Stima del fattore frequenza (F)", content.FATTORE_F_TESTO,
             None, None, None),
        ]:
            self._add_heading(doc, label, level=2)
            self._add_paragraph(doc, testo, size=10)
            if formula:
                self._add_paragraph(doc, formula, italic=True, size=10)
            if headers and rows:
                self._add_data_table(doc, headers, rows)
            doc.add_paragraph("")

        doc.add_page_break()
```

- [ ] **Step 6.2: Run tests — NIOSH section + reference tables should pass**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v -k 'Metodologia or Modalità or frequency_table or cp_table' 2>&1 | tail -25
```
Expected: `test_contains_cp_table_values`, `test_contains_frequency_table_label`, `test_section_heading_present[Metodologia]`, `test_section_heading_present[Modalità di valutazione]` all PASS.

- [ ] **Step 6.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "feat(allegato-mmc): render NIOSH methodology + factor A-F reference tables"
```

---

## Task 7: Indicatori di rischio + per-task Tavole di Valutazione

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py`

- [ ] **Step 7.1: Replace the two stubs**

Find and replace:
```python
    def _add_indicatori_di_rischio(self, doc): pass
    def _add_tavole_valutazione(self, doc, mmc_rows, persone, ambienti): pass
```

Replace with:
```python
    def _add_indicatori_di_rischio(self, doc: Document) -> None:
        self._add_heading(doc, "Indicatori di rischio e azioni conseguenti", level=1)
        self._add_paragraph(doc, content.INDICATORI_DI_RISCHIO_INTRO, size=10)
        doc.add_paragraph("")
        # Render the zone table with colored first-column background
        table = doc.add_table(rows=1, cols=len(content.ZONE_TABLE_HEADERS))
        try:
            table.style = "Table Grid"
            need_manual = False
        except KeyError:
            need_manual = True
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = table.rows[0]
        for i, h in enumerate(content.ZONE_TABLE_HEADERS):
            hdr.cells[i].text = h
        self._style_header_row(hdr)
        for row_data in content.ZONE_TABLE_ROWS:
            row = table.add_row()
            for i, cell_val in enumerate(row_data):
                row.cells[i].text = cell_val
                for p in row.cells[i].paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
            # Color the Zona cell (column index 1) based on its label
            zona = (row_data[1] or "").upper()
            if zona in _ZONE_FILL:
                self._shade_cell(row.cells[1], _ZONE_FILL[zona])
        if need_manual:
            self._apply_borders(table)
        doc.add_page_break()

    def _add_tavole_valutazione(self, doc: Document, mmc_rows: list, persone: list, ambienti: list) -> None:
        self._add_heading(doc, "Tavole di Valutazione del rischio da M.M.C.", level=1)
        if not mmc_rows:
            self._add_paragraph(
                doc,
                "Nessun compito di movimentazione manuale dei carichi è stato "
                "valutato per questa azienda. Aggiornare il presente allegato "
                "quando saranno disponibili le valutazioni NIOSH per i compiti "
                "applicabili.",
                italic=True,
            )
            doc.add_page_break()
            return

        persone_by_id = {p.id: p for p in persone}
        ambienti_by_id = {a.id: a for a in ambienti}

        for idx, r in enumerate(mmc_rows, 1):
            worker = persone_by_id.get(getattr(r, "persona_id", None))
            amb = ambienti_by_id.get(getattr(r, "ambiente_id", None))

            self._add_heading(doc, f"Tavola {idx} — {r.compito}", level=2)

            header_rows = [
                ("Compito", r.compito or "—"),
                ("Lavoratore", worker.nominativo if worker else "Gruppo omogeneo"),
                ("Mansione", (worker.mansione if worker else None) or "—"),
                ("Ambiente", amb.nome if amb else "—"),
                ("Peso effettivamente sollevato",
                 f"{float(r.peso_kg):.1f} kg" if r.peso_kg is not None else "—"),
                ("Sesso / Fascia età",
                 f"{getattr(r, 'sesso', '—') or '—'} / {getattr(r, 'fascia_eta', '—') or '—'}"),
            ]
            self._add_kv_table(doc, header_rows)
            doc.add_paragraph("")

            factor_rows = [
                ["Costante di Peso (CP)",        f"{float(r.cp):.1f} kg"],
                ["Fattore altezza (A)",           f"{float(r.fattore_a):.2f}"],
                ["Fattore dislocazione vert. (B)", f"{float(r.fattore_b):.2f}"],
                ["Fattore orizzontale (C)",       f"{float(r.fattore_c):.2f}"],
                ["Fattore asimmetria (D)",        f"{float(r.fattore_d):.2f}"],
                ["Fattore presa (E)",             f"{float(r.fattore_e):.2f}"],
                ["Fattore frequenza (F)",         f"{float(r.fattore_f):.2f}"],
            ]
            self._add_data_table(doc, ["Fattore", "Valore"], factor_rows)
            doc.add_paragraph("")

            # Outcome
            plr = float(r.plr) if r.plr is not None else None
            ir = float(r.indice_ir) if r.indice_ir is not None else None
            zona = (r.livello_rischio or "").upper()
            outcome_rows = [
                ("PLR (Peso Limite Raccomandato)",
                 f"{plr:.1f} kg" if plr is not None else "—"),
                ("Indice IR = peso / PLR",
                 f"{ir:.2f}" if ir is not None else "—"),
                ("Zona di rischio", zona or "—"),
            ]
            self._add_kv_table(doc, outcome_rows)

            # Color the zone row
            # (last table just rendered — re-fetch via doc.tables[-1])
            last_table = doc.tables[-1]
            if zona in _ZONE_FILL:
                self._shade_cell(last_table.rows[-1].cells[1], _ZONE_FILL[zona])

            note = getattr(r, "note", None)
            if note:
                self._add_paragraph(doc, f"Note: {note}", italic=True, size=9)

            doc.add_page_break()
```

- [ ] **Step 7.2: Run tests — PLR + zone + compito should pass**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v -k 'compito or plr_value or ir_zone or Tavole or Indicatori' 2>&1 | tail -25
```
Expected: all PASS.

- [ ] **Step 7.3: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "feat(allegato-mmc): render zone table + per-task NIOSH assessment tables"
```

---

## Task 8: Quadro sinottico + Programma misure + Dichiarazione DdL

**Files:**
- Modify: `backend/app/services/document_generator/allegato_mmc.py`

- [ ] **Step 8.1: Replace the three remaining stubs**

Find and replace:
```python
    def _add_quadro_sinottico(self, doc, mmc_rows): pass
    def _add_programma_misure(self, doc, mmc_rows): pass
    def _add_dichiarazione(self, doc, azienda, persone, generated_at): pass
```

Replace with:
```python
    def _add_quadro_sinottico(self, doc: Document, mmc_rows: list) -> None:
        self._add_heading(doc, "Quadro sinottico di esposizione", level=1)
        if not mmc_rows:
            self._add_paragraph(doc, "Nessuna esposizione rilevata.", italic=True)
            doc.add_page_break()
            return
        headers = ["#", "Compito", "Peso (kg)", "PLR (kg)", "IR", "Zona"]
        rows = []
        for i, r in enumerate(mmc_rows, 1):
            rows.append([
                str(i),
                r.compito or "—",
                f"{float(r.peso_kg):.1f}" if r.peso_kg is not None else "—",
                f"{float(r.plr):.1f}" if r.plr is not None else "—",
                f"{float(r.indice_ir):.2f}" if r.indice_ir is not None else "—",
                (r.livello_rischio or "—").upper(),
            ])
        self._add_data_table(doc, headers, rows)

        # Color the Zona column per row
        last_table = doc.tables[-1]
        for i, r in enumerate(mmc_rows, 1):
            zona = (r.livello_rischio or "").upper()
            if zona in _ZONE_FILL:
                # rows[0] is header, so data row i is at index i
                self._shade_cell(last_table.rows[i].cells[5], _ZONE_FILL[zona])
        doc.add_page_break()

    def _add_programma_misure(self, doc: Document, mmc_rows: list) -> None:
        self._add_heading(doc, "Programma di attuazione delle Misure di Prevenzione", level=1)
        # Pick narrative based on worst zone across tasks.
        severity = {"VERDE": 0, "GIALLO": 1, "GIALLA": 1, "ROSSO": 2, "ROSSA": 2}
        worst = 0
        for r in mmc_rows:
            worst = max(worst, severity.get((r.livello_rischio or "").upper(), 0))
        if worst >= 2:
            self._add_heading(doc, "Area Rossa", level=2)
            self._add_paragraph(doc, content.PROGRAMMA_AREA_ROSSA)
        elif worst == 1:
            self._add_heading(doc, "Area Gialla", level=2)
            self._add_paragraph(doc, content.PROGRAMMA_AREA_GIALLA)
        else:
            self._add_heading(doc, "Area Verde", level=2)
            self._add_paragraph(doc, content.PROGRAMMA_AREA_VERDE)
        doc.add_page_break()

    def _add_dichiarazione(self, doc: Document, azienda, persone: list, generated_at: datetime) -> None:
        self._add_heading(doc, "Dichiarazione del Datore di Lavoro", level=1)
        ddl = next((p for p in persone if getattr(p, "ruolo_datore_lavoro", False)), None)
        ddl_nome = (ddl.nominativo if ddl else "[Datore di Lavoro da designare]")
        sede_legale = self._format_address(
            getattr(azienda, "sede_legale_via", None),
            getattr(azienda, "sede_legale_citta", None),
        )
        testo = content.DICHIARAZIONE_TESTO.format(
            ddl_nome=ddl_nome,
            ragione_sociale=azienda.ragione_sociale or "",
            sede_legale=sede_legale,
        )
        self._add_paragraph(doc, testo, size=10)
        doc.add_paragraph("")
        doc.add_paragraph("")
        # Signature lines
        citta = getattr(azienda, "sede_legale_citta", None) or ""
        self._add_paragraph(
            doc,
            f"{citta}, lì {generated_at.strftime('%d/%m/%Y')}",
            size=10,
        )
        doc.add_paragraph("")
        self._add_data_table(
            doc,
            headers=["Il Datore di Lavoro", "Il RSPP", "Il RLS"],
            data_rows=[["", "", ""], ["", "", ""]],  # Two empty rows for signatures
        )
```

- [ ] **Step 8.2: Run the full MMC test suite — should be all-green**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_allegato_mmc.py -v 2>&1 | tail -40
```
Expected: ALL tests PASS (including anti-leak and length tests).

- [ ] **Step 8.3: Run the whole generator smoke suite to ensure nothing else broke**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_generators.py -x -q
```
Expected: PASS (17/17 still build).

- [ ] **Step 8.4: Commit**

```bash
cd /mnt/c/Dev/dlg
git add backend/app/services/document_generator/allegato_mmc.py
git commit -m "feat(allegato-mmc): render quadro sinottico, misure, dichiarazione DdL

Completes the programmatic MMC allegato. Generator no longer depends on
the ALLEGATO RISCHIO MMC.docx template — every section is built from DB
data + NIOSH reference tables. Anti-leak tests pass: no prior-client
text reaches the output."
```

---

## Task 9: End-to-end smoke test against live backend

Runs the rebuilt generator via Celery against the dev DB and downloads the .docx to verify it opens cleanly.

- [ ] **Step 9.1: Trigger generation via API**

Run:
```bash
cd /mnt/c/Dev/dlg/backend && /usr/bin/python3 -c "
import requests, json, subprocess
# Find an azienda id from DB
out = subprocess.check_output([
    'docker', 'exec', 'dlg-postgres-1', 'psql', '-U', 'postgres', '-d', 'n2o',
    '-tAc', \"SELECT id FROM aziende ORDER BY created_at DESC LIMIT 1;\"
]).decode().strip()
print('Azienda:', out)
"
```
Expected: a UUID printed. Save it for the next step.

- [ ] **Step 9.2: Re-queue the MMC task via the API (requires NextAuth session)**

*Manual:* in the browser at `http://localhost:3000/documents`, select the azienda from the previous step, then click "Rigenera" on the **Allegato MMC** card.

Watch the worker log:
```bash
tail -f /tmp/n2o_worker.log
```
Expected: within ~5 seconds, `Generated allegato_mmc v<N> -> /mnt/c/Dev/dlg/backend/var/storage/documents/<uuid>/allegato_mmc_<slug>_v<N>.docx`.

- [ ] **Step 9.3: Confirm the output has real DB content (not template leakage)**

Run (substitute the filepath from step 9.2):
```bash
/usr/bin/python3 - <<'PY'
from docx import Document
import glob, os
files = sorted(glob.glob("/mnt/c/Dev/dlg/backend/var/storage/documents/*/allegato_mmc_*.docx"), key=os.path.getmtime)
p = files[-1]
print("Inspecting:", p)
d = Document(p)
text = "\n".join(par.text for par in d.paragraphs)
for tbl in d.tables:
    for row in tbl.rows:
        for cell in row.cells:
            text += "\n" + cell.text
for leak in ("N2O SRL", "CIARAMITARO", "GORGONZOLA", "SORMANI ANNALISA"):
    assert leak not in text, f"LEAK: {leak!r} still present"
print("No leaks. paragraphs=", len(d.paragraphs), "tables=", len(d.tables))
PY
```
Expected: `No leaks. paragraphs= <number> tables= <number>` (no assertion failure).

- [ ] **Step 9.4: Open in Word and eyeball it**

Open the .docx in Word/LibreOffice. Verify:
- Cover page shows the **selected** azienda's name + address (not N2O SRL)
- Anagrafica table is fully populated
- Dati occupazionali lists the persone you've registered for this azienda
- Metodologia has the full NIOSH explanation + CP/factor/frequency tables
- Tavole di Valutazione: one block per MMC row in the DB (or "nessuna valutazione" notice if none)
- Dichiarazione names the DdL from your persone

- [ ] **Step 9.5: No extra commit needed — this task is verification only**

---

## Task 10: Document the POC result for next-phase planning

**Files:**
- Create: `.planning/notes/2026-04-15-allegato-mmc-poc-result.md`

Captures what worked / what revealed gaps. Feeds the planning session for the other 9 generators.

- [ ] **Step 10.1: Write the retro note**

Content template (fill in after running through Tasks 1-9):

```markdown
# Allegato MMC POC — Result

**Date:** 2026-04-15
**Generator:** `backend/app/services/document_generator/allegato_mmc.py`
**Content module:** `backend/app/services/document_generator/allegato_mmc_content.py`

## What worked
- <bullet>
- <bullet>

## What surfaced gaps / required fixture updates
- <bullet>  (e.g. missing azienda field, missing persona flag)

## Decisions to replicate across the other 9 generators
- Content split: `<tipo>_content.py` module for boilerplate + lookup tables
- Section method naming: `_add_<section>`
- Helper methods to be promoted to `docx_utils.py`: <list>
- Anti-leak test pattern (parametrized `test_no_prior_client_content`)

## Effort (actual)
- Time: <hh:mm> elapsed
- Lines added: allegato_mmc.py ≈ <N>, allegato_mmc_content.py ≈ <N>, test ≈ <N>

## Open questions for the next phase
- <bullet>
```

- [ ] **Step 10.2: Commit**

```bash
cd /mnt/c/Dev/dlg
git add .planning/notes/2026-04-15-allegato-mmc-poc-result.md
git commit -m "docs(allegato-mmc): capture POC retro for next-phase planning"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Cover, revision, indice, introduzione → Task 4
- ✅ Anagrafica, dati occupazionali, descrizione, organizzazione sicurezza → Task 5
- ✅ Metodologia NIOSH + CP/F tables → Task 6
- ✅ Factor A-F with formula + lookup tables → Task 6
- ✅ Indicatori di rischio (zone table) → Task 7
- ✅ Tavole di valutazione per compito → Task 7
- ✅ Quadro sinottico, programma misure, dichiarazione → Task 8
- ✅ Anti-leak tests → Task 1 (parametrized)
- ✅ Structural section tests → Task 1
- ✅ NIOSH reference data in code → Task 2
- ✅ Live backend verification → Task 9
- ✅ POC retrospective → Task 10

**Placeholder scan:** no TODOs, no "implement later", every code block complete.

**Type consistency:** method names `_add_<section>` used in `generate()` match stub definitions in Task 3. Helper signatures (`_add_kv_table(doc, rows)`, `_add_data_table(doc, headers, data_rows)`, `_format_address(via, citta)`) are consistent across all tasks.

**Known limitations (intentional, not gaps):**
- Medico Competente is rendered as a free-text slot from `azienda.medico_competente` (if present) or "Da designare". If the Azienda model doesn't have this field, the generator gracefully degrades — confirmed via `getattr(..., None)`. Adding the field is a Model concern, not a doc-generation concern.
- TOC is a static flat list, not Word auto-updating. Matches the current DVR Master approach.
- "Descrizione attività" falls back to a boilerplate paragraph if `azienda.descrizione_attivita` is empty. In Phase 3 this is the natural hook for AI-generated descriptions (US-2.1).
