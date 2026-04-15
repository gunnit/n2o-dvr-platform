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
