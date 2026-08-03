from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

MAX_DOCUMENT_IMAGE_BYTES = 3 * 1024 * 1024
MAX_DOCUMENT_IMAGE_EDGE = 2000
MIN_DOCUMENT_IMAGE_EDGE = 640
JPEG_QUALITIES = (88, 82, 76, 70, 64, 58, 52, 46, 40)


class DocumentImageNormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizedDocumentImage:
    content: bytes
    content_type: str


def normalize_document_image(content: bytes) -> NormalizedDocumentImage:
    register_heif_opener()
    try:
        with Image.open(BytesIO(content)) as opened:
            image = ImageOps.exif_transpose(opened).copy()
    except (OSError, ValueError, UnidentifiedImageError) as exc:
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
