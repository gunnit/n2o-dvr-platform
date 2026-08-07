"""Regressions for durable document-task delivery and redelivery."""

from types import SimpleNamespace
import uuid

import pytest

from app.services import gdrive_service
from app.tasks import document_tasks


class _DocumentResult:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


class _CompletedDocumentSession:
    def __init__(self, document):
        self._document = document
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        return _DocumentResult(self._document)

    async def commit(self):
        self.commit_calls += 1


def test_generation_task_requeues_if_worker_is_lost():
    """An abrupt worker loss leaves the accepted task available for redelivery."""
    assert document_tasks.generate_document_task.acks_late is True
    assert document_tasks.generate_document_task.reject_on_worker_lost is True


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", ["completed", "ready"])
async def test_terminal_document_redelivery_returns_without_side_effects(
    monkeypatch, terminal_status
):
    """A post-commit redelivery preserves either terminal lifecycle row."""
    document_id = uuid.uuid4()
    document = SimpleNamespace(
        id=document_id,
        azienda_id=uuid.uuid4(),
        tipo_documento="DVR_MASTER",
        versione=1,
        options=None,
        status=terminal_status,
        file_path="/persisted/document.docx",
        file_name="document.docx",
        file_content=b"persisted document",
        error_message=None,
        generation_started_at=None,
        generation_completed_at=None,
        survey_snapshot_hash=None,
        stale_snapshot=False,
    )
    before = vars(document).copy()
    session = _CompletedDocumentSession(document)

    def unexpected_generator(*args, **kwargs):
        pytest.fail("generator lookup must not run for a terminal document")

    async def unexpected_async_boundary(*args, **kwargs):
        pytest.fail("post-generation work must not run for a terminal document")

    async def snapshot_hash(*args, **kwargs):
        return "snapshot"

    monkeypatch.setattr(document_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(document_tasks, "compute_survey_snapshot_hash", snapshot_hash)
    monkeypatch.setattr(document_tasks, "get_generator_for", unexpected_generator)
    monkeypatch.setattr(
        document_tasks, "record_activation_for_azienda", unexpected_async_boundary
    )
    monkeypatch.setattr(
        gdrive_service, "upload_generated_document", unexpected_async_boundary
    )

    await document_tasks._run_generation(document_id)

    assert vars(document) == before
    assert session.commit_calls == 0
