import importlib.util
import struct
import uuid
import zlib
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pillow_heif
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.ambienti import get_ambiente_foto_content, upload_ambiente_foto
from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.ambiente_foto import AmbienteFoto
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


def test_invalid_image_raises_typed_error():
    with pytest.raises(DocumentImageNormalizationError):
        normalize_document_image(b"not an image")


@pytest.mark.parametrize(
    ("width", "height"),
    [(10_000, 5_000), (20_001, 1)],
)
def test_source_dimension_limits_reject_before_decoding(width, height):
    source = _png_with_declared_dimensions(width, height)
    with patch(
        "PIL.PngImagePlugin.PngImageFile.load",
        side_effect=AssertionError("oversized source was decoded"),
    ):
        with pytest.raises(DocumentImageNormalizationError, match="dimensioni"):
            normalize_document_image(source)


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
async def test_content_read_prefers_original_local_file(tmp_path, monkeypatch):
    original = tmp_path / "original.png"
    original.write_bytes(b"original")
    photo = SimpleNamespace(
        file_path=str(original),
        content_type="image/png",
        filename="reparto.png",
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
