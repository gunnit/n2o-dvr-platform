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
MAX_SOURCE_IMAGE_PIXELS = 40_000_000
MAX_SOURCE_IMAGE_EDGE = 20_000
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
            width, height = opened.size
            if (
                width > MAX_SOURCE_IMAGE_EDGE
                or height > MAX_SOURCE_IMAGE_EDGE
                or width * height > MAX_SOURCE_IMAGE_PIXELS
            ):
                raise DocumentImageNormalizationError(
                    "Immagine con dimensioni non supportate"
                )
            image = ImageOps.exif_transpose(opened).copy()
    except DocumentImageNormalizationError:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        ValueError,
        UnidentifiedImageError,
    ) as exc:
        raise DocumentImageNormalizationError("Immagine non decodificabile") from exc

    image = _flatten_to_rgb(image)
    image.thumbnail(
        (MAX_DOCUMENT_IMAGE_EDGE, MAX_DOCUMENT_IMAGE_EDGE),
        Image.Resampling.LANCZOS,
    )
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
            normalized = normalize_document_image(source.read_bytes())
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
