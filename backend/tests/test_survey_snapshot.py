"""Unit tests for US-5.2 — survey-snapshot drift + field-dependency catalog.

Pins the deterministic-hash contract that the documents pipeline relies
on, plus the field-dependency lookup the frontend tooltip consumes.
Tests are unit-level (no live DB) — they instantiate model objects
directly and feed them through ``compute_survey_snapshot_hash`` via a
stubbed AsyncSession that satisfies the small subset of the protocol the
hasher uses.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

from app.data.field_dependencies import (
    FIELD_DEPENDENCIES,
    all_field_dependencies,
    dependencies_for,
)
from app.models.documento_generato import DocumentoGenerato
from app.schemas.document import DocumentResponse


# ---------------------------------------------------------------------------
# DocumentoGenerato model + schema contract
# ---------------------------------------------------------------------------


def test_documento_generato_exposes_snapshot_columns():
    cols = {c.name: c for c in DocumentoGenerato.__table__.columns}
    assert "survey_snapshot_hash" in cols, "survey_snapshot_hash column missing"
    assert "stale_snapshot" in cols, "stale_snapshot column missing"
    # Hash is nullable (legacy rows pre-migration) but stale_snapshot is
    # NOT NULL with a server default — the documents page treats absence
    # as "fresh enough" only via the schema default, not via NULL.
    assert cols["survey_snapshot_hash"].nullable is True
    assert cols["stale_snapshot"].nullable is False


def test_document_response_defaults_stale_snapshot_to_false():
    """Frontend reads `doc.stale_snapshot` to decide whether to render the
    amber 'rigenera' banner. Default must be False so legacy rows from
    before the column existed don't blink red on page load."""
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "tipo_documento": "dvr_master",
        "versione": 1,
        "status": "completed",
        "created_at": "2026-04-15T12:00:00+00:00",
    }
    resp = DocumentResponse(**payload)
    assert resp.stale_snapshot is False


def test_document_response_carries_explicit_stale_snapshot_true():
    payload = {
        "id": uuid.uuid4(),
        "azienda_id": uuid.uuid4(),
        "tipo_documento": "dvr_master",
        "versione": 1,
        "status": "completed",
        "created_at": "2026-04-15T12:00:00+00:00",
        "stale_snapshot": True,
    }
    resp = DocumentResponse(**payload)
    assert resp.stale_snapshot is True


# ---------------------------------------------------------------------------
# Snapshot hash determinism
# ---------------------------------------------------------------------------


class _StubResult:
    """Minimal stand-in for SQLAlchemy `Result` that the hasher uses.

    Implements just `scalar_one_or_none()` and `scalars().all()`.
    """

    def __init__(self, value=None, items=None):
        self._value = value
        self._items = list(items or [])

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _StubSession:
    """AsyncSession stub. Returns a fixed sequence of `_StubResult`s, in the
    order the hasher executes its queries: azienda, persone, ambienti,
    attrezzature, sostanze, rischi.
    """

    def __init__(self, *results: _StubResult):
        self._iter = iter(results)

    async def execute(self, *_args, **_kw):
        return next(self._iter)


def _stub_persona(**kw):
    class P:
        pass

    p = P()
    p.id = kw.get("id", uuid.uuid4())
    p.nominativo = kw.get("nominativo", "Mario Rossi")
    p.mansione = kw.get("mansione", "operaio")
    p.tipologia_contrattuale = kw.get("tipologia_contrattuale", "indeterminato")
    p.sesso = kw.get("sesso", "M")
    p.fascia_eta = kw.get("fascia_eta", ">18")
    p.ruolo_rspp = kw.get("ruolo_rspp", False)
    p.ruolo_rls = kw.get("ruolo_rls", False)
    p.ruolo_primo_soccorso = kw.get("ruolo_primo_soccorso", False)
    p.ruolo_antincendio = kw.get("ruolo_antincendio", False)
    p.ruolo_preposto = kw.get("ruolo_preposto", False)
    p.ruolo_datore_lavoro = kw.get("ruolo_datore_lavoro", False)
    return p


def _stub_azienda(**kw):
    class A:
        pass

    a = A()
    a.ragione_sociale = kw.get("ragione_sociale", "Acme SRL")
    a.partita_iva = kw.get("partita_iva", "12345678901")
    a.sede_legale_via = None
    a.sede_legale_citta = None
    a.sede_operativa_via = None
    a.sede_operativa_citta = "Milano"
    a.attivita = "produzione"
    a.codice_ateco = "25.62.00"
    a.orario_lavoro = "8-17"
    a.metratura_totale = 500
    a.zona_sismica = 3
    a.descrizione_attivita = kw.get("descrizione_attivita", None)
    a.contesto_territoriale = None
    return a


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.new_event_loop().run_until_complete(coro)


def test_snapshot_hash_is_deterministic_for_identical_state():
    from app.services.survey_snapshot import compute_survey_snapshot_hash

    az_id = uuid.uuid4()
    p_id = uuid.uuid4()

    def make_session():
        return _StubSession(
            _StubResult(value=_stub_azienda()),
            _StubResult(items=[_stub_persona(id=p_id)]),
            _StubResult(items=[]),
            _StubResult(items=[]),
            _StubResult(items=[]),
            _StubResult(items=[]),
        )

    h1 = _run(compute_survey_snapshot_hash(az_id, make_session()))
    h2 = _run(compute_survey_snapshot_hash(az_id, make_session()))
    assert h1 == h2
    # SHA-256 hex string
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_snapshot_hash_changes_when_azienda_field_changes():
    from app.services.survey_snapshot import compute_survey_snapshot_hash

    az_id = uuid.uuid4()
    p_id = uuid.uuid4()

    h1 = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda(descrizione_attivita="vecchia")),
                _StubResult(items=[_stub_persona(id=p_id)]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    h2 = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda(descrizione_attivita="nuova")),
                _StubResult(items=[_stub_persona(id=p_id)]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    assert h1 != h2, "descrizione_attivita change must shift the hash"


def test_snapshot_hash_changes_when_persona_mansione_changes():
    from app.services.survey_snapshot import compute_survey_snapshot_hash

    az_id = uuid.uuid4()
    p_id = uuid.uuid4()

    h1 = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda()),
                _StubResult(items=[_stub_persona(id=p_id, mansione="operaio")]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    h2 = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda()),
                _StubResult(items=[_stub_persona(id=p_id, mansione="capoturno")]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    # AC1 — survey edits propagate. The hash MUST change so the worker
    # flips stale_snapshot=True and the documents page surfaces the
    # rigenera banner.
    assert h1 != h2


def test_snapshot_hash_invariant_to_persona_load_order():
    """Two different load orders for the same set of persone must hash
    identically — pins the sorted-by-id step in the hasher."""
    from app.services.survey_snapshot import compute_survey_snapshot_hash

    az_id = uuid.uuid4()
    a_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    b_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    p_a = _stub_persona(id=a_id, nominativo="Anna")
    p_b = _stub_persona(id=b_id, nominativo="Bruno")

    h_ab = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda()),
                _StubResult(items=[p_a, p_b]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    h_ba = _run(
        compute_survey_snapshot_hash(
            az_id,
            _StubSession(
                _StubResult(value=_stub_azienda()),
                _StubResult(items=[p_b, p_a]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
                _StubResult(items=[]),
            ),
        )
    )
    assert h_ab == h_ba


def test_snapshot_hash_handles_missing_azienda():
    """Defensive: never raise; return a stable sentinel hash."""
    from app.services.survey_snapshot import compute_survey_snapshot_hash

    h = _run(
        compute_survey_snapshot_hash(uuid.uuid4(), _StubSession(_StubResult(value=None)))
    )
    assert len(h) == 64


# ---------------------------------------------------------------------------
# Field-dependency catalog (US-5.2 AC3)
# ---------------------------------------------------------------------------


def test_dependencies_for_known_field_returns_documents():
    deps = dependencies_for("persona.mansione")
    # Mansione drives DVR personnel + MMC + VDT + Stress + Gestanti + HACCP + POS.
    assert "dvr_master" in deps
    assert "mmc" in deps
    assert "vdt" in deps
    # Returns a fresh list each call — caller mutation must not leak back
    # into the catalog.
    deps.append("scratch")
    assert "scratch" not in dependencies_for("persona.mansione")


def test_dependencies_for_unknown_field_returns_empty():
    assert dependencies_for("nonexistent.field") == []
    assert dependencies_for("") == []


def test_all_field_dependencies_returns_complete_catalog():
    snap = all_field_dependencies()
    assert snap.keys() == FIELD_DEPENDENCIES.keys()
    # Same defensive copy contract as `dependencies_for`.
    snap.clear()
    assert all_field_dependencies(), "snapshot is supposed to be a copy"


def test_field_dependency_doc_types_are_known():
    """All values must be known generator identifiers — mistyped names
    here would silently produce empty tooltip rows on the frontend."""
    known = {
        "dvr_master",
        "mmc",
        "vdt",
        "stress",
        "incendio",
        "microclima",
        "gestanti",
        "biologico",
        "duvri",
        "pee_azienda",
        "pee_comune",
        "pos",
        "haccp",
        "haccp_forms",
    }
    for field, docs in FIELD_DEPENDENCIES.items():
        for doc in docs:
            assert doc in known, f"unknown doc type {doc!r} for field {field!r}"


def test_field_dependency_anagrafica_includes_all_writers():
    """Spot-check: ragione_sociale must propagate to every doc that has
    a cover page or letterhead."""
    deps = set(dependencies_for("azienda.ragione_sociale"))
    for must_have in {"dvr_master", "duvri", "pos", "haccp", "pee_azienda"}:
        assert must_have in deps, f"{must_have} missing from ragione_sociale deps"


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_router_registers_field_dependencies_endpoint():
    from app.api.v1.router import api_router

    paths = {
        (method, getattr(r, "path", ""))
        for r in api_router.routes
        for method in getattr(r, "methods", set()) or set()
    }
    assert (
        "GET",
        "/api/v1/lookup/field-dependencies",
    ) in paths, "GET /lookup/field-dependencies missing"
