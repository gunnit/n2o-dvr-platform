"""The VERA ITALIA mark ships in every document's footer and in each HACCP
form, so it is kept web-sized (final review, M-6): 360 px wide for a
2.4 × 0.85 cm footer box (about 380 dpi), transparency and colours kept.
``scripts/extract_document_art.py`` writes it the same way, so re-running the
extraction cannot bring the 86 KB original back."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.services.document_generator.docx_utils import LOGO_PATH
from scripts import extract_document_art

# N2O's model holds the mark at 640 × 226.
_MODEL_SIZE = (640, 226)


def _model_like_mark() -> bytes:
    """A 640 × 226 RGBA logo: a colour gradient over a transparent field,
    with anti-aliased (partly transparent) edges."""
    image = Image.new("RGBA", _MODEL_SIZE, (0, 0, 0, 0))
    for x in range(40, 600):
        for y in range(30, 196):
            alpha = 255 if 45 <= x < 595 and 35 <= y < 191 else 128
            image.putpixel((x, y), (x % 256, 40, 134, alpha))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_committed_mark_is_web_sized_with_its_transparency():
    content = LOGO_PATH.read_bytes()
    with Image.open(BytesIO(content)) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"
        assert image.size == (extract_document_art.MARK_WIDTH, 127)
        alpha_low, alpha_high = image.getchannel("A").getextrema()
    assert (alpha_low, alpha_high) == (0, 255)
    # 86 600 bytes as extracted from the model; about 26 KB at 360 px.
    assert len(content) < 30_000


def test_extraction_writes_the_mark_at_360_px_keeping_alpha_and_aspect():
    written = extract_document_art.mark_png(_model_like_mark())
    with Image.open(BytesIO(written)) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"
        assert image.size == (360, round(226 * 360 / 640))
        assert image.getchannel("A").getextrema() == (0, 255)
        assert not image.info.get("exif") and not image.info.get("xmp")


def test_extraction_never_upscales_a_smaller_mark():
    small = Image.new("RGBA", (300, 106), (24, 41, 134, 255))
    buffer = BytesIO()
    small.save(buffer, format="PNG")
    with Image.open(BytesIO(extract_document_art.mark_png(buffer.getvalue()))) as image:
        assert image.size == (300, 106)
