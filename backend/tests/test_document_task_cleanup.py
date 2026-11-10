"""The worker deletes what a generation wrote to its disk (final review, W-1).

The Celery worker writes each document to its own 1 GB Render disk, copies
the bytes into Postgres (``file_content``) and uploads them to Drive. Nothing
else ever reads that file: the API runs on another disk and serves
``file_content``. So once the bytes are stored and the Drive attempt is over,
the run's files go — the document itself and, for the HACCP forms, the
record forms packed into its zip. Nothing else in the shared per-azienda
directory is touched, and a cleanup problem never fails the generation.
"""

from __future__ import annotations

import logging
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import gdrive_service
from app.tasks import document_tasks


def _document():
    return SimpleNamespace(
        id=uuid.uuid4(),
        azienda_id=uuid.uuid4(),
        tipo_documento="dvr_master",
        versione=1,
        options=None,
        status="pending",
        generation_attempts=0,
        file_path=None,
        file_name=None,
        file_content=None,
        error_message=None,
        generation_started_at=None,
        generation_completed_at=None,
        survey_snapshot_hash=None,
        stale_snapshot=False,
        gdrive_file_id=None,
    )


class _Result:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


class _Session:
    def __init__(self, document):
        self._document = document

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, statement):
        return _Result(self._document)

    async def commit(self):
        pass

    async def rollback(self):
        pass


class _Generator:
    def __init__(self, write):
        self._write = write

    async def generate(self):
        return str(self._write())


@pytest.fixture
def worker(monkeypatch):
    """Run ``_run_generation`` against a fake session and generator; returns
    ``run(write, upload=...)`` -> the document row afterwards."""

    async def snapshot_hash(*args, **kwargs):
        return "snapshot"

    async def record_activation(*args, **kwargs):
        return True

    monkeypatch.setattr(document_tasks, "compute_survey_snapshot_hash", snapshot_hash)
    monkeypatch.setattr(document_tasks, "record_activation_for_azienda", record_activation)

    async def no_drive(doc, path):
        return None

    async def run(write, upload=no_drive):
        document = _document()
        monkeypatch.setattr(document_tasks, "async_session_factory", lambda: _Session(document))
        monkeypatch.setattr(
            document_tasks, "get_generator_for", lambda *a, **k: _Generator(write)
        )
        monkeypatch.setattr(gdrive_service, "upload_generated_document", upload)
        await document_tasks._run_generation(document.id)
        return document

    return run


# What other runs left in the same per-azienda directory: never touched.
_OTHER_RUNS = {
    "allegato_vdt_acme_v3.docx": b"another document",
    "haccp_forms_SA-01_acme_v1.docx": b"an older form",
}


def _azienda_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "documents" / "azienda"
    directory.mkdir(parents=True)
    for name, content in _OTHER_RUNS.items():
        (directory / name).write_bytes(content)
    return directory


def _files(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.asyncio
async def test_completed_document_is_deleted_after_the_drive_attempt(tmp_path, worker):
    directory = _azienda_dir(tmp_path)
    output = directory / "dvr_master_acme_v4.docx"
    seen_by_drive = []

    def write():
        output.write_bytes(b"the generated DVR")
        return output

    async def upload(doc, path):
        seen_by_drive.append((path, Path(path).read_bytes()))
        return "drive-id"

    document = await worker(write, upload)

    assert document.status == "completed"
    assert document.file_content == b"the generated DVR"
    assert seen_by_drive == [(str(output), b"the generated DVR")]
    assert document.gdrive_file_id == "drive-id"
    assert not output.exists()
    # The row still names the file: the documents page and the filename of
    # a download read these, never the disk.
    assert (document.file_path, document.file_name) == (str(output), output.name)
    assert _files(directory) == _OTHER_RUNS


@pytest.mark.asyncio
async def test_failed_drive_upload_still_deletes_the_file(tmp_path, worker):
    directory = _azienda_dir(tmp_path)
    output = directory / "dvr_master_acme_v4.docx"

    def write():
        output.write_bytes(b"the generated DVR")
        return output

    async def upload(doc, path):
        raise RuntimeError("Drive is down")

    document = await worker(write, upload)

    assert document.status == "completed"
    assert document.file_content == b"the generated DVR"
    assert not output.exists()


@pytest.mark.asyncio
async def test_file_is_kept_when_its_bytes_were_not_stored(tmp_path, worker, monkeypatch):
    directory = _azienda_dir(tmp_path)
    output = directory / "dvr_master_acme_v4.docx"

    def write():
        output.write_bytes(b"the generated DVR")
        return output

    def unreadable(path, *args, **kwargs):
        raise OSError("disk read error")

    # The task's own `open` (module globals shadow the builtin).
    monkeypatch.setattr(document_tasks, "open", unreadable, raising=False)

    document = await worker(write)

    assert document.status == "completed"
    assert document.file_content is None
    # The file is the only copy: it stays.
    assert output.read_bytes() == b"the generated DVR"


def _write_bundle(directory: Path) -> tuple[Path, list[Path], Path]:
    """What the HACCP forms generator does: one .docx per form beside the
    zip, each packed under its own name, plus an index built in memory."""
    forms = [
        directory / f"haccp_forms_{code}_acme_v2.docx" for code in ("SA-01", "SA-02", "SA-03")
    ]
    for index, form in enumerate(forms):
        form.write_bytes(f"form {index}".encode() * 50)
    bundle = directory / "haccp_forms_acme_v2.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("INDICE_schede_HACCP.docx", b"index")
        for form in forms:
            zf.write(form, arcname=form.name)
    # Rewritten after packing: no longer the run's packed file, so it stays.
    changed = forms[2]
    changed.write_bytes(b"edited after packing")
    return bundle, forms[:2], changed


@pytest.mark.asyncio
async def test_bundle_deletes_the_forms_it_packed_and_nothing_else(tmp_path, worker):
    directory = _azienda_dir(tmp_path)
    created = {}

    def write():
        bundle, packed, changed = _write_bundle(directory)
        created.update(bundle=bundle, packed=packed, changed=changed)
        return bundle

    document = await worker(write)

    assert document.status == "completed"
    assert document.file_content[:2] == b"PK"  # the zip, stored before deletion
    assert not created["bundle"].exists()
    assert [form.exists() for form in created["packed"]] == [False, False]
    assert _files(directory) == {
        **_OTHER_RUNS,
        created["changed"].name: b"edited after packing",
    }


@pytest.mark.asyncio
async def test_failed_generation_discards_the_bundle_and_its_forms(
    tmp_path, worker, monkeypatch
):
    directory = _azienda_dir(tmp_path)
    created = {}

    def write():
        bundle, packed, changed = _write_bundle(directory)
        created.update(bundle=bundle, packed=packed)
        return bundle

    async def metering_down(*args, **kwargs):
        raise RuntimeError("metering unavailable")

    monkeypatch.setattr(document_tasks, "record_activation_for_azienda", metering_down)

    document = await worker(write)

    assert document.status == "bozza"
    assert not created["bundle"].exists()
    assert [form.exists() for form in created["packed"]] == [False, False]
    assert set(_files(directory)) == {*_OTHER_RUNS, "haccp_forms_SA-03_acme_v2.docx"}


@pytest.mark.asyncio
async def test_cleanup_failure_is_logged_and_never_fails_the_generation(
    tmp_path, worker, monkeypatch, caplog
):
    directory = _azienda_dir(tmp_path)
    output = directory / "dvr_master_acme_v4.docx"

    def write():
        output.write_bytes(b"the generated DVR")
        return output

    def refuse(path, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(document_tasks.os, "remove", refuse)
    monkeypatch.setattr(document_tasks.os, "unlink", refuse)

    with caplog.at_level(logging.WARNING, logger=document_tasks.logger.name):
        document = await worker(write)

    assert document.status == "completed"
    assert document.file_content == b"the generated DVR"
    assert output.exists()
    assert any(
        record.levelno == logging.WARNING and str(output) in record.getMessage()
        for record in caplog.records
    )
