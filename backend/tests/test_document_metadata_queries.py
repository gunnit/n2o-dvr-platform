"""The document list, status and version queries never load a document's bytes.

``documenti_generati.file_content`` holds the whole .docx or .zip: a DVR with
the 2026-11 art is about 3 MB, and the documents page polls the list every
3 s while anything is generating. The endpoints that only describe documents
must not drag those bytes out of Postgres (final review, I-1). Nor do the
editor's preview on a cache hit and its overrides PATCH, run on every
autosave (final review, P-2).

Unit-level, like the rest of the off-DB API tests: the session is a mock that
records each statement, and the SQL is compiled for Postgres to see which
columns it selects.
"""

from __future__ import annotations

import io
import uuid
from collections import OrderedDict
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from docx import Document
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import documents as documents_api
from app.core.exceptions import NotFoundError
from app.schemas.document import (
    DocumentBatchRequest,
    DocumentGenerateRequest,
    OverridesPatchRequest,
)


def _sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


class _MetadataOnlyDocument:
    """A listed row whose bytes were deferred: touching them is a bug.

    In the async session a deferred column that is read lazy-loads, and the
    load raises (MissingGreenlet), so the response must be built without it.
    """

    def __init__(self, **fields):
        self.__dict__.update(fields)

    @property
    def file_content(self):
        raise AssertionError("file_content was read while building a metadata response")


def _listed_document(azienda_id: uuid.UUID) -> _MetadataOnlyDocument:
    return _MetadataOnlyDocument(
        id=uuid.uuid4(),
        azienda_id=azienda_id,
        tipo_documento="dvr_master",
        versione=3,
        status="completed",
        file_path="/data/documents/x/dvr_master_acme_v3.docx",
        gdrive_file_id=None,
        gdoc_file_id=None,
        options=None,
        error_message=None,
        created_at=datetime(2026, 11, 10, 9, 30),
        stale_snapshot=False,
    )


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def one_or_none(self):
        return self._rows[0] if self._rows else None


def _recording_session(result):
    db = AsyncMock(spec=AsyncSession)
    statements = []

    async def execute(statement, *args, **kwargs):
        statements.append(statement)
        return result

    db.execute.side_effect = execute
    return db, statements


@pytest.mark.asyncio
async def test_list_documents_never_selects_the_document_bytes():
    azienda_id, org_id = uuid.uuid4(), uuid.uuid4()
    row = _listed_document(azienda_id)
    db, statements = _recording_session(_Rows([(row, "Mario Rossi")]))

    with (
        patch.object(documents_api, "_get_azienda", new=AsyncMock()),
        patch(
            "app.services.survey_snapshot.mark_documents_stale_for",
            new=AsyncMock(return_value=0),
        ),
    ):
        listed = await documents_api.list_documents(azienda_id, org_id, db)

    assert [(doc.id, doc.versione, doc.generated_by_name) for doc in listed] == [
        (row.id, 3, "Mario Rossi")
    ]
    (query,) = statements
    sql = _sql(query)
    assert "documenti_generati.versione" in sql
    assert "file_content" not in sql


@pytest.mark.asyncio
async def test_document_status_never_selects_the_document_bytes():
    azienda_id, org_id = uuid.uuid4(), uuid.uuid4()
    row = _listed_document(azienda_id)
    db, statements = _recording_session(_Rows([(row, None)]))

    with patch.object(documents_api, "_get_azienda", new=AsyncMock()):
        status = await documents_api.get_document_status(azienda_id, row.id, org_id, db)

    assert (status.id, status.status) == (row.id, "completed")
    (query,) = statements
    sql = _sql(query)
    assert "documenti_generati.status" in sql
    assert "file_content" not in sql


class _VersionResult:
    """Answers both the old query (the latest full row) and the new one
    (``max(versione)``), so the test fails on the SQL, not on a mock."""

    def __init__(self, statement, latest_version):
        self._full_row = "file_content" in _sql(statement)
        self._latest = latest_version

    def scalar_one_or_none(self):
        if self._full_row:
            return None if self._latest is None else Mock(versione=self._latest)
        return self._latest

    def scalar(self):
        return self.scalar_one_or_none()

    def scalar_one(self):
        return self.scalar_one_or_none()


def _generation_session(latest_version):
    db = AsyncMock(spec=AsyncSession)
    statements = []
    added = []

    async def execute(statement, *args, **kwargs):
        statements.append(statement)
        return _VersionResult(statement, latest_version)

    async def refresh(doc, *args, **kwargs):
        doc.id = uuid.uuid4()
        doc.created_at = datetime(2026, 11, 10)

    db.execute.side_effect = execute
    db.refresh.side_effect = refresh
    db.add = Mock(side_effect=added.append)
    return db, statements, added


def _generation_patches():
    async_none = {"new": AsyncMock(return_value=None)}
    return (
        patch.object(documents_api, "_get_azienda", **async_none),
        patch.object(documents_api, "ensure_subscription_active"),
        patch.object(documents_api, "ensure_doc_type_allowed"),
        patch.object(documents_api, "_ensure_company_slot_available", **async_none),
        patch.object(documents_api, "_ensure_anagrafica_complete_for_dvr", **async_none),
        patch.object(documents_api, "_ensure_dvr_exists_for_dependent", **async_none),
        patch.object(
            documents_api, "_check_batch_preconditions", new=AsyncMock(return_value=[])
        ),
        patch.object(documents_api, "_preflight_dvr_photo_transport", **async_none),
        patch.object(documents_api, "_resolve_user_name", **async_none),
        patch.object(documents_api, "_enqueue_generation"),
    )


async def _generate(endpoint, body, db):
    patches = _generation_patches()
    for active in patches:
        active.start()
    try:
        user = Mock(id=uuid.uuid4())
        await endpoint(uuid.uuid4(), body, uuid.uuid4(), user, Mock(), db)
    finally:
        for active in reversed(patches):
            active.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(("latest", "expected"), [(None, 1), (3, 4)])
@pytest.mark.parametrize(
    ("endpoint", "body", "types"),
    [
        (
            documents_api.generate_document,
            DocumentGenerateRequest(tipo_documento="allegato_vdt"),
            ["allegato_vdt"],
        ),
        (
            documents_api.batch_generate_documents,
            DocumentBatchRequest(tipi_documento=["allegato_vdt", "allegato_mmc"]),
            ["allegato_vdt", "allegato_mmc"],
        ),
    ],
    ids=["generate", "batch"],
)
async def test_next_version_is_read_as_max_versione_without_loading_rows(
    endpoint, body, types, latest, expected
):
    db, statements, added = _generation_session(latest)

    await _generate(endpoint, body, db)

    # The numbering is unchanged: one more than the highest version of that
    # type for the azienda, 1 for the first.
    assert [(doc.tipo_documento, doc.versione) for doc in added] == [
        (tipo, expected) for tipo in types
    ]
    assert len(statements) == len(types)
    for statement in statements:
        sql = _sql(statement)
        assert "max(documenti_generati.versione)" in sql
        assert "file_content" not in sql


# --- The editor: preview, its images, the overrides PATCH (final review P-2) --


def _editor_row(**fields) -> _MetadataOnlyDocument:
    """A completed .docx row as the editor endpoints read it, bytes left in
    Postgres: reading ``file_content`` off it fails the test."""
    base = dict(
        id=uuid.uuid4(),
        azienda_id=uuid.uuid4(),
        tipo_documento="dvr_master",
        versione=2,
        status="completed",
        file_name="DVR_acme_v2.docx",
        file_path=None,
        stale_snapshot=False,
        generation_completed_at=datetime(2026, 11, 10, 9, 30),
        content_overrides={"3": "Testo salvato"},
    )
    base.update(fields)
    return _MetadataOnlyDocument(**base)


class _Result:
    """One statement's result: the (row, azienda name) pair of the
    org-scoped lookup, or a single scalar (the bytes)."""

    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


def _scripted_session(*results):
    db = AsyncMock(spec=AsyncSession)
    statements = []
    pending = list(results)

    async def execute(statement, *args, **kwargs):
        statements.append(statement)
        return _Result(pending.pop(0))

    db.execute.side_effect = execute
    return db, statements


def _docx_bytes() -> bytes:
    doc = Document()
    doc.add_paragraph("Il documento di valutazione dei rischi")
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_preview_on_a_cache_hit_never_selects_the_document_bytes(monkeypatch):
    row = _editor_row()
    cached = {"blocks": [], "furniture": None, "page_setup": None, "style_props": {}}
    monkeypatch.setattr(documents_api, "_PREVIEW_CACHE", OrderedDict({row.id: cached}))
    db, statements = _scripted_session((row, "Acme Srl"))

    preview = await documents_api.preview_document(row.id, uuid.uuid4(), db)

    assert (preview.id, preview.overrides) == (row.id, {"3": "Testo salvato"})
    (lookup,) = statements
    sql = _sql(lookup)
    assert "documenti_generati.content_overrides" in sql
    assert "file_content" not in sql


@pytest.mark.asyncio
async def test_preview_on_a_cache_miss_reads_the_bytes_in_a_select_of_their_own(monkeypatch):
    row = _editor_row()
    monkeypatch.setattr(documents_api, "_PREVIEW_CACHE", OrderedDict())
    db, statements = _scripted_session((row, "Acme Srl"), _docx_bytes())

    preview = await documents_api.preview_document(row.id, uuid.uuid4(), db)

    assert [block.runs[0].text for block in preview.blocks] == ["Il documento di valutazione dei rischi"]
    assert row.id in documents_api._PREVIEW_CACHE
    lookup, content = (_sql(statement) for statement in statements)
    assert "file_content" not in lookup
    assert content.startswith("SELECT documenti_generati.file_content \nFROM documenti_generati")
    assert "documenti_generati.id =" in content


@pytest.mark.asyncio
async def test_overrides_patch_never_selects_the_document_bytes():
    row = _editor_row()
    db, statements = _scripted_session((row, "Acme Srl"))

    out = await documents_api.patch_document_overrides(
        row.id, OverridesPatchRequest(set={"4": "Nuovo testo", "3": None}), uuid.uuid4(), db
    )

    assert out.overrides == {"4": "Nuovo testo"}
    db.commit.assert_awaited_once()
    (lookup,) = statements
    assert "file_content" not in _sql(lookup)


def _database_url() -> str | None:
    import os

    from app.db.session import _normalize_async_url

    url = os.environ.get("DATABASE_URL")
    return _normalize_async_url(url) if url else None


async def _reachable(url: str | None) -> bool:
    if not url:
        return False
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


def _postgres_reachable() -> bool:
    import asyncio

    try:
        return asyncio.run(_reachable(_database_url()))
    except Exception:
        return False


@pytest.mark.skipif(not _postgres_reachable(), reason="no reachable Postgres in DATABASE_URL")
@pytest.mark.asyncio
async def test_editor_endpoints_on_a_real_session_read_the_bytes_only_when_needed(monkeypatch):
    """The same contract against Postgres: the deferred column is never
    lazy-loaded (that raises under the async session), the preview fetches
    it once on a miss, and the PATCH and its refresh never select it."""
    from sqlalchemy import event, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_database_url())
    selected = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selected.append(" ".join(statement.split()))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    org_id, azienda_id, document_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(documents_api, "_PREVIEW_CACHE", OrderedDict())
    try:
        async with factory() as s:
            await s.execute(
                text("INSERT INTO organizations (id, name) VALUES (:i, :n)"),
                {"i": org_id, "n": f"pytest-bytes-{org_id}"},
            )
            await s.execute(
                text(
                    "INSERT INTO aziende (id, organization_id, ragione_sociale, survey_status)"
                    " VALUES (:a, :o, 'Acme Srl', 'draft')"
                ),
                {"a": azienda_id, "o": org_id},
            )
            await s.execute(
                text(
                    "INSERT INTO documenti_generati (id, azienda_id, tipo_documento, versione, status,"
                    " file_content, file_name, generation_attempts)"
                    " VALUES (:d, :a, 'dvr_master', 1, 'completed', :c, 'DVR_v1.docx', 1)"
                ),
                {"d": document_id, "a": azienda_id, "c": _docx_bytes()},
            )
            await s.commit()

        def bytes_selects():
            return [sql for sql in selected if "file_content" in sql]

        async with factory() as s:
            selected.clear()
            miss = await documents_api.preview_document(document_id, org_id, s)
            assert [block.runs[0].text for block in miss.blocks] == ["Il documento di valutazione dei rischi"]
            (only,) = bytes_selects()
            assert only.startswith("SELECT documenti_generati.file_content FROM documenti_generati")

        async with factory() as s:
            selected.clear()
            hit = await documents_api.preview_document(document_id, org_id, s)
            assert hit.blocks == miss.blocks and selected and bytes_selects() == []

            selected.clear()
            out = await documents_api.patch_document_overrides(
                document_id, OverridesPatchRequest(set={"0": "Testo modificato"}), org_id, s
            )
            assert out.overrides == {"0": "Testo modificato"} and selected and bytes_selects() == []

            selected.clear()
            with pytest.raises(NotFoundError):
                await documents_api.preview_document_image(document_id, "rId999", org_id, s)
            assert len(bytes_selects()) == 1
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM aziende WHERE organization_id=:o"), {"o": org_id})
            await s.execute(text("DELETE FROM organizations WHERE id=:o"), {"o": org_id})
            await s.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_preview_image_loads_the_bytes_with_the_row():
    """It always serves a picture out of the bytes: one query, bytes included."""
    row = SimpleNamespace(**vars(_editor_row()), file_content=_docx_bytes())
    db, statements = _scripted_session((row, "Acme Srl"))

    with pytest.raises(NotFoundError):  # the document has no such picture
        await documents_api.preview_document_image(row.id, "rId999", uuid.uuid4(), db)

    (lookup,) = statements
    assert "documenti_generati.file_content" in _sql(lookup)
