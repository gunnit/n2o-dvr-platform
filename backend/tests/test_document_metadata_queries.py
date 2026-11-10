"""The document list, status and version queries never load a document's bytes.

``documenti_generati.file_content`` holds the whole .docx or .zip: a DVR with
the 2026-11 art is about 3 MB, and the documents page polls the list every
3 s while anything is generating. The endpoints that only describe documents
must not drag those bytes out of Postgres (final review, I-1).

Unit-level, like the rest of the off-DB API tests: the session is a mock that
records each statement, and the SQL is compiled for Postgres to see which
columns it selects.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import documents as documents_api
from app.schemas.document import DocumentBatchRequest, DocumentGenerateRequest


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
