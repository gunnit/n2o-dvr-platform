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


def _document(*, status: str = "pending", generation_attempts: int = 0):
    return SimpleNamespace(
        id=uuid.uuid4(),
        azienda_id=uuid.uuid4(),
        tipo_documento="DVR_MASTER",
        versione=1,
        options=None,
        status=status,
        generation_attempts=generation_attempts,
        file_path=None,
        file_name=None,
        file_content=None,
        error_message=None,
        generation_started_at=None,
        generation_completed_at=None,
        survey_snapshot_hash=None,
        stale_snapshot=False,
    )


class _GenerationSession(_CompletedDocumentSession):
    def __init__(self, document, events):
        super().__init__(document)
        self._events = events

    async def commit(self):
        await super().commit()
        self._events.append(
            (
                "commit",
                self._document.generation_attempts,
                self._document.status,
            )
        )


def test_generation_task_requeues_if_worker_is_lost():
    """An abrupt worker loss leaves the accepted task available for redelivery."""
    assert document_tasks.generate_document_task.acks_late is True
    assert document_tasks.generate_document_task.reject_on_worker_lost is True
    assert document_tasks.generate_document_task.acks_on_failure_or_timeout is False


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", ["completed", "ready"])
async def test_terminal_document_redelivery_repairs_meter_without_regeneration(
    monkeypatch, terminal_status
):
    """A post-commit redelivery repairs metering without regenerating the file."""
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

    meter_calls = []

    async def record_activation(azienda_id, db):
        meter_calls.append((azienda_id, db))
        return False

    async def unexpected_async_boundary(*args, **kwargs):
        pytest.fail("Google Drive upload must not run for a terminal document")

    async def snapshot_hash(*args, **kwargs):
        return "snapshot"

    monkeypatch.setattr(document_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(document_tasks, "compute_survey_snapshot_hash", snapshot_hash)
    monkeypatch.setattr(document_tasks, "get_generator_for", unexpected_generator)
    monkeypatch.setattr(document_tasks, "record_activation_for_azienda", record_activation)
    monkeypatch.setattr(
        gdrive_service, "upload_generated_document", unexpected_async_boundary
    )

    await document_tasks._run_generation(document_id)

    assert vars(document) == before
    assert session.commit_calls == 0
    assert meter_calls == [(document.azienda_id, session)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("starting_attempts", "expected_attempts"),
    [(0, 1), (1, 2)],
)
async def test_generation_attempt_is_committed_before_dispatch(
    monkeypatch, tmp_path, starting_attempts, expected_attempts
):
    """The initial delivery and one recovery are durable before generator I/O."""
    events = []
    document = _document(generation_attempts=starting_attempts)
    session = _GenerationSession(document, events)
    output_path = tmp_path / "document.docx"
    output_path.write_bytes(b"generated document")

    class _Generator:
        async def generate(self):
            events.append(
                ("generate", document.generation_attempts, session.commit_calls)
            )
            return str(output_path)

    def generator_for(*args, **kwargs):
        return _Generator()

    async def snapshot_hash(*args, **kwargs):
        return "stable-snapshot"

    async def record_activation(*args, **kwargs):
        events.append(("meter", document.generation_attempts, document.status))
        return True

    async def upload(*args, **kwargs):
        events.append(("drive", document.generation_attempts, document.status))
        return None

    monkeypatch.setattr(document_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(document_tasks, "compute_survey_snapshot_hash", snapshot_hash)
    monkeypatch.setattr(document_tasks, "get_generator_for", generator_for)
    monkeypatch.setattr(document_tasks, "record_activation_for_azienda", record_activation)
    monkeypatch.setattr(gdrive_service, "upload_generated_document", upload)

    await document_tasks._run_generation(document.id)

    assert document.generation_attempts == expected_attempts
    assert document.status == "completed"
    assert document.file_content == b"generated document"
    assert events == [
        ("commit", expected_attempts, "in_progress"),
        ("generate", expected_attempts, 1),
        ("commit", expected_attempts, "completed"),
        ("meter", expected_attempts, "completed"),
        ("drive", expected_attempts, "completed"),
    ]


@pytest.mark.asyncio
async def test_third_delivery_returns_row_to_bozza_without_external_side_effects(
    monkeypatch,
):
    """Two interrupted generator entries bound automatic recovery at one replay."""
    events = []
    document = _document(status="in_progress", generation_attempts=2)
    document.file_path = "/worker/partial.docx"
    document.file_content = b"partial"
    document.file_name = "partial.docx"
    session = _GenerationSession(document, events)

    def unexpected_generator(*args, **kwargs):
        pytest.fail("a third delivery must not dispatch the generator")

    async def unexpected_async_boundary(*args, **kwargs):
        pytest.fail("a third delivery must not meter, upload, or snapshot")

    monkeypatch.setattr(document_tasks, "async_session_factory", lambda: session)
    monkeypatch.setattr(
        document_tasks, "compute_survey_snapshot_hash", unexpected_async_boundary
    )
    monkeypatch.setattr(document_tasks, "get_generator_for", unexpected_generator)
    monkeypatch.setattr(
        document_tasks, "record_activation_for_azienda", unexpected_async_boundary
    )
    monkeypatch.setattr(
        gdrive_service, "upload_generated_document", unexpected_async_boundary
    )

    await document_tasks._run_generation(document.id)

    assert document.status == "bozza"
    assert document.generation_attempts == 2
    assert document.file_path is None
    assert document.file_content is None
    assert document.file_name is None
    assert document.error_message == (
        "Generazione interrotta due volte. Riprova manualmente."
    )
    assert document.generation_completed_at is not None
    assert events == [("commit", 2, "bozza")]
