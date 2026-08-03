import importlib.util
import inspect as pyinspect
import logging
import struct
import threading
import uuid
import zlib
from datetime import datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pillow_heif
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import documents as documents_api
from app.api.v1.ambienti import get_ambiente_foto_content, upload_ambiente_foto
from app.api.v1.documents import batch_generate_documents, generate_document
from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.ambiente_foto import AmbienteFoto
from app.schemas.document import DocumentBatchRequest, DocumentGenerateRequest
from app.services import ambiente_photo
from app.services.ambiente_photo import (
    DocumentImageNormalizationError,
    NormalizedDocumentImage,
    normalize_document_image,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _image_bytes(image: Image.Image, image_format: str, **save_kwargs) -> bytes:
    output = BytesIO()
    image.save(output, format=image_format, **save_kwargs)
    return output.getvalue()


def _png_with_declared_dimensions(width: int, height: int) -> bytes:
    """Forge only the generated PNG header; no large pixel asset is allocated."""
    source = bytearray(_image_bytes(Image.new("RGB", (1, 1), "blue"), "PNG"))
    source[16:24] = struct.pack(">II", width, height)
    source[29:33] = struct.pack(">I", zlib.crc32(source[12:29]) & 0xFFFFFFFF)
    return bytes(source)


@pytest.fixture
def heic_fixture_bytes() -> bytes:
    output = BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (48, 32), "green")).save(output)
    return output.getvalue()


def test_png_normalizes_to_bounded_white_background_jpeg():
    source_image = Image.new("RGBA", (4000, 1200), (0, 0, 0, 0))
    source = _image_bytes(source_image, "PNG")
    result = normalize_document_image(source)
    assert result.content_type == "image/jpeg"
    assert len(result.content) <= 3 * 1024 * 1024
    with Image.open(BytesIO(result.content)) as image:
        assert image.mode == "RGB"
        assert max(image.size) == 2000
        assert all(channel >= 250 for channel in image.getpixel((0, 0)))


def test_exif_orientation_is_applied():
    source_image = Image.new("RGB", (40, 20), "red")
    exif = Image.Exif()
    exif[274] = 6
    result = normalize_document_image(_image_bytes(source_image, "JPEG", exif=exif))
    with Image.open(BytesIO(result.content)) as image:
        assert image.size == (20, 40)


def test_small_image_is_not_enlarged():
    result = normalize_document_image(
        _image_bytes(Image.new("RGB", (320, 200), "blue"), "PNG")
    )
    with Image.open(BytesIO(result.content)) as image:
        assert image.size == (320, 200)


def test_ordinary_twelve_megapixel_phone_photo_is_supported():
    source = _image_bytes(Image.new("RGB", (4_032, 3_024), "navy"), "JPEG")

    result = normalize_document_image(source)

    with Image.open(BytesIO(result.content)) as image:
        assert image.size == (2_000, 1_500)


def test_payload_fallback_reduces_dimensions(monkeypatch):
    noisy = Image.effect_noise((2000, 2000), 100).convert("RGB")
    monkeypatch.setattr(
        "app.services.ambiente_photo.MAX_DOCUMENT_IMAGE_BYTES", 200_000
    )
    result = normalize_document_image(_image_bytes(noisy, "PNG"))
    assert len(result.content) <= 200_000
    with Image.open(BytesIO(result.content)) as image:
        assert max(image.size) < 2000


def test_heic_normalizes_to_jpeg(heic_fixture_bytes):
    result = normalize_document_image(heic_fixture_bytes)
    assert result.content[:2] == b"\xff\xd8"


@pytest.mark.parametrize("image_format", ["GIF", "WEBP", "TIFF"])
def test_decodable_non_photo_contract_formats_are_rejected(image_format):
    disguised = _image_bytes(Image.new("RGB", (16, 16), "purple"), image_format)

    with pytest.raises(DocumentImageNormalizationError, match="formato"):
        normalize_document_image(disguised)


def test_invalid_image_raises_typed_error():
    with pytest.raises(DocumentImageNormalizationError):
        normalize_document_image(b"not an image")


@pytest.mark.parametrize(
    ("width", "height"),
    [(6_251, 4_000), (8_193, 1)],
)
def test_source_dimension_limits_reject_before_decoding(width, height):
    source = _png_with_declared_dimensions(width, height)
    with patch(
        "PIL.PngImagePlugin.PngImageFile.load",
        side_effect=AssertionError("oversized source was decoded"),
    ):
        with pytest.raises(DocumentImageNormalizationError, match="dimensioni"):
            normalize_document_image(source)


def test_rgba_source_is_resized_before_alpha_flattening(monkeypatch):
    source = _image_bytes(Image.new("RGBA", (4_000, 1_200), (0, 0, 0, 0)), "PNG")
    flattened_sizes = []
    real_flatten = ambiente_photo._flatten_to_rgb

    def record_flatten(image):
        flattened_sizes.append(image.size)
        return real_flatten(image)

    monkeypatch.setattr(ambiente_photo, "_flatten_to_rgb", record_flatten)

    normalize_document_image(source)

    assert flattened_sizes == [(2_000, 600)]


def test_photo_model_has_nullable_document_derivative_columns():
    table = AmbienteFoto.__table__
    assert table.c.document_image_bytes.nullable is True
    assert table.c.document_image_content_type.nullable is True


def test_photo_migration_upgrades_and_downgrades_disposable_sqlite(monkeypatch):
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "a9b0c1d2e3f4_add_document_image_to_ambiente_foto.py"
    )
    spec = importlib.util.spec_from_file_location("photo_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE ambienti_foto (id INTEGER PRIMARY KEY)")
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()
        upgraded = {
            column["name"] for column in inspect(connection).get_columns("ambienti_foto")
        }
        assert {"document_image_bytes", "document_image_content_type"} <= upgraded
        migration.downgrade()
        downgraded = {
            column["name"] for column in inspect(connection).get_columns("ambienti_foto")
        }
        assert downgraded == {"id"}


@pytest.mark.asyncio
async def test_upload_persists_normalized_bytes(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with patch("app.api.v1.ambienti.normalize_document_image") as normalize:
        normalize.return_value = NormalizedDocumentImage(b"jpeg", "image/jpeg")
        photo = await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )
    assert photo.document_image_bytes == b"jpeg"
    assert photo.document_image_content_type == "image/jpeg"
    assert Path(photo.file_path).read_bytes()


@pytest.mark.asyncio
async def test_upload_normalization_runs_off_the_event_loop(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    event_loop_thread = threading.get_ident()
    normalization_threads = []
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())

    def record_normalization(_content):
        normalization_threads.append(threading.get_ident())
        return NormalizedDocumentImage(b"jpeg", "image/jpeg")

    monkeypatch.setattr(
        "app.api.v1.ambienti.normalize_document_image", record_normalization
    )
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )

    await upload_ambiente_foto(
        uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
    )

    assert normalization_threads
    assert normalization_threads[0] != event_loop_thread


@pytest.mark.asyncio
async def test_upload_removes_only_new_file_when_commit_fails(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    azienda_id, ambiente_id, org_id, file_id = [uuid.uuid4() for _ in range(4)]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.commit.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    monkeypatch.setattr("app.api.v1.ambienti.uuid.uuid4", lambda: file_id)
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        await upload_ambiente_foto(azienda_id, ambiente_id, upload, org_id, db)
    assert not (
        tmp_path / "foto_ambienti" / str(ambiente_id) / f"{file_id}.png"
    ).exists()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_image_creates_no_row(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="guasto.jpg",
        file=BytesIO(b"not-an-image"),
        headers={"content-type": "image/jpeg"},
    )
    with pytest.raises(
        BadRequestError, match="Formato non supportato o file troppo grande"
    ):
        await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )
    db.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("image_format", ["GIF", "WEBP", "TIFF"])
async def test_disguised_format_upload_creates_no_row_or_file(
    tmp_path, monkeypatch, image_format
):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="camuffata.jpg",
        file=BytesIO(
            _image_bytes(Image.new("RGB", (16, 16), "purple"), image_format)
        ),
        headers={"content-type": "image/jpeg"},
    )

    with pytest.raises(BadRequestError) as exc_info:
        await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )

    assert exc_info.value.detail == (
        "Formato non supportato o file troppo grande (max 10 MB)"
    )
    db.add.assert_not_called()
    assert not (tmp_path / "foto_ambienti").exists()


@pytest.mark.asyncio
async def test_oversized_source_upload_creates_no_row_or_file(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    upload = UploadFile(
        filename="troppo-grande.png",
        file=BytesIO(_png_with_declared_dimensions(20_000, 10_000)),
        headers={"content-type": "image/png"},
    )

    with pytest.raises(
        BadRequestError,
        match=r"Formato non supportato o file troppo grande \(max 10 MB\)",
    ):
        await upload_ambiente_foto(
            uuid.uuid4(), uuid.uuid4(), upload, uuid.uuid4(), db
        )

    db.add.assert_not_called()
    assert not (tmp_path / "foto_ambienti").exists()


@pytest.mark.asyncio
async def test_refresh_failure_keeps_file_after_successful_commit(tmp_path, monkeypatch):
    class CountResult:
        def scalar_one(self):
            return 0

    azienda_id, ambiente_id, org_id, file_id = [uuid.uuid4() for _ in range(4)]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = CountResult()
    db.add = Mock()
    db.refresh.side_effect = RuntimeError("refresh failed")
    monkeypatch.setattr(settings, "FILE_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())
    monkeypatch.setattr("app.api.v1.ambienti.uuid.uuid4", lambda: file_id)
    upload = UploadFile(
        filename="reparto.png",
        file=BytesIO(_image_bytes(Image.new("RGB", (32, 32), "blue"), "PNG")),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(RuntimeError, match="refresh failed"):
        await upload_ambiente_foto(azienda_id, ambiente_id, upload, org_id, db)
    assert (
        tmp_path / "foto_ambienti" / str(ambiente_id) / f"{file_id}.png"
    ).exists()
    db.rollback.assert_not_awaited()


class _PhotoResult:
    def __init__(self, photo):
        self.photo = photo

    def scalar_one_or_none(self):
        return self.photo


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stored_name",
    ["folder/photo.jpg", r"folder\photo.jpg"],
    ids=["posix-separator", "windows-separator"],
)
async def test_content_read_local_file_sanitizes_response_filename(
    tmp_path, monkeypatch, stored_name
):
    original = tmp_path / "original.png"
    original.write_bytes(b"original")
    photo = SimpleNamespace(
        file_path=str(original),
        content_type="image/png",
        filename=stored_name,
        document_image_bytes=b"normalized",
        document_image_content_type="image/jpeg",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = _PhotoResult(photo)
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())

    response = await get_ambiente_foto_content(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), db
    )

    assert isinstance(response, FileResponse)
    assert Path(response.path).read_bytes() == b"original"
    assert response.media_type == "image/png"
    assert response.headers["content-disposition"] == (
        'attachment; filename="photo.jpg"'
    )


@pytest.mark.asyncio
async def test_content_read_falls_back_to_database_derivative(tmp_path, monkeypatch):
    photo = SimpleNamespace(
        file_path=str(tmp_path / "missing.heic"),
        content_type="image/heic",
        filename="reparto.heic",
        document_image_bytes=b"normalized-jpeg",
        document_image_content_type="image/jpeg",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = _PhotoResult(photo)
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())

    response = await get_ambiente_foto_content(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), db
    )

    assert response.body == b"normalized-jpeg"
    assert response.media_type == "image/jpeg"
    assert response.headers["content-disposition"] == (
        "inline; filename*=UTF-8''reparto.heic"
    )


@pytest.mark.asyncio
async def test_content_read_404s_when_original_and_derivative_are_unavailable(
    tmp_path, monkeypatch
):
    photo = SimpleNamespace(
        file_path=str(tmp_path / "missing.png"),
        content_type="image/png",
        filename="reparto.png",
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = _PhotoResult(photo)
    monkeypatch.setattr("app.api.v1.ambienti._get_ambiente_for_org", AsyncMock())

    with pytest.raises(NotFoundError, match="Foto file missing on storage"):
        await get_ambiente_foto_content(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), db
        )


@pytest.mark.asyncio
async def test_backfill_reads_legacy_api_disk_and_commits_before_return(tmp_path):
    class ScalarRows:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    source = tmp_path / "legacy.png"
    source.write_bytes(_image_bytes(Image.new("RGB", (64, 32), "blue"), "PNG"))
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="legacy.png",
        file_path=str(source),
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows([photo])

    result = await ambiente_photo.backfill_document_images_for_dvr(uuid.uuid4(), db)

    assert result == ambiente_photo.PhotoBackfillResult(
        attempted=1, stored=1, unavailable=0, failed=0
    )
    assert photo.document_image_bytes.startswith(b"\xff\xd8")
    assert photo.document_image_content_type == "image/jpeg"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_requests_only_a_bounded_legacy_read(tmp_path):
    class ScalarRows:
        def scalars(self):
            return self

        def all(self):
            return [photo]

    requested_sizes = []

    class RecordingReader(BytesIO):
        def read(self, size=-1):
            requested_sizes.append(size)
            return super().read(size)

    source = tmp_path / "legacy.png"
    source.write_bytes(b"placeholder")
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="legacy.png",
        file_path=str(source),
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows()
    reader = RecordingReader(
        _image_bytes(Image.new("RGB", (64, 32), "blue"), "PNG")
    )

    with patch.object(Path, "open", return_value=reader):
        result = await ambiente_photo.backfill_document_images_for_dvr(
            uuid.uuid4(), db
        )

    assert result == ambiente_photo.PhotoBackfillResult(1, 1, 0, 0)
    assert requested_sizes == [10 * 1024 * 1024 + 1]


@pytest.mark.asyncio
async def test_backfill_rejects_legacy_file_over_original_upload_limit(
    tmp_path, monkeypatch
):
    class ScalarRows:
        def scalars(self):
            return self

        def all(self):
            return [photo]

    source = tmp_path / "legacy-too-large.jpg"
    source.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="legacy-too-large.jpg",
        file_path=str(source),
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows()
    normalize = Mock(
        return_value=NormalizedDocumentImage(b"must-not-store", "image/jpeg")
    )
    monkeypatch.setattr(ambiente_photo, "normalize_document_image", normalize)

    result = await ambiente_photo.backfill_document_images_for_dvr(
        uuid.uuid4(), db
    )

    assert result == ambiente_photo.PhotoBackfillResult(1, 0, 0, 1)
    assert photo.document_image_bytes is None
    normalize.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_file_and_cpu_work_run_off_the_event_loop(
    tmp_path, monkeypatch
):
    class ScalarRows:
        def scalars(self):
            return self

        def all(self):
            return [photo]

    source = tmp_path / "legacy.png"
    source.write_bytes(_image_bytes(Image.new("RGB", (64, 32), "blue"), "PNG"))
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="legacy.png",
        file_path=str(source),
        document_image_bytes=None,
        document_image_content_type=None,
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows()
    event_loop_thread = threading.get_ident()
    normalization_threads = []

    def record_normalization(_content):
        normalization_threads.append(threading.get_ident())
        return NormalizedDocumentImage(b"jpeg", "image/jpeg")

    monkeypatch.setattr(ambiente_photo, "normalize_document_image", record_normalization)

    result = await ambiente_photo.backfill_document_images_for_dvr(
        uuid.uuid4(), db
    )

    assert result == ambiente_photo.PhotoBackfillResult(1, 1, 0, 0)
    assert normalization_threads
    assert normalization_threads[0] != event_loop_thread


@pytest.mark.asyncio
async def test_backfill_leaves_unavailable_and_invalid_rows_null_without_paths_in_logs(
    tmp_path, caplog
):
    class ScalarRows:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    invalid_path = tmp_path / "invalid.jpg"
    invalid_path.write_bytes(b"not-an-image")
    rows = [
        SimpleNamespace(
            id=uuid.UUID(int=11),
            filename="private/missing.jpg",
            file_path=str(tmp_path / "private" / "missing.jpg"),
            document_image_bytes=None,
            document_image_content_type=None,
        ),
        SimpleNamespace(
            id=uuid.UUID(int=12),
            filename=r"private\invalid.jpg",
            file_path=str(invalid_path),
            document_image_bytes=None,
            document_image_content_type=None,
        ),
    ]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = ScalarRows(rows)

    with caplog.at_level(logging.WARNING):
        result = await ambiente_photo.backfill_document_images_for_dvr(
            uuid.uuid4(), db
        )

    assert result == ambiente_photo.PhotoBackfillResult(2, 0, 1, 1)
    assert all(photo.document_image_bytes is None for photo in rows)
    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert {
        (record.photo_id, record.photo_filename) for record in warnings
    } == {
        (str(uuid.UUID(int=11)), "missing.jpg"),
        (str(uuid.UUID(int=12)), "invalid.jpg"),
    }
    assert all(str(tmp_path) not in record.getMessage() for record in warnings)
    assert all("private" not in record.getMessage() for record in warnings)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_photo_content_falls_back_to_database_bytes_when_disk_is_missing(
    tmp_path,
):
    class OneRow:
        def __init__(self, row):
            self.row = row

        def scalar_one_or_none(self):
            return self.row

    photo = SimpleNamespace(
        id=uuid.uuid4(),
        filename="folder/foto con spazi.jpg",
        file_path=str(tmp_path / "missing.jpg"),
        content_type="image/jpeg",
        document_image_bytes=b"jpeg-from-db",
        document_image_content_type="image/jpeg",
    )
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = OneRow(photo)
    ids = [uuid.uuid4() for _ in range(3)]

    with patch("app.api.v1.ambienti._get_ambiente_for_org", new=AsyncMock()):
        response = await get_ambiente_foto_content(
            ids[0], ids[1], photo.id, ids[2], db
        )

    assert isinstance(response, Response)
    assert response.body == photo.document_image_bytes
    assert response.media_type == "image/jpeg"
    assert response.headers["content-disposition"] == (
        "inline; filename*=UTF-8''foto%20con%20spazi.jpg"
    )


@pytest.mark.asyncio
async def test_preflight_calls_backfill_only_when_dvr_is_requested():
    db = AsyncMock(spec=AsyncSession)
    azienda_id = uuid.uuid4()
    result = SimpleNamespace(attempted=1, stored=1, unavailable=0, failed=0)
    with patch.object(
        documents_api,
        "backfill_document_images_for_dvr",
        new=AsyncMock(return_value=result),
        create=True,
    ) as backfill:
        assert await documents_api._preflight_dvr_photo_transport(
            azienda_id, ["dvr_master", "allegato_vdt"], db
        ) == result
        assert (
            await documents_api._preflight_dvr_photo_transport(
                azienda_id, ["allegato_vdt"], db
            )
            is None
        )
    backfill.assert_awaited_once_with(azienda_id, db)


def test_single_and_batch_routes_preflight_before_dispatch():
    for endpoint in (generate_document, batch_generate_documents):
        source = pyinspect.getsource(endpoint)
        assert source.index("await _preflight_dvr_photo_transport") < source.index(
            "_enqueue_generation"
        )


class _LatestDocumentResult:
    def scalar_one_or_none(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "body", "requested_types", "expects_preflight"),
    [
        (
            generate_document,
            DocumentGenerateRequest(tipo_documento="dvr_master"),
            ["dvr_master"],
            True,
        ),
        (
            generate_document,
            DocumentGenerateRequest(tipo_documento="allegato_vdt"),
            ["allegato_vdt"],
            False,
        ),
        (
            batch_generate_documents,
            DocumentBatchRequest(tipi_documento=["allegato_vdt", "dvr_master"]),
            ["allegato_vdt", "dvr_master"],
            True,
        ),
        (
            batch_generate_documents,
            DocumentBatchRequest(tipi_documento=["allegato_vdt"]),
            ["allegato_vdt"],
            False,
        ),
    ],
)
async def test_document_routes_preflight_once_only_for_dvr_requests(
    endpoint, body, requested_types, expects_preflight
):
    azienda_id, org_id, user_id = [uuid.uuid4() for _ in range(3)]
    db = AsyncMock(spec=AsyncSession)
    db.add = Mock()
    db.execute.return_value = _LatestDocumentResult()
    events: list[str] = []

    async def record_backfill(*args):
        events.append("preflight")

    def record_dispatch(*args):
        events.append("dispatch")

    async def stamp_document(doc):
        doc.id = uuid.uuid4()
        doc.created_at = datetime(2026, 8, 3)

    db.refresh.side_effect = stamp_document
    azienda = SimpleNamespace(
        codice_fiscale="01234567890", telefono=None, email=None, pec=None
    )
    user = SimpleNamespace(id=user_id)
    ent = SimpleNamespace()
    with (
        patch.object(documents_api, "_get_azienda", new=AsyncMock(return_value=azienda)),
        patch.object(documents_api, "ensure_subscription_active"),
        patch.object(documents_api, "ensure_doc_type_allowed"),
        patch.object(
            documents_api,
            "_ensure_company_slot_available",
            new=AsyncMock(),
        ),
        patch.object(
            documents_api,
            "_ensure_anagrafica_complete_for_dvr",
            new=AsyncMock(),
        ),
        patch.object(
            documents_api,
            "_ensure_dvr_exists_for_dependent",
            new=AsyncMock(),
        ),
        patch.object(
            documents_api,
            "_check_batch_preconditions",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(
            documents_api,
            "_resolve_user_name",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            documents_api,
            "backfill_document_images_for_dvr",
            new=AsyncMock(side_effect=record_backfill),
            create=True,
        ) as backfill,
        patch.object(documents_api, "_enqueue_generation", side_effect=record_dispatch),
    ):
        await endpoint(azienda_id, body, org_id, user, ent, db)

    if expects_preflight:
        backfill.assert_awaited_once_with(azienda_id, db)
        assert events[0] == "preflight"
    else:
        backfill.assert_not_awaited()
    assert events.count("dispatch") == len(requested_types)
