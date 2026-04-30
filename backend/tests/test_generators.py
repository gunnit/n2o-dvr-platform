"""Integration test: every generator produces a valid .docx for Acme fixture.

This reuses scripts/verify_all_generators.py which monkey-patches the DB
loaders to run without a live Postgres. Under real deployment, generators
would run via Celery with the actual DB.
"""

import asyncio
import importlib
import os
import sys
import zipfile
from pathlib import Path

import pytest
from docx import Document


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))


def _load_verify():
    spec = importlib.util.spec_from_file_location(
        "verify_all_generators",
        str(BACKEND_ROOT / "scripts" / "verify_all_generators.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated_outputs(tmp_path_factory):
    out = tmp_path_factory.mktemp("gen_out")
    module = _load_verify()
    fixture = module.build_fixture()
    module.patch_generators(fixture, str(out))

    from app.services.document_generator.dispatcher import ALL_DOCUMENT_TYPES

    results = {}

    async def run_all():
        for tipo in ALL_DOCUMENT_TYPES:
            try:
                ok, path, msg = await module.run_one(tipo, fixture["azienda"].id)
                results[tipo] = (ok, path, msg)
            except Exception as e:
                results[tipo] = (False, "", str(e))

    asyncio.run(run_all())
    return results


def test_all_17_generators_pass(generated_outputs):
    failed = {k: v for k, v in generated_outputs.items() if not v[0]}
    assert not failed, f"Failed generators: {failed}"
    assert len(generated_outputs) == 17


def test_dvr_master_has_acme_name(generated_outputs):
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text += "\n" + cell.text
    assert "ACME" in full_text.upper()


def test_haccp_forms_produces_zip(generated_outputs):
    ok, path, _ = generated_outputs["HACCP_FORMS"]
    assert ok and path.endswith(".zip")
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as z:
        # Index + 16 forms = 17 entries
        assert len(z.namelist()) >= 16


def test_pos_has_significant_content(generated_outputs):
    """POS is the most complex document — should have many tables."""
    ok, path, _ = generated_outputs["POS"]
    assert ok and path
    doc = Document(path)
    assert len(doc.tables) >= 5


def test_biologico_all_three_variants_generate(generated_outputs):
    for key in ("ALLEGATO_BIOLOGICO_ALIMENTARE", "ALLEGATO_BIOLOGICO_ASILO", "ALLEGATO_BIOLOGICO_DENTISTI"):
        ok, path, _ = generated_outputs[key]
        assert ok and path.endswith(".docx"), f"{key} failed"


def test_vdt_emits_full_template_sections(generated_outputs):
    """Allegato VDT must emit every template section, not just a header +
    summary. The audit on 2026-04-29 caught the pre-rewrite generator only
    producing a few sections; this guards against regression to that state.
    """
    ok, path, _ = generated_outputs["ALLEGATO_VDT"]
    assert ok and path.endswith(".docx")
    doc = Document(path)

    headings = [
        p.text.strip() for p in doc.paragraphs
        if p.style.name.startswith("Heading") and p.text.strip()
    ]
    required = [
        "Indice",
        "Introduzione",
        "Anagrafica Aziendale",
        "Dati Occupazionali",
        "Organizzazione Aziendale della Sicurezza",
        "Principali fattori di rischio",
        "La postazione di lavoro",
        "Elenco postazioni VDT",
        "Tavole di Valutazione del Rischio VDT",
        "Quadro sinottico di esposizione",
        "Misure di prevenzione",
        "Programma di Attuazione delle Misure di Prevenzione",
        "Dichiarazione del Datore di Lavoro",
        "Firme",
    ]
    missing = [r for r in required if r not in headings]
    assert not missing, f"Allegato VDT missing sections: {missing}"


def test_vdt_quadro_sinottico_emits_classification(generated_outputs):
    """The quadro sinottico must show every valutazione row with its
    Esposto/Non Esposto classification — that's the per-worker summary
    the medico competente reads first.
    """
    ok, path, _ = generated_outputs["ALLEGATO_VDT"]
    assert ok and path
    doc = Document(path)

    sinottico_header = ("Nominativo", "Mansione", "Tempo di utilizzo (h/sett)", "Rischio VDT")
    matched = False
    for t in doc.tables:
        if not t.rows:
            continue
        header = tuple(c.text.strip() for c in t.rows[0].cells)
        if header == sinottico_header:
            matched = True
            assert len(t.rows) >= 2, "quadro sinottico has no data rows"
            risk_col = {row.cells[3].text.strip() for row in t.rows[1:]}
            assert risk_col & {"Esposto", "Non Esposto"}, (
                f"quadro sinottico Rischio VDT col missing classification: {risk_col}"
            )
            break
    assert matched, "VDT quadro sinottico table not found"


def test_dvr_total_table_count_hits_template_parity(generated_outputs):
    """US-2.8 AC1: DVR .docx emits enough tables to match the master template
    (Pre-Parte I + Parte I + II + III + IV).

    For the 6-env Acme fixture: 3 pre + 15 Parte I + 5 Parte II +
    (1 azienda + 6 envs × (identity + addetti + checklist + 2 cat)) +
    3 Parte IV = 57 tables. Real clients with richer per-env risk data
    climb toward the template's 111 organically.
    """
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)
    count = len(doc.tables)
    assert count >= 50, (
        f"DVR Master emitted only {count} tables; expected ≥50 for the "
        f"Acme fixture. Regression in Parte I/II/III/IV parity."
    )


def test_dvr_parte_i_has_anagrafica_and_hazard_library(generated_outputs):
    """US-2.8 AC1: Parte I must emit the anagrafica block, single-role title
    tables, and the 3-group static hazard library (Tables 4, 6–9, 15–17)."""
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)

    headers_seen = []
    for table in doc.tables:
        if not table.rows:
            continue
        header_cells = [cell.text.strip() for cell in table.rows[0].cells]
        headers_seen.append(tuple(header_cells))

    assert ("Datore di Lavoro",) in headers_seen, (
        "missing single-role Datore di Lavoro table (Template Table 6)"
    )
    assert ("Responsabile del Servizio di Prevenzione e Protezione",) in headers_seen, (
        "missing RSPP title table (Template Table 7)"
    )
    assert ("Rappresentante dei Lavoratori per la Sicurezza",) in headers_seen, (
        "missing RLS title table (Template Table 8)"
    )

    macro_headers = {"Rischi per la Sicurezza", "Rischi per la Salute", "Rischi Trasversali"}
    static_library_headers = [
        h for h in headers_seen
        if len(h) == 2 and h[1] in macro_headers and h[0] == "Categoria"
    ]
    assert len(static_library_headers) == 3, (
        f"expected 3 static hazard-library tables (Templates 15/16/17), "
        f"got {len(static_library_headers)}"
    )


def test_dvr_parte_ii_has_definizioni_and_criteria(generated_outputs):
    """US-2.8 AC1: Parte II must emit the Definizioni glossary and full
    P/D criteria tables (Templates 19, 21, 22)."""
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)

    found_definizioni = False
    found_prob = False
    found_danno = False
    for table in doc.tables:
        if not table.rows:
            continue
        header_cells = tuple(cell.text.strip() for cell in table.rows[0].cells)
        if header_cells == ("Termine", "Definizione"):
            found_definizioni = len(table.rows) >= 10
        if header_cells == ("P", "Livello", "Criteri"):
            found_prob = True
        if header_cells == ("D", "Livello", "Criteri"):
            found_danno = True

    assert found_definizioni, "missing Definizioni glossary (Template Table 19) with ≥10 rows"
    assert found_prob, "missing Scala di Probabilita with criteri column (Template Table 21)"
    assert found_danno, "missing Scala del Danno with criteri column (Template Table 22)"


def test_dvr_parte_iv_has_signature_table(generated_outputs):
    """US-2.8 AC1: Parte IV emits the improvement program grid and the 2×3
    signature block as a real table (Templates 109, 110)."""
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)

    found_program = False
    for table in doc.tables:
        if not table.rows:
            continue
        header_cells = [cell.text.strip() for cell in table.rows[0].cells]
        if (
            header_cells[:1] == ["Misure di miglioramento"]
            and "Tempi di attuazione" in header_cells
        ):
            found_program = True
            break
    assert found_program, (
        "missing improvement-program grid (Template Table 109)"
    )

    signature_match = False
    for table in doc.tables:
        if len(table.rows) != 2 or len(table.rows[0].cells) != 3:
            continue
        row0_text = " ".join(cell.text for cell in table.rows[0].cells)
        row1_text = " ".join(cell.text for cell in table.rows[1].cells)
        if "Datore di Lavoro" in row0_text and "Rappresentante dei Lavoratori" in row1_text:
            signature_match = True
            break
    assert signature_match, (
        "missing 2×3 signature table (Template Table 110)"
    )


def test_dvr_parte_iii_env_block_structure(generated_outputs):
    """US-2.8 AC1: each environment in Parte III emits the full template block.

    Expected per env: 1 identity table (Table 24), 1 addetti table (Table 25),
    1 SI/NO risk-category checklist (Table 26), plus 1 per-category 5-col risk
    table for every applicable macro-category. The Acme fixture has 6 envs
    each with 2 applicable risk categories → at least 6 × (3 + 2) = 30
    template-shaped tables in Parte III alone.
    """
    ok, path, _ = generated_outputs["DVR_MASTER"]
    assert ok and path
    doc = Document(path)

    headings = [
        p.text for p in doc.paragraphs
        if p.style.name.startswith("Heading")
    ]
    env_identity_headers = [
        h for h in headings
        if h.startswith("Identificazione dell'Ambiente di Lavoro")
    ]
    assert len(env_identity_headers) == 6, (
        f"expected one env-identity heading per Acme env (6), "
        f"got {len(env_identity_headers)}: {env_identity_headers}"
    )

    si_no_tables = 0
    macro_label_set = {"Rischi per la Sicurezza", "Rischi per la Salute", "Rischi Trasversali"}
    for table in doc.tables:
        cell_texts = {cell.text.strip() for row in table.rows for cell in row.cells}
        if macro_label_set.issubset(cell_texts) and "Applicabile" in cell_texts:
            si_no_tables += 1
    assert si_no_tables == 6, (
        f"expected one SI/NO risk-category checklist per env (6), "
        f"got {si_no_tables}"
    )

    category_headers_seen = 0
    for table in doc.tables:
        if not table.rows:
            continue
        header_texts = [cell.text.strip() for cell in table.rows[0].cells]
        if header_texts[:1] == ["PERICOLO"] and "I = P + 2*D" in header_texts:
            category_headers_seen += 1
    assert category_headers_seen >= 12, (
        f"expected ≥12 per-category risk tables (6 envs × 2 cats), "
        f"got {category_headers_seen}"
    )
