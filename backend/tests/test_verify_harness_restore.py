"""The off-DB generator harness puts the real methods back (final review, T3).

``scripts/verify_all_generators.patch_generators`` swaps ``load_data``,
``_load_dvr_extras``, the output directory, the version helpers and every data
loader for fixture fakes. It used to leave them swapped for the rest of the
pytest session, so a later DB-backed test that called a generator silently
ran the fakes. It now returns a restore function (the CLI ignores it) and
``patched_generators`` wraps it in a ``with`` block.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from app.services.document_generator.base import BaseDocumentGenerator
from app.services.document_generator.dvr_master import DVRMasterGenerator
from scripts import verify_dvr_luca_fixture

BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MISSING = object()

# The real state of every object the harness patches, taken while this module
# is collected: before any test has run, so before any test could leak.
_OWNERS = verify_dvr_luca_fixture._generator_patch_objects()
_REAL = [(owner, dict(vars(owner))) for owner in _OWNERS]
_REAL_LOAD_DVR_EXTRAS = DVRMasterGenerator._load_dvr_extras
_REAL_LOAD_DATA = BaseDocumentGenerator.load_data


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "verify_all_generators_restore",
        str(BACKEND_ROOT / "scripts" / "verify_all_generators.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _differences() -> list[tuple[str, str]]:
    """(owner, attribute) pairs that are not the real ones."""
    found = []
    for owner, real in _REAL:
        current = vars(owner)
        for name in real.keys() | current.keys():
            if current.get(name, _MISSING) is not real.get(name, _MISSING):
                found.append((getattr(owner, "__name__", repr(owner)), name))
    return sorted(found)


@pytest.fixture
def real_generators(monkeypatch):
    """Start from the real methods even if an earlier test (one that cannot
    use the restore yet) leaked its patches; monkeypatch puts the session's
    state back afterwards."""
    for owner, real in _REAL:
        current = vars(owner)
        for name in current.keys() - real.keys():
            monkeypatch.delattr(owner, name)
        for name, value in real.items():
            if current.get(name, _MISSING) is not value:
                monkeypatch.setattr(owner, name, value)
    assert _differences() == []


def test_patch_generators_returns_a_restore_that_brings_the_real_methods_back(
    real_generators, tmp_path
):
    harness = _load_harness()

    restore = harness.patch_generators(harness.build_fixture(), str(tmp_path))

    patched = {name for _owner, name in _differences()}
    assert {
        "load_data",
        "_get_output_dir",
        "_load_dvr_extras",
        "_get_next_version",
        "_next_version",
        "load_mmc",
        "load_pee",
        "load_biologico",
    } <= patched
    assert DVRMasterGenerator._load_dvr_extras is not _REAL_LOAD_DVR_EXTRAS

    restore()

    assert _differences() == []
    assert DVRMasterGenerator._load_dvr_extras is _REAL_LOAD_DVR_EXTRAS
    assert BaseDocumentGenerator.load_data is _REAL_LOAD_DATA
    restore()  # a second call changes nothing
    assert _differences() == []


def test_patched_block_restores_after_a_generation_and_after_an_error(
    real_generators, tmp_path
):
    harness = _load_harness()
    fixture = harness.build_fixture()

    with harness.patched_generators(fixture, str(tmp_path)):
        ok, _path, message = asyncio.run(
            harness.run_one("ALLEGATO_VDT", fixture["azienda"].id)
        )
        assert ok, message
    assert _differences() == []

    with pytest.raises(RuntimeError, match="consumer failed"):
        with harness.patched_generators(fixture, str(tmp_path)):
            assert BaseDocumentGenerator.load_data is not _REAL_LOAD_DATA
            raise RuntimeError("consumer failed")
    assert _differences() == []
