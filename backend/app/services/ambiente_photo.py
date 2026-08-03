import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ambiente import Ambiente
from app.models.ambiente_foto import AmbienteFoto

MAX_DOCUMENT_IMAGE_BYTES = 3 * 1024 * 1024
MAX_DOCUMENT_IMAGE_EDGE = 2000
MIN_DOCUMENT_IMAGE_EDGE = 640
MAX_ORIGINAL_IMAGE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_IMAGE_PIXELS = 25_000_000
MAX_SOURCE_IMAGE_EDGE = 8_192
ALLOWED_DECODED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "HEIF", "HEIC"})
JPEG_QUALITIES = (88, 82, 76, 70, 64, 58, 52, 46, 40)
logger = logging.getLogger(__name__)


class DocumentImageNormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizedDocumentImage:
    content: bytes
    content_type: str


@dataclass(frozen=True)
class PhotoBackfillResult:
    attempted: int
    stored: int
    unavailable: int
    failed: int


def normalize_document_image(content: bytes) -> NormalizedDocumentImage:
    register_heif_opener()
    try:
        with Image.open(BytesIO(content)) as opened:
            decoded_format = (opened.format or "").upper()
            if decoded_format not in ALLOWED_DECODED_IMAGE_FORMATS:
                raise DocumentImageNormalizationError(
                    "Immagine con formato non supportato"
                )
            width, height = opened.size
            if (
                width > MAX_SOURCE_IMAGE_EDGE
                or height > MAX_SOURCE_IMAGE_EDGE
                or width * height > MAX_SOURCE_IMAGE_PIXELS
            ):
                raise DocumentImageNormalizationError(
                    "Immagine con dimensioni non supportate"
                )
            # JPEG decoders can subsample during decode. For every format,
            # reduce the single source image before EXIF copying and alpha
            # flattening so no second full-resolution RGBA buffer is created.
            if decoded_format == "JPEG":
                opened.draft(
                    "RGB", (MAX_DOCUMENT_IMAGE_EDGE, MAX_DOCUMENT_IMAGE_EDGE)
                )
            opened.thumbnail(
                (MAX_DOCUMENT_IMAGE_EDGE, MAX_DOCUMENT_IMAGE_EDGE),
                Image.Resampling.LANCZOS,
                reducing_gap=2.0,
            )
            image = _flatten_to_rgb(ImageOps.exif_transpose(opened))
    except DocumentImageNormalizationError:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        ValueError,
        UnidentifiedImageError,
    ) as exc:
        raise DocumentImageNormalizationError("Immagine non decodificabile") from exc

    while True:
        for quality in JPEG_QUALITIES:
            output = BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            if output.tell() <= MAX_DOCUMENT_IMAGE_BYTES:
                return NormalizedDocumentImage(output.getvalue(), "image/jpeg")

        longest = max(image.size)
        if longest <= MIN_DOCUMENT_IMAGE_EDGE:
            raise DocumentImageNormalizationError(
                "Immagine normalizzata oltre il limite di 3 MB"
            )
        scale = max(MIN_DOCUMENT_IMAGE_EDGE / longest, 0.85)
        image = image.resize(
            (
                max(1, round(image.width * scale)),
                max(1, round(image.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        foreground = image.convert("RGBA")
        background = Image.new("RGBA", foreground.size, (255, 255, 255, 255))
        background.alpha_composite(foreground)
        return background.convert("RGB")
    return image.convert("RGB")


def _read_and_normalize_legacy_photo(source: Path) -> NormalizedDocumentImage:
    with source.open("rb") as stream:
        content = stream.read(MAX_ORIGINAL_IMAGE_BYTES + 1)
    if len(content) > MAX_ORIGINAL_IMAGE_BYTES:
        raise DocumentImageNormalizationError(
            "File originale oltre il limite di 10 MB"
        )
    return normalize_document_image(content)


async def backfill_document_images_for_dvr(
    azienda_id: UUID, db: AsyncSession
) -> PhotoBackfillResult:
    """Persist normalized derivatives for legacy photos before DVR dispatch."""
    photos = (
        (
            await db.execute(
                select(AmbienteFoto)
                .join(Ambiente, Ambiente.id == AmbienteFoto.ambiente_id)
                .where(
                    Ambiente.azienda_id == azienda_id,
                    AmbienteFoto.document_image_bytes.is_(None),
                )
                .order_by(AmbienteFoto.created_at, AmbienteFoto.id)
            )
        )
        .scalars()
        .all()
    )
    stored = unavailable = failed = 0
    for photo in photos:
        safe_name = Path(
            str(getattr(photo, "filename", None) or photo.id).replace("\\", "/")
        ).name[:255]
        file_path = getattr(photo, "file_path", None)
        source = Path(file_path) if file_path else None
        if source is None or not source.is_file():
            unavailable += 1
            logger.warning(
                "Legacy DVR photo file is unavailable",
                extra={"photo_id": str(photo.id), "photo_filename": safe_name},
            )
            continue
        try:
            normalized = await asyncio.to_thread(
                _read_and_normalize_legacy_photo, source
            )
        except (OSError, DocumentImageNormalizationError):
            failed += 1
            logger.warning(
                "Legacy DVR photo normalization failed",
                extra={"photo_id": str(photo.id), "photo_filename": safe_name},
            )
            continue
        photo.document_image_bytes = normalized.content
        photo.document_image_content_type = normalized.content_type
        stored += 1
    await db.commit()
    return PhotoBackfillResult(len(photos), stored, unavailable, failed)
